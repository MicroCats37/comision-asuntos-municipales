"""
Unit tests para el handler on_http_error en core.exceptions.

Verifica que el mensaje específico de la excepción se preserve como
error.message de primer nivel en la respuesta.

on_http_error es una función anidada dentro de register_exception_handlers,
por lo que se testa indirectamente via el controller/endpoint real.
"""

import pytest
from django.test import AsyncClient
from ninja.errors import HttpError
from unittest.mock import patch


@pytest.mark.django_db
class TestOnHttpErrorPreservesMessage:
    """Tests que verifican que el handler on_http_error preserva exc.message como error.message de primer nivel."""

    async def test_specific_error_message_preserved_at_error_message_field(self):
        """
        Cuando el worker retorna 503 con mensaje específico,
        la respuesta debe tener ese mensaje en error.message de nivel superior.
        """
        # Mock RealConsultaExternaClient para que lance una excepción con mensaje específico
        from modules.entidades.infrastructure.services import RealConsultaExternaClient
        from modules.entidades.domain.exceptions import ScraperUnavailableError

        exc_to_raise = ScraperUnavailableError(
            "El servicio de consulta de documentos no está disponible. Intente más tarde."
        )

        with patch.object(
            RealConsultaExternaClient,
            "consultar_documento",
            side_effect=exc_to_raise,
        ):
            client = AsyncClient()
            resp = await client.get("/api/entidades/consulta/20492913151")

            assert resp.status_code == 503
            data = resp.json()
            assert data["success"] is False
            assert data["error"]["message"] == "El servicio de consulta de documentos no está disponible. Intente más tarde."
            assert data["error"]["code"] == "SCRAPER_UNAVAILABLE"
            assert "non_field_errors" in data["error"]["details"]

    async def test_documento_invalido_error_message_preserved(self):
        """422 con mensaje específico → error.message debe contener ese mensaje."""
        from modules.entidades.infrastructure.services import RealConsultaExternaClient
        from modules.entidades.domain.exceptions import DocumentoInvalidoError

        exc_to_raise = DocumentoInvalidoError("El documento tiene formato o longitud inválida")

        with patch.object(
            RealConsultaExternaClient,
            "consultar_documento",
            side_effect=exc_to_raise,
        ):
            client = AsyncClient()
            # Use 8-char documento to pass path validation; service raises DocumentoInvalidoError
            resp = await client.get("/api/entidades/consulta/12345678")

            assert resp.status_code == 422
            data = resp.json()
            assert data["success"] is False
            assert "formato" in data["error"]["message"] or "inválida" in data["error"]["message"]
            assert data["error"]["code"] == "DOCUMENT_INVALID"

    async def test_sunat_not_found_error_preserves_message(self):
        """SunatNotFoundError → error.message con el mensaje específico del RUC no encontrado."""
        from modules.entidades.infrastructure.services import RealConsultaExternaClient
        from modules.entidades.domain.exceptions import SunatNotFoundError

        exc_to_raise = SunatNotFoundError("20492913151")

        with patch.object(
            RealConsultaExternaClient,
            "consultar_documento",
            side_effect=exc_to_raise,
        ):
            client = AsyncClient()
            resp = await client.get("/api/entidades/consulta/20492913151")

            assert resp.status_code == 404
            data = resp.json()
            assert data["success"] is False
            assert "20492913151" in data["error"]["message"]
            assert data["error"]["code"] == "SUNAT_NOT_FOUND"

    async def test_scraper_timeout_error_preserves_message(self):
        """504 ScraperTimeoutError → error.message con mensaje de timeout."""
        from modules.entidades.infrastructure.services import RealConsultaExternaClient
        from modules.entidades.domain.exceptions import ScraperTimeoutError

        exc_to_raise = ScraperTimeoutError("El portal externo no respondió a tiempo. Intente más tarde.")

        with patch.object(
            RealConsultaExternaClient,
            "consultar_documento",
            side_effect=exc_to_raise,
        ):
            client = AsyncClient()
            resp = await client.get("/api/entidades/consulta/20492913151")

            assert resp.status_code == 504
            data = resp.json()
            assert data["success"] is False
            assert "no respondió a tiempo" in data["error"]["message"]
            assert data["error"]["code"] == "SCRAPER_TIMEOUT"
