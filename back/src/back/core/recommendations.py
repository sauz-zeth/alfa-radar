from dataclasses import dataclass
from functools import lru_cache

from back.core.categories import CATEGORIES
from back.core.rss_importance import rss_importance
from back.core.sources import CHANNELS, ChannelSeed

GENERAL_CATEGORY_IDS = frozenset(item.id for item in CATEGORIES if item.group == "general")
INDUSTRY_CATEGORY_IDS = frozenset(item.id for item in CATEGORIES if item.group == "industry")

GENERAL_SLOTS = 15
RECOMMENDATIONS_LIMIT = 50
PER_TYPE_LIMIT = RECOMMENDATIONS_LIMIT // 2

HANDLE_CATEGORY_IDS: dict[str, set[int]] = {}
for _category in CATEGORIES:
    for _handle in _category.channels:
        HANDLE_CATEGORY_IDS.setdefault(_handle.lower(), set()).add(_category.id)

BROAD_GENERAL_TOPICS = frozenset(
    {
        "политика, экономика",
        "макро, рынки",
        "регионы",
        "внешние рынки",
        "мировая пресса",
    }
)

TOPIC_CATEGORY_IDS: dict[str, frozenset[int]] = {
    "политика, экономика": GENERAL_CATEGORY_IDS,
    "макро, рынки": frozenset({1, 2, 9, 12, 13, 23}),
    "налоги, право": frozenset({5, 6, 7, 8, 11}),
    "ВЭД, таможня": frozenset({2, 3, 4, 12, 20}),
    "регионы": GENERAL_CATEGORY_IDS,
    "внешние рынки": frozenset({2, 3, 4, 12}),
    "мировая пресса": frozenset({1, 2, 12, 13}),
    "логистика": frozenset({20}),
    "ритейл": frozenset({13, 22}),
    "банки, финтех": frozenset({1, 23}),
    "АПК": frozenset({18}),
    "нефтегаз": frozenset({16}),
    "металлургия": frozenset({15}),
    "химия": frozenset({17}),
    "уголь": frozenset({15}),
    "машиностроение": frozenset({19}),
    "автобизнес": frozenset({21}),
    "туризм": frozenset({28}),
    "ЖКХ": frozenset({10, 14}),
    "мебель": frozenset({29}),
    "мода": frozenset({29}),
    "маркетинг, медиа": frozenset({30}),
    "IT, телеком": frozenset({25}),
    "образование": frozenset({26}),
    "фарма": frozenset({27}),
    "бьюти": frozenset({29}),
    "страхование": frozenset({24}),
    "сырьё, энергетика": frozenset({15, 16, 17, 19}),
    "ритейл, авто, фарма": frozenset({21, 22, 27}),
}

RELATED_CATEGORY_IDS: dict[int, frozenset[int]] = {
    1: frozenset({13, 23}),
    2: frozenset({3, 4, 12, 20, 23}),
    3: frozenset({2, 4, 12, 15, 16, 17, 19, 20, 25}),
    4: frozenset({2, 3, 12, 15, 16, 17, 18, 19, 20, 21, 22}),
    5: frozenset({6, 7, 8, 11}),
    6: frozenset({5, 7}),
    7: frozenset({5, 6, 8, 11}),
    8: frozenset({5}),
    9: frozenset({10, 14, 18, 19}),
    10: frozenset({14, 16, 19}),
    11: frozenset({5, 7, 9, 14, 19, 25, 27}),
    12: frozenset({2, 3, 4, 16, 20, 23}),
    13: frozenset({18, 21, 22, 28, 29, 30}),
    14: frozenset({10, 15, 17, 19, 20, 29}),
    15: frozenset({3, 4, 10, 14, 16, 17, 19, 20, 23}),
    16: frozenset({4, 10, 12, 15, 17, 19, 20}),
    17: frozenset({4, 14, 15, 16, 18, 19, 20, 27, 29}),
    18: frozenset({4, 13, 17, 20, 22, 29}),
    19: frozenset({4, 9, 11, 14, 15, 16, 17, 20, 21, 25}),
    20: frozenset({2, 3, 4, 12, 14, 15, 16, 17, 18, 21, 22}),
    21: frozenset({4, 13, 19, 20, 22}),
    22: frozenset({4, 13, 18, 20, 21, 29, 30}),
    23: frozenset({1, 2, 12, 25}),
    24: frozenset({1, 5, 7, 14, 21, 23}),
    25: frozenset({3, 11, 13, 19, 23, 26, 30}),
    26: frozenset({8, 25}),
    27: frozenset({4, 5, 11, 17, 22}),
    28: frozenset({13, 20, 22}),
    29: frozenset({4, 13, 17, 20, 22, 30}),
    30: frozenset({13, 22, 25}),
}

SOURCE_CATEGORY_OVERRIDES: dict[str, frozenset[int]] = {
    "New Retail": frozenset({22}),
    "Drom.ru — новости": frozenset({21}),
    "Колёса.ру": frozenset({21}),
    "Vademecum": frozenset({27}),
    "Advertology.ru": frozenset({30}),
    "AdVesti.ru": frozenset({30}),
    "Учительская газета": frozenset({26}),
}

KEYWORD_CATEGORY_IDS: dict[str, frozenset[int]] = {
    "санкц": frozenset({3}),
    "тамож": frozenset({4}),
    "пошлин": frozenset({4}),
    "налог": frozenset({5}),
    "бухгал": frozenset({6}),
    "отчёт": frozenset({6}),
    "отчет": frozenset({6}),
    "банкрот": frozenset({7}),
    "суд": frozenset({7}),
    "кадр": frozenset({8}),
    "труд": frozenset({8}),
    "господдерж": frozenset({9}),
    "субсид": frozenset({9}),
    "жкх": frozenset({10, 14}),
    "тариф": frozenset({10}),
    "закуп": frozenset({11}),
    "геополит": frozenset({12}),
    "инфляц": frozenset({13}),
    "строит": frozenset({14}),
    "недвиж": frozenset({14}),
    "металл": frozenset({15}),
    "сталь": frozenset({15}),
    "нержав": frozenset({15}),
    "руда": frozenset({15}),
    "уголь": frozenset({15}),
    "нефт": frozenset({16}),
    "хим": frozenset({17}),
    "удобр": frozenset({17}),
    "полимер": frozenset({17}),
    "агро": frozenset({18}),
    "зерн": frozenset({18}),
    "апк": frozenset({18}),
    "машин": frozenset({19}),
    "промышлен": frozenset({19}),
    "логист": frozenset({20}),
    "перевоз": frozenset({20}),
    "груз": frozenset({20}),
    "порт": frozenset({20}),
    "автобизнес": frozenset({21}),
    "автомобил": frozenset({21}),
    "авторын": frozenset({21}),
    "автосервис": frozenset({21}),
    "ритейл": frozenset({22}),
    "торгов": frozenset({22}),
    "e-commerce": frozenset({22}),
    "маркетплейс": frozenset({22}),
    "банк": frozenset({23}),
    "финтех": frozenset({23}),
    "страхов": frozenset({24}),
    "телеком": frozenset({25}),
    "кибер": frozenset({25}),
    "цифров": frozenset({25}),
    "образован": frozenset({26}),
    "фарм": frozenset({27}),
    "медиц": frozenset({27}),
    "туризм": frozenset({28}),
    "мебел": frozenset({29}),
    "модный": frozenset({29}),
    "бьюти": frozenset({29}),
    "космет": frozenset({29}),
    "реклам": frozenset({30}),
    "маркетинг": frozenset({30}),
    "медиа": frozenset({30}),
    "ставк": frozenset({1}),
    "валют": frozenset({2}),
    "курс": frozenset({2}),
}


@dataclass(frozen=True)
class SourceCandidate:
    id: str
    name: str
    source_type: str
    popularity: int
    category_ids: frozenset[int]
    is_general: bool


def source_category_ids(seed: ChannelSeed) -> frozenset[int]:
    override = SOURCE_CATEGORY_OVERRIDES.get(seed.name)
    if override is not None:
        return override
    ids: set[int] = set(TOPIC_CATEGORY_IDS.get(seed.topics, ()))
    if seed.handle:
        ids.update(HANDLE_CATEGORY_IDS.get(seed.handle.lower(), ()))
    text = f"{seed.id} {seed.name} {seed.feed_url or ''}".lower()
    for keyword, category_ids in KEYWORD_CATEGORY_IDS.items():
        if keyword in text:
            ids.update(category_ids)
    return frozenset(ids or GENERAL_CATEGORY_IDS)


def _popularity(seed: ChannelSeed) -> int:
    if seed.feed_url:
        return rss_importance(seed.name)
    if seed.subscribers is not None:
        return seed.subscribers
    return seed.popularity or 0


@lru_cache
def candidates() -> tuple[SourceCandidate, ...]:
    return tuple(
        SourceCandidate(
            id=seed.id,
            name=seed.name,
            source_type="rss" if seed.feed_url else "telegram",
            popularity=_popularity(seed),
            category_ids=source_category_ids(seed),
            is_general=seed.topics in BROAD_GENERAL_TOPICS,
        )
        for seed in CHANNELS
    )


@lru_cache
def candidates_by_id() -> dict[str, SourceCandidate]:
    return {item.id: item for item in candidates()}


def _ranked(pool: list[SourceCandidate]) -> list[SourceCandidate]:
    return sorted(pool, key=lambda item: (-item.popularity, item.name.lower()))


def recommend_ids(profile_category_ids: set[int], limit: int = RECOMMENDATIONS_LIMIT) -> list[str]:
    categories = set(profile_category_ids)
    industry_categories = categories & INDUSTRY_CATEGORY_IDS
    related: set[int] = set()
    for category_id in industry_categories:
        related.update(RELATED_CATEGORY_IDS.get(category_id, ()))
    related = (related - categories) & INDUSTRY_CATEGORY_IDS
    other_categories = categories - industry_categories
    general_target = max(10, min(20, limit // 3))
    per_type = limit // 2
    general_tg = general_target // 2 + general_target % 2
    general_rss = general_target - general_tg
    selected: list[SourceCandidate] = []
    for source_type, general_slots in (("telegram", general_tg), ("rss", general_rss)):
        pool = [item for item in candidates() if item.source_type == source_type]
        general_pool = _ranked([item for item in pool if item.is_general])
        industry_pool = _ranked(
            [
                item
                for item in pool
                if not item.is_general and item.category_ids & industry_categories
            ]
        )
        other_pool = _ranked(
            [
                item
                for item in pool
                if not item.is_general and item.category_ids & other_categories
            ]
        )
        related_pool = _ranked(
            [item for item in pool if not item.is_general and item.category_ids & related]
        )
        picks = general_pool[:general_slots]
        seen = {item.id for item in picks}
        for ranked in (industry_pool, other_pool, related_pool):
            for item in ranked:
                if len(picks) >= per_type:
                    break
                if item.id not in seen:
                    seen.add(item.id)
                    picks.append(item)
            if len(picks) >= per_type:
                break
        if len(picks) < per_type:
            picks.extend(item for item in general_pool if item.id not in seen)
        selected.extend(picks[:per_type])

    result: list[str] = []
    result_seen: set[str] = set()
    for item in selected:
        if item.id not in result_seen:
            result_seen.add(item.id)
            result.append(item.id)
    return result[:limit]
