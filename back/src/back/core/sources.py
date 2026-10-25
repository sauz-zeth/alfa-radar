import hashlib
import re
from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import urlparse


@dataclass(frozen=True)
class ChannelSeed:
    id: str
    name: str
    topics: str
    handle: str | None = None
    feed_url: str | None = None
    subscribers: int | None = None
    popularity: int | None = None


CHANNELS: tuple[ChannelSeed, ...] = (
    ChannelSeed("rian_ru", "РИА Новости", "политика, экономика", "@rian_ru", subscribers=3029269),
    ChannelSeed(
        "kommersant",
        "Коммерсантъ",
        "политика, экономика",
        "@kommersant",
        subscribers=294819,
    ),
    ChannelSeed(
        "rbc_news",
        "РБК. Новости. Главное",
        "политика, экономика",
        "@rbc_news",
        subscribers=917026,
    ),
    ChannelSeed("tass_agency", "ТАСС", "политика, экономика", "@tass_agency", subscribers=569385),
    ChannelSeed("vedomosti", "ВЕДОМОСТИ", "политика, экономика", "@vedomosti", subscribers=86776),
    ChannelSeed("gazetaru", "Газета.Ru", "политика, экономика", "@gazetaru", subscribers=196415),
    ChannelSeed("izvestia", "IZ.RU", "политика, экономика", "@izvestia", subscribers=133886),
    ChannelSeed(
        "duma_gov_ru",
        "Государственная Дума",
        "политика, экономика",
        "@duma_gov_ru",
        subscribers=111644,
    ),
    ChannelSeed(
        "government_rus",
        "Правительство России",
        "политика, экономика",
        "@government_rus",
        subscribers=167665,
    ),
    ChannelSeed(
        "mir24tv",
        "МИР 24 | Первый Евразийский",
        "политика, экономика",
        "@mir24tv",
        subscribers=12918,
    ),
    ChannelSeed(
        "bbbreaking",
        "Раньше всех. Ну почти.",
        "политика, экономика",
        "@bbbreaking",
        subscribers=1975280,
    ),
    ChannelSeed(
        "rusanctions",
        "Санкции в РФ",
        "политика, экономика",
        "@RUSanctions",
        subscribers=299441,
    ),
    ChannelSeed(
        "govorit_eu",
        "Говорит Европа",
        "политика, экономика",
        "@govorit_eu",
        subscribers=38538,
    ),
    ChannelSeed(
        "economica",
        "The Экономист",
        "политика, экономика",
        "@economica",
        subscribers=1580619,
    ),
    ChannelSeed(
        "garantnews",
        "ГАРАНТ. Новости законодательства",
        "политика, экономика",
        "@garantnews",
        subscribers=24573,
    ),
    ChannelSeed(
        "consultant_plus",
        "КонсультантПлюс",
        "политика, экономика",
        "@consultant_plus",
        subscribers=45164,
    ),
    ChannelSeed(
        "ekonomika_banki",
        "Деньги в Эфире",
        "макро, рынки",
        "@ekonomika_banki",
        subscribers=318931,
    ),
    ChannelSeed("ecotopor", "Топор. Экономика.", "макро, рынки", "@ecotopor", subscribers=1193500),
    ChannelSeed(
        "prostoecon",
        "Простая экономика",
        "макро, рынки",
        "@prostoecon",
        subscribers=301250,
    ),
    ChannelSeed(
        "oslabilrubl",
        "Осла бил рубль • Экономика",
        "макро, рынки",
        "@oslabilrubl",
        subscribers=50066,
    ),
    ChannelSeed(
        "oslabilrubl_news",
        "Осла бил рубль • Новости, экономика",
        "макро, рынки",
        "@oslabilrubl_news",
        subscribers=9919,
    ),
    ChannelSeed(
        "alfa_investments",
        "Альфа-Инвестиции",
        "макро, рынки",
        "@alfa_investments",
        subscribers=705452,
    ),
    ChannelSeed("proeconomics", "Proeconomics", "макро, рынки", "@proeconomics", subscribers=68694),
    ChannelSeed(
        "spydell_finance",
        "Spydell_finance",
        "макро, рынки",
        "@spydell_finance",
        subscribers=131128,
    ),
    ChannelSeed("rerussia_org", "Re: Russia", "макро, рынки", "@rerussia_org", subscribers=18191),
    ChannelSeed(
        "eschulmann",
        "Екатерина Шульман",
        "макро, рынки",
        "@eschulmann",
        subscribers=301284,
    ),
    ChannelSeed(
        "moneyandpolarfox",
        "Деньги и песец",
        "макро, рынки",
        "@moneyandpolarfox",
        subscribers=50998,
    ),
    ChannelSeed(
        "eglavbukru",
        "Журнал \"Главбух\"",
        "налоги, право",
        "@eglavbukru",
        subscribers=82630,
    ),
    ChannelSeed(
        "klerkonline",
        "Бухучет и налоги от «Клерк.Ру»",
        "налоги, право",
        "@klerkonline",
        subscribers=20415,
    ),
    ChannelSeed(
        "gazeta_unp",
        "Учет. Налоги. Право",
        "налоги, право",
        "@gazeta_unp",
        subscribers=8314,
    ),
    ChannelSeed(
        "financ_director",
        "Финансовый директор",
        "налоги, право",
        "@financ_director",
        subscribers=20917,
    ),
    ChannelSeed(
        "cfo_russiaru",
        "CFO-Russia.ru || Финансовый директор: кейсы и мероприятия",
        "налоги, право",
        "@cfo_russiaru",
        subscribers=6039,
    ),
    ChannelSeed("dd_tax", "Налоги и Таможня", "налоги, право", "@DD_tax", subscribers=6310),
    ChannelSeed(
        "corplawpro",
        "Корпоративные споры • Case by Case",
        "налоги, право",
        "@corplawpro",
        subscribers=23647,
    ),
    ChannelSeed(
        "nalogi_po_umu",
        "Налоги по Уму|Эксперты",
        "налоги, право",
        "@nalogi_po_umu",
        subscribers=18231,
    ),
    ChannelSeed(
        "asnnewsru",
        "АСН — Агентство Страховых Новостей",
        "страхование",
        "@asnnewsru",
        subscribers=19471,
    ),
    ChannelSeed("ssluchay", "Страховой случай", "страхование", "@ssluchay", subscribers=25916),
    ChannelSeed(
        "insurancenew",
        "Что по страхованию?",
        "страхование",
        "@insurancenew",
        subscribers=9666,
    ),
    ChannelSeed(
        "vottak_me",
        "ВТ: Новости страхования, экономики и общества для профессионалов и страхователей",
        "страхование",
        "@vottak_me",
        subscribers=44117,
    ),
    ChannelSeed("customs_rf", "ФТС России", "ВЭД, таможня", "@customs_rf", subscribers=54722),
    ChannelSeed("vedofon", "ВЭД-OFF/ON", "ВЭД, таможня", "@vedofon", subscribers=16449),
    ChannelSeed("proimport", "Импорт в Россию", "ВЭД, таможня", "@proimport", subscribers=53148),
    ChannelSeed(
        "proved_is_here",
        "Всё о таможне и ВЭД",
        "ВЭД, таможня",
        "@proved_is_here",
        subscribers=18445,
    ),
    ChannelSeed(
        "centrved",
        "ЦентрВЭД (импорт, экспорт, таможня, логистика, сертификация, ВЭД)",
        "ВЭД, таможня",
        "@CentrVED",
        subscribers=11543,
    ),
    ChannelSeed("gruz0potok", "Грузопоток", "логистика", "@gruz0potok", subscribers=37051),
    ChannelSeed("logirus", "Logirus - №1 о логистике", "логистика", "@logirus", subscribers=6757),
    ChannelSeed(
        "transportandlogistic",
        "Транспорт и логистика",
        "логистика",
        "@transportandlogistic",
        subscribers=11093,
    ),
    ChannelSeed(
        "retail_ru",
        "Retail.ru - пишем о ритейле каждый день",
        "ритейл",
        "@retail_ru",
        subscribers=17806,
    ),
    ChannelSeed("retailrus", "Русский ритейл и бизнес", "ритейл", "@retailrus", subscribers=285585),
    ChannelSeed(
        "svobodakassa",
        "Свободная касса (ритейл & e-com)",
        "ритейл",
        "@svobodakassa",
        subscribers=31919,
    ),
    ChannelSeed(
        "inferno_retail",
        "Адский e-comm и ритейл",
        "ритейл",
        "@inferno_retail",
        subscribers=47950,
    ),
    ChannelSeed(
        "fintechassociation",
        "Ассоциация ФинТех",
        "банки, финтех",
        "@fintechassociation",
        subscribers=16164,
    ),
    ChannelSeed("frank_media", "Frank Media", "банки, финтех", "@frank_media", subscribers=32139),
    ChannelSeed("fintexno", "Финтехно", "банки, финтех", "@fintexno", subscribers=29771),
    ChannelSeed(
        "economicno",
        "Экономично | про банки и финтех",
        "банки, финтех",
        "@economicno",
        subscribers=55828,
    ),
    ChannelSeed(
        "fintex",
        "Русский финтех, е-ком и бизнес",
        "банки, финтех",
        "@fintex",
        subscribers=404565,
    ),
    ChannelSeed("mcx_ru", "Минсельхоз России", "АПК", "@mcx_ru", subscribers=30206),
    ChannelSeed(
        "agroinvestor",
        "Агроинвестор | Новости АПК",
        "АПК",
        "@agroinvestor",
        subscribers=14928,
    ),
    ChannelSeed("agro_nomika", "Агрономика", "АПК", "@agro_nomika", subscribers=37743),
    ChannelSeed("mcxae", "Агроэкспорт", "АПК", "@mcxae", subscribers=11110),
    ChannelSeed(
        "neftegazchannel",
        "Neftegaz.RU",
        "нефтегаз",
        "@neftegazchannel",
        subscribers=13467,
    ),
    ChannelSeed("papagaz", "Газ-Батюшка", "нефтегаз", "@papagaz", subscribers=108989),
    ChannelSeed(
        "oil_capital",
        "Нефть и Капитал I Новости Нефтегазовой отрасли",
        "нефтегаз",
        "@oil_capital",
        subscribers=22286,
    ),
    ChannelSeed("infotek_russia", "ИнфоТЭК", "нефтегаз", "@Infotek_Russia", subscribers=32770),
    ChannelSeed(
        "neftegazterritory",
        "Neftegaz Territory",
        "нефтегаз",
        "@neftegazterritory",
        subscribers=13698,
    ),
    ChannelSeed("nerzhavey", "Нержавейка", "металлургия", "@nerzhavey", subscribers=28570),
    ChannelSeed("prometallinfo", "ПРОметалл", "металлургия", "@prometallinfo", subscribers=10003),
    ChannelSeed(
        "metals_mining",
        "Металл и Минерал",
        "металлургия",
        "@Metals_Mining",
        subscribers=13368,
    ),
    ChannelSeed("rupec", "RUPEC", "химия", "@Rupec", subscribers=16954),
    ChannelSeed(
        "fertilizerdaily",
        "Fertilizer Daily",
        "химия",
        "@fertilizerdaily",
        subscribers=1160,
    ),
    ChannelSeed("coala_russia", "Coala", "уголь", "@Coala_Russia", subscribers=28713),
    ChannelSeed(
        "soyuzmash1",
        "Союз машиностроителей России",
        "машиностроение",
        "@soyuzmash1",
        subscribers=3311,
    ),
    ChannelSeed("uecrus_official", "ОДК", "машиностроение", "@uecrus_official", subscribers=24193),
    ChannelSeed(
        "protradein",
        "Самородов Про АвтоБизнес",
        "автобизнес",
        "@protradein",
        subscribers=34102,
    ),
    ChannelSeed("tourdom", "Крыша ТурДома", "туризм", "@tourdom", subscribers=80365),
    ChannelSeed(
        "tourismsafety",
        "Безопасность туризма",
        "туризм",
        "@tourismsafety",
        subscribers=9429,
    ),
    ChannelSeed("gkhnews", "ЖКХ Ньюс", "ЖКХ", "@gkhnews", subscribers=15047),
    ChannelSeed(
        "starshijpodomu",
        "Старший по дому | ЖКХ",
        "ЖКХ",
        "@starshijpodomu",
        subscribers=9521,
    ),
    ChannelSeed("dpilorama", "Деловая пилорама", "мебель", "@dpilorama", subscribers=2369),
    ChannelSeed("mebel_nom", "Интерьерный бизнес", "мебель", "@mebel_nom", subscribers=18331),
    ChannelSeed("industrymebel", "Индустрия мебели", "мебель", "@industrymebel", subscribers=2419),
    ChannelSeed("prayandsew", "Молиться и шить", "мода", "@prayandsew", subscribers=3644),
    ChannelSeed(
        "fashionprokachka",
        "Fashion прокачка",
        "мода",
        "@fashionprokachka",
        subscribers=11970,
    ),
    ChannelSeed(
        "daniyatkacheva",
        "Дания Ткачёва | Модный ритейл | Продажи | Стратегия",
        "мода",
        "@DaniyaTkacheva",
        subscribers=7018,
    ),
    ChannelSeed("sostav", "Sostav", "маркетинг, медиа", "@sostav", subscribers=56311),
    ChannelSeed("adindex", "AdIndex", "маркетинг, медиа", "@AdIndex", subscribers=31108),
    ChannelSeed("ftsec", "42 секунды", "IT, телеком", "@ftsec", subscribers=19377),
    ChannelSeed("t_bank_data", "T-Data", "IT, телеком", "@t_bank_data", subscribers=17283),
    ChannelSeed(
        "disruptors_official",
        "Дизраптор",
        "IT, телеком",
        "@disruptors_official",
        subscribers=72500,
    ),
    ChannelSeed("edtexno", "Эдтехно | образование", "образование", "@edtexno", subscribers=21369),
    ChannelSeed(
        "ru_education",
        "Образование, которое мы заслужили",
        "образование",
        "@ru_education",
        subscribers=42304,
    ),
    ChannelSeed("gxpnews", "GхP News", "фарма", "@gxpnews", subscribers=4303),
    ChannelSeed("bigbeautyboss", "Big Beauty Boss", "бьюти", "@bigbeautyboss", subscribers=89884),
    ChannelSeed(
        "rss_4e0d8db8964c",
        "Интерфакс",
        "политика, экономика",
        feed_url="https://www.interfax.ru/rss.asp",
        popularity=25,
    ),
    ChannelSeed(
        "rss_4a43cbef2ee4",
        "Взгляд",
        "политика, экономика",
        feed_url="https://vz.ru/rss.xml",
        popularity=200,
    ),
    ChannelSeed(
        "rss_1d8749c77f01",
        "Life.ru",
        "политика, экономика",
        feed_url="https://life.ru/xml/feed.xml",
        popularity=200,
    ),
    ChannelSeed(
        "rss_bc6605e004ce",
        "Рамблер/новости",
        "политика, экономика",
        feed_url="https://news.rambler.ru/rss/head/",
        popularity=100,
    ),
    ChannelSeed(
        "rss_cd597e8b8142",
        "Новости Mail",
        "политика, экономика",
        feed_url="https://news.mail.ru/rss/main/",
        popularity=16,
    ),
    ChannelSeed(
        "rss_82698e4cb420",
        "Российская газета",
        "политика, экономика",
        feed_url="https://rg.ru/xml/index.xml",
        popularity=100,
    ),
    ChannelSeed(
        "rss_77fc1e140d41",
        "Независимая газета",
        "политика, экономика",
        feed_url="https://www.ng.ru/rss/",
        popularity=100,
    ),
    ChannelSeed(
        "rss_57f88267eff4",
        "RT на русском",
        "политика, экономика",
        feed_url="https://russian.rt.com/rss",
        popularity=50,
    ),
    ChannelSeed(
        "rss_f6712c1dd13f",
        "Аргументы и Факты",
        "политика, экономика",
        feed_url="https://aif.ru/rss/all.php",
        popularity=225,
    ),
    ChannelSeed(
        "rss_687435db517d",
        "Комсомольская правда",
        "политика, экономика",
        feed_url="https://www.kp.ru/rss/allsections.xml",
        popularity=200,
    ),
    ChannelSeed(
        "rss_d727cfb0fd5d",
        "REGNUM",
        "политика, экономика",
        feed_url="https://regnum.ru/rss",
        popularity=239,
    ),
    ChannelSeed(
        "rss_739b250ab0c5",
        "Версия",
        "политика, экономика",
        feed_url="https://versia.ru/rss/index.xml",
        popularity=60,
    ),
    ChannelSeed(
        "rss_7931065bf780",
        "Утро.ру",
        "политика, экономика",
        feed_url="https://utro.ru/export/rss.xml",
        popularity=20,
    ),
    ChannelSeed(
        "rss_31ffde0b7096",
        "24СМИ",
        "политика, экономика",
        feed_url="https://24smi.org/rss/",
        popularity=30,
    ),
    ChannelSeed(
        "rss_0c05c006f73b",
        "Metro",
        "политика, экономика",
        feed_url="https://www.metronews.ru/services/materials/press/yandex/",
        popularity=185,
    ),
    ChannelSeed(
        "rss_7edfb52c1843",
        "Forbes.ru",
        "макро, рынки",
        feed_url="https://www.forbes.ru/newrss.xml",
        popularity=19,
    ),
    ChannelSeed(
        "rss_ce3e10954886",
        "Банки.ру",
        "макро, рынки",
        feed_url="https://www.banki.ru/xml/news.rss",
        popularity=25,
    ),
    ChannelSeed(
        "rss_06ded6b70066",
        "ПРАЙМ",
        "макро, рынки",
        feed_url="https://1prime.ru/export/rss2/index.xml",
        popularity=100,
    ),
    ChannelSeed(
        "rss_536984d225b8",
        "Финмаркет",
        "макро, рынки",
        feed_url="https://www.finmarket.ru/rss/mainnews.asp",
        popularity=20,
    ),
    ChannelSeed(
        "rss_ba3cfaa5b9c0",
        "BFM.ru",
        "макро, рынки",
        feed_url="https://www.bfm.ru/news.rss",
        popularity=50,
    ),
    ChannelSeed(
        "rss_a1693375c711",
        "Банк России — события",
        "макро, рынки",
        feed_url="https://www.cbr.ru/rss/eventrss",
        popularity=5,
    ),
    ChannelSeed(
        "rss_8aa4c6ce3e5b",
        "Финам",
        "макро, рынки",
        feed_url="https://www.finam.ru/analysis/conews/rsspoint/",
        popularity=100,
    ),
    ChannelSeed(
        "rss_8e3a39be7f5b",
        "Smart-Lab",
        "макро, рынки",
        feed_url="https://smart-lab.ru/rss/",
        popularity=20,
    ),
    ChannelSeed(
        "rss_3a547b37999c",
        "Investing.com Россия",
        "макро, рынки",
        feed_url="https://ru.investing.com/rss/news.rss",
        popularity=10,
    ),
    ChannelSeed(
        "rss_de8a1e95c102",
        "МК — Экономика",
        "макро, рынки",
        feed_url="https://www.mk.ru/rss/economics/index.xml",
        popularity=43,
    ),
    ChannelSeed(
        "rss_b9662626acdf",
        "Профиль",
        "макро, рынки",
        feed_url="https://profile.ru/feed/",
        popularity=50,
    ),
    ChannelSeed(
        "rss_bcdfe7ff41af",
        "Bits.media",
        "макро, рынки",
        feed_url="https://bits.media/rss2/",
        popularity=30,
    ),
    ChannelSeed(
        "rss_ad539527d2ce",
        "ФНС России",
        "налоги, право",
        feed_url="https://www.nalog.gov.ru/rn77/rss/",
        popularity=4,
    ),
    ChannelSeed(
        "rss_a71a930d9b3a",
        "Право.ру",
        "налоги, право",
        feed_url="https://pravo.ru/rss/",
        popularity=25,
    ),
    ChannelSeed(
        "rss_3de75035bc45",
        "ALTA.ru — законодательство",
        "налоги, право",
        feed_url="https://www.alta.ru/rss/laws_news/",
        popularity=6,
    ),
    ChannelSeed(
        "rss_5efe15516235",
        "ALTA.ru — внешнеэкономические новости",
        "налоги, право",
        feed_url="https://www.alta.ru/rss/external_news/",
        popularity=10,
    ),
    ChannelSeed(
        "rss_ba7b635b6d13",
        "БИЗНЕС Online",
        "регионы",
        feed_url="https://www.business-gazeta.ru/rss.xml",
        popularity=69,
    ),
    ChannelSeed(
        "rss_2019fdea4b27",
        "Фонтанка",
        "регионы",
        feed_url="https://www.fontanka.ru/rss-feeds/rss.xml",
        popularity=100,
    ),
    ChannelSeed(
        "rss_930ea3831216",
        "Деловой Петербург",
        "регионы",
        feed_url="https://www.dp.ru/exportnews.xml",
        popularity=100,
    ),
    ChannelSeed(
        "rss_2ec1294808bf",
        "Агентство Бизнес Новостей",
        "регионы",
        feed_url="https://abn.agency/feed/",
        popularity=10,
    ),
    ChannelSeed(
        "rss_a2d7ae716ff9",
        "Сибирское агентство новостей",
        "регионы",
        feed_url="https://sibnovosti.ru/rss/",
        popularity=100,
    ),
    ChannelSeed(
        "rss_a025f3925a48",
        "66.ру (Екатеринбург)",
        "регионы",
        feed_url="https://66.ru/news/rss/",
        popularity=25,
    ),
    ChannelSeed(
        "rss_633eb77d9b92",
        "74.ру (Челябинск)",
        "регионы",
        feed_url="https://74.ru/rss-feeds/rss.xml",
        popularity=100,
    ),
    ChannelSeed(
        "rss_4e7ac46282d9",
        "72.ру (Тюмень)",
        "регионы",
        feed_url="https://72.ru/rss-feeds/rss.xml",
        popularity=100,
    ),
    ChannelSeed(
        "rss_a01133d7f06f",
        "59.ру (Пермь)",
        "регионы",
        feed_url="https://59.ru/rss-feeds/rss.xml",
        popularity=100,
    ),
    ChannelSeed(
        "rss_9a317da1bfa4",
        "63.ру (Самара)",
        "регионы",
        feed_url="https://63.ru/rss-feeds/rss.xml",
        popularity=100,
    ),
    ChannelSeed(
        "rss_fe24f3ee8351",
        "161.ру (Ростов-на-Дону)",
        "регионы",
        feed_url="https://161.ru/rss-feeds/rss.xml",
        popularity=100,
    ),
    ChannelSeed(
        "rss_7811a994fc07",
        "Trend",
        "внешние рынки",
        feed_url="https://www.trend.az/feeds/index.rss",
        popularity=25,
    ),
    ChannelSeed(
        "rss_4483145134ef",
        "Anadolu Ajansı",
        "внешние рынки",
        feed_url="https://www.aa.com.tr/tr/rss/default?cat=guncel",
        popularity=30,
    ),
    ChannelSeed(
        "rss_82a636041ff9",
        "Daily Sabah — Business",
        "внешние рынки",
        feed_url="https://www.dailysabah.com/rss/business",
        popularity=34,
    ),
    ChannelSeed(
        "rss_b71db42bec2c",
        "Hürriyet Daily News — Economy",
        "внешние рынки",
        feed_url="https://www.hurriyetdailynews.com/rss/economy",
        popularity=58,
    ),
    ChannelSeed(
        "rss_70ddde36811c",
        "Азия-Плюс",
        "внешние рынки",
        feed_url="https://asiaplus.news/feed/",
        popularity=30,
    ),
    ChannelSeed(
        "rss_8d55c37cdee4",
        "Tazabek",
        "внешние рынки",
        feed_url="https://www.tazabek.kg/rss/",
        popularity=20,
    ),
    ChannelSeed(
        "rss_fe7ecaa9535f",
        "Vesti.kg",
        "внешние рынки",
        feed_url="https://vesti.kg/rss.html",
        popularity=50,
    ),
    ChannelSeed(
        "rss_72a34d9ad64e",
        "Podrobno.uz",
        "внешние рынки",
        feed_url="https://podrobno.uz/rss/",
        popularity=30,
    ),
    ChannelSeed(
        "rss_b9a3643dac5a",
        "Sputnik Азербайджан",
        "внешние рынки",
        feed_url="https://az.sputniknews.ru/export/rss2/archive/index.xml",
        popularity=100,
    ),
    ChannelSeed(
        "rss_8052206466fb",
        "Кошелёк Onlíner",
        "внешние рынки",
        feed_url="https://money.onliner.by/feed",
        popularity=18,
    ),
    ChannelSeed(
        "rss_d23d16ea6711",
        "EADaily",
        "внешние рынки",
        feed_url="https://eadaily.com/ru/rss/index.xml",
        popularity=30,
    ),
    ChannelSeed(
        "rss_b60f07f55bfe",
        "DW на русском",
        "внешние рынки",
        feed_url="https://rss.dw.com/rdf/rss-ru-all",
        popularity=38,
    ),
    ChannelSeed(
        "rss_87c09ea99ddb",
        "Euronews по-русски",
        "внешние рынки",
        feed_url="https://ru.euronews.com/rss",
        popularity=50,
    ),
    ChannelSeed(
        "rss_86e5ca3c7b87",
        "Financial Times",
        "мировая пресса",
        feed_url="https://www.ft.com/rss/home/international",
        popularity=11,
    ),
    ChannelSeed(
        "rss_2d7ac3b21662",
        "The Economist — Finance & economics",
        "мировая пресса",
        feed_url="https://www.economist.com/finance-and-economics/rss.xml",
        popularity=6,
    ),
    ChannelSeed(
        "rss_3f776f78a13e",
        "BBC — Business",
        "мировая пресса",
        feed_url="https://feeds.bbci.co.uk/news/business/rss.xml",
        popularity=38,
    ),
    ChannelSeed(
        "rss_70f2f3a3f196",
        "CNBC — Top News",
        "мировая пресса",
        feed_url="https://www.cnbc.com/id/100003114/device/rss/rss.html",
        popularity=30,
    ),
    ChannelSeed(
        "rss_13718dd2d4ab",
        "The New York Times — Business",
        "мировая пресса",
        feed_url="https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        popularity=49,
    ),
    ChannelSeed(
        "rss_c6f763ab48a3",
        "The Guardian — Business",
        "мировая пресса",
        feed_url="https://www.theguardian.com/uk/business/rss",
        popularity=39,
    ),
    ChannelSeed(
        "rss_df1d388d5efd",
        "MarketWatch",
        "мировая пресса",
        feed_url="https://feeds.content.dowjones.io/public/rss/mw_topstories",
        popularity=10,
    ),
    ChannelSeed(
        "rss_43adf952551a",
        "Forbes — Business",
        "мировая пресса",
        feed_url="https://www.forbes.com/business/feed2/",
        popularity=25,
    ),
    ChannelSeed(
        "rss_3ac92b73be87",
        "Business Insider",
        "мировая пресса",
        feed_url="https://feeds.feedburner.com/businessinsider",
        popularity=50,
    ),
    ChannelSeed(
        "rss_b45aafdc4981",
        "Los Angeles Times — Business",
        "мировая пресса",
        feed_url="https://www.latimes.com/business/rss2.0.xml",
        popularity=23,
    ),
    ChannelSeed(
        "rss_ea6c557e882a",
        "South China Morning Post — Business",
        "мировая пресса",
        feed_url="https://www.scmp.com/rss/92/feed",
        popularity=50,
    ),
    ChannelSeed(
        "rss_ecd16e1ec9b8",
        "Al Jazeera",
        "мировая пресса",
        feed_url="https://www.aljazeera.com/xml/rss/all.xml",
        popularity=25,
    ),
    ChannelSeed(
        "rss_b0887a201a6d",
        "Агентство нефтегазовой информации",
        "сырьё, энергетика",
        feed_url="https://angi.ru/rss/yandex.xml",
        popularity=50,
    ),
    ChannelSeed(
        "rss_49730295e413",
        "OilPrice.com",
        "сырьё, энергетика",
        feed_url="https://oilprice.com/rss/main",
        popularity=15,
    ),
    ChannelSeed(
        "rss_15a0bde23046",
        "Rigzone",
        "сырьё, энергетика",
        feed_url="https://www.rigzone.com/news/rss/rigzone_latest.aspx",
        popularity=20,
    ),
    ChannelSeed(
        "rss_50e0f2dffe5a",
        "MINING.COM",
        "сырьё, энергетика",
        feed_url="https://www.mining.com/feed/",
        popularity=36,
    ),
    ChannelSeed(
        "rss_8e967943f30c",
        "World Grain",
        "сырьё, энергетика",
        feed_url="https://www.world-grain.com/rss/articles",
        popularity=27,
    ),
    ChannelSeed(
        "rss_e0ff41bbd5ff",
        "Элек.ру",
        "сырьё, энергетика",
        feed_url="https://www.elec.ru/news/feed.xml",
        popularity=15,
    ),
    ChannelSeed(
        "rss_c5aa1e7a57ce",
        "ЦАМТО",
        "сырьё, энергетика",
        feed_url="https://armstrade.org/export/news.xml",
        popularity=50,
    ),
    ChannelSeed(
        "rss_6082b7d50482",
        "Unipack.ru",
        "сырьё, энергетика",
        feed_url="https://unipack.ru/rss/rss.xml",
        popularity=60,
    ),
    ChannelSeed(
        "rss_45d78c2bf206",
        "RZD-Partner",
        "логистика",
        feed_url="https://www.rzd-partner.ru/news/xml.php",
        popularity=157,
    ),
    ChannelSeed(
        "rss_7565b840c16c",
        "ALTA.ru — логистика",
        "логистика",
        feed_url="https://www.alta.ru/rss/logistics_news/",
        popularity=10,
    ),
    ChannelSeed(
        "rss_8a6cc18366c4",
        "Hellenic Shipping News",
        "логистика",
        feed_url="https://www.hellenicshippingnews.com/feed/",
        popularity=20,
    ),
    ChannelSeed(
        "rss_9f13b6b0f35b",
        "Splash247",
        "логистика",
        feed_url="https://splash247.com/feed/",
        popularity=10,
    ),
    ChannelSeed(
        "rss_3998eff936a9",
        "New Retail",
        "ритейл, авто, фарма",
        feed_url="https://new-retail.ru/rss/",
        popularity=120,
    ),
    ChannelSeed(
        "rss_18db781a8958",
        "Drom.ru — новости",
        "ритейл, авто, фарма",
        feed_url="https://www.drom.ru/cached_files/xml/news.rss",
        popularity=8,
    ),
    ChannelSeed(
        "rss_b07deaefcc86",
        "Колёса.ру",
        "ритейл, авто, фарма",
        feed_url="https://www.kolesa.ru/export/rss.xml",
        popularity=15,
    ),
    ChannelSeed(
        "rss_96c57f77dd26",
        "Vademecum",
        "ритейл, авто, фарма",
        feed_url="https://vademec.ru/rss/",
        popularity=20,
    ),
    ChannelSeed(
        "rss_08f248048bce",
        "Advertology.ru",
        "ритейл, авто, фарма",
        feed_url="https://www.advertology.ru/rss/complete.xml",
        popularity=8,
    ),
    ChannelSeed(
        "rss_35c243d81219",
        "AdVesti.ru",
        "ритейл, авто, фарма",
        feed_url="https://advesti.ru/exp/rss_lent.php",
        popularity=14,
    ),
    ChannelSeed(
        "rss_28ab18c52372",
        "Учительская газета",
        "ритейл, авто, фарма",
        feed_url="https://ug.ru/feed/",
        popularity=65,
    ),
    ChannelSeed(
        "rss_8cebc8e0cd3b",
        "CNews",
        "IT, телеком",
        feed_url="https://www.cnews.ru/inc/rss/news.xml",
        popularity=167,
    ),
    ChannelSeed(
        "rss_a93dd29b9963",
        "TAdviser",
        "IT, телеком",
        feed_url="https://www.tadviser.ru/xml/tadviser.xml",
        popularity=50,
    ),
    ChannelSeed(
        "rss_54c6dec307d8",
        "ComNews",
        "IT, телеком",
        feed_url="https://www.comnews.ru/rss",
        popularity=11,
    ),
    ChannelSeed(
        "rss_6670492faecb",
        "vc.ru",
        "IT, телеком",
        feed_url="https://vc.ru/rss/all",
        popularity=12,
    ),
    ChannelSeed(
        "rss_fc1452976af0",
        "Хабр — лучшее за неделю",
        "IT, телеком",
        feed_url="https://habr.com/ru/rss/articles/top/weekly/?fl=ru",
        popularity=40,
    ),
    ChannelSeed(
        "rss_542bac2eca81",
        "3DNews",
        "IT, телеком",
        feed_url="https://3dnews.ru/news/rss/",
        popularity=61,
    ),
    ChannelSeed(
        "rss_90d0f78e28c3",
        "iXBT.com",
        "IT, телеком",
        feed_url="https://www.ixbt.com/export/news.rss",
        popularity=50,
    ),
    ChannelSeed(
        "rss_cf6e652c190b",
        "SecurityLab.ru",
        "IT, телеком",
        feed_url="https://www.securitylab.ru/_services/export/rss/",
        popularity=100,
    ),
    ChannelSeed(
        "rss_bf137f744a51",
        "Компьютерра",
        "IT, телеком",
        feed_url="https://www.computerra.ru/feed/",
        popularity=235,
    ),
    ChannelSeed(
        "rss_c42fa48e9a7f",
        "OpenNet",
        "IT, телеком",
        feed_url="https://www.opennet.ru/opennews/opennews_all_noadv.rss",
        popularity=36,
    ),
    ChannelSeed(
        "rss_7829040e90c9",
        "devby.io",
        "IT, телеком",
        feed_url="https://devby.io/rss",
        popularity=30,
    ),
    ChannelSeed(
        "rss_2f536dad5739",
        "Comss.one",
        "IT, телеком",
        feed_url="https://www.comss.ru/rss.php",
        popularity=10,
    ),
    ChannelSeed(
        "rss_e8d31cec2893",
        "The Verge",
        "IT, телеком",
        feed_url="https://www.theverge.com/rss/index.xml",
        popularity=10,
    ),
    ChannelSeed(
        "rss_480604124173",
        "Naked Science",
        "IT, телеком",
        feed_url="https://naked-science.ru/feed",
        popularity=20,
    ),
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
HTTP_RE = re.compile(r"^https?://", re.IGNORECASE)


def parse_handle(value: str) -> str | None:
    text = (value or "").strip()
    match = HANDLE_RE.match(text) or AT_RE.match(text)
    return f"@{match.group(1)}" if match else None


def _is_public_host(host: str | None) -> bool:
    if not host:
        return False
    lowered = host.lower()
    if lowered == "localhost" or lowered.endswith(".local"):
        return False
    try:
        address = ip_address(lowered)
    except ValueError:
        return True
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
    )


def parse_feed_url(value: str) -> str | None:
    text = (value or "").strip()
    if not HTTP_RE.match(text) or parse_handle(text):
        return None
    if not _is_public_host(urlparse(text).hostname):
        return None
    return text


def rss_channel_id(url: str) -> str:
    return "rss_" + hashlib.sha1(url.encode()).hexdigest()[:12]


def find_channel(value: str) -> ChannelSeed | None:
    text = (value or "").strip().lower()
    if not text:
        return None
    handle = parse_handle(value)
    feed_url = parse_feed_url(value)
    for item in CHANNELS:
        if text in {item.id.lower(), item.name.lower(), (item.handle or "").lower()}:
            return item
        if handle and item.handle and item.handle.lower() == handle.lower():
            return item
        if feed_url and item.feed_url and item.feed_url.lower() == feed_url.lower():
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
