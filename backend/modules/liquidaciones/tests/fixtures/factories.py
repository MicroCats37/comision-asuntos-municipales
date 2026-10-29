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
    numero_revision=1,
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
        numero_revision: int — revision number chosen by the user (1, 3 or 5).
            It is REQUIRED by the creation / relacionada / nueva-revision contracts, so
            it is always sent. Pass a different value to exercise another revision.

    Returns:
        dict with keys: liquidacion_general, liquidacion_especifica, numero_revision
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

    payload = {
        "liquidacion_general": general,
        "liquidacion_especifica": especifica,
        "numero_revision": numero_revision,
    }
    return payload


# ── M2 payloads ───────────────────────────────────────────────────────────────

def make_payload_m2(
    valid_municipalidad_id,
    valid_distrito_id,
    tarifa_m2_id,
    *,
    expediente="EXP-M2-001",
    area_solicitada=100.0,
    observacion="Test M2",
    numero_revision=1,
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
        numero_revision: int — revision number chosen by the user (1, 3 or 5).
            It is REQUIRED by the creation / relacionada / nueva-revision contracts, so
            it is always sent. Pass a different value to exercise another revision.

    Returns:
        dict with keys: liquidacion_general, liquidacion_especifica, numero_revision
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
    payload = {
        "liquidacion_general": general,
        "liquidacion_especifica": {
            "datos": {
                "area_solicitada": area_solicitada,
            },
            "tarifa": {
                "tarifa_m2_id": str(tarifa_m2_id),
            },
        },
        "numero_revision": numero_revision,
    }
    return payload


# ── Revision-aware payloads (numero_revision is client-authoritative) ─────────

def make_payload_relacionada(payload, liquidacion_previa_id, numero_revision=None):
    """Extend a creation payload with the /relacionada keys.

    Args:
        payload: dict — a creation payload (make_payload_po / make_payload_m2)
        liquidacion_previa_id: str — id of the previous liquidacion
        numero_revision: int or None — revision number chosen by the user (1, 3 or 5).
            None keeps the revision already carried by `payload` (which is already
            contract-valid). Pass an explicit value to override it.

    Returns:
        dict with keys: liquidacion_previa_id + the creation keys (incl. numero_revision)
    """
    result = dict(payload)
    result["liquidacion_previa_id"] = str(liquidacion_previa_id)
    if numero_revision is not None:
        result["numero_revision"] = numero_revision
    return result


def make_payload_po_nueva_revision(
    liquidacion_previa_id,
    *,
    expediente="EXP-NUEVA-REV-001",
    observacion="Test nueva revision",
    tipo_tramite=None,
    tarifas=None,
    numero_revision=3,
):
    """Build a reduced PO payload for /nueva-revision (Edificaciones/Taludes/Impacto Vial).

    The reduced payload inherits proyecto/municipalidad/valor_declarado from the
    previous liquidacion, so only expediente, observacion, denominacion and the
    tarifas are sent.

    Args:
        liquidacion_previa_id: str — id of the previous liquidacion
        expediente: str
        observacion: str
        tipo_tramite: str or None — only Edificaciones consumes it
        tarifas: list or None — None/[] = auto-fill
        numero_revision: int — revision number chosen by the user (1, 3 or 5).
            The backend never derives it from the previa and never rejects a repeated
            revision number.

    Returns:
        dict with keys: liquidacion_previa_id, liquidacion_general, liquidacion_especifica,
            numero_revision
    """
    payload = {
        "liquidacion_previa_id": str(liquidacion_previa_id),
        "liquidacion_general": {
            "expediente": expediente,
            "observacion": observacion,
            "denominacion_de_proyecto": "Proyecto Test Nueva Revision",
        },
        "liquidacion_especifica": {
            "tarifas": [] if tarifas is None else tarifas,
        },
        "numero_revision": numero_revision,
    }
    if tipo_tramite is not None:
        payload["liquidacion_especifica"]["tipo_tramite"] = tipo_tramite
    return payload


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


# ── M2 Edge payloads ───────────────────────────────────────────────────────────

def make_payload_m2_edge(
    valid_municipalidad_id,
    valid_distrito_id,
    *,
    subtotal_manual: float,
    area_m2: float = 100.0,
    numero_revision: int = 1,
    expediente="EXP-EDGE-M2-001",
    observacion="Test Edge M2",
    contacto=None,
    denominacion_de_proyecto=None,
):
    """
    Build an M2 edge (manual) payload for Habilitación Urbana or Mecánica de Suelos.

    Args:
        valid_municipalidad_id: str — municipalidad.id
        valid_distrito_id: str — ubigeo_distrito.id
        subtotal_manual: float — pre-IGV subtotal (must be > 0)
        area_m2: float — area for traceability (must be >= 0)
        numero_revision: int — revision number: 1, 3, or 5
        expediente: str
        observacion: str
        contacto: dict or None — contacto sub-dict
        denominacion_de_proyecto: str or None

    Returns:
        dict with keys: liquidacion_general, subtotal_manual, area_m2, numero_revision
    """
    proyecto = make_proyecto_payload(
        distrito_id=valid_distrito_id,
        denominacion="Proyecto Test Edge M2",
    )
    general = make_liquidacion_general_payload(
        municipalidad_id=valid_municipalidad_id,
        expediente=expediente,
        observacion=observacion,
        proyecto=proyecto,
        contacto=contacto,
        denominacion_de_proyecto=denominacion_de_proyecto,
    )
    return {
        "liquidacion_general": general,
        "subtotal_manual": subtotal_manual,
        "area_m2": area_m2,
        "numero_revision": numero_revision,
    }


# ── PO Edge payloads ───────────────────────────────────────────────────────────

def make_payload_po_edge(
    valid_municipalidad_id,
    valid_distrito_id,
    *,
    subtotal_manual: float,
    numero_revision: int = 1,
    expediente="EXP-EDGE-001",
    observacion="Test Edge PO",
    contacto=None,
    denominacion_de_proyecto=None,
):
    """
    Build a PO edge (manual) payload for Edificaciones/Taludes/Impacto Vial.

    Args:
        valid_municipalidad_id: str — municipalidad.id
        valid_distrito_id: str — ubigeo_distrito.id
        subtotal_manual: float — pre-IGV subtotal (must be > 0)
        numero_revision: int — revision number: 1, 3, or 5
        expediente: str
        observacion: str
        contacto: dict or None — contacto sub-dict
        denominacion_de_proyecto: str or None

    Returns:
        dict with keys: liquidacion_general, subtotal_manual, numero_revision
    """
    proyecto = make_proyecto_payload(
        distrito_id=valid_distrito_id,
        denominacion="Proyecto Test Edge",
    )
    general = make_liquidacion_general_payload(
        municipalidad_id=valid_municipalidad_id,
        expediente=expediente,
        observacion=observacion,
        proyecto=proyecto,
        contacto=contacto,
        denominacion_de_proyecto=denominacion_de_proyecto,
    )
    return {
        "liquidacion_general": general,
        "subtotal_manual": subtotal_manual,
        "numero_revision": numero_revision,
    }


# ── PATCH payloads (editable revision) ───────────────────────────────────────

def make_patch_general_payload(numero_revision=None, **kwargs):
    """Build the PATCH body for PATCH /liquidaciones/generales/{id}.

    Args:
        numero_revision: int or None — revision number chosen by the user (1, 3 or 5).
            It is OPTIONAL: when omitted the stored revision is preserved.
        **kwargs: any other editable general field (expediente, observacion,
            denominacion_de_proyecto, municipalidad_id, proyecto, contacto).

    Returns:
        dict — the PATCH body.
    """
    payload = dict(kwargs)
    if numero_revision is not None:
        payload["numero_revision"] = numero_revision
    return payload


def make_patch_wrapper_general_payload(numero_revision=None, **kwargs):
    """Build the PATCH body for PATCH /liquidaciones/{tipo}/{id} (wrapper format).

    Args:
        numero_revision: int or None — revision number chosen by the user (1, 3 or 5).
            It is OPTIONAL: when omitted the stored revision is preserved.
        **kwargs: any other editable general field.

    Returns:
        dict with key: liquidacion_general
    """
    liquidacion_general = dict(kwargs)
    if numero_revision is not None:
        liquidacion_general["numero_revision"] = numero_revision
    return {"liquidacion_general": liquidacion_general}


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


# ── PO Edificaciones: payloads por estrategia de cotización ───────────────────
#
# El discriminador `estrategia_cotizacion` es OPCIONAL: si no se envía, el
# backend asume NORMAL_SELECCIONADAS y el payload vigente queda byte-compatible.

def make_estrategia_po_especifica(
    *,
    estrategia_cotizacion=None,
    valor_declarado=1000000.00,
    total_explicito=None,
    tarifas=None,
    tipo_tramite=None,
    datos_extra=None,
):
    """Build the `liquidacion_especifica` block of an Edificaciones strategy payload.

    Args:
        estrategia_cotizacion: str or None — one of the three canonical strategies.
            None omits the discriminator (backend assumes NORMAL_SELECCIONADAS).
        valor_declarado: float — required by all three strategies; in
            TOTAL_EXPLICITO it is informational.
        total_explicito: float or None — used by TOTAL_EXPLICITO (IGV included).
        tarifas: list or None — [{"tarifa_porcentaje_obra_id", "especialidad_id"}, ...].
            None/[] = auto-fill mode.
        tipo_tramite: str or None.
        datos_extra: dict or None — extra keys merged into `datos` (used to build
            intentionally invalid payloads in the union validation tests).

    Returns:
        dict with keys: estrategia_cotizacion (optional), datos, tipo_tramite, tarifas
    """
    datos = {"valor_declarado": valor_declarado}
    if total_explicito is not None:
        datos["total_explicito"] = total_explicito
    if datos_extra:
        datos.update(datos_extra)

    especifica = {
        "datos": datos,
        "tarifas": [] if tarifas is None else tarifas,
    }
    if estrategia_cotizacion is not None:
        especifica["estrategia_cotizacion"] = estrategia_cotizacion
    if tipo_tramite is not None:
        especifica["tipo_tramite"] = tipo_tramite
    return especifica


def make_payload_po_estrategia(
    valid_municipalidad_id,
    valid_distrito_id,
    *,
    estrategia_cotizacion=None,
    valor_declarado=1000000.00,
    total_explicito=None,
    tarifas=None,
    tipo_tramite=None,
    expediente="EXP-PO-ESTRATEGIA-001",
    observacion="Test PO estrategias",
    contacto=None,
    denominacion_de_proyecto=None,
    numero_revision=1,
    datos_extra=None,
):
    """Build a full Edificaciones creation payload with a quotation strategy."""
    proyecto = make_proyecto_payload(
        distrito_id=valid_distrito_id,
        denominacion="Proyecto Test PO Estrategia",
    )
    general = make_liquidacion_general_payload(
        municipalidad_id=valid_municipalidad_id,
        expediente=expediente,
        observacion=observacion,
        proyecto=proyecto,
        contacto=contacto,
        denominacion_de_proyecto=denominacion_de_proyecto,
    )
    return {
        "liquidacion_general": general,
        "liquidacion_especifica": make_estrategia_po_especifica(
            estrategia_cotizacion=estrategia_cotizacion,
            valor_declarado=valor_declarado,
            total_explicito=total_explicito,
            tarifas=tarifas,
            tipo_tramite=tipo_tramite,
            datos_extra=datos_extra,
        ),
        "numero_revision": numero_revision,
    }


def make_payload_po_cotizar_estrategia(
    *,
    estrategia_cotizacion=None,
    valor_declarado=1000000.00,
    total_explicito=None,
    tarifas=None,
    tipo_tramite=None,
    datos_extra=None,
):
    """Build an Edificaciones `/cotizar` preview payload with a quotation strategy."""
    return {
        "liquidacion_especifica": make_estrategia_po_especifica(
            estrategia_cotizacion=estrategia_cotizacion,
            valor_declarado=valor_declarado,
            total_explicito=total_explicito,
            tarifas=tarifas,
            tipo_tramite=tipo_tramite,
            datos_extra=datos_extra,
        )
    }


# -- PO Edificaciones: payloads de edicion (Module 5) -------------------------
#
# El bloque `liquidacion_tipo` de la edicion lleva la MISMA union discriminado
# de estrategias que la creacion, pero `tarifas` es OBLIGATORIO: en edicion los
# participantes no se auto-completan (auto-rellenar cambiaria en silencio el
# alcance del calculo).


def make_estrategia_po_edicion_tipo(
    *,
    estrategia_cotizacion=None,
    valor_declarado=None,
    total_explicito=None,
    tarifas=None,
    tipo_tramite=None,
):
    """Build the `liquidacion_tipo` block of an Edificaciones EDITION payload.

    Args:
        estrategia_cotizacion: str or None - one of the three canonical strategies.
            None omits the discriminator (backend keeps the persisted strategy
            on PATCH / inherits it on nueva-revision).
        valor_declarado: float or None - required by NORMAL_SELECCIONADAS and
            TARIFA_HABILITADAS_PARTICIPANTES.
        total_explicito: float or None - required by TOTAL_EXPLICITO.
        tarifas: list or None - [{"tarifa_porcentaje_obra_id", "especialidad_id"}].
            None = preserve the current participants (PATCH) / required on edit.
        tipo_tramite: str or None.

    Returns:
        dict with keys: estrategia_cotizacion (optional), datos, tipo_tramite, tarifas
    """
    datos = {}
    if valor_declarado is not None:
        datos["valor_declarado"] = valor_declarado
    if total_explicito is not None:
        datos["total_explicito"] = total_explicito
    if tipo_tramite is not None:
        datos["tipo_tramite"] = tipo_tramite

    tipo = {"datos": datos}
    if estrategia_cotizacion is not None:
        tipo["estrategia_cotizacion"] = estrategia_cotizacion
    if tipo_tramite is not None:
        tipo["tipo_tramite"] = tipo_tramite
    if tarifas is not None:
        tipo["tarifas"] = tarifas
    return tipo


def make_payload_po_cotizar_edicion_estrategia(
    *,
    estrategia_cotizacion=None,
    valor_declarado=1000000.00,
    total_explicito=None,
    tarifas=None,
    tipo_tramite=None,
):
    """Build an Edificaciones `/cotizar-edicion` preview payload with a strategy."""
    return {
        "liquidacion_tipo": make_estrategia_po_edicion_tipo(
            estrategia_cotizacion=estrategia_cotizacion,
            valor_declarado=valor_declarado,
            total_explicito=total_explicito,
            tarifas=tarifas,
            tipo_tramite=tipo_tramite,
        )
    }


def make_patch_po_estrategia(
    *,
    estrategia_cotizacion=None,
    valor_declarado=None,
    total_explicito=None,
    tarifas=None,
    tipo_tramite=None,
    numero_revision=None,
    general_extra=None,
):
    """Build an Edificaciones PATCH payload with the quotation strategy block.

    Returns:
        dict with keys: liquidacion_general (opcional), liquidacion_tipo (opcional)
    """
    payload = {}

    general = dict(general_extra or {})
    if numero_revision is not None:
        general["numero_revision"] = numero_revision
    if general:
        payload["liquidacion_general"] = general

    tipo = make_estrategia_po_edicion_tipo(
        estrategia_cotizacion=estrategia_cotizacion,
        valor_declarado=valor_declarado,
        total_explicito=total_explicito,
        tarifas=tarifas,
        tipo_tramite=tipo_tramite,
    )
    if tipo:
        payload["liquidacion_tipo"] = tipo
    return payload


def make_payload_po_nueva_revision_estrategia(
    liquidacion_previa_id,
    *,
    estrategia_cotizacion=None,
    valor_declarado=None,
    total_explicito=None,
    tarifas=None,
    tipo_tramite=None,
    numero_revision=3,
    expediente="EXP-NUEVA-REV-ESTRATEGIA-001",
    observacion="Test nueva revision con estrategia",
):
    """Build an Edificaciones `/nueva-revision` payload with the strategy block.

    The revision INHERITS the strategy and the data of the previa when the
    payload does not declare them.
    """
    payload = {
        "liquidacion_previa_id": str(liquidacion_previa_id),
        "liquidacion_general": {
            "expediente": expediente,
            "observacion": observacion,
        },
        "liquidacion_especifica": {
            "tarifas": [] if tarifas is None else tarifas,
        },
        "numero_revision": numero_revision,
    }
    if tipo_tramite is not None:
        payload["liquidacion_especifica"]["tipo_tramite"] = tipo_tramite
    if estrategia_cotizacion is not None:
        payload["liquidacion_especifica"]["estrategia_cotizacion"] = (
            estrategia_cotizacion
        )
    datos = {}
    if valor_declarado is not None:
        datos["valor_declarado"] = valor_declarado
    if total_explicito is not None:
        datos["total_explicito"] = total_explicito
    if datos:
        payload["liquidacion_especifica"]["datos"] = datos
    return payload


def make_payload_po_relacionada_estrategia(
    liquidacion_previa_id,
    *,
    municipalidad_id,
    distrito_id,
    estrategia_cotizacion=None,
    valor_declarado=1000000.00,
    total_explicito=None,
    tarifas=None,
    tipo_tramite=None,
    numero_revision=1,
    expediente="EXP-RELACIONADA-ESTRATEGIA-001",
    observacion="Test relacionada con estrategia",
):
    """Build an Edificaciones `/relacionada` payload with the strategy union."""
    payload = {
        "liquidacion_previa_id": str(liquidacion_previa_id),
        "numero_revision": numero_revision,
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad_id),
            "expediente": expediente,
            "observacion": observacion,
            "proyecto": {
                "denominacion": "Proyecto Test Relacionada Estrategia",
                "nombre_propietario": "Propietario Relacionada SAC",
                "direccion": "Av. Relacionada 456, Lima",
                "distrito_id": str(distrito_id),
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789099",
                    "razon_social": "Propietario Relacionada SAC",
                },
            },
        },
        "liquidacion_especifica": make_estrategia_po_especifica(
            estrategia_cotizacion=estrategia_cotizacion,
            valor_declarado=valor_declarado,
            total_explicito=total_explicito,
            tarifas=tarifas,
            tipo_tramite=tipo_tramite,
        ),
    }
    return payload
