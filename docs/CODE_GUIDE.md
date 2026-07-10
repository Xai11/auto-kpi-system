# Ключевые функционалы системы KPI — аннотированный разбор кода

Документ разбирает пять модулей, составляющих ядро системы: схему конфигурации правил,
расчётный движок, версионирование, оркестрацию расчёта и расчётный лист.
Каждый блок кода снабжён построчными пояснениями.

---

## 1. Схема конфигурации правил (`app/schemas/rule_config.py`)

Правила расчёта — это **данные**, а не код. Конфигурация хранится в поле `config` (JSONB)
таблицы `scheme_version`. Данный модуль описывает контракт: что именно может лежать в этом
поле. Pydantic проверяет корректность при сохранении версии; неверные данные отклоняются
с ошибкой ещё на API-уровне, до записи в БД.

```python
class ScaleStep(BaseModel):
    # Нижняя граница диапазона (алиас "from", т.к. from — зарезервированное слово Python)
    from_: Decimal = Field(alias="from")
    # Верхняя граница диапазона (не включается: from <= performance < to)
    to: Decimal
    # Коэффициент, который применяется к базовой ставке в этом диапазоне
    coefficient: Decimal

    # populate_by_name=True позволяет передавать как from_, так и from при создании объекта
    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def check_range(self) -> ScaleStep:
        # Гарантируем, что from < to; иначе шкала некорректна
        if self.from_ >= self.to:
            raise ValueError("scale step: 'from' must be less than 'to'")
        return self


class Component(BaseModel):
    # Код метрики из каталога (таблица metric.code); по нему находится фактическое значение
    metric: str
    # Плановое значение показателя; на него делим факт → получаем степень выполнения
    plan: Decimal = Field(gt=0)
    # Базовая ставка в рублях; умножается на коэффициент шкалы и вес
    base_rate: Decimal = Field(ge=0)
    # Вес компонента в итоговой сумме (по умолчанию 1.0 — полный вес)
    weight: Decimal = Field(default=Decimal("1.0"), gt=0)
    # Ступенчатая шкала: список диапазонов "от–до" с коэффициентом
    scale: list[ScaleStep] = Field(min_length=1)

    @model_validator(mode="after")
    def check_scale_contiguous(self) -> Component:
        # Сортируем шаги по нижней границе и проверяем, что конец каждого шага
        # совпадает с началом следующего — шкала не должна содержать пробелов
        steps = sorted(self.scale, key=lambda s: s.from_)
        for i in range(1, len(steps)):
            if steps[i].from_ != steps[i - 1].to:
                raise ValueError(f"scale steps are not contiguous at index {i}: ...")
        return self


class Modifier(BaseModel):
    # Тип: "bonus" (прибавка) или "penalty" (штраф)
    type: str
    # Код модификатора; используется как метка в декомпозиции расчётного листа
    code: str
    # Сумма в рублях; для штрафа — отрицательная (например, -3000)
    amount: Decimal


class Limits(BaseModel):
    # Минимальный итог (например, 0 — итог не может быть отрицательным)
    min: Decimal | None = None
    # Максимальный итог (cap на выплату)
    max: Decimal | None = None


class EditableField(BaseModel):
    # Путь к полю в config (dot-notation), которое руководитель может менять
    # Пример: "components.0.plan" — плановый показатель первого компонента
    path: str
    # Допустимый минимум для этого поля (если None — ограничений нет)
    min: Decimal | None = None
    # Допустимый максимум для этого поля
    max: Decimal | None = None


class RuleConfig(BaseModel):
    # Список компонентов расчёта; обязателен хотя бы один
    components: list[Component] = Field(min_length=1)
    # Модификаторы (бонусы/штрафы); могут отсутствовать
    modifiers: list[Modifier] = Field(default_factory=list)
    # Ограничители итоговой суммы
    limits: Limits = Field(default_factory=Limits)
    # Параметры, открытые для редактирования руководителем (роль head)
    editable: list[EditableField] = Field(default_factory=list)
```

**Где используется:** `RuleConfigService.create_version()` валидирует конфиг через
`RuleConfig.model_validate(...)` перед записью в БД. `update_params()` строит словарь
`editable_map` для проверки границ при patch-операциях роли `head`.

---

## 2. Расчётный движок (`app/services/calculation.py`)

Ядро системы: чистые функции без побочных эффектов. Принимают словарь фактических
значений и конфиг из JSONB — возвращают итоговую сумму и список шагов декомпозиции.
Детерминированы: один и тот же вход всегда даёт один и тот же результат.

```python
def resolve_threshold(scale: list[dict], performance: Decimal) -> Decimal:
    # Получаем степень выполнения как float для сравнения с границами шкалы
    p = float(performance)
    for step in scale:
        # Ищем диапазон: from <= performance < to
        # Условие "< to" означает верхнюю границу не включаем (полуоткрытый интервал)
        if step["from"] <= p < step["to"]:
            # Возвращаем Decimal, чтобы последующий расчёт сохранял точность
            return Decimal(str(step["coefficient"]))
    # Если не попали ни в один диапазон — коэффициент 0 (нет выплаты)
    return Decimal("0")


def calculate_reward(
    metrics: dict[str, Decimal],   # {код_метрики: фактическое_значение}
    config: dict,                   # содержимое scheme_version.config
) -> tuple[Decimal, list[dict]]:
    steps = []       # шаги для расчётного листа (декомпозиция)
    total = Decimal("0")

    # ── Шаг 1: Компоненты ──────────────────────────────────────────────
    for i, comp in enumerate(config["components"]):
        # Берём фактическое значение метрики (0 если данных нет)
        value = Decimal(str(metrics.get(comp["metric"], 0)))
        plan  = Decimal(str(comp["plan"]))

        # Степень выполнения: факт / план (например, 0.8 = 80%)
        performance = (value / plan) if plan else Decimal("0")

        # Коэффициент по ступенчатой шкале (Strategy: шкала — это данные, не ветки if/else)
        coeff = resolve_threshold(comp["scale"], performance)

        weight    = Decimal(str(comp.get("weight", 1)))
        base_rate = Decimal(str(comp["base_rate"]))

        # Итог компонента: ставка × коэффициент × вес
        amount = base_rate * coeff * weight
        total += amount

        # Сохраняем шаг для расчётного листа; сотрудник увидит каждую строку
        steps.append({
            "step_no":     i + 1,
            "description": f"Компонент: {comp['metric']}",
            "metric":      comp["metric"],
            "value":       float(value),        # фактическое значение показателя
            "plan":        float(plan),          # плановое значение
            "performance": round(float(performance), 4),  # степень выполнения (округлённая)
            "coefficient": float(coeff),         # коэффициент из шкалы
            "amount":      float(amount.quantize(Decimal("0.01"))),  # сумма компонента
        })

    # ── Шаг 2: Модификаторы ────────────────────────────────────────────
    for j, mod in enumerate(config.get("modifiers", [])):
        amount = Decimal(str(mod["amount"]))
        total += amount  # бонус прибавляется, штраф (отрицательный) вычитается
        steps.append({
            "step_no":     len(config["components"]) + j + 1,
            "description": f"Модификатор: {mod['code']}",
            "modifier":    mod["code"],
            "type":        mod["type"],   # "bonus" или "penalty"
            "amount":      float(amount),
        })

    # ── Шаг 3: Ограничители итога ──────────────────────────────────────
    limits = config.get("limits", {})
    if "min" in limits and limits["min"] is not None:
        # Итог не может быть ниже минимума (например, 0 — нет отрицательных выплат)
        total = max(total, Decimal(str(limits["min"])))
    if "max" in limits and limits["max"] is not None:
        # Cap на выплату — итог не превысит максимума
        total = min(total, Decimal(str(limits["max"])))

    # Округляем до 2 знаков (рубли и копейки); Decimal гарантирует точность
    return total.quantize(Decimal("0.01")), steps
```

**Почему нет формул в коде:** все числа (ставки, планы, шкалы, лимиты) живут в `config`.
Движок только интерпретирует структуру. Чтобы изменить правила расчёта для подразделения —
методолог создаёт новую версию конфига; код не трогается.

---

## 3. Версионирование правил (`app/services/rules.py` + `app/repositories/rules.py`)

Опубликованные версии неизменны. Каждое изменение правил — это новая версия
со статусом `draft → published` и датой вступления в силу (`effective_from`).
Это позволяет воспроизвести расчёт за любой прошлый период по действовавшим тогда правилам.

```python
# ── Декодер Decimal → float для JSONB ──────────────────────────────────
class _DecimalEncoder(json.JSONEncoder):
    # PostgreSQL JSONB не знает тип Decimal; нужно конвертировать в float
    # (json.dumps по умолчанию выбрасывает TypeError на Decimal)
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)   # число в JSONB, не строка "30000" — важно для сравнений движка
        return super().default(o)


class RuleConfigService:

    def create_version(self, scheme_id: int, data: VersionCreate) -> SchemeVersion:
        # 1. Валидация конфига Pydantic-схемой; бросает ValidationError при ошибке
        validated = RuleConfig.model_validate(data.config.model_dump(by_alias=True))

        # 2. Сериализация: Decimal → float, чтобы JSONB хранил числа, а не строки
        #    json.dumps(..., cls=_DecimalEncoder) → строка JSON с числами
        #    json.loads(...)                      → словарь Python с float
        config_dict = json.loads(
            json.dumps(validated.model_dump(by_alias=True), cls=_DecimalEncoder)
        )

        # 3. Создаём запись в БД со статусом draft (ещё не активна)
        v = self._versions.create_draft(
            scheme_id=scheme_id,
            config=config_dict,
            effective_from=data.effective_from,
        )
        self.db.commit()
        self.db.refresh(v)
        return v   # возвращаем черновик; клиент увидит id для последующей публикации

    def publish_version(self, version_id: int, effective_from: date) -> SchemeVersion:
        v = self._versions.get_by_id(version_id)
        # Только черновики можно публиковать; повторная публикация — ошибка
        if v.status != SchemeStatus.draft:
            raise ValueError(f"Only draft versions can be published")
        v.status = SchemeStatus.published   # переводим в активный статус
        v.effective_from = effective_from   # с какой даты действует
        self.db.commit()
        return v   # после этого версия доступна движку; изменить её нельзя

    def update_params(self, version_id: int, patches: dict) -> SchemeVersion:
        """
        Позволяет руководителю (роль head) менять только разрешённые параметры
        черновика в пределах заданных границ min/max.
        """
        v = self._versions.get_by_id(version_id)
        # Опубликованную версию менять нельзя — создаётся новая версия
        if v.status == SchemeStatus.published:
            raise ValueError("Cannot modify a published version")

        # Строим словарь {path: EditableField} из списка editable в конфиге
        config = RuleConfig.model_validate(v.config)
        editable_map = {e.path: e for e in config.editable}

        for path, value in patches.items():
            # Путь должен быть явно разрешён; произвольное изменение — ошибка
            if path not in editable_map:
                raise ValueError(f"Path '{path}' is not in editable list")
            boundary = editable_map[path]
            dec_val = Decimal(str(value))
            # Проверяем границы min/max, установленные методологом
            if boundary.min is not None and dec_val < boundary.min:
                raise ValueError(...)
            if boundary.max is not None and dec_val > boundary.max:
                raise ValueError(...)
            # Применяем патч: dot-notation "components.0.plan" → dict navigation
            _apply_patch(v.config, path, dec_val)

        # Повторная валидация Pydantic: убеждаемся, что после патча конфиг всё ещё корректен
        RuleConfig.model_validate(v.config)
        # flag_modified нужен SQLAlchemy, чтобы увидеть изменения внутри JSONB-словаря
        flag_modified(v, "config")
        self.db.commit()
        return v


# ── Поиск действующей версии ────────────────────────────────────────────
class VersionRepository:

    def get_effective_version(self, scheme_id: int, on_date: date) -> SchemeVersion | None:
        """
        Возвращает опубликованную версию схемы, действовавшую на указанную дату.
        Выбирает версию с максимальной effective_from, не превышающей on_date.
        Это гарантирует воспроизводимость: пересчёт за прошлый период всегда берёт
        те же правила, что действовали тогда.
        """
        stmt = (
            select(SchemeVersion)
            .where(
                SchemeVersion.scheme_id == scheme_id,
                SchemeVersion.status == SchemeStatus.published,   # только опубликованные
                SchemeVersion.effective_from <= on_date,          # вступила в силу до/в этот день
            )
            .order_by(SchemeVersion.effective_from.desc())  # самая свежая из подходящих
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()
```

---

## 4. Оркестрация расчёта (`app/services/orchestration.py`)

Координирует полный цикл расчёта за период: обходит активных сотрудников, для каждого
находит действующую версию правил, загружает фактические значения, вызывает движок,
сохраняет результат и шаги декомпозиции. Один `commit` на весь период — транзакционность.

```python
class OrchestrationService:

    def run_calculation(self, period_id: int) -> dict:
        period = self._get_period(period_id)  # проверяет существование периода

        # Только сотрудники, активные на дату начала периода (hired_at <= date < fired_at)
        employees = self._employees.get_active_on(period.date_start)

        saved = 0
        for employee in employees:
            # Находим схему мотивации сотрудника (по подразделению или роли)
            # и берём версию правил, действовавшую на начало периода
            version = self._get_effective_version(employee, period)
            if version is None:
                continue  # у сотрудника нет схемы — пропускаем без ошибки

            # Загружаем фактические значения метрик за период {код: значение}
            metrics = self._get_metric_values(employee.id, period_id)

            # Вызываем чистый движок: конфиг + факт → итог + шаги
            total, steps = calculate_reward(metrics, version.config)

            # Сохраняем calculation_result + decomposition_step (flush без commit)
            self._save_result(employee.id, period_id, version.id, total, steps)
            saved += 1

        # Единственный commit: либо все результаты сохранены, либо ни одного
        self.db.commit()
        return {"period_id": period_id, "calculated": saved}

    def recalculate(self, period_id: int) -> dict:
        # Удаляем существующие результаты (cascade удалит и decomposition_step)
        existing = self.db.execute(
            select(CalculationResult).where(CalculationResult.period_id == period_id)
        ).scalars().all()
        for r in existing:
            self.db.delete(r)
        self.db.flush()   # применяем удаление до нового расчёта (в той же транзакции)
        return self.run_calculation(period_id)

    def _get_effective_version(self, employee, period) -> SchemeVersion | None:
        # Ищем схему мотивации: сначала по подразделению, потом по роли
        # (условие OR — один запрос вместо двух)
        stmt = (
            select(MotivationScheme)
            .where(
                (MotivationScheme.department_id == employee.department_id)
                | (MotivationScheme.role_id == employee.role_id)
            )
            .limit(1)
        )
        scheme = self.db.execute(stmt).scalar_one_or_none()
        if scheme is None:
            return None  # нет схемы — нечего считать

        # Делегируем поиск версии репозиторию (бизнес-правило: max effective_from <= date)
        return self._versions.get_effective_version(scheme.id, period.date_start)

    def _save_result(self, employee_id, period_id, version_id, total, steps) -> None:
        # Создаём запись итога (заголовок расчётного листа)
        result = CalculationResult(
            employee_id=employee_id,
            period_id=period_id,
            scheme_version_id=version_id,  # ссылка на версию правил — для аудита
            total_amount=total,
            calculated_at=datetime.utcnow(),
        )
        self.db.add(result)
        self.db.flush()  # получаем result.id до создания шагов (нужен как FK)

        # Создаём строки декомпозиции: каждый шаг из движка → отдельная запись
        for i, step in enumerate(steps):
            ds = DecompositionStep(
                result_id=result.id,
                step_no=step.get("step_no", i + 1),
                description=step.get("description"),
                # coefficient может отсутствовать у модификаторов (только сумма)
                coefficient=Decimal(str(step["coefficient"])) if "coefficient" in step else None,
                subtotal=Decimal(str(step["amount"])),  # NUMERIC(14,2), не float
            )
            self.db.add(ds)
```

---

## 5. Расчётный лист и права доступа

### PayslipService (`app/services/payslip.py`)

Сотрудник получает расчётный лист: итог и постатейную декомпозицию.

```python
class PayslipService:

    def get_payslip(self, employee_id: int, period_id: int) -> PayslipRead | None:
        # Ищем последний расчёт сотрудника за период (order by calculated_at desc)
        # Последний — потому что recalculate может создать новый результат
        stmt = (
            select(CalculationResult)
            .where(
                CalculationResult.employee_id == employee_id,
                CalculationResult.period_id == period_id,
            )
            .order_by(CalculationResult.calculated_at.desc())
            .limit(1)
        )
        result = self.db.execute(stmt).scalar_one_or_none()
        if result is None:
            return None  # расчёт ещё не запускался

        # Шаги декомпозиции подгружаются через relationship result.steps
        steps = [DecompositionStepRead.model_validate(s) for s in result.steps]

        return PayslipRead(
            employee_id=employee_id,
            period_id=period_id,
            period_start=period.date_start,
            period_end=period.date_end,
            total_amount=result.total_amount,   # итог в Decimal (NUMERIC в БД)
            calculated_at=result.calculated_at,
            steps=steps,
            config=result.scheme_version.config,  # конфиг на момент расчёта (для прозрачности)
        )
```

### RBAC — аутентификация и роли (`app/core/security.py`)

```python
bearer = HTTPBearer(auto_error=False)
# auto_error=False — не бросаем 403 автоматически; обрабатываем отсутствие токена вручную

def get_current_user(credentials = Depends(bearer)) -> CurrentUser:
    if credentials is None:
        raise HTTPException(401, "Not authenticated")

    # Формат токена: "role:login" (например, "admin:alice", "employee:ivanov")
    # Простой stub — в production заменяется на JWT или OAuth2
    role_str, login = credentials.credentials.split(":", 1)
    role = AccessRole(role_str)  # валидирует, что роль существует в enum
    return CurrentUser(login=login, role=role)


def require_role(*roles: AccessRole):
    """
    Фабрика зависимостей FastAPI.
    Использование в роутере: Depends(require_role(AccessRole.admin))
    Если роль текущего пользователя не в списке — возвращает 403.
    """
    def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(403, f"Role '{user.role.value}' is not allowed here")
        return user
    return _check
```

### Пример применения в роутере (`app/api/routers/admin.py`)

```python
# Создаём проверку один раз — используем во всех эндпоинтах роутера
_only_admin = require_role(AccessRole.admin)

@router.get("/audit", response_model=list[AuditLogRead])
def list_audit(
    limit: int = 200,
    _: CurrentUser = Depends(_only_admin),  # 401 если нет токена, 403 если не admin
    db: Session = Depends(get_db),
) -> list[AuditLogRead]:
    # До этой строки доходят только пользователи с ролью admin
    svc = AuditService(db)
    logs = svc.list_logs(limit=limit)
    return [AuditLogRead.model_validate(lg) for lg in logs]

@router.get("/users", response_model=list[AppUserRead])
def list_users(
    _: CurrentUser = Depends(_only_admin),
    db: Session = Depends(get_db),
) -> list[AppUserRead]:
    # Список учётных записей — только для администратора
    users = list(db.execute(select(AppUser)).scalars().all())
    return [AppUserRead.model_validate(u) for u in users]
```

---

## Итоговая схема взаимодействия модулей

```
POST /calculations/{period_id}/run
         │
         ▼
OrchestrationService.run_calculation(period_id)
  │
  ├─► EmployeeRepository.get_active_on(date)       — активные сотрудники
  │
  ├─► [для каждого сотрудника]
  │     │
  │     ├─► VersionRepository.get_effective_version(scheme_id, date)
  │     │       SQL: WHERE status='published' AND effective_from <= date
  │     │             ORDER BY effective_from DESC LIMIT 1
  │     │
  │     ├─► MetricValue (таблица)                  — фактические показатели
  │     │
  │     └─► calculate_reward(metrics, config)       — чистый движок
  │               │
  │               ├─► resolve_threshold(scale, performance)
  │               │       итерируем шкалу, возвращаем коэффициент
  │               │
  │               ├─► сумма компонентов + модификаторы
  │               └─► применяем лимиты min/max
  │
  ├─► CalculationResult + DecompositionStep (flush в транзакцию)
  │
  └─► db.commit()  — единственный commit, атомарно для всего периода


GET /payslips/{employee_id}?period_id=N
         │
         ▼
PayslipService.get_payslip(employee_id, period_id)
  └─► SELECT calculation_result + JOIN decomposition_step
      → PayslipRead (total_amount + steps с декомпозицией)
```
