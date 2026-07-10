"""Tests for RBAC: 401 without token, 403 for wrong role."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _auth(role: str, login: str = "user") -> dict[str, str]:
    return {"Authorization": f"Bearer {role}:{login}"}


# ---- admin endpoints ----


def test_admin_audit_requires_auth() -> None:
    resp = client.get("/admin/audit")
    assert resp.status_code == 401


def test_admin_audit_forbidden_for_employee() -> None:
    resp = client.get("/admin/audit", headers=_auth("employee"))
    assert resp.status_code == 403


def test_admin_audit_allowed_for_admin() -> None:
    # raise_server_exceptions=False so DB-connection errors become 500, not exceptions
    c = TestClient(app, raise_server_exceptions=False)
    resp = c.get("/admin/audit", headers=_auth("admin"))
    assert resp.status_code not in (401, 403)


def test_admin_users_forbidden_for_methodologist() -> None:
    resp = client.get("/admin/users", headers=_auth("methodologist"))
    assert resp.status_code == 403


def test_invalid_token_returns_401() -> None:
    resp = client.get("/admin/audit", headers={"Authorization": "Bearer badtoken"})
    assert resp.status_code == 401
