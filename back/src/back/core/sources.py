import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelSeed:
    id: str
    name: str
    topics: str
    handle: str | None = None


CHANNELS: tuple[ChannelSeed, ...] = (
    ChannelSeed("rian_ru", "РИА Новости", "политика, экономика", "@rian_ru"),
    ChannelSeed("kommersant", "Коммерсантъ", "политика, экономика", "@kommersant"),
    ChannelSeed("rbc_news", "РБК. Новости. Главное", "политика, экономика", "@rbc_news"),
    ChannelSeed("tass_agency", "ТАСС", "политика, экономика", "@tass_agency"),
    ChannelSeed("vedomosti", "ВЕДОМОСТИ", "политика, экономика", "@vedomosti"),
    ChannelSeed("gazetaru", "Газета.Ru", "политика, экономика", "@gazetaru"),
    ChannelSeed("izvestia", "IZ.RU", "политика, экономика", "@izvestia"),
    ChannelSeed("duma_gov_ru", "Государственная Дума", "политика, экономика", "@duma_gov_ru"),
    ChannelSeed("government_rus", "Правительство России", "политика, экономика", "@government_rus"),
    ChannelSeed("mir24tv", "МИР 24 | Первый Евразийский", "политика, экономика", "@mir24tv"),
    ChannelSeed("bbbreaking", "Раньше всех. Ну почти.", "политика, экономика", "@bbbreaking"),
    ChannelSeed("rusanctions", "Санкции в РФ", "политика, экономика", "@RUSanctions"),
    ChannelSeed("govorit_eu", "Говорит Европа", "политика, экономика", "@govorit_eu"),
    ChannelSeed("economica", "The Экономист", "политика, экономика", "@economica"),
    ChannelSeed(
        "garantnews",
        "ГАРАНТ. Новости законодательства",
        "политика, экономика",
        "@garantnews",
    ),
    ChannelSeed("consultant_plus", "КонсультантПлюс", "политика, экономика", "@consultant_plus"),
    ChannelSeed("ekonomika_banki", "Деньги в Эфире", "макро, рынки", "@ekonomika_banki"),
    ChannelSeed("ecotopor", "Топор. Экономика.", "макро, рынки", "@ecotopor"),
    ChannelSeed("prostoecon", "Простая экономика", "макро, рынки", "@prostoecon"),
    ChannelSeed("oslabilrubl", "Осла бил рубль • Экономика", "макро, рынки", "@oslabilrubl"),
    ChannelSeed(
        "oslabilrubl_news",
        "Осла бил рубль • Новости, экономика",
        "макро, рынки",
        "@oslabilrubl_news",
    ),
    ChannelSeed("alfa_investments", "Альфа-Инвестиции", "макро, рынки", "@alfa_investments"),
    ChannelSeed("proeconomics", "Proeconomics", "макро, рынки", "@proeconomics"),
    ChannelSeed("spydell_finance", "Spydell_finance", "макро, рынки", "@spydell_finance"),
    ChannelSeed("rerussia_org", "Re: Russia", "макро, рынки", "@rerussia_org"),
    ChannelSeed("eschulmann", "Екатерина Шульман", "макро, рынки", "@eschulmann"),
    ChannelSeed("moneyandpolarfox", "Деньги и песец", "макро, рынки", "@moneyandpolarfox"),
    ChannelSeed("eglavbukru", "Журнал \"Главбух\"", "налоги, право", "@eglavbukru"),
    ChannelSeed("klerkonline", "Бухучет и налоги от «Клерк.Ру»", "налоги, право", "@klerkonline"),
    ChannelSeed("gazeta_unp", "Учет. Налоги. Право", "налоги, право", "@gazeta_unp"),
    ChannelSeed("financ_director", "Финансовый директор", "налоги, право", "@financ_director"),
    ChannelSeed(
        "cfo_russiaru",
        "CFO-Russia.ru || Финансовый директор: кейсы и мероприятия",
        "налоги, право",
        "@cfo_russiaru",
    ),
    ChannelSeed("dd_tax", "Налоги и Таможня", "налоги, право", "@DD_tax"),
    ChannelSeed("corplawpro", "Корпоративные споры • Case by Case", "налоги, право", "@corplawpro"),
    ChannelSeed("nalogi_po_umu", "Налоги по Уму|Эксперты", "налоги, право", "@nalogi_po_umu"),
    ChannelSeed("asnnewsru", "АСН — Агентство Страховых Новостей", "страхование", "@asnnewsru"),
    ChannelSeed("ssluchay", "Страховой случай", "страхование", "@ssluchay"),
    ChannelSeed("insurancenew", "Что по страхованию?", "страхование", "@insurancenew"),
    ChannelSeed(
        "vottak_me",
        "ВТ: Новости страхования, экономики и общества для профессионалов и страхователей",
        "страхование",
        "@vottak_me",
    ),
    ChannelSeed("customs_rf", "ФТС России", "ВЭД, таможня", "@customs_rf"),
    ChannelSeed("vedofon", "ВЭД-OFF/ON", "ВЭД, таможня", "@vedofon"),
    ChannelSeed("proimport", "Импорт в Россию", "ВЭД, таможня", "@proimport"),
    ChannelSeed("proved_is_here", "Всё о таможне и ВЭД", "ВЭД, таможня", "@proved_is_here"),
    ChannelSeed(
        "centrved",
        "ЦентрВЭД (импорт, экспорт, таможня, логистика, сертификация, ВЭД)",
        "ВЭД, таможня",
        "@CentrVED",
    ),
    ChannelSeed("gruz0potok", "Грузопоток", "логистика", "@gruz0potok"),
    ChannelSeed("logirus", "Logirus - №1 о логистике", "логистика", "@logirus"),
    ChannelSeed(
        "transportandlogistic",
        "Транспорт и логистика",
        "логистика",
        "@transportandlogistic",
    ),
    ChannelSeed("retail_ru", "Retail.ru - пишем о ритейле каждый день", "ритейл", "@retail_ru"),
    ChannelSeed("retailrus", "Русский ритейл и бизнес", "ритейл", "@retailrus"),
    ChannelSeed("svobodakassa", "Свободная касса (ритейл & e-com)", "ритейл", "@svobodakassa"),
    ChannelSeed("inferno_retail", "Адский e-comm и ритейл", "ритейл", "@inferno_retail"),
    ChannelSeed("fintechassociation", "Ассоциация ФинТех", "банки, финтех", "@fintechassociation"),
    ChannelSeed("frank_media", "Frank Media", "банки, финтех", "@frank_media"),
    ChannelSeed("fintexno", "Финтехно", "банки, финтех", "@fintexno"),
    ChannelSeed("economicno", "Экономично | про банки и финтех", "банки, финтех", "@economicno"),
    ChannelSeed("fintex", "Русский финтех, е-ком и бизнес", "банки, финтех", "@fintex"),
    ChannelSeed("mcx_ru", "Минсельхоз России", "АПК", "@mcx_ru"),
    ChannelSeed("agroinvestor", "Агроинвестор | Новости АПК", "АПК", "@agroinvestor"),
    ChannelSeed("agro_nomika", "Агрономика", "АПК", "@agro_nomika"),
    ChannelSeed("mcxae", "Агроэкспорт", "АПК", "@mcxae"),
    ChannelSeed("neftegazchannel", "Neftegaz.RU", "нефтегаз", "@neftegazchannel"),
    ChannelSeed("papagaz", "Газ-Батюшка", "нефтегаз", "@papagaz"),
    ChannelSeed(
        "oil_capital",
        "Нефть и Капитал I Новости Нефтегазовой отрасли",
        "нефтегаз",
        "@oil_capital",
    ),
    ChannelSeed("infotek_russia", "ИнфоТЭК", "нефтегаз", "@Infotek_Russia"),
    ChannelSeed("neftegazterritory", "Neftegaz Territory", "нефтегаз", "@neftegazterritory"),
    ChannelSeed("nerzhavey", "Нержавейка", "металлургия", "@nerzhavey"),
    ChannelSeed("prometallinfo", "ПРОметалл", "металлургия", "@prometallinfo"),
    ChannelSeed("metals_mining", "Металл и Минерал", "металлургия", "@Metals_Mining"),
    ChannelSeed("rupec", "RUPEC", "химия", "@Rupec"),
    ChannelSeed("fertilizerdaily", "Fertilizer Daily", "химия", "@fertilizerdaily"),
    ChannelSeed("coala_russia", "Coala", "уголь", "@Coala_Russia"),
    ChannelSeed("soyuzmash1", "Союз машиностроителей России", "машиностроение", "@soyuzmash1"),
    ChannelSeed("uecrus_official", "ОДК", "машиностроение", "@uecrus_official"),
    ChannelSeed("protradein", "Самородов Про АвтоБизнес", "автобизнес", "@protradein"),
    ChannelSeed("tourdom", "Крыша ТурДома", "туризм", "@tourdom"),
    ChannelSeed("tourismsafety", "Безопасность туризма", "туризм", "@tourismsafety"),
    ChannelSeed("gkhnews", "ЖКХ Ньюс", "ЖКХ", "@gkhnews"),
    ChannelSeed("starshijpodomu", "Старший по дому | ЖКХ", "ЖКХ", "@starshijpodomu"),
    ChannelSeed("dpilorama", "Деловая пилорама", "мебель", "@dpilorama"),
    ChannelSeed("mebel_nom", "Интерьерный бизнес", "мебель", "@mebel_nom"),
    ChannelSeed("industrymebel", "Индустрия мебели", "мебель", "@industrymebel"),
    ChannelSeed("prayandsew", "Молиться и шить", "мода", "@prayandsew"),
    ChannelSeed("fashionprokachka", "Fashion прокачка", "мода", "@fashionprokachka"),
    ChannelSeed(
        "daniyatkacheva",
        "Дания Ткачёва | Модный ритейл | Продажи | Стратегия",
        "мода",
        "@DaniyaTkacheva",
    ),
    ChannelSeed("sostav", "Sostav", "маркетинг, медиа", "@sostav"),
    ChannelSeed("adindex", "AdIndex", "маркетинг, медиа", "@AdIndex"),
    ChannelSeed("ftsec", "42 секунды", "IT, телеком", "@ftsec"),
    ChannelSeed("t_bank_data", "T-Data", "IT, телеком", "@t_bank_data"),
    ChannelSeed("disruptors_official", "Дизраптор", "IT, телеком", "@disruptors_official"),
    ChannelSeed("edtexno", "Эдтехно | образование", "образование", "@edtexno"),
    ChannelSeed(
        "ru_education",
        "Образование, которое мы заслужили",
        "образование",
        "@ru_education",
    ),
    ChannelSeed("gxpnews", "GхP News", "фарма", "@gxpnews"),
    ChannelSeed("bigbeautyboss", "Big Beauty Boss", "бьюти", "@bigbeautyboss"),
)

RECOMMENDED_IDS: tuple[str, ...] = (
    "rian_ru",
    "kommersant",
    "rbc_news",
    "tass_agency",
    "vedomosti",
    "government_rus",
    "duma_gov_ru",
    "garantnews",
    "consultant_plus",
    "ekonomika_banki",
    "ecotopor",
    "alfa_investments",
    "customs_rf",
    "mcx_ru",
    "frank_media",
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
