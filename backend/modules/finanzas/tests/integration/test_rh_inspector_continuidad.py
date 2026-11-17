"""
Integration tests for the CONDITIONAL RH BASE with Continuidad de visitas
(change `io-continuidad-visitas-impacto`).

R5: la cotización del RH mensual y el listado de candidatas de inspector deben
resolver la base con la MISMA regla y el MISMO resolver:

    base_rh = continuidad.monto_acumulado   # IO con fila de continuidad
    base_rh = liquidacion_general.sub_total  # IO normal (comportamiento vigente)

Este test es el de PARIDAD: si uno de los dos caminos deja de usar el resolver
compartido, la comparación falla.
"""
import pytest
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from modules.entidades.domain.models import Entidad
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.entidades.domain.models.ubigeo import (
    UbigeoDepartamento,
    UbigeoDistrito,
    UbigeoProvincia,
)
from modules.finanzas.domain.models.descuento_inspector import (
    EscalaDescuentoInspector,
    RangoDescuentoInspector,
)
from modules.finanzas.domain.models.detalle_honorario_inspector import (
    DetalleHonorarioInspector,
)
from modules.finanzas.domain.schemas import RHInspectorCotizarIn, RHInspectorCotizarItemIn
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.services.flujos.rh_inspector_mensual_flujo import (
    RHInspectorMensualCotizarFlujo,
    RHInspectorMensualCrearFlujo,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion as TipoLiquidacionConst
from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    LiquidacionInspector,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionContinuidadVisitas,
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.domain.models.tipo_liquidacion import (
    TipoLiquidacion as TipoLiquidacionModel,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    PerfilIngeniero,
    EspecialidadRevision,
)


@pytest.fixture
def escala_descuento(db):
    """Escala vigente sin descuento (para aislar el cálculo de la base)."""
    escala = EscalaDescuentoInspector.objects.create(
        nombre="Escala Continuidad",
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    RangoDescuentoInspector.objects.create(
        escala=escala,
        monto_minimo=Decimal("0"),
        monto_maximo=None,
        porcentaje_descuento=Decimal("0"),
    )
    return escala


@pytest.fixture
def ubigeo(db):
    depto = UbigeoDepartamento.objects.create(nombre="LIMA")
    provincia = UbigeoProvincia.objects.create(departamento=depto, nombre="LIMA")
    distrito = UbigeoDistrito.objects.create(
        provincia=provincia, nombre="MIRAFLORES", ubigeo="150132"
    )
    return distrito


@pytest.fixture
def municipalidad(db, ubigeo):
    return Municipalidad.objects.create(
        codigo="M900", nombre="Municipalidad Continuidad", distrito=ubigeo
    )


@pytest.fixture
def proyecto(db, municipalidad, ubigeo):
    entidad = Entidad.objects.create(
        tipo_documento="RUC", numero_documento="20777777777"
    )
    return Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Propietario Continuidad",
        direccion="Av. Continuidad 900",
        distrito_id=ubigeo.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20777777777",
        entidad_razon_social="Propietario Continuidad",
    )


@pytest.fixture
def inspector(db):
    perfil = PerfilIngeniero.objects.create(
        cip="990011",
        dni="99001122",
        nombres="Inspector",
        apellido_paterno="Continuidad",
        apellido_materno="Test",
        correo_personal="inspector_rh_continuidad@example.com",
    )
    return Inspector.objects.create(perfil_ingeniero=perfil)


@pytest.fixture
def liquidacion_io(db, proyecto, municipalidad, inspector):
    """
    IO con 10 visitas, sub_total = 1000.00 (IO NORMAL, sin continuidad).

    El inspector queda asociado a la LCV.
    """
    User = get_user_model()
    usuario = User.objects.create_user(
        username="rh_cont", email="rh_cont@test.com", password="x", dni="55667788"
    )
    tipo_io = TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacionConst.INSPECCION_OBRA,
        defaults={"nombre": "Inspección de Obra"},
    )[0]
    base = TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_io,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )
    tarifa = TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=base,
        porcentaje_uit=Decimal("0.05"),
        categoria_visitas="A",
    )
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_io,
        usuario_creador=usuario,
        expediente="EXP-RH-CONT-001",
        estado="PENDIENTE",
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
    )
    LiquidacionInspeccionObra.objects.create(liquidacion=lg)
    lcv = LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg,
        cantidad_visitas=10,
        porcentaje_uit=Decimal("0.05"),
        categoria="A",
        tarifa_aplicada=tarifa,
    )
    esp_rev = EspecialidadRevision.objects.create(
        slug="cont", nombre="Continuidad"
    )
    LiquidacionInspector.objects.create(
        liquidacion=lcv,
        inspector=inspector,
        especialidad_revision=esp_rev,
    )
    return {"lg": lg, "lcv": lcv, "inspector": inspector}


@pytest.fixture
def proyecto_previa(db, municipalidad, ubigeo):
    """
    Proyecto de la liquidación PREVIA (A).

    `LiquidacionGeneral.proyecto` es un OneToOneField: cada liquidación necesita
    su propio Proyecto (compartirlo viola la unicidad de `proyecto_id`).
    """
    return Proyecto.objects.create(
        nombre_propietario="Propietario Previo Continuidad",
        direccion="Av. Previa 100",
        distrito_id=ubigeo.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20777777778",
        entidad_razon_social="Propietario Previo Continuidad",
    )


@pytest.fixture
def liquidacion_io_previa(db, liquidacion_io, proyecto_previa, municipalidad, inspector):
    """
    IO PREVIA (A): 10 visitas, sub_total = 1000.00, SIN fila de continuidad.

    Es la liquidación que la continuidad de B referencia como `liquidacion_previa`.
    Comparte tarifa con la IO principal (es un catálogo), pero necesita su
    propio Proyecto.
    """
    User = get_user_model()
    usuario = User.objects.create_user(
        username="rh_cont_previa",
        email="rh_cont_previa@test.com",
        password="x",
        dni="55667799",
    )
    tipo_io = TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacionConst.INSPECCION_OBRA,
        defaults={"nombre": "Inspección de Obra"},
    )[0]
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto_previa,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_io,
        usuario_creador=usuario,
        expediente="EXP-RH-CONT-PREV-001",
        estado="PENDIENTE",
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
    )
    LiquidacionInspeccionObra.objects.create(liquidacion=lg)
    lcv = LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg,
        cantidad_visitas=10,
        porcentaje_uit=Decimal("0.05"),
        categoria="A",
        tarifa_aplicada=liquidacion_io["lcv"].tarifa_aplicada,
    )
    esp_rev = EspecialidadRevision.objects.create(
        slug="cont-prev", nombre="Continuidad Previa"
    )
    LiquidacionInspector.objects.create(
        liquidacion=lcv,
        inspector=inspector,
        especialidad_revision=esp_rev,
    )
    return {"lg": lg, "lcv": lcv, "inspector": inspector}


@pytest.fixture
def core_service(db):
    return FinanzasCoreService()


@pytest.fixture
def cotizar_flujo(core_service):
    return RHInspectorMensualCotizarFlujo(core=core_service)


@pytest.fixture
def crear_flujo(core_service, cotizar_flujo):
    return RHInspectorMensualCrearFlujo(core=core_service, cotizar_flujo=cotizar_flujo)


def _cotizar(cotizar_flujo, lcv, inspector, cantidad=2):
    payload = RHInspectorCotizarIn(
        cip=inspector.perfil_ingeniero.cip,
        periodo=2026,
        mes=1,
        items=[
            RHInspectorCotizarItemIn(
                liquidacion_categoria_visitas_id=str(lcv.id),
                cantidad_visitas=cantidad,
            )
        ],
    )
    return cotizar_flujo.cotizar(payload)


# ── IO NORMAL: la base sigue siendo `liquidacion_general.sub_total` ────────


@pytest.mark.django_db
def test_rh_sin_continuidad_usa_sub_total(
    liquidacion_io, cotizar_flujo, core_service, escala_descuento
):
    """
    GIVEN: una IO normal (10 visitas, sub_total = 1000.00, sin continuidad).
    THEN: la cotización RH usa 1000.00 como base → costo por inspección 100.00,
          y las candidatas muestran el MISMO valor.
    """
    lcv = liquidacion_io["lcv"]
    inspector = liquidacion_io["inspector"]

    result = _cotizar(cotizar_flujo, lcv, inspector, cantidad=2)
    item = result.items[0]

    assert item.importe_bruto == Decimal("1000.00")
    assert item.costo_por_inspeccion == Decimal("100.00")

    candidatas = core_service.list_liquidaciones_inspector_candidatas(
        inspector_id=inspector.id
    )
    assert len(candidatas) == 1
    assert candidatas[0]["total_liquidacion"] == Decimal("1000.00")
    assert candidatas[0]["costo_por_inspeccion"] == Decimal("100.00")

    # PARIDAD: ambos caminos coinciden bit a bit.
    assert item.costo_por_inspeccion == candidatas[0]["costo_por_inspeccion"]
    assert item.importe_bruto == candidatas[0]["total_liquidacion"]


# ── IO CON CONTINUIDAD: la base pasa a ser `continuidad.monto_acumulado` ──


@pytest.mark.django_db
def test_rh_con_continuidad_usa_monto_acumulado(
    liquidacion_io, cotizar_flujo, core_service, escala_descuento
):
    """
    GIVEN: una IO con continuidad cuyo `sub_total` = 400.00 (la diferencia) y
           `monto_acumulado` = 1000.00 (el valor completo del trabajo).
    THEN: la cotización RH y las candidatas usan 1000.00 (NO 400.00), con el
          mismo costo por inspección (100.00).
    """
    lcv = liquidacion_io["lcv"]
    inspector = liquidacion_io["inspector"]
    liquidacion_io["lg"].sub_total = Decimal("400.00")
    liquidacion_io["lg"].total = Decimal("472.00")
    liquidacion_io["lg"].save(update_fields=["sub_total", "total"])

    LiquidacionContinuidadVisitas.objects.create(
        liquidacion_visitas=lcv,
        monto_acumulado=Decimal("1000.00"),
        total_acumulado=Decimal("1180.00"),
        subtotal_credito=Decimal("600.00"),
        total_credito=Decimal("708.00"),
    )

    result = _cotizar(cotizar_flujo, lcv, inspector, cantidad=2)
    item = result.items[0]

    # La base del RH es el valor completo del trabajo, no la diferencia.
    assert item.importe_bruto == Decimal("1000.00")
    assert item.costo_por_inspeccion == Decimal("100.00")
    assert item.monto_contribuido == Decimal("200.00")

    candidatas = core_service.list_liquidaciones_inspector_candidatas(
        inspector_id=inspector.id
    )
    assert len(candidatas) == 1
    assert candidatas[0]["total_liquidacion"] == Decimal("1000.00")
    assert candidatas[0]["costo_por_inspeccion"] == Decimal("100.00")

    # PARIDAD entre cotización RH y candidatas.
    assert item.costo_por_inspeccion == candidatas[0]["costo_por_inspeccion"]
    assert item.importe_bruto == candidatas[0]["total_liquidacion"]


@pytest.mark.django_db
def test_candidatas_paginadas_usan_la_misma_base(
    liquidacion_io, core_service, escala_descuento
):
    """
    GIVEN: la misma IO con continuidad.
    THEN: la variante PAGINADA de candidatas también usa `monto_acumulado`.
    """
    lcv = liquidacion_io["lcv"]
    inspector = liquidacion_io["inspector"]
    liquidacion_io["lg"].sub_total = Decimal("400.00")
    liquidacion_io["lg"].save(update_fields=["sub_total"])

    LiquidacionContinuidadVisitas.objects.create(
        liquidacion_visitas=lcv,
        monto_acumulado=Decimal("1000.00"),
        total_acumulado=Decimal("1180.00"),
        subtotal_credito=Decimal("600.00"),
        total_credito=Decimal("708.00"),
    )

    candidatas, total = core_service.list_liquidaciones_inspector_candidatas_paginated(
        inspector_id=inspector.id,
        page=1,
        page_size=10,
    )

    assert total == 1
    assert len(candidatas) == 1
    assert candidatas[0]["total_liquidacion"] == Decimal("1000.00")
    assert candidatas[0]["costo_por_inspeccion"] == Decimal("100.00")


# ── Paridad estricta entre los TRES puntos de lectura de la base RH ───────


@pytest.mark.django_db
def test_paridad_entre_cotizacion_y_las_dos_variantes_de_candidatas(
    liquidacion_io, cotizar_flujo, core_service, escala_descuento
):
    """
    GIVEN: una IO con continuidad (`monto_acumulado` = 1000.00,
           `sub_total` = 400.00 = la diferencia a cobrar).
    WHEN:  se cotiza el RH y se listan las candidatas (con y sin paginación).
    THEN:  los TRES puntos de lectura devuelven EXACTAMENTE la misma base y el
           mismo costo por inspección — hay UNA sola regla (`resolver_base_rh`).
    """
    lcv = liquidacion_io["lcv"]
    inspector = liquidacion_io["inspector"]
    liquidacion_io["lg"].sub_total = Decimal("400.00")
    liquidacion_io["lg"].save(update_fields=["sub_total"])

    LiquidacionContinuidadVisitas.objects.create(
        liquidacion_visitas=lcv,
        monto_acumulado=Decimal("1000.00"),
        total_acumulado=Decimal("1180.00"),
        subtotal_credito=Decimal("600.00"),
        total_credito=Decimal("708.00"),
    )

    item = _cotizar(cotizar_flujo, lcv, inspector, cantidad=2).items[0]

    candidatas = core_service.list_liquidaciones_inspector_candidatas(
        inspector_id=inspector.id
    )
    paginadas, total = core_service.list_liquidaciones_inspector_candidatas_paginated(
        inspector_id=inspector.id,
        page=1,
        page_size=10,
    )

    assert total == 1
    assert len(candidatas) == 1
    assert len(paginadas) == 1

    # La BASE es la misma en los tres caminos de lectura.
    assert item.importe_bruto == Decimal("1000.00")
    assert candidatas[0]["total_liquidacion"] == Decimal("1000.00")
    assert paginadas[0]["total_liquidacion"] == Decimal("1000.00")

    # Y el COSTO POR INSPECCIÓN también (regla única, sin descuadre RH ↔ candidata).
    assert item.costo_por_inspeccion == Decimal("100.00")
    assert candidatas[0]["costo_por_inspeccion"] == item.costo_por_inspeccion
    assert paginadas[0]["costo_por_inspeccion"] == item.costo_por_inspeccion


@pytest.mark.django_db
def test_candidatas_exponen_la_misma_base_en_todos_los_campos_monetarios(
    liquidacion_io, core_service
):
    """
    GIVEN: una IO con continuidad (`sub_total` = 400.00, `monto_acumulado` = 1000.00).
    THEN:  TODOS los campos monetarios expuestos por las candidatas (variante no
           paginada y paginada) derivan de la MISMA base condicional (1000.00),
           no de la diferencia persistida en la cabecera de B (400.00).
    """
    lcv = liquidacion_io["lcv"]
    inspector = liquidacion_io["inspector"]
    liquidacion_io["lg"].sub_total = Decimal("400.00")
    liquidacion_io["lg"].save(update_fields=["sub_total"])

    LiquidacionContinuidadVisitas.objects.create(
        liquidacion_visitas=lcv,
        monto_acumulado=Decimal("1000.00"),
        total_acumulado=Decimal("1180.00"),
        subtotal_credito=Decimal("600.00"),
        total_credito=Decimal("708.00"),
    )

    candidatas = core_service.list_liquidaciones_inspector_candidatas(
        inspector_id=inspector.id
    )
    paginadas, _ = core_service.list_liquidaciones_inspector_candidatas_paginated(
        inspector_id=inspector.id,
        page=1,
        page_size=10,
    )

    assert len(candidatas) == 1
    assert len(paginadas) == 1

    for candidata in (candidatas[0], paginadas[0]):
        assert candidata["total_liquidacion"] == Decimal("1000.00")
        assert candidata["sub_total_liquidacion"] == Decimal("1000.00")
        assert candidata["costo_por_inspeccion"] == Decimal("100.00")
        # NO es la diferencia persistida en la cabecera de B.
        assert candidata["total_liquidacion"] != Decimal("400.00")
        assert candidata["sub_total_liquidacion"] != Decimal("400.00")


# ── El `DetalleHonorario` persistido congela la MISMA base ────────────────


@pytest.mark.django_db
def test_rh_creado_persiste_la_base_condicional_en_el_detalle_honorario(
    liquidacion_io, crear_flujo, escala_descuento
):
    """
    GIVEN: una IO con continuidad (`sub_total` = 400.00 = diferencia,
           `monto_acumulado` = 1000.00 = valor completo del trabajo).
    WHEN:  se CREA el RH mensual del inspector sobre esa IO.
    THEN:  el `DetalleHonorarioInspector` persistido CONGELA la base condicional
           (1000.00) — la misma que muestran las candidatas — y no la diferencia
           de la cabecera (400.00).
    """
    lcv = liquidacion_io["lcv"]
    inspector = liquidacion_io["inspector"]
    liquidacion_io["lg"].sub_total = Decimal("400.00")
    liquidacion_io["lg"].total = Decimal("472.00")
    liquidacion_io["lg"].save(update_fields=["sub_total", "total"])

    LiquidacionContinuidadVisitas.objects.create(
        liquidacion_visitas=lcv,
        monto_acumulado=Decimal("1000.00"),
        total_acumulado=Decimal("1180.00"),
        subtotal_credito=Decimal("600.00"),
        total_credito=Decimal("708.00"),
    )

    payload = RHInspectorCotizarIn(
        cip=inspector.perfil_ingeniero.cip,
        periodo=2026,
        mes=1,
        items=[
            RHInspectorCotizarItemIn(
                liquidacion_categoria_visitas_id=str(lcv.id),
                cantidad_visitas=2,
            )
        ],
    )
    resultado = crear_flujo.crear(payload)

    detalle_id = resultado.items[0].detalle_id
    assert detalle_id is not None
    detalle = DetalleHonorarioInspector.objects.get(id=detalle_id)

    # La base congelada es la condicional (valor completo del trabajo).
    assert detalle.importe_bruto == Decimal("1000.00")
    assert detalle.costo_por_inspeccion == Decimal("100.00")
    assert detalle.monto_contribuido == Decimal("200.00")
    # NO es la diferencia persistida en la cabecera de B.
    assert detalle.importe_bruto != Decimal("400.00")


# ── Sin overlay de RH sobre la liquidación previa (A) ─────────────────────


@pytest.mark.django_db
def test_la_liquidacion_previa_no_sufre_overlay_de_saldo(
    liquidacion_io, liquidacion_io_previa, core_service
):
    """
    GIVEN: B tiene continuidad que referencia a A (10 visitas, 3 pendientes).
    THEN:  el saldo disponible de A NO se reduce (NO hay overlay de RH sobre A):
           sigue siendo 10 y A conserva su propia base (`sub_total`).
           B, por su parte, usa `monto_acumulado` (1000.00) y no la diferencia
           de su cabecera (400.00).
    """
    lg_a = liquidacion_io_previa["lg"]
    lg_b = liquidacion_io["lg"]
    inspector = liquidacion_io["inspector"]

    lg_b.sub_total = Decimal("400.00")
    lg_b.total = Decimal("472.00")
    lg_b.save(update_fields=["sub_total", "total"])

    LiquidacionContinuidadVisitas.objects.create(
        liquidacion_visitas=liquidacion_io["lcv"],
        liquidacion_previa=lg_a,
        monto_acumulado=Decimal("1000.00"),
        total_acumulado=Decimal("1180.00"),
        subtotal_credito=Decimal("600.00"),
        total_credito=Decimal("708.00"),
        visitas_previas_totales=10,
        visitas_previas_pendientes=3,
    )

    candidatas = core_service.list_liquidaciones_inspector_candidatas(
        inspector_id=inspector.id
    )
    por_general = {c["liquidacion_general_id"]: c for c in candidatas}
    assert len(por_general) == 2

    a = por_general[str(lg_a.id)]
    b = por_general[str(lg_b.id)]

    # A NO pierde saldo por la continuidad de B (sin overlay).
    assert a["saldo_disponible"] == 10
    assert a["total_liquidacion"] == Decimal("1000.00")
    assert a["costo_por_inspeccion"] == Decimal("100.00")

    # B usa el valor completo del trabajo, no la diferencia de su cabecera.
    assert b["saldo_disponible"] == 10
    assert b["total_liquidacion"] == Decimal("1000.00")
    assert b["total_liquidacion"] != Decimal("400.00")
    assert b["costo_por_inspeccion"] == Decimal("100.00")
