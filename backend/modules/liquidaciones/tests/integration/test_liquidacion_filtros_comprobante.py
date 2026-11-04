"""
Integration tests for the ACTIVE-RECEIPT (comprobante vigente) filters and the
entity-document filter on the liquidacion listings.

"Comprobante vigente" = a `LiquidacionComprobante` row with `activo=True` for
that liquidacion (at most one, enforced by the partial unique constraint
`unique_liquidacion_comprobante_activo`). Replaced receipts stay in the
history with `activo=False` and must NEVER match the filter.

The filter is implemented with `Exists` (not a JOIN) so a liquidacion with
several receipts is NOT duplicated in `items` and `total` stays truthful.

Covers:
- serie / numero filters match the ACTIVE receipt only
- a liquidation with an active + a replaced receipt appears exactly once
- the entity-document filter still applies
- the six type controllers accept the new filters
- `creado_por` / `numero_revisiones` are still accepted (no breaking change)
"""
from datetime import date
from decimal import Decimal

import pytest

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
    LiquidacionComprobante,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)

# ── Endpoints de listado por tipo ─────────────────────────────────────────────

ENDPOINTS_POR_TIPO = [
    "/liquidaciones/edificaciones/",
    "/liquidaciones/habilitacion-urbana/",
    "/liquidaciones/impacto-vial/",
    "/liquidaciones/inspeccion-obra/",
    "/liquidaciones/mecanica-suelos/",
    "/liquidaciones/taludes/",
]


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def liquidacion_con_comprobantes(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidad_estructuras,
    tipo_edificacion,
):
    """
    LiquidacionGeneral de Edificaciones con DOS comprobantes:
    - F001 / 000123 → ACTIVO (el vigente)
    - F002 / 000456 → histórico (reemplazado, activo=False)
    """
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=create_user,
        expediente="EXP-COMP-2026-001",
        observacion="Liquidacion con comprobante vigente y historico",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )

    # Comprobante histórico (reemplazado): NO es el vigente.
    LiquidacionComprobante.objects.create(
        liquidacion_general=lg,
        tipo_comprobante="FACTURA",
        serie="F002",
        numero="000456",
        fecha_emision=date(2026, 8, 10),
        monto=Decimal("1180.00"),
        activo=False,
        motivo_reemplazo="Corrección de datos del proveedor",
    )

    # Comprobante vigente.
    LiquidacionComprobante.objects.create(
        liquidacion_general=lg,
        tipo_comprobante="FACTURA",
        serie="F001",
        numero="000123",
        fecha_emision=date(2026, 9, 20),
        monto=Decimal("1180.00"),
        activo=True,
    )

    return lg


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_list_filtra_por_serie_del_comprobante_vigente(
    auth_client,
    liquidacion_con_comprobantes,
):
    """
    GIVEN: una liquidación con un comprobante vigente (F001) y uno histórico (F002)
    WHEN: se filtra por la serie del comprobante vigente
    THEN: la liquidación aparece; la serie del comprobante histórico no la devuelve.
    """
    vigente = auth_client.get(
        "/liquidaciones/edificaciones/?comprobante_serie=F001"
    )
    assert vigente.status_code == 200
    assert vigente.json()["data"]["total"] == 1

    historico = auth_client.get(
        "/liquidaciones/edificaciones/?comprobante_serie=F002"
    )
    assert historico.status_code == 200
    assert historico.json()["data"]["total"] == 0


@pytest.mark.django_db
def test_list_filtra_por_numero_del_comprobante_vigente(
    auth_client,
    liquidacion_con_comprobantes,
):
    """
    El filtro por número del comprobante también resuelve contra el ACTIVO.
    """
    vigente = auth_client.get(
        "/liquidaciones/edificaciones/?comprobante_numero=000123"
    )
    assert vigente.status_code == 200
    assert vigente.json()["data"]["total"] == 1

    historico = auth_client.get(
        "/liquidaciones/edificaciones/?comprobante_numero=000456"
    )
    assert historico.status_code == 200
    assert historico.json()["data"]["total"] == 0


@pytest.mark.django_db
def test_list_no_duplica_las_liquidaciones_con_historial_de_comprobantes(
    auth_client,
    liquidacion_con_comprobantes,
):
    """
    GIVEN: una liquidación con 2 comprobantes (1 vigente + 1 histórico)
    WHEN: se lista con el filtro de comprobante vigente
    THEN: la liquidación aparece UNA sola vez y `total` no se infla.
    """
    response = auth_client.get(
        "/liquidaciones/edificaciones/?comprobante_serie=F001&page_size=50"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert len(data["items"]) == 1


@pytest.mark.django_db
def test_list_filtra_por_documento_de_entidad(
    auth_client,
    liquidacion_con_comprobantes,
):
    """
    El filtro por N.º de documento de la entidad sigue funcionando y es
    combinable con el de comprobante vigente.
    """
    response = auth_client.get(
        "/liquidaciones/edificaciones/?documento=20456789012&comprobante_serie=F001"
    )
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1

    sin_match = auth_client.get(
        "/liquidaciones/edificaciones/?documento=00000000&comprobante_serie=F001"
    )
    assert sin_match.status_code == 200
    assert sin_match.json()["data"]["total"] == 0


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", ENDPOINTS_POR_TIPO)
def test_los_seis_endpoints_aceptan_los_filtros_nuevos(auth_client, endpoint):
    """
    Los 6 controllers por tipo aceptan `comprobante_serie`, `comprobante_numero`
    y `documento` sin error (contrato de API estable para los 6 tipos).
    """
    response = auth_client.get(
        f"{endpoint}?comprobante_serie=F001&comprobante_numero=000123&documento=20456789012"
    )

    assert response.status_code == 200, response.content
    assert "total" in response.json()["data"]


@pytest.mark.django_db
def test_creado_por_y_numero_revisiones_siguen_siendo_aceptados(
    auth_client,
    liquidacion_con_comprobantes,
):
    """
    Retirar los controles del frontend NO rompe el contrato de API: los 6
    controllers siguen aceptando `creado_por` y `numero_revisiones`.
    """
    # Los dos params se aceptan (sin error de validación).
    ambos = auth_client.get(
        "/liquidaciones/edificaciones/?creado_por=__no_existe__&numero_revisiones=1"
    )
    assert ambos.status_code == 200, ambos.content

    # `numero_revisiones` sigue filtrando (la liquidación es de revisión 1).
    solo_revisiones = auth_client.get(
        "/liquidaciones/edificaciones/?numero_revisiones=1"
    )
    assert solo_revisiones.status_code == 200
    assert solo_revisiones.json()["data"]["total"] == 1

    # `creado_por` sigue filtrando (nadie coincide con ese username).
    solo_creador = auth_client.get(
        "/liquidaciones/edificaciones/?creado_por=__no_existe__"
    )
    assert solo_creador.status_code == 200
    assert solo_creador.json()["data"]["total"] == 0
