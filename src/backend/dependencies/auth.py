"""Authentication helpers for API routes."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status


@dataclass(slots=True)
class AuthenticatedUser:
    """Represents the authenticated caller."""

    id: str


async def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthenticatedUser:
    """Extract the caller identity from the Authorization header.

    This lightweight helper expects a ``Bearer <user-id>`` token. Real deployments
    would swap this for session cookies or JWT validation, but the important part
    is that we *do not* trust arbitrary ``userId`` values supplied in the request
    body.
    """

    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    return AuthenticatedUser(id=token)


__all__ = ["AuthenticatedUser", "get_current_user"]
