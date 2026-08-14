from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.usuarios"
    label = "usuarios"
    verbose_name = "Usuarios"

    def ready(self):
        """Import admin package to trigger admin registration."""
        from . import admin  # noqa: F401
