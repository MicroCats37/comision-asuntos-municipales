"""
Integration tests — expediente atómico con el guardado del RH mensual.

Cubre el contrato "Expediente por liquidación en el payload del RH":

- El `expediente` viaja por item en los payloads del RH (delegado e inspector).
- El backend lo persiste EN LA MISMA TRANSACCIÓN que la mutación del RH.
- Una liquidación PAGADA con un expediente DISTINTO aborta toda la operación
  (409 LIQUIDACION_PAGADA_NOT_EDITABLE) y no deja ni RH ni expediente a medias.
- Un expediente IGUAL al persistido es un no-op (no se escribe, no falla).
- La cotización NO persiste el expediente: sigue mostrando el persistido.
- El `expediente` es POR LIQUIDACIÓN: nunca metadata compartida de la
  asignación al delegado/inspector.

Los flujos se invocan directamente (mismo criterio que el resto de la suite de
`modules/finanzas/tests/integration/`): son los mismos que los endpoints
llaman por detrás, y así se puede comprobar la atomicidad de la transacción
sin depender del cliente HTTP.

Tests NO ejecutados en este batch (verificación diferida a la fase final).
"""
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from core.exceptions import ConflictError
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.entidades.domain.models.ubigeo import (
    UbigeoDepartamento,
    UbigeoDistrito,
    UbigeoProvincia,
)
from modules.liquidaciones.domain.constants import (
    EstadoLiquidacion,
    TipoLiquidacion as TipoLiquidacionConst,
)
from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoOperacion,
    LiquidacionDelegado,
)
from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    LiquidacionInspector,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorcentajeObra,
    TarifaPorcentajeObra,
    TarifaPorCategoriaVisitas,
    TarifaLiquidacionBase,
)
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.domain.models.tipo_liquidacion import (
    TipoLiquidacion as TipoLiquidacionModel,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    PerfilIngeniero,
)
from modules.finanzas.domain.models.descuento_inspector import (
    EscalaDescuentoInspector,
    RangoDescuentoInspector,
)
from modules.finanzas.domain.models.recibo_honorario_delegado_mensual import (
    ReciboHonorarioDelegadoMensual,
)
from modules.finanzas.domain.models.recibo_honorario_inspector_mensual import (
    ReciboHonorarioInspectorMensual,
)
from modules.finanzas.domain.models.tasa_delegado import TasaDelegado
from modules.finanzas.domain.schemas import (
    RHDelegadoActualizarIn,
    RHDelegadoActualizarItemIn,
    RHDelegadoCotizarIn,
    RHDelegadoCotizarItemIn,
    RHInspectorActualizarIn,
    RHInspectorActualizarItemIn,
    RHInspectorCotizarIn,
    RHInspectorCotizarItemIn,
)
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
    RHDelegadoMensualActualizarFlujo,
    RHDelegadoMensualCotizarFlujo,
    RHDelegadoMensualCrearFlujo,
)
from modules.finanzas.domain.services.flujos.rh_inspector_mensual_flujo import (
    RHInspectorMensualActualizarFlujo,
    RHInspectorMensualCotizarFlujo,
    RHInspectorMensualCrearFlujo,
)


# ── Fixtures: ubigeo / municipalidad / proyectos ───────────────────────────────


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
def segundo_proyecto(db, municipalidad, ubigeo_distrito):
    """`LiquidacionGeneral.proyecto` es OneToOne: cada liquidación necesita uno."""
    return Proyecto.objects.create(
        nombre_propietario="Propietario Test Dos SAC",
        direccion="Av. Test 456",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789013",
        entidad_razon_social="Propietario Test Dos SAC",
    )


@pytest.fixture
def tercer_proyecto(db, municipalidad, ubigeo_distrito):
    return Proyecto.objects.create(
        nombre_propietario="Propietario Test Tres SAC",
        direccion="Av. Test 789",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789014",
        entidad_razon_social="Propietario Test Tres SAC",
    )


@pytest.fixture
def usuario_liquidacion(db):
    User = get_user_model()
    return User.objects.create_user(
        username="liq_expediente",
        email="liq_expediente@test.com",
        password="testpass123",
        dni="11223344",
    )


# ── Fixtures: delegado (PO) ─────────────────────────────────────────────────────


@pytest.fixture
def tipo_edificacion(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacionConst.EDIFICACION,
        defaults={"nombre": "Edificaciones"},
    )[0]


@pytest.fixture
def especialidad_estructuras(db):
    return EspecialidadRevision.objects.create(
        slug="estructuras", nombre="Estructuras"
    )


@pytest.fixture
def tarifa_liquidacion_base(db, tipo_edificacion):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
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
def tarifa_porcentaje_obra(db, tarifa_liquidacion_base):
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base,
        porcentaje_liquidacion=Decimal("0.0010"),
    )


@pytest.fixture
def tasa_delegado_vigente(db, tipo_edificacion):
    return TasaDelegado.objects.create(
        nombre="Tasas Delegado (vigencia histórica)",
        tipo_liquidacion=tipo_edificacion,
        renta_cip=Decimal("0.25"),
        aporte_codemu=Decimal("0.05"),
        fondo_comun=Decimal("0.10"),
        periodo_inicio=date(1900, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def usuario_delegado(db):
    User = get_user_model()
    return User.objects.create_user(
        username="delegado_expediente",
        email="delegado_expediente@test.com",
        password="testpass123",
        dni="87654321",
    )


@pytest.fixture
def perfil_ingeniero_delegado(db, usuario_delegado):
    return PerfilIngeniero.objects.create(
        usuario=usuario_delegado,
        apellido_paterno="Pérez",
        apellido_materno="García",
        nombres="Juan",
        cip="CIP-DELEGADO-EXP",
        dni="87654321",
    )


@pytest.fixture
def delegado(db, perfil_ingeniero_delegado):
    return Delegado.objects.create(perfil_ingeniero=perfil_ingeniero_delegado)


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
def crear_liquidacion_po(
    db,
    municipalidad,
    tipo_edificacion,
    usuario_liquidacion,
    tarifa_porcentaje_obra,
    derecho_porcentaje_vigente,
    especialidad_estructuras,
):
    """
    Crea una liquidación de tipo PO con su detalle de especialidad.

    Devuelve ``(liquidacion_general, detalle_porcentaje)``.
    """

    def _crear(
        proyecto,
        *,
        expediente,
        estado=EstadoLiquidacion.PENDIENTE,
        subtotal=Decimal("1000.00"),
    ):
        liquidacion = LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_edificacion,
            usuario_creador=usuario_liquidacion,
            expediente=expediente,
            estado=estado,
            sub_total=subtotal,
            total=subtotal * Decimal("1.18"),
            numero_revision=1,
        )
        porcentaje_obra = LiquidacionPorcentajeObra.objects.create(
            liquidacion_general=liquidacion,
            tipo_tramite="OBRA_NUEVA",
            valor_declarado=Decimal("100000.00"),
            porcentaje_liquidacion=Decimal("0.0010"),
            derecho_minimo=Decimal("500.00"),
            derecho_maximo=Decimal("50000.00"),
            porcentaje_minimo_uit=Decimal("0.10"),
            derecho_aplicado=derecho_porcentaje_vigente,
        )
        detalle = LiquidacionPorcentajeObraDetalle.objects.create(
            liquidacion_porcentaje=porcentaje_obra,
            tarifa_aplicada=tarifa_porcentaje_obra,
            especialidad=especialidad_estructuras,
            porcentaje_aplicado=Decimal("0.0010"),
            subtotal=subtotal,
            importe_parcial=subtotal,
            ajuste_redondeo=Decimal("0.00"),
        )
        return liquidacion, detalle

    return _crear


@pytest.fixture
def liquidacion_po(crear_liquidacion_po, proyecto):
    return crear_liquidacion_po(proyecto, expediente="EXP-PO-001")


@pytest.fixture
def segunda_liquidacion_po(crear_liquidacion_po, segundo_proyecto):
    return crear_liquidacion_po(segundo_proyecto, expediente="EXP-PO-002")


@pytest.fixture
def tercera_liquidacion_po(crear_liquidacion_po, tercer_proyecto):
    return crear_liquidacion_po(tercer_proyecto, expediente="EXP-PO-003")


# ── Fixtures: inspector (IO) ────────────────────────────────────────────────────


@pytest.fixture
def escala_descuento(db):
    """Escala vigente con un único rango del 15%."""
    escala = EscalaDescuentoInspector.objects.create(
        nombre="Escala 2026",
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=None,
    )
    RangoDescuentoInspector.objects.create(
        escala=escala,
        monto_minimo=Decimal("0"),
        monto_maximo=Decimal("8000"),
        porcentaje_descuento=Decimal("0.15"),
    )
    return escala


@pytest.fixture
def tipo_inspeccion_obra(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacionConst.INSPECCION_OBRA,
        defaults={"nombre": "Inspección de Obra"},
    )[0]


@pytest.fixture
def tarifa_base_io(db, tipo_inspeccion_obra):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_inspeccion_obra,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_visitas_io(db, tarifa_base_io):
    return TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=tarifa_base_io,
        porcentaje_uit=Decimal("0.05"),
        categoria_visitas="INSPECCION",
    )


@pytest.fixture
def usuario_inspector(db):
    User = get_user_model()
    return User.objects.create_user(
        username="inspector_expediente",
        email="inspector_expediente@test.com",
        password="testpass123",
        dni="76543210",
    )


@pytest.fixture
def perfil_ingeniero_inspector(db, usuario_inspector):
    return PerfilIngeniero.objects.create(
        usuario=usuario_inspector,
        apellido_paterno="Quispe",
        apellido_materno="Rojas",
        nombres="María",
        cip="CIP-INSPECTOR-EXP",
        dni="76543210",
    )


@pytest.fixture
def inspector(db, perfil_ingeniero_inspector):
    return Inspector.objects.create(perfil_ingeniero=perfil_ingeniero_inspector)


@pytest.fixture
def crear_liquidacion_io(
    db,
    municipalidad,
    tipo_inspeccion_obra,
    usuario_liquidacion,
    tarifa_visitas_io,
):
    """Crea una liquidación de IO con su LiquidacionPorCategoriaVisitas."""

    def _crear(proyecto, *, expediente, estado=EstadoLiquidacion.PENDIENTE):
        liquidacion = LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_inspeccion_obra,
            usuario_creador=usuario_liquidacion,
            expediente=expediente,
            estado=estado,
            sub_total=Decimal("1000.00"),
            total=Decimal("1180.00"),
            numero_revision=1,
        )
        io = LiquidacionPorCategoriaVisitas.objects.create(
            liquidacion_general=liquidacion,
            cantidad_visitas=10,
            porcentaje_uit=Decimal("0.05"),
            categoria="A",
            tarifa_aplicada=tarifa_visitas_io,
        )
        return liquidacion, io

    return _crear


@pytest.fixture
def liquidacion_io(crear_liquidacion_io, proyecto):
    return crear_liquidacion_io(proyecto, expediente="EXP-IO-001")


@pytest.fixture
def segunda_liquidacion_io(crear_liquidacion_io, segundo_proyecto):
    return crear_liquidacion_io(segundo_proyecto, expediente="EXP-IO-002")


@pytest.fixture
def liquidacion_inspector(
    db, liquidacion_io, inspector, especialidad_estructuras
):
    """Asocia el inspector a la IO (tabla puente)."""
    return LiquidacionInspector.objects.create(
        liquidacion=liquidacion_io[1],
        inspector=inspector,
        especialidad_revision=especialidad_estructuras,
    )


# ── Flujos ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def core_service(db):
    return FinanzasCoreService()


@pytest.fixture
def cotizar_flujo_delegado(core_service):
    return RHDelegadoMensualCotizarFlujo(core=core_service)


@pytest.fixture
def crear_flujo_delegado(core_service, cotizar_flujo_delegado):
    return RHDelegadoMensualCrearFlujo(
        core=core_service, cotizar_flujo=cotizar_flujo_delegado
    )


@pytest.fixture
def actualizar_flujo_delegado(core_service, cotizar_flujo_delegado):
    return RHDelegadoMensualActualizarFlujo(
        core=core_service, cotizar_flujo=cotizar_flujo_delegado
    )


@pytest.fixture
def cotizar_flujo_inspector(core_service):
    return RHInspectorMensualCotizarFlujo(core=core_service)


@pytest.fixture
def crear_flujo_inspector(core_service, cotizar_flujo_inspector):
    return RHInspectorMensualCrearFlujo(
        core=core_service, cotizar_flujo=cotizar_flujo_inspector
    )


@pytest.fixture
def actualizar_flujo_inspector(core_service, cotizar_flujo_inspector):
    return RHInspectorMensualActualizarFlujo(
        core=core_service, cotizar_flujo=cotizar_flujo_inspector
    )


# ── Payload builders ────────────────────────────────────────────────────────────


def _payload_delegado(cip, periodo, mes, items, delegado_operacion_id):
    """Payload de cotización/creación del RH mensual del delegado."""
    return RHDelegadoCotizarIn(
        cip=cip,
        periodo=periodo,
        mes=mes,
        delegado_operacion_id=delegado_operacion_id,
        items=[RHDelegadoCotizarItemIn(**item) for item in items],
    )


def _payload_actualizar_delegado(cip, periodo, mes, items, delegado_operacion_id):
    """Payload de PATCH (sincronización) del RH mensual del delegado."""
    return RHDelegadoActualizarIn(
        cip=cip,
        periodo=periodo,
        mes=mes,
        delegado_operacion_id=delegado_operacion_id,
        items=[RHDelegadoActualizarItemIn(**item) for item in items],
    )


def _payload_inspector(cip, periodo, mes, items):
    """Payload de cotización/creación del RH mensual del inspector."""
    return RHInspectorCotizarIn(
        cip=cip,
        periodo=periodo,
        mes=mes,
        items=[RHInspectorCotizarItemIn(**item) for item in items],
    )


def _payload_actualizar_inspector(cip, periodo, mes, items):
    """Payload de PATCH (sincronización) del RH mensual del inspector."""
    return RHInspectorActualizarIn(
        cip=cip,
        periodo=periodo,
        mes=mes,
        items=[RHInspectorActualizarItemIn(**item) for item in items],
    )


# ── B1 · Create delegado persiste el expediente ────────────────────────────────


@pytest.mark.django_db
def test_crear_delegado_persiste_el_expediente_de_cada_liquidacion(
    crear_flujo_delegado,
    perfil_ingeniero_delegado,
    delegado_operacion,
    liquidacion_po,
    tasa_delegado_vigente,
):
    """
    GIVEN: Un RH de delegado con una liquidación seleccionada.
    WHEN: El payload incluye el `expediente` de esa liquidación.
    THEN: El RH se persiste y el expediente queda en la LiquidacionGeneral.
    """
    liquidacion, detalle = liquidacion_po

    resultado = crear_flujo_delegado.crear(
        _payload_delegado(
            cip=perfil_ingeniero_delegado.cip,
            periodo=2026,
            mes=1,
            items=[
                {
                    "liquidacion_general_id": str(liquidacion.id),
                    "especialidad_revision_id": str(detalle.especialidad_id),
                    "periodo": 2026,
                    "mes": 1,
                    "expediente": "EXP-NUEVO-001",
                }
            ],
            delegado_operacion_id=str(delegado_operacion.id),
        )
    )

    liquidacion.refresh_from_db()
    assert liquidacion.expediente == "EXP-NUEVO-001"
    assert ReciboHonorarioDelegadoMensual.objects.count() == 1
    # La respuesta refleja el valor persistido.
    assert resultado.items[0].exp_liqui == "EXP-NUEVO-001"


# ── B2 · Atomicidad: un fallo aborta TODO el RH ────────────────────────────────


@pytest.mark.django_db
def test_crear_delegado_aborta_y_revierte_todo_si_una_liquidacion_pagada_cambia(
    crear_flujo_delegado,
    perfil_ingeniero_delegado,
    delegado_operacion,
    crear_liquidacion_po,
    proyecto,
    segundo_proyecto,
    tasa_delegado_vigente,
):
    """
    GIVEN: Un payload de 2 liquidaciones; la segunda está PAGADA.
    WHEN: Se guardan y la segunda cambia su expediente.
    THEN: 409 LIQUIDACION_PAGADA_NOT_EDITABLE y NADA queda persistido:
          ni el RH, ni el expediente ya escrito de la primera liquidación.
    """
    liquidacion_ok, detalle_ok = crear_liquidacion_po(
        proyecto, expediente="EXP-ATOM-001"
    )
    liquidacion_pagada, detalle_pagada = crear_liquidacion_po(
        segundo_proyecto,
        expediente="EXP-ATOM-002",
        estado=EstadoLiquidacion.PAGADA,
    )

    with pytest.raises(ConflictError) as excepcion:
        crear_flujo_delegado.crear(
            _payload_delegado(
                cip=perfil_ingeniero_delegado.cip,
                periodo=2026,
                mes=1,
                items=[
                    {
                        "liquidacion_general_id": str(liquidacion_ok.id),
                        "especialidad_revision_id": str(detalle_ok.especialidad_id),
                        "periodo": 2026,
                        "mes": 1,
                        "expediente": "EXP-ATOM-NUEVO-001",
                    },
                    {
                        "liquidacion_general_id": str(liquidacion_pagada.id),
                        "especialidad_revision_id": str(detalle_pagada.especialidad_id),
                        "periodo": 2026,
                        "mes": 1,
                        "expediente": "EXP-ATOM-NUEVO-002",
                    },
                ],
                delegado_operacion_id=str(delegado_operacion.id),
            )
        )

    assert excepcion.value.status_code == 409
    assert excepcion.value.code == "LIQUIDACION_PAGADA_NOT_EDITABLE"

    # Rollback total: el RH no existe y ningún expediente cambió.
    assert ReciboHonorarioDelegadoMensual.objects.count() == 0
    liquidacion_ok.refresh_from_db()
    liquidacion_pagada.refresh_from_db()
    assert liquidacion_ok.expediente == "EXP-ATOM-001"
    assert liquidacion_pagada.expediente == "EXP-ATOM-002"


# ── B3 · Guard PAGADA: 409 y sin cambios ───────────────────────────────────────


@pytest.mark.django_db
def test_crear_delegado_con_liquidacion_pagada_y_expediente_distinto_responde_409(
    crear_flujo_delegado,
    perfil_ingeniero_delegado,
    delegado_operacion,
    crear_liquidacion_po,
    proyecto,
    tasa_delegado_vigente,
):
    """
    GIVEN: Una liquidación PAGADA seleccionada en el RH.
    WHEN: El payload cambia su expediente.
    THEN: 409 LIQUIDACION_PAGADA_NOT_EDITABLE, sin RH y sin cambio de expediente.
    """
    liquidacion, detalle = crear_liquidacion_po(
        proyecto,
        expediente="EXP-PAGADA-001",
        estado=EstadoLiquidacion.PAGADA,
    )

    with pytest.raises(ConflictError) as excepcion:
        crear_flujo_delegado.crear(
            _payload_delegado(
                cip=perfil_ingeniero_delegado.cip,
                periodo=2026,
                mes=1,
                items=[
                    {
                        "liquidacion_general_id": str(liquidacion.id),
                        "especialidad_revision_id": str(detalle.especialidad_id),
                        "periodo": 2026,
                        "mes": 1,
                        "expediente": "EXP-PAGADA-CAMBIADO",
                    }
                ],
                delegated_operacion_id=str(delegado_operacion.id),
            )
        )

    assert excepcion.value.status_code == 409
    assert excepcion.value.code == "LIQUIDACION_PAGADA_NOT_EDITABLE"
    assert ReciboHonorarioDelegadoMensual.objects.count() == 0
    liquidacion.refresh_from_db()
    assert liquidacion.expediente == "EXP-PAGADA-001"


# ── B4 · Guard PAGADA: mismo valor = no-op ──────────────────────────────────────


@pytest.mark.django_db
def test_crear_delegado_con_liquidacion_pagada_y_expediente_igual_es_no_op(
    crear_flujo_delegado,
    perfil_ingeniero_delegado,
    delegado_operacion,
    crear_liquidacion_po,
    proyecto,
    tasa_delegado_vigente,
):
    """
    GIVEN: Una liquidación PAGADA cuyo expediente es "EXP-PAGADA-OK".
    WHEN: El payload reenvía ese MISMO expediente.
    THEN: El guardado termina bien, no se escribe el campo y no hay 409.
    """
    liquidacion, detalle = crear_liquidacion_po(
        proyecto,
        expediente="EXP-PAGADA-OK",
        estado=EstadoLiquidacion.PAGADA,
    )
    actualizado_en = liquidacion.updated_at

    resultado = crear_flujo_delegado.crear(
        _payload_delegado(
            cip=perfil_ingeniero_delegado.cip,
            periodo=2026,
            mes=1,
            items=[
                {
                    "liquidacion_general_id": str(liquidacion.id),
                    "especialidad_revision_id": str(detalle.especialidad_id),
                    "periodo": 2026,
                    "mes": 1,
                    "expediente": "EXP-PAGADA-OK",
                }
            ],
            delegado_operacion_id=str(delegado_operacion.id),
        )
    )

    assert ReciboHonorarioDelegadoMensual.objects.count() == 1
    liquidacion.refresh_from_db()
    assert liquidacion.expediente == "EXP-PAGADA-OK"
    # No-op real: la fila NO fue escrita (updated_at no cambió).
    assert liquidacion.updated_at == actualizado_en
    assert resultado.items[0].exp_liqui == "EXP-PAGADA-OK"


# ── B5 · PATCH delegado persiste el expediente ──────────────────────────────────


@pytest.mark.django_db
def test_patch_delegado_persiste_el_expediente_en_la_misma_transaccion(
    crear_flujo_delegado,
    actualizar_flujo_delegado,
    perfil_ingeniero_delegado,
    delegado_operacion,
    liquidacion_po,
    tasa_delegado_vigente,
):
    """
    GIVEN: Un RH de delegado ya persistido.
    WHEN: Se hace PATCH con el `expediente` del item conservado.
    THEN: El RH se sincroniza y el expediente se persiste con el mismo RH.
    """
    liquidacion, detalle = liquidacion_po

    crear_flujo_delegado.crear(
        _payload_delegado(
            cip=perfil_ingeniero_delegado.cip,
            periodo=2026,
            mes=1,
            items=[
                {
                    "liquidacion_general_id": str(liquidacion.id),
                    "especialidad_revision_id": str(detalle.especialidad_id),
                    "periodo": 2026,
                    "mes": 1,
                }
            ],
            delegado_operacion_id=str(delegado_operacion.id),
        )
    )
    rh = ReciboHonorarioDelegadoMensual.objects.first()
    detalle_persistido = rh.detalles.first()

    resultado = actualizar_flujo_delegado.actualizar(
        rh.id,
        _payload_actualizar_delegado(
            cip=perfil_ingeniero_delegado.cip,
            periodo=2026,
            mes=1,
            items=[
                {
                    "liquidacion_general_id": str(liquidacion.id),
                    "especialidad_revision_id": str(detalle.especialidad_id),
                    "detalle_id": str(detalle_persistido.id),
                    "expediente": "EXP-PATCH-001",
                }
            ],
            delegado_operacion_id=str(delegado_operacion.id),
        ),
    )

    liquidacion.refresh_from_db()
    assert liquidacion.expediente == "EXP-PATCH-001"
    rh.refresh_from_db()
    assert rh.detalles.count() == 1
    assert resultado.items[0].exp_liqui == "EXP-PATCH-001"


# ── B6 · Create inspector persiste el expediente de la IO ───────────────────────


@pytest.mark.django_db
def test_crear_inspector_persiste_el_expediente_de_la_io(
    crear_flujo_inspector,
    perfil_ingeniero_inspector,
    escala_descuento,
    liquidacion_io,
    liquidacion_inspector,
):
    """
    GIVEN: Un RH de inspector con una IO seleccionada.
    WHEN: El payload incluye el `expediente` de esa IO.
    THEN: El expediente queda en la LiquidacionGeneral de la IO.
    """
    liquidacion, io = liquidacion_io

    resultado = crear_flujo_inspector.crear(
        _payload_inspector(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026,
            mes=1,
            items=[
                {
                    "liquidacion_categoria_visitas_id": str(io.id),
                    "cantidad_visitas": 3,
                    "expediente": "EXP-IO-NUEVO-001",
                }
            ],
        )
    )

    liquidacion.refresh_from_db()
    assert liquidacion.expediente == "EXP-IO-NUEVO-001"
    assert ReciboHonorarioInspectorMensual.objects.count() == 1
    assert resultado.items[0].exp_liqui == "EXP-IO-NUEVO-001"


# ── B7 · PATCH inspector persiste el expediente ─────────────────────────────────


@pytest.mark.django_db
def test_patch_inspector_persiste_el_expediente_en_la_misma_transaccion(
    crear_flujo_inspector,
    actualizar_flujo_inspector,
    perfil_ingeniero_inspector,
    escala_descuento,
    liquidacion_io,
    liquidacion_inspector,
):
    """
    GIVEN: Un RH de inspector ya persistido.
    WHEN: Se hace PATCH con el `expediente` del item conservado.
    THEN: El RH se sincroniza y el expediente se persiste con el mismo RH.
    """
    liquidacion, io = liquidacion_io

    crear_flujo_inspector.crear(
        _payload_inspector(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026,
            mes=1,
            items=[
                {
                    "liquidacion_categoria_visitas_id": str(io.id),
                    "cantidad_visitas": 3,
                }
            ],
        )
    )
    rh = ReciboHonorarioInspectorMensual.objects.first()
    detalle_persistido = rh.detalles.first()

    resultado = actualizar_flujo_inspector.actualizar(
        rh.id,
        _payload_actualizar_inspector(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026,
            mes=1,
            items=[
                {
                    "liquidacion_categoria_visitas_id": str(io.id),
                    "cantidad_visitas": 3,
                    "detalle_id": str(detalle_persistido.id),
                    "expediente": "EXP-IO-PATCH-001",
                }
            ],
        ),
    )

    liquidacion.refresh_from_db()
    assert liquidacion.expediente == "EXP-IO-PATCH-001"
    rh.refresh_from_db()
    assert rh.detalles.count() == 1
    assert resultado.items[0].exp_liqui == "EXP-IO-PATCH-001"


# ── B8 · Payload sin expediente: nada cambia ────────────────────────────────────


@pytest.mark.django_db
def test_crear_delegado_sin_expediente_no_altera_ninguna_liquidacion(
    crear_flujo_delegado,
    perfil_ingeniero_delegado,
    delegado_operacion,
    liquidacion_po,
    tasa_delegado_vigente,
):
    """
    GIVEN: Un cliente antiguo que NO envía el campo `expediente`.
    WHEN: Se guarda el RH.
    THEN: Ningún expediente cambia y el RH se guarda normal.
    """
    liquidacion, detalle = liquidacion_po
    actualizado_en = liquidacion.updated_at

    resultado = crear_flujo_delegado.crear(
        _payload_delegado(
            cip=perfil_ingeniero_delegado.cip,
            periodo=2026,
            mes=1,
            items=[
                {
                    "liquidacion_general_id": str(liquidacion.id),
                    "especialidad_revision_id": str(detalle.especialidad_id),
                    "periodo": 2026,
                    "mes": 1,
                }
            ],
            delegado_operacion_id=str(delegado_operacion.id),
        )
    )

    assert ReciboHonorarioDelegadoMensual.objects.count() == 1
    liquidacion.refresh_from_db()
    assert liquidacion.expediente == "EXP-PO-001"
    assert liquidacion.updated_at == actualizado_en
    assert resultado.items[0].exp_liqui == "EXP-PO-001"


# ── B9 · La cotización no persiste el expediente ───────────────────────────────


@pytest.mark.django_db
def test_cotizar_delegado_con_expediente_no_persiste_y_muestra_el_persistido(
    cotizar_flujo_delegado,
    perfil_ingeniero_delegado,
    delegado_operacion,
    liquidacion_po,
    tasa_delegado_vigente,
):
    """
    GIVEN: Un payload de cotización con un `expediente` distinto del persistido.
    WHEN: Se cotiza.
    THEN: No se persiste el expediente y la respuesta muestra el PERSISTIDO.
    """
    liquidacion, detalle = liquidacion_po

    resultado = cotizar_flujo_delegado.cotizar(
        _payload_delegado(
            cip=perfil_ingeniero_delegado.cip,
            periodo=2026,
            mes=1,
            items=[
                {
                    "liquidacion_general_id": str(liquidacion.id),
                    "especialidad_revision_id": str(detalle.especialidad_id),
                    "periodo": 2026,
                    "mes": 1,
                    "expediente": "EXP-SOLO-COTIZACION",
                }
            ],
            delegado_operacion_id=str(delegado_operacion.id),
        )
    )

    liquidacion.refresh_from_db()
    assert liquidacion.expediente == "EXP-PO-001"
    assert resultado.items[0].exp_liqui == "EXP-PO-001"


# ── B10 · Semántica por liquidación ─────────────────────────────────────────────


@pytest.mark.django_db
def test_crear_delegado_con_dos_expedientes_conserva_el_expediente_por_liquidacion(
    crear_flujo_delegado,
    perfil_ingeniero_delegado,
    delegado_operacion,
    liquidacion_po,
    segunda_liquidacion_po,
    tasa_delegado_vigente,
):
    """
    GIVEN: Un RH de delegado con 2 liquidaciones.
    WHEN: Cada item lleva su propio `expediente`.
    THEN: Cada liquidación conserva el suyo y la ASIGNACIÓN al delegado no
          almacena el expediente (es por liquidación, no metadata compartida).
    """
    liquidacion_1, detalle_1 = liquidacion_po
    liquidacion_2, detalle_2 = segunda_liquidacion_po

    crear_flujo_delegado.crear(
        _payload_delegado(
            cip=perfil_ingeniero_delegado.cip,
            periodo=2026,
            mes=2,
            items=[
                {
                    "liquidacion_general_id": str(liquidacion_1.id),
                    "especialidad_revision_id": str(detalle_1.especialidad_id),
                    "periodo": 2026,
                    "mes": 2,
                    "expediente": "EXP-DOS-001",
                },
                {
                    "liquidacion_general_id": str(liquidacion_2.id),
                    "especialidad_revision_id": str(detalle_2.especialidad_id),
                    "periodo": 2026,
                    "mes": 2,
                    "expediente": "EXP-DOS-002",
                },
            ],
            delegado_operacion_id=str(delegado_operacion.id),
        )
    )

    liquidacion_1.refresh_from_db()
    liquidacion_2.refresh_from_db()
    assert liquidacion_1.expediente == "EXP-DOS-001"
    assert liquidacion_2.expediente == "EXP-DOS-002"

    # La asignación al delegado NO guarda el expediente.
    assert "expediente" not in [
        field.name for field in LiquidacionDelegado._meta.get_fields()
    ]


# ── Extra · Limpiar el expediente (valor vacío) ────────────────────────────────


@pytest.mark.django_db
def test_crear_delegado_con_expediente_vacio_limpia_el_expediente(
    crear_flujo_delegado,
    perfil_ingeniero_delegado,
    delegado_operacion,
    liquidacion_po,
    tasa_delegado_vigente,
):
    """
    GIVEN: Una liquidación con expediente "EXP-PO-001".
    WHEN: El payload envía `expediente` vacío (limpiar).
    THEN: El expediente queda vacío en la LiquidacionGeneral.
    """
    liquidacion, detalle = liquidacion_po

    resultado = crear_flujo_delegado.crear(
        _payload_delegado(
            cip=perfil_ingeniero_delegado.cip,
            periodo=2026,
            mes=1,
            items=[
                {
                    "liquidacion_general_id": str(liquidacion.id),
                    "especialidad_revision_id": str(detalle.especialidad_id),
                    "periodo": 2026,
                    "mes": 1,
                    "expediente": "",
                }
            ],
            delegado_operacion_id=str(delegado_operacion.id),
        )
    )

    liquidacion.refresh_from_db()
    assert liquidacion.expediente == ""
    assert resultado.items[0].exp_liqui == ""


# ── Extra · El inspector resuelve por IO, no por el expediente nuevo ───────────


@pytest.mark.django_db
def test_crear_inspector_resuelve_por_io_y_no_por_el_expediente_nuevo(
    crear_flujo_inspector,
    perfil_ingeniero_inspector,
    escala_descuento,
    liquidacion_io,
    segunda_liquidacion_io,
    liquidacion_inspector,
    inspector,
    especialidad_estructuras,
):
    """
    GIVEN: Dos liquidaciones de IO (una con el mismo expediente que la otra).
    WHEN: El payload lleva `liquidacion_categoria_visitas_id` + un expediente nuevo.
    THEN: Se actualiza la liquidación de ESA IO y ninguna otra.
    """
    liquidacion, io = liquidacion_io
    otra_liquidacion, _otra_io = segunda_liquidacion_io
    # La otra liquidación comparte el expediente: no debe ser la que se actualiza.
    otra_liquidacion.expediente = liquidacion.expediente
    otra_liquidacion.save(update_fields=["expediente"])

    crear_flujo_inspector.crear(
        _payload_inspector(
            cip=perfil_ingeniero_inspector.cip,
            periodo=2026,
            mes=1,
            items=[
                {
                    "liquidacion_categoria_visitas_id": str(io.id),
                    "cantidad_visitas": 3,
                    "expediente": "EXP-IO-EDITADO",
                }
            ],
        )
    )

    liquidacion.refresh_from_db()
    otra_liquidacion.refresh_from_db()
    assert liquidacion.expediente == "EXP-IO-EDITADO"
    assert otra_liquidacion.expediente == "EXP-IO-001"


# ── Extra · Expediente ambiguo en el flujo manual del inspector ─────────────────


@pytest.mark.django_db
def test_crear_inspector_con_expediente_ambiguo_responde_409(
    crear_flujo_inspector,
    perfil_ingeniero_inspector,
    escala_descuento,
    crear_liquidacion_io,
    proyecto,
    segundo_proyecto,
    inspector,
    especialidad_estructuras,
):
    """
    GIVEN: Dos liquidaciones de IO que comparten el mismo expediente.
    WHEN: El payload identifica la liquidación por `exp_liqui` (flujo manual).
    THEN: 409 (resolución ambigua): nunca se escribe sobre una liquidación
          arbitraria.
    """
    liquidacion_1, io_1 = crear_liquidacion_io(proyecto, expediente="EXP-DUP-001")
    liquidacion_2, io_2 = crear_liquidacion_io(
        segundo_proyecto, expediente="EXP-DUP-001"
    )
    # Ambas IOs están asociadas al inspector: el flujo llega a la resolución
    # del expediente sin fallar antes por otra regla.
    LiquidacionInspector.objects.create(
        liquidacion=io_1,
        inspector=inspector,
        especialidad_revision=especialidad_estructuras,
    )
    LiquidacionInspector.objects.create(
        liquidacion=io_2,
        inspector=inspector,
        especialidad_revision=especialidad_estructuras,
    )

    with pytest.raises(ConflictError) as excepcion:
        crear_flujo_inspector.crear(
            _payload_inspector(
                cip=perfil_ingeniero_inspector.cip,
                periodo=2026,
                mes=1,
                items=[
                    {
                        "exp_liqui": "EXP-DUP-001",
                        "cantidad_visitas": 3,
                        "expediente": "EXP-DUP-EDITADO",
                    }
                ],
            )
        )

    assert excepcion.value.status_code == 409
    assert excepcion.value.code == "LIQUIDACION_AMBIGUA"
    assert ReciboHonorarioInspectorMensual.objects.count() == 0
    liquidacion_1.refresh_from_db()
    liquidacion_2.refresh_from_db()
    assert liquidacion_1.expediente == "EXP-DUP-001"
    assert liquidacion_2.expediente == "EXP-DUP-001"
