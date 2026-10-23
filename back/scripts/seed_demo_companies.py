"""Seed synthetic companies and payments for the business-selection demo.

Usage (from back/):
    uv run python scripts/seed_demo_companies.py
    uv run python scripts/seed_demo_companies.py --companies 1000 --with-payments 40
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random

import asyncpg

from back.config import get_settings
from back.core.company import company_tags, revenue_segment

INDUSTRIES: tuple[tuple[str, str, str], ...] = (
    ("24.10", "Производство металлургической продукции", "металлургия"),
    ("49.20", "Грузовые перевозки", "логистика"),
    ("41.20", "Строительство зданий", "строительство"),
    ("47.11", "Розничная торговля", "ритейл"),
    ("01.11", "Сельское хозяйство", "АПК"),
    ("62.01", "Разработка программного обеспечения", "IT"),
    ("28.11", "Производство машин и оборудования", "машиностроение"),
    ("20.13", "Производство химической продукции", "химия"),
    ("64.19", "Деятельность банков", "финансы"),
    ("35.11", "Производство электроэнергии", "энергетика"),
    ("06.10", "Добыча нефти и газа", "нефтегаз"),
    ("16.10", "Лесозаготовка", "лесная промышленность"),
    ("21.20", "Фармацевтическое производство", "фарма"),
    ("85.11", "Деятельность в области образования", "образование"),
    ("79.90", "Туристические услуги", "туризм"),
    ("73.11", "Рекламные агентства", "реклама"),
    ("65.12", "Страхование", "страхование"),
    ("14.13", "Производство одежды", "потребительские товары"),
    ("61.10", "Телекоммуникации", "телеком"),
    ("68.20", "Операции с недвижимостью", "недвижимость"),
)

CITIES: tuple[tuple[str, str], ...] = (
    ("Москва", "Московская область"),
    ("Санкт-Петербург", "Ленинградская область"),
    ("Екатеринбург", "Свердловская область"),
    ("Казань", "Татарстан"),
    ("Новосибирск", "Новосибирская область"),
    ("Нижний Новгород", "Нижегородская область"),
    ("Самара", "Самарская область"),
    ("Ростов-на-Дону", "Ростовская область"),
    ("Краснодар", "Краснодарский край"),
    ("Владивосток", "Приморский край"),
    ("Челябинск", "Челябинская область"),
    ("Пермь", "Пермский край"),
    ("Уфа", "Башкортостан"),
    ("Воронеж", "Воронежская область"),
    ("Волгоград", "Волгоградская область"),
    ("Красноярск", "Красноярский край"),
    ("Тюмень", "Тюменская область"),
    ("Иркутск", "Иркутская область"),
    ("Хабаровск", "Хабаровский край"),
    ("Омск", "Омская область"),
    ("Томск", "Томская область"),
    ("Саратов", "Саратовская область"),
    ("Тула", "Тульская область"),
    ("Ярославль", "Ярославская область"),
    ("Калининград", "Калининградская область"),
)

FTS_COUNTRIES: tuple[str, ...] = (
    "Китай",
    "Турция",
    "Индия",
    "Казахстан",
    "Беларусь",
    "ОАЭ",
    "Египет",
    "Бразилия",
)

AGE_GRADATIONS = ("до 1 года", "1-3 года", "3-5 лет", "5-10 лет", "более 10 лет")
WORKER_GRADATIONS = ("до 15", "16-100", "101-250", "251-1000", "более 1000")
ECO_LABELS = ("Высокий", "Средний", "Низкий")
ORG_TYPES = (("ООО", "Общество с ограниченной ответственностью"),) * 7 + (
    ("АО", "Акционерное общество"),
    ("АО", "Акционерное общество"),
    ("ПАО", "Публичное акционерное общество"),
)

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


def build_companies(count: int, rng: random.Random) -> list[dict]:
    companies: list[dict] = []
    for index in range(1, count + 1):
        code, okved_name, industry_tag = INDUSTRIES[index % len(INDUSTRIES)]
        city, region = CITIES[rng.randrange(len(CITIES))]
        org_type, okfs_name = ORG_TYPES[rng.randrange(len(ORG_TYPES))]
        fts_flag = rng.random() < 0.25
        revenue = round(min(120_000_000_000, 30_000_000 * (4_000 ** rng.random())), -4)
        raw = {
            "uid": f"SYN{index:06d}",
            "org_type": org_type,
            "okfs_name": okfs_name,
            "company_age_years_gradation": AGE_GRADATIONS[rng.randrange(len(AGE_GRADATIONS))],
            "eco_mark_label": ECO_LABELS[rng.randrange(len(ECO_LABELS))],
            "main_okved_code": code,
            "main_okved_name": okved_name,
            "negative_mark": round(rng.choice((0.0, 0.0, 0.0, 0.05, 0.1)), 2),
            "amount_workers_fns_gradation": WORKER_GRADATIONS[
                rng.randrange(len(WORKER_GRADATIONS))
            ],
            "amount_workers_spark_gradation": WORKER_GRADATIONS[
                rng.randrange(len(WORKER_GRADATIONS))
            ],
            "client_type": "Юридическое лицо",
            "cl_product_rko_mark": rng.random() < 0.95,
            "cl_product_gar_mark": rng.random() < 0.25,
            "cl_product_loa_mark": rng.random() < 0.45,
            "cl_product_lea_mark": rng.random() < 0.20,
            "cl_product_dep_mark": rng.random() < 0.55,
            "cl_product_zpp_mark": rng.random() < 0.40,
            "fts_flag": fts_flag,
            "fts_country_name": (
                FTS_COUNTRIES[rng.randrange(len(FTS_COUNTRIES))] if fts_flag else None
            ),
            "factoring_mark": rng.random() < 0.12,
            "revenue": revenue,
            "group_id": f"G{1000 + rng.randrange(120)}" if rng.random() < 0.30 else None,
            "city": city,
            "region": region,
        }
        raw["revenue_segment"] = revenue_segment(revenue)
        tags = [industry_tag, *company_tags(raw)]
        raw["tags"] = list(dict.fromkeys(tags))[:12]
        companies.append(raw)
    return companies


def build_payments(companies: list[dict], with_payments: int, rng: random.Random) -> list[tuple]:
    uids = [company["uid"] for company in companies]
    records: list[tuple[str, str, float, int]] = []
    for payer in uids[:with_payments]:
        partners = [uid for uid in uids if uid != payer]
        supplier_count = rng.randint(8, 20)
        buyer_count = rng.randint(8, 20)
        for supplier in rng.sample(partners, supplier_count):
            records.append(
                (
                    payer,
                    supplier,
                    round(rng.uniform(50_000, 500_000_000), 2),
                    rng.randint(1, 50),
                )
            )
        for buyer in rng.sample(partners, buyer_count):
            records.append(
                (
                    buyer,
                    payer,
                    round(rng.uniform(50_000, 500_000_000), 2),
                    rng.randint(1, 50),
                )
            )
    return records


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed synthetic demo companies")
    parser.add_argument("--companies", type=int, default=1000)
    parser.add_argument("--with-payments", type=int, default=40)
    args = parser.parse_args()

    rng = random.Random(42)
    companies = build_companies(args.companies, rng)
    records = [
        tuple(
            json.dumps(company[column], ensure_ascii=False) if column == "tags" else company[column]
            for column in COMPANY_COLUMNS
        )
        for company in companies
    ]

    settings = get_settings()
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
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

        uids = [company["uid"] for company in companies[: args.with_payments]]
        if uids:
            existing = {
                row["uid"]
                for row in await conn.fetch(
                    """
                    SELECT payer AS uid FROM payments WHERE payer = ANY($1)
                    UNION
                    SELECT beneficiary AS uid FROM payments WHERE beneficiary = ANY($1)
                    """,
                    uids,
                )
            }
            pending = [uid for uid in uids if uid not in existing]
            payment_records = build_payments(
                [company for company in companies if company["uid"] in pending],
                len(pending),
                rng,
            )
            if payment_records:
                await conn.executemany(
                    """
                    INSERT INTO payments (payer, beneficiary, amount, count)
                    VALUES ($1, $2, $3, $4)
                    """,
                    payment_records,
                )

        company_count = await conn.fetchval("SELECT count(*) FROM companies")
        payment_count = await conn.fetchval("SELECT count(*) FROM payments")
        paying = await conn.fetchval(
            "SELECT count(DISTINCT payer) FROM payments WHERE payer LIKE 'SYN%'"
        )
        print(f"companies: {company_count}")
        print(f"payments: {payment_count} (payers: {paying})")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
