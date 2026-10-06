import logging
from django.db import IntegrityError
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
    PermissionDenied,
    ObjectDoesNotExist,
)
from ninja.errors import HttpError, ValidationError as NinjaValidationError
from pydantic import ValidationError as PydanticValidationError
from django.http import HttpRequest
from .utils import format_errors
from .responses import error_response

# Configuración del logger para errores internos inesperados
logger = logging.getLogger(__name__)

# --- 1. Clases de Excepción Personalizadas ---


class NotFoundError(HttpError):
    """Excepción para recursos no encontrados (404)."""

    code: str = "NOT_FOUND"

    def __init__(self, resource: str, detail: str = "", code: str | None = None):
        msg = f"{resource} no encontrado"
        if detail:
            msg += f": {detail}"
        self.code = code or self.code
        super().__init__(404, msg)


class ConflictError(HttpError):
    """Excepción para conflictos de recursos, como duplicados (409)."""

    code: str = "CONFLICT"

    def __init__(
        self,
        message: str = "Conflicto con el estado actual del recurso",
        code: str | None = None,
    ):
        self.code = code or self.code
        super().__init__(409, message)


class BusinessError(HttpError):
    """Excepción para errores de lógica de negocio (400)."""

    code: str = "BUSINESS_ERROR"

    def __init__(self, message: str, code: str | None = None):
        self.code = code or self.code
        super().__init__(400, message)


class CipNotFoundError(HttpError):
    """Excepción cuando un CIP no es encontrado en la API externa (404)."""

    code: str = "CIP_NOT_FOUND"

    def __init__(self, cip: str):
        self.code = self.code
        super().__init__(404, f"CIP {cip} no encontrado")


# --- 2. Registro de Manejadores Globales ---


def register_exception_handlers(api):
    """
    Configura cómo NinjaAPI debe responder ante excepciones de Django o Pydantic.
    """

    @api.exception_handler(ObjectDoesNotExist)
    def on_object_not_found(request: HttpRequest, exc: ObjectDoesNotExist):
        """Maneja cualquier .get() de Django que no encuentre resultados."""
        body, status = error_response(
            code="NOT_FOUND",
            message="El recurso solicitado no existe.",
            details={"non_field_errors": "No se pudo encontrar el objeto solicitado."},
            status=404,
        )
        return api.create_response(request, body, status=status)

    @api.exception_handler(PermissionDenied)
    def on_permission_denied(request: HttpRequest, exc: PermissionDenied):
        """Maneja errores de permisos (403)."""
        body, status = error_response(
            code="PERMISSION_DENIED",
            message="No tienes permisos suficientes.",
            details={
                "non_field_errors": "No tienes autorización para realizar esta acción."
            },
            status=403,
        )
        return api.create_response(request, body, status=status)

    @api.exception_handler(PydanticValidationError)
    def on_pydantic_validation_error(
        request: HttpRequest, exc: PydanticValidationError
    ):
        """
        Maneja errores de validación de Pydantic (esquemas).
        Estandariza los errores para el consumo directo por el frontend.
        """
        body, status = error_response(
            code="VALIDATION_ERROR",
            message="Validation failed",
            details=format_errors(exc.errors(include_input=False)),
            status=422,
        )
        return api.create_response(request, body, status=status)

    @api.exception_handler(NinjaValidationError)
    def on_ninja_validation_error(request: HttpRequest, exc: NinjaValidationError):
        """
        Maneja errores de validación en tiempo de ejecución inyectados por el router Ninja.
        """
        body, status = error_response(
            code="VALIDATION_ERROR",
            message="Validation failed",
            details=format_errors(exc.errors),
            status=422,
        )
        return api.create_response(request, body, status=status)

    @api.exception_handler(HttpError)
    def on_http_error(request: HttpRequest, exc: HttpError):
        """Maneja errores explícitos del tipo HttpError o sus subclases."""
        code = getattr(exc, "code", "HTTP_ERROR")
        details = None
        if isinstance(exc.message, (list, dict)):
            details = exc.message
        else:
            details = {"non_field_errors": exc.message}
        body, status = error_response(
            code=code,
            message=exc.message,
            details=details,
            status=exc.status_code,
        )
        return api.create_response(request, body, status=status)

    @api.exception_handler(DjangoValidationError)
    def on_django_validation_error(request: HttpRequest, exc: DjangoValidationError):
        """Maneja errores de validación internos de Django (ej: unique_together)."""
        errors = (
            exc.message_dict
            if hasattr(exc, "message_dict")
            else {"non_field_errors": exc.messages}
        )
        body, status = error_response(
            code="VALIDATION_ERROR",
            message="Error de validación interna.",
            details=errors,
            status=400,
        )
        return api.create_response(request, body, status=status)

    @api.exception_handler(ValueError)
    def on_value_error(request: HttpRequest, exc: ValueError):
        """Maneja ValueError (ej: credenciales inválidas → 401."""
        body, status = error_response(
            code="AUTH_ERROR",
            message=str(exc),
            details={"non_field_errors": str(exc)},
            status=401,
        )
        return api.create_response(request, body, status=status)

    @api.exception_handler(IntegrityError)
    def on_integrity_error(request: HttpRequest, exc: IntegrityError):
        """Maneja conflictos de base de datos (Unique constraints, etc.)."""
        import traceback
        print("==== INTEGRITY ERROR ====")
        traceback.print_exc()
        body, status = error_response(
            code="CONFLICT",
            message="Conflicto de integridad en la base de datos.",
            details={
                "non_field_errors": "Un campo único ya existe o hay una violación de integridad."
            },
            status=409,
        )
        return api.create_response(request, body, status=status)

    @api.exception_handler(Exception)
    def on_unhandled_exception(request: HttpRequest, exc: Exception):
        """Atrapa-todo para errores inesperados del servidor (500)."""
        logger.exception("Unhandled exception: %s", exc)
        body, status = error_response(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            status=500,
        )
        return api.create_response(request, body, status=status)
