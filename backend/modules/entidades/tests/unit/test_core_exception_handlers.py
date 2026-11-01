"""
Unit tests del contrato central de errores (backend/core/exceptions.py).

Verifica el ENVELOPE que produce el frontend:

- `error.message` es SIEMPRE un texto humano (nunca una clave interna).
- `error.details` sólo contiene errores de CAMPO (nunca la clave global
  `non_field_errors` duplicando el mensaje).
- Los mensajes no son texto técnico en inglés.

Estos handlers son closures registrados dentro de `register_exception_handlers`,
por lo que se testean con un doble de la API de Ninja (sin HTTP ni base de
datos).
"""

import pytest
from django.core.exceptions import PermissionDenied
from ninja.errors import HttpError
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import register_exception_handlers
from core.utils import format_errors


class FakeNinjaApi:
    """Doble mínimo de NinjaAPI para capturar los exception handlers."""

    def __init__(self):
        self.handlers = {}

    def exception_handler(self, exc_class):
        def decorator(func):
            self.handlers[exc_class] = func
            return func

        return decorator

    def create_response(self, request, body, status=None):
        return body, status


@pytest.fixture
def handlers():
    api = FakeNinjaApi()
    register_exception_handlers(api)
    return api.handlers


def test_http_error_preserves_the_human_message_without_duplicating_it(handlers):
    """GIVEN: un HttpError con mensaje humano
    WHEN: se resuelve el envelope
    THEN: el mensaje vive en error.message y details no lo duplica
    """
    body, status = handlers[HttpError](
        None, HttpError(400, "Referencia de archivo rota: 'x.png' no se encontró.")
    )

    assert status == 400
    assert body["success"] is False
    assert body["error"]["message"] == (
        "Referencia de archivo rota: 'x.png' no se encontró."
    )
    assert body["error"]["details"] is None


def test_validation_error_is_human_readable_and_keeps_the_field_keys(handlers):
    """GIVEN: un error de validación de Pydantic
    WHEN: se resuelve el envelope
    THEN: el mensaje es humano y details conserva las claves de campo
    """
    try:
        raise PydanticValidationError.from_exception_data(
            "LoginIn",
            [
                {
                    "type": "missing",
                    "loc": ("username",),
                    "input": None,
                }
            ],
        )
    except PydanticValidationError as exc:
        body, status = handlers[PydanticValidationError](None, exc)

    assert status == 422
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Error de validación."
    assert body["error"]["details"] == {"username": "Field required"}


def test_unhandled_exception_message_is_human_readable(handlers):
    body, status = handlers[Exception](None, Exception("boom"))

    assert status == 500
    assert body["error"]["message"] == (
        "Ocurrió un error inesperado. Inténtelo nuevamente."
    )
    assert body["error"]["details"] is None


def test_permission_denied_message_is_human_readable(handlers):
    body, status = handlers[PermissionDenied](None, PermissionDenied())

    assert status == 403
    assert body["error"]["message"] == "No tienes permisos suficientes."
    assert body["error"]["details"] is None


def test_format_errors_groups_global_errors_without_the_literal_key():
    """GIVEN: errores de Pydantic, uno sin campo y dos del mismo campo
    WHEN: se formatean
    THEN: el error global usa la clave vacía y los mensajes de un campo se acumulan
    """
    formatted = format_errors(
        [
            {"loc": (), "msg": "Los datos están duplicados."},
            {"loc": ("body", "email"), "msg": "Ingresa un correo válido."},
            {"loc": ("body", "email"), "msg": "El correo ya existe."},
        ]
    )

    assert formatted == {
        "": "Los datos están duplicados.",
        "email": "Ingresa un correo válido.; El correo ya existe.",
    }
    assert "non_field_errors" not in formatted
