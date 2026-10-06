"""
Schema transformation utilities for the file hydration protocol.

AsForm[MySchema] → Generates a new Schema identical to MySchema but with all
                   UploadedFile fields replaced by str (file token strings).

hydrate_form(form_data, files, MySchema) → Takes the parsed AsForm instance
                                            + list of UploadedFiles and returns
                                            a fully hydrated MySchema instance.

Usage:
    class DocumentoSchema(Schema):
        name: str
        dni: UploadedFile

    @api.post("/doc")
    def create(request, data: Form[AsForm[DocumentoSchema]], files: File[list[UploadedFile]]):
        payload = hydrate_form(data, files, DocumentoSchema)
        payload.dni  # → UploadedFile real ✅
"""

import json
import re
from typing import Any, Type, TypeVar, Union, get_origin, get_args
from pydantic import create_model, model_validator
from pydantic.fields import FieldInfo
from ninja import Schema
from django.core.files.uploadedfile import UploadedFile

T = TypeVar("T", bound=Schema)

# Tipos que deben convertirse a str en la versión Form
_FILE_TYPES = (UploadedFile,)

# Patrón para identificar tokens de archivo
FILE_KEY_PATTERN = re.compile(r"^file_[A-Za-z0-9_-]+$")

# Cache para no regenerar el mismo schema dos veces
_form_schema_cache: dict[type, type] = {}


class BaseSchema(Schema):
    """
    Schema base del proyecto. Todos los schemas de negocio deben heredar de este.
    Convierte strings vacíos → None antes de validar.
    """
    model_config = {
        "arbitrary_types_allowed": True,
        "ser_json_decimal_to_float": True,
    }

    @model_validator(mode="before")
    @classmethod
    def sanitize_strings(cls, data: Any) -> Any:
        return _sanitize_empty_strings(data)


class DataForm(Schema):
    """Wrapper para recibir el campo 'data' JSON que envía buildApiPayload."""
    data: str


def AsForm(schema_cls: Type[T]) -> Type[Schema]:
    """
    Genera una versión "Form-safe" del schema dado.
    Todos los campos UploadedFile se convierten a str.
    """
    if schema_cls in _form_schema_cache:
        return _form_schema_cache[schema_cls]

    new_fields: dict[str, Any] = {}

    for field_name, field_info in schema_cls.model_fields.items():
        annotation = field_info.annotation

        if annotation is not None and _is_file_type(annotation):
            new_fields[field_name] = (str, _clone_field_as_str(field_info))
        elif annotation is not None and _is_list_of_schema(annotation):
            inner_type = get_args(annotation)[0]
            inner_form = AsForm(inner_type)
            new_fields[field_name] = (list[inner_form], field_info)
        else:
            if field_info.is_required():
                new_fields[field_name] = (annotation, field_info)
            else:
                new_fields[field_name] = (annotation, field_info.default)

    form_schema = create_model(
        f"{schema_cls.__name__}Form",
        __base__=Schema,
        **new_fields,
    )

    _form_schema_cache[schema_cls] = form_schema
    return form_schema


def hydrate_form(
    form_data: Schema, files: list[UploadedFile], target_schema: Type[T]
) -> T:
    """
    Sustituye tokens de archivo por UploadedFile reales y valida.
    """
    from ninja.errors import HttpError

    token_map: dict[str, UploadedFile] = {}
    for f in files:
        if f.name and "___" in f.name:
            token, real_name = f.name.split("___", 1)
            f.name = real_name
            token_map[token] = f
        else:
            raise HttpError(
                400,
                f"Archivo con formato de nombre inválido: '{f.name}'.",
            )

    raw = form_data.model_dump()
    claimed_tokens: set[str] = set()

    for field_name, field_info in target_schema.model_fields.items():
        if not _is_file_type(field_info.annotation):
            continue

        value = raw.get(field_name)
        if value is None:
            continue

        if not isinstance(value, str):
            raise HttpError(
                400,
                f"El campo '{field_name}' debe ser un token de archivo (string).",
            )
        if value not in token_map:
            raise HttpError(
                400,
                f"Token '{value}' no encontrado en archivos enviados.",
            )

        raw[field_name] = token_map[value]
        claimed_tokens.add(value)

    # Walk nested list[Schema] fields to hydrate file tokens inside items
    for field_name, field_info in target_schema.model_fields.items():
        if not _is_list_of_schema(field_info.annotation):
            continue
        items = raw.get(field_name)
        if not isinstance(items, list):
            continue
        inner_type = get_args(field_info.annotation)[0]
        for item in items:
            # Support both plain dicts (from model_dump with dict=True) and
            # Pydantic models (from model_dump without args). Walk the item
            # fields to replace file tokens in nested schemas.
            item_dict = dict(item) if not isinstance(item, dict) else item
            for inner_name, inner_info in inner_type.model_fields.items():
                if not _is_file_type(inner_info.annotation):
                    continue
                val = item_dict.get(inner_name)
                if val is None:
                    continue
                if isinstance(val, str) and val in token_map:
                    item[inner_name] = token_map[val]
                    claimed_tokens.add(val)

    orphan_tokens = set(token_map.keys()) - claimed_tokens
    if orphan_tokens:
        raise HttpError(
            400,
            f"Archivos huérfanos: {', '.join(orphan_tokens)}.",
        )

    raw = _sanitize_empty_strings(raw)
    return target_schema.model_validate(raw)


def parse_request_payload(request, schema_cls: Type[T]) -> T:
    """
    Generic helper that parses request body (JSON or multipart) and validates
    against the given schema class.

    For JSON (application/json):
        - Reads request.body directly
        - Validates with schema_cls.model_validate

    For multipart/form-data:
        - Tries POST/FILES first (Django-native), then falls back to _full_data (Ninja)
        - Uses parse_form_json for file hydration, including nested lists
        - Does NOT read request.body for multipart

    Raises HttpError for:
        - Missing 'data' field in multipart
        - Invalid JSON / decode errors
        - Unsupported Content-Type
        - Validation errors

    Usage:
        async def batch_imagenes_patch(self, bungalow_id: str, request):
            payload = parse_request_payload(request, BungalowImagenBatchIn)
    """
    from ninja.errors import HttpError

    # ── Extract Content-Type ────────────────────────────────────────────────
    content_type = getattr(request, "content_type", None)
    if not content_type:
        content_type = request.META.get("CONTENT_TYPE", "")

    # ── JSON path ────────────────────────────────────────────────────────────
    if "application/json" in content_type:
        try:
            body_bytes = request.body
            raw = json.loads(body_bytes.decode("utf-8"))
        except (ValueError, TypeError, UnicodeDecodeError) as e:
            raise HttpError(400, f"JSON body inválido: {e}")
        try:
            return schema_cls.model_validate(raw)
        except Exception as e:
            raise HttpError(400, f"Payload JSON no coincide con el formato esperado: {e}")

    # ── Multipart path ───────────────────────────────────────────────────────
    if "multipart" in content_type:
        # Strategy: try Django-native POST/FILES first, then Ninja's _full_data
        data_str: str | None = None
        file_objs: list = []

        # 1. Try Django's POST (handles regular form fields, includes 'data' JSON string)
        data_str = getattr(request, "POST", {}).get("data")

        # 2. Try Django's FILES for file objects
        django_files = getattr(request, "FILES", {})
        if django_files:
            for key, value in django_files.items():
                if hasattr(value, "name"):
                    file_objs.append(value)
                elif isinstance(value, list):
                    for f in value:
                        if hasattr(f, "name"):
                            file_objs.append(f)

        # 3. Fallback: Ninja's _full_data (used when request was parsed without Form/File params)
        if data_str is None:
            full_data = getattr(request, "_full_data", {})
            data_str = full_data.get("data")
            if isinstance(data_str, list):
                data_str = data_str[0] if data_str else None

            # Extract files from _full_data
            for key, value in full_data.items():
                if key.startswith("files[") or key == "files":
                    if isinstance(value, list):
                        file_objs.extend([f for f in value if hasattr(f, "name")])
                    elif hasattr(value, "name"):
                        file_objs.append(value)

        return parse_form_json(data_str, file_objs, schema_cls)

    raise HttpError(415, "Content-Type must be application/json or multipart/form-data")


def parse_form_json(
    data_field: str | None, files: Any, target_schema: Type[T]
) -> T:
    """
    Parsea JSON del FormData, hidrata archivos y valida contra el schema.
    Formato: data: '{"foto":"file_uuid"}', files: [UploadedFile "file_uuid___foto.jpg"]
    """
    from ninja.errors import HttpError

    if not data_field:
        raise HttpError(400, "El campo 'data' es requerido.")

    try:
        raw = json.loads(data_field)
    except (ValueError, TypeError):
        raise HttpError(400, "El campo 'data' no contiene JSON válido.")

    form_schema_cls = AsForm(target_schema)
    form_data = form_schema_cls.model_validate(raw)

    file_list: list = []
    if isinstance(files, list):
        file_list = files
    elif hasattr(files, "getlist"):
        for key in files.keys():
            file_list.extend(files.getlist(key))
    elif isinstance(files, dict):
        for v in files.values():
            if isinstance(v, list):
                file_list.extend(v)
            else:
                file_list.append(v)

    return hydrate_form(form_data, file_list, target_schema)


# ─── Helpers ──────────────────────────────────────────────────────────────


def _sanitize_empty_strings(node: Any) -> Any:
    """Convierte strings vacíos → None, respetando tokens de archivo."""
    if isinstance(node, dict):
        return {k: _sanitize_empty_strings(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_sanitize_empty_strings(i) for i in node]
    if isinstance(node, str):
        if FILE_KEY_PATTERN.match(node):
            return node
        return None if not node.strip() else node
    return node


def _is_file_type(annotation: Any) -> bool:
    """
    True si el tipo es UploadedFile (Django or Ninja wrapper).
    
    Handles:
    - Direct UploadedFile types (Django or Ninja)
    - Optional[UploadedFile], Union[UploadedFile, None]
    - Any alias/wrapper that is a subclass of Django UploadedFile
    """
    # Handle direct type: UploadedFile
    if isinstance(annotation, type):
        try:
            return issubclass(annotation, _FILE_TYPES)
        except TypeError:
            # Ninja's UploadedFile raises TypeError on issubclass check
            # but is a file type by convention — treat as file type
            return True

    # Handle Optional[UploadedFile], Union[UploadedFile, ...]
    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        # Check if any Union argument is a file type
        for arg in args:
            if arg is type(None):
                continue
            if isinstance(arg, type):
                try:
                    if issubclass(arg, _FILE_TYPES):
                        return True
                except TypeError:
                    # Ninja's UploadedFile raises TypeError — treat as file type
                    return True
        return False

    return False


def _is_list_of_schema(annotation: Any) -> bool:
    """True si el tipo es list[Schema]."""
    origin = get_origin(annotation)
    if origin is not list:
        return False
    args = get_args(annotation)
    if not args:
        return False
    try:
        return isinstance(args[0], type) and issubclass(args[0], Schema)
    except TypeError:
        return False


def _clone_field_as_str(field_info: FieldInfo) -> FieldInfo:
    """Clona FieldInfo para type str."""
    return FieldInfo(
        default=field_info.default,
        description=field_info.description,
        title=field_info.title,
        examples=field_info.examples,
    )
