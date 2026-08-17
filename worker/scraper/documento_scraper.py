"""
documento_scraper.py — Lógica de scraping para consulta unificada de RUC (11 dígitos) y DNI (8 dígitos).

Flujo:
  1. GET /FrameCriterioBusquedaWeb.jsp  → obtiene sesión/cookie
  2. POST /jcrS00Alias                  → scraping y parsing HTML

Manejo de errores:
  - ScraperTimeoutError     → El portal no respondió a tiempo
  - ScraperUnavailableError → El portal no responde / error de red
  - ScraperFormatError      → Formato HTML del portal cambió
  - DocumentNotFoundError   → Documento no encontrado
"""

import random
import logging
from dataclasses import dataclass
from enum import Enum

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

TIMEOUT_CONNECT = 10   # segundos para conectar
TIMEOUT_READ = 120     # segundos para leer respuesta


class TipoDocumento(str, Enum):
    RUC = "RUC"
    DNI = "DNI"


@dataclass
class ConsultaResult:
    tipo_documento: TipoDocumento
    numero_documento: str
    razon_social: str


# ──────────────────────────────────────────────
# Excepciones tipadas
# ──────────────────────────────────────────────

class ScraperTimeoutError(Exception):
    """El portal no respondió dentro del timeout configurado."""


class ScraperUnavailableError(Exception):
    """Error de red o portal no disponible."""


class ScraperFormatError(Exception):
    """El HTML del portal cambió — la estructura esperada no existe."""


class DocumentNotFoundError(Exception):
    """El documento no existe en el registro del portal."""
    def __init__(self, documento: str, tipo: TipoDocumento):
        self.documento = documento
        self.tipo = tipo
        super().__init__(f"{tipo} {documento!r} no encontrado")


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _generate_token(length: int = 52) -> str:
    """Genera token aleatorio para el formulario."""
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    return "".join(random.choice(chars) for _ in range(length))


def _create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-PE,es;q=0.9",
    })
    return session


def _init_session(session: requests.Session) -> None:
    try:
        logger.debug("GET init page...")
        session.get(
            f"{BASE_URL}/FrameCriterioBusquedaWeb.jsp",
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
        )
    except requests.exceptions.ConnectTimeout as e:
        raise ScraperUnavailableError("No se pudo conectar al portal de consultas") from e
    except requests.exceptions.ReadTimeout as e:
        raise ScraperTimeoutError("El portal de consultas no respondió el GET inicial") from e
    except requests.exceptions.ConnectionError as e:
        raise ScraperUnavailableError(f"Error de red al consultar el portal: {e}") from e


def _post_query(session: requests.Session, data: dict) -> BeautifulSoup:
    try:
        logger.debug("POST query: accion=%s", data.get("accion"))
        response = session.post(
            f"{BASE_URL}/jcrS00Alias",
            data=data,
            headers={"Referer": f"{BASE_URL}/FrameCriterioBusquedaWeb.jsp"},
            timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
        )
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")
    except requests.exceptions.ReadTimeout as e:
        raise ScraperTimeoutError("El portal no respondió el POST a tiempo") from e
    except requests.exceptions.ConnectionError as e:
        raise ScraperUnavailableError(f"Error de red en POST: {e}") from e
    except requests.exceptions.HTTPError as e:
        raise ScraperUnavailableError(f"El portal devolvió HTTP {e.response.status_code}") from e


def _check_server_error(soup: BeautifulSoup) -> None:
    title = soup.find("title")
    if title and "Pagina de Error" in title.get_text():
        raise ScraperUnavailableError("El portal devolvió página de error interna")


def _parse_ruc(soup: BeautifulSoup, ruc: str) -> ConsultaResult:
    _check_server_error(soup)

    page_text = soup.get_text()
    not_found_signals = [
        "no es válido",
        "no es valido",
        "no se encontr",
        "no existe",
    ]
    if any(sig in page_text.lower() for sig in not_found_signals):
        raise DocumentNotFoundError(ruc, TipoDocumento.RUC)

    for h4 in soup.find_all("h4"):
        text = h4.get_text(strip=True)
        if " - " in text and len(text) > 15:
            parts = text.split(" - ", 1)
            numero = parts[0].strip()
            razon = parts[1].strip()
            if numero.isdigit() and len(numero) == 11:
                return ConsultaResult(
                    tipo_documento=TipoDocumento.RUC,
                    numero_documento=numero,
                    razon_social=razon,
                )

    items = soup.find_all("div", class_="list-group-item")
    if not items:
        raise ScraperFormatError("Estructura HTML del portal no reconocida para RUC")

    result_data: dict = {}
    for item in items:
        cols = item.find_all("div", class_=lambda c: c and "col-sm" in c)
        if len(cols) >= 2:
            label = cols[0].get_text(strip=True).rstrip(":")
            value = cols[1].get_text(strip=True)
            result_data[label] = value

    razon = result_data.get("Número de RUC", "").split(" - ", 1)
    if len(razon) < 2:
        raise ScraperFormatError("No se encontró razón social en el resultado RUC")

    return ConsultaResult(
        tipo_documento=TipoDocumento.RUC,
        numero_documento=ruc,
        razon_social=razon[1].strip(),
    )


def _parse_dni(soup: BeautifulSoup, dni: str) -> ConsultaResult:
    _check_server_error(soup)

    page_text = soup.get_text()
    not_found_signals = [
        "no se encontr",
        "no existe",
        "no es válido",
        "no es valido",
    ]
    if any(sig in page_text.lower() for sig in not_found_signals):
        raise DocumentNotFoundError(dni, TipoDocumento.DNI)

    first_result = soup.find("a", class_="aRucs")
    if not first_result:
        list_group = soup.find("div", class_="list-group")
        if list_group is not None:
            raise DocumentNotFoundError(dni, TipoDocumento.DNI)
        raise ScraperFormatError("Estructura HTML del portal no reconocida para DNI")

    headings = first_result.find_all("h4")
    nombre = ""
    for h4 in headings:
        text = h4.get_text(strip=True)
        if not text.startswith("RUC:"):
            nombre = text
            break

    if not nombre:
        raise ScraperFormatError("No se encontró nombre en el resultado DNI")

    return ConsultaResult(
        tipo_documento=TipoDocumento.DNI,
        numero_documento=dni,
        razon_social=nombre,
    )


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def consultar(documento: str) -> ConsultaResult:
    """
    Consulta por número de documento (8 dígitos = DNI, 11 dígitos = RUC).
    """
    if not documento.isdigit():
        raise ValueError(f"El documento debe ser numérico: {documento!r}")

    longitud = len(documento)
    if longitud == 11:
        return _consultar_ruc(documento)
    elif longitud == 8:
        return _consultar_dni(documento)
    else:
        raise ValueError(
            f"Documento inválido: {longitud} dígitos. Se esperan 8 (DNI) o 11 (RUC)"
        )


def _consultar_ruc(ruc: str) -> ConsultaResult:
    session = _create_session()
    _init_session(session)

    data = {
        "accion": "consPorRuc",
        "razSoc": "",
        "nroRuc": ruc,
        "nrodoc": "",
        "token": _generate_token(),
        "contexto": "ti-it",
        "modo": "1",
        "rbtnTipo": "1",
        "search1": ruc,
        "tipdoc": "",
        "search2": "",
        "search3": "",
        "codigo": "",
    }
    soup = _post_query(session, data)
    return _parse_ruc(soup, ruc)


def _consultar_dni(dni: str) -> ConsultaResult:
    session = _create_session()
    _init_session(session)

    data = {
        "accion": "consPorTipdoc",
        "razSoc": "",
        "nroRuc": "",
        "nrodoc": dni,
        "token": _generate_token(),
        "contexto": "ti-it",
        "modo": "1",
        "rbtnTipo": "2",
        "search1": "",
        "tipdoc": "1",   # 1 = DNI
        "search2": dni,
        "search3": "",
        "codigo": "",
    }
    soup = _post_query(session, data)
    return _parse_dni(soup, dni)
