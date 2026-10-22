# Бэкенд: авторизация, онбординг, лента и отслеживаемое

Полная инструкция по запуску и API — в [`back/README.md`](../back/README.md).
Здесь — карта решения и места, которые важно знать при доработке.

## Что реализовано

- Логин/пароль, JWT, Argon2.
- Онбординг: выбор компании по UID → имя/название → роль → контрагенты → категории → отчётность.
- Персонализированная лента: важность корректируется весами категорий профиля и упоминаниями контрагентов.
- Тип влияния `risk` / `opportunity` / `mixed` / `neutral`.
- Пометка «(!)»: API отдаёт `prognosis_note` и `detail_note` для подсказки о том, что прогноз
  может уточниться во вкладке «Отслеживаемое».
- Вкладка «Отслеживаемое»: агент учитывает роль, категории, контрагентов и выжимку отчётности.
- Загрузка 3 форм отчётности (баланс, ОФР, ДДС): `.txt`, `.csv`, `.pdf`, `.xlsx`.
- Seed из `df_Uid_data_hack.csv` + `df_Uid_payment_hack.csv` + демо-новости.
- Демо-учётки `demo/demo` и `demo_full/demo`.

## Слои

```
src/back/
  api/routes/      HTTP-ручки (auth, businesses, onboarding, profile, feed, tracked)
  services/        бизнес-логика: онбординг, категории, контрагенты, отчётность, агент, лента
  llm/             абстракция LLM: base, stub, openai_compatible, factory, prompts
  db/              SQLAlchemy-модели и async-сессия
  schemas/         Pydantic-схемы запросов/ответов
  core/            константы, 30 категорий, безопасность, сегменты/теги компаний
scripts/seed.py       загрузка CSV, демо-новостей и учёток
scripts/import_csv.py импорт произвольных CSV с автоопределением типа
migrations/        Alembic
```

## LLM-слой и замена модели

Ключевое место: **`back/src/back/llm/factory.py`**. Провайдер выбирается переменной
`LLM_PROVIDER`:

- `stub` — офлайн, без внешних вызовов. Возвращает детерминированные fallback-результаты,
  посчитанные по данным компании, платежам и тексту отчётности.
- `openai` — любой OpenAI-compatible gateway (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`,
  `LLM_FAST_MODEL`). Ошибки 402/429 и «budget exceeded» не роняют сервис: используется fallback.

Промпты лежат в `back/src/back/llm/prompts.py`. Задачи, где LLM участвует:

- подбор весов категорий (`services/categories.py`);
- уточнение важности контрагентов (`services/counterparties.py`);
- извлечение цифр из отчётности (`services/reporting.py`);
- разбор события и действия агента (`services/agent.py`).

ML-обучения нет. Старый `pipeline/`, `ml/` и скрипты обучения удалены. Если позже нужно
подключить настоящую модель — достаточно реализовать `BaseLLM` и вернуть её из `factory.py`,
не меняя API и сервисы.

## Выбор компании в онбординге

Чтобы не показывать 85 тыс. строк, используется `GET /api/businesses/options`:

- без поиска — 15 компаний из разных отраслей и сегментов (`mode=featured`);
- с `search` — поиск по всем компаниям по UID, городу, региону и ОКВЭД
  (`mode=search`, до 50 результатов);
- полный список с фильтрами остаётся в `GET /api/businesses`.

Курируемый список лежит в `back/src/back/core/featured.py`. Если UID нет в текущей
базе, ручка автоматически добирает компании с максимальной выручкой.

## Данные

- `companies` — 85 514 уникальных UID из CSV (исходный файл содержит дубликат `U_428697`).
- `payments` — 1 382 585 строк; из них считаются поставщики/покупатели, доли и важность.
- `person_company_links` — 12 514 связей физлиц и компаний из `df_Fid_Uid_link_hack.csv`.
- `categories` — 30 категорий-факторов из `docs/Категории новостей-2.md`.
- `news_events` — 27 демо-новостей, в том числе смешанные риск/возможность.
- `business_profiles` — профиль бизнеса пользователя: имя, название, роль, теги,
  `reporting_summary`, статус онбординга.

## Быстрый сценарий проверки

```bash
cd back
podman-compose up -d postgres
uv sync --all-groups
uv run alembic upgrade head
uv run python scripts/seed.py --reset
uv run uvicorn back.main:app --reload
```

1. `POST /api/auth/login` с `demo/demo`.
2. `GET /api/onboarding/state` → `business_selected`.
3. `GET /api/businesses?search=U_57706` → `POST /api/onboarding/business`.
4. `POST /api/onboarding/skip` (имя), `POST /api/onboarding/role`.
5. `GET /api/onboarding/counterparties`, `POST /api/onboarding/categories/suggest`.
6. `POST /api/onboarding/reporting` (3 файла), `POST /api/onboarding/complete`.
7. `GET /api/feed` → `POST /api/feed/{id}/track` → `GET /api/tracked`.

Swagger: `http://localhost:8000/docs`.

## Экраны из макетов

- **Лента:** `GET /api/feed` отдаёт слайды источников, факты, разбивку важности, лайки и
  фильтры; деталь — `GET /api/feed/{id}` со вкладками разбора.
- **Скрытые:** `GET /api/feed/hidden?tab=stale|weak|skipped`, возврат — `POST /api/feed/{id}/restore`.
- **Отслеживаемое:** `GET /api/tracked`, деталь истории, вопросы, архив/возобновление
  и сценарии.
- **Источники:** `GET /api/sources`, каталог, подписка/отписка; аналитика Альфа-Банка
  подключается всегда.
- **Поиск:** `GET /api/search` по новостям и компаниям, история до 10 запросов.
- **Профиль:** `GET /api/profile` со статистикой компании, группами категорий,
  контрагентами по направлениям и настройками уведомлений.

Сценарии, сравнение источников и часть разбора сейчас детерминированные заглушки: точки
замены на ML/LLM находятся в `services/insights.py`, `llm/` и `services/agent.py`.

## Тесты

```bash
cd back
uv run pytest -q
```

`tests/test_api_mockup.py` — сквозной тест по экранам макетов. Ему нужен Postgres;
по умолчанию используется `postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/alfafuture_test`
(переопределяется через `TEST_DATABASE_URL`). Без доступной БД тест пропускается.

## Отчёты

- [Авторизация и онбординг](Auth-Onboarding-Report.md) — проверка полного сценария и негативных кейсов.
