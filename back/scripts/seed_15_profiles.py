"""Create 15 demo users with complete business profiles on a clean database.

Usage (from back/):
    uv run python scripts/seed_15_profiles.py
    uv run python scripts/seed_15_profiles.py --password demo

The script is idempotent: it applies migrations if needed, seeds reference data,
creates 15 synthetic companies with payments, then creates users demo1..demo15
with categories and counterparties. Existing users/profiles are reused.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import asyncpg

from back.config import get_settings
from back.services.categories import heuristic_category_weights

try:
    from seed import ensure_user, seed_categories, seed_channels, seed_demo_counterparties
    from seed_demo_companies import COMPANY_COLUMNS, build_companies, build_payments
except ImportError:  # running as `python -m scripts.seed_15_profiles`
    from scripts.seed import ensure_user, seed_categories, seed_channels, seed_demo_counterparties
    from scripts.seed_demo_companies import COMPANY_COLUMNS, build_companies, build_payments

COUNT = 15
COMPANY_PREFIX = "DEMO15"

ENTREPRENEURS = (
    "Андрей Волков",
    "Мария Соколова",
    "Илья Кузнецов",
    "Ольга Панова",
    "Дмитрий Лебедев",
    "Анна Морозова",
    "Сергей Волков",
    "Екатерина Орлова",
    "Павел Никитин",
    "Наталья Крылова",
    "Артём Фомин",
    "Юлия Белова",
    "Максим Гусев",
    "Светлана Котова",
    "Роман Ефимов",
)

BUSINESSES = (
    "Уралпрокат",
    "Северная логистика",
    "СтройГрад",
    "Розница Плюс",
    "АгроНива",
    "Кодекс Софт",
    "МашТех",
    "ХимСинтез",
    "ФинансПартнёр",
    "ЭнергоСбыт",
    "НефтеПоток",
    "ЛесПром",
    "ФармЛайн",
    "ТурВектор",
    "МедиаПульс",
)

ROLES = ("owner", "ceo", "cfo", "chief_accountant", "treasurer", "c_level")


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_demo_companies(count: int = 60) -> list[dict]:
    rng = random.Random(15015)
    companies = build_companies(count, rng)
    for index, company in enumerate(companies, start=1):
        company["uid"] = f"{COMPANY_PREFIX}{index:03d}"
    return companies


async def _apply_migrations() -> None:
    back_dir = Path(__file__).resolve().parent.parent
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=back_dir,
        check=True,
    )


async def _seed_companies(conn: asyncpg.Connection, companies: list[dict]) -> list[str]:
    records = [
        tuple(
            _json(company[column]) if column == "tags" else company[column]
            for column in COMPANY_COLUMNS
        )
        for company in companies
    ]
    await conn.executemany(
        """
        INSERT INTO companies ({columns})
        VALUES ({placeholders})
        ON CONFLICT (uid) DO NOTHING
        """.format(
            columns=", ".join(COMPANY_COLUMNS),
            placeholders=", ".join(f"${i}" for i in range(1, len(COMPANY_COLUMNS) + 1)),
        ),
        records,
    )
    uids = [company["uid"] for company in companies]
    has_payments = await conn.fetchval(
        "SELECT 1 FROM payments WHERE payer = ANY($1) OR beneficiary = ANY($1) LIMIT 1",
        uids,
    )
    if not has_payments:
        await conn.executemany(
            "INSERT INTO payments (payer, beneficiary, amount, count) VALUES ($1, $2, $3, $4)",
            build_payments(companies, len(companies), random.Random(15015)),
        )
    return uids


async def _ensure_profile(
    conn: asyncpg.Connection,
    user_id: uuid.UUID,
    company: dict,
    index: int,
) -> tuple[uuid.UUID, bool]:
    existing = await conn.fetchval("SELECT id FROM business_profiles WHERE user_id = $1", user_id)
    created = existing is None
    profile_id = existing or uuid.uuid4()
    if created:
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
            ENTREPRENEURS[index],
            BUSINESSES[index],
            ROLES[index % len(ROLES)],
            _json(company["tags"]),
        )

    for item in heuristic_category_weights(SimpleNamespace(**company)):  # type: ignore[arg-type]
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
    await seed_demo_counterparties(conn, profile_id, company["uid"])
    return profile_id, created


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed 15 demo business profiles")
    parser.add_argument("--password", default="demo", help="Password for demo1..demo15")
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Assume the schema is already migrated",
    )
    args = parser.parse_args()

    if not args.skip_migrations:
        await _apply_migrations()

    settings = get_settings()
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        await seed_categories(conn)
        await seed_channels(conn)
        all_companies = build_demo_companies()
        await _seed_companies(conn, all_companies)
        companies = all_companies[:COUNT]

        print(f"\n{'login':<8} {'password':<10} {'company':<14} business")
        for index, company in enumerate(companies):
            login = f"demo{index + 1}"
            user_id = await ensure_user(conn, login, args.password)
            profile_id, created = await _ensure_profile(conn, user_id, company, index)
            state = "created" if created else "exists"
            print(
                f"{login:<8} {args.password:<10} {company['uid']:<14} "
                f"{BUSINESSES[index]} ({state}, {profile_id})"
            )
    finally:
        await conn.close()
    print("\nseed_15_profiles: done")


if __name__ == "__main__":
    asyncio.run(main())
