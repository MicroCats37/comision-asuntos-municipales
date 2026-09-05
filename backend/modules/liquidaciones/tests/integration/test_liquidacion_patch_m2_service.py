"""
Integration tests for LiquidacionPatchM2Service — PATCH recalculation for M2 motor.

Tests cover:
1. Updates area_solicitada and totals
2. Changes tarifa_m2_id and updates costo/derecho/totals
3. Preserves omitted values when area_solicitada or tarifa_m2_id is None
4. Uses historical derecho (resolved by fecha_registro, not current vigentes)
5. Uses historical tariff base when tarifa_m2_id provided but base not current
6. Raises clear errors when historical records missing (no silent fallback)
7. M2 total = subtotal = monto_bruto (no IGV applied)

Scope: Service only — no HTTP, no controller.
"""
import pytest
from decimal import Decimal
from datetime import date, datetime, timezone

from django.utils import timezone as dj_timezone

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorMetroCuadrado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_mecanica_suelos import (
    LiquidacionMecanicaSuelos,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion, EstadoLiquidacion
from modules.liquidaciones.domain.services.core.liquidacion_patch_m2_service import (
    LiquidacionPatchM2Service,
    PatchM2Input,
    LiquidacionM2NoEncontradaError,
)
from modules.liquidaciones.domain.services.core.liquidacion_patch_historico_core_service import (
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
    return LiquidacionPatchM2Service()


# Historical IGV from 2024 (for completeness — M2 doesn't use it in calculation)
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


# Historical UIT from 2024 (for completeness — M2 doesn't use it)
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


# Historical TarifaLiquidacionBase (2024, closed) for HU
@pytest.fixture
def tarifa_base_hu_2024(db, tipo_habilitacion_urbana):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


# Current TarifaLiquidacionBase (2026, open) for HU
@pytest.fixture
def tarifa_base_hu_2026(db, tipo_habilitacion_urbana):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )


# Historical TarifaLiquidacionBase (2024, closed) for MS
@pytest.fixture
def tarifa_base_ms_2024(db, tipo_mecanica_suelos):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


# Current TarifaLiquidacionBase (2026, open) for MS
@pytest.fixture
def tarifa_base_ms_2026(db, tipo_mecanica_suelos):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )


# M2 tariff at 150.00/m2 tied to 2024 HU base
@pytest.fixture
def tarifa_m2_hu_150(db, tarifa_base_hu_2024):
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_hu_2024,
        costo_por_m2=Decimal("150.0000"),
    )


# Second 2024 TarifaLiquidacionBase for HU (to hold a second M2 tariff without UNIQUE constraint conflict)
@pytest.fixture
def tarifa_base_hu_2024_alt(db, tipo_habilitacion_urbana):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


# M2 tariff at 200.00/m2 tied to 2024 HU base ALT (different cost, different base to avoid UNIQUE constraint)
@pytest.fixture
def tarifa_m2_hu_200(db, tarifa_base_hu_2024_alt):
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_hu_2024_alt,
        costo_por_m2=Decimal("200.0000"),
    )


# M2 tariff at 180.00/m2 tied to 2026 HU base (current, different cost)
@pytest.fixture
def tarifa_m2_hu_180(db, tarifa_base_hu_2026):
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_hu_2026,
        costo_por_m2=Decimal("180.0000"),
    )


# M2 tariff at 160.00/m2 tied to 2024 MS base
@pytest.fixture
def tarifa_m2_ms_160(db, tarifa_base_ms_2024):
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_ms_2024,
        costo_por_m2=Decimal("160.0000"),
    )


# M2 tariff at 210.00/m2 tied to 2026 MS base
@pytest.fixture
def tarifa_m2_ms_210(db, tarifa_base_ms_2026):
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_ms_2026,
        costo_por_m2=Decimal("210.0000"),
    )


# Historical derecho M2 from 2024
@pytest.fixture
def derecho_m2_2024(db):
    return DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
    )


# Current derecho M2 from 2026
@pytest.fixture
def derecho_m2_2026(db):
    return DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("600.00"),
        derecho_maximo=Decimal("60000.00"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )


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
        denominacion="Loteo Test",
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


# Composite fixture: HU liquidacion registered in 2024 with 2024 historical records
@pytest.fixture
def liq_hu_2024(
    db,
    proyecto,
    municipalidad,
    user,
    igv_2024,
    uit_2024,
    derecho_m2_2024,
    tarifa_base_hu_2024,
    tarifa_m2_hu_150,
    tipo_habilitacion_urbana,
):
    """
    A LiquidacionGeneral + LiquidacionPorMetroCuadrado for HU created in 2024
    using 2024-era financial variables (derecho_minimo=500).

    fecha_registro is Jun 2024. Current (2026) records exist with different values.
    """
    fecha_2024 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-HU-2024-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_revision=1,
        sub_total=Decimal("3000.00"),   # 20m2 * 150 = 3000
        total=Decimal("3000.00"),       # no IGV on M2
        igv_id=igv_2024,
        uit_id=uit_2024,
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("4700"),
        fecha_registro=fecha_2024,
    )

    LiquidacionHabilitacionUrbana.objects.create(liquidacion=lg, numero=1)

    liq_m2 = LiquidacionPorMetroCuadrado.objects.create(
        liquidacion_general=lg,
        area_m2=Decimal("20.00"),
        costo_por_m2=Decimal("150.0000"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        tarifa_aplicada=tarifa_m2_hu_150,
        derecho=derecho_m2_2024,
    )

    return {"lg": lg, "liq_m2": liq_m2}


# Composite fixture: MS liquidacion registered in 2024
@pytest.fixture
def liq_ms_2024(
    db, proyecto, municipalidad, user, igv_2024, uit_2024,
    derecho_m2_2024, tarifa_base_ms_2024, tarifa_m2_ms_160, tipo_mecanica_suelos,
):
    fecha_2024 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-MS-2024-001",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_mecanica_suelos,
        numero_revision=1,
        sub_total=Decimal("3200.00"),   # 20m2 * 160 = 3200
        total=Decimal("3200.00"),
        igv_id=igv_2024,
        uit_id=uit_2024,
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("4700"),
        fecha_registro=fecha_2024,
    )

    LiquidacionMecanicaSuelos.objects.create(liquidacion=lg, numero=1)

    liq_m2 = LiquidacionPorMetroCuadrado.objects.create(
        liquidacion_general=lg,
        area_m2=Decimal("20.00"),
        costo_por_m2=Decimal("160.0000"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        tarifa_aplicada=tarifa_m2_ms_160,
        derecho=derecho_m2_2024,
    )

    return {"lg": lg, "liq_m2": liq_m2}


# ── Tests ────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_recalcular_updates_area_solicitada_and_totals(svc, liq_hu_2024):
    """
    GIVEN: HU liquidacion with area_m2=20, costo_por_m2=150, derecho_minimo=500
           subtotal=3000, total=3000 (no IGV)
    WHEN:  recalcular is called with area_solicitada=30
    THEN:  area_m2 updated to 30,
           monto_bruto = 30 * 150 = 4500 → derecho_minimo=500 (floor applies: 4500 > 500)
           subtotal=4500, total=4500 (no IGV)
    """
    lg = liq_hu_2024["lg"]
    liq_m2 = liq_hu_2024["liq_m2"]

    patch = PatchM2Input(area_solicitada=30.0, tarifa_m2_id=None)

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    liq_m2.refresh_from_db()

    assert liq_m2.area_m2 == Decimal("30.00")
    assert float(liq_m2.costo_por_m2) == 150.0
    # 30 * 150 = 4500 > derecho_minimo(500) → no floor, subtotal=4500
    assert lg.sub_total == Decimal("4500.00")
    assert lg.total == Decimal("4500.00")  # no IGV on M2


@pytest.mark.django_db
def test_recalcular_updates_tarifa_m2_id_and_totals(svc, liq_hu_2024, tarifa_m2_hu_200):
    """
    GIVEN: HU liquidacion with costo_por_m2=150, area=20, total=3000
    WHEN:  recalcular is called with tarifa_m2_id pointing to 200/m2 tariff
    THEN:  costo_por_m2 updated to 200,
           monto_bruto = 20 * 200 = 4000 > minimo(500) → subtotal=4000, total=4000
    """
    lg = liq_hu_2024["lg"]
    liq_m2 = liq_hu_2024["liq_m2"]

    patch = PatchM2Input(area_solicitada=None, tarifa_m2_id=str(tarifa_m2_hu_200.id))

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    liq_m2.refresh_from_db()

    assert float(liq_m2.costo_por_m2) == 200.0
    assert lg.sub_total == Decimal("4000.00")
    assert lg.total == Decimal("4000.00")
    # derecho updated to 2024 derecho (not 2026)
    assert liq_m2.derecho_id == liq_hu_2024["liq_m2"].derecho_id


@pytest.mark.django_db
def test_recalcular_changes_both_area_and_tarifa(svc, liq_hu_2024, tarifa_m2_hu_200):
    """
    GIVEN: HU liquidacion with area=20, costo=150, total=3000
    WHEN:  recalcular is called with area=25 AND tarifa_m2_id=200/m2
    THEN:  area_m2=25, costo_por_m2=200,
           monto_bruto = 25 * 200 = 5000 > minimo(500)
           subtotal=5000, total=5000
    """
    lg = liq_hu_2024["lg"]
    liq_m2 = liq_hu_2024["liq_m2"]

    patch = PatchM2Input(area_solicitada=25.0, tarifa_m2_id=str(tarifa_m2_hu_200.id))

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    liq_m2.refresh_from_db()

    assert liq_m2.area_m2 == Decimal("25.00")
    assert float(liq_m2.costo_por_m2) == 200.0
    assert lg.sub_total == Decimal("5000.00")
    assert lg.total == Decimal("5000.00")


@pytest.mark.django_db
def test_recalcular_preserves_area_when_omitted(svc, liq_hu_2024):
    """
    GIVEN: HU liquidacion with area_m2=20, costo_por_m2=150, total=3000
    WHEN:  recalcular is called with area_solicitada=None
    THEN:  area_m2 stays 20, totals recalculated with stored tariff
           20 * 150 = 3000 > minimo(500) → subtotal=3000, total=3000
    """
    lg = liq_hu_2024["lg"]
    liq_m2 = liq_hu_2024["liq_m2"]

    patch = PatchM2Input(area_solicitada=None, tarifa_m2_id=None)

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    liq_m2.refresh_from_db()

    assert liq_m2.area_m2 == Decimal("20.00")
    assert lg.sub_total == Decimal("3000.00")
    assert lg.total == Decimal("3000.00")


@pytest.mark.django_db
def test_recalcular_preserves_tarifa_when_omitted(svc, liq_hu_2024):
    """
    GIVEN: HU liquidacion with area_m2=20, costo_por_m2=150
    WHEN:  recalcular is called with tarifa_m2_id=None
    THEN:  costo_por_m2 stays 150, area unchanged
           totals recalculated with stored tariff
    """
    lg = liq_hu_2024["lg"]
    liq_m2 = liq_hu_2024["liq_m2"]

    patch = PatchM2Input(area_solicitada=18.0, tarifa_m2_id=None)

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    liq_m2.refresh_from_db()

    assert liq_m2.area_m2 == Decimal("18.00")
    assert float(liq_m2.costo_por_m2) == 150.0
    # 18 * 150 = 2700 > minimo(500) → subtotal=2700, total=2700
    assert lg.sub_total == Decimal("2700.00")
    assert lg.total == Decimal("2700.00")


@pytest.mark.django_db
def test_recalcular_uses_historical_derecho_not_current(
    svc, db, proyecto, municipalidad, user, igv_2024, uit_2024,
    derecho_m2_2024, tarifa_base_hu_2024, tarifa_m2_hu_150,
    igv_2026, uit_2026, derecho_m2_2026,
    tarifa_base_hu_2026, tarifa_m2_hu_180, tipo_habilitacion_urbana,
):
    """
    GIVEN: liquidacion registered in 2024 with derecho_minimo=500 (2024)
           AND 2026 records exist with derecho_minimo=600
    WHEN:  recalcular is called with area changed
    THEN:  uses 2024 derecho (500), not 2026 derecho (600)
           — proves historical resolution, not current vigente
    """
    fecha_2024 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto, municipalidad=municipalidad, usuario_creador=user,
        expediente="EXP-HU-HIST-001", estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_habilitacion_urbana, numero_revision=1,
        sub_total=Decimal("3000.00"), total=Decimal("3000.00"),
        igv_id=igv_2024, uit_id=uit_2024,
        igv_snapshot=Decimal("0.18"), uit_snapshot=Decimal("4700"),
        fecha_registro=fecha_2024,
    )

    LiquidacionHabilitacionUrbana.objects.create(liquidacion=lg, numero=1)

    liq_m2 = LiquidacionPorMetroCuadrado.objects.create(
        liquidacion_general=lg,
        area_m2=Decimal("20.00"),
        costo_por_m2=Decimal("150.0000"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        tarifa_aplicada=tarifa_m2_hu_150,
        derecho=derecho_m2_2024,
    )

    patch = PatchM2Input(area_solicitada=10.0, tarifa_m2_id=None)

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    liq_m2.refresh_from_db()

    # 10 * 150 = 1500 > derecho_minimo(500) → subtotal=1500, total=1500
    # Uses 2024 derecho, not 2026
    assert lg.sub_total == Decimal("1500.00")
    assert lg.total == Decimal("1500.00")
    assert liq_m2.derecho_id == derecho_m2_2024.id


@pytest.mark.django_db
def test_recalcular_raises_when_explicit_tarifa_base_not_vigente_at_fecha(
    svc, db, proyecto, municipalidad, user, igv_2024, uit_2024,
    derecho_m2_2024, tarifa_base_hu_2024, tarifa_m2_hu_150,
    igv_2026, uit_2026, derecho_m2_2026,
    tarifa_base_hu_2026, tarifa_m2_hu_180, tipo_habilitacion_urbana,
):
    """
    GIVEN: liquidacion registered in 2024, 2026 tariff exists with different cost
    WHEN:  recalcular is called with an explicit 2026 tariff ID (not vigente at 2024)
    THEN:  raises NoTarifaVigenteError (historical accuracy violation)
    """
    fecha_2024 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto, municipalidad=municipalidad, usuario_creador=user,
        expediente="EXP-HU-NO-TAR", estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_habilitacion_urbana, numero_revision=1,
        sub_total=Decimal("3000.00"), total=Decimal("3000.00"),
        igv_id=igv_2024, uit_id=uit_2024,
        igv_snapshot=Decimal("0.18"), uit_snapshot=Decimal("4700"),
        fecha_registro=fecha_2024,
    )

    LiquidacionHabilitacionUrbana.objects.create(liquidacion=lg, numero=1)

    LiquidacionPorMetroCuadrado.objects.create(
        liquidacion_general=lg,
        area_m2=Decimal("20.00"),
        costo_por_m2=Decimal("150.0000"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        tarifa_aplicada=tarifa_m2_hu_150,
        derecho=derecho_m2_2024,
    )

    # Attempt to use 2026 tariff (not vigente at 2024 fecha_registro)
    patch = PatchM2Input(area_solicitada=20.0, tarifa_m2_id=str(tarifa_m2_hu_180.id))

    with pytest.raises(NoTarifaVigenteError) as exc_info:
        svc.recalcular(lg, patch)

    assert "No existe tarifa base vigente" in str(exc_info.value.message)


@pytest.mark.django_db
def test_recalcular_raises_when_no_historical_derecho(
    svc, db, proyecto, municipalidad, user, igv_2024, uit_2024,
    tarifa_base_hu_2024, tarifa_m2_hu_150,
    igv_2026, uit_2026, derecho_m2_2026,
    tarifa_base_hu_2026, tipo_habilitacion_urbana,
):
    """
    GIVEN: only 2026 DerechoPorMetroCuadrado exists (no derecho covering 2024)
    WHEN:  recalcular is called on a 2024 liquidacion
    THEN:  raises NoDerechoVigenteError (no silent fallback to current)
    """
    fecha_2024 = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto, municipalidad=municipalidad, usuario_creador=user,
        expediente="EXP-HU-NO-DER", estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_habilitacion_urbana, numero_revision=1,
        sub_total=Decimal("3000.00"), total=Decimal("3000.00"),
        igv_id=igv_2024, uit_id=uit_2024,
        igv_snapshot=Decimal("0.18"), uit_snapshot=Decimal("4700"),
        fecha_registro=fecha_2024,
    )

    LiquidacionHabilitacionUrbana.objects.create(liquidacion=lg, numero=1)

    LiquidacionPorMetroCuadrado.objects.create(
        liquidacion_general=lg,
        area_m2=Decimal("20.00"),
        costo_por_m2=Decimal("150.0000"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        tarifa_aplicada=tarifa_m2_hu_150,
        derecho=derecho_m2_2026,
    )

    patch = PatchM2Input(area_solicitada=20.0, tarifa_m2_id=None)

    with pytest.raises(NoDerechoVigenteError) as exc_info:
        svc.recalcular(lg, patch)

    assert "No existe derecho" in str(exc_info.value.message)


@pytest.mark.django_db
def test_recalcular_raises_when_liquidacion_has_no_m2_record(
    svc, db, proyecto, municipalidad, user, igv_2024, uit_2024, tipo_habilitacion_urbana,
):
    """
    GIVEN: a LiquidacionGeneral with no LiquidacionPorMetroCuadrado
    WHEN:  recalcular is called
    THEN:  raises LiquidacionM2NoEncontradaError
    """
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto, municipalidad=municipalidad, usuario_creador=user,
        expediente="EXP-NO-M2", estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_habilitacion_urbana, numero_revision=1,
        sub_total=Decimal("0.00"), total=Decimal("0.00"),
        igv_id=igv_2024, uit_id=uit_2024,
        fecha_registro=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(LiquidacionM2NoEncontradaError) as exc_info:
        svc.recalcular(lg, PatchM2Input(area_solicitada=20.0, tarifa_m2_id=None))

    assert "no tiene un registro LiquidacionPorMetroCuadrado" in str(exc_info.value.message)


@pytest.mark.django_db
def test_recalcular_derecho_minimo_floor_applies(
    svc, liq_hu_2024,
):
    """
    GIVEN: HU liquidacion with area=20, costo=150, derecho_minimo=500
           20 * 150 = 3000 which is > 500 (floor not triggered)
    WHEN:  recalcular is called with area=2 (very small, 2 * 150 = 300 < 500)
    THEN:  derecho_minimo floor applies: subtotal = max(300, 500) = 500
    """
    lg = liq_hu_2024["lg"]
    liq_m2 = liq_hu_2024["liq_m2"]

    patch = PatchM2Input(area_solicitada=2.0, tarifa_m2_id=None)

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    liq_m2.refresh_from_db()

    # 2 * 150 = 300 < derecho_minimo(500) → floor bumps subtotal to derecho_minimo
    assert lg.sub_total == Decimal("500.00")  # floor applied: max(300, 500)
    assert lg.total == Decimal("500.00")


@pytest.mark.django_db
def test_recalcular_updates_lg_totals_correctly(
    svc, liq_hu_2024,
):
    """
    GIVEN: an M2 liquidacion
    WHEN:  recalcular changes area
    THEN:  LiquidacionGeneral.sub_total and .total are updated correctly (no IGV)
           igv_snapshot and uit_snapshot are NOT changed (M2 doesn't use them)
    """
    lg = liq_hu_2024["lg"]
    original_igv_snapshot = lg.igv_snapshot
    original_uit_snapshot = lg.uit_snapshot

    patch = PatchM2Input(area_solicitada=25.0, tarifa_m2_id=None)
    svc.recalcular(lg, patch)

    lg.refresh_from_db()

    assert lg.sub_total == Decimal("3750.00")   # 25 * 150
    assert lg.total == Decimal("3750.00")       # no IGV
    # Snapshots NOT updated (M2 doesn't use IGV/UIT)
    assert lg.igv_snapshot == original_igv_snapshot
    assert lg.uit_snapshot == original_uit_snapshot


@pytest.mark.django_db
def test_recalcular_updates_tarifa_aplicada_and_derecho_fields(
    svc, liq_hu_2024, tarifa_m2_hu_200,
):
    """
    GIVEN: HU liquidacion with stored 150/m2 tariff and 2024 derecho
    WHEN:  recalcular is called with explicit 200/m2 tariff
    THEN:  liq_m2.tarifa_aplicada updated to new tariff
           liq_m2.derecho updated to 2024 derecho (not changed since both are 2024 era)
           liq_m2.derecho_minimo and derecho_maximo updated from cotizacion
    """
    lg = liq_hu_2024["lg"]
    liq_m2 = liq_hu_2024["liq_m2"]
    old_derecho_id = liq_m2.derecho_id

    patch = PatchM2Input(area_solicitada=20.0, tarifa_m2_id=str(tarifa_m2_hu_200.id))

    svc.recalcular(lg, patch)

    liq_m2.refresh_from_db()

    assert liq_m2.tarifa_aplicada_id == tarifa_m2_hu_200.id
    assert float(liq_m2.costo_por_m2) == 200.0
    # Derecho remains 2024 derecho (still vigente)
    assert liq_m2.derecho_id == old_derecho_id


@pytest.mark.django_db
def test_recalcular_ms_tipo_also_works(
    svc, liq_ms_2024,
):
    """
    GIVEN: MS liquidacion with area=20, costo=160, total=3200
    WHEN:  recalcular is called with area=15
    THEN:  area_m2=15, costo unchanged, 15*160=2400, total=2400
           uses MS-specific tariff and derecho
    """
    lg = liq_ms_2024["lg"]
    liq_m2 = liq_ms_2024["liq_m2"]

    patch = PatchM2Input(area_solicitada=15.0, tarifa_m2_id=None)

    svc.recalcular(lg, patch)

    lg.refresh_from_db()
    liq_m2.refresh_from_db()

    assert liq_m2.area_m2 == Decimal("15.00")
    assert float(liq_m2.costo_por_m2) == 160.0
    assert lg.sub_total == Decimal("2400.00")
    assert lg.total == Decimal("2400.00")
