"""
Validadores y mixins reutilizables para schemas Pydantic (Django Ninja).

NOTA: Los parsers de DRF (JSONParser, MultiPartParser, FormParser) NO se
necesitan en Ninja. Ninja parsea el body automáticamente según la firma
del endpoint. Ver skill django-dev-ninja para patrones de File upload.
"""
from pydantic import field_validator


class EmptyStrToNoneMixin:
    """
    Pydantic v2: convierte strings vacíos o solo espacios a None.

    Reemplaza el SanitizeEmptyStringMixin de DRF.

    Problema que resuelve:
        El frontend envía "" para campos opcionales vacíos,
        pero Django espera None para campos con null=True.

    Uso:
        class PerfilIn(EmptyStrToNoneMixin, Schema):
            celular: str | None = None
            direccion: str | None = None
            correo: str | None = None
    """

    @field_validator('*', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v
