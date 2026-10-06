"""
conftest.py — Fixtures globales para tests de CAM.

Inspirado en: centro-de-esparcimiento/backend/conftest.py
"""
import os

os.environ.setdefault("NINJA_SKIP_REGISTRY", "1")

# Force CIP simulator in tests to avoid real HTTP calls to external CIP API.
# This overrides development.py's CIP_USE_SIMULATOR = False so that
# test_ingeniero_habilitado_integration.py and other tests using the
# ICipClient dependency get CipClientSimulator instead of RealCipClient.
os.environ["CIP_USE_SIMULATOR"] = "True"

import pytest
from pathlib import Path


# ── Test database cleanup ───────────────────────────────────────────
@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_db():
    """Remove stale test_db.sqlite3 before the test session to avoid stale row collisions."""
    test_db = Path(__file__).resolve().parent.parent / "test_db.sqlite3"
    if test_db.exists():
        os.remove(test_db)
    yield
    # No post-run cleanup — keep it for debugging if tests fail


# ── Django test client (sync) ───────────────────────────────────────

@pytest.fixture
def client(db):
    """Django test client (sync) — usa Django's test Client, no Ninja TestClient.

    Para tests de integración que usan Django test Client (no NinjaExtra).
    El db fixture asegura que la base SQLite en memoria esté lista.
    """
    from django.test import Client
    return Client()


# ── Ninja-style TestClient fixtures (opcional para tests más controlados) ──

def _get_ninja_api():
    """Obtiene la instancia de NinjaExtraAPI para usar en tests."""
    from config.api import api
    return api


def _get_override_dict():
    """Resolve dependency_overrides dict for NinjaExtraAPI."""
    ninja_api = _get_ninja_api()
    if hasattr(ninja_api, 'dependency_overrides'):
        return ninja_api.dependency_overrides
    app = getattr(ninja_api, 'app', None)
    if app is not None and hasattr(app, 'dependency_overrides'):
        return app.dependency_overrides
    return {}


@pytest.fixture
def test_sync_client(db):
    """Ninja TestClient sin autenticación.

    Útil para tests que quieren el cliente de Ninja (no Django test Client).
    """
    from ninja.testing import TestClient
    api = _get_ninja_api()
    return TestClient(api)


@pytest.fixture
def api():
    """NinjaExtraAPI instance from config/api.py."""
    return _get_ninja_api()


@pytest.fixture
def test_async_client(db):
    """Ninja TestAsyncClient sin autenticación.

    Para tests async del módulo finanzas.
    """
    from ninja.testing import TestAsyncClient
    api = _get_ninja_api()
    return TestAsyncClient(api)
