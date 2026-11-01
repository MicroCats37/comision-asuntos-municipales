"""
Regresión: el output de RH Delegado mensual expone la estrategia PO y su
total explícito.

El motor PO de Edificaciones tiene TRES estrategias de cotización. RH mensual
consume liquidaciones PO (estrategia `detail`), así que el output debe poder
distinguir en qué estrategia se cotizó la liquidación:

- `estrategia_cotizacion`: el discriminador persistido en LiquidacionPorcentajeObra.
- `total_explicito`: el total final autoritativo (solo TOTAL_EXPLICITO).

Ambos son NULL cuando la liquidación NO tiene wrapper PO (motor M2).

Tests DB-backed (pytest-django + ORM real, flujos reales). Sin mocks.
"""
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.entidades.domain.models.ubigeo import (
    UbigeoDepartamento,
    UbigeoDistrito,
    UbigeoProvincia,
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
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import (
    TipoLiquidacion as TipoLiquidacionModel,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    PerfilIngeniero,
    EspecialidadRevision,
)

TOTAL_EXPLICITO_VALOR = Decimal("177.00")
SUBTOTAL_DETALLE = Decimal("50.00")
TASA_RENTA_CIP = Decimal("0.25")
TASA_APORTE_CODEMU = Decimal("0.05")
TASA_FONDO_COMUN = Decimal("0.10")


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def ubigeo_departamento(db):
    return UbigeoDepartamento.objects.create(nombre="LIMA")


@pytest.fixture
def ubigeo_provincia(db, ubigeo_departamento):
    return UbigeoProvincia.objects.create(
        departamento=ubigeo_departamento, nombre="LIMA"
    )


@pytest.fixture
def ubigeo_distrito(db, ubigeo_provincia):
    return UbigeoDistrito.objects.create(
        provincia=ubigeo_provincia, nombre="MIRAFLORES", ubigeo="150132"
    )


@pytest.fixture
def municipalidad(db, ubigeo_distrito):
    return Municipalidad.objects.create(
        codigo="M-ESTR", nombre="Municipalidad Miraflores", distrito=ubigeo_distrito
    )


@pytest.fixture
def proyecto(db, municipalidad, ubigeo_distrito):
    from modules.entidades.domain.models import Entidad
    from modules.liquidaciones.domain.models.proyecto import Proyecto

    entidad = Entidad.objects.create(
        tipo_documento="RUC", numero_documento="20456789013"
    )
    return Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Propietario Estrategia SAC",
        direccion="Av. Estrategia 123",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789013",
        entidad_razon_social="Propietario Estrategia SAC",
    )


@pytest.fixture
def usuario_delegado(db):
    User = get_user_model()
    return User.objects.create_user(
        username="rh_estrategia_delegado",
        email="rh_estrategia_delegado@test.com",
        password="testpass123",
        dni="11223355",
    )


@pytest.fixture
def perfil_ingeniero_delegado(db, usuario_delegado):
    return PerfilIngeniero.objects.create(
        usuario=usuario_delegado,
        apellido_paterno="Pérez",
        apellido_materno="García",
        nombres="Juan",
        cip="CIP-DELEGADO-ESTRATEGIA",
        dni="87654322",
    )


@pytest.fixture
def delegado(db, perfil_ingeniero_delegado):
    return Delegado.objects.create(perfil_ingeniero=perfil_ingeniero_delegado)


@pytest.fixture
def especialidad_estructuras(db):
    return EspecialidadRevision.objects.create(
        slug="estructuras-estrategia", nombre="Estructuras"
    )


@pytest.fixture
def tipo_edificacion(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacionConst.EDIFICACION, defaults={"nombre": "Edificaciones"}
    )[0]


@pytest.fixture
def tipo_habilitacion_urbana(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacionConst.HABILITACION_URBANA,
        defaults={"nombre": "Habilitación Urbana"},
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
def tasa_delegado_vigente(db, tipo_edificacion):
    return TasaDelegado.objects.create(
        nombre="Tasas Delegado (estrategia)",
        tipo_liquidacion=tipo_edificacion,
        renta_cip=TASA_RENTA_CIP,
        aporte_codemu=TASA_APORTE_CODEMU,
        fondo_comun=TASA_FONDO_COMUN,
        periodo_inicio=date(1900, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def core_service(db):
    return FinanzasCoreService()


@pytest.fixture
def cotizar_flujo(core_service):
    return RHDelegadoMensualCotizarFlujo(core=core_service)


@pytest.fixture
def liquidacion_po_total_explicito(
    db, municipalidad, proyecto, usuario_delegado, tipo_edificacion
):
    """Liquidación PO en TOTAL_EXPLICITO con su total explícito persistido."""
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=usuario_delegado,
        expediente="EXP-TOTAL-EXPLICITO",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("150.00"),
        total=TOTAL_EXPLICITO_VALOR,
    )
    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)
    po = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("1000000.00"),
        porcentaje_liquidacion=None,
        porcentaje_minimo_uit=Decimal("0.10"),
        estrategia_cotizacion=EstrategiaCotizacionPO.TOTAL_EXPLICITO,
        cantidad_especialidades_habilitadas=3,
        total_explicito=TOTAL_EXPLICITO_VALOR,
    )
    return lg, po


@pytest.fixture
def liquidacion_po_detalle(
    db, liquidacion_po_total_explicito, tarifa_porcentaje_obra, especialidad_estructuras
):
    """Detalle participante: el importe que el RH usa como base imponible."""
    _lg, po = liquidacion_po_total_explicito
    return LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=po,
        tarifa_aplicada=tarifa_porcentaje_obra,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=None,
        subtotal=SUBTOTAL_DETALLE,
        importe_parcial=SUBTOTAL_DETALLE,
        ajuste_redondeo=Decimal("0.00"),
    )


@pytest.fixture
def delegado_operacion(
    db, delegado, municipalidad, especialidad_estructuras, tipo_edificacion
):
    return DelegadoOperacion.objects.create(
        delegado=delegado,
        municipalidad=municipalidad,
        especialidad_revision=especialidad_estructuras,
        tipo_liquidacion=tipo_edificacion,
    )


@pytest.fixture
def liquidacion_sin_wrapper_po(
    db, municipalidad, proyecto, usuario_delegado, tipo_habilitacion_urbana
):
    """Liquidación M2: sin wrapper de PorcentajeObra."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=usuario_delegado,
        expediente="EXP-SIN-PO",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_revision=1,
        sub_total=Decimal("250.00"),
        total=Decimal("295.00"),
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_el_rh_delegado_expone_la_estrategia_po_y_su_total_explicito(
    cotizar_flujo,
    perfil_ingeniero_delegado,
    delegado_operacion,
    liquidacion_po_total_explicito,
    liquidacion_po_detalle,
    tasa_delegado_vigente,
):
    """
    GIVEN: una liquidación PO en TOTAL_EXPLICITO con total_explicito persistido.
    WHEN:  se cotiza el RH mensual del delegado.
    THEN:  el item expone `estrategia_cotizacion` = TOTAL_EXPLICITO y su
           `total_explicito`; la base imponible sigue viniendo del detalle
           participante (el total explícito NO se suma al honorario).
    """
    lg, _po = liquidacion_po_total_explicito

    result = cotizar_flujo.cotizar(
        RHDelegadoCotizarIn(
            cip=perfil_ingeniero_delegado.cip,
            periodo=2026,
            mes=1,
            delegado_operacion_id=str(delegado_operacion.id),
            items=[
                RHDelegadoCotizarItemIn(
                    liquidacion_general_id=str(lg.id),
                    especialidad_revision_id=str(
                        liquidacion_po_detalle.especialidad_id
                    ),
                    periodo=2026,
                    mes=1,
                )
            ],
        )
    )

    assert len(result.items) == 1
    item = result.items[0]

    assert item.estrategia_cotizacion == EstrategiaCotizacionPO.TOTAL_EXPLICITO
    assert item.total_explicito == TOTAL_EXPLICITO_VALOR

    # El total explícito es informativo: la base sigue siendo el detalle.
    assert item.imp_bruto == SUBTOTAL_DETALLE


@pytest.mark.django_db
def test_el_rh_delegado_no_expone_estrategia_en_liquidaciones_sin_wrapper_po(
    cotizar_flujo,
    perfil_ingeniero_delegado,
    liquidacion_sin_wrapper_po,
    tasa_delegado_vigente,
):
    """
    GIVEN: una liquidación de un motor SIN wrapper PO (M2).
    WHEN:  el RH resuelve la estrategia de esa liquidación.
    THEN:  `estrategia_cotizacion` y `total_explicito` son None (no se inventan).
    """
    from modules.finanzas.domain.services.helpers.liquidacion_helpers import (
        _resolve_estrategia_po,
    )

    estrategia, total_explicito = _resolve_estrategia_po(liquidacion_sin_wrapper_po)

    assert estrategia is None
    assert total_explicito is None
