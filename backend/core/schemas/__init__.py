"""
Reusable response schemas for Django Ninja controllers.

Usage:
    from core.schemas import MessageOut, ErrorOut

    @router.post("/action", response=MessageOut)
    def my_action(request):
        return MessageOut(detail="Operation completed successfully.")

NOTE: Prefer ModelSchema over manual Schema when a Django model exists.
    from ninja_schema import ModelSchema
    from modulos.identidad.models import User

    class UserOut(ModelSchema):
        class Meta:
            model = User
            fields = ["id", "email", "first_name"]
"""

from ninja import Schema
from typing import Generic, TypeVar, Optional

T = TypeVar("T")
IDType = TypeVar("IDType")


class SuccessOut(Schema, Generic[T]):
    """
    Estructura genérica para respuestas exitosas (200, 201).
    Permite estandarizar mensajes y envolver los datos devueltos.
    """

    message: str
    data: Optional[T] = None


class MessageOut(Schema):
    """Standard success response with a detail message."""

    detail: str


class M2MDiffSchema(Generic[IDType], Schema):
    """Schema for Many-to-Many delta processing (add/remove)."""

    add: list[IDType] = []
    remove: list[IDType] = []


class ErrorOut(Schema):
    """Standard error response."""

    detail: str
    code: str | None = None
