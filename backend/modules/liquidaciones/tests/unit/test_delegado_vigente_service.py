"""
Unit tests for _obtener_delegados_vigentes in LiquidacionesEdificacionesService.

Tests verify that the vigencia rule is correctly implemented:
  periodo_inicio <= fecha AND (periodo_fin IS NULL OR periodo_fin >= fecha)

This means:
- periodo_fin = NULL means currently vigente (open-ended)
- periodo_fin < fecha means expired (NOT returned)
- periodo_fin >= fecha means vigente (within range)
"""
import pytest
from datetime import date

from modules.liquidaciones.domain.services.core.liquidacion_edificaciones_core_service import (
    LiquidacionesEdificacionesService,
)
from modules.liquidaciones.tests.factories.delegado_factory import (
    DelegadoFactory,
    PeriodoDelegadoFactory,
    MunicipalidadDelegadoFactory,
)
from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
from modules.entidades.models import Municipalidad


@pytest.mark.django_db
class TestObtenerDelegadosVigentes:
    """Test _obtener_delegados_vigentes vigencia rule."""

    def setup_method(self):
        """Create municipalidad for tests."""
        self.core = LiquidacionesEdificacionesService()
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo=f"MUN-TEST-{date.today().year}-{self.distrito.ubigeo}",
            nombre="Municipalidad de Prueba",
            distrito=self.distrito,
        )

    def _crear_delegado_con_periodo(
        self,
        periodo_inicio: date,
        periodo_fin: date | None,
        municipalidad: Municipalidad = None,
    ):
        """
        Helper to create a Delegado with PeriodoDelegado and MunicipalidadesDelegado.

        Args:
            periodo_inicio: Start date of the period
            periodo_fin: End date (None = open-ended/vigente)
            municipalidad: The municipalidad to assign (uses self.municipalidad if None)
        """
        if municipalidad is None:
            municipalidad = self.municipalidad

        # Create the Delegado using factory
        delegado = DelegadoFactory()

        # Create PeriodoDelegado with specified dates
        PeriodoDelegadoFactory(
            delegado=delegado,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
        )

        # Create MunicipalidadesDelegado assignment
        MunicipalidadDelegadoFactory(
            delegado=delegado,
            municipalidad=municipalidad,
            activo=True,
        )

        return delegado

    def test_delegado_periodo_fin_null_es_vigente(self):
        """
        A Delegado with periodo_fin=NULL and periodo_inicio<=fecha must be returned.

        Rule: periodo_inicio <= fecha AND (periodo_fin IS NULL OR periodo_fin >= fecha)
        With periodo_fin=NULL, the IS NULL part is True, so the OR is satisfied.
        """
        today = date.today()
        periodo_inicio = date(today.year - 1, 1, 1)  # Last year

        # Create Delegado with open-ended period (periodo_fin=NULL)
        self._crear_delegado_con_periodo(
            periodo_inicio=periodo_inicio,
            periodo_fin=None,  # NULL = open-ended/vigente
        )

        # Call the service method
        resultados = self.core._obtener_delegados_vigentes(
            municipalidad_id=str(self.municipalidad.id),
            fecha=today,
        )

        # Verify the delegado is returned
        assert len(resultados) == 1, f"Expected 1 delegado, got {len(resultados)}"
        assert resultados[0].nombre_completo is not None

    def test_delegado_periodo_fin_futuro_es_vigente(self):
        """
        A Delegado with periodo_fin > fecha must be returned.
        """
        today = date.today()
        periodo_inicio = date(today.year - 1, 1, 1)
        periodo_fin = date(today.year + 1, 12, 31)  # Future date

        self._crear_delegado_con_periodo(
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
        )

        resultados = self.core._obtener_delegados_vigentes(
            municipalidad_id=str(self.municipalidad.id),
            fecha=today,
        )

        assert len(resultados) == 1

    def test_delegado_periodo_fin_presente_es_vigente(self):
        """
        A Delegado with periodo_fin == fecha (same day) must be returned.
        The condition is periodo_fin >= fecha, so fecha == periodo_fin satisfies it.
        """
        today = date.today()
        periodo_inicio = date(today.year - 1, 1, 1)
        periodo_fin = today  # Same day as fecha

        self._crear_delegado_con_periodo(
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
        )

        resultados = self.core._obtener_delegados_vigentes(
            municipalidad_id=str(self.municipalidad.id),
            fecha=today,
        )

        assert len(resultados) == 1

    def test_delegado_periodo_fin_pasado_no_es_vigente(self):
        """
        A Delegado with periodo_fin < fecha (expired) must NOT be returned.

        Rule: periodo_inicio <= fecha AND (periodo_fin IS NULL OR periodo_fin >= fecha)
        With periodo_fin < fecha, neither condition in the OR is True, so the
        completo rule fails.
        """
        today = date.today()
        periodo_inicio = date(today.year - 2, 1, 1)
        periodo_fin = date(today.year - 1, 12, 31)  # Past date

        self._crear_delegado_con_periodo(
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
        )

        resultados = self.core._obtener_delegados_vigentes(
            municipalidad_id=str(self.municipalidad.id),
            fecha=today,
        )

        # Expired delegado must NOT be returned
        assert len(resultados) == 0, f"Expected 0 delegados, got {len(resultados)} - expired delegado should not be returned"

    def test_delegado_periodo_inicio_futuro_no_es_vigente(self):
        """
        A Delegado with periodo_inicio > fecha must NOT be returned.
        """
        today = date.today()
        periodo_inicio = date(today.year + 1, 1, 1)  # Future date
        periodo_fin = None  # Open-ended

        self._crear_delegado_con_periodo(
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
        )

        resultados = self.core._obtener_delegados_vigentes(
            municipalidad_id=str(self.municipalidad.id),
            fecha=today,
        )

        assert len(resultados) == 0

    def test_delegado_municipalidad_diferente_no_es_vigente(self):
        """
        A Delegado assigned to a different municipalidad must NOT be returned.
        """
        today = date.today()

        # Create a different municipalidad
        otro_distrito = UbigeoDistritoFactory()
        otra_municipalidad = Municipalidad.objects.create(
            codigo=f"MUN-OTRA-{today.year}-{otro_distrito.ubigeo}",
            nombre="Otra Municipalidada",
            distrito=otro_distrito,
        )

        # Create Delegado assigned to the OTHER municipalidad
        self._crear_delegado_con_periodo(
            periodo_inicio=date(today.year - 1, 1, 1),
            periodo_fin=None,
            municipalidad=otra_municipalidad,
        )

        # Query for self.municipalidad
        resultados = self.core._obtener_delegados_vigentes(
            municipalidad_id=str(self.municipalidad.id),
            fecha=today,
        )

        assert len(resultados) == 0

    def test_delegado_municipalidad_activa_false_no_es_vigente(self):
        """
        A Delegado with MunicipalidadesDelegado.activo=False must NOT be returned.
        """
        from modules.liquidaciones.domain.models.delegado import Delegado, PeriodoDelegado, MunicipalidadDelegado
        from modules.liquidaciones.domain.constants import DelegadoStatus, TipoDelegado

        today = date.today()
        periodo_inicio = date(today.year - 1, 1, 1)

        # Create Delegado with factory
        delegado = DelegadoFactory()

        # Create PeriodoDelegado with NULL periodo_fin (vigente)
        PeriodoDelegado.objects.create(
            delegado=delegado,
            periodo_inicio=periodo_inicio,
            periodo_fin=None,  # Open-ended
        )

        # Create MunicipalidadesDelegado with activo=False
        MunicipalidadDelegado.objects.create(
            delegado=delegado,
            municipalidad=self.municipalidad,
            activo=False,  # NOT active
        )

        resultados = self.core._obtener_delegados_vigentes(
            municipalidad_id=str(self.municipalidad.id),
            fecha=today,
        )

        assert len(resultados) == 0

    def test_delegado_result_es_delegado_vigente_result_dto(self):
        """
        Verify that the returned objects are DelegadoVigenteResult DTOs (typed), not dicts.
        """
        from modules.liquidaciones.domain.schemas import DelegadoVigenteResult

        today = date.today()
        self._crear_delegado_con_periodo(
            periodo_inicio=date(today.year - 1, 1, 1),
            periodo_fin=None,
        )

        resultados = self.core._obtener_delegados_vigentes(
            municipalidad_id=str(self.municipalidad.id),
            fecha=today,
        )

        assert len(resultados) == 1
        # Verify it's a DelegadoVigenteResult instance, not a dict
        assert isinstance(resultados[0], DelegadoVigenteResult)
        # Verify expected fields exist
        assert hasattr(resultados[0], 'id')
        assert hasattr(resultados[0], 'nombre_completo')
        assert hasattr(resultados[0], 'cip')
        assert hasattr(resultados[0], 'especialidad')
        assert hasattr(resultados[0], 'tipo')
        # Verify nested especialidad has expected fields
        assert hasattr(resultados[0].especialidad, 'id')
        assert hasattr(resultados[0].especialidad, 'nombre')

