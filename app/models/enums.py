import enum


class PeriodType(str, enum.Enum):
    month = "month"
    quarter = "quarter"


class SchemeStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class AccessRole(str, enum.Enum):
    methodologist = "methodologist"
    head = "head"
    employee = "employee"
    admin = "admin"
