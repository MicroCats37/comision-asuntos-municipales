"""
Unit tests for simulators — SunatClientSimulator and ReniecClientSimulator.

Tests both "found" and "generated" scenarios for each simulator.
"""
import pytest

from modules.entidades.infrastructure.services import (
    SunatClientSimulator,
    ReniecClientSimulator,
)


class TestSunatClientSimulator:
    """Test SunatClientSimulator methods."""

    def setup_method(self):
        """Set up test data."""
        self.simulator = SunatClientSimulator()

    @pytest.mark.asyncio
    async def test_get_institucion_returns_data_for_hardcoded_ruc(self):
        """
        get_institucion(ruc) should return SunatInstitucionResult for a hardcoded RUC.
        """
        result = await self.simulator.get_institucion("20492913151")

        assert result.ruc == "20492913151"
        assert result.razon_social == "MUNICIPALIDAD PROVINCIAL DE LIMA"
        assert result.nombre_comercial == "MPL"
        assert result.estado == "ACTIVO"
        assert result.tipo_contribuyente == "GOBIERNO LOCAL"
        assert result.direccion == "AV. PCM S/N"
        assert result.departamento == "LIMA"
        assert result.provincia == "LIMA"
        assert result.distrito == "LIMA"

    @pytest.mark.asyncio
    async def test_get_institucion_returns_data_for_another_hardcoded_ruc(self):
        """
        get_institucion(ruc) should return correct data for another hardcoded CIP RUC.
        """
        result = await self.simulator.get_institucion("20131312957")

        assert result.ruc == "20131312957"
        assert result.razon_social == "COLEGIO DE INGENIEROS DEL PERU"
        assert result.estado == "ACTIVO"

    @pytest.mark.asyncio
    async def test_get_institucion_generates_data_for_arbitrary_valid_ruc(self):
        """
        get_institucion(ruc) should return generated data for any 11-digit RUC
        not in the hardcoded list.
        """
        # Use a RUC that is NOT in _SIMULADOS
        arbitrary_ruc = "10512345678"
        result = await self.simulator.get_institucion(arbitrary_ruc)

        assert result.ruc == arbitrary_ruc
        assert result.razon_social is not None
        assert result.nombre_comercial is not None
        assert result.estado is not None
        assert result.departamento is not None
        assert result.provincia is not None
        assert result.distrito is not None

    @pytest.mark.asyncio
    async def test_get_institucion_returns_deterministic_data_for_same_ruc(self):
        """
        get_institucion(ruc) should return the same data when called multiple
        times with the same RUC (deterministic generation).
        """
        arbitrary_ruc = "10987654321"

        result1 = await self.simulator.get_institucion(arbitrary_ruc)
        result2 = await self.simulator.get_institucion(arbitrary_ruc)
        result3 = await self.simulator.get_institucion(arbitrary_ruc)

        # All three calls should return identical data
        assert result1.ruc == result2.ruc == result3.ruc == arbitrary_ruc
        assert result1.razon_social == result2.razon_social == result3.razon_social
        assert result1.nombre_comercial == result2.nombre_comercial == result3.nombre_comercial
        assert result1.estado == result2.estado == result3.estado
        assert result1.direccion == result2.direccion == result3.direccion


class TestReniecClientSimulator:
    """Test ReniecClientSimulator methods."""

    def setup_method(self):
        """Set up test data."""
        self.simulator = ReniecClientSimulator()

    @pytest.mark.asyncio
    async def test_get_persona_returns_data_for_hardcoded_dni(self):
        """
        get_persona(dni) should return ReniecPersonaResult for a hardcoded DNI.
        """
        result = await self.simulator.get_persona("45406196")

        assert result.dni == "45406196"
        assert result.nombres == "DENNIS JOEL"
        assert result.apellidos == "ZARATE TORRES"
        assert result.nombre_completo == "ZARATE TORRES, DENNIS JOEL"
        assert result.genero == "M"
        assert result.fecha_nacimiento.year == 1986
        assert result.fecha_nacimiento.month == 8
        assert result.fecha_nacimiento.day == 24

    @pytest.mark.asyncio
    async def test_get_persona_returns_data_for_female_hardcoded_dni(self):
        """
        get_persona(dni) should return correct data for female hardcoded DNI.
        """
        result = await self.simulator.get_persona("87654321")

        assert result.dni == "87654321"
        assert result.nombres == "MARIA ELENA"
        assert result.apellidos == "LOPEZ SANCHEZ"
        assert result.genero == "F"

    @pytest.mark.asyncio
    async def test_get_persona_generates_data_for_arbitrary_valid_dni(self):
        """
        get_persona(dni) should return generated data for any 8-digit DNI
        not in the hardcoded list.
        """
        # Use a DNI that is NOT in _SIMULADOS
        arbitrary_dni = "12345678"
        result = await self.simulator.get_persona(arbitrary_dni)

        assert result.dni == arbitrary_dni
        assert result.nombres is not None
        assert result.apellidos is not None
        assert result.nombre_completo is not None
        assert result.genero is not None
        assert result.fecha_nacimiento is not None
        assert result.ubigeo is not None

    @pytest.mark.asyncio
    async def test_get_persona_returns_deterministic_data_for_same_dni(self):
        """
        get_persona(dni) should return the same data when called multiple
        times with the same DNI (deterministic generation).
        """
        arbitrary_dni = "11223344"

        result1 = await self.simulator.get_persona(arbitrary_dni)
        result2 = await self.simulator.get_persona(arbitrary_dni)
        result3 = await self.simulator.get_persona(arbitrary_dni)

        # All three calls should return identical data
        assert result1.dni == result2.dni == result3.dni == arbitrary_dni
        assert result1.nombres == result2.nombres == result3.nombres
        assert result1.apellidos == result2.apellidos == result3.apellidos
        assert result1.nombre_completo == result2.nombre_completo == result3.nombre_completo
        assert result1.genero == result2.genero == result3.genero
        assert result1.fecha_nacimiento == result2.fecha_nacimiento == result3.fecha_nacimiento
        assert result1.direccion == result2.direccion == result3.direccion
