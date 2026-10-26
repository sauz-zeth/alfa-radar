# Alfa Future — новостная аналитика для бизнеса

Сервис собирает деловые новости из RSS, группирует публикации по событиям и показывает предпринимателю персональную ленту с оценкой влияния на его бизнес. Пользователь настраивает профиль компании, отраслевые темы и источники, а затем может отслеживать событие и задавать вопросы по его истории.

## Версия для проверки

Исходный снимок перед финализацией: `87716524bb54b1525b9bdcfc3147ac82ab54d6a4`. После фиксации релизного commit замените hash здесь на его полный hash и опубликуйте этот commit в GitHub. Именно опубликованный commit или tag должен однозначно указывать версию на момент дедлайна.

## Архитектура

- `front/` — SPA на React и Bun; экран адаптируется под мобильный и настольный вид. Запросы идут через same-origin proxy на API.
- `back/` — FastAPI, SQLAlchemy async и Alembic. API отвечает за регистрацию, онбординг, компании, источники, ленту, поиск и отслеживаемые события.
- PostgreSQL 17 — пользователи, профили, компании, платежи, публикации и события.
- RSS poller в API опрашивает RSS/Atom-подписки. `rsshub` — дополнительный сервис для совместимых источников.
- `ml-worker` — отдельный worker обработки и анализа ленты; включение ML требует локально установленных моделей.
- `ml_pipeline/` и `ml_artifact/` — код и артефакты, подключённые worker-у read-only.

Поток данных: RSS/Atom → публикации → разбор и группировка в события → профильная оценка влияния → персональная лента → отслеживание и аналитический разбор. Без внешнего LLM-провайдера используется `LLM_PROVIDER=stub` с детерминированными локальными ответами. Для внешнего OpenAI-совместимого шлюза задаются `LLM_PROVIDER=openai`, `LLM_BASE_URL` и `LLM_API_KEY`.

## Требования

- Git и Docker Compose v2 (`docker compose`).
- Для запуска без Docker: Python 3.14 и `uv` 0.12.7+, Bun 1.x.
- Интернет нужен Docker для загрузки образов и RSS-обновлений. Для локального воспроизводимого демо можно отключить опрос RSS.
- CSV датасета кейса необязательны: синтетические компании и платежи создаются локально. Данные кейса не включены в репозиторий.

Python-зависимости зафиксированы в `back/uv.lock` и `ml_pipeline/uv.lock`; frontend — в `front/bun.lock`. Docker-образы backend/frontend используют lock-файлы и frozen install. Образы БД и RSSHub указываются в `docker-compose.yml`.

## Быстрый запуск всего приложения

Из корня репозитория:

```bash
cp .env.example .env
```

Задайте в `.env` уникальный `JWT_SECRET` (например, `openssl rand -hex 32`) и установите локальный режим без внешнего LLM и RSS-запросов:

```dotenv
JWT_SECRET=replace-with-a-random-secret
LLM_PROVIDER=stub
LLM_AGENT_ENABLED=false
LLM_ML_ENABLED=false
RSS_POLL_ENABLED=false
ML_WORKER_ENABLED=false
```

Затем запустите сервисы и подготовьте синтетические данные:

```bash
docker compose up --build -d
docker compose exec api python scripts/seed_demo_companies.py --companies 1000 --with-payments 40
docker compose exec api python scripts/seed.py --skip-payments
docker compose exec api python scripts/seed_15_profiles.py --skip-migrations
docker compose exec api python scripts/seed_demo_tracked.py
```

`seed_demo_companies.py` создаёт синтетические компании и платежи; `seed.py` при отсутствии приватного CSV всё равно создаёт категории, источники, события и аккаунты; `seed_15_profiles.py` создаёт готовые профили demo1–demo3. Команды не очищают таблицы. `seed.py --reset` очищает таблицы приложения и не нужен для обычного старта. API применяет миграции при старте; дождитесь `healthy` у `api` через `docker compose ps`.

Откройте <http://localhost:3000>. API: <http://localhost:8000>; Swagger UI: <http://localhost:8000/docs>; health: <http://localhost:8000/health>.

Демо-учётные записи после seed:

| Логин | Пароль | Состояние |
| --- | --- | --- |
| `demo` | `demo` | Новый профиль для прохождения онбординга |
| `demo_full` | `demo` | Заполненный профиль и демо-события для ленты/«Отслеживаемого» |

Пароли и логины можно переопределить переменными `DEMO_LOGIN`, `DEMO_PASSWORD`, `DEMO_FULL_LOGIN`, `DEMO_FULL_PASSWORD`. Для чистой базы пересоздайте только данные Compose: `docker compose down -v` удаляет базу и загруженные данные; после этого повторите `up` и команды seed.

## Сквозная проверка

1. Откройте приложение и войдите как `demo_full` / `demo`.
2. Проверьте, что отображается лента новостей; откройте карточку, просмотрите влияние и детали события.
3. Перейдите в «Отслеживаемое», откройте готовую тему, проверьте историю и задайте вопрос.
4. Выйдите и войдите как `demo` / `demo`. Выберите синтетическую компанию (например, поиск по `SYN`), пройдите шаги настройки профиля, роли, контрагентов и категорий. Отчётность можно пропустить.
5. После завершения онбординга проверьте источники и персональную ленту. При `RSS_POLL_ENABLED=false` новые внешние публикации не поступают, но синтетические демо-события доступны.
6. Проверьте состояние API: `curl http://localhost:8000/health` и `curl http://localhost:8000/health/db`.

## Конфигурация

Полный перечень с комментариями находится в [.env.example](.env.example) и [back/.env.example](back/.env.example). Для Compose основные переменные:

| Переменная | Назначение |
| --- | --- |
| `JWT_SECRET` | Секрет подписи токенов; обязателен для Compose, задайте уникальное значение. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | База и учётные данные PostgreSQL. |
| `FRONT_PORT`, `API_PORT` | Порты frontend и API на хосте. |
| `LLM_PROVIDER` | `stub` для офлайн-режима, `openai` для OpenAI-совместимого сервиса. |
| `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_FAST_MODEL` | Адрес, ключ и модели LLM; ключ необязателен в stub-режиме. |
| `LLM_AGENT_ENABLED`, `LLM_ML_ENABLED` | Включение LLM-разбора и LLM-подсказок. |
| `RSS_POLL_ENABLED`, `RSS_FEEDS`, `RSSHUB_BASE_URL` | Фоновый опрос пользовательских RSS и адрес RSSHub. |
| `ML_WORKER_ENABLED` | Фоновая обработка новостных публикаций. |
| `DEMO_LOGIN`, `DEMO_PASSWORD`, `DEMO_FULL_LOGIN`, `DEMO_FULL_PASSWORD` | Учётные записи, создаваемые seed-скриптом. |
| `BACK_DATA_DIR` | Каталог с CSV датасета, если он предоставлен отдельно. |

`INGEST_TOKEN` задаёт общий токен для внутренних endpoint-ов приёма публикаций. Не публикуйте секреты и не используйте демонстрационные пароли в развёртывании с реальными данными.

## Данные и дополнительные сценарии

Для синтетического набора достаточно команд выше. Если предоставлен датасет, поместите `df_Uid_data_hack.csv`, `df_Uid_payment_hack.csv` и `df_Fid_Uid_link_hack.csv` в каталог `back/data` либо задайте `BACK_DATA_DIR`, затем загрузите его:

```bash
docker compose exec api python scripts/seed.py --reset
```

Синтетический сценарий не содержит исходные данные Альфа-Банка. Не загружайте приватные CSV/PDF и Telegram session-файлы в публичный репозиторий. Дополнительные backend-команды и описание API см. в [back/README.md](back/README.md), документацию развёртывания — в [docs/DEPLOY.md](docs/DEPLOY.md).

Чтобы скачать публикации за последние 48 часов из встроенного каталога, запустите:

```bash
docker compose exec api python scripts/ingest_last_48h.py
```

Скрипт использует первые 40 прямых RSS-источников каталога. Доступность зависит от внешних сайтов. Полный каталог интерфейса содержит 193 источника, в том числе Telegram; `scripts/ingest_rss.py URL ...` загружает указанные RSS, а без аргументов читает `RSS_FEEDS`.

## ML-модели

Модели не входят в Git; скачайте их отдельно в `ml_artifact/models/` и сохраните структуру: `rubert_int4/{model.onnx,metadata.json,tokenizer/}`, `bge_m3_int8/` и `bge_reranker_int8/` с `model_quantized.onnx` и tokenizer/config-файлами. BGE ревизии закреплены в `ml_artifact/models/manifest.json`.

| Модель | Источник |
| --- | --- |
| ruBERT INT4 classifier | [sauz-zeth/rubert-news-classification](https://huggingface.co/sauz-zeth/rubert-news-classification) |
| BGE-M3 INT8 embeddings | [skatzR/USER-BGE-M3-ONNX-INT8](https://huggingface.co/skatzR/USER-BGE-M3-ONNX-INT8) |
| BGE reranker INT8 | [keisuke-miyako/bge-reranker-base-onnx-int8](https://huggingface.co/keisuke-miyako/bge-reranker-base-onnx-int8) |

Убедитесь, что ruBERT-репозиторий содержит совместимые ONNX INT4, metadata и tokenizer-файлы; если нет — используйте отдельный release-артефакт проекта. Не переименовывайте обычные веса в ONNX. Для инференса включите `ML_WORKER_ENABLED=true`. Демо запускается без скачивания моделей при `ML_WORKER_ENABLED=false`.

## Сторонние компоненты

- FastAPI, SQLAlchemy, Alembic, asyncpg, Pydantic, Uvicorn и остальные Python-пакеты — версии см. в `back/pyproject.toml` и `back/uv.lock`.
- React, React DOM, TanStack Query, Zod и Playwright — версии см. в `front/package.json` и `front/bun.lock`.
- PostgreSQL (`postgres:17-alpine`), RSSHub (`diygod/rsshub:latest`), Python и Bun — контейнерные базовые образы указаны в Dockerfiles и Compose.
- Внешний LLM-шлюз и RSS/Atom-источники используются только при включённой соответствующей конфигурации; это внешние сервисы, они не входят в локальный offline-сценарий.
- Модели, источники данных, внешние сервисы и смоделированный Outlook перечислены в [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES); перед распространением весов проверьте лицензию в карточке каждой модели.

Проверки: из `back/` — `uv run pytest -q`; из `ml_pipeline/` — `uv run pytest -q`; из `front/` — `bun run test:visual`.
