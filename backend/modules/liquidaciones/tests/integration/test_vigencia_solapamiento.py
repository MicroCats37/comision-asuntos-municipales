"""
Integration tests for vigencia overlap detection.

The overlap validation (HttpError on >1 vigente record) lives in:
1. `validar_sin_solapamiento` helper in orchestrator layer
2. Orchestrators call it after fetching the raw list from core

Core services are now PURE ORM (no HttpError).
These tests verify:
- Core services return raw lists (no HttpError)
- `validar_sin_solapamiento` raises HttpError(400) when overlap is detected
"""
import pytest
from decimal import Decimal
from datetime import date

from ninja.errors import HttpError

from modules.liquidaciones.domain.services.core.liquidacion_tipo.tarifas_historicas_core_service import (
    TarifasHistoricasCoreService,
)
from modules.liquidaciones.domain.services.orchestrators._shared.vigencia_validation import (
    validar_sin_solapamiento,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    DerechoPorMetroCuadrado,
    DerechoPorcentajeObra,
)
from modules.liquidaciones.tests.fixtures.tipos_fixtures import (
    tipo_edificacion,
    tipo_habilitacion_urbana,
)


@pytest.fixture
def servicio():
    return TarifasHistoricasCoreService()


# ── Core services return pure lists (no HttpError) ─────────────────────────────────


@pytest.mark.django_db
def test_get_derechos_porcentaje_vigentes_returns_list(servicio, db):
    """
    Core returns a list (no HttpError), even with overlapping records.
    Validation happens in the orchestrator layer.
    """
    # Record 1: Jan-May 2026
    DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 5, 1),
    )
    # Record 2: Apr 2026-open (overlaps with record 1 at date 2026-04-15)
    DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("600.00"),
        derecho_maximo=Decimal("60000.00"),
        porcentaje_minimo_uit=Decimal("0.12"),
        periodo_inicio=date(2026, 4, 1),
        periodo_fin=None,
    )

    # Core returns list — NO HttpError raised here
    result = servicio.get_derechos_porcentaje_vigentes(fecha=date(2026, 4, 15))
    assert len(result) == 2


@pytest.mark.django_db
def test_get_derechos_porcentaje_vigentes_single_record_ok(servicio, db):
    """
    When exactly one DerechoPorcentajeObra is vigente, core returns a 1-item list.
    """
    DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )

    result = servicio.get_derechos_porcentaje_vigentes(fecha=date(2026, 6, 1))
    assert len(result) == 1


@pytest.mark.django_db
def test_get_derechos_m2_vigentes_returns_list(servicio, db):
    """
    Core returns a list (no HttpError), even with overlapping records.
    Validation happens in the orchestrator layer.
    """
    # Record 1: Jan-Dec 2026
    DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("100.00"),
        derecho_maximo=Decimal("10000.00"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 12, 31),
    )
    # Record 2: Jun 2026-open (overlaps with record 1 at date 2026-07-01)
    DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("120.00"),
        derecho_maximo=Decimal("12000.00"),
        periodo_inicio=date(2026, 6, 1),
        periodo_fin=None,
    )

    # Core returns list — NO HttpError raised here
    result = servicio.get_derechos_m2_vigentes(fecha=date(2026, 7, 1))
    assert len(result) == 2


@pytest.mark.django_db
def test_get_derechos_m2_vigentes_single_record_ok(servicio, db):
    """
    When exactly one DerechoPorMetroCuadrado is vigente, core returns a 1-item list.
    """
    DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("100.00"),
        derecho_maximo=Decimal("10000.00"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )

    result = servicio.get_derechos_m2_vigentes(fecha=date(2026, 6, 1))
    assert len(result) == 1


@pytest.mark.django_db
def test_get_tarifas_vigentes_returns_list(servicio, db, tipo_edificacion):
    """
    Core returns a list (no HttpError), even with overlapping records.
    Validation happens in the orchestrator layer.
    """
    # Record 1: Jan-Jun 2026
    TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 6, 30),
    )
    # Record 2: Apr 2026-open (overlaps with record 1 at date 2026-05-01)
    TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 4, 1),
        periodo_fin=None,
    )

    # Core returns list — NO HttpError raised here
    result = servicio.get_tarifas_vigentes("EDIFICACION", fecha=date(2026, 5, 1))
    assert len(result) == 2


@pytest.mark.django_db
def test_get_tarifas_vigentes_different_tipos_no_overlap(servicio, db, tipo_edificacion, tipo_habilitacion_urbana):
    """
    Two TarifaLiquidacionBase records with DIFFERENT tipo_liquidacion are NOT
    considered overlapping (each tipo has its own tariff schedule).
    Core returns a 1-item list for each tipo.
    """
    # EDIFICACION: Jan-Jun 2026
    TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 6, 30),
    )
    # HU: Jan-Jun 2026 (different tipo, same dates — NOT overlap for our check)
    TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 6, 30),
    )

    result = servicio.get_tarifas_vigentes("EDIFICACION", fecha=date(2026, 3, 1))
    assert len(result) == 1

    result_hu = servicio.get_tarifas_vigentes("HABILITACION_URBANA", fecha=date(2026, 3, 1))
    assert len(result_hu) == 1


@pytest.mark.django_db
def test_get_tarifas_vigentes_single_record_ok(servicio, db, tipo_edificacion):
    """
    When exactly one TarifaLiquidacionBase is vigente for a tipo, core returns a 1-item list.
    """
    TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )

    result = servicio.get_tarifas_vigentes("EDIFICACION", fecha=date(2026, 6, 1))
    assert len(result) == 1


# ── validar_sin_solapamiento raises HttpError(400) ─────────────────────────────────


@pytest.mark.django_db
def test_validar_sin_solapamiento_raises_on_derecho_porcentaje_overlap(db):
    """
    When two DerechoPorcentajeObra records overlap at the same date,
    validar_sin_solapamiento raises HttpError(400).
    """
    # Record 1: Jan-May 2026
    DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 5, 1),
    )
    # Record 2: Apr 2026-open (overlaps with record 1 at date 2026-04-15)
    DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("600.00"),
        derecho_maximo=Decimal("60000.00"),
        porcentaje_minimo_uit=Decimal("0.12"),
        periodo_inicio=date(2026, 4, 1),
        periodo_fin=None,
    )

    servicio = TarifasHistoricasCoreService()
    records = servicio.get_derechos_porcentaje_vigentes(fecha=date(2026, 4, 15))

    with pytest.raises(HttpError) as exc_info:
        validar_sin_solapamiento(records, "DerechoPorcentajeObra")

    assert exc_info.value.status_code == 400
    assert "Solapamiento de vigencias en DerechoPorcentajeObra" in str(exc_info.value.message)
    assert "2 registros vigentes" in str(exc_info.value.message)


@pytest.mark.django_db
def test_validar_sin_solapamiento_raises_on_derecho_m2_overlap(db):
    """
    When two DerechoPorMetroCuadrado records overlap at the same date,
    validar_sin_solapamiento raises HttpError(400).
    """
    # Record 1: Jan-Dec 2026
    DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("100.00"),
        derecho_maximo=Decimal("10000.00"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 12, 31),
    )
    # Record 2: Jun 2026-open (overlaps with record 1 at date 2026-07-01)
    DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("120.00"),
        derecho_maximo=Decimal("12000.00"),
        periodo_inicio=date(2026, 6, 1),
        periodo_fin=None,
    )

    servicio = TarifasHistoricasCoreService()
    records = servicio.get_derechos_m2_vigentes(fecha=date(2026, 7, 1))

    with pytest.raises(HttpError) as exc_info:
        validar_sin_solapamiento(records, "DerechoPorMetroCuadrado")

    assert exc_info.value.status_code == 400
    assert "Solapamiento de vigencias en DerechoPorMetroCuadrado" in str(exc_info.value.message)
    assert "2 registros vigentes" in str(exc_info.value.message)


@pytest.mark.django_db
def test_validar_sin_solapamiento_raises_on_tarifa_base_overlap(db, tipo_edificacion):
    """
    When two TarifaLiquidacionBase records for the same tipo_liquidacion
    overlap at the same date, validar_sin_solapamiento raises HttpError(400).
    """
    # Record 1: Jan-Jun 2026
    TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 6, 30),
    )
    # Record 2: Apr 2026-open (overlaps with record 1 at date 2026-05-01)
    TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 4, 1),
        periodo_fin=None,
    )

    servicio = TarifasHistoricasCoreService()
    records = servicio.get_tarifas_vigentes("EDIFICACION", fecha=date(2026, 5, 1))

    with pytest.raises(HttpError) as exc_info:
        validar_sin_solapamiento(records, "TarifaLiquidacionBase tipo=EDIFICACION")

    assert exc_info.value.status_code == 400
    assert "Solapamiento de vigencias en TarifaLiquidacionBase" in str(exc_info.value.message)
    assert "tipo=EDIFICACION" in str(exc_info.value.message)
    assert "2 registros vigentes" in str(exc_info.value.message)


@pytest.mark.django_db
def test_validar_sin_solapamiento_single_record_ok(db):
    """
    When exactly one record is vigente, no error is raised.
    """
    DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )

    servicio = TarifasHistoricasCoreService()
    records = servicio.get_derechos_porcentaje_vigentes(fecha=date(2026, 6, 1))

    # Should NOT raise
    validar_sin_solapamiento(records, "DerechoPorcentajeObra")
    assert len(records) == 1
