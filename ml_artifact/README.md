# ML-пайплайн новостей

Папка `ml_artifact/` содержит офлайн-конвейер новостной аналитики Alfa-Future. Он собирает RSS-публикации, отбрасывает рекламу и нерелевантный текст, объединяет публикации одного события, выбирает новости для профиля компании и при необходимости передаёт их на анализ LLM.

Классификация, эмбеддинги и кластеризация работают локально на CPU по ONNX-моделям. Сеть нужна для RSS ingest и финального LLM-этапа.

## Архитектура

```text
RSS → news.jsonl → очистка → ruBERT → BGE-M3 → cosine + reranker
            → clusters.json → профиль компании и фильтр источников
            → candidates.json → Qwen screening → Kimi final → ranked.json/HTML
```

Публикация и событие — разные сущности: несколько постов могут войти в один кластер, а единицей LLM-анализа является кластер события.

## Быстрый запуск

Команды выполняются из `ml_artifact/`.

```bash
python3 -m pip install -r requirements.txt
python3 run.py --uid U_71020 --ingest --dry-run --output-dir outputs/demo
```

Команда за последние 48 часов по UTC скачает RSS, сохранит корпус и изображения, выполнит ruBERT/BGE/reranker, построит кандидатов и сформирует preview без вызовов LLM.

Для LLM уберите `--dry-run` и передайте ключ через окружение или `.env`:

```bash
export ALFA_LLM_API_KEY='...'
python3 run.py --uid U_71020 --ingest --output-dir outputs/business_run
```

Интервал задаётся как полуоткрытый UTC-срез `[start, end)`:

```bash
python3 run.py --uid U_71020 --raw-dir data/raw \
  --start 2026-10-25T00:00:00Z --end 2026-10-26T00:00:00Z \
  --dry-run --limit 20 --output-dir outputs/check
```

## Запуск этапов отдельно

### Сбор RSS

```bash
python3 -m core.ingest \
  --start 2026-10-25T00:00:00Z \
  --end 2026-10-26T00:00:00Z \
  --output-dir outputs/ingest
```

Источники читаются из `RSS_ленты_для_новостной_аналитики_кейс_Альфа_Банка.md`.

### Классификация и кластеризация

```bash
python3 -m core.pipeline \
  --raw-dir outputs/ingest/data/raw \
  --start 2026-10-25T00:00:00Z --end 2026-10-26T00:00:00Z \
  --output-dir outputs/clusters
```

Основные параметры:

| Параметр | По умолчанию | Назначение |
| --- | ---: | --- |
| `--cosine-threshold` | `0.78` | Минимальная близость кандидата |
| `--reranker-threshold` | `0.0` | Минимальный raw logit reranker |
| `--reranker-candidates` | `8` | Кандидаты после cosine-поиска |
| `--window-hours` | `24` | Окно активности кластера |
| `--embedding-chars` | `1200` | Символы для BGE |
| `--embedding-batch-size` | `16` | Batch BGE |
| `--reranker-batch-size` | `8` | Batch reranker |
| `--classifier-batch-size` | `16` | Batch ruBERT |

`--predictions path.jsonl` переиспользует готовые предсказания ruBERT. Кеш должен покрывать весь срез. `--no-html` отключает отчёт.

### Кандидаты для всех профилей

```bash
python3 -m core.select_business_news \
  --accounts reference_uids.json \
  --clusters outputs/clusters/clusters.json \
  --output outputs/candidates.json
```

Профили строятся из `reference_uids.json`, порогов `models/rubert_int4/metadata.json` и `business_sources.json`. Переопределения категорий передаются через `--profiles`.

### LLM-ранжирование одной компании

```bash
python3 -m core.rank_business_news \
  --uid U_71020 \
  --clusters outputs/clusters/clusters.json \
  --output-dir outputs/ranking
```

Для проверки без API используйте `--dry-run`. Темы и контекст компании передаются через `--topics topics.json` и `--context company_context.json`.

Подробные правила маршрутизации описаны в [pipeline.md](pipeline.md). Справка по бизнес-отбору и метрикам — в [BUSINESS_NEWS.md](BUSINESS_NEWS.md).

## Входные данные

Минимальная запись в любом `*.jsonl` внутри `--raw-dir`:

```json
{"post_id":"rss/123","channel":"Example RSS","date":"2026-10-25T12:30:00Z","text":"Текст публикации"}
```

Дополнительные поля `source`, `url` и `images` сохраняются в кластере. Некорректные даты считаются в `invalid_dates` и исключаются. Перед ruBERT удаляются URL, Telegram-упоминания и лишние пробелы; тексты короче 40 символов не классифицируются.

## ML-этапы

`models/rubert_int4/` содержит ONNX INT4-модель и токенизатор. ruBERT предсказывает 31 multilabel-категорию, включая `Реклама/мусор`, с индивидуальными порогами из `metadata.json`.

- нет меток → `no_labels` и удаление;
- есть `Реклама/мусор` → `ad_or_spam` и удаление;
- тематические метки без spam → `kept`.

Для оставшихся публикаций BGE-M3 INT8 строит CLS-вектор по первым 1200 символам очищенного текста, нормирует его по L2 и кеширует в `.npz`. Публикации обрабатываются хронологически: активные 24 часа кластеры, без того же источника, проходят cosine-поиск и максимум 8 кандидатов в reranker. При лучшем raw logit ниже `0.0` создаётся новый кластер; слияния кластеров нет.

Профиль компании содержит максимум восемь активных категорий (`прямое` + `косвенное`) и до 40 RSS-источников. Фильтр источников выполняется до подсчёта меток и независимых групп.

Для LLM используется `qwen/qwen3.6-35b-a3b` для screening косвенного влияния и `moonshotai/kimi-k2.6` для финального анализа. Итоговая важность считается кодом:

```text
I = 40 * related + 25 * direct + 20 * fact + 15 * within_month
```

`I >= 50` даёт `feed`, меньшие значения — `weak`; найденный `topic_id` даёт `tracked`. Подробности, форматы тем/контекста и кеширование см. в [pipeline.md](pipeline.md).

## Выходные файлы

```text
outputs/demo/
├── data/raw/news.jsonl
├── media/
├── ingest_report.json
├── clusters/
│   ├── predictions.jsonl
│   ├── embeddings_<hash>.npz
│   ├── clusters.json
│   ├── news_clusters.json
│   └── clusters_browser.html
├── candidates.json / candidates.html
└── ranking/
    ├── preview.json / preview.html или ranked.json / ranked.html
    ├── *_metrics.json
    ├── requests.jsonl
    ├── api_cache/ и state/
    └── runs/
```

`clusters.json` содержит `parameters` и `clusters`; кластер содержит `event_id`, `sources`, агрегированные `labels`, `images` и `members`. Повторный запуск переиспользует локальные кеши и завершённые LLM-оценки. Для полного пересчёта используйте новый `output-dir`.

## Модели, проверка и безопасность

Локальные модели: `models/rubert_int4/`, `models/bge_m3_int8/`, `models/bge_reranker_int8/`. Ревизии BGE зафиксированы в `models/manifest.json`; инференс использует `CPUExecutionProvider` и не скачивает модели.

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m compileall -q core run.py
```

Тесты покрывают кластеризацию, кеши, источники, изображения и метрики. Качество объединения и LLM без эталонной разметки не измеряется; пороги `0.78` и `0.0` требуют калибровки на размеченных парах.

Не коммитьте `.env`, Telegram session-файлы, ключи API и `outputs/`: там находятся исходные тексты, профили, изображения и ответы LLM. Не запускайте два процесса с одним `output-dir`.
