"""
Tests de PRESENTACIÓN y CONSUMIDORES del motor PO de Edificaciones.

Cubre el Module 7 del change `liquidacion-po-modos-cotizacion`:

- El DETALLE y el LISTADO canónicos de Edificaciones exponen la estrategia
  persistida, sus snapshots (H, total explícito, % de tarifa, tarifa del
  padre) y la acumulación vigente (proyección informativa), con el mismo
  wrapper tipado y sin serialización ad hoc.
- La acumulación es OPCIONAL: sin diferencia, `acumulacion` es `null`.
- Modo 1 (NORMAL_SELECCIONADAS): estrategia persistida y SIN acumulación.
- Regresión de contrato: Taludes e Impacto Vial NO exponen campos de
  estrategia PO ni de acumulación (siguen usando el wrapper PO compartido).
- Regresión de edge: la liquidación edge (modo MANUAL) no expone ni persiste
  acumulación.
- Regresión de consultas: el listado NO hace una consulta por liquidación
  para resolver la acumulación (sin N+1 en el camino de lista/detalle).

Tests DB-backed (pytest-django + ORM real, fixtures existentes). Sin mocks.
NO SE EJECUTAN en este módulo: toda la ejecución queda reservada para el
Módulo 8.
"""
from decimal import Decimal
from datetime import date

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from modules.liquidaciones.domain.constants import EstrategiaCotizacionPO
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_impacto_vial import (
    LiquidacionImpactoVial,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_taludes import (
    LiquidacionTaludes,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraAcumulacion,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.tests.fixtures.factories import (
    make_payload_po_edge,
    make_payload_po_estrategia,
)


# ── Helper de comparacion de decimales ───────────────────────────────────────

def _dec(valor) -> Decimal:
    """
    Normaliza un decimal de la API a `Decimal` para compararlo con exactitud.

    La API serializa los decimales como TEXTO (contrato `BaseSchema` +
    `success_response`); el frontend los coacciona a numero con
    `z.coerce.number()`. Las aserciones comparan contra `Decimal` para no
    depender de la representacion textual ni de la precision de `float`.
    """
    return Decimal(str(valor))


# ── Constantes ─────────────────────────────────────────────────────────────────

NORMAL = EstrategiaCotizacionPO.NORMAL_SELECCIONADAS
HABILITADAS = EstrategiaCotizacionPO.TARIFA_HABILITADAS_PARTICIPANTES
TOTAL = EstrategiaCotizacionPO.TOTAL_EXPLICITO

LISTA_EDIFICACIONES = "/liquidaciones/edificaciones/"
LISTA_TALUDES = "/liquidaciones/taludes/"
LISTA_IV = "/liquidaciones/impacto-vial/"

# Nombre de la tabla de acumulación (app_label + model_name en snake_case).
TABLA_ACUMULACION = "liquidaciones_liquidacionporcentajeobraacumulacion"


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def derecho_po_sin_rangos(db):
    """
    Derecho vigente SIN piso UIT ni tope.

    Aísla la aritmética de TOTAL_EXPLICITO: con el derecho por defecto
    (piso 500.00 / 0.10 % de UIT) un total explícito de 177.00 se
    rechazaría por debajo del mínimo, que no es lo que se quiere probar aquí.
    """
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
        DerechoPorcentajeObra,
    )

    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=None,
        derecho_maximo=None,
        porcentaje_minimo_uit=Decimal("0"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def liquidacion_edificaciones_habilitadas(
    db, municipalidad, proyecto, create_user,
    derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, especialidad_estructuras,
    tipo_edificacion,
):
    """
    Liquidación de Edificaciones en TARIFA_HABILITADAS_PARTICIPANTES con su
    fila de acumulación vigente (padre 1500.00, detalle 500.00, diferencia
    1000.00 @ 0.10 %).
    """
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=create_user,
        expediente="EXP-EDIF-HABILITADAS-001",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1500.00"),
        total=Decimal("1770.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )
    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("1000000.00"),
        porcentaje_liquidacion=Decimal("0.0015"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
        estrategia_cotizacion=HABILITADAS,
        count_habilitadas=3,
        porcentaje_tarifa=Decimal("0.0005"),
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
    )
    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0005"),
        subtotal=Decimal("500.00"),
    )
    LiquidacionPorcentajeObraAcumulacion.objects.create(
        liquidacion_porcentaje=lpo,
        porcentaje_acumulado=Decimal("0.0010"),
        subtotal_acumulado=Decimal("1000.00"),
    )
    return lg


@pytest.fixture
def liquidacion_edificaciones_normal(
    db, municipalidad, proyecto, create_user,
    derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, especialidad_estructuras,
    tipo_edificacion,
):
    """Liquidación de Edificaciones en modo 1 (NORMAL_SELECCIONADAS), sin acumulación."""
    proyecto_normal = Proyecto.objects.create(
        entidad=proyecto.entidad,
        entidad_razon_social=proyecto.entidad_razon_social,
        entidad_tipo_documento=proyecto.entidad_tipo_documento,
        entidad_numero_documento=proyecto.entidad_numero_documento,
        nombre_propietario=proyecto.nombre_propietario,
        distrito=proyecto.distrito,
        urbanizacion=proyecto.urbanizacion,
        direccion=proyecto.direccion,
        descripcion=proyecto.descripcion,
    )
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto_normal,
        municipalidad=municipalidad,
        usuario_creador=create_user,
        expediente="EXP-EDIF-NORMAL-001",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )
    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=2)

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("1000000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
        estrategia_cotizacion=NORMAL,
        count_habilitadas=3,
        porcentaje_tarifa=Decimal("0.0005"),
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
    )
    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )
    return lg


@pytest.fixture
def liquidacion_taludes(
    db, municipalidad, proyecto, create_user,
    derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_taludes, especialidad_taludes, tipo_taludes,
):
    """Liquidación de Taludes: motor PO SIN estrategias."""
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=create_user,
        expediente="EXP-TALUDES-PRES-001",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_taludes,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )
    LiquidacionTaludes.objects.create(liquidacion=lg, numero=1)

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        valor_declarado=Decimal("1000000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )
    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_taludes,
        especialidad=especialidad_taludes,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )
    return lg


@pytest.fixture
def liquidacion_impacto_vial(
    db, municipalidad, proyecto, create_user,
    derecho_porcentaje_vigente, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_iv, especialidad_impacto_vial, tipo_impacto_vial,
):
    """Liquidación de Impacto Vial: motor PO SIN estrategias."""
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=create_user,
        expediente="EXP-IV-PRES-001",
        estado="PENDIENTE",
        tipo_liquidacion=tipo_impacto_vial,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )
    LiquidacionImpactoVial.objects.create(liquidacion=lg, numero=1)

    lpo = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg,
        valor_declarado=Decimal("1000000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )
    LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo,
        tarifa_aplicada=tarifa_porcentaje_obra_iv,
        especialidad=especialidad_impacto_vial,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )
    return lg


# ── Detalle y lista de Edificaciones ──────────────────────────────────────────

@pytest.mark.django_db
def test_detalle_edificaciones_expone_estrategia_snapshots_y_acumulacion(
    auth_client, liquidacion_edificaciones_habilitadas,
):
    """
    GIVEN: una liquidación de Edificaciones en TARIFA_HABILITADAS_PARTICIPANTES
           con su fila de acumulación vigente.
    WHEN:  se pide el DETALLE canónico.
    THEN:  el wrapper `liquidacion_tipo` expone la estrategia, sus snapshots y
           la acumulación (monto y porcentaje), sin campos inventados.
    """
    response = auth_client.get(
        f"/liquidaciones/edificaciones/{liquidacion_edificaciones_habilitadas.id}"
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert tipo["estrategia_cotizacion"] == HABILITADAS
    assert tipo["count_habilitadas"] == 3
    assert _dec(tipo["porcentaje_tarifa"]) == pytest.approx(Decimal("0.0005"))
    assert tipo["tarifa_aplicada_id"] is not None
    assert tipo["total_explicito"] is None

    acumulacion = tipo["acumulacion"]
    assert acumulacion is not None
    assert _dec(acumulacion["subtotal_acumulado"]) == pytest.approx(Decimal("1000.0"))
    assert _dec(acumulacion["porcentaje_acumulado"]) == pytest.approx(Decimal("0.0010"))


@pytest.mark.django_db
def test_lista_edificaciones_expone_estrategia_snapshots_y_acumulacion(
    auth_client, liquidacion_edificaciones_habilitadas,
):
    """
    GIVEN: la misma liquidación con estrategia y acumulación.
    WHEN:  se pide el LISTADO canónico.
    THEN:  el wrapper `liquidacion_tipo` del item expone los mismos campos que
           el detalle (mismo camino de presentación).
    """
    response = auth_client.get(LISTA_EDIFICACIONES)

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    items = response.json()["data"]["items"]
    assert len(items) == 1

    tipo = items[0]["liquidacion_tipo"]
    assert tipo["estrategia_cotizacion"] == HABILITADAS
    assert tipo["count_habilitadas"] == 3
    assert _dec(tipo["porcentaje_tarifa"]) == pytest.approx(Decimal("0.0005"))
    assert tipo["acumulacion"] is not None
    assert _dec(tipo["acumulacion"]["subtotal_acumulado"]) == pytest.approx(Decimal("1000.0"))


@pytest.mark.django_db
def test_detalle_edificaciones_sin_acumulacion_devuelve_null(
    auth_client, liquidacion_edificaciones_normal,
):
    """
    GIVEN: una liquidación en modo 1 (NORMAL_SELECCIONADAS), sin diferencia.
    WHEN:  se pide el DETALLE.
    THEN:  la estrategia persistida es NORMAL_SELECCIONADAS y la acumulación es
           `null` (la clave existe en el contrato, pero no hay proyección).
    """
    response = auth_client.get(
        f"/liquidaciones/edificaciones/{liquidacion_edificaciones_normal.id}"
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert tipo["estrategia_cotizacion"] == NORMAL
    assert tipo["acumulacion"] is None
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0


@pytest.mark.django_db
def test_detalle_edificaciones_total_explicito_expone_total_y_acumulacion_sin_porcentaje(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    tarifa_porcentaje_obra_estructuras, especialidad_estructuras,
    derecho_po_sin_rangos, especialidades_disponibles_edificacion,
):
    """
    GIVEN: una liquidación creada con la estrategia TOTAL_EXPLICITO.
    WHEN:  se pide el DETALLE.
    THEN:  la estrategia persistida es TOTAL_EXPLICITO, el total explícito se
           expone y la acumulación va SIN porcentaje (el total es autoritativo).
    """
    payload = make_payload_po_estrategia(
        municipalidad.id,
        municipalidad.distrito_id,
        estrategia_cotizacion=TOTAL,
        total_explicito=177.00,
        tarifas=[
            {
                "tarifa_porcentaje_obra_id": str(tarifa_porcentaje_obra_estructuras.id),
                "especialidad_id": str(especialidad_estructuras.id),
            }
        ],
    )

    create = auth_client.post(
        "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
        json=payload,
    )
    assert create.status_code == 200, f"{create.status_code}: {create.content}"

    liquidacion_id = create.json()["data"]["liquidacion_general"]["id"]
    response = auth_client.get(f"/liquidaciones/edificaciones/{liquidacion_id}")

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    assert tipo["estrategia_cotizacion"] == TOTAL
    assert _dec(tipo["total_explicito"]) == pytest.approx(Decimal("177.0"))
    assert tipo["valor_declarado"] is None
    assert tipo["acumulacion"] is not None
    assert tipo["acumulacion"]["porcentaje_acumulado"] is None


# ── Regresión de contrato: Taludes e Impacto Vial ─────────────────────────────

@pytest.mark.django_db
def test_detalle_taludes_no_expone_campos_de_estrategia(
    auth_client, liquidacion_taludes,
):
    """
    GIVEN: una liquidación de Taludes (motor PO sin estrategias).
    WHEN:  se pide el DETALLE.
    THEN:  el wrapper PO compartido NO expone ningún campo de estrategia PO.
    """
    response = auth_client.get(f"/liquidaciones/taludes/{liquidacion_taludes.id}")

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    for campo in (
        "estrategia_cotizacion",
        "count_habilitadas",
        "total_explicito",
        "porcentaje_tarifa",
        "acumulacion",
    ):
        assert campo not in tipo, f"Taludes no debe exponer '{campo}'"


@pytest.mark.django_db
def test_lista_taludes_no_expone_campos_de_estrategia(
    auth_client, liquidacion_taludes,
):
    """GIVEN/WHEN/THEN: el LISTADO de Taludes tampoco expone campos de estrategia."""
    response = auth_client.get(LISTA_TALUDES)

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    items = response.json()["data"]["items"]
    assert len(items) == 1

    tipo = items[0]["liquidacion_tipo"]
    for campo in (
        "estrategia_cotizacion",
        "count_habilitadas",
        "total_explicito",
        "porcentaje_tarifa",
        "acumulacion",
    ):
        assert campo not in tipo, f"Taludes no debe exponer '{campo}'"


@pytest.mark.django_db
def test_detalle_impacto_vial_no_expone_campos_de_estrategia(
    auth_client, liquidacion_impacto_vial,
):
    """GIVEN/WHEN/THEN: el DETALLE de Impacto Vial tampoco expone estrategia."""
    response = auth_client.get(
        f"/liquidaciones/impacto-vial/{liquidacion_impacto_vial.id}"
    )

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    tipo = response.json()["data"]["liquidacion_tipo"]

    for campo in (
        "estrategia_cotizacion",
        "count_habilitadas",
        "total_explicito",
        "porcentaje_tarifa",
        "acumulacion",
    ):
        assert campo not in tipo, f"Impacto Vial no debe exponer '{campo}'"


@pytest.mark.django_db
def test_lista_impacto_vial_no_expone_campos_de_estrategia(
    auth_client, liquidacion_impacto_vial,
):
    """GIVEN/WHEN/THEN: el LISTADO de Impacto Vial tampoco expone estrategia."""
    response = auth_client.get(LISTA_IV)

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    items = response.json()["data"]["items"]
    assert len(items) == 1

    tipo = items[0]["liquidacion_tipo"]
    for campo in (
        "estrategia_cotizacion",
        "count_habilitadas",
        "total_explicito",
        "porcentaje_tarifa",
        "acumulacion",
    ):
        assert campo not in tipo, f"Impacto Vial no debe exponer '{campo}'"


# ── Regresión de edge (modo MANUAL) ───────────────────────────────────────────

@pytest.mark.django_db
def test_lista_edificaciones_conserva_el_edge_sin_acumulacion(
    auth_client, municipalidad, igv_vigente, uit_vigente,
    especialidades_disponibles_edificacion,
):
    """
    GIVEN: una liquidación edge (modo MANUAL) de Edificaciones.
    WHEN:  se pide el LISTADO.
    THEN:  la estrategia es NORMAL_SELECCIONADAS, la acumulación es `null` y no
           existe fila de acumulación persistida.
    """
    payload = make_payload_po_edge(
        municipalidad.id,
        municipalidad.distrito_id,
        subtotal_manual=1000.00,
    )
    create = auth_client.post("/liquidaciones/edificaciones/edge", json=payload)
    assert create.status_code == 200, f"{create.status_code}: {create.content}"

    response = auth_client.get(LISTA_EDIFICACIONES)
    assert response.status_code == 200, f"{response.status_code}: {response.content}"

    items = response.json()["data"]["items"]
    assert len(items) == 1

    tipo = items[0]["liquidacion_tipo"]
    assert tipo["estrategia_cotizacion"] == NORMAL
    assert tipo["acumulacion"] is None
    assert LiquidacionPorcentajeObraAcumulacion.objects.count() == 0


# ── Regresión de consultas (sin N+1 por la acumulación) ───────────────────────

@pytest.mark.django_db
def test_lista_edificaciones_no_hace_una_consulta_por_liquidacion_por_la_acumulacion(
    auth_client,
    liquidacion_edificaciones_habilitadas,
    liquidacion_edificaciones_normal,
):
    """
    GIVEN: dos liquidaciones de Edificaciones (una con acumulación y otra sin ella).
    WHEN:  se pide el LISTADO y se cuentan las consultas sobre la tabla de
           acumulación.
    THEN:  el número de consultas a esa tabla NO crece con el número de
           liquidaciones (como máximo una, la del prefetch).

    REQUISITO PENDIENTE DE APLICAR (fuera de las raíces editables de este
    módulo): la cadena de prefetch de Edificaciones debe incluir
    `liquidacion_porcentaje_obra__acumulacion`. Sin eso, el presenter resuelve
    la acumulación con una consulta por liquidación (N+1) en el camino de lista
    y de detalle.
    """
    with CaptureQueriesContext(connection) as ctx:
        response = auth_client.get(LISTA_EDIFICACIONES)

    assert response.status_code == 200, f"{response.status_code}: {response.content}"
    assert len(response.json()["data"]["items"]) == 2

    consultas_acumulacion = [
        q for q in ctx.captured_queries if TABLA_ACUMULACION in q["sql"].lower()
    ]

    assert len(consultas_acumulacion) <= 1, (
        "El listado de Edificaciones no debe resolver la acumulación con una "
        "consulta por liquidación (N+1). "
        f"Se ejecutaron {len(consultas_acumulacion)} consultas sobre "
        f"{TABLA_ACUMULACION}."
    )
