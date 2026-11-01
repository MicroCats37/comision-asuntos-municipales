"""
Catálogo histórico para el REGISTRO MANUAL LEGACY (Fase 3 del change
`registro-liquidaciones-legacy`).

El periodo de referencia es 2023-01-01 → 2023-12-31, ANTERIOR y DISCRETO del
periodo de los catálogos compartidos (`tests/fixtures/tarifas_*_fixtures.py` y
`tests/fixtures/finanzas_fixtures.py`, que viven en 2024-01-01 → sin fin).
Gracias a eso:

- ambos catálogos conviven en la misma base de datos de test sin solaparse;
- la resolución por fecha del resolver canónico
  (`LiquidacionHistoricoCoreService`) es determinista;
- el test puede demostrar que el registro legacy usa los valores de SU fecha
  (2023) y NO los de hoy (2024+).

Los valores son deliberadamente DISTINTOS de los compartidos (UIT 4950 vs
5150, tarifa PO 0.20 % vs 0.10 %, costo M2 100 vs 150) para que una resolución
con la fecha equivocada sea visible en las aserciones.

Las especialidades históricas son filas PROPIAS (slug propio) porque
`LiquidacionEspecialidadDisponibles` declara
`UniqueConstraint(tipo_liquidacion, especialidad)`: este catálogo puede
pedirse junto a los compartidos sin violar la restricción.

Este módulo SOLO define fixtures. Los payload builders viven en
`tests/fixtures/factories.py` (funciones puras, sin DB).
"""
import pytest
from datetime import date
from decimal import Decimal

from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionEspecialidadDisponibles,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorMetroCuadrado,
    DerechoPorcentajeObra,
    TarifaLiquidacionBase,
    TarifaPorCategoriaVisitas,
    TarifaPorMetroCuadrado,
    TarifaPorcentajeObra,
)
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision


# ── Constantes del periodo histórico ────────────────────────────────────────

FECHA_LEGACY_HISTORICA = date(2023, 6, 15)

PERIODO_HISTORICO_INICIO = date(2023, 1, 1)
PERIODO_HISTORICO_FIN = date(2023, 12, 31)

IGV_HISTORICO = Decimal("0.18")
UIT_HISTORICO = 4950

TARIFA_PO_HISTORICA = Decimal("0.0020")  # 0.20 %
DERECHO_PO_MINIMO = Decimal("500.00")
DERECHO_PO_MAXIMO = Decimal("50000.00")
DERECHO_PO_MINIMO_UIT = Decimal("0.10")

COSTO_M2_HU_HISTORICO = Decimal("100.0000")
COSTO_M2_MS_HISTORICO = Decimal("120.0000")
DERECHO_M2_MINIMO = Decimal("500.00")
DERECHO_M2_MAXIMO = Decimal("50000.00")

PORCENTAJE_UIT_VISITAS_HISTORICO = Decimal("0.05")
CATEGORIA_VISITAS_HISTORICA = "INSPECCION"


# ── Fecha de referencia ─────────────────────────────────────────────────────

@pytest.fixture
def fecha_registro_historica():
    """Fecha efectiva de referencia del catálogo histórico (constante de test)."""
    return FECHA_LEGACY_HISTORICA


# ── Variables financieras históricas ─────────────────────────────────────────

@pytest.fixture
def igv_historico_2023(db):
    """IGV vigente durante 2023 (0.18)."""
    return IGV.objects.create(
        valor=IGV_HISTORICO,
        periodo_inicio=PERIODO_HISTORICO_INICIO,
        periodo_fin=PERIODO_HISTORICO_FIN,
    )


@pytest.fixture
def uit_historico_2023(db):
    """UIT vigente durante 2023 (4950.00) — distinto del vigente de hoy (5150.00)."""
    return UIT.objects.create(
        valor=UIT_HISTORICO,
        periodo_inicio=PERIODO_HISTORICO_INICIO,
        periodo_fin=PERIODO_HISTORICO_FIN,
    )


# ── Derechos históricos ─────────────────────────────────────────────────────

@pytest.fixture
def derecho_porcentaje_historico_2023(db):
    """DerechoPorcentajeObra vigente durante 2023 (motor PorcentajeObra)."""
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=DERECHO_PO_MINIMO,
        derecho_maximo=DERECHO_PO_MAXIMO,
        porcentaje_minimo_uit=DERECHO_PO_MINIMO_UIT,
        periodo_inicio=PERIODO_HISTORICO_INICIO,
        periodo_fin=PERIODO_HISTORICO_FIN,
    )


@pytest.fixture
def derecho_m2_historico_2023(db):
    """DerechoPorMetroCuadrado vigente durante 2023 (motor Por Metro Cuadrado)."""
    return DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=DERECHO_M2_MINIMO,
        derecho_maximo=DERECHO_M2_MAXIMO,
        periodo_inicio=PERIODO_HISTORICO_INICIO,
        periodo_fin=PERIODO_HISTORICO_FIN,
    )


# ── Catálogo PO histórico (Edificaciones / Taludes / Impacto Vial) ──────────

@pytest.fixture
def especialidad_historica_edificaciones(db):
    """Especialidades PROPIAS del catálogo histórico de Edificaciones.

    Filas propias (no las compartidas) para no violar el
    `UniqueConstraint(tipo_liquidacion, especialidad)` de
    `LiquidacionEspecialidadDisponibles`.
    """
    return [
        EspecialidadRevision.objects.create(slug=slug, nombre=nombre)
        for slug, nombre in [
            ("estructuras-historico", "Estructuras (histórico)"),
            ("arquitectura-historico", "Arquitectura (histórico)"),
            ("instalaciones-historico", "Instalaciones (histórico)"),
        ]
    ]


@pytest.fixture
def especialidades_disponibles_historicas_edificacion(
    db, tipo_edificacion, especialidad_historica_edificaciones
):
    """Habilitadas del catálogo de Edificaciones vigentes durante 2023 (H = 3)."""
    return [
        LiquidacionEspecialidadDisponibles.objects.create(
            tipo_liquidacion=tipo_edificacion,
            especialidad=esp,
            activo=True,
            periodo_inicio=PERIODO_HISTORICO_INICIO,
            periodo_fin=PERIODO_HISTORICO_FIN,
        )
        for esp in especialidad_historica_edificaciones
    ]


@pytest.fixture
def tarifa_base_po_historica_edificacion(db, tipo_edificacion):
    """TarifaLiquidacionBase de Edificaciones vigente durante 2023."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=PERIODO_HISTORICO_INICIO,
        periodo_fin=PERIODO_HISTORICO_FIN,
    )


@pytest.fixture
def tarifa_po_historica_edificacion(db, tarifa_base_po_historica_edificacion):
    """TarifaPorcentajeObra de Edificaciones vigente durante 2023 (0.20 %)."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_po_historica_edificacion,
        porcentaje_liquidacion=TARIFA_PO_HISTORICA,
    )


@pytest.fixture
def especialidad_historica_taludes(db):
    """Especialidad PROPIA del catálogo histórico de Taludes."""
    return EspecialidadRevision.objects.create(
        slug="taludes-historico",
        nombre="Taludes (histórico)",
    )


@pytest.fixture
def especialidad_disponible_historica_taludes(
    db, tipo_taludes, especialidad_historica_taludes
):
    """Habilitada del catálogo de Taludes vigente durante 2023 (H = 1)."""
    return LiquidacionEspecialidadDisponibles.objects.create(
        tipo_liquidacion=tipo_taludes,
        especialidad=especialidad_historica_taludes,
        activo=True,
        periodo_inicio=PERIODO_HISTORICO_INICIO,
        periodo_fin=PERIODO_HISTORICO_FIN,
    )


@pytest.fixture
def tarifa_base_po_historica_taludes(db, tipo_taludes):
    """TarifaLiquidacionBase de Taludes vigente durante 2023."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_taludes,
        periodo_inicio=PERIODO_HISTORICO_INICIO,
        periodo_fin=PERIODO_HISTORICO_FIN,
    )


@pytest.fixture
def tarifa_po_historica_taludes(db, tarifa_base_po_historica_taludes):
    """TarifaPorcentajeObra de Taludes vigente durante 2023 (0.20 %)."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_po_historica_taludes,
        porcentaje_liquidacion=TARIFA_PO_HISTORICA,
    )


@pytest.fixture
def especialidad_historica_impacto_vial(db):
    """Especialidad PROPIA del catálogo histórico de Impacto Vial."""
    return EspecialidadRevision.objects.create(
        slug="impacto-vial-historico",
        nombre="Impacto Vial (histórico)",
    )


@pytest.fixture
def especialidad_disponible_historica_impacto_vial(
    db, tipo_impacto_vial, especialidad_historica_impacto_vial
):
    """Habilitada del catálogo de Impacto Vial vigente durante 2023 (H = 1)."""
    return LiquidacionEspecialidadDisponibles.objects.create(
        tipo_liquidacion=tipo_impacto_vial,
        especialidad=especialidad_historica_impacto_vial,
        activo=True,
        periodo_inicio=PERIODO_HISTORICO_INICIO,
        periodo_fin=PERIODO_HISTORICO_FIN,
    )


@pytest.fixture
def tarifa_base_po_historica_impacto_vial(db, tipo_impacto_vial):
    """TarifaLiquidacionBase de Impacto Vial vigente durante 2023."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_impacto_vial,
        periodo_inicio=PERIODO_HISTORICO_INICIO,
        periodo_fin=PERIODO_HISTORICO_FIN,
    )


@pytest.fixture
def tarifa_po_historica_impacto_vial(db, tarifa_base_po_historica_impacto_vial):
    """TarifaPorcentajeObra de Impacto Vial vigente durante 2023 (0.20 %)."""
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_base_po_historica_impacto_vial,
        porcentaje_liquidacion=TARIFA_PO_HISTORICA,
    )


# ── Catálogo M2 histórico (Habilitación Urbana / Mecánica de Suelos) ───────

@pytest.fixture
def tarifa_base_m2_historica_habilitacion_urbana(db, tipo_habilitacion_urbana):
    """TarifaLiquidacionBase de Habilitación Urbana vigente durante 2023."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=PERIODO_HISTORICO_INICIO,
        periodo_fin=PERIODO_HISTORICO_FIN,
    )


@pytest.fixture
def tarifa_m2_historica_habilitacion_urbana(
    db, tarifa_base_m2_historica_habilitacion_urbana
):
    """TarifaPorMetroCuadrado de Habilitación Urbana vigente durante 2023 (100.00/m²)."""
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_m2_historica_habilitacion_urbana,
        costo_por_m2=COSTO_M2_HU_HISTORICO,
    )


@pytest.fixture
def tarifa_base_m2_historica_mecanica_suelos(db, tipo_mecanica_suelos):
    """TarifaLiquidacionBase de Mecánica de Suelos vigente durante 2023."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio=PERIODO_HISTORICO_INICIO,
        periodo_fin=PERIODO_HISTORICO_FIN,
    )


@pytest.fixture
def tarifa_m2_historica_mecanica_suelos(db, tarifa_base_m2_historica_mecanica_suelos):
    """TarifaPorMetroCuadrado de Mecánica de Suelos vigente durante 2023 (120.00/m²)."""
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_m2_historica_mecanica_suelos,
        costo_por_m2=COSTO_M2_MS_HISTORICO,
    )


# ── Catálogo de visitas histórico (Inspección de Obra) ──────────────────────

@pytest.fixture
def tarifa_base_visitas_historica_inspeccion_obra(db, tipo_inspeccion_obra):
    """TarifaLiquidacionBase de Inspección de Obra vigente durante 2023."""
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_inspeccion_obra,
        periodo_inicio=PERIODO_HISTORICO_INICIO,
        periodo_fin=PERIODO_HISTORICO_FIN,
    )


@pytest.fixture
def tarifa_visitas_historica_inspeccion_obra(
    db, tarifa_base_visitas_historica_inspeccion_obra
):
    """TarifaPorCategoriaVisitas de Inspección de Obra vigente durante 2023 (5 % UIT)."""
    return TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=tarifa_base_visitas_historica_inspeccion_obra,
        porcentaje_uit=PORCENTAJE_UIT_VISITAS_HISTORICO,
        categoria_visitas=CATEGORIA_VISITAS_HISTORICA,
    )


# ── Catálogo compuesto ──────────────────────────────────────────────────────

@pytest.fixture
def catalogo_legacy_historico(
    db,
    fecha_registro_historica,
    igv_historico_2023,
    uit_historico_2023,
    derecho_porcentaje_historico_2023,
    derecho_m2_historico_2023,
    tarifa_po_historica_edificacion,
    especialidades_disponibles_historicas_edificacion,
    tarifa_po_historica_taludes,
    especialidad_disponible_historica_taludes,
    tarifa_po_historica_impacto_vial,
    especialidad_disponible_historica_impacto_vial,
    tarifa_m2_historica_habilitacion_urbana,
    tarifa_m2_historica_mecanica_suelos,
    tarifa_visitas_historica_inspeccion_obra,
):
    """Catálogo histórico completo de los seis motores para el registro legacy.

    Devuelve un dict con todas las piezas del catálogo en la fecha de
    referencia, para que los tests de los seis tipos compartan un único
    setup cohesivo (mismo patrón que `po_base_setup` / `m2_base_setup`).
    """
    return {
        "fecha_registro": fecha_registro_historica,
        "igv": igv_historico_2023,
        "uit": uit_historico_2023,
        "derecho_porcentaje": derecho_porcentaje_historico_2023,
        "derecho_m2": derecho_m2_historico_2023,
        "tarifa_po_edificacion": tarifa_po_historica_edificacion,
        "especialidades_edificacion": especialidades_disponibles_historicas_edificacion,
        "tarifa_po_taludes": tarifa_po_historica_taludes,
        "tarifa_po_impacto_vial": tarifa_po_historica_impacto_vial,
        "tarifa_m2_habilitacion_urbana": tarifa_m2_historica_habilitacion_urbana,
        "tarifa_m2_mecanica_suelos": tarifa_m2_historica_mecanica_suelos,
        "tarifa_visitas_inspeccion_obra": tarifa_visitas_historica_inspeccion_obra,
    }
