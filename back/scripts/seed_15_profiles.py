"""Create three demo users with complete business profiles.

Usage (from back/):
    uv run python scripts/seed_15_profiles.py
    uv run python scripts/seed_15_profiles.py --password demo

The script is idempotent: it applies migrations if needed, seeds reference data,
creates the 15 onboarding companies with payments, then creates users demo1..demo3
for three selected companies. Existing users/profiles are reused.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import csv
import json
import math
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
    from seed import (
        company_record,
        ensure_user,
        resolve_data_dir,
        seed_categories,
        seed_channels,
        seed_companies,
        seed_payments,
        seed_person_links,
    )
    from seed_demo_companies import COMPANY_COLUMNS, build_companies, build_payments
except ImportError:  # running as `python -m scripts.seed_15_profiles`
    from scripts.seed import (
        company_record,
        ensure_user,
        resolve_data_dir,
        seed_categories,
        seed_channels,
        seed_companies,
        seed_payments,
        seed_person_links,
    )
    from scripts.seed_demo_companies import COMPANY_COLUMNS, build_companies, build_payments

COUNT = 15
COMPANY_PREFIX = "DEMO15"
DEMO_UIDS = ("U_71020", "U_8501", "U_137980")

REFERENCE_UIDS = (
    "U_71020",
    "U_42698",
    "U_8501",
    "U_88590",
    "U_74980",
    "U_109161",
    "U_83337",
    "U_132290",
    "U_30566",
    "U_2644",
    "U_174285",
    "U_223799",
    "U_92383",
    "U_218649",
    "U_137980",
)

ENTREPRENEURS = (
    "Алексей Волков",
    "Мария Соколова",
    "Илья Кузнецов",
)

BUSINESSES = (
    "ДомТрейд",
    "Кодекс Софт",
    "СтройГрад",
)

DEMO_COUNTERPARTY_NAMES = {
    "U_71020": (
        "ПосудаОпт",
        "ТехноДом",
        "Текстиль Импорт",
        "ИнструментПро",
        "Турция Текстиль",
        "Иу-Трейд",
        "ХозТовары Юг",
        "ЭлектроБыт",
    ),
    "U_8501": (
        "ОблакоТех",
        "ДатаЦентр Север",
        "СофтЛицензии",
        "СерверКомплект",
        "ИТ-Аутсорс",
        "Кадры Плюс",
        "Офис Бизнес-Центр",
        "Телеком Линк",
    ),
    "U_137980": (
        "Бетон Юг",
        "АрматураСнаб",
        "Стеновые Материалы",
        "Субподряд Монтаж",
        "СпецТехАренда",
        "Альфа-Лизинг",
        "КровляПро",
        "ЭлектроМонтаж Юг",
    ),
}
DEMO_BUYER_NAMES = {
    "U_71020": (
        "DIY Гипермаркет",
        "Маркетплейс Дом",
        "Сеть Уют",
        "HoReCa Групп",
        "Дистрибьютор Москва",
        "Алматы Опт",
        "Минск Хозторг",
        "Регион Сеть",
    ),
    "U_8501": (
        "Частный Банк",
        "Федеральная Розница",
        "ФинТех Платёж",
        "Логистический Оператор",
        "Транспорт Гос",
        "Аптечная Сеть",
        "Региональный Банк",
        "Отраслевой Маркетплейс",
    ),
    "U_137980": (
        "Девелопер ЖК Объект 1",
        "Девелопер ЖК Объект 2",
        "Складской Комплекс А",
        "Генподрядчик Школа",
        "УК Торговый Центр",
        "Муниципальный Заказ",
        "Коммерческий Заказчик",
        "Благоустройство Юг",
    ),
}

REPORTING_SUMMARIES = {
    "U_71020": """## Итоги за 2025 год

Выручка — **666 047 тыс. ₽** (+14,6% к 581 230 тыс. ₽ в 2024 году),
чистая прибыль — **30 353 тыс. ₽**.

### Отчёт о финансовых результатах

| Показатель | 2025 г., тыс. ₽ |
|---|---:|
| Выручка | 666 047 |
| Себестоимость продаж | −446 252 |
| Валовая прибыль | 219 795 |
| Коммерческие расходы | −117 770 |
| Управленческие расходы | −39 479 |
| Прибыль от продаж | 62 546 |
| Проценты к уплате | −26 004 |
| Прочие доходы | 14 375 |
| Прочие расходы | −10 730 |
| Чистая прибыль | 30 353 |

### Бухгалтерский баланс на 31.12.2025

Валюта баланса — **337 874 тыс. ₽**: внеоборотные активы 28 942 тыс. ₽,
оборотные 308 932 тыс. ₽. В оборотных активах запасы 128 900 тыс. ₽,
дебиторская задолженность 147 300 тыс. ₽, денежные средства 29 032 тыс. ₽.

Капитал и резервы — 113 565 тыс. ₽. Долгосрочные обязательства — 240 тыс. ₽,
краткосрочные — 224 069 тыс. ₽, в том числе заёмные средства
**141 869 тыс. ₽**.

### Денежные потоки

| Текущие операции | Инвестиционные операции | Финансовые операции | За период |
|---:|---:|---:|---:|
| 2 508 тыс. ₽ | −9 600 тыс. ₽ | 4 516 тыс. ₽ | −2 576 тыс. ₽ |

### Что важно

- Оборот растёт двузначными темпами, но коммерческие расходы занимают 17,7% выручки.
- Краткосрочные займы 141 869 тыс. ₽ — основной источник финансирования оборотного капитала.
- Запасы оборачиваются за 98 дней, дебиторская задолженность — за 47 дней.
- Операционный поток положительный, но не покрывает инвестиции, поэтому итоговое
  изменение денежных средств отрицательное.
- Среднесписочная численность — 48 человек.""",
    "U_8501": """## Итоги за 2025 год

Выручка — **553 898 тыс. ₽** (+17,5% к 471 230 тыс. ₽ в 2024 году),
чистая прибыль — **73 573 тыс. ₽**.

### Отчёт о финансовых результатах

| Показатель | 2025 г., тыс. ₽ |
|---|---:|
| Выручка | 553 898 |
| Себестоимость продаж | −362 802 |
| Валовая прибыль | 191 096 |
| Коммерческие расходы | −28 132 |
| Управленческие расходы | −82 148 |
| Прибыль от продаж | 80 816 |
| Проценты к уплате | −9 047 |
| Прочие доходы | 9 500 |
| Прочие расходы | −5 350 |
| Чистая прибыль | 73 573 |

### Бухгалтерский баланс на 31.12.2025

Валюта баланса — **323 367 тыс. ₽**: внеоборотные активы 149 370 тыс. ₽,
оборотные 173 997 тыс. ₽. В оборотных активах запасы 14 000 тыс. ₽,
дебиторская задолженность 118 200 тыс. ₽, денежные средства 38 797 тыс. ₽.

Капитал и резервы — 138 167 тыс. ₽. Долгосрочные обязательства — 49 420 тыс. ₽,
краткосрочные — 135 780 тыс. ₽.

### Денежные потоки

| Текущие операции | Инвестиционные операции | Финансовые операции | За период |
|---:|---:|---:|---:|
| 94 264 тыс. ₽ | −50 200 тыс. ₽ | −74 300 тыс. ₽ | −30 236 тыс. ₽ |

### Что важно

- Чистая рентабельность — 13,3% при выручке 553 898 тыс. ₽.
- Основная статья затрат — оплата труда (357 504 тыс. ₽), что соответствует профилю разработки ПО.
- Операционный поток 94 264 тыс. ₽ покрывает инвестиции в НМА и оборудование.
- Денежные средства снизились с 70 440 до 38 797 тыс. ₽ из-за инвестиций и финансовых выплат.
- Среднесписочная численность — 196 человек.""",
    "U_137980": """## Итоги за 2025 год

Выручка — **707 849 тыс. ₽** (+126,4% к 312 600 тыс. ₽ в 2024 году),
чистая прибыль — **18 871 тыс. ₽**.

### Отчёт о финансовых результатах

| Показатель | 2025 г., тыс. ₽ |
|---|---:|
| Выручка | 707 849 |
| Себестоимость продаж | −614 263 |
| Валовая прибыль | 93 586 |
| Коммерческие расходы | −2 124 |
| Управленческие расходы | −42 164 |
| Прибыль от продаж | 49 298 |
| Проценты к уплате | −20 833 |
| Прочие доходы | 2 050 |
| Прочие расходы | −6 220 |
| Чистая прибыль | 18 871 |

### Бухгалтерский баланс на 31.12.2025

Валюта баланса — **365 569 тыс. ₽**: внеоборотные активы 164 044 тыс. ₽,
оборотные 201 525 тыс. ₽. В оборотных активах запасы 59 900 тыс. ₽,
дебиторская задолженность 122 000 тыс. ₽, денежные средства 15 525 тыс. ₽.

Капитал и резервы — 27 619 тыс. ₽. Долгосрочные обязательства — 133 834 тыс. ₽,
краткосрочные — 204 116 тыс. ₽.

### Денежные потоки

| Текущие операции | Инвестиционные операции | Финансовые операции | За период |
|---:|---:|---:|---:|
| 25 694 тыс. ₽ | −24 000 тыс. ₽ | −6 400 тыс. ₽ | −4 706 тыс. ₽ |

### Что важно

- Выручка выросла в 2,3 раза, но чистая рентабельность составляет 2,7%.
- Себестоимость 614 263 тыс. ₽ — 86,8% выручки, что типично для генподряда.
- Дебиторская задолженность 122 000 тыс. ₽ сопоставима с 17% годовой выручки.
- Краткосрочные обязательства 204 116 тыс. ₽ превышают оборотные активы 201 525 тыс. ₽.
- Среднесписочная численность — 185 человек.""",
}

REPORT_FILENAMES = {
    uid: {
        "balance": f"{uid}_1_Бухгалтерский_баланс_2025.pdf",
        "income": f"{uid}_2_Отчет_о_финансовых_результатах_2025.pdf",
        "cash_flow": f"{uid}_3_Отчет_о_движении_денежных_средств_2025.pdf",
    }
    for uid in DEMO_UIDS
}

DEMO_FTS_COUNTRIES = {
    "U_71020": "Китай",
    "U_8501": "США",
    "U_137980": "Турция",
}


def reporting_payload(uid: str) -> dict:
    full = REPORTING_SUMMARIES[uid].strip()
    sections = {
        "balance": ("### Бухгалтерский баланс", "### Денежные потоки"),
        "income": ("### Отчёт о финансовых результатах", "### Бухгалтерский баланс"),
        "cash_flow": ("### Денежные потоки", "### Что важно"),
    }
    forms = {}
    for key, (heading, next_heading) in sections.items():
        start = full.find(heading)
        if start >= 0:
            end = full.find(next_heading, start + len(heading))
            if end < 0:
                end = len(full)
            markdown = full[start:end].strip()
        else:
            markdown = full
        overview = full[: full.find(heading)].strip() if full.find(heading) > 0 else ""
        forms[key] = {
            "filename": REPORT_FILENAMES[uid][key],
            "markdown": f"# Саммари отчёта\n\n{overview}\n\n{markdown}".strip(),
        }
    return {"period": "2025", "forms": forms, "markdown": full}


ROLES = ("owner", "ceo", "cfo", "chief_accountant", "treasurer", "c_level")


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_demo_companies(count: int = 60) -> list[dict]:
    rng = random.Random(15015)
    companies = build_companies(count, rng)
    for index, company in enumerate(companies, start=1):
        company["uid"] = (
            REFERENCE_UIDS[index - 1]
            if index <= COUNT
            else f"{COMPANY_PREFIX}{index:03d}"
        )
        if company["uid"] in DEMO_FTS_COUNTRIES:
            company["fts_flag"] = True
            company["fts_country_name"] = DEMO_FTS_COUNTRIES[company["uid"]]
    return companies


def load_reference_companies(data_dir: Path) -> list[dict] | None:
    path = data_dir / "df_Uid_data_hack.csv"
    if not path.exists():
        return None
    wanted = set(REFERENCE_UIDS)
    found: dict[str, dict] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            uid = (row.get("SYNTHETIC_U") or "").strip()
            if uid not in wanted:
                continue
            company = dict(zip(COMPANY_COLUMNS, company_record(row), strict=True))
            company["tags"] = json.loads(company["tags"])
            if uid in DEMO_FTS_COUNTRIES:
                company["fts_flag"] = True
                company["fts_country_name"] = DEMO_FTS_COUNTRIES[uid]
            found[uid] = company
    missing = wanted - found.keys()
    if missing:
        raise SystemExit(
            f"В CSV нет компаний из reference_uids.json: {sorted(missing)}"
        )
    return [found[uid] for uid in REFERENCE_UIDS]


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
    updates = ", ".join(
        f"{column} = EXCLUDED.{column}" for column in COMPANY_COLUMNS if column != "uid"
    )
    await conn.executemany(
        f"""
        INSERT INTO companies ({", ".join(COMPANY_COLUMNS)})
        VALUES ({", ".join(f"${i}" for i in range(1, len(COMPANY_COLUMNS) + 1))})
        ON CONFLICT (uid) DO UPDATE SET {updates}
        """,
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


async def _seed_demo_counterparties(
    conn: asyncpg.Connection, profile_id: uuid.UUID, company_uid: str
) -> None:
    for direction, where_column, company_column, names, label in (
        ("supplier", "payer", "beneficiary", DEMO_COUNTERPARTY_NAMES[company_uid], "закупок"),
        ("buyer", "beneficiary", "payer", DEMO_BUYER_NAMES[company_uid], "выручки"),
    ):
        rows = await conn.fetch(
            f"SELECT {company_column} AS uid, sum(amount) AS amount, sum(\"count\") AS cnt "
            f"FROM payments WHERE {where_column} = $1 GROUP BY {company_column} "
            "ORDER BY amount DESC LIMIT $2",
            company_uid,
            len(names),
        )
        rows = list(rows)
        if len(rows) < len(names):
            rows.extend(
                {
                    "uid": f"DEMO_{company_uid}_{direction}_{index}",
                    "amount": 900_000 - index * 70_000,
                    "cnt": max(1, 25 - index * 2),
                }
                for index in range(len(rows), len(names))
            )
        total = sum(float(row["amount"] or 0) for row in rows) or 1
        for index, row in enumerate(rows):
            amount = float(row["amount"] or 0)
            count = int(row["cnt"] or 0)
            share = amount / total
            importance = min(
                100,
                round(share * 80 + min(math.log1p(count) / math.log1p(1000), 1) * 20),
            )
            await conn.execute(
                """
                INSERT INTO counterparties (
                    id, profile_id, company_uid, direction, total_amount, payments_count,
                    share, importance, default_name, note
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (profile_id, company_uid, direction) DO UPDATE SET
                    default_name = EXCLUDED.default_name, note = EXCLUDED.note
                """,
                uuid.uuid4(), profile_id, row["uid"], direction, amount, count,
                round(share, 4), importance, names[index],
                f"{share:.0%} {label}, {count} платежей",
            )


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
    await conn.execute(
        """
        UPDATE business_profiles
        SET company_uid = $2, entrepreneur_name = $3, business_name = $4, role = $5,
            tags = $6::jsonb, reporting_summary = $7::jsonb,
            onboarding_step = 'completed', onboarding_completed = true
        WHERE id = $1
        """,
        profile_id,
        company["uid"],
        ENTREPRENEURS[index],
        BUSINESSES[index],
        ROLES[index % len(ROLES)],
        _json(company["tags"]),
        _json(reporting_payload(company["uid"])),
    )
    await conn.execute("DELETE FROM counterparties WHERE profile_id = $1", profile_id)

    for item in heuristic_category_weights(SimpleNamespace(**company)):
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
    return profile_id, created


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed three demo business profiles")
    parser.add_argument("--password", default="demo", help="Password for demo1..demo3")
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Assume the schema is already migrated",
    )
    parser.add_argument("--data-dir", help="Directory with df_*_hack.csv files")
    args = parser.parse_args()

    if not args.skip_migrations:
        await _apply_migrations()

    settings = get_settings()
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute("DELETE FROM users WHERE login ~ '^demo([4-9]|1[0-5])$'")
        await seed_categories(conn)
        await seed_channels(conn)
        data_dir = None
        with contextlib.suppress(SystemExit):
            data_dir = resolve_data_dir(args.data_dir)
        reference = load_reference_companies(data_dir) if data_dir else None
        if reference:
            print(f"companies: reference data from {data_dir}")
            await seed_companies(conn, data_dir, 0)
            if settings.seed_with_payments:
                await seed_payments(conn, data_dir)
            await seed_person_links(conn, data_dir)
            await _seed_companies(conn, reference)
            companies = reference
        else:
            all_companies = build_demo_companies()
            await _seed_companies(conn, all_companies)
            companies = all_companies[:COUNT]

        demo_companies = {company["uid"]: company for company in companies}

        print(f"\n{'login':<8} {'password':<10} {'company':<14} business")
        for index, uid in enumerate(DEMO_UIDS):
            company = demo_companies[uid]
            login = f"demo{index + 1}"
            user_id = await ensure_user(conn, login, args.password)
            profile_id, created = await _ensure_profile(conn, user_id, company, index)
            await _seed_demo_counterparties(conn, profile_id, company["uid"])
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
