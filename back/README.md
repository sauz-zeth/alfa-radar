# Backend

FastAPI-сервис и ML-пайплайн новостной аналитики. Структура повторяет шаги из
`ML-пайплайн сервиса новостной аналитики.md` и `Цепочки обновлений новостей.md`.

## Стек

- FastAPI + Uvicorn, Pydantic v2 / pydantic-settings
- PostgreSQL + SQLAlchemy 2 (asyncpg) + Alembic
- LiteLLM (OpenAI-совместимый шлюз)
- ruBERT (`transformers`, `torch`) — мультилейбл-классификатор категорий
- `multilingual-e5-base` (`sentence-transformers`) — эмбеддинги новостей и цепочек
- `pymorphy3` — лемматизация и поиск алиасов
- numpy, scikit-learn — предскоринг, кластеризация, подбор порогов

## Структура

```text
back/
├── src/back/
│   ├── main.py                 # создание FastAPI-приложения
│   ├── config.py               # настройки из .env
│   ├── api/
│   │   └── routes/             # health, feed, events, chains, companies, swipes
│   ├── db/
│   │   ├── base.py             # DeclarativeBase
│   │   ├── session.py          # async engine и сессии
│   │   └── models/             # news, events, companies, feed, chains
│   ├── ml/
│   │   ├── classifier.py       # ruBERT, multi-label
│   │   ├── embeddings.py       # e5 с префиксом passage:
│   │   ├── lemmatizer.py       # pymorphy3 и поиск алиасов
│   │   └── llm.py              # LiteLLM + валидация ответов Pydantic
│   ├── pipeline/
│   │   ├── enrich.py           # шаг 1. обогащение новости
│   │   ├── cluster.py          # шаг 2. кластеризация в события
│   │   ├── prescore.py         # шаг 3. S_cat
│   │   ├── select.py           # шаг 4. отбор событий в LLM
│   │   ├── analyze.py          # шаг 5. LLM-анализ и I
│   │   ├── rank.py             # шаг 6. R, срочность, разнообразие
│   │   └── chains/             # цепочки: кандидаты, LLM-проверка, отчёт, пуш
│   ├── schemas/                # Pydantic-схемы API и ответов LLM
│   └── services/               # обратная связь от свайпов
├── migrations/                 # Alembic, начальная схема уже создана
├── scripts/                    # офлайн-подготовка: разметка, обучение, пороги
├── tests/                      # формулы пайплайна
├── docker-compose.yml          # Postgres
├── alembic.ini
└── .env.example
```

## Запуск

```bash
cd back
cp .env.example .env
docker compose up -d postgres
uv sync --extra ml --dev
uv run alembic upgrade head
uv run uvicorn back.main:app --reload --app-dir src
```

`--extra ml` нужен для torch/transformers/sentence-transformers. Без него
поднимаются только API, БД и LiteLLM-клиент.

Новые миграции после изменения моделей:

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

## Офлайн-подготовка

```bash
uv run python scripts/train_classifier.py data/labeled_news.jsonl
uv run python scripts/tune_category_thresholds.py data/labeled_news.jsonl
uv run python scripts/tune_prescore_tau.py data/golden_set.jsonl
uv run python scripts/tune_chain_threshold.py data/chain_pairs.jsonl
```

Форматы входных данных: JSONL, по одному объекту на строку. Для обучения
классификатора нужны поля `text` и `labels`; для порогов — `scores` и `labels`,
`prescore` и `important`, либо `similarity` и `continuation`.

## Проверки

```bash
uv run ruff check .
uv run mypy src
uv run pytest
```

## Важные допущения

- Векторы событий и цепочек пока хранятся в `JSONB`. При росте числа цепочек до
  тысяч документ предусматривает переезд на `pgvector` без изменения логики.
- Пороги `t_c`, `θ`, `τ`, `θ_ch` задаются конфигом и подбираются офлайн на
  размеченных наборах.
- Модель LLM задаётся в `.env`; профиль компании и кеш «событие + компания»
  общие для всех пользователей компании.
