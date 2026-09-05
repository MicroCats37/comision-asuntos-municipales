"""
Factories — helper functions to build valid API payloads for liquidaciones.

These are NOT fixtures (no db dependency), just pure functions that return dicts.
Use them inside tests or fixtures to avoid hardcoded payload literals.

Payload structures match the actual API schemas:
- PO (Edificaciones, Taludes, Impacto Vial): valor_declarado + tarifas[]
- M2 (HU, MS): area_solicitada + tarifa_m2_id
- IO (Inspección Obra): cantidad_visitas + categoria + tarifa_visitas_id
"""


def make_proyecto_payload(distrito_id, denominacion="Proyecto Test", **kwargs):
    """Build the proyecto sub-dict for liquidacion_general.proyecto.

    Args:
        distrito_id: str — ubigeo_distrito.id
        denominacion: str — project name
        **kwargs: override any proyecto field (nombre_propietario, direccion,
                  entidad_tipo_documento, entidad_numero_documento, entidad_razon_social)
    """
    defaults = {
        "denominacion": denominacion,
        "nombre_propietario": "Propietario Test SAC",
        "direccion": "Av. Test 123, Lima",
        "distrito_id": distrito_id,
        "entidad": {
            "tipo_documento": "RUC",
            "numero_documento": "20456789012",
            "razon_social": "Propietario Test SAC",
        },
    }
    defaults.update(kwargs)
    return defaults


def make_liquidacion_general_payload(
    municipalidad_id,
    expediente="EXP-TEST-001",
    observacion="Test liquidacion",
    proyecto=None,
    contacto=None,
    denominacion_de_proyecto=None,
):
    """Build the liquidacion_general dict.

    Args:
        municipalidad_id: str
        expediente: str
        observacion: str
        proyecto: dict — result of make_proyecto_payload(), or None (a default is created)
        contacto: dict or None — contacto sub-dict (nombres, apellidos, dni, cargo, celular)
        denominacion_de_proyecto: str or None — project title at liquidacion level
    """
    if proyecto is None:
        raise ValueError("proyecto is required (use make_proyecto_payload)")
    result = {
        "municipalidad_id": municipalidad_id,
        "expediente": expediente,
        "observacion": observacion,
        "proyecto": proyecto,
    }
    if contacto is not None:
        result["contacto"] = contacto
    if denominacion_de_proyecto is not None:
        result["denominacion_de_proyecto"] = denominacion_de_proyecto
    return result


# ── PO payloads ───────────────────────────────────────────────────────────────

def make_payload_po(
    valid_municipalidad_id,
    valid_distrito_id,
    *,
    expediente="EXP-PO-001",
    valor_declarado=100000.00,
    tarifas=None,
    observacion="Test PO",
    contacto=None,
    tipo_tramite=None,
    denominacion_de_proyecto=None,
):
    """Build a complete PO (PorcentajeObra) payload for Edificaciones/Taludes/Impacto Vial.

    Auto-fill mode: tarifas=None or tarifas=[] (backend fills from vigentes)
    Explicit mode:  tarifas=[{tarifa_porcentaje_obra_id, especialidad_id}, ...]

    Args:
        valid_municipalidad_id: str — municipalidad.id
        valid_distrito_id: str — ubigeo_distrito.id
        expediente: str
        valor_declarado: float
        tarifas: list or None — None/[] = auto-fill, [...] = explicit
        observacion: str
        contacto: dict or None — contacto sub-dict (nombres, apellidos, dni, cargo, celular)
        tipo_tramite: str or None — tipo_tramite value (e.g. OBRA_NUEVA, AMPLIACION).
            Sent at top level of liquidacion_especifica to match frontend payload format.

    Returns:
        dict with keys: liquidacion_general, liquidacion_especifica
    """
    proyecto = make_proyecto_payload(
        distrito_id=valid_distrito_id,
        denominacion="Proyecto Test PO",
    )
    general = make_liquidacion_general_payload(
        municipalidad_id=valid_municipalidad_id,
        expediente=expediente,
        observacion=observacion,
        proyecto=proyecto,
        contacto=contacto,
        denominacion_de_proyecto=denominacion_de_proyecto,
    )
    # auto-fill mode: send empty list (not null) so backend recognizes auto-fill
    tarifas_list = [] if tarifas is None else tarifas

    especifica = {
        "datos": {
            "valor_declarado": valor_declarado,
        },
        "tarifas": tarifas_list,
    }
    # tipo_tramite sent at top level (frontend format)
    if tipo_tramite is not None:
        especifica["tipo_tramite"] = tipo_tramite

    return {
        "liquidacion_general": general,
        "liquidacion_especifica": especifica,
    }


# ── M2 payloads ───────────────────────────────────────────────────────────────

def make_payload_m2(
    valid_municipalidad_id,
    valid_distrito_id,
    tarifa_m2_id,
    *,
    expediente="EXP-M2-001",
    area_solicitada=100.0,
    observacion="Test M2",
):
    """Build a complete M2 (Por Metro Cuadrado) payload for HU or MS.

    The cotizar endpoint only needs liquidacion_especifica.
    The crear endpoint (primera-revision) also needs liquidacion_general.

    Args:
        valid_municipalidad_id: str
        valid_distrito_id: str
        tarifa_m2_id: str — TarifaPorMetroCuadrado.id
        expediente: str
        area_solicitada: float
        observacion: str

    Returns:
        dict with keys: liquidacion_general, liquidacion_especifica
    """
    proyecto = make_proyecto_payload(
        distrito_id=valid_distrito_id,
        denominacion="Proyecto Test M2",
    )
    general = make_liquidacion_general_payload(
        municipalidad_id=valid_municipalidad_id,
        expediente=expediente,
        observacion=observacion,
        proyecto=proyecto,
    )
    return {
        "liquidacion_general": general,
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": area_solicitada,
            },
            "tarifa": {
                "tarifa_m2_id": str(tarifa_m2_id),
            },
        },
    }


def make_payload_m2_cotizar(tarifa_m2_id, area_solicitada=100.0):
    """Build a cotizar-only M2 payload (no liquidacion_general needed).

    Args:
        tarifa_m2_id: str — TarifaPorMetroCuadrado.id
        area_solicitada: float

    Returns:
        dict with key: liquidacion_especifica
    """
    return {
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": area_solicitada,
            },
            "tarifa": {
                "tarifa_m2_id": str(tarifa_m2_id),
            },
        },
    }


# ── IO payloads ───────────────────────────────────────────────────────────────

def make_payload_io(
    valid_municipalidad_id,
    valid_distrito_id,
    tarifa_visitas_id,
    *,
    expediente="EXP-IO-001",
    cantidad_visitas=3,
    categoria="INSPECCION",
    observacion="Test IO",
):
    """Build a complete IO (Inspección de Obra) payload.

    Args:
        valid_municipalidad_id: str
        valid_distrito_id: str
        tarifa_visitas_id: str — TarifaPorCategoriaVisitas.id
        expediente: str
        cantidad_visitas: int
        categoria: str — e.g. "INSPECCION"
        observacion: str

    Returns:
        dict with keys: liquidacion_general, liquidacion_especifica
    """
    proyecto = make_proyecto_payload(
        distrito_id=valid_distrito_id,
        denominacion="Proyecto Test IO",
    )
    general = make_liquidacion_general_payload(
        municipalidad_id=valid_municipalidad_id,
        expediente=expediente,
        observacion=observacion,
        proyecto=proyecto,
    )
    return {
        "liquidacion_general": general,
        "liquidacion_especifica": {
            "datos": {
                "cantidad_visitas": cantidad_visitas,
                "categoria": categoria,
            },
            "tarifa": {
                "tarifa_visitas_id": str(tarifa_visitas_id),
            },
        },
    }
