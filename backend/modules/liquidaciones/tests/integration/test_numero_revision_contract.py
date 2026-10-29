"""
Contract tests for the `numero_revision` input contracts.

Covers:
- Creation / relacionada / nueva-revision inputs of the five revision-capable types
  (Edificaciones, Habilitacion Urbana, Mecanica Suelos, Taludes, Impacto Vial)
  require `numero_revision`.
- The allowed set is centralized in {1, 3, 5} (max MAX_REVISIONES = 5).
- PATCH general contracts accept an optional `numero_revision` with the same validation.
- Inspeccion de Obra stays outside the editable revision contracts (fixed at revision 1).

These are schema-level tests — no DB access required.
"""
import uuid

import pytest
from pydantic import ValidationError

from modules.liquidaciones.domain.constants import (
    MAX_REVISIONES,
    NUMERO_REVISION_PERMITIDOS,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_edificaciones_schemas import (
    LiquidacionEdificacionesInput,
    LiquidacionEdificacionesNuevaRevisionInput,
    LiquidacionEdificacionesRelacionadaInput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_habilitacion_urbana_schemas import (
    LiquidacionHabilitacionUrbanaInput,
    LiquidacionHabilitacionUrbanaNuevaRevisionInput,
    LiquidacionHabilitacionUrbanaRelacionadaInput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_impacto_vial_schemas import (
    LiquidacionImpactoVialInput,
    LiquidacionImpactoVialNuevaRevisionInput,
    LiquidacionImpactoVialRelacionadaInput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
    LiquidacionInspeccionObraNuevaLiquidacionInput,
    LiquidacionInspeccionObraNuevaRevisionInput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_mecanica_suelos_schemas import (
    LiquidacionMecanicaSuelosInput,
    LiquidacionMecanicaSuelosNuevaRevisionInput,
    LiquidacionMecanicaSuelosRelacionadaInput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_patch_m2_schemas import (
    LiquidacionPatchM2GeneralIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_patch_po_schemas import (
    LiquidacionPatchPOGeneralIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_patch_visitas_schemas import (
    LiquidacionPatchVisitasGeneralIn,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_taludes_schemas import (
    LiquidacionTaludesInput,
    LiquidacionTaludesNuevaRevisionInput,
    LiquidacionTaludesRelacionadaInput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralUpdateIn,
    NumeroRevisionOpcionalMixin,
    NumeroRevisionRequeridoMixin,
)
from modules.liquidaciones.tests.fixtures.factories import (
    make_payload_m2,
    make_payload_po,
    make_payload_po_nueva_revision,
    make_payload_relacionada,
)

# ── Constants ─────────────────────────────────────────────────────────────────

MUNICIPALIDAD_ID = str(uuid.uuid4())
DISTRITO_ID = str(uuid.uuid4())
TARIFA_M2_ID = str(uuid.uuid4())
PREVIA_ID = str(uuid.uuid4())

PO_TYPES = ("edificaciones", "taludes", "impacto_vial")
M2_TYPES = ("habilitacion_urbana", "mecanica_suelos")

# tipo -> {modo: schema de entrada}
INPUT_SCHEMAS = {
    "edificaciones": {
        "creacion": LiquidacionEdificacionesInput,
        "relacionada": LiquidacionEdificacionesRelacionadaInput,
        "nueva_revision": LiquidacionEdificacionesNuevaRevisionInput,
    },
    "taludes": {
        "creacion": LiquidacionTaludesInput,
        "relacionada": LiquidacionTaludesRelacionadaInput,
        "nueva_revision": LiquidacionTaludesNuevaRevisionInput,
    },
    "impacto_vial": {
        "creacion": LiquidacionImpactoVialInput,
        "relacionada": LiquidacionImpactoVialRelacionadaInput,
        "nueva_revision": LiquidacionImpactoVialNuevaRevisionInput,
    },
    "habilitacion_urbana": {
        "creacion": LiquidacionHabilitacionUrbanaInput,
        "relacionada": LiquidacionHabilitacionUrbanaRelacionadaInput,
        "nueva_revision": LiquidacionHabilitacionUrbanaNuevaRevisionInput,
    },
    "mecanica_suelos": {
        "creacion": LiquidacionMecanicaSuelosInput,
        "relacionada": LiquidacionMecanicaSuelosRelacionadaInput,
        "nueva_revision": LiquidacionMecanicaSuelosNuevaRevisionInput,
    },
}

MODOS = ("creacion", "relacionada", "nueva_revision")


def build_payload(tipo: str, modo: str) -> dict:
    """Build a valid payload (without numero_revision) for a given tipo/modo.

    The factories always send `numero_revision` because the contract requires it;
    here it is stripped on purpose to assert that omitting it is rejected.
    """
    if tipo in PO_TYPES:
        creation = make_payload_po(MUNICIPALIDAD_ID, DISTRITO_ID)
        if modo == "creacion":
            payload = creation
        elif modo == "relacionada":
            payload = make_payload_relacionada(creation, PREVIA_ID)
        else:
            payload = make_payload_po_nueva_revision(PREVIA_ID)
    else:
        creation = make_payload_m2(MUNICIPALIDAD_ID, DISTRITO_ID, TARIFA_M2_ID)
        if modo == "creacion":
            payload = creation
        else:
            # HU / MS nueva-revision uses the full general header (same shape as creation)
            payload = make_payload_relacionada(creation, PREVIA_ID)

    payload.pop("numero_revision", None)
    return payload


# ── Tests: requiredness ───────────────────────────────────────────────────────

@pytest.mark.parametrize("tipo", sorted(INPUT_SCHEMAS))
@pytest.mark.parametrize("modo", MODOS)
def test_revision_capable_inputs_require_numero_revision(tipo, modo):
    """
    GIVEN: a revision-capable liquidacion type
    WHEN: its creation / relacionada / nueva-revision input schema is inspected
    THEN: numero_revision is declared and required
    """
    schema = INPUT_SCHEMAS[tipo][modo]

    assert "numero_revision" in schema.model_fields
    assert schema.model_fields["numero_revision"].is_required()


@pytest.mark.parametrize("tipo", sorted(INPUT_SCHEMAS))
@pytest.mark.parametrize("modo", MODOS)
def test_revision_capable_inputs_use_the_shared_revision_block(tipo, modo):
    """
    GIVEN: a revision-capable liquidacion type
    WHEN: its input schema is inspected
    THEN: it composes the shared NumeroRevisionRequeridoMixin block (DRY)
    """
    schema = INPUT_SCHEMAS[tipo][modo]

    assert issubclass(schema, NumeroRevisionRequeridoMixin)


@pytest.mark.parametrize("tipo", sorted(INPUT_SCHEMAS))
@pytest.mark.parametrize("modo", MODOS)
def test_payload_without_numero_revision_is_rejected(tipo, modo):
    """
    GIVEN: a valid creation / relacionada / nueva-revision payload
    WHEN: numero_revision is omitted
    THEN: the contract rejects it — the backend never derives the revision number
    """
    schema = INPUT_SCHEMAS[tipo][modo]
    payload = build_payload(tipo, modo)

    assert "numero_revision" not in payload

    with pytest.raises(ValidationError) as exc_info:
        schema.model_validate(payload)

    assert "numero_revision" in str(exc_info.value)


# ── Tests: allowed set ────────────────────────────────────────────────────────

@pytest.mark.parametrize("tipo", sorted(INPUT_SCHEMAS))
@pytest.mark.parametrize("modo", MODOS)
@pytest.mark.parametrize("numero_revision", [1, 3, 5])
def test_allowed_revision_values_are_accepted(tipo, modo, numero_revision):
    """
    GIVEN: a valid creation / relacionada / nueva-revision payload
    WHEN: numero_revision is one of the allowed values (1, 3, 5)
    THEN: the contract accepts it
    """
    schema = INPUT_SCHEMAS[tipo][modo]
    payload = build_payload(tipo, modo)
    payload["numero_revision"] = numero_revision

    validated = schema.model_validate(payload)

    assert validated.numero_revision == numero_revision


@pytest.mark.parametrize("tipo", sorted(INPUT_SCHEMAS))
@pytest.mark.parametrize("modo", MODOS)
@pytest.mark.parametrize("numero_revision", [0, 2, 4, 6, -1])
def test_revision_values_outside_allowed_set_are_rejected(tipo, modo, numero_revision):
    """
    GIVEN: a valid creation / relacionada / nueva-revision payload
    WHEN: numero_revision is outside the allowed set {1, 3, 5}
    THEN: the contract rejects it
    """
    schema = INPUT_SCHEMAS[tipo][modo]
    payload = build_payload(tipo, modo)
    payload["numero_revision"] = numero_revision

    with pytest.raises(ValidationError):
        schema.model_validate(payload)


def test_allowed_revision_set_is_centralized():
    """
    GIVEN: the domain constants
    WHEN: the allowed revision set is inspected
    THEN: it is a single source of truth — {1, 3, 5}, never above MAX_REVISIONES
    """
    assert NUMERO_REVISION_PERMITIDOS == (1, 3, 5)
    assert max(NUMERO_REVISION_PERMITIDOS) == MAX_REVISIONES


def test_shared_revision_block_enforces_the_allowed_set():
    """
    GIVEN: the shared NumeroRevisionRequeridoMixin block
    WHEN: it is validated with values inside and outside the allowed set
    THEN: only {1, 3, 5} is accepted
    """

    class _Requerido(NumeroRevisionRequeridoMixin):
        pass

    for valor in NUMERO_REVISION_PERMITIDOS:
        assert _Requerido(numero_revision=valor).numero_revision == valor

    for valor in (0, 2, 4, 6, -1):
        with pytest.raises(ValidationError):
            _Requerido(numero_revision=valor)


# ── Tests: PATCH general contracts ────────────────────────────────────────────

@pytest.mark.parametrize(
    "schema",
    [LiquidacionGeneralUpdateIn, LiquidacionPatchPOGeneralIn, LiquidacionPatchM2GeneralIn],
)
def test_patch_general_contracts_accept_optional_numero_revision(schema):
    """
    GIVEN: a general PATCH contract (general liquidaciones, PO types, M2 types)
    WHEN: numero_revision is inspected
    THEN: it is declared, optional, and validated against the allowed set
    """
    assert "numero_revision" in schema.model_fields
    assert not schema.model_fields["numero_revision"].is_required()
    assert issubclass(schema, NumeroRevisionOpcionalMixin)

    assert schema().numero_revision is None
    for valor in NUMERO_REVISION_PERMITIDOS:
        assert schema(numero_revision=valor).numero_revision == valor
    for valor in (0, 2, 4, 6, -1):
        with pytest.raises(ValidationError):
            schema(numero_revision=valor)


# ── Tests: Inspección de Obra stays outside the editable revision contracts ───

def test_inspeccion_obra_contracts_exclude_numero_revision():
    """
    GIVEN: the Inspección de Obra contracts
    WHEN: they are inspected
    THEN: they do not expose numero_revision — IO stays fixed at revision 1
    """
    assert "numero_revision" not in LiquidacionInspeccionObraNuevaLiquidacionInput.model_fields
    assert "numero_revision" not in LiquidacionInspeccionObraNuevaRevisionInput.model_fields
    assert "numero_revision" not in LiquidacionPatchVisitasGeneralIn.model_fields
