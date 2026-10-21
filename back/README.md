# Backend — новостная аналитика для КИБ

FastAPI-бэкенд сервиса: авторизация, онбординг бизнеса по обезличенным данным Альфа-Банка,
персонализированная лента событий и отслеживаемые разборы с учётом роли пользователя и отчётности.

## Стек

- Python 3.14 + [uv](https://docs.astral.sh/uv/)
- FastAPI + Pydantic v2
- SQLAlchemy 2 (async) + asyncpg
- PostgreSQL 17 (alpine)
- Alembic
- JWT (PyJWT) + Argon2

## Быстрый запуск

```bash
cd back
cp .env.example .env
podman-compose up -d postgres      # или: docker compose up -d postgres
uv sync --all-groups
uv run alembic upgrade head
uv run python scripts/seed.py --reset
uv run uvicorn back.main:app --reload
```

API: `http://localhost:8000`, Swagger: `http://localhost:8000/docs`.

Если данные лежат не в `back/data`, укажите путь:

```bash
uv run python scripts/seed.py --reset --data-dir "/tmp/alfadata/Данные для участников"
```

Скрипт seed сам находит `/tmp/alfadata/Данные для участников`, если `--data-dir` не задан.
Флаги: `--limit N` — ограничить число компаний, `--skip-payments` — не грузить 1.38M платежей,
`--reset` — очистить таблицы перед загрузкой.

### Импорт произвольных CSV

`scripts/import_csv.py` принимает файлы или каталоги и сам определяет тип по заголовку:

```bash
uv run python scripts/import_csv.py "/tmp/alfadata/Данные для участников"
uv run python scripts/import_csv.py df_Uid_data_hack.csv df_Fid_Uid_link_hack.csv
uv run python scripts/import_csv.py path/to/file.csv --limit 5000 --skip-payments
```

Поддерживаются все три файла кейса:

| Файл | Таблица |
| --- | --- |
| `df_Uid_data_hack.csv` | `companies` (upsert по UID) |
| `df_Uid_payment_hack.csv` | `payments` |
| `df_Fid_Uid_link_hack.csv` | `person_company_links` (связи физлиц и компаний) |

Компании и связи идемпотентны. Платежи не имеют естественного ключа, поэтому по умолчанию
не перезаписываются, если таблица не пуста; для перезагрузки — `--replace-payments`.
Связи можно перезагрузить через `--replace-person-links`.

### Docker

```bash
cd back
docker compose up --build
```

`api` применяет миграции при старте. Seed нужно запустить отдельно (из хоста, пока порт 5432
опубликован) или выполнить `docker compose run --rm api python scripts/seed.py --reset`.

## Демо-учётки

| Логин | Пароль | Что показывает |
| --- | --- | --- |
| `demo` | `demo` | чистый пользователь, проходит весь онбординг |
| `demo_full` | `demo` | заполненный профиль (CFO, категории, контрагенты) — сразу лента и «Отслеживаемое» |

## Данные

После seed в БД:

- 85 514 компаний из `df_Uid_data_hack.csv` (дубликаты UID схлопнуты);
- 1 382 585 платежей из `df_Uid_payment_hack.csv`;
- 12 514 связей физлиц с компаниями из `df_Fid_Uid_link_hack.csv`;
- 30 категорий-факторов;
- 27 демо-новостей, включая события типа `mixed` (одновременно риск и возможность).

Компания выбирается по UID и показывает город, регион, сегмент по выручке, ОКВЭД, сотрудников,
возраст, ВЭД-страну, продукты банка и теги. Список поддерживает поиск и фильтры:
`GET /api/businesses?search=&city=&segment=&okved=&product=&fts=&min_revenue=&max_revenue=`.

## Онбординг

7 шагов, значения по умолчанию можно пропустить:

1. `POST /api/auth/register` или `POST /api/auth/login` — логин/пароль.
2. `POST /api/onboarding/business` `{ "uid": "U_..." }` — выбор бизнеса.
3. `PATCH /api/onboarding/profile` — имя предпринимателя и название бизнеса
   (по умолчанию `Иван Иванов` / `Моя компания`). Пропуск: `POST /api/onboarding/skip` `{ "step": "profile_filled" }`.
4. `POST /api/onboarding/role` — роль (`owner`, `ceo`, `cfo`, `chief_accountant`, `treasurer`,
   `c_level`, `other_decision_maker`). Роль сохраняется в профиле бизнеса и передаётся агенту.
5. `GET /api/onboarding/counterparties` — поставщики/покупатели по платежам, важность и доля.
   Переименование: `PATCH /api/onboarding/counterparties`.
6. `POST /api/onboarding/categories/suggest` — отраслевые + общие категории с весами
   `1.0 / 0.6 / 0.3`. Правка: `PATCH /api/onboarding/categories/{id}`.
7. `POST /api/onboarding/reporting` (multipart: `balance`, `income`, `cash_flow`) — баланс,
   ОФР, ДДС. Поддерживаются `.txt`, `.csv`, `.pdf`, `.xlsx`. LLM извлекает период, выручку,
   долг, проценты, денежные потоки и ключевые тезисы в `reporting_summary`.
   Пропуск: `POST /api/onboarding/skip` `{ "step": "reporting_uploaded" }`.

Состояние: `GET /api/onboarding/state`; завершение: `POST /api/onboarding/complete`.

## Лента и «Отслеживаемое»

- `GET /api/feed` — персонализированная важность: базовая важность события корректируется
  весами категорий профиля и упоминаниями контрагентов. Поддерживает `impact`, `category`, `q`.
- `GET /api/feed/{id}` — детали события.
- `POST /api/feed/{id}/track` — добавляет событие в «Отслеживаемое» и запускает агента.
- `POST /api/feed/{id}/feedback` — `track`, `skip`, `important`, `not_relevant`.
- `GET /api/tracked`, `GET /api/tracked/{id}`, `DELETE /api/tracked/{id}`,
  `POST /api/tracked/{id}/reanalyze`.

Тип влияния: `risk`, `opportunity`, `mixed`, `neutral`. Для `mixed` карточка одновременно
показывает риски и возможности.

Пометка «(!)» отдаётся в каждом элементе ленты:

```json
{
  "prognosis_note": "При детальном разборе во вкладке «Отслеживаемое» прогноз может уточниться",
  "detail_note": "(!) При детальном разборе во вкладке «Отслеживаемое» прогноз может уточниться"
}
```

Фронтенд показывает `(!)` рядом с цифрой и этот текст при наведении/тапе.

Агент при разборе получает роль пользователя, категории, контрагентов и выжимку отчётности.
Роль меняет акценты и действия: казначею — ликвидность и валютные позиции, главбуху — налоги
и отчётность, собственнику — стоимость бизнеса и стратегические риски. Если отчётность загружена,
в отчёте `reporting_used = true`, а прогноз может отличаться от оценки в ленте.

## LLM layer

Весь LLM-слой изолирован в `src/back/llm/` и переключается одной переменной:

```env
LLM_PROVIDER=stub   # offline, без вызовов
LLM_PROVIDER=openai # любой OpenAI-compatible gateway
```

- `base.py` — контракт `BaseLLM`, парсинг JSON, ошибки `LLMError` / `LLMBudgetExceeded`.
- `stub.py` — офлайн-провайдер. Ничего не выдумывает: вызывает переданный детерминированный
  fallback, посчитанный по данным компании/платежам/тексту отчётности.
- `openai_compatible.py` — HTTP-клиент к `/chat/completions`, обработка 402/429 и ошибок шлюза.
- `factory.py` — точка выбора провайдера. **Менять провайдера/добавлять новый нужно здесь.**
- `prompts.py` — все системные промпты (категории, контрагенты, отчётность, агент).

Задачи и модели задаются через `LLM_MODEL` и `LLM_FAST_MODEL`. Бюджетный лимит обрабатывается
мягко: при ошибке LLM сервис отдаёт детерминированный fallback, а не падает.

ML-обучения в проекте нет: старый pipeline/классификатор удалён. Всё, что можно заменить
моделью позже, вынесено в `llm/` и `services/` (категории, контрагенты, отчётность, агент).

## API

Все защищённые ручки — `Authorization: Bearer <token>`.

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET /api/businesses`, `GET /api/businesses/{uid}`
- `/api/onboarding/*` — см. выше
- `GET/PATCH /api/profile`, `GET/PATCH /api/profile/categories`,
  `GET/PATCH /api/profile/counterparties`, `GET/POST /api/profile/reporting`
- `/api/feed/*`, `/api/tracked/*`
- `GET /health`, `GET /health/db`

## Модель данных

`users`, `companies`, `payments`, `person_company_links`, `business_profiles`, `categories`,
`business_categories`, `counterparties`, `reporting_uploads`, `news_events`, `tracked_items`,
`feedback`.

Профиль привязан к бизнесу пользователя; роль хранится в `business_profiles.role`.
Категории, контрагенты и отчётность — часть профиля. Имена контрагентов по умолчанию
«Поставщик N» / «Покупатель N», переименование хранится в `custom_name`.

## Разработка

```bash
uv run ruff check src scripts tests
uv run ruff format --check src scripts tests
uv run pytest -q
uv run alembic revision --autogenerate -m "change"
uv run alembic upgrade head
```

## Ограничения прототипа

- Новости засеяны демо-набором; парсер Telegram/официальных источников не входит в этот этап.
- Аналитика Альфа-Банка и RAG не подключены — оставлены как следующий слой.
- Обратная связь сохраняется, но не пересчитывает персональные веса (это следующий этап).

## Отчёты

- [`docs/Auth-Onboarding-Report.md`](../docs/Auth-Onboarding-Report.md) — проверка авторизации и онбординга.
