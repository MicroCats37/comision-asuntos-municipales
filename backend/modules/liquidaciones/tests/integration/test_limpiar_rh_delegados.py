"""
Integration tests for `limpiar_rh_delegados` (limpieza EXCLUSIVA de RH Delegados).

Cubre el contrato destructivo del comando:

1. DRY-RUN por defecto: no borra nada e informa los conteos exactos por modelo.
2. `--apply` sin `--confirm-destructive` aborta con `CommandError`.
3. `--apply --confirm-destructive` borra los cuatro modelos del alcance
   (incluidos los detalles ligados a RH mensual ya emitido).
4. El catalogo de profesionales (`Delegado`, `DelegadoOperacion`), las
   liquidaciones, los proyectos y las municipalidades quedan intactos.
5. El comando NO importa CSV ni crea datos (contrato estatico).
"""
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.finanzas.domain.models.recibo_honorario import ReciboHonorarioDelegado
from modules.finanzas.domain.models.recibo_honorario_delegado_mensual import (
    ReciboHonorarioDelegadoMensual,
)
from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoOperacion,
    DelegadoOperacionPeriodo,
    LiquidacionDelegado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    PerfilIngeniero,
)


COMMANDS_DIR = Path(__file__).parents[2] / "management" / "commands"
COMMAND_NAME = "limpiar_rh_delegados"


# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def especialidad_revision(db):
    """EspecialidadRevision de revision (FK protegida de LiquidacionDelegado)."""
    return EspecialidadRevision.objects.create(
        slug="civil-limpiar-rh",
        nombre="Ingenieria Civil (limpiar_rh_delegados)",
    )


@pytest.fixture
def perfil_ingeniero(db):
    """PerfilIngeniero del delegado (PROTECT desde Delegado)."""
    return PerfilIngeniero.objects.create(
        cip="99887",
        dni="11111111",
        nombres="Test",
        apellido_paterno="RH",
        apellido_materno="Clean",
        correo_personal="rh.clean@test.com",
    )


@pytest.fixture
def delegado(db, perfil_ingeniero):
    """Delegado que debe sobrevivir a la limpieza."""
    return Delegado.objects.create(perfil_ingeniero=perfil_ingeniero)


@pytest.fixture
def delegado_operacion(db, delegado, municipalidad, especialidad_revision):
    """Operacion de delegacion que debe sobrevivir a la limpieza."""
    return DelegadoOperacion.objects.create(
        delegado=delegado,
        municipalidad=municipalidad,
        tipo_liquidacion=None,
        tipo="TITULAR",
        especialidad_revision=especialidad_revision,
    )


@pytest.fixture
def liquidacion_general(db, proyecto, municipalidad, tipo_edificacion):
    """Liquidacion que debe sobrevivir a la limpieza (no se toca el agregado)."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        total=Decimal("100.00"),
        sub_total=Decimal("100.00"),
    )


@pytest.fixture
def liquidacion_delegado(db, liquidacion_general, delegado, especialidad_revision):
    """Asignacion de delegado a liquidacion (se elimina)."""
    return LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_general,
        delegado=delegado,
        especialidad_revision=especialidad_revision,
        periodo=2024,
        mes=8,
    )


@pytest.fixture
def detalle_honorario(db, liquidacion_delegado):
    """Detalle historico (recibo_mensual NULL) — se elimina."""
    return DetalleHonorarioDelegado.objects.create(
        liquidacion_delegado=liquidacion_delegado,
        imp_bruto=Decimal("100.00"),
        sub_total=Decimal("100.00"),
        renta_cip=Decimal("25.00"),
        aporte_codemu=Decimal("5.00"),
        fondo_comun=Decimal("10.00"),
        neto_honorario=Decimal("60.00"),
    )


@pytest.fixture
def recibo_mensual(db, delegado, delegado_operacion):
    """RH mensual emitido — se elimina (decision de negocio confirmada)."""
    return ReciboHonorarioDelegadoMensual.objects.create(
        delegado=delegado,
        delegado_operacion=delegado_operacion,
        periodo=2024,
        mes=8,
        sub_total=Decimal("100.00"),
        renta_cip=Decimal("25.00"),
        aporte_codemu=Decimal("5.00"),
        fondo_comun=Decimal("10.00"),
        neto_honorario=Decimal("60.00"),
    )


@pytest.fixture
def detalle_de_rh_mensual(db, liquidacion_delegado, recibo_mensual):
    """Detalle ligado a un RH mensual emitido — tambien se elimina."""
    return DetalleHonorarioDelegado.objects.create(
        recibo_mensual=recibo_mensual,
        liquidacion_delegado=liquidacion_delegado,
        imp_bruto=Decimal("100.00"),
        sub_total=Decimal("100.00"),
        renta_cip=Decimal("25.00"),
        aporte_codemu=Decimal("5.00"),
        fondo_comun=Decimal("10.00"),
        neto_honorario=Decimal("60.00"),
    )


@pytest.fixture
def recibo_honorario(db, liquidacion_delegado):
    """Recibo de honorarios por asignacion — se elimina."""
    return ReciboHonorarioDelegado.objects.create(
        liquidacion_delegado=liquidacion_delegado,
        sub_total=Decimal("100.00"),
        imp_bruto=Decimal("100.00"),
        renta_cip=Decimal("25.00"),
        aporte_codemu=Decimal("5.00"),
        fondo_comun=Decimal("10.00"),
        neto_honorario=Decimal("60.00"),
        honorario=Decimal("60.00"),
    )


# ── Tests ───────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_dry_run_por_defecto_no_borra_nada(
    detalle_honorario,
    detalle_de_rh_mensual,
    recibo_honorario,
    recibo_mensual,
    liquidacion_delegado,
):
    """GIVEN datos de RH Delegado WHEN se ejecuta sin flags THEN nada se borra."""
    out = StringIO()
    call_command(COMMAND_NAME, stdout=out)
    texto = out.getvalue()

    assert "DRY-RUN" in texto
    assert "DetalleHonorarioDelegado: 2" in texto
    assert "ReciboHonorarioDelegado: 1" in texto
    assert "ReciboHonorarioDelegadoMensual: 1" in texto
    assert "LiquidacionDelegado: 1" in texto

    assert DetalleHonorarioDelegado.objects.count() == 2
    assert ReciboHonorarioDelegado.objects.count() == 1
    assert ReciboHonorarioDelegadoMensual.objects.count() == 1
    assert LiquidacionDelegado.objects.count() == 1


@pytest.mark.django_db
def test_apply_sin_confirmacion_aborta(detalle_honorario, liquidacion_delegado):
    """WHEN --apply sin --confirm-destructive THEN CommandError y cero escrituras."""
    with pytest.raises(CommandError):
        call_command(COMMAND_NAME, "--apply")

    assert DetalleHonorarioDelegado.objects.count() == 1
    assert LiquidacionDelegado.objects.count() == 1


@pytest.mark.django_db
def test_apply_borra_los_cuatro_modelos_del_alcance(
    detalle_honorario,
    detalle_de_rh_mensual,
    recibo_honorario,
    recibo_mensual,
    liquidacion_delegado,
):
    """WHEN --apply --confirm-destructive THEN los cuatro modelos quedan vacios."""
    out = StringIO()
    call_command(COMMAND_NAME, "--apply", "--confirm-destructive", stdout=out)
    texto = out.getvalue()

    assert DetalleHonorarioDelegado.objects.count() == 0
    assert ReciboHonorarioDelegado.objects.count() == 0
    assert ReciboHonorarioDelegadoMensual.objects.count() == 0
    assert LiquidacionDelegado.objects.count() == 0

    assert "Conteo final (registros eliminados):" in texto
    assert "LiquidacionDelegado: 1 borrados | restantes: 0" in texto


@pytest.mark.django_db
def test_apply_no_toca_catalogo_ni_liquidaciones(
    detalle_honorario,
    detalle_de_rh_mensual,
    recibo_honorario,
    recibo_mensual,
    liquidacion_delegado,
    delegado,
    delegado_operacion,
    liquidacion_general,
    proyecto,
    municipalidad,
):
    """WHEN se ejecuta el borrado THEN el catalogo y el agregado quedan intactos."""
    periodos_antes = DelegadoOperacionPeriodo.objects.count()
    delegated_antes = Delegado.objects.count()
    operaciones_antes = DelegadoOperacion.objects.count()
    liquidaciones_antes = LiquidacionGeneral.objects.count()

    call_command(COMMAND_NAME, "--apply", "--confirm-destructive", stdout=StringIO())

    assert Delegado.objects.count() == delegated_antes
    assert DelegadoOperacion.objects.count() == operaciones_antes
    assert DelegadoOperacionPeriodo.objects.count() == periodos_antes
    assert LiquidacionGeneral.objects.count() == liquidaciones_antes

    assert Delegado.objects.filter(pk=delegado.pk).exists()
    assert DelegadoOperacion.objects.filter(pk=delegado_operacion.pk).exists()
    assert LiquidacionGeneral.objects.filter(pk=liquidacion_general.pk).exists()
    assert proyecto is not None
    assert municipalidad is not None


def test_comando_no_importa_csv():
    """Contrato estatico: el comando es de limpieza, no de importacion."""
    fuente = (COMMANDS_DIR / f"{COMMAND_NAME}.py").read_text(encoding="utf-8")

    assert "import csv" not in fuente
    assert "RH_EDIF" not in fuente
    assert "read_rh_rows" not in fuente
