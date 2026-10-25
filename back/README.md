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
uv run python scripts/seed_demo_tracked.py
uv run uvicorn back.main:app --reload
```

API: `http://localhost:8000`, Swagger: `http://localhost:8000/docs`.

Если данные лежат не в `back/data`, укажите путь:

```bash
uv run python scripts/seed.py --reset --data-dir "/tmp/alfadata/Данные для участников"
```

`seed_demo_tracked.py` добавляет демо-темы, цепочки событий и вопросы для `demo_full`
(идемпотентно, можно запускать повторно).

### 15 демо-профилей бизнесов

`seed_15_profiles.py` разворачивает в чистой базе 15 пользователей `demo1`…`demo15`
(пароль `demo`) с готовыми профилями: компания, цифры, категории, контрагенты.
Скрипт сам применяет миграции, сеет справочники, 60 синтетических компаний и платежи,
поэтому его можно запускать первым на пустой базе. Повторный запуск идемпотентен.

```bash
uv run python scripts/seed_15_profiles.py
# пароль по умолчанию demo, миграции уже применены:
uv run python scripts/seed_15_profiles.py --skip-migrations --password demo
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

Для дропдауна онбординга есть отдельная ручка:

```http
GET /api/businesses/options?search=&limit=15
```

- без `search` — 15 репрезентативных компаний из разных отраслей (не 85k);
- с `search` — поиск по всем компаниям (UID, город, регион, ОКВЭД), до 50 результатов;
- ответ содержит `mode: "featured" | "search"`, `items` и `total`.

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
  весами категорий профиля и упоминаниями контрагентов. Поддерживает `impact`, `category`, `q`,
  `include_hidden` и `include_tracked`.
- `GET /api/feed/{id}` — детали события: источники-слайды, факты, разбивка важности,
  тезисы, сравнение источников, аналитика банка, сценарии, вопросы, действия и журнал агента.
- `GET /api/feed/hidden?tab=stale|weak|skipped` — «Скрытые»: устаревшие, слабое влияние и
  пропущенные; `POST /api/feed/{id}/restore` возвращает новость в ленту.
- `POST /api/feed/{id}/like` — поставить/снять отметку «нравится».
- `POST /api/feed/{id}/track` — добавляет событие в «Отслеживаемое» и запускает агента.
- `POST /api/feed/{id}/feedback` — `track`, `skip`, `important`, `not_relevant` + причина.
- `GET /api/feed/{id}/scenarios?horizon=3m|6m|12m` — сценарный расчёт (детерминированная заглушка).
- `GET /api/tracked?status=active|archived|all`, `GET /api/tracked/{id}`,
  `DELETE /api/tracked/{id}`, `POST /api/tracked/{id}/reanalyze`.
- `POST /api/tracked/{id}/questions` — свой вопрос к истории.
- `POST /api/tracked/{id}/archive`, `POST /api/tracked/{id}/resume` — архив и возобновление.

### Источники

- `GET /api/sources` — подписки профиля; при первом обращении подписывает на 15 рекомендаций.
- `GET /api/sources/catalog?q=` — поиск по каталогу и пользовательским каналам.
- `POST /api/sources/channels` — добавить свой источник: `@тег`, `t.me`-ссылка или
  URL RSS/Atom-ленты (`http://` / `https://`).
- `POST /api/sources/channels/{id}/subscribe`, `DELETE /api/sources/channels/{id}`,
  `POST /api/sources/channels/unsubscribe-all`, `POST /api/sources/channels/restore`.

Каталог и рекомендации лежат в `core/sources.py` как сид: 93 Telegram-канала и
100 RSS-лент. Пользовательские источники создаются в таблице `channels`
(`kind = custom`, RSS определяется по `meta.feed_url`). Ответы `CHANNEL_OUT` содержат
`source_type` (`telegram` / `rss`), `avatar_url` и закэшированное число подписчиков
`tg_subscribers`. RSS пользовательских и каталожных подписок опрашивается фоновым
заданием (`RSS_POLL_ENABLED`, `RSS_POLL_INTERVAL_SECONDS`). Подробности — в
[`docs/Sources-Migration.md`](../docs/Sources-Migration.md).

### Поиск

- `GET /api/search?q=` — новости и компании (своя компания, контрагенты, база).
- `GET /api/search/history`, `DELETE /api/search/history`,
  `DELETE /api/search/history/{id}` — история до 10 запросов.

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
LLM_BASE_URL=https://your-gateway/v1
LLM_API_KEY=...
LLM_MODEL=...
LLM_FAST_MODEL=...
LLM_AGENT_ENABLED=true  # LLM для разбора события
LLM_ML_ENABLED=false    # категории/контрагенты/отчётность пока детерминированные
```

- `base.py` — контракт `BaseLLM`, парсинг JSON, ошибки `LLMError` / `LLMBudgetExceeded`.
- `stub.py` — офлайн-провайдер. Ничего не выдумывает: вызывает переданный детерминированный
  fallback, посчитанный по данным компании/платежам/тексту отчётности.
- `openai_compatible.py` — HTTP-клиент к `/chat/completions`, обработка 402/429 и ошибок шлюза.
- `factory.py` — точка выбора провайдера. **Менять провайдера/добавлять новый нужно здесь.**
- `prompts.py` — все системные промпты (категории, контрагенты, отчётность, агент).

Задачи и модели задаются через `LLM_MODEL` и `LLM_FAST_MODEL`. Бюджетный лимит обрабатывается
мягко: при ошибке LLM сервис отдаёт детерминированный fallback, а не падает.
Для пайплайна есть роли: `LLM_WEAK_MODEL` (по умолчанию `LLM_FAST_MODEL`) и
`LLM_STRONG_MODEL` (по умолчанию `LLM_MODEL`). Пустое значение = откат к старым переменным.

ML-обучения в проекте нет: старый pipeline/классификатор удалён. Всё, что можно заменить
моделью позже, вынесено в `llm/` и `services/` (категории, контрагенты, отчётность, агент).
По умолчанию LLM включён только для агента (`LLM_AGENT_ENABLED=true`); ML-подобные
подсказки категорий/контрагентов и извлечение отчётности остаются детерминированными,
пока не выставлен `LLM_ML_ENABLED=true`.

Агент возвращает в отчёте `impact_tiles` — упорядоченный JSON плиток для вкладки «Влияние»:
`type` (`metric` / `statement` / `accent`), `value`, `label`, `note`, `span` (`half` / `full`).
Если плиток нет, бэкенд строит их из `impact_metrics`.

## Pipeline

Пост принимается через `POST /api/ingest/posts` (внутренний endpoint, опционально защищён
`X-Ingest-Token`, см. `INGEST_TOKEN`). Пайплайн сохраняет каждый пост и все решения в таблицу
`posts` (`raw`, `parsed`, `categories`, `embedding`, `cluster_key`, `news_event_id`,
`status`, `stage`, `decision_trace`). События отслеживаемых тем получают
`news_events.is_feed_visible = false`, поэтому в ленту не попадают, но открываются по прямой
ссылке `/api/feed/{id}`.

Этапы и ветки:

1. **parse** — нормализует `title/text/source/url/published_at`, чистит HTML, выводит заголовок
   из текста, принимает ISO/человеческие даты, отсутствующие поля не ломают приём.
2. **classify** — `services/ml.py`: stub-классификатор категорий (ключевой лексикон) и
   детерминированный hashed-эмбеддинг (64 измерения). Интерфейс `PostClassifier` — точка
   замены на ruBERT/e5.
3. **cluster** — косинус к центроидам существующих кластеров (центроид считается на лету по
   последним постам, без отдельной таблицы). `>= 0.85` — «Источник кластера», LLM не
   вызывается; `0.75–0.85` — weak-модель отвечает на «То же событие?»; `< 0.75` — новый
   кластер. Пороги: `SAME_CLUSTER_THRESHOLD`, `AMBIGUOUS_CLUSTER_THRESHOLD`.
4. **continuation** — weak-модель «Продолжение темы?». Да → пост отслеживается
   (`TrackedItem`, в ленту не идёт), но только если передан `profile_id`; без профиля решение
   пишется в trace, сущности не создаются.
5. **influence** — только при переданном `profile_id`: уровень `none | indirect | direct` по
   категориям поста и весам категорий профиля (прямое влияние — вес `>= 0.8`). `none` —
   пост игнорируется. `indirect` → weak-модель, `direct` → strong-модель. Оценка важности
   `I` и короткое обоснование сохраняются в `posts` и `NewsEvent`.
6. **routing** — `I >= 30` → `NewsEvent` попадает в ленту; `I < 30` → событие создаётся, но
   скрывается существующей логикой «Слабое влияние» (`/api/feed/hidden?tab=weak`).

Почему так: кластеризация и «продолжение темы» глобальны для поста, а влияние — свойство
профиля. Для демо влияние считается для одного явно переданного `profile_id`; без него
пайплайн останавливается после кластеризации и сохраняет глобальный trace. Полный fan-out по
всем активным профилям — следующий шаг.

Сейчас заглушки (детерминированные, без сети): категории, эмбеддинги, решения weak/strong.
При `LLM_ML_ENABLED=false` (по умолчанию) вызываются офлайн-fallback; при `true` те же
функции идут в `get_llm()` с ролями weak/strong. Пороги и точка замены ML — только в
`services/pipeline.py` и `services/ml.py`.

Пример:

```bash
curl -s -X POST http://127.0.0.1:8000/api/ingest/posts \
  -H 'Content-Type: application/json' \
  -d '{"title":"ЦБ повысил ставку","text":"Регулятор повысил ключевую ставку до 21%.",
       "source":"ЦБ РФ","published_at":"2026-10-24T10:00:00Z"}'

curl -s http://127.0.0.1:8000/api/ingest/posts/<post_id>
```

### RSS/Atom

`services/rss.py` читает RSS 2.0 и Atom через `httpx` (stdlib `ElementTree`, без новых
зависимостей), чистит HTML, нормализует даты и отправляет каждый новый пост в тот же
пайплайн. Дубли отсекаются по `url`. Фоновый поллер (`services/rss_poller.py`) сам
опрашивает RSS-источники, на которые подписаны пользователи, раз в
`RSS_POLL_INTERVAL_SECONDS`; включается через `RSS_POLL_ENABLED`.

```bash
# URL из RSS_FEEDS (.env, через запятую) или аргументами
uv run python scripts/ingest_rss.py
uv run python scripts/ingest_rss.py https://example.com/rss https://example.com/atom
```

### Telegram

Отдельный подсервис `tg-ingest/` логинится в Telegram как обычный аккаунт (Telethon),
периодически забирает `GET /api/ingest/channels`, подписывает твинка на каналы с
подписчиками (`subscribers > 0`) и шлёт новые посты в этот же `POST /api/ingest/posts`
с `X-Ingest-Token`. Запуск, вход по номеру/коду и хранение сессии — в
[`tg-ingest/README.md`](../tg-ingest/README.md).

Каталог Telegram-каналов — 93 реальных источника из
[`docs/ТГ_каналы_для_новостной_аналитики_кейс_Альфа_Банка_1.md`](../docs/ТГ_каналы_для_новостной_аналитики_кейс_Альфа_Банка_1.md);
ещё 100 RSS-лент — из
[`docs/RSS_ленты_для_новостной_аналитики_кейс_Альфа_Банка.md`](../docs/RSS_ленты_для_новостной_аналитики_кейс_Альфа_Банка.md).
Аватарки и счётчики подписчиков кэшируются подсервисом:

- `GET /api/ingest/channels` — все активные Telegram-каналы с `handle`, числом подписчиков
  в системе и закэшированным `tg_subscribers`;
- `PUT /api/ingest/channels/{channel_id}/avatar` — тело `image/jpeg|png|webp` до 2 МБ,
  `X-Ingest-Token`; файл сохраняется в `src/back/static/avatars`, а URL пишется в
  `channels.meta.avatar_url`;
- `PUT /api/ingest/channels/{channel_id}/stats` — `{ "subscribers": 123 }` обновляет
  `channels.meta.tg_subscribers`;
- `GET /api/sources` и `/api/sources/catalog` отдают `avatar_url`, `source_type` и
  `tg_subscribers` для фронта.

### Ленивый разбор события

`GET /api/feed/{id}` при первом открытии строит отчёт агента (LLM при
`LLM_AGENT_ENABLED=true`, иначе детерминированный fallback) и сохраняет его в
`event_analyses` по паре `profile_id + event_id`. Повторные открытия, сценарии и чат
читают кэш; `POST /track` переиспользует тот же отчёт.

## API

Все защищённые ручки — `Authorization: Bearer <token>`.

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET /api/businesses`, `GET /api/businesses/options`, `GET /api/businesses/{uid}`
- `/api/onboarding/*` — см. выше
- `GET/PATCH /api/profile` — профиль, статистика компании, группы категорий и контрагенты.
  Дополнительно: `PATCH /api/profile/notifications`.
- `GET/PATCH /api/profile/categories`, `GET/PATCH /api/profile/counterparties`,
  `GET/POST /api/profile/reporting`
- `/api/feed/*`, `/api/tracked/*`, `/api/sources/*`, `/api/search/*`
- `GET /health`, `GET /health/db`

## Модель данных

`users`, `companies`, `payments`, `person_company_links`, `business_profiles`, `categories`,
`business_categories`, `counterparties`, `reporting_uploads`, `news_events`, `tracked_items`,
`feedback`, `event_likes`, `channels`, `profile_channels`.

Профиль привязан к бизнесу пользователя; роль хранится в `business_profiles.role`.
Категории, контрагенты и отчётность — часть профиля. Имена контрагентов по умолчанию
«Поставщик N» / «Покупатель N», переименование хранится в `custom_name`.
Источники: `channels` — каталог и кастомные каналы, `profile_channels` — подписки профиля.
Старый JSONB `business_profiles.sources` оставлен только для обратной совместимости.

## Разработка

```bash
uv run ruff check src scripts tests
uv run ruff format --check src scripts tests
uv run pytest -q
uv run alembic revision --autogenerate -m "change"
uv run alembic upgrade head
```

`tests/test_api_mockup.py` — интеграционный тест сценариев из макетов (лента, скрытые,
источники, поиск, отслеживаемое, профиль). Он поднимает схему в отдельной БД и по умолчанию
использует `postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/alfafuture_test`.
Другую БД можно указать через `TEST_DATABASE_URL`; без доступного Postgres тест пропускается.

## Ограничения прототипа

- Новости засеяны демо-набором; парсер Telegram/официальных источников не входит в этот этап.
- Аналитика Альфа-Банка и RAG не подключены — оставлены как следующий слой.
- Обратная связь сохраняется, но не пересчитывает персональные веса (это следующий этап).
- Сценарии, сравнение источников и часть разбора — детерминированные заглушки вместо ML/LLM.
- Outlook смоделирован: подключение, черновики, отправка, статусы и напоминания работают
  на демо-провайдере (состояние в `business_profiles.outlook_state`); Microsoft Graph
  не подключён. Парсер Telegram и RAG по аналитике банка не входят в этот этап.

## Отчёты

- [`docs/Auth-Onboarding-Report.md`](../docs/Auth-Onboarding-Report.md) — проверка авторизации и онбординга.
