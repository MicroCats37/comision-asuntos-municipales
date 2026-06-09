"""
Usuario — Custom user model with DNI as identifier.
Extends AbstractBaseUser + PermissionsMixin following the project pattern.
"""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator
from simple_history.models import HistoricalRecords

from core.models import BaseModel, DjangoAuthMixin


class UsuarioManager(BaseUserManager):
    """Custom manager for Usuario model."""

    def create_user(self, dni, password=None, **extra_fields):
        if not dni:
            raise ValueError("El campo DNI debe estar establecido.")
        user = self.model(dni=dni, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, dni, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(dni, password, **extra_fields)


# DNI validator: exactly 8 digits
dni_validator = RegexValidator(
    regex=r"^\d{8}$",
    message="El DNI debe contener exactamente 8 dígitos numéricos.",
    code="invalid_dni",
)


class Usuario(AbstractBaseUser, PermissionsMixin, DjangoAuthMixin, BaseModel):
    history = HistoricalRecords()
    """
    Usuario customizado con AbstractBaseUser + PermissionsMixin.
    Usa DNI como identificador único de login (no username/email).
    """
    nombres = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nombre")
    apellidos = models.CharField(max_length=255, blank=True, null=True, verbose_name="Apellido")
    email = models.EmailField(max_length=255, blank=True, null=True, unique=True, verbose_name="Correo electrónico")
    username = models.CharField(max_length=255, blank=True, null=True, unique=True, verbose_name="Nombre de usuario")  # Opcional — futuro login alternativo
    dni = models.CharField(
        max_length=8,
        unique=True,
        validators=[dni_validator],
        verbose_name="DNI",
        help_text="8 dígitos numéricos exactamente.",
    )

    # Inherit from AbstractBaseUser: password, last_login, is_active
    # Inherit from PermissionsMixin: groups, user_permissions, is_superuser
    # Inherit from DjangoAuthMixin: is_staff
    # Inherit from BaseModel: id (UUID), created_at, updated_at

    USERNAME_FIELD = "dni"
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Usuario {self.dni}"