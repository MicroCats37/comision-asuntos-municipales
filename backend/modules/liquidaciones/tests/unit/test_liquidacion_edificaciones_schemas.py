"""
Unit tests for Liquidaciones Edificaciones schemas (HTTP request validation).

Tests that the Ninja Schema validators correctly accept/reject input
without going through the full HTTP stack.
"""
import pytest
import uuid
from decimal import Decimal

from modules.liquidaciones.presentation.schemas.liquidacion_edificaciones_schemas import (
    PrimeraRevisionLiquidacionIn,
    NuevaRevisionLiquidacionIn,
)


class TestPrimeraRevisionLiquidacionIn:
    """Test PrimeraRevisionLiquidacionIn schema validation."""

    def test_valid_minimal_input(self):
        """Input con solo campos requeridos debe ser válido."""
        municipalidad_id = uuid.uuid4()
        tarifa_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
            "valor_base_calculo": 10000.0,
            "tarifas_ids": [tarifa_id],
        }
        schema = PrimeraRevisionLiquidacionIn(**data)
        assert schema.proyecto_public_id == "PROY-2026-00001"
        assert schema.municipalidad_id == municipalidad_id
        assert schema.tipo_tramite == "OBRA_NUEVA"
        assert schema.valor_proyecto == 10000.0
        assert schema.valor_base_calculo == 10000.0
        assert schema.revisiones_ids == []
        assert schema.tarifas_ids == [tarifa_id]

    def test_valid_full_input(self):
        """Input con todos los campos opcionales debe ser válido."""
        municipalidad_id = uuid.uuid4()
        rev1 = str(uuid.uuid4())
        rev2 = str(uuid.uuid4())
        rev3 = str(uuid.uuid4())
        tarifa_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "AMPLIACION",
            "valor_proyecto": 50000.0,
            "valor_base_calculo": 50000.0,
            "observacion": "Test observacion",
            "revisiones_ids": [rev1, rev2, rev3],
            "tarifas_ids": [tarifa_id],
        }
        schema = PrimeraRevisionLiquidacionIn(**data)
        assert schema.observacion == "Test observacion"
        assert schema.revisiones_ids == [rev1, rev2, rev3]
        assert schema.tarifas_ids == [tarifa_id]

    def test_valor_proyecto_zero_invalid(self):
        """valor_proyecto=0 debe fallar validación (gt=0)."""
        from pydantic import ValidationError
        municipalidad_id = uuid.uuid4()
        tarifa_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 0.0,
            "valor_base_calculo": 0.0,
            "tarifas_ids": [tarifa_id],
        }
        with pytest.raises(ValidationError) as exc_info:
            PrimeraRevisionLiquidacionIn(**data)
        assert "valor_proyecto" in str(exc_info.value)

    def test_valor_proyecto_negative_invalid(self):
        """valor_proyecto negativo debe fallar validación."""
        from pydantic import ValidationError
        municipalidad_id = uuid.uuid4()
        tarifa_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": -100.0,
            "valor_base_calculo": -100.0,
            "tarifas_ids": [tarifa_id],
        }
        with pytest.raises(ValidationError) as exc_info:
            PrimeraRevisionLiquidacionIn(**data)
        assert "valor_proyecto" in str(exc_info.value)

    def test_proyecto_public_id_empty_accepted(self):
        """proyecto_public_id vacío es técnicamente válido según schema actual (sin min_length)."""
        municipalidad_id = uuid.uuid4()
        tarifa_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
            "valor_base_calculo": 10000.0,
            "tarifas_ids": [tarifa_id],
        }
        schema = PrimeraRevisionLiquidacionIn(**data)
        assert schema.proyecto_public_id == ""

    def test_revisiones_ids_empty_is_valid(self):
        """revisiones_ids=[] (default) es válido."""
        municipalidad_id = uuid.uuid4()
        tarifa_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
            "valor_base_calculo": 10000.0,
            "revisiones_ids": [],
            "tarifas_ids": [tarifa_id],
        }
        schema = PrimeraRevisionLiquidacionIn(**data)
        assert schema.revisiones_ids == []

    def test_revisiones_ids_with_duplicates_valid(self):
        """revisiones_ids puede tener duplicados (validación de negocio)."""
        municipalidad_id = uuid.uuid4()
        rev1 = str(uuid.uuid4())
        rev2 = str(uuid.uuid4())
        tarifa_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
            "valor_base_calculo": 10000.0,
            "revisiones_ids": [rev1, rev1, rev2, rev2],
            "tarifas_ids": [tarifa_id],
        }
        schema = PrimeraRevisionLiquidacionIn(**data)
        assert schema.revisiones_ids == [rev1, rev1, rev2, rev2]

    def test_proyecto_inline_accepted_by_schema(self):
        """proyecto_inline (como objeto) es aceptado por el schema sin validar XOR."""
        municipalidad_id = uuid.uuid4()
        tarifa_id = uuid.uuid4()
        data = {
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
            "valor_base_calculo": 10000.0,
            "tarifas_ids": [tarifa_id],
            "proyecto_inline": {
                "denominacion": "Mi Proyecto Inline",
                "direccion": "Calle Falsa 123",
                "nombre_propietario": "Juan Perez Rodriguez",
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789012",
                    "razon_social": "Empresa Test S.A.",
                },
            },
        }
        schema = PrimeraRevisionLiquidacionIn(**data)
        assert schema.proyecto_inline is not None
        assert schema.proyecto_inline.denominacion == "Mi Proyecto Inline"
        assert schema.proyecto_inline.direccion == "Calle Falsa 123"
        # proyecto_public_id es Optional[str] así que "" es válido como "not provided"
        assert schema.proyecto_public_id is None

    def test_proyecto_inline_con_distrito_y_entidad(self):
        """proyecto_inline con distrito_id y entidad (inline) es aceptado."""
        municipalidad_id = uuid.uuid4()
        distrito_id = uuid.uuid4()
        tarifa_id = uuid.uuid4()
        data = {
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
            "valor_base_calculo": 10000.0,
            "tarifas_ids": [tarifa_id],
            "proyecto_inline": {
                "denominacion": "Proyecto con Entidad",
                "direccion": "Av.Principal 456",
                "distrito_id": str(distrito_id),
                "nombre_propietario": "Carlos Rodriguez Perez",
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20456789015",
                    "razon_social": "Empresa Entidad S.A.",
                },
            },
        }
        schema = PrimeraRevisionLiquidacionIn(**data)
        assert schema.proyecto_inline.distrito_id == distrito_id
        assert schema.proyecto_inline.entidad.tipo_documento == "RUC"
        assert schema.proyecto_inline.nombre_propietario == "Carlos Rodriguez Perez"

    def test_tarifas_ids_required_omitted_fails(self):
        """tarifas_ids es requerido — omitirlo falla validación Pydantic.

        El schema usa ... (required) con min_length=1, max_length=1.
        Si no se proporciona tarifas_ids, falla con ValidationError.
        """
        from pydantic import ValidationError
        municipalidad_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
            "valor_base_calculo": 10000.0,
        }
        with pytest.raises(ValidationError) as exc_info:
            PrimeraRevisionLiquidacionIn(**data)
        assert "tarifas_ids" in str(exc_info.value)

    def test_tarifas_ids_with_one_uuid_valid(self):
        """tarifas_ids con exactamente 1 UUID es aceptado por el schema."""
        municipalidad_id = uuid.uuid4()
        tarifa_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
            "valor_base_calculo": 10000.0,
            "tarifas_ids": [tarifa_id],
        }
        schema = PrimeraRevisionLiquidacionIn(**data)
        assert schema.tarifas_ids == [tarifa_id]

    def test_tarifas_ids_with_multiple_uuids_fails(self):
        """tarifas_ids con múltiples UUIDs falla validación del schema (max_length=1)."""
        from pydantic import ValidationError
        municipalidad_id = uuid.uuid4()
        t1 = uuid.uuid4()
        t2 = uuid.uuid4()
        t3 = uuid.uuid4()
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
            "valor_base_calculo": 10000.0,
            "tarifas_ids": [t1, t2, t3],
        }
        with pytest.raises(ValidationError) as exc_info:
            PrimeraRevisionLiquidacionIn(**data)
        assert "tarifas_ids" in str(exc_info.value)

    def test_tarifas_ids_invalid_uuid_fails(self):
        """tarifas_ids con UUID inválido falla validación del schema."""
        from pydantic import ValidationError
        municipalidad_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
            "valor_base_calculo": 10000.0,
            "tarifas_ids": ["not-a-valid-uuid"],
        }
        with pytest.raises(ValidationError) as exc_info:
            PrimeraRevisionLiquidacionIn(**data)
        assert "tarifas_ids" in str(exc_info.value)

    def test_delegados_ids_not_in_primera_revision_schema(self):
        """delegados_ids no existe en PrimeraRevisionLiquidacionIn (Fase 4)."""
        municipalidad_id = uuid.uuid4()
        tarifa_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
            "valor_base_calculo": 10000.0,
            "tarifas_ids": [tarifa_id],
        }
        schema = PrimeraRevisionLiquidacionIn(**data)
        # delegagos_ids no debe existir como campo
        assert not hasattr(schema, 'delegados_ids')


class TestNuevaRevisionLiquidacionIn:
    """Test NuevaRevisionLiquidacionIn schema validation."""

    def test_valid_minimal_input(self):
        """Input con solo campos requeridos debe ser válido."""
        liquidacion_id = uuid.uuid4()
        rev1 = uuid.uuid4()
        data = {
            "liquidacion_previa_id": liquidacion_id,
            "revisiones_ids": [rev1],
        }
        schema = NuevaRevisionLiquidacionIn(**data)
        assert schema.liquidacion_previa_id == liquidacion_id
        assert schema.revisiones_ids == [rev1]

    def test_valid_full_input(self):
        """Input con todos los campos opcionales debe ser válido."""
        liquidacion_id = uuid.uuid4()
        rev4 = uuid.uuid4()
        data = {
            "liquidacion_previa_id": liquidacion_id,
            "revisiones_ids": [rev4],
            "observacion": "Segunda revisión",
        }
        schema = NuevaRevisionLiquidacionIn(**data)
        assert schema.liquidacion_previa_id == liquidacion_id
        assert schema.observacion == "Segunda revisión"
        assert schema.revisiones_ids == [rev4]

    def test_liquidacion_previa_id_zero_invalid(self):
        """liquidacion_previa_id='0' no es un UUID válido y debe fallar."""
        from pydantic import ValidationError
        data = {
            "liquidacion_previa_id": "0",
            "revisiones_ids": [str(uuid.uuid4())],
        }
        with pytest.raises(ValidationError) as exc_info:
            NuevaRevisionLiquidacionIn(**data)
        assert "liquidacion_previa_id" in str(exc_info.value)

    def test_revisiones_ids_empty_fails(self):
        """revisiones_ids=[] debe fallar validación (min_length=1)."""
        from pydantic import ValidationError
        data = {
            "liquidacion_previa_id": str(uuid.uuid4()),
            "revisiones_ids": [],
        }
        with pytest.raises(ValidationError) as exc_info:
            NuevaRevisionLiquidacionIn(**data)
        assert "revisiones_ids" in str(exc_info.value)

    def test_revisiones_ids_invalid_uuid_fails(self):
        """revisiones_ids con UUID inválido debe fallar."""
        from pydantic import ValidationError
        data = {
            "liquidacion_previa_id": str(uuid.uuid4()),
            "revisiones_ids": ["not-a-valid-uuid"],
        }
        with pytest.raises(ValidationError) as exc_info:
            NuevaRevisionLiquidacionIn(**data)
        assert "revisiones_ids" in str(exc_info.value)
