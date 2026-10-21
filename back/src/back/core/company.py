from typing import Any

SEGMENTS: tuple[tuple[float, str], ...] = (
    (120_000_000, "микро"),
    (800_000_000, "малый"),
    (2_000_000_000, "средний"),
    (15_000_000_000, "крупный"),
)


def revenue_segment(revenue: float | None) -> str:
    if not revenue:
        return "неизвестен"
    for threshold, label in SEGMENTS:
        if revenue < threshold:
            return label
    return "крупнейший"


def company_tags(row: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    okved_name = (row.get("main_okved_name") or "").lower()
    city = row.get("city")
    region = row.get("region")

    keyword_tags = {
        "металл": "металлургия",
        "прокат": "металлургия",
        "нефт": "нефтегаз",
        "газ": "нефтегаз",
        "хим": "химия",
        "удобрен": "химия",
        "сельск": "АПК",
        "пищев": "АПК",
        "зерн": "АПК",
        "машин": "машиностроение",
        "оборудован": "машиностроение",
        "строит": "строительство",
        "недвиж": "недвижимость",
        "перевоз": "логистика",
        "транспорт": "логистика",
        "торговл": "торговля",
        "рознич": "ритейл",
        "оптов": "торговля",
        "информац": "IT",
        "программ": "IT",
        "телеком": "телеком",
        "банк": "финансы",
        "страхов": "страхование",
        "фарма": "фарма",
        "медицин": "фарма",
        "образова": "образование",
        "туризм": "туризм",
        "реклам": "реклама",
        "мебел": "потребтовары",
        "одежд": "потребительские товары",
    }
    for keyword, tag in keyword_tags.items():
        if keyword in okved_name and tag not in tags:
            tags.append(tag)

    if row.get("cl_product_loa_mark"):
        tags.append("кредитная нагрузка")
    if row.get("cl_product_dep_mark"):
        tags.append("депозиты")
    if row.get("cl_product_rko_mark"):
        tags.append("РКО")
    if row.get("cl_product_zpp_mark"):
        tags.append("зарплатный проект")
    if row.get("cl_product_lea_mark"):
        tags.append("лизинг")
    if row.get("fts_flag"):
        tags.append("ВЭД")
    if row.get("fts_country_name"):
        tags.append(f"ВЭД: {row['fts_country_name']}")
    if row.get("negative_mark"):
        tags.append("признак ключевого собственника")
    if row.get("eco_mark_label"):
        tags.append(str(row["eco_mark_label"]))
    if city:
        tags.append(str(city))
    if region and region != city:
        tags.append(str(region))

    seen: set[str] = set()
    unique: list[str] = []
    for tag in tags:
        normalized = tag.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(tag.strip())
    return unique[:12]
