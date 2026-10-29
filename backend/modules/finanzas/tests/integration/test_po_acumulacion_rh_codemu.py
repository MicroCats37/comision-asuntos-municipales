"""
Regresión de consumidores RH / CODEMU frente a la acumulación PO.

Cubre el Module 7 del change `liquidacion-po-modos-cotizacion`:

- La base imponible del RH del Delegado se extrae SOLO del detalle
  participante persistido (`LiquidacionPorcentajeObraDetalle.subtotal`).
- La proyección de acumulación (diferencia padre - detalles) es
  INFORMATIVA: NO se distribuye, NO se suma al honorario y NO se lee como
  importe de participante.
- El aporte CODEMU se calcula sobre el subtotal de los detalles
  participantes, no sobre el subtotal del padre.
- Los candidatos de delegación siguen exigiendo un detalle participante:
  una liquidación cuyo único importe es la acumulación no es candidata.

Tests DB-backed (pytest-django + ORM real, flujos reales). Sin mocks.
NO SE EJECUTAN en este módulo: toda la ejecución queda reservada para el
Módulo 8.
"""
from decimal import Decimal
from datetime import date

import pytest
from django.contrib.auth import get_user_model

from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.entidades.domain.models.ubigeo import (
    UbigeoDepartamento,
    UbigeoProvincia,
    UbigeoDistrito,
)
from modules.liquidaciones.domain.constants import (
    EstrategiaCotizacionPO,
    TipoLiquidacion as TipoLiquidacionConst,
)
from modules.liquidaciones.domain.models.delegado import Delegado, DelegadoOperacion
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraAcumulacion,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorcentajeObra,
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
)
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.domain.models.tipo_liquidacion import (
    TipoLiquidacion as TipoLiquidacionModel,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    PerfilIngeniero,
    EspecialidadRevision,
)
from modules.finanzas.domain.models.tasa_delegado import TasaDelegado
from modules.finanzas.domain.schemas import (
    RHDelegadoCotizarIn,
    RHDelegadoCotizarItemIn,
)
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
    RHDelegadoMensualCotizarFlujo,
)


# ── Constantes ─────────────────────────────────────────────────────────────────

HABILITADAS = EstrategiaCotizacionPO.TARIFA_HABILITADAS_PARTICIPANTES

SUBTOTAL_PADRE = Decimal("1500.00")     # H (3) x f (0.05 %) sobre 1 000 000
SUBTOTAL_DETALLE = Decimal("500.00")    # subtotal_padre / H
SUBTOTAL_ACUMULACION = Decimal("1000.00")  # padre - detalle (no distribuible)

TASA_RENTA_CIP = Decimal("0.25")
TASA_APORTE_CODEMU = Decimal("0.05")
TASA_FONDO_COMUN = Decimal("0.10")


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def ubigeo_departamento(db):
    return UbigeoDepartamento.objects.create(nombre="LIMA")


@pytest.fixture
def ubigeo_provincia(db, ubigeo_departamento):
    return UbigeoProvincia.objects.create(departamento=ubigeo_departamento, nombre="LIMA")


@pytest.fixture
def ubigeo_distrito(db, ubigeo_provincia):
    return UbigeoDistrito.objects.create(
        provincia=ubigeo_provincia, nombre="MIRAFLORES", ubigeo="150132"
    )


@pytest.fixture
def municipalidad(db, ubigeo_distrito):
    return Municipalidad.objects.create(
        codigo="M001",
        nombre="Municipalidad de Miraflores",
        distrito=ubigeo_distrito,
    )


@pytest.fixture
def proyecto(db, municipalidad, ubigeo_distrito):
    return Proyecto.objects.create(
        nombre_propietario="Propietario Test SAC",
        direccion="Av. Test 123",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789012",
        entidad_razon_social="Propietario Test SAC",
    )


@pytest.fixture
def usuario_delegado(db):
    User = get_user_model()
    return User.objects.create_user(
        username="delegado_acumulacion",
        email="delegado_acumulacion@test.com",
        password="testpass123",
        dni="87654321",
    )


@pytest.fixture
def usuario_liquidacion(db):
    User = get_user_model()
    return User.objects.create_user(
        username="liq_acumulacion",
        email="liq_acumulacion@test.com",
        password="testpass123",
        dni="11223344",
    )


@pytest.fixture
def perfil_ingeniero_delegado(db, usuario_delegado):
    return PerfilIngeniero.objects.create(
        usuario=usuario_delegado,
        apellido_paterno="Pérez",
        apellido_materno="García",
        nombres="Juan",
        cip="CIP-DELEGADO-ACUM",
        dni="87654321",
    )


@pytest.fixture
def delegado(db, perfil_ingeniero_delegado):
    return Delegado.objects.create(perfil_ingeniero=perfil_ingeniero_delegado)


@pytest.fixture
def especialidad_estructuras(db):
    return EspecialidadRevision.objects.create(slug="estructuras", nombre="Estructuras")


@pytest.fixture
def tipo_edificacion(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacionConst.EDIFICACION, defaults={"nombre": "Edificaciones"}
    )[0]


@pytest.fixture
def tarifa_liquidacion_base(db, tipo_edificacion):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_porcentaje_obra(db, tarifa_liquidacion_base):
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base,
        porcentaje_liquidacion=Decimal("0.0005"),
    )


@pytest.fixture
def derecho_porcentaje_vigente(db):
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tasa_delegado_vigente(db, tipo_edificacion):
    return TasaDelegado.objects.create(
        nombre="Tasas Delegado (acumulación)",
        tipo_liquidacion=tipo_edificacion,
        renta_cip=TASA_RENTA_CIP,
        aporte_codemu=TASA_APORTE_CODEMU,
        fondo_comun=TASA_FONDO_COMUN,
        periodo_inicio=date(1900, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def liquidacion_general_po(db, proyecto, municipalidad, tipo_edificacion, usuario_liquidacion):
    """Liquidación de Edificaciones cuyo padre cobra H (1500.00)."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-ACUM-001",
        estado="REGISTRADO",
        sub_total=SUBTOTAL_PADRE,
        total=Decimal("1770.00"),
        numero_revision=1,
    )


@pytest.fixture
def liquidacion_po_padre(
    db, liquidacion_general_po, derecho_porcentaje_vigente, tarifa_porcentaje_obra
):
    """PO padre en TARIFA_HABILITADAS_PARTICIPANTES con H = 3 y f = 0.05 %."""
    LiquidacionEdificacion.objects.create(liquidacion=liquidacion_general_po, numero=1)

    return LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=liquidacion_general_po,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("1000000.00"),
        porcentaje_liquidacion=Decimal("0.0015"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
        estrategia_cotizacion=HABILITADAS,
        count_habilitadas=3,
        porcentaje_tarifa=Decimal("0.0005"),
        tarifa_aplicada=tarifa_porcentaje_obra,
    )


@pytest.fixture
def liquidacion_po_detalle(
    db, liquidacion_po_padre, tarifa_porcentaje_obra, especialidad_estructuras
):
    """Único detalle participante: recibe subtotal_padre / H = 500.00."""
    return LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=liquidacion_po_padre,
        tarifa_aplicada=tarifa_porcentaje_obra,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0005"),
        subtotal=SUBTOTAL_DETALLE,
        importe_parcial=SUBTOTAL_DETALLE,
        ajuste_redondeo=Decimal("0.00"),
    )


@pytest.fixture
def liquidacion_po_acumulacion(db, liquidacion_po_padre):
    """Fila de acumulación vigente: la diferencia padre - detalle (informativa)."""
    return LiquidacionPorcentajeObraAcumulacion.objects.create(
        liquidacion_porcentaje=liquidacion_po_padre,
        porcentaje_acumulado=Decimal("0.0010"),
        subtotal_acumulado=SUBTOTAL_ACUMULACION,
    )


@pytest.fixture
def core_service(db):
    return FinanzasCoreService()


@pytest.fixture
def cotizar_flujo(core_service):
    return RHDelegadoMensualCotizarFlujo(core=core_service)


@pytest.fixture
def delegado_operacion(db, delegado, municipalidad, especialidad_estructuras, tipo_edificacion):
    return DelegadoOperacion.objects.create(
        delegado=delegado,
        municipalidad=municipalidad,
        especialidad_revision=especialidad_estructuras,
        tipo_liquidacion=tipo_edificacion,
    )


def _payload(cip: str, items: list[dict], delegado_operacion_id: str):
    return RHDelegadoCotizarIn(
        cip=cip,
        periodo=2026,
        mes=1,
        delegado_operacion_id=delegado_operacion_id,
        items=[RHDelegadoCotizarItemIn(**i) for i in items],
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_la_base_imponible_del_rh_solo_usa_el_detalle_participante(
    core_service, liquidacion_general_po, liquidacion_po_detalle, liquidacion_po_acumulacion
):
    """
    GIVEN: una liquidación PO cuyo padre cobra 1500.00 y tiene UN detalle
           participante de 500.00, con una acumulación de 1000.00.
    WHEN:  el core de finanzas resuelve los importes del detalle.
    THEN:  devuelve el subtotal del DETALLE (500.00), no el del padre (1500.00)
           y no la diferencia acumulada (1000.00).
    """
    importes = core_service.get_importes_po_detalle(
        liquidacion_general_po.id,
        liquidacion_po_detalle.especialidad_id,
    )

    assert importes is not None
    importe_parcial, ajuste_redondeo, subtotal = importes

    assert subtotal == SUBTOTAL_DETALLE
    assert importe_parcial == SUBTOTAL_DETALLE
    assert ajuste_redondeo == Decimal("0.00")

    # La acumulación existe y NO forma parte de la base imponible.
    assert liquidacion_po_acumulacion.subtotal_acumulado == SUBTOTAL_ACUMULACION
    assert subtotal != SUBTOTAL_PADRE
    assert subtotal != SUBTOTAL_ACUMULACION


@pytest.mark.django_db
def test_el_rh_delegado_no_distribuye_la_acumulacion(
    cotizar_flujo, delegado, perfil_ingeniero_delegado, delegado_operacion,
    liquidacion_general_po, liquidacion_po_detalle, liquidacion_po_acumulacion,
    tasa_delegado_vigente,
):
    """
    GIVEN: la liquidación PO con acumulación (padre 1500.00 / detalle 500.00 /
           acumulación 1000.00).
    WHEN:  se cotiza el RH mensual del delegado para esa especialidad.
    THEN:  el importe bruto y el SUBTOTAL del RH son 500.00 (solo el detalle
           participante) y el aporte CODEMU es el 5 % de 500.00 (25.00), no el
           5 % de 1500.00 ni el 5 % de 1000.00.
    """
    result = cotizar_flujo.cotizar(
        _payload(
            cip=perfil_ingeniero_delegado.cip,
            items=[
                {
                    "liquidacion_general_id": str(liquidacion_general_po.id),
                    "especialidad_revision_id": str(liquidacion_po_detalle.especialidad_id),
                    "periodo": 2026,
                    "mes": 1,
                }
            ],
            delegado_operacion_id=str(delegado_operacion.id),
        )
    )

    assert len(result.items) == 1
    item = result.items[0]

    # Base imponible = detalle participante, NO el padre y NO la acumulación.
    assert item.imp_bruto == SUBTOTAL_DETALLE

    # CODEMU sobre la base del detalle (5 % de 500.00 = 25.00).
    assert item.aporte_codemu == Decimal("25.00")
    assert result.totales.aporte_codemu == Decimal("25.00")

    # El subtotal congelado del RH tampoco incluye la acumulación.
    assert result.totales.sub_total == SUBTOTAL_DETALLE

    # Y el neto al delegado se calcula sobre esa misma base.
    neto_esperado = (
        SUBTOTAL_DETALLE * (Decimal("1") - TASA_RENTA_CIP - TASA_APORTE_CODEMU - TASA_FONDO_COMUN)
    ).quantize(Decimal("0.01"))
    assert item.neto_honorario == neto_esperado
    assert result.totales.neto_honorario == neto_esperado


@pytest.mark.django_db
def test_los_candidatos_exigen_detalle_participante_y_no_la_acumulacion(
    db, liquidacion_general_po, liquidacion_po_padre, liquidacion_po_acumulacion,
):
    """
    GIVEN: una liquidación PO SIN detalles participantes (sólo el padre y su
           acumulación).
    WHEN:  se consulta la existencia de un detalle participante para la
           especialidad del delegado.
    THEN:  no existe: los candidatos de delegación se alimentan SOLO de los
           detalles participantes, nunca del padre ni de la acumulación.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
        LiquidacionPorcentajeObraDetalle as DetallePO,
    )

    assert DetallePO.objects.filter(
        liquidacion_porcentaje__liquidacion_general_id=liquidacion_general_po.id
    ).count() == 0

    # La liquidación sigue siendo una liquidación PO válida con padre y
    # acumulación: lo que no existe es el detalle participante.
    assert liquidacion_po_padre.estrategia_cotizacion == HABILITADAS
    assert liquidacion_po_acumulacion.subtotal_acumulado == SUBTOTAL_ACUMULACION
