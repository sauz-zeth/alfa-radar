# Источники: нормализация и план миграции

Документ для будущих сессий агента: что уже сделано, как устроены источники и как
подключать реальные сервисы (Telegram-парсер, поиск, ML), не ломая API.

**Актуальное состояние.** Каталог — 93 Telegram-канала и 100 RSS-лент из `docs/`.
Пользователь добавляет свой источник через `POST /api/sources/channels` (`@handle`,
`t.me`-ссылка или URL RSS). Telegram-каналы тянет `tg-ingest/` (подписка, посты,
аватарки, число подписчиков), RSS — фоновый `services/rss_poller.py` в бэкенде.
Аватарки хранятся в `src/back/static/avatars`, метаданные каналов — в `channels.meta`
(`feed_url`, `avatar_url`, `tg_subscribers`).

## Что уже сделано

Источники вынесены из `business_profiles.sources` (JSONB) в две таблицы:

- `channels` — каталог и пользовательские каналы;
- `profile_channels` — подписки профиля на каналы.

`core/sources.py` теперь играет роль **сида каталога и списка рекомендаций**:
`CHANNELS` — стартовый каталог, `RECOMMENDED_IDS` — 15 каналов, на которые
подписывается новый профиль. Пользовательские каналы в этот файл не попадают.

### `channels`

| Поле | Смысл |
| --- | --- |
| `id` | стабильный id: slug каталога (`metall-inside`) или `tg_<handle>` для кастомного |
| `name` | отображаемое имя |
| `handle` | `@username`, если есть |
| `topics` | короткое описание тематики |
| `kind` | `catalog` или `custom` |
| `is_recommended` | входит ли в профильную подборку |
| `is_active` | можно ли показывать/подписываться |
| `meta` | запас для Telegram-метаданных, внешних id, аватарок и т.п. |
| `created_at`, `updated_at` | служебные |

### `profile_channels`

| Поле | Смысл |
| --- | --- |
| `id` | UUID подписки |
| `profile_id` | профиль бизнеса |
| `channel_id` | ссылка на `channels.id` |
| `source` | `catalog`, `recommended` или `custom` |
| `subscribed_at` | когда подписались |

Ограничение `unique(profile_id, channel_id)` не даёт дублировать подписки.

### Поведение API

- `GET /api/sources` — каналы профиля; при первом обращении подписывает на
  `RECOMMENDED_IDS`, если `business_profiles.sources_initialized = false`.
- `GET /api/sources/catalog?q=` — поиск по `channels` (каталог + custom).
- `POST /api/sources/channels` — принимает `@handle` или `t.me`-ссылку; если канала нет,
  создаёт строку `channels` с `kind='custom'` и подписывает профиль.
- `POST /api/sources/channels/{id}/subscribe` — подписка на существующий канал.
- `DELETE /api/sources/channels/{id}` — отписка; сама строка `channels` остаётся,
  чтобы канал можно было найти и подписаться снова.
- `POST /api/sources/channels/unsubscribe-all` — удаляет все подписки профиля.
- `POST /api/sources/channels/restore` — удаляет подписки и подписывает на рекомендации.

### Миграция `a0c5e5283689_normalize_sources_and_channels`

Что делает:

1. Создаёт `channels` и `profile_channels`.
2. Добавляет `business_profiles.sources_initialized` (по умолчанию `false`).
3. Заливает `CHANNELS` в `channels`.
4. Переносит старый `business_profiles.sources`:
   - `channels[]` → подписки;
   - `custom[]` → строки `channels` (`kind='custom'`);
   - если у профиля были каналы/custom, ставит `sources_initialized = true`.
5. Профили без старых источников остаются с `false` и получат рекомендации при первом
   `GET /api/sources`.

Старый JSONB-столбец `business_profiles.sources` пока оставлен для совместимости
и как источник для миграции. Его больше не читает прикладной код (кроме fallback
`_ensure_legacy_channels`, если миграция почему-то не прошла).

Проверка миграции на чистой БД:

```bash
cd back
export DATABASE_URL='postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/alfafuture_migtest'
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head
```

Проверка переноса старых данных: поднять БД до `723d9ff58715`, вставить профиль с
`sources` JSONB, затем `uv run alembic upgrade head` и проверить:

```sql
SELECT channel_id, source FROM profile_channels ORDER BY channel_id;
SELECT sources_initialized FROM business_profiles;
```

## Что делать при подключении реального Telegram-парсера

Не менять API источников. Добавлять слой ingestion вокруг `channels`/`profile_channels`.

### Шаг 1. Расширить `channels`

Добавить поля под Telegram:

- `external_id` — числовой id канала, если появится;
- `username` — нормализованный `@handle`;
- `last_post_at`;
- `last_ingested_at`;
- `ingest_status` (`active`, `paused`, `error`);
- при необходимости `meta` уже есть.

Отдельная миграция, без изменения `profile_channels`.

### Шаг 2. Посты и события

Добавить таблицу постов:

```text
channel_posts(
  id UUID PK,
  channel_id FK channels,
  external_post_id TEXT,
  published_at TIMESTAMPTZ,
  text TEXT,
  url TEXT,
  raw JSONB,
  unique(channel_id, external_post_id)
)
```

Дальше два варианта:

1. **Быстрый:** пост сразу создаёт/обновляет `news_events` и `source_posts`, без отдельной
   таблицы. Подходит для демо, но хуже для дедупликации и кластеризации.
2. **Правильный:** `channel_posts` хранит сырой поток, а `news_events` ссылается на
   `source_posts`/`channel_posts`. Нужен для повторной обработки и аудита.

Рекомендуется второй вариант, если есть время.

### Шаг 3. Очередь

Для прототипа Kafka/Redis не нужны. Порядок внедрения:

1. **Postgres-очередь:** таблица `ingest_jobs` + `SELECT ... FOR UPDATE SKIP LOCKED`.
   Достаточно для нескольких воркеров и демо.
2. **Redis/RQ или Celery** — если нужна отдельная инфраструктура воркеров, ретраи и
   расписания.
3. **Kafka** — только если появится реальный поток из нескольких независимых
   producer'ов и требование replay. Для хакатонного кейса это оверкилл.

Воркер должен читать только активные `profile_channels`-каналы, но посты хранить на
уровне `channels`, чтобы не дублировать один канал для разных пользователей.

### Шаг 4. Связь постов с лентой

После парсинга:

- нормализовать текст, вытащить `source_name`, `source_url`, `published_at`;
- прогнать через текущий `match_event`/LLM-слой;
- записать `news_events.source_posts`, `chain_key`, `update_label`.

Поле `source_posts` в `news_events` уже есть и совместимо с текущими слайдами ленты.

## Как менять ML/LLM-заглушки

Точки замены:

| Сейчас | Файл | Куда менять |
| --- | --- | --- |
| LLM-провайдер | `llm/factory.py` | новый `BaseLLM` или `LLM_PROVIDER` |
| Категории | `services/categories.py` | вызов модели/сервиса, fallback оставить |
| Контрагенты | `services/counterparties.py` | агрегаты платежей + модель |
| Агентский разбор | `services/agent.py` | реальные инструменты/агент |
| Сценарии и вкладки разбора | `services/insights.py` | вынести за протокол/фабрику |
| Поиск | `services/search.py` | SQL → поисковый сервис/эмбеддинги |
| Ранжирование ленты | `services/feed.py` | заменить `match_event` |

Рекомендуемый минимальный рефакторинг перед реальным ML:

1. Ввести `InsightService` protocol и `get_insight_service()` по аналогии с `get_llm()`.
2. Ввести `SearchService` protocol для `services/search.py`.
3. Оставить Pydantic-схемы и ручки без изменений — e2e-тест фиксирует контракт.
4. Для сценариев добавить структурированные финансовые поля компании (выручка, доля
   экспорта, долг, ставка, логистика), иначе реальная модель не сможет считать эффект.

## Каталог и рекомендации

`core/sources.py` — только сид. Если каталог начнёт жить отдельно:

- оставить `CHANNELS` как fallback для пустой БД;
- добавить админский импорт/обновление `channels`;
- `RECOMMENDED_IDS` заменить на правило рекомендаций (категории профиля → каналы);
- не удалять `is_recommended`, иначе сломается `restore`.

Кастомные каналы:

- id `tg_<handle>` детерминирован, поэтому повторное добавление не создаёт дубль;
- если нужен глобальный канал без `@handle`, добавить отдельный сценарий с `external_id`;
- при удалении канала из каталога ставить `is_active=false`, а не `DELETE`, чтобы не
  рвать историю подписок.

## Edge cases

- **Повторная подписка:** `unique(profile_id, channel_id)` + `ON CONFLICT DO NOTHING`.
- **Отписка от всех:** не удаляет `channels`, только `profile_channels`.
- **Restore:** подписывает на `is_recommended=true`, кастомные подписки не возвращает.
- **Пустой профиль:** `sources_initialized=false` → первая выдача подпишет на рекомендации.
- **Старый JSONB:** если миграция не отработала, `_ensure_legacy_channels` перенесёт
  данные лениво при первом запросе.
- **Одинаковый handle у каталога и custom:** `_find_channel` сначала ищет по id/name/handle,
  поэтому каталог имеет приоритет; при необходимости добавить явную проверку конфликтов.

## Чек-лист будущей сессии

- [ ] Прочитать этот файл и `back/README.md`.
- [ ] Поднять Postgres и выполнить `uv run alembic upgrade head`.
- [ ] Прогнать `uv run pytest -q`, `ruff`, `mypy`.
- [ ] При изменении схемы сделать отдельную миграцию и проверить `downgrade base/upgrade head`.
- [ ] Не менять API-контракты источников без обновления e2e-теста.
- [ ] Новые внешние сервисы подключать за протоколом/фабрикой, как `llm/factory.py`.
- [ ] Для парсера сначала Postgres-очередь; Redis/RQ — по необходимости; Kafka — нет.
