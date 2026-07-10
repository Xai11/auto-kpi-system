from datetime import date

from sqlalchemy.orm import Session

from app.models import Department, Employee, Role


def test_create_read_employee(db_session: Session) -> None:
    role = Role(name="Специалист")
    dept = Department(name="Отдел взыскания", code="COLL-01")
    db_session.add_all([role, dept])
    db_session.flush()

    emp = Employee(
        personnel_no="EMP-001",
        last_name="Иванов",
        first_name="Иван",
        middle_name="Иванович",
        department_id=dept.id,
        role_id=role.id,
        hired_at=date(2024, 1, 1),
    )
    db_session.add(emp)
    db_session.flush()

    found = db_session.get(Employee, emp.id)
    assert found is not None
    assert found.personnel_no == "EMP-001"
    assert found.last_name == "Иванов"
    assert found.first_name == "Иван"
    assert found.middle_name == "Иванович"
    assert found.hired_at == date(2024, 1, 1)
    assert found.fired_at is None
    assert found.department.code == "COLL-01"
    assert found.role.name == "Специалист"
