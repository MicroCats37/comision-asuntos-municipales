import uuid
from .permissions import SystemPermissions
from datetime import datetime
from django.db import models


class UUIDModel(models.Model):
    """
    Base abstracta: utiliza UUID como clave primaria.
    Protege contra ataques de enumeración de IDs secuenciales.
    """

    id: uuid.UUID = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    """
    Base abstracta: incluye campos de auditoría de tiempo.
    Ninja ModelSchema inferirá automáticamente el tipo datetime.
    """

    created_at: datetime = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Fecha de creación"
    )
    updated_at: datetime = models.DateTimeField(
        auto_now=True, 
        verbose_name="Última actualización"
    )

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimestampedModel):
    """
    Modelo base completo: UUID + Marcas de tiempo.
    La mayoría de los modelos del proyecto deben heredar de esta clase.

    Uso:
        from core.models import BaseModel

        class MiModelo(BaseModel):
            nombre = models.CharField(max_length=100)
    """

    class Meta:
        abstract = True


class DjangoAuthMixin(models.Model):
    """
    Mixin abstracto con los campos de autenticación de Django:
    is_staff e is_active. Heredado por modelos de usuario customizados
    que no heredan de AbstractUser directamente.
    """

    is_staff = models.BooleanField(
        default=False,
        verbose_name="¿Es Staff?"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="¿Está Activo?"
    )

    class Meta:
        abstract = True
