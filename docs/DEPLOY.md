# Деплой всей системы одной командой

Короткий ответ на вопрос «оно разворачивается вместе или нет?»:

- **До этого гайда — нет.** В репозитории backend и frontend не запускались единым стеком.
- **После — да.** В корне появился общий `docker-compose.yml`, который поднимает
  Postgres, API, фронт и ML worker в одной сети.

Руками остаётся только заливка демо-данных (`seed`).

## Что из чего состоит

```
                 ┌──────────────────────────────┐
   браузер ─────▶│ front :3000 (Bun + React)    │
                 │  /api/* ──proxy──┐           │
                 └──────────────────┼───────────┘
                                    ▼
                 ┌──────────────────────────────┐      ┌──────────────┐
                 │ api :8000 (FastAPI + RSS)    │─────▶│ postgres     │
                 │  миграции при старте         │      │ :5432        │
                 └──────────────────────────────┘      └──────────────┘
```

- `front` — статика и прокси `/api`, `/docs`, `/openapi.json` на `api`. Наружу нужен только он.
- `api` — вся бизнес-логика, LLM-слой, RSS-поллер. Сам применяет миграции Alembic при старте.
- `postgres` — база. Данные лежат в named volume `pgdata`.

## Что нужно заранее

- Сервер с Docker + `docker compose` **или** Podman + `podman-compose` (у вас — Podman 5.x
  и `podman-compose` 1.6, этого достаточно). Все команды ниже записаны как `docker compose`;
  с Podman просто заменяйте их на `podman-compose` — файл называется `docker-compose.yml`,
  поэтому `-f` не нужен.
- Свободный порт `3000` (фронт). `8000` проброшен
  только на `127.0.0.1`.
- Для реального LLM: ключ любого OpenAI-совместимого шлюза. Без ключа оставьте
  `LLM_PROVIDER=stub` — всё поднимется, но анализ будет заглушкой.
- Для полного демо — CSV из архива хакатона (см. ниже). Без них тоже можно запуститься.

## Шаг 1. Конфиги

Из корня репозитория:

```bash
cp .env.example .env
```

В корневом `.env` обязательно:

```dotenv
# сгенерировать: openssl rand -hex 32
JWT_SECRET=<длинная случайная строка>

# необязательный токен для доверенных post-ingest запросов
INGEST_TOKEN=

# простой пароль или URL-encode спецсимволы
POSTGRES_PASSWORD=<пароль>
```

## Шаг 2. Демо-данные (опционально)

Без данных сервис поднимется, но в онбординге не будет компаний. Положите три CSV
в `back/data`:

```
back/data/df_Uid_data_hack.csv
back/data/df_Uid_payment_hack.csv
back/data/df_Fid_Uid_link_hack.csv
```

Папка монтируется в контейнер read-only как `/app/data`.

`seed_15_profiles.py` использует те же CSV: 15 эталонных компаний из `reference_uids.json`
с реальными платежами. Если CSV нет — заливает синтетику (15 пользователей `demo1`…`demo15`,
пароль `demo`, 15 компаний, платежи, каналы).

## Шаг 3. Запуск

```bash
docker compose up -d --build
docker compose ps
```

Первый запуск собирает образы, это несколько минут. `api` сам выполнит
`alembic upgrade head`. Ждём, пока `api` станет `healthy`:

```bash
docker compose logs -f api
```

## Шаг 4. Seed

Полное демо (нужны CSV):

```bash
docker compose exec api python scripts/seed.py --reset
docker compose exec api python scripts/seed_demo_tracked.py
```

`--reset` очищает таблицы — не используйте на боевой базе.

Без CSV:

```bash
docker compose exec api python scripts/seed_15_profiles.py
```

Учётки после полного seed: `demo` / `demo` (пустой профиль, проходит онбординг)
и `demo_full` / `demo` (готовый профиль с лентой и «Отслеживаемым»).

## Шаг 5. Проверка

- Фронт: `http://<host>:3000`
- API напрямую: `http://127.0.0.1:8000/health` (с сервера) или `ssh -L 8000:127.0.0.1:8000`
- Swagger через фронт: `http://<host>:3000/docs`
- Логи: `docker compose logs -f api front ml-worker`
- Статус: `docker compose ps` — у `postgres` и `api` должно быть `healthy`.

## Обновление

```bash
git pull
docker compose up -d --build
```

Миграции применяются автоматически при перезапуске `api`. Данные в `pgdata` и
`avatars` сохраняются. Пересоздаются только контейнеры.

## Бэкапы

```bash
# база (подставьте свои POSTGRES_DB/USER)
docker compose exec -T postgres pg_dump -U postgres alfafuture | gzip > db-$(date +%F).sql.gz

# аватарки каналов (named volume avatars)
docker compose run --rm --no-deps -v "$PWD":/backup:z api \
  tar cf /backup/avatars-$(date +%F).tar -C /app/src/back/static/avatars .
```

Восстановление базы и аватарок:

```bash
gunzip -c db-2026-10-25.sql.gz | docker compose exec -T postgres psql -U postgres -d alfafuture
docker compose run --rm --no-deps -v "$PWD":/backup:z api \
  tar xf /backup/avatars-2026-10-25.tar -C /app/src/back/static/avatars
```

Если восстановить только БД, в `channels.meta` останутся старые `avatar_url`, а файлов в
новом volume не будет — фронт получит 404. Либо залейте tar с аватарками, либо очистите
`avatar_url` у каналов.

## Podman

Всё то же самое, только команды короче:

```bash
cp .env.example .env
# заполнить JWT_SECRET, INGEST_TOKEN, POSTGRES_PASSWORD

podman-compose up -d --build
podman-compose ps
podman-compose logs -f api
podman-compose exec api python scripts/seed.py --reset
```

Важное для Podman:

- **SELinux** (Fedora, Silverblue, Kinoite, Bazzite): bind-mount'ы в compose уже помечены
  `:z` — `back/data`. Если добавляете свои каталоги, тоже ставьте
  `:z` (или `:Z`), иначе контейнер получит `Permission denied`.
- **Прокси хоста.** Podman может автоматически прокинуть `HTTP_PROXY/HTTPS_PROXY`
  в контейнеры. Если прокси слушает `127.0.0.1` на хосте, из контейнера он недоступен:
  сборка падает на скачивании пакетов, а фронт не может достучаться до `api`. В compose
  внутренние имена уже добавлены в `NO_PROXY`, поэтому связка front↔api работает. Если
  сборка падает на PyPI (`Connection refused` в `uv sync`):

  ```bash
  podman-compose --podman-build-args="--network=host" build
  ```

  Если не идут внешние запросы (LLM, RSS), запускайте без проброса прокси:

  ```bash
  podman-compose --podman-run-args="--http-proxy=false" up -d --build
  ```

  Это же лечится отключением проброса в `~/.config/containers/containers.conf`
  (`[engine] http_proxy = false`). На обычном VPS без прокси ничего из этого не нужно.
- **Занятые порты.** Если локально уже крутится старый стек (`back_postgres_1`,
  `uvicorn` на 8000, фронт на 3000), либо остановите его, либо поменяйте в `.env`
  `FRONT_PORT=3001`, `API_PORT=8001`. Postgres наружу не
  публикуется, поэтому 5432 не конфликтует.
- **Автозапуск после ребута.** Rootless-контейнеры сами не встают. Либо один раз
  зарегистрируйте systemd-юнит (имя проекта смотрите в выводе команды):

  ```bash
  loginctl enable-linger "$USER"
  podman-compose systemd -a create-unit   # один раз, может попросить sudo
  podman-compose systemd -a register
  systemctl --user start podman-compose@alfa-future
  ```

  либо запускайте `podman-compose up -d` после загрузки вручную.
- `podman-compose down -v` **удаляет и named volumes**, то есть базу. Без `-v` — только
  контейнеры.
- Порт `3000` публикуется через rootless-проброс, sudo не нужен.
- `podman compose` (обёртка) у вас делегирует в `podman-compose`, так что можно писать
  и так, и так.

## Прод-заметки

- Наружу отдавайте только фронт. Поставьте Caddy/nginx с TLS перед `127.0.0.1:3000`:

  ```caddyfile
  news.example.com {
      reverse_proxy 127.0.0.1:3000
  }
  ```

- `CORS_ORIGINS` укажите на реальный домен, если ходите в API не через прокси фронта.
- `LLM_PROVIDER=openai` + `LLM_API_KEY` включает настоящий анализ; `stub` — офлайн.
- Пароль Postgres с `@`, `:` и `/` сломает `DATABASE_URL`. Либо простой пароль,
  либо URL-encode.
- В гайде нет автоматических бэкапов, мониторинга и ротации логов — для хакатона это ок,
  для прода добавьте.

## Если что-то не так

| Симптом | Причина | Что делать |
| --- | --- | --- |
| `set JWT_SECRET in .env` | нет `.env` или пустой `JWT_SECRET` | `cp .env.example .env`, заполнить |
| фронт отдаёт 502 на `/api` | `api` не поднялся | `docker compose logs api`, проверить `DATABASE_URL` и пароль Postgres |
| `address already in use` | заняты 3000/8000 | остановить старый стек или поменять `FRONT_PORT`/`API_PORT` |
| `seed.py`: не найден `df_Uid_data_hack.csv` | нет CSV в `back/data` | положить файлы или запустить `seed_15_profiles.py` |
| аватарки каналов 404 | БД восстановлена, а volume `avatars` пустой | залить tar с аватарками или очистить `avatar_url` у каналов |
| RSS не обновляется | выключен RSS polling или нет подписанных лент | проверить `RSS_POLL_ENABLED` и подписки в «Источниках» |
| нужно снести всё | — | `docker compose down -v` **удалит базу** |

## Что было добавлено

- `docker-compose.yml` в корне — общий стек сервисов.
- `front/Dockerfile` — прод-сборка Bun-сервера (без Playwright и dev-зависимостей).
- `back/.dockerignore`, `front/.dockerignore` — чтобы в образы не попали `.env`,
  `.venv`, `node_modules`, тесты и данные.
- `.env.example` в корне — общие переменные для compose.
- `.gitignore` в корне — чтобы `.env` не улетел в git.

Для единого деплоя используйте корневой compose.
