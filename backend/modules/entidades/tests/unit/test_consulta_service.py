"""
Unit tests para RealConsultaExternaClient y manejo de errores del worker.

Usa unittest.mock para simular respuestas HTTP del worker sin hacer llamadas reales.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from modules.entidades.infrastructure.services import RealConsultaExternaClient
from modules.entidades.domain.exceptions import (
    SunatNotFoundError,
    ReniecNotFoundError,
    DocumentoInvalidoError,
    ScraperFormatError,
    ScraperUnavailableError,
    ScraperTimeoutError,
)


class FakeResponse:
    """Fake httpx response para testing."""

    def __init__(self, status_code: int, json_data: dict | None = None, detail: str = ""):
        self._status_code = status_code
        self._json_data = json_data or {}
        self._detail = detail
        self.headers = {}

    @property
    def status_code(self):
        return self._status_code

    def json(self):
        return self._json_data


class TestRealConsultaExternaClientErrorMapping:
    """Tests que verifican que el cliente mapea correctamente los códigos de error del worker."""

    @pytest.mark.asyncio
    async def test_200_returns_result(self):
        """200 → ConsultaDocumentoResult con datos."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = FakeResponse(
                200,
                {"tipo_documento": "DNI", "numero_documento": "12345678", "razon_social": "JUAN PEREZ"},
            )
            mock_client_cls.return_value = mock_client

            client = RealConsultaExternaClient()
            result = await client.consultar_documento("12345678")

            assert result.tipo_documento == "DNI"
            assert result.numero_documento == "12345678"
            assert result.razon_social == "JUAN PEREZ"

    @pytest.mark.asyncio
    async def test_404_dni_raises_reniec_not_found_error(self):
        """404 con DNI (8 dígitos) → ReniecNotFoundError (code: RENIEC_NOT_FOUND, status: 404)."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = FakeResponse(
                404,
                {"error": "NOT_FOUND", "detail": "DNI 12345678 no encontrado"},
            )
            mock_client_cls.return_value = mock_client

            client = RealConsultaExternaClient()
            with pytest.raises(ReniecNotFoundError) as exc_info:
                await client.consultar_documento("12345678")

            assert exc_info.value.code == "RENIEC_NOT_FOUND"
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_404_ruc_raises_sunat_not_found_error(self):
        """404 con RUC (11 dígitos) → SunatNotFoundError (code: SUNAT_NOT_FOUND, status: 404)."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = FakeResponse(
                404,
                {"error": "NOT_FOUND", "detail": "RUC 20492913151 no encontrado"},
            )
            mock_client_cls.return_value = mock_client

            client = RealConsultaExternaClient()
            with pytest.raises(SunatNotFoundError) as exc_info:
                await client.consultar_documento("20492913151")

            assert exc_info.value.code == "SUNAT_NOT_FOUND"
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_422_raises_documento_invalido_error(self):
        """422 → DocumentoInvalidoError (code: DOCUMENT_INVALID, status: 422)."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = FakeResponse(
                422,
                {"error": "INVALID_FORMAT", "detail": "El documento debe tener 8 u 11 dígitos"},
            )
            mock_client_cls.return_value = mock_client

            client = RealConsultaExternaClient()
            with pytest.raises(DocumentoInvalidoError) as exc_info:
                await client.consultar_documento("12345")

            assert exc_info.value.code == "DOCUMENT_INVALID"
            assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_502_raises_scraper_format_error(self):
        """502 → ScraperFormatError (code: SCRAPER_FORMAT_ERROR, status: 502)."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = FakeResponse(
                502,
                {"error": "FORMAT_ERROR", "detail": "El HTML del portal cambió y no se puede parsear"},
            )
            mock_client_cls.return_value = mock_client

            client = RealConsultaExternaClient()
            with pytest.raises(ScraperFormatError) as exc_info:
                await client.consultar_documento("20492913151")

            assert exc_info.value.code == "SCRAPER_FORMAT_ERROR"
            assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_503_raises_scraper_unavailable_error(self):
        """503 → ScraperUnavailableError (code: SCRAPER_UNAVAILABLE, status: 503)."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = FakeResponse(
                503,
                {"error": "UNAVAILABLE", "detail": "Portal de consultas no disponible"},
            )
            mock_client_cls.return_value = mock_client

            client = RealConsultaExternaClient()
            with pytest.raises(ScraperUnavailableError) as exc_info:
                await client.consultar_documento("20492913151")

            assert exc_info.value.code == "SCRAPER_UNAVAILABLE"
            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_504_raises_scraper_timeout_error(self):
        """504 → ScraperTimeoutError (code: SCRAPER_TIMEOUT, status: 504)."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = FakeResponse(
                504,
                {"error": "TIMEOUT", "detail": "El portal no respondió en 300 segundos"},
            )
            mock_client_cls.return_value = mock_client

            client = RealConsultaExternaClient()
            with pytest.raises(ScraperTimeoutError) as exc_info:
                await client.consultar_documento("20492913151")

            assert exc_info.value.code == "SCRAPER_TIMEOUT"
            assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_unexpected_status_raises_scraper_unavailable(self):
        """Código de estado inesperado → ScraperUnavailableError (code: SCRAPER_UNAVAILABLE, status: 503)."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.get.return_value = FakeResponse(500, {"error": "INTERNAL_ERROR", "detail": "Error interno"})
            mock_client_cls.return_value = mock_client

            client = RealConsultaExternaClient()
            with pytest.raises(ScraperUnavailableError) as exc_info:
                await client.consultar_documento("20492913151")

            assert exc_info.value.code == "SCRAPER_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_connect_timeout_raises_scraper_unavailable(self):
        """ConnectTimeout → ScraperUnavailableError."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.side_effect = httpx.ConnectTimeout("Connection timed out")
            mock_client_cls.return_value = mock_client

            client = RealConsultaExternaClient()
            with pytest.raises(ScraperUnavailableError) as exc_info:
                await client.consultar_documento("20492913151")

            assert exc_info.value.code == "SCRAPER_UNAVAILABLE"
            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_read_timeout_raises_scraper_timeout(self):
        """ReadTimeout → ScraperTimeoutError."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.side_effect = httpx.ReadTimeout("Read timed out")
            mock_client_cls.return_value = mock_client

            client = RealConsultaExternaClient()
            with pytest.raises(ScraperTimeoutError) as exc_info:
                await client.consultar_documento("20492913151")

            assert exc_info.value.code == "SCRAPER_TIMEOUT"
            assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_connect_error_raises_scraper_unavailable(self):
        """ConnectError → ScraperUnavailableError."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.side_effect = httpx.ConnectError("Connection refused")
            mock_client_cls.return_value = mock_client

            client = RealConsultaExternaClient()
            with pytest.raises(ScraperUnavailableError) as exc_info:
                await client.consultar_documento("20492913151")

            assert exc_info.value.code == "SCRAPER_UNAVAILABLE"
            assert exc_info.value.status_code == 503
