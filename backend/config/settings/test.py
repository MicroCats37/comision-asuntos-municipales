"""
Test settings.
"""
from .base import *  # noqa

DEBUG = False
SECRET_KEY = "django-insecure-test-secret-key-1234567890"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# ── CIP Simulator ────────────────────────────────────────────
# En tests usamos el simulador para no depender del API externo real
CIP_USE_SIMULATOR = True

# ── Notificaciones (Mock) ───────────────────────────────────
NOTI_EMULATOR_ENABLED = True
NOTI_URL = "http://mock-noti"
NOTI_APP_ID = 999

# Deshabilitamos middleware pesado para tests unitarios
MIDDLEWARE = [m for m in MIDDLEWARE if "debug_toolbar" not in m]
