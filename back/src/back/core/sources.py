import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelSeed:
    id: str
    name: str
    topics: str
    handle: str | None = None


CHANNELS: tuple[ChannelSeed, ...] = (
    ChannelSeed("metall-inside", "Металл-Инсайд", "цены, конкуренты", "@metall_inside"),
    ChannelSeed("raw-market", "Сырьевой рынок", "руда, уголь, лом", "@raw_market"),
    ChannelSeed("steel-sheet", "Сталь и прокат", "спрос, цены", "@steel_sheet"),
    ChannelSeed("export-today", "Экспорт сегодня", "пошлины, квоты", "@export_today"),
    ChannelSeed("asia-markets", "Азия: рынки", "Китай, Вьетнам", "@asia_markets"),
    ChannelSeed(
        "transport-logistics",
        "Транспорт и логистика",
        "тарифы РЖД",
        "@transport_logistic",
    ),
    ChannelSeed("business-herald", "Деловой вестник", "деловые новости", "@business_herald"),
    ChannelSeed("industrial-policy", "Промышленная политика", "господдержка", "@industrial_policy"),
    ChannelSeed("customs-ved", "Таможня и ВЭД", "таможня, санкции", "@customs_ved"),
    ChannelSeed("east-corridor", "Восточный коридор", "порты, маршруты", "@east_corridor"),
    ChannelSeed("cargo-ports", "Грузы и порты", "перевалка", "@cargo_ports"),
    ChannelSeed("fx-market", "Валютный рынок", "CNY, USD", "@fx_market"),
    ChannelSeed("fin-analyst", "Финансовый аналитик", "ставка, кредиты", "@fin_analyst"),
    ChannelSeed("cbr", "Банк России", "официальные заявления", "@centralbank_russia"),
    ChannelSeed("minfin", "Минфин России", "налоги, бюджет", "@minfin_russia"),
    ChannelSeed("energy-today", "Энергетика сегодня", "энергетика", "@energy_today"),
    ChannelSeed("oil-gas", "Нефть и газ", "энергетика", "@oil_gas"),
    ChannelSeed("construction", "Строительный рынок", "строительство", "@construction_ru"),
    ChannelSeed("autoprom", "Автопром", "машиностроение", "@autoprom_ru"),
    ChannelSeed("agro-review", "Агро-обзор", "сельское хозяйство", "@agro_review"),
    ChannelSeed("retail-inside", "Ритейл-инсайд", "ритейл", "@retail_inside"),
    ChannelSeed("digital-economy", "Цифровая экономика", "технологии", "@digital_economy"),
    ChannelSeed("real-estate", "Рынок недвижимости", "недвижимость", "@real_estate_ru"),
    ChannelSeed("chemistry", "Химпром", "химия", "@chemistry_ru"),
    ChannelSeed("coal-ore", "Уголь и руда", "сырьё", "@coal_ore"),
    ChannelSeed("nonferrous", "Цветные металлы", "металлургия", "@nonferrous"),
    ChannelSeed("sea-freight", "Морской фрахт", "логистика", "@sea_freight"),
    ChannelSeed("china-business", "Китай: бизнес", "рынки Азии", "@china_business"),
    ChannelSeed("india-markets", "Индия: рынки", "рынки Азии", "@india_markets"),
    ChannelSeed("middle-east", "Ближний Восток: бизнес", "международные рынки", "@middle_east_biz"),
    ChannelSeed("tax-law", "Налоги и право", "право", "@tax_law"),
    ChannelSeed("courts", "Арбитраж и суды", "право", "@arbitration_courts"),
    ChannelSeed("procurement", "Госзакупки", "госрегулирование", "@procurement_ru"),
    ChannelSeed("bonds-debt", "Облигации и долг", "финансы", "@bonds_debt"),
    ChannelSeed("stock-market", "Фондовый рынок", "финансы", "@stock_market"),
    ChannelSeed("macro", "Макроэкономика", "экономика", "@macro_economics"),
    ChannelSeed("urals", "Урал промышленный", "регионы", "@urals_industry"),
    ChannelSeed("siberia", "Сибирь деловая", "регионы", "@siberia_business"),
    ChannelSeed("baltic-ports", "Порты Балтики", "логистика", "@baltic_ports"),
    ChannelSeed("metal-trade", "Металлоторговля", "металлургия", "@metal_trade"),
    ChannelSeed("sanctions", "Санкции и комплаенс", "госрегулирование", "@sanctions_compliance"),
)

RECOMMENDED_IDS: tuple[str, ...] = (
    "metall-inside",
    "raw-market",
    "steel-sheet",
    "export-today",
    "asia-markets",
    "transport-logistics",
    "business-herald",
    "industrial-policy",
    "customs-ved",
    "east-corridor",
    "cargo-ports",
    "fx-market",
    "fin-analyst",
    "cbr",
    "minfin",
)

HANDLE_RE = re.compile(r"^(?:https?://)?t\.me/([A-Za-z0-9_]{3,})/?$", re.IGNORECASE)
AT_RE = re.compile(r"^@([A-Za-z0-9_]{3,})$")


def parse_handle(value: str) -> str | None:
    text = (value or "").strip()
    match = HANDLE_RE.match(text) or AT_RE.match(text)
    return f"@{match.group(1)}" if match else None


def find_channel(value: str) -> ChannelSeed | None:
    text = (value or "").strip().lower()
    if not text:
        return None
    handle = parse_handle(value)
    for item in CHANNELS:
        if text in {item.id.lower(), item.name.lower(), (item.handle or "").lower()}:
            return item
        if handle and item.handle and item.handle.lower() == handle.lower():
            return item
    return None


def search_channels(query: str) -> list[ChannelSeed]:
    text = (query or "").strip().lower()
    if not text:
        return list(CHANNELS)
    handle = parse_handle(query)
    result = []
    for item in CHANNELS:
        haystack = " ".join((item.id, item.name, item.topics, item.handle or "")).lower()
        if text in haystack or (handle and (item.handle or "").lower() == handle.lower()):
            result.append(item)
    return result
