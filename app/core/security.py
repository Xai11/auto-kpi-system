"""Lightweight auth stub: token = "role:login", e.g. "admin:alice"."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.enums import AccessRole

bearer = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, login: str, role: AccessRole) -> None:
        self.login = login
        self.role = role


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    token = credentials.credentials
    try:
        role_str, login = token.split(":", 1)
        role = AccessRole(role_str)
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    return CurrentUser(login=login, role=role)


def require_role(*roles: AccessRole):  # type: ignore[no-untyped-def]
    """Dependency factory: raises 403 if current user's role is not in `roles`."""

    def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' is not allowed here",
            )
        return user

    return _check
