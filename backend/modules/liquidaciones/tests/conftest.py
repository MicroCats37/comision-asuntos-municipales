"""
Shared fixtures for liquidaciones integration tests.

Extracted from test_edificaciones_nueva_liquidacion.py to avoid duplication
across multiple test files.
"""
import pytest
from decimal import Decimal
from datetime import date

from ninja.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api
from modules.entidades.domain.models.ubigeo import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.usuarios.domain.models.perfil_ingeniero import Especialidad
from modules.finanzas.domain.models.impuestos import UIT, IGV
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    DerechoPorcentajeObra,
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel


# ── TipoLiquidacion Fixtures ────────────────────────────────────────────────────

@pytest.fixture
def tipo_edificacion(db):
    """Get or create TipoLiquidacion for EDIFICACION."""
    return TipoLiquidacionModel.objects.get_or_create(codigo="EDIFICACION", defaults={"nombre": "Edificaciones"})[0]


@pytest.fixture
def tipo_habilitacion_urbana(db):
    """Get or create TipoLiquidacion for HABILITACION_URBANA."""
    return TipoLiquidacionModel.objects.get_or_create(codigo="HABILITACION_URBANA", defaults={"nombre": "Habilitación Urbana"})[0]


@pytest.fixture
def tipo_mecanica_suelos(db):
    """Get or create TipoLiquidacion for MECANICA_SUELOS."""
    return TipoLiquidacionModel.objects.get_or_create(codigo="MECANICA_SUELOS", defaults={"nombre": "Mecánica de Suelos"})[0]


@pytest.fixture
def tipo_impacto_vial(db):
    """Get or create TipoLiquidacion for IMPACTO_VIAL."""
    return TipoLiquidacionModel.objects.get_or_create(codigo="IMPACTO_VIAL", defaults={"nombre": "Impacto Vial"})[0]


@pytest.fixture
def tipo_taludes(db):
    """Get or create TipoLiquidacion for TALUDES."""
    return TipoLiquidacionModel.objects.get_or_create(codigo="TALUDES", defaults={"nombre": "Taludes"})[0]


@pytest.fixture
def tipo_inspeccion_obra(db):
    """Get or create TipoLiquidacion for INSPECCION_OBRA."""
    return TipoLiquidacionModel.objects.get_or_create(codigo="INSPECCION_OBRA", defaults={"nombre": "Inspección de Obra"})[0]


# ── Core Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def api_client(db):
    """Ninja TestClient for testing Ninja endpoints with proper async handling."""
    return TestClient(api)


@pytest.fixture
def create_user(db):
    """Create a test user (needed for FK to usuarios_usuario on LiquidacionGeneral)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="testuser_edif",
        email="test_edif@example.com",
        password="testpass123",
        dni="12345678",
    )


@pytest.fixture
def auth_client(api_client, create_user):
    """Authenticate the test client using JWT token."""
    user = create_user
    token = AccessToken.for_user(user)
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    api_client.user = user
    return api_client


# ── Ubigeo Fixtures ────────────────────────────────────────────────────────────

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


# ── Entidad Fixtures ────────────────────────────────────────────────────────────

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


# ── Finanzas Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def igv_vigente(db):
    """Create an IGV vigente for testing."""
    return IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def uit_vigente(db):
    """Create a UIT vigente for testing."""
    return UIT.objects.create(
        valor=Decimal("5150.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


# ── Tarifa Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def tarifa_liquidacion_base_edificacion(db, tipo_edificacion):
    """Create a TarifaLiquidacionBase for Edificaciones."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def especialidad_estructuras(db):
    """Create an Especialidad for Edificaciones testing."""
    return Especialidad.objects.create(
        codigo="E01",
        nombre="Estructuras",
    )


@pytest.fixture
def especialidad_arquitectura(db):
    """Create an Especialidad for Edificaciones testing."""
    return Especialidad.objects.create(
        codigo="A01",
        nombre="Arquitectura",
    )


@pytest.fixture
def especialidad_installaciones(db):
    """Create an Especialidad for Edificaciones testing."""
    return Especialidad.objects.create(
        codigo="I01",
        nombre="Instalaciones",
    )


@pytest.fixture
def tarifa_porcentaje_obra_estructuras(db, tarifa_liquidacion_base_edificacion, especialidad_estructuras):
    """Create a TarifaPorcentajeObra for Estructuras."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        especialidad=especialidad_estructuras,
        porcentaje_liquidacion=Decimal("0.0010"),  # 0.10%
    )


@pytest.fixture
def tarifa_porcentaje_obra_arquitectura(db, tarifa_liquidacion_base_edificacion, especialidad_arquitectura):
    """Create a TarifaPorcentajeObra for Arquitectura."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        especialidad=especialidad_arquitectura,
        porcentaje_liquidacion=Decimal("0.0005"),  # 0.05%
    )


@pytest.fixture
def tarifa_porcentaje_obra_installaciones(db, tarifa_liquidacion_base_edificacion, especialidad_installaciones):
    """Create a TarifaPorcentajeObra for Instalaciones."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        especialidad=especialidad_installaciones,
        porcentaje_liquidacion=Decimal("0.0003"),  # 0.03%
    )


@pytest.fixture
def derecho_porcentaje_vigente(db):
    """Create a DerechoPorcentajeObra vigente for testing."""
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


# ── usuario_admin Fixture (alias for create_user) ──────────────────────────────

@pytest.fixture
def usuario_admin(db, create_user):
    """Alias for create_user to match naming convention used in some tests."""
    return create_user


# ── IO (Inspección de Obra) Tarifa Fixtures ──────────────────────────────────

@pytest.fixture
def tarifa_liquidacion_base_io(db, tipo_inspeccion_obra):
    """Create a TarifaLiquidacionBase for Inspección de Obra."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_inspeccion_obra,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_visitas_io(db, tarifa_liquidacion_base_io):
    """Create a TarifaPorCategoriaVisitas for Inspección de Obra testing."""
    return TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=tarifa_liquidacion_base_io,
        porcentaje_uit=Decimal("0.05"),  # 5% of UIT
        categoria_visitas="INSPECCION",
    )
