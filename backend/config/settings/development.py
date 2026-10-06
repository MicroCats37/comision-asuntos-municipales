"""
Development settings.
"""
from datetime import timedelta
from .base import *  # noqa

DEBUG = True

# development usa hosts locales; base define fallback ["*"]
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', 'testserver']

# ── Base de datos — respetamos DB_ENGINE de base.py si está definido ─────
# USE_SQLITE=true se mantiene por compatibilidad hacia atrás pero DB_ENGINE tiene precedencia
import os

db_engine = os.environ.get("DB_ENGINE", "").lower()
use_sqlite_env = os.environ.get("USE_SQLITE", "").lower() in ("1", "true", "yes")

# Solo aplicar override SQLite de development si no hay DB_ENGINE explícito
# y USE_SQLITE está activo (viejo comportamiento)
if not db_engine and use_sqlite_env:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
# Si DB_ENGINE=mariadb, base.py ya configuro PyMySQL + mysql engine; no hacemos override aqui

# ── CORS ─────────────────────────────────────────────────────
# Allow all origins in development (override with CORS_ALLOWED_ORIGINS for specific domains)
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)
if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
    ])
CORS_ALLOW_CREDENTIALS = not CORS_ALLOW_ALL_ORIGINS  # Can't use credentials with wildcard origin

# ── Debug Toolbar ────────────────────────────────────────────
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
INTERNAL_IPS = ['127.0.0.1']

# ── Email ────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ── JWT — Tokens de larga duración para desarrollo fácil ─────
NINJA_JWT = {
    **NINJA_JWT,
    'ACCESS_TOKEN_LIFETIME': timedelta(days=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=90),
}

# ── CIP — Usar cliente real en desarrollo (no el simulador) ──
# Tests siguen usando CIP_USE_SIMULATOR=True en test.py
CIP_USE_SIMULATOR = False
