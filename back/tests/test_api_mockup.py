import os
from datetime import UTC, datetime, timedelta

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from back.core.categories import CATEGORIES
from back.core.security import create_access_token, hash_password
from back.db.base import Base
from back.db.models import (
    BusinessCategory,
    BusinessProfile,
    Category,
    Company,
    EventAnalysis,
    NewsEvent,
    User,
)
from back.db.session import get_session
from back.main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/alfafuture_test",
)


def _event(
    title: str,
    summary: str,
    *,
    impact: str,
    importance: int,
    category_ids: list[int],
    days_ago: float = 0,
) -> NewsEvent:
    published = datetime.now(UTC) - timedelta(days=days_ago)
    return NewsEvent(
        title=title,
        summary=summary,
        what_it_means="Влияние на экспорт и маржу компании.",
        source_name="Правительство РФ",
        published_at=published,
        importance=importance,
        impact=impact,
        category_ids=category_ids,
        mentioned_company_uids=[],
        facts=[{"text": "Постановление опубликовано", "status": "Официально"}],
        source_posts=[
            {
                "name": "Правительство РФ",
                "time": published.isoformat(),
                "tone": "official",
                "text": summary,
                "is_primary": True,
            },
            {
                "name": "Деловой вестник",
                "time": (published + timedelta(minutes=15)).isoformat(),
                "tone": "neutral",
                "text": "Подробности в отраслевом канале.",
            },
        ],
        chain_key="metals-duty",
    )


@pytest.fixture
async def api_env():
    url = make_url(TEST_DATABASE_URL)
    try:
        admin = await asyncpg.connect(
            user=url.username,
            password=url.password,
            host=url.host,
            port=url.port or 5432,
            database="postgres",
        )
    except Exception as exc:  # pragma: no cover - depends on local services
        pytest.skip(f"Postgres недоступен: {exc}")
    try:
        exists = await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", url.database)
        if not exists:
            await admin.execute(f'CREATE DATABASE "{url.database}"')
    finally:
        await admin.close()

    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        for item in CATEGORIES:
            session.add(
                Category(
                    id=item.id,
                    slug=item.slug,
                    name=item.name,
                    short_name=item.short_name,
                    group=item.group,
                    description=item.description,
                    example=item.example,
                    channels=list(item.channels),
                )
            )
        session.add(
            Company(
                uid="U_TEST_001",
                main_okved_code="24.10",
                main_okved_name="Производство чугуна, стали и ферросплавов",
                revenue=52_000_000_000,
                revenue_segment="крупнейший",
                city="Екатеринбург",
                region="Свердловская область",
                fts_flag=True,
                fts_country_name="Турция",
                cl_product_rko_mark=True,
                cl_product_loa_mark=True,
                tags=["металлургия", "ВЭД"],
            )
        )
        user = User(login="api_test", password_hash=hash_password("secret"))
        session.add(user)
        await session.flush()
        profile = BusinessProfile(
            user_id=user.id,
            company_uid="U_TEST_001",
            entrepreneur_name="Андрей Волков",
            business_name="ТрансМеталл",
            role="cfo",
            tags=["металлургия", "ВЭД"],
            onboarding_step="completed",
            onboarding_completed=True,
        )
        session.add(profile)
        await session.flush()
        session.add_all(
            [
                BusinessCategory(profile_id=profile.id, category_id=4, weight=1.0),
                BusinessCategory(profile_id=profile.id, category_id=15, weight=1.0),
                BusinessCategory(profile_id=profile.id, category_id=1, weight=0.6),
            ]
        )
        risk = _event(
            "Повышены экспортные пошлины на металлопрокат",
            "Ставка пошлины составит 7%.",
            impact="risk",
            importance=80,
            category_ids=[4, 15],
        )
        weak = _event(
            "Форум цифровой индустрии",
            "Отраслевое мероприятие без последствий.",
            impact="neutral",
            importance=10,
            category_ids=[99],
        )
        opportunity = _event(
            "РЖД снижает тариф на перевозку металлов",
            "Скидка 12% с декабря.",
            impact="opportunity",
            importance=60,
            category_ids=[20],
        )
        stale = _event(
            "ФАС предложила ограничить цены на арматуру",
            "Инициатива обсуждается.",
            impact="risk",
            importance=70,
            category_ids=[15],
            days_ago=5,
        )
        session.add_all([risk, weak, opportunity, stale])
        await session.commit()
        ids = {
            "user": user.id,
            "profile": profile.id,
            "risk": risk.id,
            "weak": weak.id,
            "opportunity": opportunity.id,
            "stale": stale.id,
        }

    async def _session_override():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _session_override
    token = create_access_token(str(ids["user"]))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, ids, {"Authorization": f"Bearer {token}"}, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


async def test_mockup_api_flow(api_env) -> None:
    client, ids, headers, session_factory = api_env

    feed = await client.get("/api/feed", headers=headers)
    assert feed.status_code == 200
    items = {item["title"]: item for item in feed.json()["items"]}
    risk = items["Повышены экспортные пошлины на металлопрокат"]
    assert risk["sources"][1]["name"] == "Деловой вестник"
    assert risk["facts"][0]["status"] == "Официально"
    assert len(risk["score_breakdown"]) == 4
    assert risk["score_breakdown"][0]["max"] == 5

    weak = await client.get("/api/feed/hidden?tab=weak", headers=headers)
    assert weak.status_code == 200
    assert any(item["id"] == str(ids["weak"]) for item in weak.json()["items"])
    stale = await client.get("/api/feed/hidden?tab=stale", headers=headers)
    assert any(item["id"] == str(ids["stale"]) for item in stale.json()["items"])

    skip = await client.post(
        f"/api/feed/{ids['opportunity']}/feedback",
        headers=headers,
        json={"action": "skip", "reason": "Уже знаю"},
    )
    assert skip.status_code == 200
    skipped = await client.get("/api/feed/hidden?tab=skipped", headers=headers)
    assert skipped.json()["items"][0]["reason"] == "Уже знаю"
    restore = await client.post(f"/api/feed/{ids['opportunity']}/restore", headers=headers)
    assert restore.status_code == 200
    skipped = await client.get("/api/feed/hidden?tab=skipped", headers=headers)
    assert skipped.json()["total"] == 0

    liked = await client.post(f"/api/feed/{ids['risk']}/like", headers=headers)
    assert liked.json() == {"liked": True, "likes": 1}
    unliked = await client.post(f"/api/feed/{ids['risk']}/like", headers=headers)
    assert unliked.json() == {"liked": False, "likes": 0}

    detail = await client.get(f"/api/feed/{ids['risk']}", headers=headers)
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["scenarios"]["scenarios"][1]["effect"] != 0
    assert payload["theses"]
    assert payload["alfa"] is None
    assert payload["actions"]
    assert payload["agent_log"]
    assert payload["impact_tiles"] == []
    async with session_factory() as session:
        stored = await session.scalar(
            select(EventAnalysis).where(EventAnalysis.event_id == ids["risk"])
        )
        assert stored is not None and stored.report
    scenarios = await client.get(f"/api/feed/{ids['risk']}/scenarios?horizon=3m", headers=headers)
    assert scenarios.status_code == 200
    assert scenarios.json()["horizon"] == "3m"

    sources = await client.get("/api/sources", headers=headers)
    assert sources.status_code == 200
    assert len(sources.json()["channels"]) == 15
    assert sources.json()["alfa_analytics"] is True
    assert "official" not in sources.json()
    catalog = await client.get("/api/sources/catalog", headers=headers, params={"q": "металл"})
    assert catalog.json()["total"] >= 2
    custom = await client.post(
        "/api/sources/channels", headers=headers, json={"query": "@my_channel"}
    )
    custom_channel = next(
        item for item in custom.json()["channels"] if item["handle"] == "@my_channel"
    )
    assert custom_channel["kind"] == "custom"
    custom_catalog = await client.get(
        "/api/sources/catalog", headers=headers, params={"q": "my_channel"}
    )
    assert any(item["id"] == custom_channel["id"] for item in custom_catalog.json()["items"])
    unsubscribed = await client.delete(
        f"/api/sources/channels/{custom_channel['id']}", headers=headers
    )
    assert all(item["id"] != custom_channel["id"] for item in unsubscribed.json()["channels"])
    restored = await client.post("/api/sources/channels/restore", headers=headers)
    assert len(restored.json()["channels"]) == 15
    assert restored.json()["custom_count"] == 0

    search = await client.get("/api/search", headers=headers, params={"q": "пошлин"})
    assert search.status_code == 200
    assert search.json()["total_news"] >= 1
    history = await client.get("/api/search/history", headers=headers)
    assert history.json()["items"][0]["query"] == "пошлин"
    cleared = await client.delete("/api/search/history", headers=headers)
    assert cleared.json()["items"] == []

    tracked = await client.post(f"/api/feed/{ids['risk']}/track", headers=headers)
    assert tracked.status_code == 200
    tracked_id = tracked.json()["id"]
    listing = await client.get("/api/tracked", headers=headers)
    assert listing.json()["total"] == 1
    tracked_detail = await client.get(f"/api/tracked/{tracked_id}", headers=headers)
    assert tracked_detail.json()["insight"]["scenarios"]["scenarios"]
    assert tracked_detail.json()["insight"]["actions"]
    assert tracked_detail.json()["insight"]["agent_log"]
    assert tracked_detail.json()["events"][0]["title"].startswith("Повышены")

    tracked_event = await client.get(f"/api/feed/{ids['risk']}", headers=headers)
    assert tracked_event.json()["actions"]
    assert tracked_event.json()["agent_log"]

    question = await client.post(
        f"/api/tracked/{tracked_id}/questions",
        headers=headers,
        json={"question": "Касается ли пошлина ЕАЭС?"},
    )
    assert question.status_code == 200
    assert any(item["text"] == "Касается ли пошлина ЕАЭС?" for item in question.json()["questions"])

    streamed = await client.post(
        f"/api/feed/{ids['risk']}/questions/stream",
        headers=headers,
        json={"question": "Что изменилось по пошлине?"},
    )
    assert streamed.status_code == 200
    assert streamed.headers["content-type"].startswith("text/event-stream")
    assert '"done": true' in streamed.text
    with_question = await client.get(f"/api/feed/{ids['risk']}", headers=headers)
    asked = with_question.json()["open_questions"]
    assert any(item["text"] == "Что изменилось по пошлине?" for item in asked)

    archived = await client.post(f"/api/tracked/{tracked_id}/archive", headers=headers)
    assert archived.json()["status"] == "archived"
    archived_list = await client.get("/api/tracked?status=archived", headers=headers)
    assert archived_list.json()["total"] == 1
    resumed = await client.post(f"/api/tracked/{tracked_id}/resume", headers=headers)
    assert resumed.json()["status"] == "active"

    outlook = await client.get(
        "/api/outlook", headers=headers, params={"event_id": str(ids["risk"])}
    )
    assert outlook.status_code == 200
    assert outlook.json()["connected"] is False

    connected = await client.post(
        "/api/outlook/connect", headers=headers, json={"email": "owner@company.example"}
    )
    assert connected.status_code == 200
    assert connected.json()["connected"] is True
    contacts = await client.get("/api/outlook/contacts", headers=headers)
    assert any(item["email"] == "cfo@company.example" for item in contacts.json()["items"])

    created = await client.post(
        "/api/outlook/messages",
        headers=headers,
        json={
            "event_id": str(ids["risk"]),
            "action_id": "action-1",
            "to": [{"name": "Финансовый директор", "email": "cfo@company.example"}],
            "subject": "Поручение по пошлине",
            "body": "Проверьте контракты и сроки.",
        },
    )
    assert created.status_code == 200
    draft_id = created.json()["id"]
    assert created.json()["status"] == "draft"

    sent = await client.post(f"/api/outlook/messages/{draft_id}/send", headers=headers)
    assert sent.json()["status"] == "sent"
    advanced = await client.post(f"/api/outlook/messages/{draft_id}/advance", headers=headers)
    assert advanced.json()["status"] == "delivered"
    reminded = await client.post(f"/api/outlook/messages/{draft_id}/remind", headers=headers)
    assert reminded.json()["reminder_count"] == 1

    event_messages = await client.get(
        "/api/outlook", headers=headers, params={"event_id": str(ids["risk"])}
    )
    assert event_messages.json()["messages"][0]["subject"] == "Поручение по пошлине"

    disconnected = await client.post("/api/outlook/disconnect", headers=headers)
    assert disconnected.json()["connected"] is False

    reporting = await client.post(
        "/api/onboarding/reporting",
        headers=headers,
        files={"income": ("income.txt", "Отчёт за 2025\nВыручка 1 000 000 000", "text/plain")},
    )
    assert reporting.status_code == 200
    reporting_summary = reporting.json()["summary"]
    assert "## Отчёт о финансовых результатах" in reporting_summary["markdown"]
    assert "| Показатель | Значение |" in reporting_summary["markdown"]
    assert "| Выручка | 1 млрд ₽ |" in reporting_summary["markdown"]

    profile = await client.get("/api/profile", headers=headers)
    assert profile.status_code == 200
    bundle = profile.json()
    assert bundle["stats"]["revenue_label"] == "52 млрд ₽"
    assert {group["key"] for group in bundle["category_groups"]} == {
        "direct",
        "indirect",
        "background",
        "none",
    }
    assert "## Отчёт о финансовых результатах" in bundle["reporting"]["markdown"]
    assert bundle["notifications"]
    notifications = await client.patch(
        "/api/profile/notifications", headers=headers, json={"key_rate": False}
    )
    assert notifications.status_code == 200
    assert (
        next(item for item in notifications.json() if item["key"] == "key_rate")["enabled"] is False
    )


async def test_ingest_pipeline_api(api_env) -> None:
    client, ids, headers, session_factory = api_env
    profile_id = str(ids["profile"])
    text = "Минфин повысил экспортную пошлину на металлопрокат до 7 процентов."

    first = await client.post(
        "/api/ingest/posts",
        json={
            "title": "Повышены экспортные пошлины на металлопрокат",
            "text": text,
            "source": "Минфин",
            "profile_id": profile_id,
        },
    )
    assert first.status_code == 200
    payload = first.json()
    assert payload["status"] == "feed"
    assert payload["news_event_id"] is not None
    assert payload["importance"] >= 30
    assert [step["stage"] for step in payload["decision_trace"]][:3] == [
        "parse",
        "classify",
        "cluster",
    ]

    duplicate = await client.post(
        "/api/ingest/posts",
        json={"text": text, "source": "Деловой вестник", "profile_id": profile_id},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "source_cluster"
    assert duplicate.json()["cluster_key"] == payload["cluster_key"]
    assert duplicate.json()["similarity"] >= 0.85

    tracked = await client.post(
        "/api/ingest/posts",
        json={
            "text": (
                "Продолжение истории: во вторник регулятор уточнил порядок "
                "подачи апелляций по ограничительным мерам."
            ),
            "profile_id": profile_id,
        },
    )
    assert tracked.status_code == 200
    assert tracked.json()["status"] == "tracked"
    assert tracked.json()["tracked_item_id"] is not None

    feed = await client.get("/api/feed", headers=headers)
    assert any(item["id"] == payload["news_event_id"] for item in feed.json()["items"])

    weak = await client.post(
        "/api/ingest/posts",
        json={
            "text": "Курс рубля изменился незначительно по итогам торгов.",
            "source": "Биржа",
            "profile_id": profile_id,
        },
    )
    assert weak.status_code == 200
    assert weak.json()["status"] == "ignored"

    trace = await client.get(f"/api/ingest/posts/{payload['id']}")
    assert trace.status_code == 200
    assert trace.json()["embedding"]
