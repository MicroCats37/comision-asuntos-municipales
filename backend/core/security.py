from typing import List, Union, Any
import warnings
from functools import wraps

from django.db import models
from django.http import HttpRequest, HttpResponse, JsonResponse
from ninja_extra import permissions
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_jwt.exceptions import AuthenticationFailed, TokenError


class OptionalJWTAuth(JWTAuth):
    """
    JWT Auth opcional para endpoints semi-públicos.
    Retorna None si el token es inválido en lugar de lanzar error.
    """

    def authenticate(self, request, token: str):
        try:
            return super().authenticate(request, token)
        except Exception:
            return None


def verify_user_permissions(user, permisos: list, requerir_todos: bool = True) -> bool:
    """
    Centralized function to validate user permissions.

    All business permissions live under the app_label 'core'
    (anchored in the proxy model SystemPermissions).

    The 'core.' prefix is automatically added if the codename doesn't contain a dot.
    This allows using TextChoices directly without worrying about the prefix.

    Examples:
        verify_user_permissions(user, [AccommodationPermissions.MANAGE_BUNGALOWS])
        # Evaluates: user.has_perm("core.acc_manage_bungalows")
    """
    if not user or not user.is_authenticated:
        return False

    # Superusuario siempre tiene acceso
    if user.is_superuser:
        return True

    permisos_finales = []
    for p in permisos:
        p_str = p.value if hasattr(p, "value") else str(p)
        # Si el codename ya incluye un prefijo de app (contiene '.'), lo dejamos tal cual.
        # De lo contrario, lo anclamos a 'core.' donde vive SystemPermissions.
        permisos_finales.append(p_str if "." in p_str else f"core.{p_str}")

    if requerir_todos:
        return all(user.has_perm(p) for p in permisos_finales)
    return any(user.has_perm(p) for p in permisos_finales)


def verificar_permisos_usuario(*args, **kwargs):
    """Deprecated: Use verify_user_permissions() instead."""
    warnings.warn(
        "verificar_permisos_usuario is deprecated. Use verify_user_permissions() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return verify_user_permissions(*args, **kwargs)


from django.http import HttpRequest


class CheckPermission(permissions.BasePermission):
    """
    Validador de permisos para usar nativamente en Ninja Extra Controllers.

    Soporta:
    - Lógica AND (requerir_todos=True, por defecto): Todos los permisos son exigidos.
    - Lógica OR (requerir_todos=False): Basta con tener al menos uno.

    Uso:
        @route.patch("/{id}/", permissions=[
            CheckPermission(SystemPermissions.Accommodation.MANAGE_BUNGALOWS)
        ])

        @route.get("/", permissions=[
            CheckPermission([PermA, PermB], requerir_todos=False)
        ])
    """

    def __init__(
        self,
        permisos: Union[models.TextChoices, str, List[Union[models.TextChoices, str]]],
        requerir_todos: bool = True,
    ):
        self.permisos = [permisos] if not isinstance(permisos, list) else permisos
        self.requerir_todos = requerir_todos

    def has_permission(self, request: HttpRequest, controller: Any) -> bool:
        user = getattr(request, "auth", None)
        return verify_user_permissions(user, self.permisos, self.requerir_todos)


# ── Swagger / OpenAPI protection ──────────────────────────────────────────────

_jwt_docs_auth = JWTAuth()


def jwt_required_docs(view):
    """django-ninja ``docs_decorator`` — exige JWT para /docs y /openapi.json.

    django-ninja sirve la documentación Swagger y el esquema OpenAPI como vistas
    Django simples, fuera del mecanismo de autenticación de los controllers, por
    lo que quedan públicas por defecto. El hook oficial ``docs_decorator``
    permite envolver esas vistas; aquí se reutiliza el mismo ``JWTAuth`` global
    de la API para que la documentación tenga exactamente el mismo requisito de
    credencial que el resto de operaciones.
    """

    @wraps(view)
    def _wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            user = _jwt_docs_auth(request)
        except (AuthenticationFailed, TokenError):
            return JsonResponse({"detail": "Unauthorized"}, status=401)
        if user is None:
            return JsonResponse({"detail": "Unauthorized"}, status=401)
        return view(request, *args, **kwargs)

    return _wrapped


__all__ = [
    "JWTAuth",
    "NinjaJWTDefaultController",
    "OptionalJWTAuth",
    "CheckPermission",
    "jwt_required_docs",
    "verify_user_permissions",
    "verificar_permisos_usuario",
]
