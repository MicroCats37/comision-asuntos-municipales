"""
Unit tests for VigenciaQuerySet and VigenciaManager base contract.

Tests the common `vigente()` and `vigentes()` methods on the base
VigenciaQuerySet/VigenciaManager classes using EscalaDescuentoInspector
(which correctly uses VigenciaManager via VigenciaModel).

These tests verify the base contract BEFORE any subclass overrides,
ensuring the foundational behavior is correct and stable.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from modules.finanzas.domain.models import EscalaDescuentoInspector, IGV, TasaDelegado, UIT
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion


@pytest.fixture
def escala(db):
    """Create a simple EscalaDescuentoInspector for testing."""
    return EscalaDescuentoInspector.objects.create(
        nombre="Escala Test",
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def escala_with_fin(db):
    """Create an EscalaDescuentoInspector with explicit end date."""
    return EscalaDescuentoInspector.objects.create(
        nombre="Escala Con Fin",
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2025, 12, 31),
    )


@pytest.fixture
def igv_current(db):
    """Create an IGV with no end date (currently vigente)."""
    return IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def igv_with_fin(db):
    """Create an IGV with an explicit end date."""
    return IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2025, 12, 31),
    )


@pytest.fixture
def igv_future(db):
    """Create an IGV that starts in the future."""
    tomorrow = date.today() + timedelta(days=1)
    return IGV.objects.create(
        valor=Decimal("0.19"),
        periodo_inicio=tomorrow,
        periodo_fin=None,
    )


@pytest.fixture
def uit_current(db):
    """Create a UIT with no end date (currently vigente)."""
    return UIT.objects.create(
        valor=4950,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def uit_with_fin(db):
    """Create a UIT with an explicit end date."""
    return UIT.objects.create(
        valor=4950,
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2023, 12, 31),
    )


@pytest.fixture
def uit_future(db):
    """Create a UIT that starts in the future."""
    tomorrow = date.today() + timedelta(days=1)
    return UIT.objects.create(
        valor=5150,
        periodo_inicio=tomorrow,
        periodo_fin=None,
    )


@pytest.fixture
def tipo_liq_tasa(db):
    """Get or create a TipoLiquidacion for TasaDelegado tests."""
    return TipoLiquidacion.objects.get_or_create(codigo="TASA_TEST", defaults={"nombre": "Tasa Test"})[0]


@pytest.fixture
def tasa_delegado_current(db, tipo_liq_tasa):
    """Create a TasaDelegado with no end date (currently vigente)."""
    return TasaDelegado.objects.create(
        tipo_liquidacion=tipo_liq_tasa,
        nombre="Tasa Actual",
        renta_cip=Decimal("0.25"),
        aporte_codemu=Decimal("0.05"),
        fondo_comun=Decimal("0.10"),
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tasa_delegado_with_fin(db, tipo_liq_tasa):
    """Create a TasaDelegado with an explicit end date."""
    return TasaDelegado.objects.create(
        tipo_liquidacion=tipo_liq_tasa,
        nombre="Tasa Con Fin",
        renta_cip=Decimal("0.25"),
        aporte_codemu=Decimal("0.05"),
        fondo_comun=Decimal("0.10"),
        periodo_inicio=date(2020, 1, 1),
        periodo_fin=date(2025, 12, 31),
    )


@pytest.fixture
def tasa_delegado_future(db, tipo_liq_tasa):
    """Create a TasaDelegado that starts in the future."""
    tomorrow = date.today() + timedelta(days=1)
    return TasaDelegado.objects.create(
        tipo_liquidacion=tipo_liq_tasa,
        nombre="Tasa Futura",
        renta_cip=Decimal("0.30"),
        aporte_codemu=Decimal("0.06"),
        fondo_comun=Decimal("0.12"),
        periodo_inicio=tomorrow,
        periodo_fin=None,
    )


@pytest.mark.django_db
class TestVigenciaQuerySetBasics:
    """Tests for VigenciaQuerySet.vigentes() basic behavior."""

    def test_vigentes_fecha_defaults_to_today(self, escala):
        """
        vigentes() with no fecha argument defaults to date.today().
        """
        today = date.today()
        escala.periodo_inicio = today
        escala.save()

        qs = EscalaDescuentoInspector.objects.vigentes()
        assert qs.count() == 1
        assert qs.first() == escala

    def test_vigentes_excludes_future_start(self, db):
        """
        Records with periodo_inicio in the future are NOT vigentes at today.
        """
        tomorrow = date.today() + timedelta(days=1)
        future = EscalaDescuentoInspector.objects.create(
            nombre="Future Escala",
            periodo_inicio=tomorrow,
            periodo_fin=None,
        )

        qs = EscalaDescuentoInspector.objects.vigentes()
        assert future not in qs

    def test_vigentes_includes_open_ended(self, escala):
        """
        Records with periodo_fin=None are vigentes if periodo_inicio <= fecha.
        """
        today = date.today()
        qs = EscalaDescuentoInspector.objects.vigentes(fecha=today)
        assert qs.filter(pk=escala.pk).exists()

    def test_vigentes_includes_within_range(self, escala_with_fin):
        """
        Records with periodo_fin >= fecha are vigentes when periodo_inicio <= fecha.
        """
        qs = EscalaDescuentoInspector.objects.vigentes(fecha=date(2023, 6, 15))
        assert qs.filter(pk=escala_with_fin.pk).exists()

    def test_vigentes_excludes_expired(self, escala_with_fin):
        """
        Records with periodo_fin < fecha are NOT vigentes.
        """
        qs = EscalaDescuentoInspector.objects.vigentes(fecha=date(2026, 1, 1))
        assert not qs.filter(pk=escala_with_fin.pk).exists()

    def test_vigentes_filter_rule_three_conditions(self, db):
        """
        Verify the three-condition filter rule:
        periodo_inicio <= fecha AND (periodo_fin IS NULL OR periodo_fin >= fecha).

        Test case: record that starts AFTER fecha is NOT vigente even if no end date.
        """
        yesterday = date.today() - timedelta(days=1)
        tomorrow = date.today() + timedelta(days=1)

        # Record starts tomorrow, no end - should NOT be vigente today
        future_open = EscalaDescuentoInspector.objects.create(
            nombre="Future Open",
            periodo_inicio=tomorrow,
            periodo_fin=None,
        )

        qs = EscalaDescuentoInspector.objects.vigentes()
        assert future_open not in qs


@pytest.mark.django_db
class TestVigenciaQuerySetSingular:
    """Tests for VigenciaQuerySet.vigente() singular method."""

    def test_vigente_returns_single_record(self, escala):
        """
        vigente() returns a single record, not a QuerySet.
        """
        result = EscalaDescuentoInspector.objects.vigente()
        assert result is not None
        assert isinstance(result, EscalaDescuentoInspector)

    def test_vigente_returns_newest_when_multiple_vigentes(self, db):
        """
        When multiple records are vigentes, vigente() returns the newest by periodo_inicio.
        """
        older = EscalaDescuentoInspector.objects.create(
            nombre="Older",
            periodo_inicio=date(2020, 1, 1),
            periodo_fin=None,
        )
        newer = EscalaDescuentoInspector.objects.create(
            nombre="Newer",
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=None,
        )

        result = EscalaDescuentoInspector.objects.vigente()
        assert result == newer

    def test_vigente_returns_none_when_no_match(self, db):
        """
        vigente() returns None when no record matches the fecha.
        """
        # Create a record that expired long ago
        old = EscalaDescuentoInspector.objects.create(
            nombre="Old Expired",
            periodo_inicio=date(2000, 1, 1),
            periodo_fin=date(2000, 12, 31),
        )

        result = EscalaDescuentoInspector.objects.vigente(fecha=date(2026, 1, 1))
        assert result is None

    def test_vigente_respects_periodo_inicio(self, db):
        """
        vigente() does NOT return a record that starts in the future.
        """
        tomorrow = date.today() + timedelta(days=1)
        future = EscalaDescuentoInspector.objects.create(
            nombre="Future Escala",
            periodo_inicio=tomorrow,
            periodo_fin=None,
        )

        result = EscalaDescuentoInspector.objects.vigente()
        assert result is None or result != future


@pytest.mark.django_db
class TestVigenciaManagerProxy:
    """Tests that VigenciaManager proxies correctly to VigenciaQuerySet."""

    def test_manager_vigente_proxy(self, escala):
        """
        VigenciaManager.vigente() returns the same result as VigenciaQuerySet.vigente().
        """
        manager_result = EscalaDescuentoInspector.objects.vigente()
        qs_result = (
            EscalaDescuentoInspector.objects.get_queryset().vigente()
        )
        assert manager_result == qs_result

    def test_manager_vigentes_proxy(self, escala):
        """
        VigenciaManager.vigentes() returns the same result as VigenciaQuerySet.vigentes().
        """
        manager_result = EscalaDescuentoInspector.objects.vigentes()
        qs_result = (
            EscalaDescuentoInspector.objects.get_queryset().vigentes()
        )
        assert list(manager_result) == list(qs_result)


@pytest.mark.django_db
class TestIGVQuerySet:
    """Tests for IGV QuerySet using inherited VigenciaQuerySet logic."""

    def test_vigente_returns_single_record(self, igv_current):
        """
        vigente() returns a single IGV instance, not a QuerySet.
        """
        result = IGV.objects.vigente()
        assert result is not None
        assert isinstance(result, IGV)

    def test_vigente_returns_none_when_no_match(self, db):
        """
        vigente() returns None when no IGV is vigente at the given fecha.
        """
        expired = IGV.objects.create(
            valor=Decimal("0.16"),
            periodo_inicio=date(2000, 1, 1),
            periodo_fin=date(2000, 12, 31),
        )
        result = IGV.objects.vigente(fecha=date(2026, 1, 1))
        assert result is None

    def test_vigente_returns_newest_when_multiple_vigentes(self, db):
        """
        When multiple IGV records are vigentes, vigente() returns the newest by periodo_inicio.
        """
        older = IGV.objects.create(
            valor=Decimal("0.16"),
            periodo_inicio=date(2018, 1, 1),
            periodo_fin=None,
        )
        newer = IGV.objects.create(
            valor=Decimal("0.18"),
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=None,
        )
        result = IGV.objects.vigente()
        assert result == newer

    def test_vigente_excludes_future_start(self, igv_future):
        """
        vigente() does NOT return a record with periodo_inicio in the future.
        """
        result = IGV.objects.vigente()
        assert result is None or result != igv_future

    def test_vigente_includes_open_ended(self, igv_current):
        """
        vigente() includes records with periodo_fin=None when periodo_inicio <= fecha.
        """
        today = date.today()
        result = IGV.objects.vigente(fecha=today)
        assert result is not None

    def test_vigente_excludes_expired(self, igv_with_fin):
        """
        vigente() excludes records whose periodo_fin < fecha.
        """
        result = IGV.objects.vigente(fecha=date(2026, 1, 1))
        assert result is None

    def test_vigente_includes_within_range(self, igv_with_fin):
        """
        vigente() includes records with periodo_fin >= fecha when periodo_inicio <= fecha.
        """
        result = IGV.objects.vigente(fecha=date(2023, 6, 15))
        assert result is not None

    def test_vigentes_excludes_future_start(self, igv_future):
        """
        vigentes() does NOT include records with periodo_inicio in the future.
        """
        qs = IGV.objects.vigentes()
        assert igv_future not in qs

    def test_vigentes_includes_open_ended(self, igv_current):
        """
        vigentes() includes records with periodo_fin=None when periodo_inicio <= fecha.
        """
        today = date.today()
        qs = IGV.objects.vigentes(fecha=today)
        assert qs.filter(pk=igv_current.pk).exists()

    def test_vigentes_excludes_expired(self, igv_with_fin):
        """
        vigentes() excludes records with periodo_fin < fecha.
        """
        qs = IGV.objects.vigentes(fecha=date(2026, 1, 1))
        assert not qs.filter(pk=igv_with_fin.pk).exists()


@pytest.mark.django_db
class TestUITQuerySet:
    """Tests for UIT QuerySet using inherited VigenciaQuerySet logic."""

    def test_vigente_returns_single_record(self, uit_current):
        """
        vigente() returns a single UIT instance, not a QuerySet.
        """
        result = UIT.objects.vigente()
        assert result is not None
        assert isinstance(result, UIT)

    def test_vigente_returns_none_when_no_match(self, db):
        """
        vigente() returns None when no UIT is vigente at the given fecha.
        """
        result = UIT.objects.vigente(fecha=date(2000, 1, 1))
        assert result is None

    def test_vigente_returns_newest_when_multiple_vigentes(self, db):
        """
        When multiple UIT records are vigentes, vigente() returns the newest by periodo_inicio.
        """
        older = UIT.objects.create(
            valor=4400,
            periodo_inicio=date(2021, 1, 1),
            periodo_fin=None,
        )
        newer = UIT.objects.create(
            valor=4950,
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=None,
        )
        result = UIT.objects.vigente()
        assert result == newer

    def test_vigente_excludes_future_start(self, uit_future):
        """
        vigente() does NOT return a record with periodo_inicio in the future.
        """
        result = UIT.objects.vigente()
        assert result is None or result != uit_future

    def test_vigente_includes_open_ended(self, uit_current):
        """
        vigente() includes records with periodo_fin=None when periodo_inicio <= fecha.
        """
        today = date.today()
        result = UIT.objects.vigente(fecha=today)
        assert result is not None

    def test_vigente_excludes_expired(self, uit_with_fin):
        """
        vigente() excludes records whose periodo_fin < fecha.
        """
        result = UIT.objects.vigente(fecha=date(2026, 1, 1))
        assert result is None

    def test_vigente_includes_within_range(self, uit_with_fin):
        """
        vigente() includes records with periodo_fin >= fecha when periodo_inicio <= fecha.
        """
        result = UIT.objects.vigente(fecha=date(2022, 6, 15))
        assert result is not None

    def test_vigentes_excludes_future_start(self, uit_future):
        """
        vigentes() does NOT include records with periodo_inicio in the future.
        """
        qs = UIT.objects.vigentes()
        assert uit_future not in qs

    def test_vigentes_includes_open_ended(self, uit_current):
        """
        vigentes() includes records with periodo_fin=None when periodo_inicio <= fecha.
        """
        today = date.today()
        qs = UIT.objects.vigentes(fecha=today)
        assert qs.filter(pk=uit_current.pk).exists()

    def test_vigentes_excludes_expired(self, uit_with_fin):
        """
        vigentes() excludes records with periodo_fin < fecha.
        """
        qs = UIT.objects.vigentes(fecha=date(2026, 1, 1))
        assert not qs.filter(pk=uit_with_fin.pk).exists()


@pytest.mark.django_db
class TestTasaDelegadoQuerySet:
    """Tests for TasaDelegado QuerySet using inherited VigenciaQuerySet logic."""

    def test_vigente_returns_single_record(self, tasa_delegado_current):
        """
        vigente() returns a single TasaDelegado instance, not a QuerySet.
        """
        result = TasaDelegado.objects.vigente()
        assert result is not None
        assert isinstance(result, TasaDelegado)

    def test_vigente_returns_none_when_no_match(self, db):
        """
        vigente() returns None when no TasaDelegado is vigente at the given fecha.
        """
        expired = TasaDelegado.objects.create(
            tipo_liquidacion=TipoLiquidacion.objects.get_or_create(codigo="EXP", defaults={"nombre": "Expired"})[0],
            nombre="Expired",
            renta_cip=Decimal("0.25"),
            aporte_codemu=Decimal("0.05"),
            fondo_comun=Decimal("0.10"),
            periodo_inicio=date(2000, 1, 1),
            periodo_fin=date(2000, 12, 31),
        )
        result = TasaDelegado.objects.vigente(fecha=date(2026, 1, 1))
        assert result is None

    def test_vigente_returns_newest_when_multiple_vigentes(self, db):
        """
        When multiple TasaDelegado records are vigentes, vigente() returns the newest by periodo_inicio.
        """
        tipo = TipoLiquidacion.objects.get_or_create(codigo="MULTI", defaults={"nombre": "Multi"})[0]
        older = TasaDelegado.objects.create(
            tipo_liquidacion=tipo,
            nombre="Older",
            renta_cip=Decimal("0.20"),
            aporte_codemu=Decimal("0.04"),
            fondo_comun=Decimal("0.08"),
            periodo_inicio=date(2020, 1, 1),
            periodo_fin=None,
        )
        newer = TasaDelegado.objects.create(
            tipo_liquidacion=tipo,
            nombre="Newer",
            renta_cip=Decimal("0.25"),
            aporte_codemu=Decimal("0.05"),
            fondo_comun=Decimal("0.10"),
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=None,
        )
        result = TasaDelegado.objects.vigente()
        assert result == newer

    def test_vigente_excludes_future_start(self, tasa_delegado_future):
        """
        vigente() does NOT return a record with periodo_inicio in the future.
        """
        result = TasaDelegado.objects.vigente()
        assert result is None or result != tasa_delegado_future

    def test_vigente_includes_open_ended(self, tasa_delegado_current):
        """
        vigente() includes records with periodo_fin=None when periodo_inicio <= fecha.
        """
        today = date.today()
        result = TasaDelegado.objects.vigente(fecha=today)
        assert result is not None

    def test_vigente_excludes_expired(self, tasa_delegado_with_fin):
        """
        vigente() excludes records whose periodo_fin < fecha.
        """
        result = TasaDelegado.objects.vigente(fecha=date(2026, 1, 1))
        assert result is None

    def test_vigente_includes_within_range(self, tasa_delegado_with_fin):
        """
        vigente() includes records with periodo_fin >= fecha when periodo_inicio <= fecha.
        """
        result = TasaDelegado.objects.vigente(fecha=date(2023, 6, 15))
        assert result is not None

    def test_vigentes_excludes_future_start(self, tasa_delegado_future):
        """
        vigentes() does NOT include records with periodo_inicio in the future.
        """
        qs = TasaDelegado.objects.vigentes()
        assert tasa_delegado_future not in qs

    def test_vigentes_includes_open_ended(self, tasa_delegado_current):
        """
        vigentes() includes records with periodo_fin=None when periodo_inicio <= fecha.
        """
        today = date.today()
        qs = TasaDelegado.objects.vigentes(fecha=today)
        assert qs.filter(pk=tasa_delegado_current.pk).exists()

    def test_vigentes_excludes_expired(self, tasa_delegado_with_fin):
        """
        vigentes() excludes records with periodo_fin < fecha.
        """
        qs = TasaDelegado.objects.vigentes(fecha=date(2026, 1, 1))
        assert not qs.filter(pk=tasa_delegado_with_fin.pk).exists()
