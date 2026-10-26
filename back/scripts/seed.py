"""Seed the local database from the hackathon CSV files.

Usage (from back/):
    uv run python scripts/seed.py --reset
    uv run python scripts/seed.py --reset --limit 2000 --skip-payments
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import asyncpg

from back.config import get_settings
from back.core.categories import CATEGORIES
from back.core.company import company_tags, revenue_segment
from back.core.constants import DEFAULT_ENTREPRENEUR_NAME
from back.core.security import hash_password
from back.core.sources import CHANNELS, RECOMMENDED_IDS
from back.services.categories import heuristic_category_weights

try:
    from scripts.demo_events import seeded_events
except ImportError:  # running as `python scripts/seed.py`
    from demo_events import seeded_events  # type: ignore[no-redef]

RESET_SQL = """
TRUNCATE TABLE
    profile_channels,
    channels,
    event_likes,
    tracked_items,
    feedback,
    reporting_uploads,
    business_categories,
    counterparties,
    business_profiles,
    users,
    person_company_links,
    payments,
    news_events,
    categories,
    companies
RESTART IDENTITY CASCADE
"""

COMPANY_COLUMNS = [
    "uid",
    "org_type",
    "okfs_name",
    "company_age_years_gradation",
    "eco_mark_label",
    "main_okved_code",
    "main_okved_name",
    "negative_mark",
    "amount_workers_fns_gradation",
    "amount_workers_spark_gradation",
    "client_type",
    "cl_product_rko_mark",
    "cl_product_gar_mark",
    "cl_product_loa_mark",
    "cl_product_lea_mark",
    "cl_product_dep_mark",
    "cl_product_zpp_mark",
    "fts_flag",
    "fts_country_name",
    "factoring_mark",
    "revenue",
    "group_id",
    "city",
    "region",
    "revenue_segment",
    "tags",
]


def resolve_data_dir(value: str | None) -> Path:
    candidates: list[Path] = []
    if value:
        candidates.append(Path(value))
    else:
        candidates.extend(
            [
                get_settings().data_dir,
                Path("/tmp/alfadata/Данные для участников"),
                Path("/tmp/alfadata"),
            ]
        )
    for candidate in candidates:
        if (candidate / "df_Uid_data_hack.csv").exists():
            return candidate
        nested = candidate / "Данные для участников"
        if (nested / "df_Uid_data_hack.csv").exists():
            return nested
    raise SystemExit(
        "Не найден df_Uid_data_hack.csv. Укажите --data-dir или распакуйте архив в /tmp/alfadata."
    )


def as_bool(value: str | None) -> bool:
    if not value:
        return False
    try:
        return float(value.replace(",", ".")) > 0
    except ValueError:
        return value.strip().lower() in {"true", "1", "y", "yes", "да"}


def as_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def company_record(row: dict[str, str]) -> tuple[Any, ...]:
    raw: dict[str, Any] = {
        "uid": row.get("SYNTHETIC_U", "").strip(),
        "org_type": row.get("ORG_TYPE") or None,
        "okfs_name": row.get("OKFS_NAME") or None,
        "company_age_years_gradation": row.get("COMPANY_AGE_YEARS_GRADATION") or None,
        "eco_mark_label": row.get("ECO_MARK_LABEL") or None,
        "main_okved_code": row.get("MAINOKVED_CODE") or None,
        "main_okved_name": row.get("MAINOKVED_NAME") or None,
        "negative_mark": as_float(row.get("NEGATIVEMARK")),
        "amount_workers_fns_gradation": row.get("AMOUNT_WORKERS_FNS_GRADATION") or None,
        "amount_workers_spark_gradation": row.get("AMOUNT_WORKERS_SPARK_GRADATION") or None,
        "client_type": row.get("CL_TYPE") or None,
        "cl_product_rko_mark": as_bool(row.get("CL_PRODUCT_RKO_MARK")),
        "cl_product_gar_mark": as_bool(row.get("CL_PRODUCT_GAR_MARK")),
        "cl_product_loa_mark": as_bool(row.get("CL_PRODUCT_LOA_MARK")),
        "cl_product_lea_mark": as_bool(row.get("CL_PRODUCT_LEA_MARK")),
        "cl_product_dep_mark": as_bool(row.get("CL_PRODUCT_DEP_MARK")),
        "cl_product_zpp_mark": as_bool(row.get("CL_PRODUCT_ZPP_MARK")),
        "fts_flag": as_bool(row.get("FTS_FLAG")),
        "fts_country_name": row.get("FTS_COUNTRY_NAME") or None,
        "factoring_mark": as_bool(row.get("FACTORING_MARK")),
        "revenue": as_float(row.get("REVENUE_COMPANY")),
        "group_id": row.get("GROUP_ID") or None,
        "city": row.get("CITY") or None,
        "region": row.get("REGION") or None,
    }
    raw["revenue_segment"] = revenue_segment(raw["revenue"])
    raw["tags"] = company_tags(raw)
    return tuple(
        json.dumps(raw[column], ensure_ascii=False) if column == "tags" else raw[column]
        for column in COMPANY_COLUMNS
    )


async def seed_categories(conn: asyncpg.Connection) -> None:
    records = [
        (
            item.id,
            item.slug,
            item.name,
            item.short_name,
            item.group,
            item.description,
            item.example,
            json.dumps(list(item.channels), ensure_ascii=False),
        )
        for item in CATEGORIES
    ]
    await conn.executemany(
        """
        INSERT INTO categories (id, slug, name, short_name, "group", description, example, channels)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
        ON CONFLICT (id) DO UPDATE SET
            slug = EXCLUDED.slug,
            name = EXCLUDED.name,
            short_name = EXCLUDED.short_name,
            "group" = EXCLUDED."group",
            description = EXCLUDED.description,
            example = EXCLUDED.example,
            channels = EXCLUDED.channels
        """,
        records,
    )
    print(f"categories: {len(records)}")


async def seed_channels(conn: asyncpg.Connection) -> None:
    records = [
        (
            item.id,
            item.name,
            item.handle,
            item.topics,
            "catalog",
            item.id in RECOMMENDED_IDS,
            True,
            json.dumps({}),
        )
        for item in CHANNELS
    ]
    await conn.executemany(
        """
        INSERT INTO channels (
            id, name, handle, topics, kind, is_recommended, is_active, meta
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            handle = EXCLUDED.handle,
            topics = EXCLUDED.topics,
            kind = EXCLUDED.kind,
            is_recommended = EXCLUDED.is_recommended,
            is_active = EXCLUDED.is_active
        """,
        records,
    )
    print(f"channels: {len(records)}")


async def seed_companies(conn: asyncpg.Connection, data_dir: Path, limit: int) -> None:
    count = await conn.fetchval("SELECT count(*) FROM companies")
    if count:
        print(f"companies: already {count}, skipping")
        return

    path = data_dir / "df_Uid_data_hack.csv"
    records: list[tuple[Any, ...]] = []
    batch: list[tuple[Any, ...]] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for index, row in enumerate(reader, start=1):
            if limit and index > limit:
                break
            uid = (row.get("SYNTHETIC_U") or "").strip()
            if not uid or uid in seen:
                continue
            seen.add(uid)
            batch.append(company_record(row))
            if len(batch) >= 20_000:
                await conn.copy_records_to_table(
                    "companies", records=batch, columns=COMPANY_COLUMNS
                )
                records.extend(batch)
                batch = []
    if batch:
        await conn.copy_records_to_table("companies", records=batch, columns=COMPANY_COLUMNS)
        records.extend(batch)
    print(f"companies: {len(records)}")


async def seed_payments(conn: asyncpg.Connection, data_dir: Path) -> None:
    count = await conn.fetchval("SELECT count(*) FROM payments")
    if count:
        print(f"payments: already {count}, skipping")
        return
    path = data_dir / "df_Uid_payment_hack.csv"
    batch: list[tuple[str, str, float, int]] = []
    total = 0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            amount = as_float(row.get("PAY_AMT"))
            if not row.get("PAYER") or not row.get("BENEFICIARY") or amount is None:
                continue
            batch.append(
                (
                    row["PAYER"].strip(),
                    row["BENEFICIARY"].strip(),
                    amount,
                    int(as_float(row.get("PAY_CNT")) or 0),
                )
            )
            if len(batch) >= 50_000:
                await conn.copy_records_to_table(
                    "payments",
                    records=batch,
                    columns=["payer", "beneficiary", "amount", "count"],
                )
                total += len(batch)
                batch = []
                print(f"payments: {total}...", end="\r")
    if batch:
        await conn.copy_records_to_table(
            "payments",
            records=batch,
            columns=["payer", "beneficiary", "amount", "count"],
        )
        total += len(batch)
    print(f"payments: {total}          ")


async def seed_person_links(conn: asyncpg.Connection, data_dir: Path) -> None:
    count = await conn.fetchval("SELECT count(*) FROM person_company_links")
    if count:
        print(f"person_company_links: already {count}, skipping")
        return
    path = data_dir / "df_Fid_Uid_link_hack.csv"
    records: list[tuple[str, str, str | None, str | None]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            person = (row.get("SYNTHETIC_F") or "").strip()
            company = (row.get("SYNTHETIC_U") or "").strip()
            if not person or not company:
                continue
            records.append(
                (
                    person,
                    company,
                    row.get("CITY_NAME") or None,
                    row.get("RC_NAME") or None,
                )
            )
    await conn.executemany(
        """
        INSERT INTO person_company_links (synthetic_f, synthetic_u, city_name, rc_name)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (synthetic_f, synthetic_u) DO NOTHING
        """,
        records,
    )
    print(f"person_company_links: {len(records)}")


async def seed_news(conn: asyncpg.Connection) -> None:
    events = seeded_events()
    records = [
        (
            event["id"],
            event["title"],
            event["summary"],
            event["what_it_means"],
            event["source_name"],
            event["source_url"],
            event["published_at"],
            event["importance"],
            event["impact"],
            json.dumps(event["category_ids"]),
            json.dumps(event["mentioned_company_uids"]),
            json.dumps(event["facts"], ensure_ascii=False),
            json.dumps(event["source_posts"], ensure_ascii=False),
            json.dumps(event["impact_metrics"], ensure_ascii=False),
            event["chain_key"],
            event["update_label"],
            True,
        )
        for event in events
    ]
    await conn.executemany(
        """
        INSERT INTO news_events (
            id, title, summary, what_it_means, source_name, source_url, published_at,
            importance, impact, category_ids, mentioned_company_uids, facts,
            source_posts, impact_metrics, chain_key, update_label, is_active
        )
        VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb, $12::jsonb,
            $13::jsonb, $14::jsonb, $15, $16, $17
        )
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            summary = EXCLUDED.summary,
            what_it_means = EXCLUDED.what_it_means,
            source_name = EXCLUDED.source_name,
            source_url = EXCLUDED.source_url,
            published_at = EXCLUDED.published_at,
            importance = EXCLUDED.importance,
            impact = EXCLUDED.impact,
            category_ids = EXCLUDED.category_ids,
            facts = EXCLUDED.facts,
            source_posts = EXCLUDED.source_posts,
            impact_metrics = EXCLUDED.impact_metrics,
            chain_key = EXCLUDED.chain_key,
            update_label = EXCLUDED.update_label,
            is_active = EXCLUDED.is_active
        """,
        records,
    )
    print(f"news: {len(records)}")


async def ensure_user(conn: asyncpg.Connection, login: str, password: str) -> uuid.UUID:
    row = await conn.fetchrow("SELECT id FROM users WHERE login = $1", login)
    if row:
        return row["id"]
    user_id = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO users (id, login, password_hash, is_active)
        VALUES ($1, $2, $3, true)
        """,
        user_id,
        login,
        hash_password(password),
    )
    return user_id


async def create_demo_profile(conn: asyncpg.Connection, user_id: uuid.UUID, login: str) -> None:
    existing = await conn.fetchval("SELECT id FROM business_profiles WHERE user_id = $1", user_id)
    if existing:
        return
    row = await conn.fetchrow(
        """
        SELECT * FROM companies
        WHERE revenue IS NOT NULL
        ORDER BY (revenue >= 15000000000) DESC, revenue DESC
        LIMIT 1
        """
    )
    if row is None:
        await conn.execute(
            """
            INSERT INTO business_profiles (
                id, user_id, entrepreneur_name, business_name, role,
                tags, reporting_summary, onboarding_step, onboarding_completed
            )
            VALUES ($1, $2, $3, $4, 'cfo', '[]'::jsonb, '{}'::jsonb, 'completed', true)
            """,
            uuid.uuid4(),
            user_id,
            DEFAULT_ENTREPRENEUR_NAME,
            "Демо Бизнес",
        )
        print(f"{login}: profile created without company")
        return
    company = dict(row)
    company["tags"] = (
        json.loads(company["tags"]) if isinstance(company["tags"], str) else company["tags"]
    )
    profile_id = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO business_profiles (
            id, user_id, company_uid, entrepreneur_name, business_name, role,
            tags, reporting_summary, onboarding_step, onboarding_completed
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, '{}'::jsonb, 'completed', true)
        """,
        profile_id,
        user_id,
        company["uid"],
        DEFAULT_ENTREPRENEUR_NAME,
        f"Бизнес {company['uid']}",
        "cfo",
        json.dumps(company["tags"], ensure_ascii=False),
    )
    ns = SimpleNamespace(**company)
    for item in heuristic_category_weights(ns):  # type: ignore[arg-type]
        await conn.execute(
            """
            INSERT INTO business_categories (
                id, profile_id, category_id, weight, rationale, is_manual
            )
            VALUES ($1, $2, $3, $4, $5, false)
            ON CONFLICT (profile_id, category_id) DO NOTHING
            """,
            uuid.uuid4(),
            profile_id,
            item["category_id"],
            item["weight"],
            item["rationale"],
        )
    print(f"{login}: profile created for {company['uid']}")


DEMO_SKIP_SLUGS = (
    "fsbu-lease",
    "ai-law",
    "tax-deadlines",
    "construction-mortgage",
    "marketplace-returns",
)


async def seed_demo_feedback(conn: asyncpg.Connection, user_id: uuid.UUID) -> None:
    profile_id = await conn.fetchval("SELECT id FROM business_profiles WHERE user_id = $1", user_id)
    if profile_id is None:
        return
    event_ids = {event["slug"]: event["id"] for event in seeded_events()}
    records = [
        (uuid.uuid4(), profile_id, event_ids[slug], "skip", "Демо: скрыто для проверки")
        for slug in DEMO_SKIP_SLUGS
        if slug in event_ids
    ]
    await conn.executemany(
        """
        INSERT INTO feedback (id, profile_id, event_id, action, reason)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (profile_id, event_id) DO NOTHING
        """,
        records,
    )
    print(f"{profile_id}: demo feedback skipped {len(records)}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Alfa Future database")
    parser.add_argument("--data-dir", help="Directory with df_*_hack.csv files")
    parser.add_argument("--limit", type=int, default=0, help="Limit companies, 0 = all")
    parser.add_argument("--skip-payments", action="store_true")
    parser.add_argument("--reset", action="store_true", help="Truncate all tables first")
    args = parser.parse_args()

    settings = get_settings()
    data_dir = None
    try:
        data_dir = resolve_data_dir(args.data_dir)
    except SystemExit:
        if args.data_dir:
            raise
        print("seed: CSV dataset not found; seeding categories, sources, news and demo users only")
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        if args.reset:
            print("reset: truncating tables")
            await conn.execute(RESET_SQL)
        await seed_categories(conn)
        await seed_channels(conn)
        if data_dir:
            limit = args.limit or settings.seed_company_limit
            await seed_companies(conn, data_dir, limit)
            if not args.skip_payments and settings.seed_with_payments:
                await seed_payments(conn, data_dir)
            await seed_person_links(conn, data_dir)
        await seed_news(conn)

        demo_id = await ensure_user(conn, settings.demo_login, settings.demo_password)
        print(f"{settings.demo_login}: user ready ({demo_id})")
        full_id = await ensure_user(conn, settings.demo_full_login, settings.demo_full_password)
        await create_demo_profile(conn, full_id, settings.demo_full_login)
        await seed_demo_feedback(conn, full_id)
    finally:
        await conn.close()
    print("seed: done")


if __name__ == "__main__":
    asyncio.run(main())
