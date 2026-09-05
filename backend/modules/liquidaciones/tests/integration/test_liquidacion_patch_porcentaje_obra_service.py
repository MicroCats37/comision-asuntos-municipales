"""
Integration tests for LiquidacionPatchPorcentajeObraService — PATCH recalculation for PO motor.

Tests cover:
1. Updates valor_declarado and totals
2. Replaces detail rows when tariffs change
3. Preserves current values when patch fields are omitted
4. Uses historical tariffs/IGV/UIT/derecho (resolved by fecha_registro)
5. Raises clear errors when historical records are missing (no silent fallback)

Scope: Service only — no HTTP, no controller.
"""
import pytest
from decimal import Decimal
from datetime import date, datetime, timezone

from django.utils import timezone as dj_timezone

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    DerechoPorcentajeObra,
)
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
from modules.liquidaciones.domain.constants import TipoLiquidacion, EstadoLiquidacion
from modules.liquidaciones.domain.services.core.liquidacion_patch_porcentaje_obra_service import (
    LiquidacionPatchPorcentajeObraService,
    PatchPorcentajeObraInput,
    TarifaPatchInput,
    LiquidacionNoEncontradaError,
)
from modules.liquidaciones.domain.services.core.liquidacion_patch_historico_core_service import (
    NoIGVVigenteError,
    NoUITVigenteError,
    NoTarifaVigenteError,
    NoDerechoVigenteError,
)
from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.entidades.domain.models.ubigeo import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.liquidaciones.domain.models.proyecto import Proyecto
from django.contrib.auth import get_user_model

User = get_user_model()


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def svc():
    return LiquidacionPatchPorcentajeObraService()


# Historical (closed) IGV from 2024
@pytest.fixture
def igv_2024(db):
    return IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


# Current (open) IGV from 2026
@pytest.fixture
def igv_2026(db):
    return IGV.objects.create(
        valor=Decimal("0.19"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )


# Historical UIT from 2024
@pytest.fixture
def uit_2024(db):
    return UIT.objects.create(
        valor=4700,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


# Current UIT from 2026
@pytest.fixture
def uit_2026(db):
    return UIT.objects.create(
        valor=5300,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )


# Historical derecho from 2024
@pytest.fixture
def derecho_po_2024(db):
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("400.00"),
        derecho_maximo=Decimal("40000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


# Current derecho from 2026
@pytest.fixture
def derecho_po_2026(db):
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )


# Historical TarifaLiquidacionBase (2024, closed)
@pytest.fixture
def tarifa_base_2024(db, tipo_edificacion):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


# Current TarifaLiquidacionBase (2026, open)
@pytest.fixture
def tarifa_base_2026(db, tipo_edificacion):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )


# PO tariff at 0.10% tied to 2024 base
@pytest.fixture
def tarifa_po_10bps(db, tarifa_base_2024):
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_2024,
        porcentaje_liquidacion=Decimal("0.0010"),
    )


# PO tariff at 0.05% tied to 2024 base (for two-tariff tests)
@pytest.fixture
def tarifa_po_5bps(db, tarifa_base_2024):
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_2024,
        porcentaje_liquidacion=Decimal("0.0005"),
    )


# Current PO tariff at 0.12% tied to 2026 base
@pytest.fixture
def tarifa_po_12bps(db, tarifa_base_2026):
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_2026,
        porcentaje_liquidacion=Decimal("0.0012"),
    )


# Current PO tariff at 0.06% tied to 2026 base
@pytest.fixture
def tarifa_po_6bps(db, tarifa_base_2026):
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_2026,
        porcentaje_liquidacion=Decimal("0.0006"),
    )


# Especialidades
@pytest.fixture
def esp_estructuras(db):
    return EspecialidadRevision.objects.create(slug="estructuras", nombre="Estructuras")


@pytest.fixture
def esp_arquitectura(db):
    return EspecialidadRevision.objects.create(slug="arquitectura", nombre="Arquitectura")


# Ubigeo chain
@pytest.fixture
def dept(db):
    return UbigeoDepartamento.objects.create(nombre="LIMA")


@pytest.fixture
def prov(db, dept):
    return UbigeoProvincia.objects.create(departamento=dept, nombre="LIMA")


@pytest.fixture
def distrito(db, prov):
    return UbigeoDistrito.objects.create(provincia=prov, nombre="MIRAFLORES", ubigeo="150132")


@pytest.fixture
def municipalidad(db, distrito):
    return Municipalidad.objects.create(distrito=distrito, nombre="Municipalidad de Lima", codigo="MUN001")


@pytest.fixture
def proyecto(db, municipalidad, distrito):
    from modules.entidades.domain.models import Entidad
    entidad = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento="20456789012",
    )
    return Proyecto.objects.create(
        entidad=entidad,
        denominacion="Edificio Test",
        nombre_propietario="Propietario Test",
        direccion="Av. Test 123",
        distrito=distrito,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789012",
        entidad_razon_social="Propietario Test",
    )


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass123", dni="12345678")


# Composite fixture: a PO liquidacion registered in 2024 with 2024 historical records
@pytest.fixture
def liq_po_2024(
    db, proyecto, municipalidad, user, igv_2024, uit_2024,
    derecho_po_2024, tarifa_base_2024, tarifa_po_10bps, esp_estructuras, tipo_edificacion,
):
    """
    A LiquidacionGeneral + LiquidacionPorcentajeObra created in 2024
    using 2024-era financial variables (IGV 18%, UIT 4700, 10bps tariff).

    fecha_registro is set to Jun 2024 to simulate a historical record.
    """
    fecha_2024 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-PO-2024-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_2024,
        uit_id=uit_2024,
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("4700"),
        fecha_registro=fecha_2024,
    )

    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("470.00"),
        derecho_maximo=Decimal("40000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_po_2024,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_po_10bps,
        especialidad=esp_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )

    return {"lg": lg, "lpo": lpo}


# ── Tests ────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_recalcular_updates_valor_declarado_and_totals(svc, liq_po_2024):
    """
    GIVEN: PO liquidacion with valor_declarado=100000, subtotal=1000, total=1180
           derecho_minimo=470.00 (uit=4700 * 0.10), 10bps tariff
    WHEN:  recalcular is called with valor_declarado=200000
    THEN:  valor_declarado updated to 200000,
           subtotal recalculated — BUT derecho_minimo floor applies:
           200000 * 0.0010 = 200 < minimo(470) → subtotal=470.00,
           igv = 470 * 0.18 = 84.60, total = 554.60
    """
    lg = liq_po_2024["lg"]
    lpo = liq_po_2024["lpo"]

    patch = PatchPorcentajeObraInput(valor_declarado=Decimal("200000.00"), tarifas=None)

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    lpo.refresh_from_db()

    assert lpo.valor_declarado == Decimal("200000.00")
    assert lg.sub_total == Decimal("470.00")
    assert lg.total == Decimal("554.60")


@pytest.mark.django_db
def test_recalcular_replaces_detail_rows_when_tariffs_change(svc, liq_po_2024, tarifa_po_5bps, esp_arquitectura):
    """
    GIVEN: PO liquidacion with 1 detail (estructuras only)
    WHEN:  recalcular is called with an explicit 2-tariff list (estructuras + arquitectura)
    THEN:  old detail deleted, 2 new details created
    """
    lg = liq_po_2024["lg"]
    lpo = liq_po_2024["lpo"]
    esp_estructuras = lpo.detalles.first().especialidad

    assert lpo.detalles.count() == 1

    patch = PatchPorcentajeObraInput(
        valor_declarado=Decimal("100000.00"),
        tarifas=[
            TarifaPatchInput(tarifa_id=str(tarifa_po_5bps.id), especialidad_id=str(esp_estructuras.id)),
            TarifaPatchInput(tarifa_id=str(tarifa_po_5bps.id), especialidad_id=str(esp_arquitectura.id)),
        ],
    )

    svc.recalcular(lg, patch)

    lpo.refresh_from_db()
    assert lpo.detalles.count() == 2


@pytest.mark.django_db
def test_recalcular_preserves_valor_declarado_when_omitted(svc, liq_po_2024):
    """
    GIVEN: PO liquidacion with valor_declarado=100000, derecho_minimo=470 (uit*0.10)
    WHEN:  recalcular is called with valor_declarado=None
    THEN:  valor_declarado stays 100000, BUT derecho_minimo floor applies:
           calculated=100 (100000*0.0010) < minimo(470) → sub_total=470.00
    """
    lg = liq_po_2024["lg"]

    patch = PatchPorcentajeObraInput(valor_declarado=None, tarifas=None)

    svc.recalcular(lg, patch)

    lpo = lg.liquidacion_porcentaje_obra
    lpo.refresh_from_db()
    assert lpo.valor_declarado == Decimal("100000.00")
    # derecho_minimo floor applies: max(100, 470) = 470
    assert lg.sub_total == Decimal("470.00")
    assert lg.total == Decimal("554.60")  # 470 * 1.18


@pytest.mark.django_db
def test_recalcular_preserves_tariffs_when_omitted(svc, liq_po_2024):
    """
    GIVEN: PO liquidacion with 1 detail (estructuras, 0.10%)
    WHEN:  recalcular is called with valor_declarado=150000 but tarifas=None
    THEN:  specialty and percentage preserved, derecho_minimo floor applies:
           calculated=150 (150000*0.0010) < minimo(470) → sub_total=470.00
    """
    lg = liq_po_2024["lg"]
    lpo = lg.liquidacion_porcentaje_obra
    original_detail = lpo.detalles.first()
    original_esp_id = original_detail.especialidad_id
    original_pct = original_detail.porcentaje_aplicado

    patch = PatchPorcentajeObraInput(valor_declarado=Decimal("150000.00"), tarifas=None)

    svc.recalcular(lg, patch)

    lpo.refresh_from_db()
    assert lpo.detalles.count() == 1
    # Detail is recreated (delete+recreate), so check specialty/percentage preserved
    assert lpo.detalles.first().especialidad_id == original_esp_id
    assert lpo.detalles.first().porcentaje_aplicado == original_pct
    assert lpo.valor_declarado == Decimal("150000.00")
    # derecho_minimo floor: max(150, 470) = 470
    assert lg.sub_total == Decimal("470.00")


@pytest.mark.django_db
def test_recalcular_uses_historical_tariffs_not_current(
    svc, db, proyecto, municipalidad, user, igv_2024, uit_2024,
    derecho_po_2024, tarifa_base_2024, tarifa_po_10bps,
    igv_2026, uit_2026, derecho_po_2026,
    tarifa_base_2026, tarifa_po_12bps, esp_estructuras, tipo_edificacion,
):
    """
    GIVEN: liquidacion registered in 2024 with 0.10% tariff AND
           2026 records exist with different 0.12% tariff
    WHEN:  recalcular is called with only valor_declarado changed
    THEN:  uses 2024 historical tariff (0.10%), not 2026 tariff (0.12%)
           — proves historical resolution, not current vigente
    """
    fecha_2024 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto, municipalidad=municipalidad, usuario_creador=user,
        expediente="EXP-HIST-001", estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion, numero_revision=1,
        sub_total=Decimal("100.00"), total=Decimal("118.00"),
        igv_id=igv_2024, uit_id=uit_2024,
        igv_snapshot=Decimal("0.18"), uit_snapshot=Decimal("4700"),
        fecha_registro=fecha_2024,
    )

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg, tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("470.00"), derecho_maximo=Decimal("40000.00"),
        porcentaje_minimo_uit=Decimal("0.10"), derecho_aplicado=derecho_po_2024,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo, tarifa_aplicada=tarifa_po_10bps,
        especialidad=esp_estructuras, porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("100.00"),
    )

    patch = PatchPorcentajeObraInput(valor_declarado=Decimal("200000.00"), tarifas=None)

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    lpo.refresh_from_db()

    # 0.10% of 200000 = 200.00 BUT derecho_minimo floor applies:
    # calculated=200 < minimo(470) → sub_total=470.00, total=554.60
    # Uses 2024 tariff (0.10%, stored in detail) not 2026 tariff (0.12%)
    assert lpo.porcentaje_liquidacion == Decimal("0.0010")
    assert lg.sub_total == Decimal("470.00")
    assert lg.total == Decimal("554.60")  # 470 * 1.18
    # Uses 2024 derecho, not 2026
    assert lpo.derecho_aplicado_id == derecho_po_2024.id


@pytest.mark.django_db
def test_recalcular_raises_when_no_historical_igv(
    svc, db, proyecto, municipalidad, user, uit_2024, derecho_po_2024,
    tarifa_base_2024, tarifa_po_10bps, esp_estructuras, igv_2026, tipo_edificacion,
):
    """
    GIVEN: only 2026 IGV exists (no IGV covering 2024)
    WHEN:  recalcular is called on a 2024 liquidacion
    THEN:  raises NoIGVVigenteError (not silent fallback to current)
    """
    fecha_2024 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto, municipalidad=municipalidad, usuario_creador=user,
        expediente="EXP-NO-IGV", estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion, numero_revision=1,
        sub_total=Decimal("100.00"), total=Decimal("118.00"),
        igv_id=igv_2026, uit_id=uit_2024,
        igv_snapshot=Decimal("0.19"), uit_snapshot=Decimal("4700"),
        fecha_registro=fecha_2024,
    )

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg, tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("470.00"), derecho_maximo=Decimal("40000.00"),
        porcentaje_minimo_uit=Decimal("0.10"), derecho_aplicado=derecho_po_2024,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo, tarifa_aplicada=tarifa_po_10bps,
        especialidad=esp_estructuras, porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("100.00"),
    )

    with pytest.raises(NoIGVVigenteError) as exc_info:
        svc.recalcular(lg, PatchPorcentajeObraInput(valor_declarado=Decimal("200000.00"), tarifas=None))

    assert "No existe IGV vigente" in str(exc_info.value.message)
    assert "2024-06-15" in str(exc_info.value.message)


@pytest.mark.django_db
def test_recalcular_raises_when_no_historical_derecho(
    svc, db, proyecto, municipalidad, user, igv_2024, uit_2024,
    tarifa_base_2024, tarifa_po_10bps, esp_estructuras, derecho_po_2026, tipo_edificacion,
):
    """
    GIVEN: only 2026 DerechoPorcentajeObra exists (no derecho covering 2024)
    WHEN:  recalcular is called on a 2024 liquidacion
    THEN:  raises NoDerechoVigenteError
    """
    fecha_2024 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto, municipalidad=municipalidad, usuario_creador=user,
        expediente="EXP-NO-DER", estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion, numero_revision=1,
        sub_total=Decimal("100.00"), total=Decimal("118.00"),
        igv_id=igv_2024, uit_id=uit_2024,
        igv_snapshot=Decimal("0.18"), uit_snapshot=Decimal("4700"),
        fecha_registro=fecha_2024,
    )

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg, tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("470.00"), derecho_maximo=Decimal("40000.00"),
        porcentaje_minimo_uit=Decimal("0.10"), derecho_aplicado=derecho_po_2026,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo, tarifa_aplicada=tarifa_po_10bps,
        especialidad=esp_estructuras, porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("100.00"),
    )

    with pytest.raises(NoDerechoVigenteError) as exc_info:
        svc.recalcular(lg, PatchPorcentajeObraInput(valor_declarado=Decimal("200000.00"), tarifas=None))

    assert "No existe derecho" in str(exc_info.value.message)


@pytest.mark.django_db
def test_recalcular_raises_when_no_historical_tarifa(
    svc, db, proyecto, municipalidad, user, igv_2024, uit_2024,
    derecho_po_2024, igv_2026, uit_2026, derecho_po_2026,
    tarifa_base_2026, tarifa_po_12bps, esp_estructuras, tipo_edificacion,
):
    """
    GIVEN: only 2026 TarifaLiquidacionBase exists (no base covering 2024)
    WHEN:  recalcular is called with explicit 2026 tariff on a 2024 liquidacion
    THEN:  raises NoTarifaVigenteError
    """
    fecha_2024 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto, municipalidad=municipalidad, usuario_creador=user,
        expediente="EXP-NO-TAR", estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion, numero_revision=1,
        sub_total=Decimal("100.00"), total=Decimal("118.00"),
        igv_id=igv_2024, uit_id=uit_2024,
        igv_snapshot=Decimal("0.18"), uit_snapshot=Decimal("4700"),
        fecha_registro=fecha_2024,
    )

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg, tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("470.00"), derecho_maximo=Decimal("40000.00"),
        porcentaje_minimo_uit=Decimal("0.10"), derecho_aplicado=derecho_po_2024,
    )

    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo, tarifa_aplicada=tarifa_po_12bps,
        especialidad=esp_estructuras, porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("100.00"),
    )

    with pytest.raises(NoTarifaVigenteError) as exc_info:
        svc.recalcular(lg, PatchPorcentajeObraInput(
            valor_declarado=Decimal("200000.00"),
            tarifas=[TarifaPatchInput(tarifa_id=str(tarifa_po_12bps.id), especialidad_id=str(esp_estructuras.id))],
        ))

    assert "No existe tarifa base vigente" in str(exc_info.value.message)


@pytest.mark.django_db
def test_recalcular_updates_lg_totals_and_snapshots(svc, liq_po_2024):
    """
    GIVEN: a PO liquidacion
    WHEN:  recalcular changes valor_declarado
    THEN:  LiquidacionGeneral.sub_total, .total are updated correctly
           AND igv_snapshot, uit_snapshot are updated to 2024 values
    """
    lg = liq_po_2024["lg"]

    patch = PatchPorcentajeObraInput(valor_declarado=Decimal("50000.00"), tarifas=None)
    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    lpo = lg.liquidacion_porcentaje_obra

    # 50000 * 0.0010 = 50.00 BUT derecho_minimo floor applies:
    # calculated=50 < minimo(470) → sub_total=470.00, total=554.60
    assert lg.sub_total == Decimal("470.00")
    assert lg.total == Decimal("554.60")  # 470 * 1.18
    # Snapshots updated to 2024 values
    assert lg.igv_snapshot == Decimal("0.18")
    assert lg.uit_snapshot == Decimal("4700")


@pytest.mark.django_db
def test_recalcular_raises_when_liquidacion_has_no_po_record(
    svc, db, proyecto, municipalidad, user, igv_2024, uit_2024, tipo_edificacion,
):
    """
    GIVEN: a LiquidacionGeneral with no LiquidacionPorcentajeObra
    WHEN:  recalcular is called
    THEN:  raises LiquidacionNoEncontradaError
    """
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto, municipalidad=municipalidad, usuario_creador=user,
        expediente="EXP-NO-PO", estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion, numero_revision=1,
        sub_total=Decimal("0.00"), total=Decimal("0.00"),
        igv_id=igv_2024, uit_id=uit_2024,
        fecha_registro=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(LiquidacionNoEncontradaError) as exc_info:
        svc.recalcular(lg, PatchPorcentajeObraInput(valor_declarado=Decimal("100000.00"), tarifas=None))

    assert "no tiene un registro LiquidacionPorcentajeObra" in str(exc_info.value.message)


@pytest.mark.django_db
def test_recalcular_raises_when_empty_tarifas_list(svc, liq_po_2024):
    """
    GIVEN: a PO liquidacion with existing details
    WHEN:  recalcular is called with tarifas=[] (empty list, not None)
    THEN:  raises BusinessError (PO requires at least 1 tariff)
    """
    lg = liq_po_2024["lg"]

    patch = PatchPorcentajeObraInput(valor_declarado=Decimal("100000.00"), tarifas=[])

    with pytest.raises(Exception) as exc_info:  # noqa: B017
        svc.recalcular(lg, patch)

    assert "al menos una tarifa" in str(exc_info.value.message)
