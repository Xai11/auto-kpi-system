# Система расчёта KPI и мотивации

Конфигурируемый движок расчёта KPI и мотивации сотрудников (~900 человек).
Правила расчёта — это **данные** (JSONB-конфигурация), а не код.
Методолог меняет шкалы, ставки и модификаторы без участия разработчиков.

## Стек

- Python 3.11+, FastAPI, Pydantic v2
- SQLAlchemy 2.x + Alembic (миграции)
- PostgreSQL 15+ (JSONB для конфигурации правил)

---

## Быстрый старт (Docker + uv)

### 1. Запустить PostgreSQL

```bash
docker compose up -d        # поднимает postgres:16-alpine на порту 5432
                            # автоматически создаёт kpi_db и kpi_test
```

### 2. Установить зависимости

```bash
uv venv --python 3.11
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### 3. Создать `.env`

```bash
cp .env.example .env        # файл уже содержит нужные URL для Docker
```

Содержимое `.env.example`:
```
DATABASE_URL=postgresql+psycopg://kpi:kpi@localhost:5432/kpi_db
TEST_DATABASE_URL=postgresql+psycopg://kpi:kpi@localhost:5432/kpi_test
```

### 4. Применить миграцию

```bash
alembic upgrade head
```

### 5. Запустить API

```bash
uvicorn app.main:app --reload
```

Документация: <http://localhost:8000/docs>

---

## Тесты

```bash
pytest -q                   # подхватывает TEST_DATABASE_URL из .env автоматически
pytest -q -k engine         # только тесты движка (без БД)
```

Все 48 тестов: 23 unit-теста движка + 20 DB-тестов + 5 RBAC-тестов.

---

## Команды разработки

```bash
mypy app                          # проверка типов
ruff check app && ruff format app # линт и форматирование
alembic revision --autogenerate -m "msg"  # новая миграция
alembic upgrade head              # применить
```

---

## Демонстрационный кейс

Сквозной сценарий: справочники → правила → расчёт за период → расчётный лист.

```bash
python scripts/demo.py
```

**Что делает скрипт:**
1. Создаёт подразделение «Отдел продаж», роль «Менеджер», 3 сотрудников
2. Заводит метрику «Объём сборов», шаблон, схему мотивации
3. Публикует версию правил со ступенчатой шкалой:

   | Выполнение плана | Коэффициент |
   |-----------------|-------------|
   | < 80%           | 0.0         |
   | 80 – 100%       | 0.5         |
   | 100 – 120%      | 1.0         |
   | ≥ 120%          | 1.3         |

4. Создаёт период (январь 2024), вносит фактические значения
5. Запускает `run_calculation` → сохраняет результаты и декомпозицию
6. Читает расчётные листы и проверяет суммы

**Ожидаемый вывод:**
```
  ── Иванов Иван ──      (факт 800 000, 80%)
    [1] Компонент ×0.5  → 15 000.00 руб.
    [2] Бонус           →  5 000.00 руб.
  ИТОГО:  20 000.00 руб. ✓

  ── Петрова Мария ──    (факт 1 050 000, 105%)
    [1] Компонент ×1.0  → 30 000.00 руб.
    [2] Бонус           →  5 000.00 руб.
  ИТОГО:  35 000.00 руб. ✓

  ── Сидоров Алексей ── (факт 1 300 000, 130%)
    [1] Компонент ×1.3  → 39 000.00 руб.
    [2] Бонус           →  5 000.00 руб.
  ИТОГО:  44 000.00 руб. ✓
```

Скрипт работает идемпотентно: все данные откатываются в конце (SAVEPOINT-транзакция), БД остаётся чистой.

---

## API (основные эндпоинты)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | /health | Health check |
| GET/POST | /departments | Подразделения |
| GET/POST | /roles | Роли |
| GET/POST | /employees | Сотрудники |
| GET/POST | /metrics | Каталог метрик |
| GET/POST | /templates | Шаблоны расчёта |
| GET/POST | /schemes | Схемы мотивации |
| POST | /schemes/{id}/versions | Создать черновик версии |
| POST | /versions/{id}/publish | Опубликовать (`effective_from`) |
| PATCH | /versions/{id}/params | Изменить параметры (роль head) |
| POST | /calculations/{period_id}/run | Запустить расчёт за период |
| POST | /calculations/{period_id}/recalc | Пересчитать |
| GET | /payslips/{employee_id}?period_id=N | Расчётный лист с декомпозицией |
| GET | /admin/users | Пользователи (admin) |
| GET | /admin/audit | Журнал аудита (admin) |

### Аутентификация (stub)

Bearer-токен формата `role:login`, например:
```
Authorization: Bearer methodologist:alice
Authorization: Bearer admin:bob
Authorization: Bearer employee:carol
```

---

## Остановить PostgreSQL

```bash
docker compose down          # контейнер + сеть
docker compose down -v       # + удалить volume с данными
```
