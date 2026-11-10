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
from django.db import IntegrityError

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
    Core returns the single record valid at the requested date.
    """
    # Record 1: Jan-May 2026
    DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 5, 1),
    )
    # Record 2: Jun 2026-open (does not overlap with record 1).
    DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("600.00"),
        derecho_maximo=Decimal("60000.00"),
        porcentaje_minimo_uit=Decimal("0.12"),
        periodo_inicio=date(2026, 6, 1),
        periodo_fin=None,
    )

    # Core returns the record active at the requested date.
    result = servicio.get_derechos_porcentaje_vigentes(fecha=date(2026, 4, 15))
    assert len(result) == 1


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
    Core returns the single record valid at the requested date.
    """
    # Record 1: Jan-Dec 2026
    DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("100.00"),
        derecho_maximo=Decimal("10000.00"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 12, 31),
    )
    # Record 2: Jan 2027-open (does not overlap with record 1).
    DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("120.00"),
        derecho_maximo=Decimal("12000.00"),
        periodo_inicio=date(2027, 1, 1),
        periodo_fin=None,
    )

    # Core returns the record active at the requested date.
    result = servicio.get_derechos_m2_vigentes(fecha=date(2026, 7, 1))
    assert len(result) == 1


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
    Core returns the single record valid at the requested date.
    """
    # Record 1: Jan-Jun 2026
    TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 6, 30),
    )
    # Record 2: Jul 2026-open (does not overlap with record 1).
    TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 7, 1),
        periodo_fin=None,
    )

    # Core returns the record active at the requested date.
    result = servicio.get_tarifas_vigentes("EDIFICACION", fecha=date(2026, 5, 1))
    assert len(result) == 1


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
def test_db_rejects_derecho_porcentaje_overlap(db):
    """
    PostgreSQL rejects intersecting DerechoPorcentajeObra ranges.
    """
    # Record 1: Jan-May 2026
    DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 5, 1),
    )
    with pytest.raises(IntegrityError):
        DerechoPorcentajeObra.objects.create(
            derecho_minimo=Decimal("600.00"),
            derecho_maximo=Decimal("60000.00"),
            porcentaje_minimo_uit=Decimal("0.12"),
            periodo_inicio=date(2026, 4, 1),
            periodo_fin=None,
        )


@pytest.mark.django_db
def test_db_rejects_derecho_m2_overlap(db):
    """
    PostgreSQL rejects intersecting DerechoPorMetroCuadrado ranges.
    """
    # Record 1: Jan-Dec 2026
    DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("100.00"),
        derecho_maximo=Decimal("10000.00"),
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 12, 31),
    )
    with pytest.raises(IntegrityError):
        DerechoPorMetroCuadrado.objects.create(
            derecho_minimo=Decimal("120.00"),
            derecho_maximo=Decimal("12000.00"),
            periodo_inicio=date(2026, 6, 1),
            periodo_fin=None,
        )


@pytest.mark.django_db
def test_db_rejects_tarifa_base_overlap(db, tipo_edificacion):
    """
    PostgreSQL rejects intersecting ranges for the same tipo_liquidacion.
    """
    # Record 1: Jan-Jun 2026
    TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 6, 30),
    )
    with pytest.raises(IntegrityError):
        TarifaLiquidacionBase.objects.create(
            tipo_liquidacion=tipo_edificacion,
            periodo_inicio=date(2026, 4, 1),
            periodo_fin=None,
        )


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
