from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

NOW = datetime.now(UTC)


def _post(
    name: str,
    *,
    hours: int,
    tone: str,
    text: str,
    image: str,
    url: str | None = None,
    primary: bool = False,
) -> dict:
    return {
        "name": name,
        "time": (NOW - timedelta(hours=hours)).isoformat(),
        "tone": tone,
        "text": text,
        "is_primary": primary,
        "url": url,
        "image_url": f"/static/news/{image}",
    }


DEMO_EVENTS = [
    {
        "slug": "metal-export-duty",
        "title": "Повышены экспортные пошлины на металлопродукцию",
        "summary": (
            "Правительство повысило ставки экспортных пошлин на горячекатаный прокат и "
            "арматуру. Новые ставки действуют с 1 ноября до конца года."
        ),
        "what_it_means": (
            "Для экспортёров металла снижается маржа: часть контрактов уже заключена по "
            "старым ценам. Внутренним потребителям металла пошлина даёт больше предложения "
            "и давление на цены вниз."
        ),
        "source_name": "Правительство РФ",
        "source_url": "https://government.ru/docs/",
        "published_at": NOW - timedelta(hours=3),
        "importance": 92,
        "impact": "risk",
        "category_ids": [4, 15],
        "chain_key": "metals-duty",
        "facts": [
            {"text": "Пошлина вступает в силу с 1 ноября.", "status": "Официально"},
            {"text": "Ставка выросла с 5% до 7% для проката.", "status": "Официально"},
            {"text": "Мера действует до конца года.", "status": "Официально"},
        ],
        "impact_metrics": [
            {
                "key": "ebitda",
                "label": "EBITDA в год",
                "value": "−1,2 млрд ₽",
                "previous_value": "−0,9 млрд ₽",
                "note": "при доле экспорта 38%",
                "tone": "negative",
            },
            {
                "key": "export",
                "label": "Экспорт под пошлиной",
                "value": "4,6 млрд ₽",
                "previous_value": "≈60%",
                "note": "контракты IV квартала",
                "tone": None,
            },
            {
                "key": "rate",
                "label": "Ставка пошлины",
                "value": "7%",
                "previous_value": "5%",
                "note": "вместо прежней ставки",
                "tone": "negative",
            },
        ],
        "source_posts": [
            _post(
                "Правительство РФ",
                hours=3,
                tone="official",
                text=(
                    "Подписано постановление о повышении ставок экспортных пошлин на "
                    "отдельные виды металлопродукции."
                ),
                image="steel.jpg",
                url="https://government.ru/docs/",
                primary=True,
            ),
            _post(
                "Деловой вестник",
                hours=4,
                tone="media",
                text=(
                    "Участники рынка оценивают потери экспортёров в 1,2 млрд ₽ EBITDA "
                    "в год при текущей доле экспорта."
                ),
                image="publication.jpg",
                url="https://www.vedomosti.ru/business",
            ),
            _post(
                "Металл-Инсайд",
                hours=5,
                tone="telegram",
                text="Под пошлину попадают контракты IV квартала на 4,6 млрд ₽.",
                image="logistics.jpg",
                url="https://t.me/metals_inside",
            ),
        ],
    },
    {
        "slug": "metal-duty-update",
        "title": "Минпромторг уточнил параметры экспортной пошлины",
        "summary": (
            "Ведомство разъяснило, что пошлина не распространяется на часть сортамента "
            "и на поставки в страны ЕАЭС."
        ),
        "what_it_means": (
            "Уточнение частично снимает риск для производителей, работающих в ЕАЭС. "
            "Экспортным контрактам в дальнее зарубежье пересмотр не поможет."
        ),
        "source_name": "Минпромторг",
        "source_url": "https://minpromtorg.gov.ru/",
        "published_at": NOW - timedelta(hours=20),
        "importance": 74,
        "impact": "mixed",
        "category_ids": [4, 15],
        "chain_key": "metals-duty",
        "update_label": "Обновлено: уточнены сроки",
        "facts": [
            {"text": "Поставки в ЕАЭС под пошлину не попадают.", "status": "Официально"},
            {"text": "Разъяснение опубликовано 22 октября.", "status": "Официально"},
        ],
        "impact_metrics": [
            {
                "key": "ebitda",
                "label": "EBITDA в год",
                "value": "−0,7 млрд ₽",
                "previous_value": "−1,18 млрд ₽",
                "note": "уточнённая оценка эффекта",
                "tone": "negative",
            },
            {
                "key": "export",
                "label": "Экспорт под пошлиной",
                "value": "2 из 9",
                "previous_value": "≈60%",
                "note": "позиций сортамента исключены",
                "tone": "positive",
            },
        ],
        "source_posts": [
            _post(
                "Минпромторг",
                hours=20,
                tone="official",
                text="Опубликованы разъяснения по применению пошлины к отдельным видам проката.",
                image="steel.jpg",
                url="https://minpromtorg.gov.ru/",
                primary=True,
            ),
            _post(
                "Интерфакс",
                hours=21,
                tone="media",
                text="Ведомство уточнило сроки и перечень исключений.",
                image="publication.jpg",
                url="https://www.interfax.ru/business/",
            ),
        ],
    },
    {
        "slug": "iron-ore-price",
        "title": "Железная руда подорожала на 8% за месяц",
        "summary": (
            "Рост цен поддерживается спросом металлургов и ограничениями поставок из "
            "крупных добывающих регионов."
        ),
        "what_it_means": (
            "Для металлурга-покупателя сырья это риск себестоимости, для производителя "
            "руды — возможность улучшить маржу."
        ),
        "source_name": "Металлы и руды",
        "source_url": "https://metals-mining.ru/",
        "published_at": NOW - timedelta(hours=9),
        "importance": 71,
        "impact": "mixed",
        "category_ids": [15],
        "facts": [
            {"text": "Цена выросла на 8% за месяц.", "status": "Пишут несколько каналов"},
            {"text": "Спрос со стороны металлургов остаётся высоким.", "status": "Оценка"},
        ],
        "impact_metrics": [
            {"value": "+8%", "note": "Цена руды\nза месяц", "tone": "positive"},
            {
                "value": "−0,3 млрд ₽",
                "note": "Себестоимость проката\nпри текущих запасах",
                "tone": "negative",
            },
        ],
        "source_posts": [
            _post(
                "Металлы и руды",
                hours=9,
                tone="media",
                text="Котировки железной руды обновили локальный максимум.",
                image="steel.jpg",
                url="https://metals-mining.ru/",
                primary=True,
            ),
            _post(
                "Металл-Инсайд",
                hours=10,
                tone="telegram",
                text="Металлурги фиксируют рост закупочных цен на сырьё.",
                image="publication.jpg",
                url="https://t.me/metals_inside",
            ),
        ],
    },
    {
        "slug": "rzd-tariffs",
        "title": "РЖД проиндексировали тарифы на грузовые перевозки",
        "summary": (
            "Индексация на 10% затрагивает ключевые номенклатуры грузов и вступает в силу "
            "с нового месяца."
        ),
        "what_it_means": (
            "Логистические расходы вырастут. Компаниям с длинными поставками нужно "
            "пересчитать себестоимость и условия контрактов."
        ),
        "source_name": "РЖД",
        "source_url": "https://www.rzd.ru/",
        "published_at": NOW - timedelta(hours=14),
        "importance": 78,
        "impact": "risk",
        "category_ids": [20, 4],
        "chain_key": "rzd-tariffs",
        "update_label": "Обновлено: уточнены сроки индексации",
        "facts": [
            {"text": "Тарифы проиндексированы на 10%.", "status": "Официально"},
            {"text": "Мера вступает в силу с 1 ноября.", "status": "Официально"},
        ],
        "impact_metrics": [
            {
                "value": "−0,4 млрд ₽",
                "note": "Логистика на восток\nпри росте тарифа",
                "tone": "negative",
            },
            {"value": "12 дней", "note": "Средний срок доставки\nдо портов", "tone": None},
            {"value": "+10%", "note": "Индексация\nгрузового тарифа", "tone": "negative"},
        ],
        "source_posts": [
            _post(
                "РЖД",
                hours=14,
                tone="official",
                text="Опубликовано решение об индексации тарифов на грузовые перевозки.",
                image="logistics.jpg",
                url="https://www.rzd.ru/",
                primary=True,
            ),
            _post(
                "РЖД-Партнёр",
                hours=15,
                tone="media",
                text="Перевозчики ожидают роста издержек в восточном направлении.",
                image="publication.jpg",
                url="https://www.rzd-partner.ru/",
            ),
            _post(
                "Грузопоток",
                hours=16,
                tone="telegram",
                text="Участники рынка пересматривают контракты на IV квартал.",
                image="steel.jpg",
                url="https://t.me/gruzpotok",
            ),
        ],
    },
    {
        "slug": "cb-rate-14",
        "title": "ЦБ сохранил ключевую ставку на уровне 14%",
        "summary": (
            "Банк России сохранил ключевую ставку 14% и отметил, что риторика остаётся "
            "жёсткой. Следующее заседание — через шесть недель."
        ),
        "what_it_means": (
            "Стоимость нового заёмного финансирования не снизится. Для компании с кредитным "
            "портфелем это риск по процентным расходам, но депозитная подушка может принести "
            "больше дохода."
        ),
        "source_name": "Банк России",
        "source_url": "https://www.cbr.ru/press/",
        "published_at": NOW - timedelta(hours=26),
        "importance": 88,
        "impact": "mixed",
        "category_ids": [1, 23],
        "chain_key": "cb-rate",
        "facts": [
            {"text": "Ключевая ставка сохранена на уровне 14% годовых.", "status": "Официально"},
            {"text": "Риторика регулятора стала жёстче.", "status": "Официально"},
            {"text": "Следующее заседание — через шесть недель.", "status": "Официально"},
        ],
        "impact_metrics": [
            {"value": "14%", "note": "Ключевая ставка\nбез изменений", "tone": None},
            {
                "value": "−0,9 млрд ₽",
                "note": "Процентные расходы\nза 12 месяцев",
                "tone": "negative",
            },
            {
                "value": "+1,1 млрд ₽",
                "note": "Доход по депозитам\nпри текущей подушке",
                "tone": "positive",
            },
        ],
        "source_posts": [
            _post(
                "Банк России",
                hours=26,
                tone="official",
                text="Совет директоров принял решение сохранить ключевую ставку на уровне 14%.",
                image="rate.jpg",
                url="https://www.cbr.ru/press/",
                primary=True,
            ),
            _post(
                "Интерфакс",
                hours=27,
                tone="media",
                text="Регулятор сигнализирует о длительном периоде жёсткой ДКП.",
                image="fx.jpg",
                url="https://www.interfax.ru/business/",
            ),
            _post(
                "Экономика и банки",
                hours=28,
                tone="telegram",
                text="Банки не ожидают снижения ставок по кредитам до конца года.",
                image="publication.jpg",
                url="https://t.me/ekonomika_banki",
            ),
        ],
    },
    {
        "slug": "sanctions-package",
        "title": "ЕС расширил санкционный список против российских компаний",
        "summary": (
            "В новый пакет вошли ограничения на оборудование и несколько юридических лиц. "
            "ЕС также ужесточил контроль за обходом ограничений."
        ),
        "what_it_means": (
            "Возможны дополнительные комплаенс-проверки и удлинение цепочек поставок. "
            "Нужно проверить контрагентов и импортные позиции."
        ),
        "source_name": "Reuters",
        "source_url": "https://www.reuters.com/world/europe/",
        "published_at": NOW - timedelta(hours=32),
        "importance": 83,
        "impact": "risk",
        "category_ids": [3, 12],
        "facts": [
            {
                "text": "Пакет включает ограничения на оборудование.",
                "status": "Пишут несколько каналов",
            },
            {"text": "В список вошли несколько юридических лиц.", "status": "Официально"},
        ],
        "impact_metrics": [
            {"value": "+18%", "note": "Срок поставки\nоборудования", "tone": "negative"},
            {
                "value": "3 позиции",
                "note": "Импортных контракта\nпод проверкой",
                "tone": "negative",
            },
        ],
        "source_posts": [
            _post(
                "Reuters",
                hours=32,
                tone="media",
                text="Евросоюз утвердил новый пакет ограничений против российских компаний.",
                image="sanctions.jpg",
                url="https://www.reuters.com/world/europe/",
                primary=True,
            ),
            _post(
                "РБК",
                hours=33,
                tone="media",
                text="В пакет вошли ограничения на оборудование и логистические сервисы.",
                image="it.jpg",
                url="https://www.rbc.ru/politics/",
            ),
            _post(
                "Комплаенс-канал",
                hours=34,
                tone="telegram",
                text="Участники рынка начали проверку контрагентов из нового списка.",
                image="publication.jpg",
                url="https://t.me/compliance_channel",
            ),
        ],
    },
    {
        "slug": "tax-deadlines",
        "title": "ФНС уточнила сроки уплаты налогов в четвёртом квартале",
        "summary": "Ведомство опубликовало разъяснения по переносу сроков и порядку уведомлений.",
        "what_it_means": (
            "Изменения требуют проверки календаря платежей. Для главного бухгалтера это "
            "возможность заранее перестроить график и избежать пеней."
        ),
        "source_name": "ФНС России",
        "source_url": "https://www.nalog.gov.ru/rn77/news/",
        "published_at": NOW - timedelta(hours=38),
        "importance": 68,
        "impact": "opportunity",
        "category_ids": [5, 6],
        "facts": [
            {"text": "Опубликованы разъяснения по срокам.", "status": "Официально"},
            {"text": "Перенос касается отдельных уведомлений.", "status": "Официально"},
        ],
        "impact_metrics": [
            {"value": "2 недели", "note": "Запас на подготовку\nуведомлений", "tone": "positive"},
            {"value": "0 ₽", "note": "Пеней при оплате\nв новые сроки", "tone": "positive"},
        ],
        "source_posts": [
            _post(
                "ФНС России",
                hours=38,
                tone="official",
                text="Опубликованы разъяснения о порядке и сроках уплаты налогов в IV квартале.",
                image="taxes.jpg",
                url="https://www.nalog.gov.ru/rn77/news/",
                primary=True,
            ),
            _post(
                "Гарант",
                hours=40,
                tone="media",
                text="Эксперты отметили, что часть сроков переносится на две недели.",
                image="publication.jpg",
                url="https://www.garant.ru/news/",
            ),
            _post(
                "Налоги и учёт",
                hours=41,
                tone="telegram",
                text="Бухгалтерам советуют проверить календарь платежей до 1 ноября.",
                image="rate.jpg",
                url="https://t.me/nalogi_uchet",
            ),
        ],
    },
    {
        "slug": "fsbu-lease",
        "title": "Утверждён новый ФСБУ по аренде",
        "summary": "Стандарт меняет порядок признания обязательств по аренде и раскрытие информации.",
        "what_it_means": "Потребуется пересмотр учётной политики и оценка влияния на отчётность.",
        "source_name": "Минфин России",
        "source_url": "https://minfin.gov.ru/ru/document/",
        "published_at": NOW - timedelta(hours=44),
        "importance": 66,
        "impact": "risk",
        "category_ids": [6, 9],
        "facts": [
            {"text": "Стандарт утверждён.", "status": "Официально"},
            {"text": "Обязательное применение — с 2027 года.", "status": "Официально"},
        ],
        "impact_metrics": [
            {
                "value": "+0,6 млрд ₽",
                "note": "Обязательства\nпо аренде в балансе",
                "tone": "negative",
            },
            {"value": "1 раз", "note": "Пересмотр учётной\nполитики", "tone": None},
        ],
        "source_posts": [
            _post(
                "Минфин России",
                hours=44,
                tone="official",
                text="Приказ об утверждении нового ФСБУ по аренде опубликован.",
                image="leasing.jpg",
                url="https://minfin.gov.ru/ru/document/",
                primary=True,
            ),
            _post(
                "КонсультантПлюс",
                hours=45,
                tone="media",
                text="Стандарт потребует пересмотра договоров аренды и раскрытий.",
                image="rate.jpg",
                url="https://www.consultant.ru/",
            ),
        ],
    },
    {
        "slug": "rub-usd",
        "title": "Рубль ослаб к юаню и доллару на фоне оттока капитала",
        "summary": "Курс рубля снизился к основным валютам, волатильность выросла.",
        "what_it_means": (
            "Для экспортёра ослабление рубля поддерживает выручку, для импортёра — "
            "увеличивает стоимость закупок. Влияние смешанное, зависит от валютной позиции."
        ),
        "source_name": "Ведомости",
        "source_url": "https://www.vedomosti.ru/market",
        "published_at": NOW - timedelta(hours=48),
        "importance": 79,
        "impact": "mixed",
        "category_ids": [2, 13],
        "facts": [
            {"text": "Волатильность валютного рынка выросла.", "status": "Пишут несколько каналов"},
            {"text": "Экспортёры увеличили продажу валютной выручки.", "status": "Оценка"},
        ],
        "impact_metrics": [
            {"value": "+2,4%", "note": "Курс юаня\nк рублю за неделю", "tone": "negative"},
            {"value": "+0,8 млрд ₽", "note": "Валютная выручка\nэкспортёра", "tone": "positive"},
        ],
        "source_posts": [
            _post(
                "Ведомости",
                hours=48,
                tone="media",
                text="Рубль ослаб к юаню и доллару на фоне роста оттока капитала.",
                image="fx.jpg",
                url="https://www.vedomosti.ru/market",
                primary=True,
            ),
            _post(
                "Банк России",
                hours=49,
                tone="official",
                text="Регулятор отмечает повышенную волатильность на валютном рынке.",
                image="rate.jpg",
                url="https://www.cbr.ru/press/",
            ),
            _post(
                "Валюта и рынки",
                hours=50,
                tone="telegram",
                text="Импортёры пересчитывают закупки по новому курсу.",
                image="publication.jpg",
                url="https://t.me/currency_markets",
            ),
        ],
    },
    {
        "slug": "wheat-forecast",
        "title": "Прогноз урожая пшеницы снижен из-за засухи",
        "summary": "Аналитики ухудшили оценку урожая и ожидают роста цен на продовольствие.",
        "what_it_means": "Для переработчиков и ритейла растёт закупочная стоимость сырья.",
        "source_name": "Агроинвестор",
        "source_url": "https://www.agroinvestor.ru/",
        "published_at": NOW - timedelta(hours=76),
        "importance": 72,
        "impact": "risk",
        "category_ids": [18, 13],
        "facts": [
            {"text": "Прогноз урожая снижен.", "status": "Пишут несколько каналов"},
            {"text": "Засуха затронула южные регионы.", "status": "Официально"},
        ],
        "impact_metrics": [
            {"value": "−9%", "note": "Прогноз урожая\nк прошлому году", "tone": "negative"},
            {"value": "+6%", "note": "Закупочная цена\nпшеницы", "tone": "negative"},
        ],
        "source_posts": [
            _post(
                "Агроинвестор",
                hours=76,
                tone="media",
                text="Аналитики снизили прогноз урожая пшеницы из-за засухи в южных регионах.",
                image="agro.jpg",
                url="https://www.agroinvestor.ru/",
                primary=True,
            ),
            _post(
                "Минсельхоз",
                hours=77,
                tone="official",
                text="Ведомство подтвердило влияние засухи на отдельные регионы.",
                image="logistics.jpg",
                url="https://mcx.gov.ru/press-service/",
            ),
        ],
    },
    {
        "slug": "ai-law",
        "title": "Принят закон об ответственности за ИИ-контент",
        "summary": "Документ вводит требования к маркировке и раскрытию использования ИИ.",
        "what_it_means": "Возможны дополнительные комплаенс-требования к цифровым каналам.",
        "source_name": "ТАСС",
        "source_url": "https://tass.ru/ekonomika",
        "published_at": NOW - timedelta(hours=57),
        "importance": 64,
        "impact": "risk",
        "category_ids": [25, 23],
        "facts": [
            {"text": "Закон принят.", "status": "Официально"},
            {"text": "Требования к маркировке вступят в силу поэтапно.", "status": "Официально"},
        ],
        "impact_metrics": [
            {"value": "3 месяца", "note": "На доработку\nцифровых каналов", "tone": "negative"},
            {"value": "+12%", "note": "Стоимость\nконтент-процессов", "tone": "negative"},
        ],
        "source_posts": [
            _post(
                "ТАСС",
                hours=57,
                tone="media",
                text="Принят закон, вводящий ответственность за немаркированный ИИ-контент.",
                image="it.jpg",
                url="https://tass.ru/ekonomika",
                primary=True,
            ),
            _post(
                "Финтех-ассоциация",
                hours=58,
                tone="telegram",
                text="Участники рынка оценивают расходы на маркировку и аудит контента.",
                image="rate.jpg",
                url="https://t.me/fintechassociation",
            ),
            _post(
                "Sostav",
                hours=59,
                tone="media",
                text="Рекламный рынок готовится к новым требованиям к ИИ-креативам.",
                image="publication.jpg",
                url="https://www.sostav.ru/",
            ),
        ],
    },
    {
        "slug": "marketplace-returns",
        "title": "Маркетплейсам расширят требования к возвратам",
        "summary": "Новые правила упрощают возврат товаров и усиливают защиту покупателей.",
        "what_it_means": (
            "Для продавца растут операционные издержки и возвраты, для покупателя — доверие "
            "к онлайн-каналу. Влияние смешанное."
        ),
        "source_name": "Retail.ru",
        "source_url": "https://www.retail.ru/news/",
        "published_at": NOW - timedelta(hours=62),
        "importance": 67,
        "impact": "mixed",
        "category_ids": [22, 13],
        "facts": [
            {"text": "Требования к возвратам расширены.", "status": "Официально"},
            {"text": "Новые правила вступят в силу с января.", "status": "Официально"},
        ],
        "impact_metrics": [
            {"value": "+4%", "note": "Доля возвратов\nв онлайн-канале", "tone": "negative"},
            {"value": "−0,2 млрд ₽", "note": "Операционные\nиздержки в год", "tone": "negative"},
            {"value": "+3%", "note": "Конверсия\nповторных покупок", "tone": "positive"},
        ],
        "source_posts": [
            _post(
                "Retail.ru",
                hours=62,
                tone="media",
                text="Маркетплейсы готовятся к расширенным требованиям по возвратам товаров.",
                image="retail.jpg",
                url="https://www.retail.ru/news/",
                primary=True,
            ),
            _post(
                "Коммерсантъ",
                hours=63,
                tone="media",
                text="Новые правила затронут продавцов и логистических партнёров.",
                image="logistics.jpg",
                url="https://www.kommersant.ru/business",
            ),
            _post(
                "Ритейл-канал",
                hours=64,
                tone="telegram",
                text="Продавцы оценивают рост возвратов в 3–5%.",
                image="publication.jpg",
                url="https://t.me/retail_channel",
            ),
        ],
    },
    {
        "slug": "construction-mortgage",
        "title": "Льготная ипотека продлена с новыми лимитами",
        "summary": (
            "Программа продлена на год, но максимальная сумма кредита снижена для "
            "отдельных регионов."
        ),
        "what_it_means": (
            "Застройщики сохраняют спрос, однако высокие ставки по рыночной ипотеке "
            "сдерживают маржу. Стоит пересмотреть план продаж."
        ),
        "source_name": "ДОМ.РФ",
        "source_url": "https://дом.рф/media/",
        "published_at": NOW - timedelta(hours=68),
        "importance": 69,
        "impact": "mixed",
        "category_ids": [14, 1],
        "facts": [
            {"text": "Программа продлена на год.", "status": "Официально"},
            {"text": "Лимиты снижены для отдельных регионов.", "status": "Официально"},
        ],
        "impact_metrics": [
            {
                "value": "−5%",
                "note": "Спрос на новостройки\nв отдельных городах",
                "tone": "negative",
            },
            {"value": "+12%", "note": "Стоимость финансирования\nпроекта", "tone": "negative"},
            {"value": "1 год", "note": "Новый срок\nпрограммы", "tone": "positive"},
        ],
        "source_posts": [
            _post(
                "ДОМ.РФ",
                hours=68,
                tone="official",
                text="Опубликованы новые условия продления льготной ипотечной программы.",
                image="construction.jpg",
                url="https://дом.рф/media/",
                primary=True,
            ),
            _post(
                "Ведомости",
                hours=69,
                tone="media",
                text="Застройщики ожидают сохранения спроса при снижении лимитов.",
                image="leasing.jpg",
                url="https://www.vedomosti.ru/business",
            ),
            _post(
                "Строительный канал",
                hours=70,
                tone="telegram",
                text="Банки пересматривают условия выдачи ипотеки под новые лимиты.",
                image="rate.jpg",
                url="https://t.me/construction_channel",
            ),
        ],
    },
]


def _history_event(
    slug: str,
    *,
    chain_key: str,
    title: str,
    summary: str,
    days_ago: float,
    importance: int,
    impact: str,
    source_name: str,
    text: str,
) -> dict:
    published = NOW - timedelta(days=days_ago)
    return {
        "slug": slug,
        "title": title,
        "summary": summary,
        "what_it_means": summary,
        "source_name": source_name,
        "source_url": None,
        "published_at": published,
        "importance": importance,
        "impact": impact,
        "category_ids": [4, 15],
        "facts": [{"text": summary, "status": "Официально"}],
        "impact_metrics": [],
        "source_posts": [
            _post(
                source_name,
                hours=int(days_ago * 24),
                tone="official",
                text=text,
                image="steel.jpg",
                primary=True,
            )
        ],
        "chain_key": chain_key,
        "update_label": None,
    }


CHAIN_HISTORY = [
    _history_event(
        "metals-duty-1",
        chain_key="metals-duty",
        title="Правительство обсуждает экспортную пошлину на прокат",
        summary="Минфин предложил ввести пошлину 5% на экспорт плоского проката.",
        days_ago=21,
        importance=58,
        impact="mixed",
        source_name="Ведомости",
        text="Обсуждается временная пошлина на экспорт металлопроката.",
    ),
    _history_event(
        "metals-duty-2",
        chain_key="metals-duty",
        title="Введена экспортная пошлина на металлопрокат",
        summary="Правительство подписало постановление о пошлине 5% с 1 октября.",
        days_ago=17,
        importance=88,
        impact="risk",
        source_name="Правительство РФ",
        text="Пошлина вводится для защиты внутреннего рынка.",
    ),
    _history_event(
        "metals-duty-3",
        chain_key="metals-duty",
        title="Ставку пошлины повысили до 7%",
        summary="Минфин повысил ставку пошлины из-за роста мировых цен на прокат.",
        days_ago=13,
        importance=80,
        impact="risk",
        source_name="Минфин России",
        text="Ставка повышена с 5% до 7%.",
    ),
    _history_event(
        "metals-duty-4",
        chain_key="metals-duty",
        title="Экспортёры проката попросили пересмотреть пошлину",
        summary="Отраслевые ассоциации просят исключить подписанные контракты из-под пошлины.",
        days_ago=9,
        importance=64,
        impact="opportunity",
        source_name="Деловой вестник",
        text="Ассоциации направили обращение в правительство.",
    ),
    _history_event(
        "rzd-tariffs-1",
        chain_key="rzd-tariffs",
        title="РЖД предложили индексацию тарифов с декабря",
        summary="Монополия предложила повысить тарифы на 10% с декабря.",
        days_ago=12,
        importance=70,
        impact="risk",
        source_name="РЖД",
        text="Предложение направлено в ФАС.",
    ),
    _history_event(
        "rzd-tariffs-2",
        chain_key="rzd-tariffs",
        title="ФАС согласовала индексацию тарифов РЖД",
        summary="ФАС согласовала рост тарифов на грузовые перевозки.",
        days_ago=6,
        importance=74,
        impact="risk",
        source_name="ФАС",
        text="Решение согласовано с учётом социальных обязательств.",
    ),
    _history_event(
        "cb-rate-1",
        chain_key="cb-rate",
        title="Инфляция замедлилась до 6,8%",
        summary="Росстат зафиксировал замедление годовой инфляции.",
        days_ago=11,
        importance=62,
        impact="opportunity",
        source_name="Росстат",
        text="Инфляция замедлилась четвёртый месяц подряд.",
    ),
    _history_event(
        "cb-rate-2",
        chain_key="cb-rate",
        title="ЦБ сохранил ключевую ставку на уровне 14%",
        summary="Регулятор сохранил ставку и ужесточил риторику.",
        days_ago=5,
        importance=88,
        impact="mixed",
        source_name="Банк России",
        text="Ставка сохранена на уровне 14% годовых.",
    ),
]

DEMO_EVENTS.extend(CHAIN_HISTORY)

# Profile-specific demo stories: each chain spans several dates so the tracked view
# can show how the conclusion changed over time.
for _event in DEMO_EVENTS:
    _chain = {
        "marketplace-returns": "retail-returns",
        "ai-law": "software-ai",
        "construction-mortgage": "construction-demand",
    }.get(_event["slug"])
    if _chain:
        _event["chain_key"] = _chain

DEMO_EVENTS.extend(
    [
        _history_event(
            "retail-returns-1", chain_key="retail-returns", title="Маркетплейсы обсуждают единые правила возврата",
            summary="Крупные площадки предложили унифицировать сроки и порядок возврата товаров.", days_ago=18,
            importance=55, impact="mixed", source_name="АКИТ", text="Ритейл обсуждает единый стандарт возвратов."),
        _history_event(
            "retail-returns-2", chain_key="retail-returns", title="Введён расширенный срок возврата для покупателей",
            summary="Площадки согласовали расширенный срок возврата и новые требования к упаковке.", days_ago=11,
            importance=63, impact="risk", source_name="Роспотребнадзор", text="Новые требования опубликованы для продавцов."),
        _history_event(
            "software-ai-1", chain_key="software-ai", title="Проект правил для генеративного ИИ вынесен на обсуждение",
            summary="Регулятор предложил маркировать синтетический контент и хранить журналы генерации.", days_ago=20,
            importance=57, impact="mixed", source_name="Минцифры России", text="Проект правил опубликован для обсуждения."),
        _history_event(
            "software-ai-2", chain_key="software-ai", title="Компании готовят реестр моделей и журналирование",
            summary="ИТ-рынок оценивает затраты на аудит моделей и хранение запросов пользователей.", days_ago=12,
            importance=68, impact="risk", source_name="РБК", text="Разработчики готовят процессы контроля ИИ."),
        _history_event(
            "construction-demand-1", chain_key="construction-demand", title="Лимиты льготной ипотеки предложили сократить",
            summary="Правительство обсудило адресное сокращение лимитов по регионам.", days_ago=22,
            importance=58, impact="risk", source_name="ДОМ.РФ", text="Обсуждаются новые параметры программы."),
        _history_event(
            "construction-demand-2", chain_key="construction-demand", title="Застройщики пересчитали продажи по новым лимитам",
            summary="Девелоперы закладывают более длинный цикл сделки и рост стоимости проектного финансирования.", days_ago=14,
            importance=66, impact="risk", source_name="Коммерсантъ", text="Компании обновили планы продаж и финансирования."),
    ]
)


def seeded_events() -> list[dict]:
    result = []
    for event in DEMO_EVENTS:
        event = dict(event)
        event["id"] = uuid5(NAMESPACE_URL, f"alfa-future-demo-event-{event['slug']}")
        event["mentioned_company_uids"] = []
        event.setdefault("source_url", None)
        event.setdefault("source_posts", [])
        event.setdefault("impact_metrics", [])
        event.setdefault("chain_key", None)
        event.setdefault("update_label", None)
        result.append(event)
    return result
