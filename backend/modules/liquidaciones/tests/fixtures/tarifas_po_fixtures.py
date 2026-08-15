"""
Tarifas PO (PorcentajeObra) fixtures — all PO motor types:
- Edificaciones: tarifa_liquidacion_base_edificacion, especialidades E01/A01/I01, tarifas PO
- Taludes: tarifa_liquidacion_base_taludes, especialidad T01, tarifa_po_taludes
- Impacto Vial: tarifa_liquidacion_base_iv, especialidad IV01, tarifa_po_iv
Plus: derecho_porcentaje_vigente (shared by all PO types)

Re-exports (via conftest): tarifa_liquidacion_base_edificacion,
    especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones,
    tarifa_porcentaje_obra_estructuras, tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones, especialidades_disponibles_edificacion,
    derecho_porcentaje_vigente,
    tarifa_liquidacion_base_taludes, especialidad_taludes, tarifa_porcentaje_obra_taludes,
    tarifa_liquidacion_base_iv, especialidad_impacto_vial, tarifa_porcentaje_obra_iv
"""
import pytest
from decimal import Decimal
from datetime import date
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    DerechoPorcentajeObra,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionEspecialidadDisponibles,
)


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
    """Create an EspecialidadRevision for Edificaciones testing."""
    return EspecialidadRevision.objects.create(
        codigo="E01",
        slug="estructuras",
        nombre="Estructuras",
    )


@pytest.fixture
def especialidad_arquitectura(db):
    """Create an EspecialidadRevision for Edificaciones testing."""
    return EspecialidadRevision.objects.create(
        codigo="A01",
        slug="arquitectura",
        nombre="Arquitectura",
    )


@pytest.fixture
def especialidad_installaciones(db):
    """Create an EspecialidadRevision for Edificaciones testing."""
    return EspecialidadRevision.objects.create(
        codigo="I01",
        slug="instalaciones",
        nombre="Instalaciones",
    )


@pytest.fixture
def tarifa_porcentaje_obra_estructuras(db, tarifa_liquidacion_base_edificacion):
    """Create a TarifaPorcentajeObra (tarifa única por base, sin especialidad FK).

    La especialidad se pasa explícitamente en el input; el modelo ya no tiene FK especialidad.
    """
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        porcentaje_liquidacion=Decimal("0.0010"),  # 0.10%
    )


@pytest.fixture
def tarifa_porcentaje_obra_arquitectura(db, tarifa_liquidacion_base_edificacion):
    """Create a TarifaPorcentajeObra for Arquitectura (0.05%)."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        porcentaje_liquidacion=Decimal("0.0005"),  # 0.05%
    )


@pytest.fixture
def tarifa_porcentaje_obra_installaciones(db, tarifa_liquidacion_base_edificacion):
    """Create a TarifaPorcentajeObra for Instalaciones (0.03%)."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_edificacion,
        porcentaje_liquidacion=Decimal("0.0003"),  # 0.03%
    )


@pytest.fixture
def especialidades_disponibles_edificacion(
    db, tipo_edificacion, especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones
):
    """Create LiquidacionEspecialidadDisponibles for the 3 especialidades of Edificaciones.

    Required for auto-fill mode: the orchestrator combines vigentes tarifas x
    vigentes especialidades when the input tarifas list is empty.
    """
    return [
        LiquidacionEspecialidadDisponibles.objects.create(
            tipo_liquidacion=tipo_edificacion,
            especialidad=esp,
            activo=True,
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=None,
        )
        for esp in [especialidad_estructuras, especialidad_arquitectura, especialidad_installaciones]
    ]


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


# ── Taludes fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def tarifa_liquidacion_base_taludes(db, tipo_taludes):
    """Create a TarifaLiquidacionBase for Taludes."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_taludes,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def especialidad_taludes(db):
    """Create an EspecialidadRevision for Taludes testing."""
    return EspecialidadRevision.objects.create(
        codigo="T01",
        slug="taludes",
        nombre="Taludes",
    )


@pytest.fixture
def tarifa_porcentaje_obra_taludes(db, tarifa_liquidacion_base_taludes):
    """Create a TarifaPorcentajeObra for Taludes (sin especialidad — tarifa única por base)."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_taludes,
        porcentaje_liquidacion=Decimal("0.0010"),  # 0.10%
    )


# ── Impacto Vial fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def tarifa_liquidacion_base_iv(db, tipo_impacto_vial):
    """Create a TarifaLiquidacionBase for Impacto Vial."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_impacto_vial,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def especialidad_impacto_vial(db):
    """Create an EspecialidadRevision for Impacto Vial testing."""
    return EspecialidadRevision.objects.create(
        codigo="IV01",
        slug="impacto-vial",
        nombre="Impacto Vial",
    )


@pytest.fixture
def tarifa_porcentaje_obra_iv(db, tarifa_liquidacion_base_iv):
    """Create a TarifaPorcentajeObra for Impacto Vial (sin especialidad — tarifa única por base)."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base_iv,
        porcentaje_liquidacion=Decimal("0.0010"),  # 0.10%
    )
