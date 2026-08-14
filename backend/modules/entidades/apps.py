from django.apps import AppConfig


class EntidadesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.entidades"
    label = "entidades"
    verbose_name = "Entidades"

    def ready(self):
        """Import admin package to trigger admin registration."""
        from . import admin  # noqa: F401
