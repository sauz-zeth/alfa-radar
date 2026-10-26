"""Add demo tracked themes, event chains and questions for demo users.

Usage (from back/):
    uv run python scripts/seed_demo_tracked.py
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

import asyncpg

from back.config import get_settings

try:
    from scripts.demo_events import seeded_events
    from scripts.seed import seed_news
except ImportError:  # running as `python scripts/seed_demo_tracked.py`
    from demo_events import seeded_events  # type: ignore[no-redef]
    from seed import seed_news  # type: ignore[no-redef]


def _track_id(profile_id: uuid.UUID, event_id: uuid.UUID) -> uuid.UUID:
    return uuid5(NAMESPACE_URL, f"alfa-demo-track-{profile_id}-{event_id}")


async def seed_tracked(conn: asyncpg.Connection, profile_id: uuid.UUID, login: str) -> None:
    events = {event["slug"]: event for event in seeded_events()}
    by_chain: dict[str, list[dict]] = {}
    for event in events.values():
        chain = event.get("chain_key")
        if chain:
            by_chain.setdefault(chain, []).append(event)
    for chain_events in by_chain.values():
        chain_events.sort(key=lambda item: item["published_at"])

    common = [
        {
            "slug": "metal-export-duty",
            "title": "Экспортная пошлина на металлопрокат",
            "chain": "metals-duty",
            "status": "active",
            "changed": True,
            "what_changed": (
                "Минфин опубликовал постановление: 7% с 1 ноября, без исключений "
                "для подписанных контрактов."
            ),
        },
        {
            "slug": "rzd-tariffs",
            "title": "Тарифы РЖД на восточном направлении",
            "chain": "rzd-tariffs",
            "status": "active",
            "changed": True,
            "what_changed": "ФАС согласовала индексацию 10% с декабря.",
        },
        {
            "slug": "cb-rate-14",
            "title": "Ключевая ставка ЦБ",
            "chain": "cb-rate",
            "status": "active",
            "changed": False,
            "what_changed": None,
        },
        {
            "slug": "fsbu-lease",
            "title": "Новый ФСБУ по аренде",
            "chain": None,
            "status": "archived",
            "changed": False,
            "what_changed": None,
        },
        {
            "slug": "ai-law",
            "title": "Регулирование ИИ в промышленности",
            "chain": None,
            "status": "archived",
            "changed": False,
            "what_changed": None,
        },
    ]
    profile_themes = {
        "demo1": [
            {"slug": "marketplace-returns", "title": "Возвраты на маркетплейсах и маржа ДомТрейд", "chain": "retail-returns", "status": "active", "changed": True, "what_changed": "После публикации требований площадки увеличили срок возврата; пересмотрите резерв и условия поставок."},
            {"slug": "rub-usd", "title": "Курс валют и закупки импортного товара", "chain": None, "status": "active", "changed": False, "what_changed": None},
        ],
        "demo2": [
            {"slug": "ai-law", "title": "Требования к ИИ-функциям и журналированию", "chain": "software-ai", "status": "active", "changed": True, "what_changed": "Обсуждение перешло к обязательному журналированию: оцените хранение запросов и аудит моделей."},
            {"slug": "sanctions-package", "title": "Доступность зарубежного ПО и оборудования", "chain": None, "status": "active", "changed": False, "what_changed": None},
        ],
        "demo3": [
            {"slug": "construction-mortgage", "title": "Лимиты ипотеки и продажи СтройГрад", "chain": "construction-demand", "status": "active", "changed": True, "what_changed": "Снижение лимитов удлиняет цикл сделки и повышает стоимость проектного финансирования."},
            {"slug": "rzd-tariffs", "title": "Индексация тарифов и стоимость стройматериалов", "chain": "rzd-tariffs", "status": "active", "changed": True, "what_changed": "ФАС согласовала индексацию грузовых тарифов, что повышает логистическую себестоимость."},
        ],
    }
    defs = common if login == "demo_full" else profile_themes.get(login, [])

    for item in defs:
        event = events[item["slug"]]
        chain_events = by_chain.get(item["chain"] or "", [event])
        event_ids = [str(entry["id"]) for entry in chain_events]
        await conn.execute(
            """
            INSERT INTO tracked_items (
                id, profile_id, event_id, status, title, event_ids, what_changed,
                conclusions_changed, questions, report
            )
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, '[]'::jsonb, '{}'::jsonb)
            ON CONFLICT (profile_id, event_id) DO UPDATE SET
                status = EXCLUDED.status,
                title = EXCLUDED.title,
                event_ids = EXCLUDED.event_ids,
                what_changed = EXCLUDED.what_changed,
                conclusions_changed = EXCLUDED.conclusions_changed
            """,
            _track_id(profile_id, event["id"]),
            profile_id,
            event["id"],
            item["status"],
            item["title"],
            json.dumps(event_ids),
            item["what_changed"],
            item["changed"],
        )


async def seed_questions(conn: asyncpg.Connection, profile_id: uuid.UUID) -> None:
    event = next(item for item in seeded_events() if item["slug"] == "metal-duty-update")
    today = datetime.now(UTC).strftime("%d.%m")
    rows = [
        (
            "confirm-contracts",
            "Распространяется ли пошлина на уже подписанные контракты?",
            "confirmed",
            "Да — на все отгрузки после 1 ноября, включая заключённые договоры.",
            "Минфин России",
            today,
        ),
        (
            "eaeu-exceptions",
            "Будут ли исключения для ЕАЭС",
            "waiting",
            None,
            None,
            None,
        ),
        (
            "term-2027",
            "Срок действия: до конца 2027 года или бессрочно",
            "waiting",
            None,
            None,
            None,
        ),
    ]
    await conn.executemany(
        """
        INSERT INTO event_questions (
            id, profile_id, event_id, text, status, answer, source, date
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (id) DO NOTHING
        """,
        [
            (
                uuid5(NAMESPACE_URL, f"alfa-demo-question-{slug}"),
                profile_id,
                event["id"],
                text,
                status,
                answer,
                source,
                date,
            )
            for slug, text, status, answer, source, date in rows
        ],
    )
    await conn.execute("DELETE FROM event_questions WHERE text = 'Проверка вопроса из UI'")


async def main() -> None:
    settings = get_settings()
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        await seed_news(conn)
        for login in (settings.demo_full_login, "demo1", "demo2", "demo3"):
            profile_id = await conn.fetchval(
                """
                SELECT bp.id FROM business_profiles bp
                JOIN users u ON u.id = bp.user_id
                WHERE u.login = $1
                """,
                login,
            )
            if profile_id is None:
                if login == settings.demo_full_login:
                    raise SystemExit(f"{login}: profile not found, run seed.py first")
                print(f"{login}: profile not found, skipping")
                continue
            await seed_tracked(conn, profile_id, login)
            if login == settings.demo_full_login:
                await seed_questions(conn, profile_id)
            print(f"{login}: demo tracked themes seeded")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
