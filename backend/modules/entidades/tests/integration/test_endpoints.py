"""
Integration tests para endpoints de entidades: RENIEC, distritos, municipalidades.

Usa pytest-django con AsyncClient para endpoints async.
"""

import pytest
import asyncio

from django.test import AsyncClient


@pytest.mark.django_db
class TestConsultaDocumentoEndpoint:
    """Tests para GET /entidades/consulta/{documento} (unificado)."""

    async def test_consulta_documento_dni_valido(self):
        """Consulta DNI válido (8 dígitos) → tipo_documento=DNI."""
        client = AsyncClient()
        resp = await client.get("/api/entidades/consulta/88888888")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["tipo_documento"] == "DNI"
        assert data["data"]["numero_documento"] == "88888888"
        assert "razon_social" in data["data"]
        # No其他的 campos deben estar ausentes
        assert "nombres" not in data["data"]
        assert "apellidos" not in data["data"]
        assert "estado" not in data["data"]

    async def test_consulta_documento_ruc_valido(self):
        """Consulta RUC válido (11 dígitos) → tipo_documento=RUC."""
        client = AsyncClient()
        resp = await client.get("/api/entidades/consulta/77777777777")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["tipo_documento"] == "RUC"
        assert data["data"]["numero_documento"] == "77777777777"
        assert "razon_social" in data["data"]
        # No其他的 campos
        assert "estado" not in data["data"]
        assert "distrito" not in data["data"]

    async def test_consulta_documento_dni_hardcoded(self):
        """DNI con datos simulados hardcoded: 45406196 → DENNIS JOEL ZARATE TORRES."""
        client = AsyncClient()
        resp = await client.get("/api/entidades/consulta/45406196")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["tipo_documento"] == "DNI"
        assert data["numero_documento"] == "45406196"
        assert "ZARATE" in data["razon_social"]
        assert "DENNIS" in data["razon_social"]

    async def test_consulta_documento_ruc_hardcoded(self):
        """RUC con datos simulados hardcoded: 20492913151 → MUNICIPALIDAD PROVINCIAL DE LIMA."""
        client = AsyncClient()
        resp = await client.get("/api/entidades/consulta/20492913151")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["tipo_documento"] == "RUC"
        assert data["numero_documento"] == "20492913151"
        assert data["razon_social"] == "MUNICIPALIDAD PROVINCIAL DE LIMA"

    async def test_consulta_documento_longitud_invalida(self):
        """Longitud inválida (ni 8 ni 11) → tipo_documento=DESCONOCIDO."""
        client = AsyncClient()
        resp = await client.get("/api/entidades/consulta/12345")

        assert resp.status_code == 422  # Validación de longitud (min_length=8)

    async def test_consulta_documento_dni_demasiado_corto(self):
        """DNI demasiado corto → validación de longitud."""
        client = AsyncClient()
        resp = await client.get("/api/entidades/consulta/123")

        assert resp.status_code == 422  # Validación de longitud


@pytest.mark.django_db
class TestDistritosEndpoint:
    """Tests para GET /entidades/ubigeo/distritos."""

    async def test_distritos_devuelve_lista(self):
        client = AsyncClient()
        resp = await client.get("/api/entidades/ubigeo/distritos")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    async def test_distritos_filtro_search(self):
        client = AsyncClient()
        resp = await client.get("/api/entidades/ubigeo/distritos?search=LIMA")

        assert resp.status_code == 200
        data = resp.json()["data"]
        # Si hay datos, todos deberían contener "LIMA"
        if isinstance(data, list) and data:
            for d in data:
                nombre = d.get("nombre", "").upper() if isinstance(d, dict) else str(d).upper()
                assert "LIMA" in nombre or "LIMA" in str(d).upper()


@pytest.mark.django_db
class TestMunicipalidadesEndpoint:
    """Tests para GET /entidades/municipalidades."""

    async def test_municipalidades_devuelve_lista(self):
        client = AsyncClient()
        resp = await client.get("/api/entidades/municipalidades")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    async def test_municipalidades_tienen_codigo_y_nombre(self):
        client = AsyncClient()
        resp = await client.get("/api/entidades/municipalidades")

        assert resp.status_code == 200
        data = resp.json()["data"]
        if isinstance(data, list) and data:
            for m in data:
                assert "codigo" in m
                assert "nombre" in m

    async def test_municipalidades_tienen_cache_control(self):
        """Los datos estáticos deben cachearse 1 año en el navegador."""
        client = AsyncClient()
        resp = await client.get("/api/entidades/municipalidades")

        assert resp.status_code == 200
        assert resp.headers.get("Cache-Control") == "public, max-age=31536000"


@pytest.mark.django_db
class TestCacheHeaders:
    """Verifica headers de caché en endpoints de datos estáticos."""

    async def test_distritos_tienen_cache_control(self):
        client = AsyncClient()
        resp = await client.get("/api/entidades/ubigeo/distritos")

        assert resp.status_code == 200
        assert resp.headers.get("Cache-Control") == "public, max-age=31536000"
