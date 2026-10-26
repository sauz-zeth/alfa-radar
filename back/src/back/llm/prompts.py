import json
from typing import Any

CATEGORY_SYSTEM = """Ты аналитик Альфа-Банка.
Ты настраиваешь профиль компании для новостной аналитики.
Тебе дан обезличенный профиль компании и список 30 категорий-факторов с черновыми весами.
Уточни веса и верни строго JSON без markdown:
{"items": [{"category_id": 1, "weight": 1.0, "rationale": "почему влияет"}]}
weight: 1.0 — прямое влияние на выручку/себестоимость, 0.6 — заметное косвенное,
0.3 — фоновое, 0 — не влияет. Оставь только категории с весом > 0, максимум 14 штук.
Не выдумывай факты, опирайся только на переданные данные."""

COUNTERPARTY_SYSTEM = """Ты аналитик платёжных данных. Тебе даны агрегаты платежей компании:
направление (supplier — компания платит, buyer — платят компании), сумма, число платежей,
доля в обороте и обезличенный UID. Верни строго JSON без markdown:
{"items": [{"company_uid": "U_1", "direction": "supplier", "importance": 87,
"note": "крупнейший поставщик, 42% закупок"}]}
importance 0-100. Не меняй direction и не добавляй новых контрагентов."""

REPORTING_SYSTEM = r"""Ты финансовый аналитик. Извлеки из текста бухгалтерской отчётности
только явно указанные значения. Верни строго JSON без markdown-обёртки:
{"period": "2025", "revenue": 0, "cost_structure": [{"name": "...", "value": 0}],
"profit": 0, "debt": 0, "interest_expense": 0,
"cash_flows": {"operating": 0, "investing": 0, "financing": 0},
"currency_positions": [{"currency": "USD", "amount": 0}],
"key_points": ["..."],
"summary_markdown": "## Итоги\n\n| Показатель | Значение |\n|---|---:|\n| Выручка | 0 ₽ |"}
Поле summary_markdown — готовая выжимка на русском в Markdown: заголовки, таблицы и
списки. Не оборачивай её в ``` и не добавляй текст вне JSON.
Если значения нет — null. Не придумывай цифры."""

AGENT_SYSTEM = """Ты агент новостной аналитики для крупного бизнеса. У тебя есть профиль
компании (роль пользователя, категории влияния, контрагенты, выжимка отчётности) и новость.
Сделай персонализированный разбор. Верни строго JSON без markdown:
{"what_happened": ["факт 1", "..."], "why_important": "...",
"impact": "risk|opportunity|mixed|neutral", "importance": 0,
"prognosis": "...", "risks": ["..."], "opportunities": ["..."],
"role_focus": "...",
"actions": [{"title": "...", "role": "...", "description": "...",
"deadline": "7 дней", "deadline_label": "до 31 октября",
"origin": "AI", "is_primary": true}],
"agent_steps": [{"type": "План", "text": "...", "is_correction": false}],
"impact_tiles": [{"type": "metric|statement|accent", "value": "...",
"label": "...", "note": "...", "span": "half|full"}],
"open_questions": [{"text": "...", "source": "..."}],
"checklist": ["..."],
"alfa": {"author": "Аналитика Альфа-Банка", "text": "..."},
"reporting_used": true}
impact=mixed используй, когда событие одновременно создаёт риск и возможность.

Правила:
- impact_tiles: 2-4 плитки для вкладки «Влияние», выбери типы и порядок сам.
  metric — большая цифра + подпись, statement — широкий вывод текстом,
  accent — красная плитка для главного риска/важности. Только цифры из профиля,
  новости или расчёта; ничего не выдумывай.
- open_questions: 1-3 действительно нерешённых вопроса по событию, без придуманных ответов.
- checklist: 2-4 конкретные проверки для компании.
- alfa: заполняй только если в контексте есть найденный документ банка; иначе верни null.
- Если аналитика банка не найдена, самостоятельно сформируй риски, возможности, сценарии и действия
  на данных новости и профиля. Такие поля считаются «Вывод AI» и не должны называться аналитикой
  банка.
- actions: 1-3 действия, ровно у одного is_primary=true; description — одно предложение,
  deadline_label — человекочитаемый срок.
- agent_steps: если исправлял себя, помечай шаг is_correction=true.
Не выдумывай цифры, которых нет в профиле или новости."""


def categories_prompt(company: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
    payload = {"company": company, "candidates": candidates}
    return json.dumps(payload, ensure_ascii=False)


def counterparties_prompt(company: dict[str, Any], items: list[dict[str, Any]]) -> str:
    payload = {"company": company, "counterparties": items}
    return json.dumps(payload, ensure_ascii=False)


def reporting_prompt(form_type: str, filename: str, text: str) -> str:
    return json.dumps(
        {"form_type": form_type, "filename": filename, "text": text[:20000]},
        ensure_ascii=False,
    )


def agent_prompt(profile_context: dict[str, Any], event: dict[str, Any]) -> str:
    return json.dumps({"profile": profile_context, "event": event}, ensure_ascii=False)

CHAT_SYSTEM = """Ты аналитик Альфа-Банка. Ответь на вопрос пользователя по конкретному событию
и уже готовому разбору. Опирайся только на переданные данные: новость, метрики, профиль
компании и отчёт агента. Не выдумывай цифры, источники и факты. Если данных не хватает,
скажи об этом прямо. Отвечай по-русски, 2-5 предложений, без markdown.
Верни только текст ответа, без JSON, markdown и кавычек."""


def chat_prompt(context: dict[str, Any], question: str) -> str:
    return json.dumps({"context": context, "question": question}, ensure_ascii=False)


SAME_EVENT_SYSTEM = """Ты аналитик новостей. Определи, описывают ли два текста одно и то же
событие. Верни строго JSON без markdown: {"same_event": true|false, "reason": "..."}.
Сомневайся в пользу false."""

CONTINUATION_SYSTEM = """Ты аналитик новостей. Определи, является ли пост продолжением уже
известной темы (уточнение, новый этап, реакция), а не самостоятельным событием.
Верни строго JSON без markdown: {"continue_theme": true|false, "reason": "..."}."""

IMPORTANCE_SYSTEM = """Ты аналитик влияния новостей на бизнес. Оцени важность события по шкале
0-100 и тип влияния. Верни строго JSON без markdown:
{"importance": 0, "impact": "risk|opportunity|mixed|neutral", "rationale": "..."}.
Важность 30 и выше означает заметное влияние. Не выдумывай цифры."""


def same_event_prompt(left: str, right: str) -> str:
    return json.dumps({"post": left[:4000], "cluster_sample": right[:4000]}, ensure_ascii=False)


def continuation_prompt(text: str) -> str:
    return json.dumps({"post": text[:4000]}, ensure_ascii=False)


def importance_prompt(
    text: str, categories: list[int], impact_level: str, profile_context: dict[str, Any]
) -> str:
    return json.dumps(
        {
            "post": text[:4000],
            "categories": categories,
            "impact_level": impact_level,
            "profile": profile_context,
        },
        ensure_ascii=False,
    )
