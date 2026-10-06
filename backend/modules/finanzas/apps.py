from django.apps import AppConfig


class FinanzasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.finanzas"
    label = "finanzas"
    verbose_name = "Finanzas"

    def ready(self):
        """Import admin package to trigger admin registration."""
        from . import admin  # noqa: F401
