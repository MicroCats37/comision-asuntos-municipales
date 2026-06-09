from functools import wraps
import inspect
import json
import warnings
from typing import Callable, Any, Union, List, get_type_hints
from ninja.errors import HttpError
from .security import verify_user_permissions
from .types import parse_form_json


def requiere_permiso(
    permisos: Union[Any, List[Any]], requerir_todos: bool = True
) -> Callable:
    """Deprecated: Use CheckPermission class instead."""
    warnings.warn(
        "requiere_permiso is deprecated. Use CheckPermission(permisos) in controller permissions instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    """
    Decorador para proteger funciones de Django Ninja.
    Uso: @requiere_permiso(Permisos.VER_DATOS, requerir_todos=False)
    """
    if not isinstance(permisos, list):
        permisos = [permisos]

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request, *args: Any, **kwargs: Any) -> Any:
            user = getattr(request, "auth", None)

            if not verify_user_permissions(user, permisos, requerir_todos):
                # Si no está autenticado, verify_user_permissions devuelve False
                if not user or not user.is_authenticated:
                    raise HttpError(401, "No autenticado")
                raise HttpError(
                    403, "No tienes los permisos necesarios para esta acción"
                )

            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def parse_payload(schema_cls: type) -> Callable:
    """
    Decorator factory that parses and validates request body into a schema instance.

    Stores the parsed schema on request.parsed_payload. The endpoint should NOT
    have a 'payload' parameter (Ninja would try to parse the body and cause double-read).

    Usage:
        @parse_payload(BungalowImagenBatchIn)
        async def batch_imagenes_patch(self, bungalow_id: str, request):
            payload: BungalowImagenBatchIn = request.parsed_payload
            ...

    Supports:
        - application/json: parse with schema_cls.model_validate(json.loads(request.body))
        - multipart/form-data: use parse_form_json(data_str, file_objs, schema_cls)
    """
    def decorator(func: Callable) -> Callable:
        from .types import parse_form_json

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Locate request from args/kwargs
            request = _find_request(func, args, kwargs)
            if request is None:
                raise HttpError(500, "parse_payload could not locate request")

            # Parse based on Content-Type
            payload = _parse_payload(request, schema_cls)
            # Store on request
            request.parsed_payload = payload

            # Call with original args/kwargs exactly as passed
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            request = _find_request(func, args, kwargs)
            if request is None:
                raise HttpError(500, "parse_payload could not locate request")

            payload = _parse_payload_sync(request, schema_cls)
            request.parsed_payload = payload

            return func(*args, **kwargs)

        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

    return decorator


def _find_request(func: Callable, args: tuple, kwargs: dict):
    """Find request object from bound args/kwargs."""
    # Try bind_partial to match by parameter name
    sig = inspect.signature(func)
    try:
        bound = sig.bind_partial(*args, **kwargs)
        if "request" in bound.arguments:
            return bound.arguments["request"]
    except TypeError:
        pass
    # Fallback: direct lookup
    if "request" in kwargs:
        return kwargs["request"]
    # Check positional args (self is first for methods)
    for arg in args:
        if hasattr(arg, "method") and hasattr(arg, "path"):
            return arg  # Django HttpRequest-like
    return None


def _extract_content_type(request) -> str:
    """Robustly extract Content-Type from Django request."""
    content_type = getattr(request, "content_type", None)
    if not content_type:
        content_type = request.META.get("CONTENT_TYPE", "")
    return content_type


def _extract_files_from_full_data(full_data: dict) -> list:
    """Extract file objects from Ninja full_data dict."""
    files = []
    for key, value in full_data.items():
        if key.startswith("files[") or key == "files":
            if isinstance(value, list):
                files.extend([f for f in value if hasattr(f, "name")])
            elif hasattr(value, "name"):
                files.append(value)
    return files


def _parse_payload(request, schema_cls: type):
    """Async payload parsing by Content-Type."""
    content_type = _extract_content_type(request)

    if "application/json" in content_type:
        try:
            raw = json.loads(request.body.decode("utf-8"))
        except (ValueError, TypeError, UnicodeDecodeError) as e:
            raise HttpError(400, f"JSON body inválido: {e}")
        try:
            return schema_cls.model_validate(raw)
        except Exception as e:
            raise HttpError(400, f"Payload JSON no coincide con el formato esperado: {e}")

    if "multipart" in content_type:
        full_data = getattr(request, "_full_data", {})
        data_str = full_data.get("data")
        if isinstance(data_str, list):
            data_str = data_str[0]
        file_objs = _extract_files_from_full_data(full_data)
        return parse_form_json(data_str, file_objs, schema_cls)

    raise HttpError(415, "Content-Type must be application/json or multipart/form-data")


def _parse_payload_sync(request, schema_cls: type):
    """Sync payload parsing (for completeness)."""
    content_type = _extract_content_type(request)

    if "application/json" in content_type:
        try:
            raw = json.loads(request.body.decode("utf-8"))
        except (ValueError, TypeError, UnicodeDecodeError) as e:
            raise HttpError(400, f"JSON body inválido: {e}")
        try:
            return schema_cls.model_validate(raw)
        except Exception as e:
            raise HttpError(400, f"Payload JSON no coincide con el formato esperado: {e}")

    if "multipart" in content_type:
        full_data = getattr(request, "_full_data", {})
        data_str = full_data.get("data")
        if isinstance(data_str, list):
            data_str = data_str[0]
        file_objs = _extract_files_from_full_data(full_data)
        return parse_form_json(data_str, file_objs, schema_cls)

    raise HttpError(415, "Content-Type must be application/json or multipart/form-data")
