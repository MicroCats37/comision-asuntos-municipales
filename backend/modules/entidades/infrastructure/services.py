"""
Infrastructure Services — Implementaciones de puertos para servicios externos.

- ConsultaExternaSimulator: Simulador unificado con datos mock para desarrollo
  (DNI → RENIEC mock, RUC → SUNAT mock)

# TODO: Implementar cliente real unificado cuando se tengan las credenciales API:
# - RealConsultaExternaClient: Cliente real que consulta la API de RENIEC/SUNAT
"""

import hashlib
import os
import random
from datetime import date

import httpx

from ..domain.ports import IConsultaExternaClient
from ..domain.results import ConsultaDocumentoResult
from ..domain.exceptions import (
    SunatNotFoundError,
    ReniecNotFoundError,
    DocumentoInvalidoError,
    ScraperFormatError,
    ScraperUnavailableError,
    ScraperTimeoutError,
)



class ConsultaExternaSimulator(IConsultaExternaClient):
    """
    Simulador unificado del cliente consulta externa con datos mock para desarrollo.

    Proporciona datos determinísticos para probar el flujo completo
    sin depender de las APIs reales de RENIEC/SUNAT.

    - DNIs hardcoded tienen datos mock determinísticos existentes.
    - RUCs hardcoded tienen datos mock determinísticos existentes.
    - Cualquier otro documento válido genera datos mock determinísticos
      basados en el número (mismo número siempre devuelve los mismos datos).

    Comportamiento:
      - documento length 11 → trata como RUC (SUNAT)
      - documento length 8 → trata como DNI (RENIEC)
      - otro length → tipo_documento="DESCONOCIDO"
    """

    # ── SUNAT MOCK DATA ─────────────────────────────────────────────────────────

    _SUNAT_SIMULADOS = {
        "20492913151": {
            "ruc": "20492913151",
            "razon_social": "MUNICIPALIDAD PROVINCIAL DE LIMA",
            "nombre_comercial": "MPL",
            "estado": "ACTIVO",
            "tipo_contribuyente": "GOBIERNO LOCAL",
            "direccion": "AV. PCM S/N",
            "departamento": "LIMA",
            "provincia": "LIMA",
            "distrito": "LIMA",
        },
        "20131312957": {
            "ruc": "20131312957",
            "razon_social": "COLEGIO DE INGENIEROS DEL PERU",
            "nombre_comercial": "CIP",
            "estado": "ACTIVO",
            "tipo_contribuyente": "ORDENANZA",
            "direccion": "AV. REPUBLICA DE CHILE 356, LIMA",
            "departamento": "LIMA",
            "provincia": "LIMA",
            "distrito": "LIMA",
        },
        "20600099773": {
            "ruc": "20600099773",
            "razon_social": "CONSORCIO CAM LIMA NORTE",
            "nombre_comercial": "CAM LN",
            "estado": "ACTIVO",
            "tipo_contribuyente": "CONTRATISTA",
            "direccion": "AV. TUPAC AMARU 1234",
            "departamento": "LIMA",
            "provincia": "LIMA",
            "distrito": "INDEPENDENCIA",
        },
    }

    _SUNAT_RAZONES_SOCIALES = [
        "EMPRESA CONSTRUCTORA",
        "SERVICIOS GENERALES",
        "INDUSTRIA MANUFACTURERA",
        "COMERCIO AL POR MAYOR",
        "COMERCIO AL POR MENOR",
        "TRANSPORTES Y LOGISTICA",
        "SERVICIOS PROFESIONALES",
        "AGRICULTURA Y GANADERIA",
        "PESCA Y ACUICULTURA",
        "MINERIA Y CANTERAS",
        "ENERGIA Y AGUA",
        "CONSTRUCCION",
        "HOSTELERIA Y RESTAURACION",
        "ACTIVIDADES INMOBILIARIAS",
        "EDUCACION",
        "SALUD",
        "ENTRETENIMIENTO",
        "ADMINISTRACION PUBLICA",
    ]

    _SUNAT_NOMBRES_COMERCIALES = [
        "ABC",
        "XYZ",
        "PRIMAX",
        "GRIFO",
        "PLAZA",
        "CENTRAL",
        "NORTE",
        "SUR",
        "ESTE",
        "OESTE",
    ]

    _SUNAT_ESTADOS = ["ACTIVO", "ACTIVO", "ACTIVO", "BAJA", "SUSPENSION"]
    _SUNAT_TIPOS_CONTRIBUYENTE = [
        "ORDENANZA",
        "GOBIERNO LOCAL",
        "GOBIERNO NACIONAL",
        "CONTRATISTA",
        "EMPRESA PRIVADA",
    ]
    _SUNAT_DEPARTAMENTOS = ["LIMA", "AREQUIPA", "CUSCO", "TRUJILLO", "PIURA", "ICA"]
    _SUNAT_PROVINCIAS = ["LIMA", "AREQUIPA", "CUSCO", "TRUJILLO", "PIURA", "ICA"]
    _SUNAT_DISTRITOS = ["LIMA", "MIRAFLORES", "SAN ISIDRO", "SURCO", "LA VICTORIA"]

    # ── RENIEC MOCK DATA ─────────────────────────────────────────────────────────

    _RENIEC_SIMULADOS = {
        "45406196": {
            "dni": "45406196",
            "nombres": "DENNIS JOEL",
            "apellidos": "ZARATE TORRES",
            "nombre_completo": "ZARATE TORRES, DENNIS JOEL",
            "genero": "M",
            "fecha_nacimiento": date(1986, 8, 24),
            "direccion": "LAS PALMAS 135 LA CAPILLA",
            "ubigeo": "150101",
        },
        "12345678": {
            "dni": "12345678",
            "nombres": "CARLOS MANUEL",
            "apellidos": "PEREZ GOMEZ",
            "nombre_completo": "PEREZ GOMEZ, CARLOS MANUEL",
            "genero": "M",
            "fecha_nacimiento": date(1990, 3, 15),
            "direccion": "AV. AREQUIPA 123",
            "ubigeo": "150101",
        },
        "87654321": {
            "dni": "87654321",
            "nombres": "MARIA ELENA",
            "apellidos": "LOPEZ SANCHEZ",
            "nombre_completo": "LOPEZ SANCHEZ, MARIA ELENA",
            "genero": "F",
            "fecha_nacimiento": date(1983, 11, 7),
            "direccion": "JR. LIMA 456",
            "ubigeo": "150201",
        },
    }

    _RENIEC_NOMBRES = [
        "JUAN",
        "CARLOS",
        "MIGUEL",
        "LUIS",
        "JOSE",
        "MARIA",
        "ELENA",
        "ANA",
        "PATRICIA",
        "LORENA",
        "FERNANDO",
        "RODRIGO",
        "VERONICA",
        "CARMEN",
        "FRANCISCO",
    ]

    _RENIEC_APELLIDOS = [
        "GARCIA",
        "PEREZ",
        "LOPEZ",
        "SANCHEZ",
        "RODRIGUEZ",
        "MARTINEZ",
        "TORRES",
        "RAMIREZ",
        "FLORES",
        "VARGAS",
        "HUAMAN",
        "QUISPE",
        "MENDOZA",
        "CASTILLO",
        "JIMENEZ",
    ]

    _RENIEC_GENEROS = ["M", "F"]

    # ── Main dispatch method ─────────────────────────────────────────────────────

    async def consultar_documento(self, documento: str) -> ConsultaDocumentoResult:
        """
        Consulta documento unificada: auto-detecta DNI (8) vs RUC (11).

        Args:
            documento: Número de documento (8 o 11 dígitos).

        Returns:
            ConsultaDocumentoResult unificado.

        Raises:
            SunatNotFoundError: Si el RUC (11 dígitos) no se encuentra.
            ReniecNotFoundError: Si el DNI (8 dígitos) no se encuentra.
        """
        length = len(documento)

        if length == 11:
            return await self._consultar_ruc(documento)
        elif length == 8:
            return await self._consultar_dni(documento)
        else:
            # Longitud inválida → devuelve DESCONOCIDO sin error
            return ConsultaDocumentoResult(
                tipo_documento="DESCONOCIDO",
                numero_documento=documento,
                razon_social="",
            )

    # ── Internal helpers ─────────────────────────────────────────────────────────

    async def _consultar_ruc(self, ruc: str) -> ConsultaDocumentoResult:
        """Consulta RUC (SUNAT)."""
        data = self._SUNAT_SIMULADOS.get(ruc)
        if data:
            return ConsultaDocumentoResult(
                tipo_documento="RUC",
                numero_documento=ruc,
                razon_social=data["razon_social"],
            )

        # Generar datos determinísticos para RUCs no hardcoded
        return self._generar_ruc_determinista(ruc)

    async def _consultar_dni(self, dni: str) -> ConsultaDocumentoResult:
        """Consulta DNI (RENIEC)."""
        data = self._RENIEC_SIMULADOS.get(dni)
        if data:
            return ConsultaDocumentoResult(
                tipo_documento="DNI",
                numero_documento=dni,
                razon_social=data["nombre_completo"],
            )

        # Generar datos determinísticos para DNIs no hardcoded
        return self._generar_dni_determinista(dni)

    def _generar_ruc_determinista(self, ruc: str) -> ConsultaDocumentoResult:
        """Genera datos mock determinísticos para RUCs no hardcoded."""
        seed = int(hashlib.md5(ruc.encode()).hexdigest(), 16)
        rng = random.Random(seed)

        razon_social = f"{rng.choice(self._SUNAT_RAZONES_SOCIALES)} S.A.C."

        return ConsultaDocumentoResult(
            tipo_documento="RUC",
            numero_documento=ruc,
            razon_social=razon_social,
        )

    def _generar_dni_determinista(self, dni: str) -> ConsultaDocumentoResult:
        """Genera datos mock determinísticos para DNIs no hardcoded."""
        seed = int(hashlib.md5(dni.encode()).hexdigest(), 16)
        rng = random.Random(seed)

        nombres = f"{rng.choice(self._RENIEC_NOMBRES)} {rng.choice(self._RENIEC_NOMBRES)}"
        apellido_paterno = rng.choice(self._RENIEC_APELLIDOS)
        apellido_materno = rng.choice(self._RENIEC_APELLIDOS)
        apellidos = f"{apellido_paterno} {apellido_materno}"
        nombre_completo = f"{apellidos}, {nombres}"

        return ConsultaDocumentoResult(
            tipo_documento="DNI",
            numero_documento=dni,
            razon_social=nombre_completo,
        )


class RealConsultaExternaClient(IConsultaExternaClient):
    """
    Cliente real que consulta el microservicio scraper de documentos.

    El scraper corre en worker/scraper/ y expone:
      GET {SCRAPER_URL}/consultar/{documento}

    Códigos HTTP del scraper:
      200 → dato encontrado
      404 → RUC/DNI no existe
      422 → documento inválido (longitud o formato)
      502 → formato del portal cambió (ScraperFormatError)
      503 → portal no disponible / sin conectividad
      504 → timeout esperando al portal
    """

    def __init__(self):
        import os
        self._base_url = os.environ.get("SCRAPER_URL", "http://scraper:8001")
        self._timeout = httpx.Timeout(
            connect=10.0,
            read=300.0,   # el portal puede tardar hasta 4 min
            write=10.0,
            pool=5.0,
        )

    async def consultar_documento(self, documento: str) -> ConsultaDocumentoResult:
        """
        Consulta el microservicio scraper por DNI (8 dígitos) o RUC (11 dígitos).

        Crea un AsyncClient por petición (async with) para evitar el error
        "Event loop is closed" al reutilizar un cliente singleton entre
        event loops distintos de gunicorn.

        Raises:
            SunatNotFoundError: RUC no encontrado (404 del scraper)
            ReniecNotFoundError: DNI no encontrado (404 del scraper)
            DocumentoInvalidoError: Documento con formato o longitud inválida (422)
            ScraperFormatError: Formato del portal cambió (502)
            ScraperUnavailableError: Portal o scraper no disponible (503)
            ScraperTimeoutError: Timeout esperando respuesta del portal (504)
        """
        import httpx

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
            ) as client:
                response = await client.get(f"/consultar/{documento}")
        except httpx.ConnectTimeout:
            raise ScraperUnavailableError("No se pudo conectar al servicio de consulta de documentos")
        except httpx.ReadTimeout:
            raise ScraperTimeoutError("El portal externo no respondió a tiempo. Intente más tarde.")
        except httpx.ConnectError:
            raise ScraperUnavailableError("Servicio de consulta de documentos no disponible")
        except httpx.HTTPError:
            raise ScraperUnavailableError("Error de conexión con el servicio de consulta de documentos")

        if response.status_code == 200:
            data = response.json()
            return ConsultaDocumentoResult(
                tipo_documento=data["tipo_documento"],
                numero_documento=data["numero_documento"],
                razon_social=data["razon_social"],
            )

        body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        detail = body.get("detail", "")

        if response.status_code == 404:
            # Determinar tipo por longitud del documento
            if len(documento) == 8:
                raise ReniecNotFoundError(documento)
            raise SunatNotFoundError(documento)

        if response.status_code == 422:
            msg = detail or "El documento tiene un formato o longitud inválida."
            raise DocumentoInvalidoError(msg)

        if response.status_code == 504:
            msg = detail or "El portal externo no respondió a tiempo. Intente más tarde."
            raise ScraperTimeoutError(msg)

        if response.status_code == 502:
            msg = detail or "El formato del portal externo cambió y no se pudo procesar la consulta."
            raise ScraperFormatError(msg)

        if response.status_code == 503:
            msg = detail or "El servicio de consulta de documentos no está disponible. Intente más tarde."
            raise ScraperUnavailableError(msg)

        # Unexpected status — raise with SCRAPER_UNAVAILABLE code for safety
        raise ScraperUnavailableError("Error inesperado en el servicio de consulta de documentos")
