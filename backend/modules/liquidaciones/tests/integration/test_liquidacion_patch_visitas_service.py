"""
Integration tests for LiquidacionPatchVisitasService — PATCH recalculation for Visitas motor.

Tests cover:
1. Updates cantidad_visitas and totals
2. Changes categoria/tarifa and updates tarifa/porcentaje/totals
3. Preserves omitted values when cantidad_visitas, categoria, or tarifa_visitas_id is None
4. Uses historical tarifa/IGV/UIT by fecha_registro, not current vigentes
5. Fails clearly when historical tariff not vigente at fecha_registro (no silent fallback)
6. Fails clearly when categoria changed but no matching tariff for that categoria at fecha_registro

Scope: Service only — no HTTP, no controller.
"""
import pytest
from decimal import Decimal
from datetime import date, datetime, timezone

from django.utils import timezone as dj_timezone

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion, EstadoLiquidacion
from modules.liquidaciones.domain.services.core.liquidacion_patch_visitas_service import (
    LiquidacionPatchVisitasService,
    PatchVisitasInput,
    LiquidacionVisitasNoEncontradaError,
    NoTarifaVisitasError,
)
from modules.liquidaciones.domain.services.core.liquidacion_patch_historico_core_service import (
    NoTarifaVigenteError,
    NoIGVVigenteError,
    NoUITVigenteError,
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
    return LiquidacionPatchVisitasService()


# Historical IGV from 2024 (IGV applies to Visitas unlike M2)
@pytest.fixture
def igv_2024(db):
    return IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


# Current IGV from 2026
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


# Historical TarifaLiquidacionBase for IO (2024, closed)
@pytest.fixture
def tarifa_base_io_2024(db, tipo_inspeccion_obra):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_inspeccion_obra,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


# Current TarifaLiquidacionBase for IO (2026, open)
@pytest.fixture
def tarifa_base_io_2026(db, tipo_inspeccion_obra):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_inspeccion_obra,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )


# TarifaPorCategoriaVisitas at 5% UIT for categoria "INSPECCION", tied to 2024 base
@pytest.fixture
def tarifa_visitas_inspeccion_2024(db, tarifa_base_io_2024):
    return TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=tarifa_base_io_2024,
        porcentaje_uit=Decimal("0.05"),
        categoria_visitas="INSPECCION",
    )


# Second 2024 TarifaLiquidacionBase for IO (to hold a second tariff without UNIQUE constraint conflict)
@pytest.fixture
def tarifa_base_io_2024_alt(db, tipo_inspeccion_obra):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_inspeccion_obra,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


# TarifaPorCategoriaVisitas at 8% UIT for categoria "C2", tied to 2024 base ALT
@pytest.fixture
def tarifa_visitas_c2_2024(db, tarifa_base_io_2024_alt):
    return TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=tarifa_base_io_2024_alt,
        porcentaje_uit=Decimal("0.08"),
        categoria_visitas="C2",
    )


# TarifaPorCategoriaVisitas at 10% UIT for categoria "C3", tied to 2026 base (current)
@pytest.fixture
def tarifa_visitas_c3_2026(db, tarifa_base_io_2026):
    return TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=tarifa_base_io_2026,
        porcentaje_uit=Decimal("0.10"),
        categoria_visitas="C3",
    )


# TarifaPorCategoriaVisitas at 7% UIT for categoria "C2", tied to 2026 base (current)
@pytest.fixture
def tarifa_visitas_c2_2026(db, tarifa_base_io_2026):
    return TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=tarifa_base_io_2026,
        porcentaje_uit=Decimal("0.07"),
        categoria_visitas="C2",
    )


# Ubigeo chain
@pytest.fixture
def dept(db):
    return UbigeoDepartamento.objects.create(nombre="Lima")


@pytest.fixture
def prov(db, dept):
    return UbigeoProvincia.objects.create(departamento=dept, nombre="Lima")


@pytest.fixture
def distrito(db, prov):
    return UbigeoDistrito.objects.create(provincia=prov, nombre="Miraflores", ubigeo="150132")


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


# Composite fixture: IO liquidacion registered in 2024 with 2024 historical records
# UIT=4700, IGV=0.18, tarifa INSPECCION 5% UIT
# subtotal = 3 * (0.05 * 4700) = 3 * 235 = 705
# total = 705 * 1.18 = 831.90
@pytest.fixture
def liq_io_2024(
    db,
    proyecto,
    municipalidad,
    user,
    igv_2024,
    uit_2024,
    tarifa_base_io_2024,
    tarifa_visitas_inspeccion_2024,
    tipo_inspeccion_obra,
):
    """
    A LiquidacionGeneral + LiquidacionPorCategoriaVisitas for IO created in 2024
    using 2024-era financial variables (IGV=0.18, UIT=4700, tarifa 5% UIT).

    fecha_registro is Jun 2024. Current (2026) records exist with different values.
    """
    fecha_2024 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-IO-2024-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        sub_total=Decimal("705.00"),
        total=Decimal("831.90"),
        igv_id=igv_2024,
        uit_id=uit_2024,
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("4700"),
        fecha_registro=fecha_2024,
    )

    LiquidacionInspeccionObra.objects.create(liquidacion=lg, numero=1)

    liq_visitas = LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg,
        cantidad_visitas=3,
        porcentaje_uit=Decimal("0.0500"),
        categoria="INSPECCION",
        tarifa_aplicada=tarifa_visitas_inspeccion_2024,
    )

    return {"lg": lg, "liq_visitas": liq_visitas}


# ── Tests ────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_recalcular_updates_cantidad_visitas_and_totals(svc, liq_io_2024):
    """
    GIVEN: IO liquidacion with cantidad=3, categoria=INSPECCION, tarifa 5% UIT,
           UIT=4700, IGV=0.18
           subtotal=705, total=831.90
    WHEN:  recalcular is called with cantidad_visitas=5
    THEN:  cantidad_visitas updated to 5,
           subtotal = 5 * (0.05 * 4700) = 5 * 235 = 1175
           total = 1175 * 1.18 = 1386.50
    """
    lg = liq_io_2024["lg"]
    liq_visitas = liq_io_2024["liq_visitas"]

    patch = PatchVisitasInput(cantidad_visitas=5, categoria=None, tarifa_visitas_id=None)

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    liq_visitas.refresh_from_db()

    assert liq_visitas.cantidad_visitas == 5
    assert liq_visitas.categoria == "INSPECCION"
    assert float(liq_visitas.porcentaje_uit) == 0.05
    # subtotal = 5 * 235 = 1175; total = 1175 * 1.18 = 1386.50
    assert lg.sub_total == Decimal("1175.00")
    assert lg.total == Decimal("1386.50")
    # Snapshots updated to historical values
    assert lg.igv_snapshot == Decimal("0.18")
    assert lg.uit_snapshot == Decimal("4700")


@pytest.mark.django_db
def test_recalcular_changes_categoria_and_updates_tarifa_porcentaje_totals(
    svc, liq_io_2024, tarifa_visitas_c2_2024
):
    """
    GIVEN: IO liquidacion with categoria=INSPECCION (5% UIT)
    WHEN:  recalcular is called with categoria="C2" (no explicit tarifa_id)
    THEN:  looks up tariff for C2 at 2024 fecha, finds 8% UIT
           categoria updated to C2, porcentaje_uit updated to 0.08
           subtotal = 3 * (0.08 * 4700) = 3 * 376 = 1128
           total = 1128 * 1.18 = 1331.04
    """
    lg = liq_io_2024["lg"]
    liq_visitas = liq_io_2024["liq_visitas"]

    patch = PatchVisitasInput(cantidad_visitas=None, categoria="C2", tarifa_visitas_id=None)

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    liq_visitas.refresh_from_db()

    assert liq_visitas.categoria == "C2"
    assert float(liq_visitas.porcentaje_uit) == 0.08
    assert liq_visitas.tarifa_aplicada_id == tarifa_visitas_c2_2024.id
    assert liq_visitas.cantidad_visitas == 3  # preserved
    # subtotal = 3 * (0.08 * 4700) = 3 * 376 = 1128
    assert lg.sub_total == Decimal("1128.00")
    assert lg.total == Decimal("1331.04")


@pytest.mark.django_db
def test_recalcular_changes_tarifa_explicit_id_and_updates_porcentaje_totals(
    svc, liq_io_2024, tarifa_visitas_c2_2024
):
    """
    GIVEN: IO liquidacion with categoria=INSPECCION (5% UIT)
    WHEN:  recalcular is called with explicit tarifa_visitas_id for C2 8% tariff
    THEN:  categoria updated to C2 (from tariff's categoria_visitas)
           porcentaje_uit updated to 0.08
           subtotal = 3 * (0.08 * 4700) = 1128
           total = 1128 * 1.18 = 1331.04
    """
    lg = liq_io_2024["lg"]
    liq_visitas = liq_io_2024["liq_visitas"]

    patch = PatchVisitasInput(
        cantidad_visitas=None, categoria=None, tarifa_visitas_id=str(tarifa_visitas_c2_2024.id)
    )

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    liq_visitas.refresh_from_db()

    assert liq_visitas.categoria == "C2"  # from tariff's categoria_visitas
    assert float(liq_visitas.porcentaje_uit) == 0.08
    assert liq_visitas.tarifa_aplicada_id == tarifa_visitas_c2_2024.id
    assert lg.sub_total == Decimal("1128.00")
    assert lg.total == Decimal("1331.04")


@pytest.mark.django_db
def test_recalcular_preserves_omitted_values(svc, liq_io_2024):
    """
    GIVEN: IO liquidacion with cantidad=3, categoria=INSPECCION, tarifa 5% UIT
           subtotal=705, total=831.90
    WHEN:  recalcular is called with all None inputs (no patch data)
    THEN:  all values preserved, totals recalculated with same values
           (result is the same since nothing changed)
    """
    lg = liq_io_2024["lg"]
    liq_visitas = liq_io_2024["liq_visitas"]

    patch = PatchVisitasInput(cantidad_visitas=None, categoria=None, tarifa_visitas_id=None)

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    liq_visitas.refresh_from_db()

    assert liq_visitas.cantidad_visitas == 3
    assert liq_visitas.categoria == "INSPECCION"
    assert float(liq_visitas.porcentaje_uit) == 0.05
    # Totals unchanged (same inputs)
    assert lg.sub_total == Decimal("705.00")
    assert lg.total == Decimal("831.90")


@pytest.mark.django_db
def test_recalcular_uses_historical_tarifa_igv_uit_by_fecha_registro(
    svc, db, proyecto, municipalidad, user,
    igv_2024, uit_2024, tarifa_base_io_2024, tarifa_visitas_inspeccion_2024,
    igv_2026, uit_2026, tarifa_base_io_2026, tarifa_visitas_c2_2026,
    tipo_inspeccion_obra,
):
    """
    GIVEN: liquidacion registered in 2024 with IGV=0.18, UIT=4700, 5% UIT tariff
           AND 2026 records exist with IGV=0.19, UIT=5300, 7% C2 tariff
    WHEN:  recalcular is called with cantidad_visitas=4
    THEN:  uses 2024 IGV (0.18), 2024 UIT (4700), 2024 tariff (5%)
           NOT current 2026 values
           subtotal = 4 * (0.05 * 4700) = 4 * 235 = 940
           total = 940 * 1.18 = 1109.20
    """
    fecha_2024 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-IO-HIST-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        sub_total=Decimal("705.00"),
        total=Decimal("831.90"),
        igv_id=igv_2024,
        uit_id=uit_2024,
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("4700"),
        fecha_registro=fecha_2024,
    )

    LiquidacionInspeccionObra.objects.create(liquidacion=lg, numero=1)

    liq_visitas = LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg,
        cantidad_visitas=3,
        porcentaje_uit=Decimal("0.0500"),
        categoria="INSPECCION",
        tarifa_aplicada=tarifa_visitas_inspeccion_2024,
    )

    patch = PatchVisitasInput(cantidad_visitas=4, categoria=None, tarifa_visitas_id=None)

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    liq_visitas.refresh_from_db()

    # Uses 2024 values (historical), not 2026 current values
    assert lg.igv_snapshot == Decimal("0.18")  # 2024 IGV, not 2026's 0.19
    assert lg.uit_snapshot == Decimal("4700")  # 2024 UIT, not 2026's 5300
    assert liq_visitas.porcentaje_uit == Decimal("0.0500")  # 2024 tariff's %, not 2026's
    # subtotal = 4 * (0.05 * 4700) = 4 * 235 = 940
    assert lg.sub_total == Decimal("940.00")
    # total = 940 * 1.18 = 1109.20
    assert lg.total == Decimal("1109.20")


@pytest.mark.django_db
def test_recalcular_raises_when_explicit_tarifa_not_vigente_at_fecha(
    svc, db, proyecto, municipalidad, user,
    igv_2024, uit_2024, tarifa_base_io_2024, tarifa_visitas_inspeccion_2024,
    igv_2026, uit_2026, tarifa_base_io_2026, tarifa_visitas_c2_2026,
    tipo_inspeccion_obra,
):
    """
    GIVEN: liquidacion registered in 2024; 2026 tariff (C3, 10% UIT) exists
    WHEN:  recalcular is called with an explicit 2026 tariff ID
           (not vigente at 2024 fecha_registro)
    THEN:  raises NoTarifaVigenteError (historical accuracy violation)
    """
    fecha_2024 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-IO-NO-TAR",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        sub_total=Decimal("705.00"),
        total=Decimal("831.90"),
        igv_id=igv_2024,
        uit_id=uit_2024,
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("4700"),
        fecha_registro=fecha_2024,
    )

    LiquidacionInspeccionObra.objects.create(liquidacion=lg, numero=1)

    LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg,
        cantidad_visitas=3,
        porcentaje_uit=Decimal("0.0500"),
        categoria="INSPECCION",
        tarifa_aplicada=tarifa_visitas_inspeccion_2024,
    )

    # Attempt to use 2026 tariff (not vigente at 2024 fecha_registro)
    patch = PatchVisitasInput(
        cantidad_visitas=3, categoria=None, tarifa_visitas_id=str(tarifa_visitas_c2_2026.id)
    )

    with pytest.raises(NoTarifaVigenteError) as exc_info:
        svc.recalcular(lg, patch)

    assert "No existe tarifa base vigente" in str(exc_info.value.message)


@pytest.mark.django_db
def test_recalcular_raises_when_categoria_changed_but_no_matching_tariff(
    svc, db, proyecto, municipalidad, user,
    igv_2024, uit_2024, tarifa_base_io_2024, tarifa_visitas_inspeccion_2024,
    igv_2026, uit_2026, tarifa_base_io_2026,
    tipo_inspeccion_obra,
):
    """
    GIVEN: liquidacion registered in 2024; 2024 base exists only for INSPECCION categoria
           2026 base exists for C3 categoria but NOT 2024
    WHEN:  recalcular is called with categoria="C3" (no explicit tarifa)
           but C3 only has 2026 tariff (not vigente at 2024)
    THEN:  raises NoTarifaVisitasError (no tariff for C3 at 2024)
    """
    fecha_2024 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-IO-NO-CAT",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        sub_total=Decimal("705.00"),
        total=Decimal("831.90"),
        igv_id=igv_2024,
        uit_id=uit_2024,
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("4700"),
        fecha_registro=fecha_2024,
    )

    LiquidacionInspeccionObra.objects.create(liquidacion=lg, numero=1)

    LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg,
        cantidad_visitas=3,
        porcentaje_uit=Decimal("0.0500"),
        categoria="INSPECCION",
        tarifa_aplicada=tarifa_visitas_inspeccion_2024,
    )

    # Attempt to change to C3 — only 2026 tariff exists for C3 (not vigente at 2024)
    patch = PatchVisitasInput(cantidad_visitas=None, categoria="C3", tarifa_visitas_id=None)

    with pytest.raises(NoTarifaVisitasError) as exc_info:
        svc.recalcular(lg, patch)

    assert "No existe tarifa de visitas para la categoria" in str(exc_info.value.message)


@pytest.mark.django_db
def test_recalcular_raises_when_liquidacion_has_no_visitas_record(
    svc, db, proyecto, municipalidad, user, igv_2024, uit_2024, tipo_inspeccion_obra,
):
    """
    GIVEN: a LiquidacionGeneral with no LiquidacionPorCategoriaVisitas
    WHEN:  recalcular is called
    THEN:  raises LiquidacionVisitasNoEncontradaError
    """
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-IO-NO-VIS",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        sub_total=Decimal("0.00"),
        total=Decimal("0.00"),
        igv_id=igv_2024,
        uit_id=uit_2024,
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("4700"),
        fecha_registro=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
    )

    LiquidacionInspeccionObra.objects.create(liquidacion=lg, numero=1)

    with pytest.raises(LiquidacionVisitasNoEncontradaError) as exc_info:
        svc.recalcular(lg, PatchVisitasInput(cantidad_visitas=3, categoria=None, tarifa_visitas_id=None))

    assert "no tiene un registro LiquidacionPorCategoriaVisitas" in str(exc_info.value.message)


@pytest.mark.django_db
def test_recalcular_updates_lg_totals_and_snapshots_correctly(svc, liq_io_2024):
    """
    GIVEN: an IO liquidacion
    WHEN:  recalcular changes cantidad_visitas
    THEN:  LiquidacionGeneral.sub_total and .total updated correctly with IGV
           igv_snapshot and uit_snapshot updated to historical values
    """
    lg = liq_io_2024["lg"]
    liq_visitas = liq_io_2024["liq_visitas"]

    patch = PatchVisitasInput(cantidad_visitas=4, categoria=None, tarifa_visitas_id=None)
    svc.recalcular(lg, patch)

    lg.refresh_from_db()

    # 4 * (0.05 * 4700) = 940; total = 940 * 1.18 = 1109.20
    assert lg.sub_total == Decimal("940.00")
    assert lg.total == Decimal("1109.20")
    # Snapshots updated to 2024 values
    assert lg.igv_snapshot == Decimal("0.18")
    assert lg.uit_snapshot == Decimal("4700")


@pytest.mark.django_db
def test_recalcular_updates_visitas_row_fields_in_place(
    svc, liq_io_2024, tarifa_base_io_2024_alt, tarifa_visitas_c2_2024
):
    """
    GIVEN: an IO liquidacion with cantidad=3, categoria=INSPECCION, 5% UIT
    WHEN:  recalcular is called with cantidad=6 and categoria="C2"
           (and looks up corresponding tariff)
    THEN:  LiquidacionPorCategoriaVisitas row updated in-place:
           cantidad_visitas=6, categoria=C2, porcentaje_uit=0.08,
           tarifa_aplicada updated
    """
    lg = liq_io_2024["lg"]
    liq_visitas = liq_io_2024["liq_visitas"]

    patch = PatchVisitasInput(cantidad_visitas=6, categoria="C2", tarifa_visitas_id=None)
    svc.recalcular(lg, patch)

    liq_visitas.refresh_from_db()

    assert liq_visitas.cantidad_visitas == 6
    assert liq_visitas.categoria == "C2"
    assert float(liq_visitas.porcentaje_uit) == 0.08
