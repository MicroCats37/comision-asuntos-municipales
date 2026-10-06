"""
Esquemas de resultado de dominio para Auth — DTOs internos usados por servicios, NO esquemas HTTP.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel


class AuthUserResult(BaseModel):
    """DTO de resultado interno con datos de usuario para generación de tokens."""
    id: uuid.UUID
    username: str
    dni: str | None
    email: str | None
    nombres: str | None
    apellidos: str | None
    is_staff: bool
    is_superuser: bool


class LoginTokenResult(BaseModel):
    """DTO de resultado para operaciones de login — contiene tokens y datos del usuario."""
    access_token: str
    refresh_token: str
    expires_at: datetime
    user: AuthUserResult
