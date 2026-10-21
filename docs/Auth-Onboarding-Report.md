# Отчёт: авторизация, регистрация и онбординг

Дата проверки: 21.10.2026  
Окружение: локально, FastAPI + PostgreSQL 17 (Podman), `LLM_PROVIDER=stub`  
Статус: **работает, блокеров нет**

## Кратко

Проверен полный сценарий от регистрации до готового профиля бизнеса:

- регистрация и логин по логину/паролю;
- JWT-авторизация защищённых ручек;
- выбор компании по UID;
- имя предпринимателя и название бизнеса, включая пропуск шага;
- роль в компании;
- контрагенты по платежам и их переименование;
- категории влияния и ручная правка веса;
- загрузка трёх форм отчётности;
- завершение онбординга и переход к ленте/«Отслеживаемому».

Выполнено **34 проверки**. Все соответствуют ожидаемому поведению. Одна проверка
изначально ожидала `400`, но API корректно вернул `409`: без выбранного бизнеса профиля
ещё нет, поэтому срабатывает зависимость `get_current_profile`. Это не дефект.

## Что проверялось

### 1. Авторизация

| Проверка | Ожидание | Результат |
| --- | --- | --- |
| `POST /api/auth/register`, новый логин | `201`, JWT, `next_step=business_selected` | OK |
| `POST /api/auth/register`, занятый логин | `409` | OK |
| `POST /api/auth/login`, верный пароль | `200`, JWT | OK |
| `POST /api/auth/login`, неверный пароль | `401` | OK |
| `GET /api/auth/me` с токеном | `200`, пользователь | OK |
| `GET /api/feed` без токена | `401` | OK |
| Пароль короче 6 символов | `422` (Pydantic) | контракт схемы |
| JWT | срок 7 дней, `sub=user_id`, issuer | OK |

Пароли хранятся как Argon2-хеш, в ответах не возвращаются.

### 2. Онбординг: полный путь

| Шаг | Ручка | Результат |
| --- | --- | --- |
| Состояние | `GET /api/onboarding/state` | `business_selected` |
| Поиск компании | `GET /api/businesses?search=U_57706` | найдена компания |
| Несуществующий UID | `POST /api/onboarding/business` | `404` |
| Выбор компании | `POST /api/onboarding/business` | `200`, профиль создан |
| Имя и название | `PATCH /api/onboarding/profile` | `200`, значения сохранены |
| Роль | `POST /api/onboarding/role` | `200`, `role=cfo` |
| Контрагенты | `GET /api/onboarding/counterparties` | `200`, список поставщиков/покупателей |
| Переименование | `PATCH /api/onboarding/counterparties` | `200`, `custom_name` сохранён |
| Категории | `POST /api/onboarding/categories/suggest` | `200`, категории с весами |
| Правка веса | `PATCH /api/onboarding/categories/{id}` | `200`, `is_manual=true` |
| Отчётность | `POST /api/onboarding/reporting` | `200`, 3 загрузки, `reporting_summary` заполнен |
| Завершение | `POST /api/onboarding/complete` | `200`, `completed=true` |
| Финальное состояние | `GET /api/onboarding/state` | `next_step=completed` |
| Профиль | `GET /api/profile` | имя, роль, категории, контрагенты, отчётность |
| Лента | `GET /api/feed` | `200`, события с персональной важностью |
| Отслеживание | `POST /api/feed/{id}/track` | `200`, отчёт агента с ролью и отчётностью |
| Список отслеживаемого | `GET /api/tracked` | `200` |

Для отчётности загружались три текстовых файла (баланс, ОФР, ДДС). В `reporting_summary`
попали период, выручка, прибыль, долг, проценты и денежные потоки. При `stub`-провайдере
извлечение детерминированное; при `LLM_PROVIDER=openai` контракт API не меняется.

### 3. Онбординг: путь с пропусками

Проверен сценарий «везде нажать Продолжить»:

- регистрация → выбор бизнеса;
- `POST /api/onboarding/skip` `{"step":"profile_filled"}` — остаются
  `Иван Иванов` / `Моя компания`;
- роль `owner`;
- категории через `POST /api/onboarding/categories/suggest`;
- `POST /api/onboarding/skip` `{"step":"reporting_uploaded"}` — отчётность не загружена;
- `POST /api/onboarding/complete` — `completed=true`.

Значения по умолчанию не затираются и доступны для правки в профиле.

### 4. Негативные проверки

| Сценарий | Ответ |
| --- | --- |
| `POST /api/onboarding/complete` без бизнеса | `409 Сначала выберите бизнес в онбординге` |
| `POST /api/onboarding/complete` с бизнесом, но без роли/категорий | `400 Не заполнено: роль, категории` |
| `POST /api/onboarding/business` с несуществующим UID | `404 Компания с таким UID не найдена` |
| `PATCH /api/onboarding/categories/{id}` для ненастроенной категории | `404` |
| Загрузка отчётности без файлов | `400 Загрузите хотя бы одну форму отчётности` |

## Роли

Поддерживаются значения:

- `owner` — собственник бизнеса
- `ceo` — генеральный директор
- `cfo` — финансовый директор
- `chief_accountant` — главный бухгалтер
- `treasurer` — руководитель казначейства
- `c_level` — другой C-level-руководитель
- `other_decision_maker` — иной сотрудник, влияющий на решения

Роль сохраняется в `business_profiles.role` и возвращается в профиле вместе с
`role_label`. Агент «Отслеживаемого» использует роль для акцентов и списка действий.

## Пример запроса

```bash
# регистрация
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"login":"demo_user","password":"secret123"}'

# логин
curl -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"login":"demo_user","password":"secret123"}'

# выбор компании
curl -X POST http://localhost:8000/api/onboarding/business \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"uid":"U_57706"}'

# роль
curl -X POST http://localhost:8000/api/onboarding/role \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"role":"cfo"}'

# отчётность: три формы одним multipart-запросом
curl -X POST http://localhost:8000/api/onboarding/reporting \
  -H "Authorization: Bearer $TOKEN" \
  -F 'balance=@balance.txt' \
  -F 'income=@income.txt' \
  -F 'cash_flow=@cash_flow.txt'
```

## Найденные и исправленные проблемы

Во время проверки:

1. **`MissingGreenlet` при создании tracked-отчёта.** Причина — ленивая загрузка
   `BusinessCategory.category` в async-сессии. Исправлено: категории загружаются через
   `selectinload` в `services/personalization.py`.
2. **Не импортировался `Counterparty` в роуте онбординга.** Исправлено, переименование
   контрагентов работает.
3. **Типовые ошибки в seed/импорте.** Исправлены аннотации и парсинг, `mypy` проходит.

## Ограничения

- Регистрация открытая, без подтверждения email и rate limiting — для прототипа.
- Пароль проверяется только по длине; требования к сложности не заданы.
- Пользователь привязан к одному профилю бизнеса.
- В прототипе нет восстановления пароля и смены пароля.
- При `LLM_PROVIDER=stub` тексты разбора детерминированные; это ожидаемо и не влияет
  на API-контракт.

## Как повторить

```bash
cd back
podman-compose up -d postgres
uv run alembic upgrade head
uv run python scripts/seed.py --reset
uv run uvicorn back.main:app --reload
```

Демо-учётки:

- `demo` / `demo` — чистый онбординг;
- `demo_full` / `demo` — уже заполненный профиль.

Временные пользователи, созданные в ходе проверки, удалены. В БД остались только
`demo` и `demo_full`.

## Вывод

Авторизация, регистрация, логин и онбординг работают исправно. Полный путь и путь
с пропусками проходят, значения по умолчанию сохраняются, роль и отчётность попадают
в профиль и в отчёт агента. Открытых дефектов по этому блоку нет.
