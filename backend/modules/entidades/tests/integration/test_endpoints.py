"""
Integration tests para endpoints de entidades: RENIEC, distritos, municipalidades.

Usa pytest-django con AsyncClient para endpoints async.
"""

import pytest
import asyncio

from django.test import AsyncClient


@pytest.mark.django_db
class TestReniecEndpoint:
    """Tests para GET /entidades/consulta-reniec/{dni}."""

    async def test_consulta_reniec_dni_valido(self):
        client = AsyncClient()
        resp = await client.get("/api/entidades/consulta-reniec/88888888")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["dni"] == "88888888"
        assert "nombres" in data["data"]
        assert "apellidos" in data["data"]
        assert "nombre_completo" in data["data"]

    async def test_consulta_reniec_dni_demasiado_corto(self):
        client = AsyncClient()
        resp = await client.get("/api/entidades/consulta-reniec/123")

        assert resp.status_code == 422  # Validación de longitud

    async def test_consulta_reniec_dni_hardcoded(self):
        """DNI con datos simulados hardcoded."""
        client = AsyncClient()
        resp = await client.get("/api/entidades/consulta-reniec/88888888")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["dni"] == "88888888"


@pytest.mark.django_db
class TestSunatEndpoint:
    """Tests para GET /entidades/consulta-sunat/{ruc}."""

    async def test_consulta_sunat_ruc_valido(self):
        client = AsyncClient()
        resp = await client.get("/api/entidades/consulta-sunat/77777777777")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["ruc"] == "77777777777"
        assert "razon_social" in data["data"]
        assert "estado" in data["data"]


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
