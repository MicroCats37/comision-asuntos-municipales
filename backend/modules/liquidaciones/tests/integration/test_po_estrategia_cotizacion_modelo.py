"""
Integration tests — modelo de estrategias de cotización PO (PorcentajeObra).

Change: liquidacion-po-modos-cotizacion — Module 2 (Modelo y migraciones).

Cubre el modelo persistido de las tres estrategias de cotización del motor PO:

1. `EstrategiaCotizacionPO` expone EXACTAMENTE tres estrategias canónicas
   (sin un cuarto modo, sin alias, sin porcentaje configurable ni estrategia
   de subtotal fijo).
2. `LiquidacionPorcentajeObra.estrategia_cotizacion` tiene default
   `NORMAL_SELECCIONADAS`: toda PO preexistente queda en modo normal.
3. Los snapshots (`count_habilitadas`, `total_explicito`, `porcentaje_tarifa`,
   `tarifa_aplicada`) nacen NULL — retro-compatible con el catálogo vigente.
4. `LiquidacionPorcentajeObraAcumulacion` es OneToOne con el PO, tiene
   `porcentaje_acumulado` nullable y `subtotal_acumulado` obligatorio, y NO
   tiene historial propio ni campos de destino/reparto.
5. El backfill de la migración `0010_backfill_estrategia_cotizacion_po` deja
   toda PO existente en `NORMAL_SELECCIONADAS` y NO crea filas de acumulación.

Sin mocks, sin directorio `unit/` (contract/TEST_ARCHITECTURE_CONTRACT.md).
"""
import importlib
from decimal import Decimal

import pytest
from django.apps import apps as django_apps
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from modules.liquidaciones.domain.constants import (
    EstadoLiquidacion,
    EstrategiaCotizacionPO,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraAcumulacion,
)


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def po_modelo(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tipo_edificacion,
):
    """
    PO (PorcentajeObra) de Edificaciones persistido sin estrategia explícita.

    Reproduce el estado de una liquidación creada ANTES de las estrategias:
    el motor guardaba sólo el padre y sus detalles.
    """
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-PO-MOD-001",
        observacion="Test modelo de estrategias PO",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("515.00"),
        total=Decimal("607.70"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

    return LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0030"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _modulo_backfill():
    """Carga la migración de backfill por su ruta (el nombre empieza con dígito)."""
    return importlib.import_module(
        "modules.liquidaciones.migrations.0010_backfill_estrategia_cotizacion_po"
    )


class _ConexionFalsa:
    alias = "default"


class _SchemaEditorFalso:
    """Schema editor mínimo: el RunPython sólo usa `connection.alias`."""

    connection = _ConexionFalsa()


def _aplicar_backfill():
    """Ejecuta la función de backfill de la migración 0010 contra la BD real."""
    _modulo_backfill().backfill_estrategia_cotizacion_po(
        django_apps, _SchemaEditorFalso()
    )


# ── Tests: enum canónico ───────────────────────────────────────────────────────

def test_estrategia_cotizacion_expone_exactamente_tres_estrategias():
    """
    GIVEN: el enum `EstrategiaCotizacionPO`
    WHEN:  se inspeccionan sus valores
    THEN:  expone exactamente las tres estrategias canónicas, en orden, y no
           existe un cuarto modo ni alias (saldo, subtotal fijo, porcentaje).
    """
    assert list(EstrategiaCotizacionPO.values) == [
        "NORMAL_SELECCIONADAS",
        "TARIFA_HABILITADAS_PARTICIPANTES",
        "TOTAL_EXPLICITO",
    ]
    assert len(EstrategiaCotizacionPO) == 3

    for prohibido in ("SALDO", "SUBTOTAL_FIJO", "PORCENTAJE", "CUSTOM"):
        assert not any(
            prohibido in valor for valor in EstrategiaCotizacionPO.values
        ), f"Estrategia no permitida en el enum canonico: {prohibido}"


# ── Tests: default y validación de la estrategia ──────────────────────────────

@pytest.mark.django_db
def test_po_nace_con_estrategia_normal_seleccionadas(po_modelo):
    """
    GIVEN: un PO creado sin especificar estrategia
    WHEN:  se persiste
    THEN:  `estrategia_cotizacion` vale NORMAL_SELECCIONADAS (mismo valor que
           aplica el backfill a las PO preexistentes).
    """
    assert po_modelo.estrategia_cotizacion == EstrategiaCotizacionPO.NORMAL_SELECCIONADAS

    campo = LiquidacionPorcentajeObra._meta.get_field("estrategia_cotizacion")
    assert campo.default == EstrategiaCotizacionPO.NORMAL_SELECCIONADAS
    assert campo.null is False
    assert campo.max_length >= len("TARIFA_HABILITADAS_PARTICIPANTES")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "estrategia",
    [
        EstrategiaCotizacionPO.NORMAL_SELECCIONADAS,
        EstrategiaCotizacionPO.TARIFA_HABILITADAS_PARTICIPANTES,
        EstrategiaCotizacionPO.TOTAL_EXPLICITO,
    ],
)
def test_persiste_las_tres_estrategias(po_modelo, estrategia):
    """
    GIVEN: un PO persistido
    WHEN:  se le asigna cada una de las tres estrategias canónicas
    THEN:  la estrategia se persiste y se relee sin cambios.
    """
    po_modelo.estrategia_cotizacion = estrategia
    po_modelo.save()

    po_modelo.refresh_from_db()
    assert po_modelo.estrategia_cotizacion == estrategia


@pytest.mark.django_db
def test_estrategia_cotizacion_rechaza_valores_fuera_del_enum(po_modelo):
    """
    GIVEN: un PO persistido
    WHEN:  se asigna una estrategia que no pertenece al enum
    THEN:  la validación del modelo la rechaza (no se persiste un estado inválido).
    """
    po_modelo.estrategia_cotizacion = "SUBTOTAL_FIJO"

    with pytest.raises(ValidationError):
        po_modelo.full_clean()


# ── Tests: snapshots ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_snapshots_nacen_null_para_po_historico(po_modelo):
    """
    GIVEN: un PO creado como lo heredaban las liquidaciones históricas
    WHEN:  se inspeccionan los snapshots nuevos
    THEN:  todos son NULL — el motor deriva H del catálogo y no inventa
           total explícito, porcentaje unitario ni tarifa padre.
    """
    assert po_modelo.count_habilitadas is None
    assert po_modelo.total_explicito is None
    assert po_modelo.porcentaje_tarifa is None
    assert po_modelo.tarifa_aplicada is None


def test_campos_de_estrategia_y_snapshot_en_el_modelo():
    """
    GIVEN: el modelo `LiquidacionPorcentajeObra`
    WHEN:  se inspecciona su metamodelo
    THEN:  expone los cinco campos nuevos con la nulabilidad del artefacto
           (estrategia NOT NULL; snapshots nullable).
    """
    meta = LiquidacionPorcentajeObra._meta

    assert meta.get_field("estrategia_cotizacion").null is False

    for nombre in (
        "count_habilitadas",
        "total_explicito",
        "porcentaje_tarifa",
        "tarifa_aplicada",
    ):
        assert meta.get_field(nombre).null is True, f"{nombre} debe ser nullable"


# ── Tests: acumulación OneToOne ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_acumulacion_es_one_to_one_con_el_po(po_modelo):
    """
    GIVEN: un PO con una fila de acumulación
    WHEN:  se intenta crear una segunda fila para el mismo PO
    THEN:  la base de datos lo rechaza (relación 1:1 real, no 1:N).
    """
    LiquidacionPorcentajeObraAcumulacion.objects.create(
        liquidacion_porcentaje=po_modelo,
        porcentaje_acumulado=Decimal("0.0010"),
        subtotal_acumulado=Decimal("100.00"),
    )

    po = LiquidacionPorcentajeObra.objects.get(id=po_modelo.id)
    assert po.acumulacion.subtotal_acumulado == Decimal("100.00")
    assert po.acumulacion.porcentaje_acumulado == Decimal("0.0010")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LiquidacionPorcentajeObraAcumulacion.objects.create(
                liquidacion_porcentaje=po_modelo,
                porcentaje_acumulado=Decimal("0.0010"),
                subtotal_acumulado=Decimal("50.00"),
            )


@pytest.mark.django_db
def test_acumulacion_admite_porcentaje_null(po_modelo):
    """
    GIVEN: un PO en modo TOTAL_EXPLICITO
    WHEN:  se persiste su acumulación sin porcentaje (el total es autoritativo)
    THEN:  el porcentaje acumulado es NULL y el subtotal acumulado se guarda.
    """
    acumulacion = LiquidacionPorcentajeObraAcumulacion.objects.create(
        liquidacion_porcentaje=po_modelo,
        porcentaje_acumulado=None,
        subtotal_acumulado=Decimal("100.00"),
    )

    assert acumulacion.porcentaje_acumulado is None
    assert acumulacion.subtotal_acumulado == Decimal("100.00")

    po = LiquidacionPorcentajeObra.objects.get(id=po_modelo.id)
    assert po.acumulacion.porcentaje_acumulado is None


@pytest.mark.django_db
def test_acumulacion_exige_subtotal_acumulado(po_modelo):
    """
    GIVEN: un PO
    WHEN:  se intenta persistir una acumulación sin subtotal acumulado
    THEN:  la base de datos lo rechaza (el subtotal es obligatorio).
    """
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LiquidacionPorcentajeObraAcumulacion.objects.create(
                liquidacion_porcentaje=po_modelo,
                porcentaje_acumulado=Decimal("0.0010"),
                subtotal_acumulado=None,
            )


@pytest.mark.django_db
def test_po_en_modo_normal_no_tiene_acumulacion(po_modelo):
    """
    GIVEN: un PO en modo NORMAL_SELECCIONADAS
    WHEN:  se consulta su acumulación
    THEN:  no existe fila de acumulación (invariante I-4: el modo normal nunca
           acumula).
    """
    assert not LiquidacionPorcentajeObraAcumulacion.objects.filter(
        liquidacion_porcentaje=po_modelo
    ).exists()

    with pytest.raises(LiquidacionPorcentajeObraAcumulacion.DoesNotExist):
        po_modelo.acumulacion


def test_acumulacion_no_tiene_historial_propio_ni_campos_de_destino():
    """
    GIVEN: el modelo `LiquidacionPorcentajeObraAcumulacion`
    WHEN:  se inspecciona su definición
    THEN:  no tiene `HistoricalRecords` propios y sus campos concretos son
           exactamente los del artefacto — sin campos de destino ni reparto.
    """
    assert not hasattr(LiquidacionPorcentajeObraAcumulacion, "history")

    campos = {
        campo.name
        for campo in LiquidacionPorcentajeObraAcumulacion._meta.get_fields()
        if campo.concrete
    }
    assert campos == {
        "id",
        "created_at",
        "updated_at",
        "liquidacion_porcentaje",
        "porcentaje_acumulado",
        "subtotal_acumulado",
    }


# ── Tests: exports y admin ─────────────────────────────────────────────────────

def test_acumulacion_esta_exportada_y_registrada_en_admin():
    """
    GIVEN: el nuevo modelo de acumulación
    WHEN:  se importan los re-exports del módulo y se consulta el admin
    THEN:  está exportado en los tres niveles de re-export y registrado en el
           admin (como wrapper oculto, igual que el resto de wrappers PO).
    """
    from modules.liquidaciones.models import (
        LiquidacionPorcentajeObraAcumulacion as ExportRoot,
    )
    from modules.liquidaciones.domain.models import (
        LiquidacionPorcentajeObraAcumulacion as ExportDomain,
    )
    from modules.liquidaciones.domain.models.liquidacion import (
        LiquidacionPorcentajeObraAcumulacion as ExportLiquidacion,
    )

    assert ExportRoot is LiquidacionPorcentajeObraAcumulacion
    assert ExportDomain is LiquidacionPorcentajeObraAcumulacion
    assert ExportLiquidacion is LiquidacionPorcentajeObraAcumulacion

    assert admin.site.is_registered(LiquidacionPorcentajeObraAcumulacion)


# ── Tests: backfill ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_backfill_deja_las_po_existentes_en_normal_seleccionadas(po_modelo):
    """
    GIVEN: una PO existente (creada antes de las estrategias)
    WHEN:  se aplica el backfill de la migración 0010
    THEN:  queda en NORMAL_SELECCIONADAS y NO se crea ninguna fila de
           acumulación (invariante I-5).
    """
    assert (
        _modulo_backfill().ESTRATEGIA_NORMAL_SELECCIONADAS
        == EstrategiaCotizacionPO.NORMAL_SELECCIONADAS
    )

    po_modelo.estrategia_cotizacion = EstrategiaCotizacionPO.TOTAL_EXPLICITO
    po_modelo.total_explicito = Decimal("177.00")
    po_modelo.save()

    _aplicar_backfill()

    po_modelo.refresh_from_db()
    assert po_modelo.estrategia_cotizacion == EstrategiaCotizacionPO.NORMAL_SELECCIONADAS

    assert not LiquidacionPorcentajeObraAcumulacion.objects.filter(
        liquidacion_porcentaje=po_modelo
    ).exists()


@pytest.mark.django_db
def test_backfill_es_idempotente(po_modelo):
    """
    GIVEN: una PO ya en NORMAL_SELECCIONADAS
    WHEN:  se aplica el backfill dos veces
    THEN:  el resultado es el mismo y no se duplica ni altera nada.
    """
    _aplicar_backfill()
    _aplicar_backfill()

    po_modelo.refresh_from_db()
    assert po_modelo.estrategia_cotizacion == EstrategiaCotizacionPO.NORMAL_SELECCIONADAS
