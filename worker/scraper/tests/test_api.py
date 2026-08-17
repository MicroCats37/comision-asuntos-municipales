"""
test_api.py — Pruebas de integración y E2E para el microservicio de scraping.

Incluye:
  1. Validaciones locales (health, formato, longitud) sin red
  2. Pruebas reales E2E con el portal de consultas (RUC, DNI, No encontrado)
"""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ──────────────────────────────────────────────
# 1. Pruebas de Validación / Unitarias API
# ──────────────────────────────────────────────

def test_health_endpoint():
    """Verifica que /health responda status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_consultar_longitud_invalida():
    """Verifica error 422 cuando la longitud no es 8 ni 11 dígitos."""
    response = client.get("/consultar/12345")
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "INVALID_LENGTH"
    assert "8 (DNI) o 11 (RUC)" in data["detail"]


def test_consultar_formato_invalido():
    """Verifica error 422 cuando contiene caracteres no numéricos."""
    response = client.get("/consultar/1234567a")
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "INVALID_FORMAT"


# ──────────────────────────────────────────────
# 2. Pruebas E2E Reales (Red Externa)
# ──────────────────────────────────────────────

@pytest.mark.e2e
def test_e2e_consulta_ruc_real():
    """Consulta real E2E por RUC (Banco de Crédito del Perú - 20100047218)."""
    response = client.get("/consultar/20100047218")
    assert response.status_code == 200
    data = response.json()
    assert data["tipo_documento"] == "RUC"
    assert data["numero_documento"] == "20100047218"
    assert "BANCO DE CREDITO" in data["razon_social"]


@pytest.mark.e2e
def test_e2e_consulta_dni_real():
    """Consulta real E2E por DNI (74827847)."""
    response = client.get("/consultar/74827847")
    assert response.status_code == 200
    data = response.json()
    assert data["tipo_documento"] == "DNI"
    assert data["numero_documento"] == "74827847"
    assert "CALLIRGOS" in data["razon_social"]


@pytest.mark.e2e
def test_e2e_consulta_ruc_no_existente():
    """Consulta real E2E con un RUC que no existe (11111111111)."""
    response = client.get("/consultar/11111111111")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "NOT_FOUND"
