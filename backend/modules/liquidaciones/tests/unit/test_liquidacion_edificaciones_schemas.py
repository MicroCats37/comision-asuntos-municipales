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
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
        }
        schema = PrimeraRevisionLiquidacionIn(**data)
        assert schema.proyecto_public_id == "PROY-2026-00001"
        assert schema.municipalidad_id == municipalidad_id
        assert schema.tipo_tramite == "OBRA_NUEVA"
        assert schema.valor_proyecto == 10000.0
        assert schema.revisiones_ids == []

    def test_valid_full_input(self):
        """Input con todos los campos opcionales debe ser válido."""
        municipalidad_id = uuid.uuid4()
        rev1 = str(uuid.uuid4())
        rev2 = str(uuid.uuid4())
        rev3 = str(uuid.uuid4())
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "AMPLIACION",
            "valor_proyecto": 50000.0,
            "observacion": "Test observacion",
            "revisiones_ids": [rev1, rev2, rev3],
        }
        schema = PrimeraRevisionLiquidacionIn(**data)
        assert schema.observacion == "Test observacion"
        assert schema.revisiones_ids == [rev1, rev2, rev3]

    def test_valor_proyecto_zero_invalid(self):
        """valor_proyecto=0 debe fallar validación (gt=0)."""
        from pydantic import ValidationError
        municipalidad_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 0.0,
        }
        with pytest.raises(ValidationError) as exc_info:
            PrimeraRevisionLiquidacionIn(**data)
        assert "valor_proyecto" in str(exc_info.value)

    def test_valor_proyecto_negative_invalid(self):
        """valor_proyecto negativo debe fallar validación."""
        from pydantic import ValidationError
        municipalidad_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": -100.0,
        }
        with pytest.raises(ValidationError) as exc_info:
            PrimeraRevisionLiquidacionIn(**data)
        assert "valor_proyecto" in str(exc_info.value)

    def test_proyecto_public_id_empty_accepted(self):
        """proyecto_public_id vacío es técnicamente válido según schema actual (sin min_length)."""
        municipalidad_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
        }
        schema = PrimeraRevisionLiquidacionIn(**data)
        assert schema.proyecto_public_id == ""

    def test_revisiones_ids_empty_is_valid(self):
        """revisiones_ids=[] (default) es válido."""
        municipalidad_id = uuid.uuid4()
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
            "revisiones_ids": [],
        }
        schema = PrimeraRevisionLiquidacionIn(**data)
        assert schema.revisiones_ids == []

    def test_revisiones_ids_with_duplicates_valid(self):
        """revisiones_ids puede tener duplicados (validación de negocio)."""
        municipalidad_id = uuid.uuid4()
        rev1 = str(uuid.uuid4())
        rev2 = str(uuid.uuid4())
        data = {
            "proyecto_public_id": "PROY-2026-00001",
            "municipalidad_id": municipalidad_id,
            "tipo_tramite": "OBRA_NUEVA",
            "valor_proyecto": 10000.0,
            "revisiones_ids": [rev1, rev1, rev2, rev2],
        }
        schema = PrimeraRevisionLiquidacionIn(**data)
        assert schema.revisiones_ids == [rev1, rev1, rev2, rev2]


class TestNuevaRevisionLiquidacionIn:
    """Test NuevaRevisionLiquidacionIn schema validation."""

    def test_valid_minimal_input(self):
        """Input con solo campos requeridos debe ser válido."""
        liquidacion_id = uuid.uuid4()
        rev1 = uuid.uuid4()
        rev2 = uuid.uuid4()
        data = {
            "liquidacion_previa_id": liquidacion_id,
            "revisiones_ids": [rev1, rev2],
        }
        schema = NuevaRevisionLiquidacionIn(**data)
        assert schema.liquidacion_previa_id == liquidacion_id
        assert schema.revisiones_ids == [rev1, rev2]

    def test_valid_full_input(self):
        """Input con todos los campos opcionales debe ser válido."""
        liquidacion_id = uuid.uuid4()
        rev4 = uuid.uuid4()
        rev5 = uuid.uuid4()
        data = {
            "liquidacion_previa_id": liquidacion_id,
            "revisiones_ids": [rev4, rev5],
            "observacion": "Segunda revisión",
        }
        schema = NuevaRevisionLiquidacionIn(**data)
        assert schema.liquidacion_previa_id == liquidacion_id
        assert schema.observacion == "Segunda revisión"
        assert schema.revisiones_ids == [rev4, rev5]

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
