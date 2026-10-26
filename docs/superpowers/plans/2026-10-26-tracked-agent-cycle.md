# Агентский цикл во вкладке «Отслеживаемое» — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Для каждой отслеживаемой новости выполнять проверяемый агентский цикл с поиском аналитики Альфа-Банка и профиля бизнеса, показывая ход и обоснованные выводы пользователю.

**Architecture:** Расширить существующий `back/services/agent.py` ограниченным последовательным workflow с типизированными шагами, явными инструментами и структурированным JSON-отчётом. Сохранять журнал в существующем `TrackedItem.report`, отдавать его через текущий tracked API и показывать в интерфейсе события. Каждый вывод хранит provenance: количество и список новостных источников, профиль компании и выдержки аналитики Альфа-Банка. Чат использует тот же контекст и provenance. RAG работает по локальным материалам с ссылками; автономные агентские фреймворки и внешние AI-сервисы не используются.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, существующий LLM adapter, React, TypeScript, Zod, pytest, Vitest.

**Spec:** `docs/Новостная аналитика для принятия бизнес-решений — кейс.md` и требования пользователя в запросе.

## Global Constraints

- Использовать только разрешённые кейсом модели: Gemma 4 26B A4B, model service, model service 35B A3B, model service, model service, Kimi-K2.6.
- Не использовать внешние AI-сервисы, автономные AI-агенты или готовые мультиагентные системы как основной компонент.
- Отделять подтверждённые факты и источники от аналитики банка и выводов модели.
- Если данных профиля для расчёта недостаточно — не выдумывать их и возвращать запрос недостающего значения.
- Для каждого вывода показывать происхождение: «Новостные источники (N)», «Профиль бизнеса (N полей)», «Аналитика Альфа-Банка (N материалов)», со ссылками на конкретные основания.
- Чат события отвечает по контексту агента и показывает основания ответа; streaming не должен терять ссылки и цитируемые источники.
- Ответ LLM валидировать по общей схеме с явными лимитами длины и количества элементов; неверные и слишком длинные значения безопасно нормализовать и записывать факт исправления.
- Соблюдать текущие слои проекта: API в `back/src/back/api`, логика в `back/src/back/services`, схемы в `back/src/back/schemas`, клиентские контракты в `front/src/api`.

---

## Файлы и ответственность

- `back/src/back/services/agent.py` — оркестрация ограниченного цикла, контекст клиента/события и отчёт.
- `back/src/back/services/bank_retrieval.py` — поиск по локальному корпусу аналитики банка, возвращающий выдержки с названием и ссылкой на источник.
- `back/src/back/services/llm_contract.py` — нормализация и проверка ответа LLM по лимитам схемы с fallback на структурированный результат.
- `back/src/back/schemas/agent.py` — Pydantic-контракты журнала и итогового JSON.
- `back/src/back/api/routes/tracked.py` — запуск анализа и сериализация журнала в `report`.
- `front/src/api/schemas/tracked.ts`, `front/src/api/endpoints/tracked.ts` — контракт API и запрос журнала/повторного анализа.
- `front/src/tracked/AnalysisSteps.tsx` — отображение «Хода анализа», статусов источников и итогового числа шагов/исправлений.
- `front/src/tracked/TrackedScreen.tsx`, `front/src/tracked/tracked.css` — встраивание журнала в выбранную тему и стили.
- `front/src/event/ChatTab.tsx`, `front/src/event/EventScreen.tsx`, `back/src/back/services/chat.py` — чат по контексту анализа с видимыми основаниями ответа.
- `back/tests/test_agent.py`, `back/tests/test_bank_retrieval.py`, `back/tests/test_tracked.py`, `front/src/api/__tests__/api.test.ts`, `front/src/tracked/AnalysisSteps.test.tsx` — контрактные, сценарные и UI проверки.

## Контракт данных

Итоговый отчёт хранит `confirmed_facts: list[Fact]`, `sources: list[Source]`, `client_signals: dict`, `relevance: str`, `risks: list[str]`, `opportunities: list[str]`, `bank_analytics: list[BankExcerpt]`, `conclusions: list[Conclusion]`, `missing_data: list[str]`, `agent_steps: list[AgentStep]`, `provenance: Provenance`. `Conclusion` содержит `text`, `source_ids`, `profile_fields`, `bank_analytics_ids`, `origin` (`fact`, `bank`, `model`) и `confidence`. `Provenance` хранит количества `source_count`, `profile_field_count`, `bank_analytics_count` и ссылки на использованные сущности. У `Fact` есть `text`, `status` (`confirmed`, `single_channel`, `conflicting`), `source_ids`; у `Source` — `id`, `title`, `url`, `channel`; у `BankExcerpt` — `id`, `title`, `excerpt`, `url`; у `AgentStep` — `type`, `text`, `at`, `tool`, `request`, `result`, `status`. Лимиты контракта: вывод — 2000 символов, риски/возможности/выводы — до 8 элементов, шаги — до 30, источники — до 50, банковские выдержки — до 10. Pydantic ограничивает и валидирует эти значения, а UI-схема Zod использует те же пределы; нормализация LLM не должна молча нарушать контракт.

### Task 1: Контракты отчёта и журнала

**Files:** создать `back/src/back/schemas/agent.py`; тест `back/tests/test_agent.py`.

**Interfaces:** Производит Pydantic-модели `AgentStep`, `AgentReport`, `Fact`, `Source`, `BankExcerpt`; сериализация через `model_dump(mode="json")`.

- [ ] **Step 1: Добавить тесты валидации** — проверить допустимые типы шага, статусы факта и JSON round-trip полного `AgentReport`.
- [ ] **Step 2: Запустить** `cd back && uv run pytest tests/test_agent.py -q`; ожидается FAIL до появления схем.
- [ ] **Step 3: Реализовать перечисления и модели** из контракта выше; поля `agent_steps` и списки по умолчанию создавать через `Field(default_factory=list)`.
- [ ] **Step 4: Повторить тест**; ожидается PASS.

### Task 2: Извлечение аналитики Альфа-Банка

**Files:** создать `back/src/back/services/bank_retrieval.py`; тест `back/tests/test_bank_retrieval.py`.

**Interfaces:** `async def retrieve_bank_analytics(query: str, limit: int = 3) -> list[BankExcerpt]`; индексировать только имеющиеся локальные материалы кейса/аналитики, не обращаться к внешнему AI.

- [ ] **Step 1: Тестом задать** fixture из двух локальных документов: запрос про ставку должен вернуть подходящий документ с названием, выдержкой и ссылкой; нерелевантный запрос — пустой список.
- [ ] **Step 2: Запустить** `cd back && uv run pytest tests/test_bank_retrieval.py -q`; ожидается FAIL.
- [ ] **Step 3: Реализовать** простой поиск по локальным документам с нормализацией текста и ранжированием совпадений; не добавлять vector DB без наличия готового корпуса/инфраструктуры.
- [ ] **Step 4: Проверить** сохранение трассировки до исходного документа и PASS тестов.

### Task 3: Последовательный агентский цикл

**Files:** изменить `back/src/back/services/agent.py`; тесты `back/tests/test_agent.py`.

**Interfaces:** `async def analyze_tracked_event(profile, event, categories, counterparties, report=None) -> AgentReport`; инструменты — функции проекта для профиля/отчётности, retrieval Task 2, существующие источники/каналы, детерминированный калькулятор.

- [ ] **Step 1: Написать тесты** с подменёнными инструментами: цикл пишет план, поиск, данные профиля, аналитику банка, расчёт, проверку и завершение; каждый инструментальный шаг содержит запрос и результат.
- [ ] **Step 2: Запустить** `cd back && uv run pytest tests/test_agent.py -q`; ожидается FAIL.
- [ ] **Step 3: Реализовать** последовательный цикл: план → первоисточник и каналы → профиль/отчётность → банковский RAG → расчёт → самопроверка → вывод. Передавать результаты между шагами как `AgentReport`/JSON; ошибки и нехватку данных фиксировать шагом, не скрывать.
- [ ] **Step 4: Добавить адаптацию:** при расхождении фактов помечать `conflicting`; при одном канале — `single_channel`; при отсутствующем обязательном значении добавлять `missing_data`, шаг «Не хватает данных» и пропускать соответствующий расчёт; исправление после проверки писать отдельным шагом с текстом «Нашёл неточность и исправил».
- [ ] **Step 5: Проверить** тестами, что роль и `reporting_context(profile)` влияют на фокус/базу, но отсутствующие числа не генерируются; выполнить тесты Task 3.
- [ ] **Step 6: Проверить provenance** каждого вывода: его ссылки на новости, поля профиля и выдержки банка должны быть подмножеством реально полученных данных, а счётчики должны совпадать с deduplicated списками.

### Task 4: Подключение к tracked API

**Files:** изменить `back/src/back/api/routes/tracked.py`; тест `back/tests/test_tracked.py`.

**Interfaces:** существующий endpoint чтения отдаёт расширенный `report`; endpoint reanalyze запускает `analyze_tracked_event` для принадлежащей профилю записи и сохраняет результат в `TrackedItem.report`.

- [ ] **Step 1: Добавить тесты** успешного reanalyze, доступности `agent_steps` при чтении и 404 для записи другого профиля.
- [ ] **Step 2: Запустить** `cd back && uv run pytest tests/test_tracked.py -q`; ожидается FAIL.
- [ ] **Step 3: Подключить workflow** к текущему маршруту повторного анализа; сохранять отчёт, включая журнал, в JSON-поле модели без новой миграции, если тип поля это допускает.
- [ ] **Step 4: Проверить** `cd back && uv run pytest tests/test_tracked.py tests/test_agent.py tests/test_bank_retrieval.py -q`.

### Task 5: Контракт LLM и безопасное согласование размеров

**Files:** создать `back/src/back/services/llm_contract.py`; обновить `back/src/back/llm/prompts.py`; тесты `back/tests/test_agent.py`.

**Interfaces:** `normalize_agent_output(raw: dict[str, Any]) -> AgentReport`; единые лимиты берутся из схемы Task 1. До передачи в Pydantic ограничить коллекции и строки, проверить обязательные поля и согласованность provenance.

- [ ] **Step 1: Написать тесты** на строку длиннее 2000 символов, список больше 8, неизвестные поля, неверные типы и отсутствующие поля; ожидать корректно ограниченный отчёт или типизированный fallback, без исключения на пользовательском запросе.
- [ ] **Step 2: Реализовать** строгую JSON-генерацию по той же схеме и post-parse нормализацию; все обрезки/исправления заносить в `agent_steps` с флагом коррекции.
- [ ] **Step 3: Проверить** лимиты и сериализацию round-trip теми же числами в Pydantic и Zod.

### Task 6: «Ход анализа», происхождение выводов и чат

**Files:** изменить `front/src/api/schemas/tracked.ts`, `front/src/api/endpoints/tracked.ts`, `front/src/tracked/TrackedScreen.tsx`, `front/src/tracked/tracked.css`; создать `front/src/tracked/AnalysisSteps.tsx` и `front/src/tracked/AnalysisSteps.test.tsx`.

**Interfaces:** `AnalysisSteps({ report }: { report: AgentReport })`; Zod-схема принимает контракт Task 1 и legacy-пустой объект. Переиспользовать `tracked.reanalyze` и polling существующего tracked query.

- [ ] **Step 1: Добавить тесты** отображения шага с временем/инструментом/запросом/результатом; у каждого вывода показывать источник основания и счётчики новостей, профиля бизнеса и банковской аналитики. Проверить чат: ответ, loading/error и те же ссылки на основания.
- [ ] **Step 2: Запустить** `cd front && bun run test:visual -- --run src/tracked/AnalysisSteps.test.tsx`; ожидается FAIL, если тестовый script не принимает путь — запустить тест штатным runner из `package.json`.
- [ ] **Step 3: Реализовать** компактный журнал и provenance-карточку в теме; встроить чат события в существующий `ChatTab`, передавать вопрос и показывать ответ вместе с источниками. В desktop/mobile использовать одинаковые данные и счётчики; старый отчёт без полей должен корректно отображаться.
- [ ] **Step 4: Проверить** схемы API, тест компонента и `cd front && bun run build`.

### Task 7: Сквозная проверка сценария

**Files:** затронутые файлы Tasks 1–5.

- [ ] **Step 1: Запустить backend проверки** `cd back && uv run pytest -q && uv run ruff check .`.
- [ ] **Step 2: Запустить frontend проверки** `cd front && bun run build && bun run test:visual`.
- [ ] **Step 3: Сверить кейс:** подтверждённые факты, источники, клиентские признаки, релевантность, риски/возможности, аналитика банка и выводы видны отдельно; роль и отчётность влияют на оценку; конфликтующие и одноканальные сведения помечены; итог показывает число шагов и исправлений.

## Самопроверка плана

- Требования кейса покрыты Tasks 1–7, включая разрешённые модели, связь выводов с источниками, роль и отчётность.
- Требования пользователя по планированию, вызовам инструментов, структурированному контексту, самопроверке, нехватке/противоречию данных, чату, UI-журналу и источникам каждого вывода покрыты Tasks 1–6.
- В план не включена неподтверждённая интеграция с внешним поиском или новая база векторов: сначала используется реально имеющийся локальный корпус.
