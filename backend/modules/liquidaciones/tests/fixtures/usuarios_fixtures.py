"""
Usuarios fixtures — auth client, user creation.

Re-exports the canonical shared auth fixtures.

The implementation lives in ``core.testing.auth_fixtures`` so there is a single
source of truth for the JWT test pattern
(``AccessToken.for_user(user)`` + ``Authorization: Bearer <token>``).
This module keeps the historical import path used by
``modules/liquidaciones/tests/conftest.py`` and the module conftests.

Re-exports: api_client, create_user, auth_client, auth_headers, usuario_admin
"""
from core.testing.auth_fixtures import (
    api_client,
    auth_client,
    auth_headers,
    auth_token,
    create_user,
    usuario_admin,
)

__all__ = [
    "api_client",
    "auth_client",
    "auth_headers",
    "auth_token",
    "create_user",
    "usuario_admin",
]
