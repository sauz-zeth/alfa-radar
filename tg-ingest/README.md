# tg-ingest — Telegram-селфбот для бэкенда

Отдельный сервис: логинится в Telegram как обычный человек, слушает новые посты
в каналах и отправляет их в `POST /api/ingest/posts` бэкенда с заголовком
`X-Ingest-Token`.

## Запуск

```bash
cd tg-ingest
cp .env.example .env        # заполнить TG_API_ID, TG_API_HASH, TG_PHONE, INGEST_TOKEN
uv sync
uv run tg-ingest login      # один раз: ввести код из Telegram (и пароль 2FA, если включён)
uv run tg-ingest run        # слушать новые посты
```

`TG_API_ID` и `TG_API_HASH` берутся на https://my.telegram.org → API development tools.

Это userbot: Telegram может ограничить аккаунт за автоматизацию. Для сервиса лучше
использовать отдельный реальный аккаунт, а не основной.

### Про креды

Пароль нигде не сохраняется. Telethon после первого входа пишет SQLite-файл сессии
`TG_SESSION` (`state/tg_ingest.session` по умолчанию) и дальше авторизуется им.
Это фактический ключ доступа к аккаунту: не коммитьте его, храните с правами `600`,
а для Docker/systemd смонтируйте `state/` как volume.

## Что делает

- Слушает каналы, на которые подписан аккаунт; если задан `TG_CHANNELS` — только их.
- Игнорирует группы, личные переписки и посты без текста/подписи.
- Формирует `source_name`, `url` (`t.me/...` или `t.me/c/...`) и `published_at`,
  отправляет пост в бэкенд с ретраями (3 попытки с backoff).
- Пропущенные за время простоя апдейты Telethon добирает при следующем подключении
  (catch-up), полного backfill истории нет.

## Формат запроса в бэкенд

```http
POST /api/ingest/posts
X-Ingest-Token: <INGEST_TOKEN>

{
  "text": "...",
  "source_name": "Металл-Инсайд",
  "channel": "@metall_inside",
  "url": "https://t.me/metall_inside/42",
  "published_at": "2026-10-25T12:00:00+00:00",
  "telegram": {"chat_id": 1234567890, "message_id": 42, "username": "metall_inside"}
}
```

`profile_id` не передаётся: пост попадает в таблицу `posts` и проходит глобальные
стадии пайплайна (parse → classify → cluster). В ленту он не попадает, потому что
лента строится на уровне профиля. Если нужна привязка к конкретному профилю,
добавьте `profile_id` в payload.

## Тесты

```bash
uv run pytest -q
uv run ruff check .
```
