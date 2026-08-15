"""
Ubigeo fixtures — department, province, district, municipalidad, proyecto.

Re-exports: ubigeo_departamento, ubigeo_provincia, ubigeo_distrito, municipalidad, proyecto
"""
import pytest
from modules.entidades.domain.models.ubigeo import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.liquidaciones.domain.models.proyecto import Proyecto


@pytest.fixture
def ubigeo_departamento(db):
    """Create a department for testing."""
    return UbigeoDepartamento.objects.create(nombre="LIMA")


@pytest.fixture
def ubigeo_provincia(db, ubigeo_departamento):
    """Create a province for testing."""
    return UbigeoProvincia.objects.create(
        departamento=ubigeo_departamento,
        nombre="LIMA",
    )


@pytest.fixture
def ubigeo_distrito(db, ubigeo_provincia):
    """Create a district for testing."""
    return UbigeoDistrito.objects.create(
        provincia=ubigeo_provincia,
        nombre="MIRAFLORES",
        ubigeo="150132",
    )


@pytest.fixture
def municipalidad(db, ubigeo_distrito):
    """Create a municipalidad for testing."""
    return Municipalidad.objects.create(
        codigo="M001",
        nombre="Municipalidad de Miraflores",
        distrito=ubigeo_distrito,
    )


@pytest.fixture
def proyecto(db, municipalidad, ubigeo_distrito):
    """Create a proyecto for testing."""
    return Proyecto.objects.create(
        denominacion="Proyecto Test Edificaciones",
        nombre_propietario="Propietario Test SAC",
        direccion="Av. Test 123",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789012",
        entidad_razon_social="Propietario Test SAC",
    )
