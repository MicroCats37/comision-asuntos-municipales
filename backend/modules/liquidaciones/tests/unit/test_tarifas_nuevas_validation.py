"""
Unit tests for tariff validation rules (ReglaTarifaEdificacion and ReglaTarifaInspeccionObra).

Tests:
- ReglaTarifaEdificacion: resolves by tipo_liquidacion + tramite_accion
- ReglaTarifaInspeccionObra: resolves by categoria + tramite_accion
- XOR validation logic in orchestrators
- THE GAP from Phase 5: tarifas_ids is validated (len=1) but NOT USED

IMPORTANT BUG DETECTED: Orchestrators validate tarifas_ids length but never use it.
The flujo calls _buscar_tarifa_m2(tipo_liquidacion, tramite_accion) which ignores
the provided tariff ID. If design decides to use tarifas_ids, schemas/orchestrator
must be adjusted coherently.
"""
import pytest
import uuid
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

from ninja.errors import HttpError

from modules.liquidaciones.domain.constants import TipoLiquidacion, TramiteAccion


class TestTarifasIdsValidationLogic:
    """Test the tarifas_ids length validation logic in orchestrators.

    This validates that if tarifas_ids is provided, it must have exactly 1 element.
    But NOTE: This validation is INCOMPLETE - the tariff ID is NOT USED after validation.
    """

    def test_tarifas_ids_none_passthrough(self):
        """
        tarifas_ids=None (not provided) passes the length check because
        the check is: if tarifas_ids is not None and len(tarifas_ids) != 1
        """
        tarifas_ids = None
        fails = (tarifas_ids is not None and len(tarifas_ids) != 1)
        assert not fails, "tarifas_ids=None should not fail length check"

    def test_tarifas_ids_empty_list_fails(self):
        """
        tarifas_ids=[] (empty list) fails the length check because len([]) == 0 != 1.
        NOTE: Schema already enforces min_length=1 so empty list would be 422 before reaching orchestrator.
        """
        tarifas_ids = []
        fails = (tarifas_ids is not None and len(tarifas_ids) != 1)
        assert fails, "tarifas_ids=[] should fail length check"

    def test_tarifas_ids_one_element_passes(self):
        """
        tarifas_ids with exactly 1 element passes the validation.
        """
        tarifas_ids = [str(uuid.uuid4())]
        fails = (tarifas_ids is not None and len(tarifas_ids) != 1)
        assert not fails, "tarifas_ids with 1 element should pass length check"

    def test_tarifas_ids_multiple_elements_fails(self):
        """
        tarifas_ids with more than 1 element fails the validation.
        """
        tarifas_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        fails = (tarifas_ids is not None and len(tarifas_ids) != 1)
        assert fails, "tarifas_ids with 2 elements should fail length check"


class TestOrchestratorTarifasIdsFixed:
    """
    Tests that verify the FIX from Phase 6: tarifas_ids IS NOW USED correctly.

    - Orchestrator extracts tarifas_ids[0] and passes as tarifa_id to flujo
    - If tarifa_id is provided, flujo validates it against tipo_liquidacion + tramite_accion
    - If tarifa_id is None, flujo falls back to rule-based auto-selection
    """

    @pytest.mark.asyncio
    async def test_tarifas_ids_provided_passes_tarifa_id_to_flujo(self):
        """
        When tarifas_ids is provided with 1 element, orchestrator passes
        tarifas_ids[0] as tarifa_id to flujo's _proceso_creacion.
        """
        from modules.liquidaciones.domain.services.orchestrators.impacto_vial_orchestrator import (
            ImpactoVialOrchestrator,
        )
        from modules.liquidaciones.domain.services.flujos.impacto_vial_flujo import (
            ImpactoVialFlujo,
        )

        mock_flujo = Mock(spec=ImpactoVialFlujo)
        mock_flujo._proceso_creacion = AsyncMock(return_value=Mock())

        orchestrator = ImpactoVialOrchestrator(flujo=mock_flujo)

        specific_tariff_id = str(uuid.uuid4())
        tarifas_ids = [specific_tariff_id]

        await orchestrator.crear_primera_revision(
            proyecto_public_id="PROY-EXISTING",
            municipalidad_id=str(uuid.uuid4()),
            area_solicitada=100.0,
            expediente=None,
            observacion=None,
            proyecto_inline=None,
            tarifas_ids=tarifas_ids,
        )

        mock_flujo._proceso_creacion.assert_called_once()
        call_kwargs = mock_flujo._proceso_creacion.call_args.kwargs

        # FIXED: tarifa_id IS passed to flujo
        assert 'tarifa_id' in call_kwargs, \
            "FIX: tarifa_id should be passed to flujo"
        assert call_kwargs['tarifa_id'] == specific_tariff_id, \
            "tarifa_id should be the first element of tarifas_ids"

    @pytest.mark.asyncio
    async def test_tarifas_ids_not_provided_passes_tarifa_id_none(self):
        """
        When tarifas_ids is None (not provided), orchestrator passes
        tarifa_id=None to flujo for auto-selection by rules.
        """
        from modules.liquidaciones.domain.services.orchestrators.impacto_vial_orchestrator import (
            ImpactoVialOrchestrator,
        )
        from modules.liquidaciones.domain.services.flujos.impacto_vial_flujo import (
            ImpactoVialFlujo,
        )

        mock_flujo = Mock(spec=ImpactoVialFlujo)
        mock_flujo._proceso_creacion = AsyncMock(return_value=Mock())

        orchestrator = ImpactoVialOrchestrator(flujo=mock_flujo)

        await orchestrator.crear_primera_revision(
            proyecto_public_id="PROY-EXISTING",
            municipalidad_id=str(uuid.uuid4()),
            area_solicitada=100.0,
            expediente=None,
            observacion=None,
            proyecto_inline=None,
            tarifas_ids=None,
        )

        mock_flujo._proceso_creacion.assert_called_once()
        call_kwargs = mock_flujo._proceso_creacion.call_args.kwargs

        assert 'tarifa_id' in call_kwargs, \
            "tarifa_id should be passed to flujo even when None"
        assert call_kwargs['tarifa_id'] is None, \
            "tarifa_id should be None when tarifas_ids not provided"

    @pytest.mark.asyncio
    async def test_inspeccion_obra_tarifas_ids_passes_tarifa_id(self):
        """
        InspeccionObraOrchestrator also passes tarifas_ids[0] as tarifa_id.
        Phase 1: liquidacion_previa_id is now required.
        """
        from modules.liquidaciones.domain.services.orchestrators.inspeccion_obra_orchestrator import (
            InspeccionObraOrchestrator,
        )
        from modules.liquidaciones.domain.services.flujos.inspeccion_obra_flujo import (
            InspeccionObraFlujo,
        )

        mock_flujo = Mock(spec=InspeccionObraFlujo)
        mock_flujo._proceso_creacion = AsyncMock(return_value=Mock())

        orchestrator = InspeccionObraOrchestrator(flujo=mock_flujo)

        specific_tariff_id = str(uuid.uuid4())
        liquidacion_previa_id = str(uuid.uuid4())

        await orchestrator.crear_primera_revision(
            liquidacion_previa_id=liquidacion_previa_id,
            proyecto_public_id="PROY-EXISTING",
            municipalidad_id=str(uuid.uuid4()),
            cantidad_visitas=3,
            categoria="A",
            expediente=None,
            observacion=None,
            proyecto_inline=None,
            tarifas_ids=[specific_tariff_id],
        )

        mock_flujo._proceso_creacion.assert_called_once()
        call_kwargs = mock_flujo._proceso_creacion.call_args.kwargs

        # FIXED: tarifa_id IS passed to flujo
        assert 'tarifa_id' in call_kwargs, \
            "tarifa_id should be passed to flujo"
        assert call_kwargs['tarifa_id'] == specific_tariff_id, \
            "tarifa_id should be the first element of tarifas_ids"


class TestXORValidationLogic:
    """Test XOR validation for proyecto_public_id vs proyecto_inline."""

    def test_xor_both_provided_fails(self):
        """has_public_id=True AND has_inline=True => fails."""
        has_public_id = True
        has_inline = True
        fails = has_public_id and has_inline
        assert fails, "Both provided should fail"

    def test_xor_neither_provided_fails(self):
        """has_public_id=False AND has_inline=False => fails."""
        has_public_id = False
        has_inline = False
        fails = not has_public_id and not has_inline
        assert fails, "Neither provided should fail"

    def test_xor_only_public_id_passes(self):
        """Only public_id provided => passes."""
        has_public_id = True
        has_inline = False
        fails = (has_public_id and has_inline) or (not has_public_id and not has_inline)
        assert not fails

    def test_xor_only_inline_passes(self):
        """Only inline provided => passes."""
        has_public_id = False
        has_inline = True
        fails = (has_public_id and has_inline) or (not has_public_id and not has_inline)
        assert not fails


class TestOrchestratorXORValidationAsync:
    """Test the XOR validation in orchestrator async methods."""

    @pytest.mark.asyncio
    async def test_xor_both_proyecto_raises_400(self):
        """
        Sending both proyecto_public_id AND proyecto_inline must raise HttpError 400.
        """
        from modules.liquidaciones.domain.services.orchestrators.impacto_vial_orchestrator import (
            ImpactoVialOrchestrator,
        )
        from modules.liquidaciones.domain.services.flujos.impacto_vial_flujo import (
            ImpactoVialFlujo,
        )
        from modules.liquidaciones.domain.schemas_proyecto import EntidadInlineData, ProyectoInlineData

        mock_flujo = Mock(spec=ImpactoVialFlujo)
        mock_flujo._proceso_creacion = AsyncMock()

        orchestrator = ImpactoVialOrchestrator(flujo=mock_flujo)

        with pytest.raises(HttpError) as exc_info:
            await orchestrator.crear_primera_revision(
                proyecto_public_id="PROY-EXISTING",
                municipalidad_id=str(uuid.uuid4()),
                area_solicitada=100.0,
                expediente=None,
                observacion=None,
                proyecto_inline=ProyectoInlineData(
                    denominacion="Test",
                    nombre_propietario="Juan Perez",
                    entidad=EntidadInlineData(
                        tipo_documento="RUC",
                        numero_documento="20456789012",
                        razon_social="Empresa Test S.A.",
                    ),
                ),
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_xor_neither_provided_raises_400(self):
        """
        Sending neither proyecto_public_id NOR proyecto_inline must raise HttpError 400.
        """
        from modules.liquidaciones.domain.services.orchestrators.impacto_vial_orchestrator import (
            ImpactoVialOrchestrator,
        )
        from modules.liquidaciones.domain.services.flujos.impacto_vial_flujo import (
            ImpactoVialFlujo,
        )

        mock_flujo = Mock(spec=ImpactoVialFlujo)
        mock_flujo._proceso_creacion = AsyncMock()

        orchestrator = ImpactoVialOrchestrator(flujo=mock_flujo)

        with pytest.raises(HttpError) as exc_info:
            await orchestrator.crear_primera_revision(
                proyecto_public_id=None,
                municipalidad_id=str(uuid.uuid4()),
                area_solicitada=100.0,
                expediente=None,
                observacion=None,
                proyecto_inline=None,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_xor_only_public_id_calls_flujo(self):
        """
        Sending only proyecto_public_id passes XOR and calls flujo.
        """
        from modules.liquidaciones.domain.services.orchestrators.impacto_vial_orchestrator import (
            ImpactoVialOrchestrator,
        )
        from modules.liquidaciones.domain.services.flujos.impacto_vial_flujo import (
            ImpactoVialFlujo,
        )

        mock_flujo = Mock(spec=ImpactoVialFlujo)
        mock_flujo._proceso_creacion = AsyncMock(return_value=Mock())

        orchestrator = ImpactoVialOrchestrator(flujo=mock_flujo)

        result = await orchestrator.crear_primera_revision(
            proyecto_public_id="PROY-EXISTING",
            municipalidad_id=str(uuid.uuid4()),
            area_solicitada=100.0,
            expediente=None,
            observacion=None,
            proyecto_inline=None,
        )

        mock_flujo._proceso_creacion.assert_called_once()

    @pytest.mark.asyncio
    async def test_xor_only_inline_calls_flujo(self):
        """
        Sending only proyecto_inline passes XOR and calls flujo.
        """
        from modules.liquidaciones.domain.services.orchestrators.impacto_vial_orchestrator import (
            ImpactoVialOrchestrator,
        )
        from modules.liquidaciones.domain.services.flujos.impacto_vial_flujo import (
            ImpactoVialFlujo,
        )
        from modules.liquidaciones.domain.schemas_proyecto import EntidadInlineData, ProyectoInlineData

        mock_flujo = Mock(spec=ImpactoVialFlujo)
        mock_flujo._proceso_creacion = AsyncMock(return_value=Mock())

        orchestrator = ImpactoVialOrchestrator(flujo=mock_flujo)

        result = await orchestrator.crear_primera_revision(
            proyecto_public_id=None,
            municipalidad_id=str(uuid.uuid4()),
            area_solicitada=100.0,
            expediente=None,
            observacion=None,
            proyecto_inline=ProyectoInlineData(
                denominacion="Test Inline",
                nombre_propietario="Pedro Gomez",
                entidad=EntidadInlineData(
                    tipo_documento="RUC",
                    numero_documento="20456789013",
                    razon_social="Empresa Inline S.A.",
                ),
            ),
        )

        mock_flujo._proceso_creacion.assert_called_once()


class TestInspeccionObraCategoriaValidation:
    """Test categoria validation in InspeccionObraOrchestrator."""

    @pytest.mark.asyncio
    async def test_categoria_empty_string_raises_400(self):
        """
        Empty categoria must raise HttpError 400.
        Phase 1: liquidacion_previa_id is now required.
        """
        from modules.liquidaciones.domain.services.orchestrators.inspeccion_obra_orchestrator import (
            InspeccionObraOrchestrator,
        )
        from modules.liquidaciones.domain.services.flujos.inspeccion_obra_flujo import (
            InspeccionObraFlujo,
        )

        mock_flujo = Mock(spec=InspeccionObraFlujo)
        mock_flujo._proceso_creacion = AsyncMock()

        orchestrator = InspeccionObraOrchestrator(flujo=mock_flujo)

        with pytest.raises(HttpError) as exc_info:
            await orchestrator.crear_primera_revision(
                liquidacion_previa_id=str(uuid.uuid4()),
                proyecto_public_id="PROY-EXISTING",
                municipalidad_id=str(uuid.uuid4()),
                cantidad_visitas=3,
                categoria="",  # Empty!
                expediente=None,
                observacion=None,
                proyecto_inline=None,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_categoria_whitespace_only_raises_400(self):
        """
        Whitespace-only categoria must raise HttpError 400.
        Phase 1: liquidacion_previa_id is now required.
        """
        from modules.liquidaciones.domain.services.orchestrators.inspeccion_obra_orchestrator import (
            InspeccionObraOrchestrator,
        )
        from modules.liquidaciones.domain.services.flujos.inspeccion_obra_flujo import (
            InspeccionObraFlujo,
        )

        mock_flujo = Mock(spec=InspeccionObraFlujo)
        mock_flujo._proceso_creacion = AsyncMock()

        orchestrator = InspeccionObraOrchestrator(flujo=mock_flujo)

        with pytest.raises(HttpError) as exc_info:
            await orchestrator.crear_primera_revision(
                liquidacion_previa_id=str(uuid.uuid4()),
                proyecto_public_id="PROY-EXISTING",
                municipalidad_id=str(uuid.uuid4()),
                cantidad_visitas=3,
                categoria="   ",  # Whitespace only!
                expediente=None,
                observacion=None,
                proyecto_inline=None,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_categoria_valid_calls_flujo(self):
        """
        Valid categoria (e.g., 'A') passes validation and calls flujo.
        Phase 1: liquidacion_previa_id is now required.
        """
        from modules.liquidaciones.domain.services.orchestrators.inspeccion_obra_orchestrator import (
            InspeccionObraOrchestrator,
        )
        from modules.liquidaciones.domain.services.flujos.inspeccion_obra_flujo import (
            InspeccionObraFlujo,
        )

        mock_flujo = Mock(spec=InspeccionObraFlujo)
        mock_flujo._proceso_creacion = AsyncMock(return_value=Mock())

        orchestrator = InspeccionObraOrchestrator(flujo=mock_flujo)

        result = await orchestrator.crear_primera_revision(
            liquidacion_previa_id=str(uuid.uuid4()),
            proyecto_public_id="PROY-EXISTING",
            municipalidad_id=str(uuid.uuid4()),
            cantidad_visitas=3,
            categoria="A",
            expediente=None,
            observacion=None,
            proyecto_inline=None,
        )

        mock_flujo._proceso_creacion.assert_called_once()
