# Деплой всей системы одной командой

Короткий ответ на вопрос «оно разворачивается вместе или нет?»:

- **До этого гайда — нет.** В репозитории было три независимых куска: `back` и `tg-ingest`
  имели свои `docker-compose.yml`, а у `front` вообще не было Dockerfile.
- **После — да.** В корне появился общий `docker-compose.yml`, который поднимает
  Postgres, API, фронт и Telegram-селфбот в одной сети. Одна команда — четыре контейнера.

Руками остаются только два действия, которые нельзя автоматизировать:
первичный вход в Telegram (код приходит человеку) и заливка демо-данных (`seed`).

## Что из чего состоит

```
                 ┌──────────────────────────────┐
   браузер ─────▶│ front :3000 (Bun + React)    │
                 │  /api/* ──proxy──┐           │
                 └──────────────────┼───────────┘
                                    ▼
                 ┌──────────────────────────────┐      ┌──────────────┐
                 │ api :8000 (FastAPI)          │─────▶│ postgres     │
                 │  миграции при старте         │      │ :5432        │
                 └──────────────▲───────────────┘      └──────────────┘
                                │ POST /api/ingest/posts
                 ┌──────────────┴───────────────┐
                 │ tg-ingest :8081 (Telethon)   │
                 │  /setup — первый вход        │
                 └──────────────────────────────┘
```

- `front` — статика и прокси `/api`, `/docs`, `/openapi.json` на `api`. Наружу нужен только он.
- `api` — вся бизнес-логика, LLM-слой, RSS-поллер. Сам применяет миграции Alembic при старте.
- `tg-ingest` — userbot: слушает каналы и льёт посты в `api` с `X-Ingest-Token`.
- `postgres` — база. Данные лежат в named volume `pgdata`.

## Что нужно заранее

- Сервер с Docker и плагином `docker compose` (или Podman + `podman-compose`).
- Свободные порты `3000` (фронт) и `8081` (первый вход в Telegram). `8000` проброшен
  только на `127.0.0.1`.
- Для Telegram: `TG_API_ID`, `TG_API_HASH` с <https://my.telegram.org> и номер аккаунта.
  Лучше отдельный аккаунт — Telegram может ограничивать userbot'ов.
- Для реального LLM: ключ любого OpenAI-совместимого шлюза. Без ключа оставьте
  `LLM_PROVIDER=stub` — всё поднимется, но анализ будет заглушкой.
- Для полного демо — CSV из архива хакатона (см. ниже). Без них тоже можно запуститься.

## Шаг 1. Конфиги

Из корня репозитория:

```bash
cp .env.example .env
cp tg-ingest/.env.example tg-ingest/.env
```

В корневом `.env` обязательно:

```dotenv
# сгенерировать: openssl rand -hex 32
JWT_SECRET=<длинная случайная строка>

# НЕ оставляйте пустым: без него не откроется /setup у tg-ingest
INGEST_TOKEN=<любая длинная случайная строка>

# простой пароль или URL-encode спецсимволы
POSTGRES_PASSWORD=<пароль>
```

`INGEST_TOKEN` из корневого `.env` подставляется и в `api`, и в `tg-ingest` — так они
гарантированно совпадут. Значение в `tg-ingest/.env` при общем compose игнорируется
(оно нужно только для отдельного запуска `tg-ingest`).

В `tg-ingest/.env` заполните только Telegram-часть:

```dotenv
TG_API_ID=123456
TG_API_HASH=...
TG_PHONE=+79990000000
TG_2FA_PASSWORD=      # пусто, если 2FA нет
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

Если CSV нет, можно залить синтетику (15 пользователей `demo1`…`demo15`, пароль `demo`,
15 компаний, платежи, каналы) — этот скрипт файлы не требует.

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

## Шаг 5. Первый вход в Telegram

Сессии ещё нет, поэтому `tg-ingest` поднимает страницу настройки:

1. Откройте `http://<host>:8081/setup`.
2. Введите `INGEST_TOKEN` (тот же, что в корневом `.env`).
3. Нажмите «Отправить код», введите код из Telegram (и пароль 2FA, если включён).
4. После «Готово» селфбот сразу начнёт слушать каналы. Перезапуск не нужен.

Сессия сохраняется в `./tg-ingest/state` (или в `TG_STATE_DIR_HOST`). Это фактический
ключ от аккаунта: не коммитьте, держите права `600`, делайте бэкап. После успешного входа
страница `/setup` больше не поднимается; закройте порт `8081` файрволом или поставьте
`SETUP_ENABLED=false` в `tg-ingest/.env`.

## Шаг 6. Проверка

- Фронт: `http://<host>:3000`
- API напрямую: `http://127.0.0.1:8000/health` (с сервера) или `ssh -L 8000:127.0.0.1:8000`
- Swagger через фронт: `http://<host>:3000/docs`
- Логи: `docker compose logs -f api front tg-ingest`
- Статус: `docker compose ps` — у `postgres` и `api` должно быть `healthy`.

## Обновление

```bash
git pull
docker compose up -d --build
```

Миграции применяются автоматически при перезапуске `api`. Данные в `pgdata`,
`tg-ingest/state` и `avatars` сохраняются. Пересоздаются только контейнеры.

## Бэкапы

```bash
# база (подставьте свои POSTGRES_DB/USER)
docker compose exec -T postgres pg_dump -U postgres alfafuture | gzip > db-$(date +%F).sql.gz

# сессия Telegram + счётчик подписок
tar czf tg-state-$(date +%F).tgz tg-ingest/state
```

Восстановление базы:

```bash
gunzip -c db-2026-10-25.sql.gz | docker compose exec -T postgres psql -U postgres -d alfafuture
```

## Прод-заметки

- Наружу отдавайте только фронт. Поставьте Caddy/nginx с TLS перед `127.0.0.1:3000`:

  ```caddyfile
  news.example.com {
      reverse_proxy 127.0.0.1:3000
  }
  ```

- Порт `8081` нужен только на время первого входа.
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
| `/setup` отвечает 401 | пустой `INGEST_TOKEN` | задать непустой токен в корневом `.env`, перезапустить |
| `seed.py`: не найден `df_Uid_data_hack.csv` | нет CSV в `back/data` | положить файлы или запустить `seed_15_profiles.py` |
| `tg-ingest` не подписывается на каналы | нет подписчиков у каналов или неверный токен | подписаться на каналы во фронте, проверить `INGEST_TOKEN` |
| забыли пароль/слетела сессия Telegram | удалён `tg-ingest/state` | повторить шаг 5 |
| нужно снести всё | — | `docker compose down -v` **удалит базу**, state Telegram останется |

## Что было добавлено

- `docker-compose.yml` в корне — общая сеть и все четыре сервиса.
- `front/Dockerfile` — прод-сборка Bun-сервера (без Playwright и dev-зависимостей).
- `back/.dockerignore`, `front/.dockerignore` — чтобы в образы не попали `.env`,
  `.venv`, `node_modules`, тесты и данные.
- `.env.example` в корне — общие переменные для compose.
- `.gitignore` в корне — чтобы `.env` не улетел в git.

Старые `back/docker-compose.yml` и `tg-ingest/docker-compose.yml` остались для
отдельного запуска и локальной разработки. Для единого деплоя используйте только
корневой compose — **не поднимайте оба одновременно**, они займут одни и те же порты
и Postgres.
