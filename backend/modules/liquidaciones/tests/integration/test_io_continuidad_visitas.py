"""
Integration tests for the CONTINUIDAD of visitas de Inspección de Obra
(change `io-continuidad-visitas-impacto`).

Cubre el contrato funcional:

- R2  `B.cantidad_visitas` = SOLO las visitas nuevas del inspector de B.
- R3  `B.sub_total` / `B.total` = la DIFERENCIA a cobrar (neto / con IGV).
- R4  La fila de continuidad (OneToOne sobre la LCV de B) persiste
      `monto_acumulado` (neto completo, calculado por el servidor) y
      `total_acumulado` (bruto), separados de `subtotal_credito`/`total_credito`.
- R5  La base del RH es condicional y la resuelve UN único resolver.
- R7  Sin fila de continuidad el comportamiento de IO es idéntico al vigente.
- R8  Editar B después recalcula la continuidad y reaplica la diferencia.
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.domain.constants import EstadoLiquidacion
from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    InspectorOperacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionContinuidadVisitas,
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_continuidad_visitas_core_service import (
    LiquidacionContinuidadVisitasCoreService,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    PerfilIngeniero,
    EspecialidadRevision,
)

# ── Constantes del escenario ──────────────────────────────────────────────
# UIT = 5150.00 · porcentaje_uit = 0.05 → costo por visita = 257.50
# IGV = 18%
COSTO_POR_VISITA = Decimal("257.50")
IGV = Decimal("0.18")


@pytest.fixture
def inspector_io(db, tipo_edificacion):
    """Inspector con operación EDIFICACION (tipo que el inspector puede revisar)."""
    perfil = PerfilIngeniero.objects.create(
        cip="778899",
        dni="77889900",
        nombres="Inspector",
        apellido_paterno="Continuidad",
        apellido_materno="Test",
        correo_personal="inspector_continuidad@example.com",
    )
    inspector = Inspector.objects.create(perfil_ingeniero=perfil)
    esp_rev = EspecialidadRevision.objects.create(
        slug="continuidad", nombre="Continuidad"
    )
    op = InspectorOperacion.objects.create(
        inspector=inspector,
        tipo_liquidacion=tipo_edificacion,
        categoria="1",
        especialidad_revision=esp_rev,
    )
    inspector.inspector_operacion_id = op.id
    return inspector


@pytest.fixture
def payload_io(db, municipalidad, ubigeo_distrito, tarifa_visitas_io, inspector_io):
    """Payload base de creación de IO (sin bloque de continuidad)."""
    return {
        "liquidacion_general": {
            "municipalidad_id": str(municipalidad.id),
            "expediente": "EXP-IO-CONT-001",
            "observacion": "Observación continuidad",
            "retencion": False,
            "denominacion_de_proyecto": "Proyecto IO continuidad",
            "proyecto": {
                "nombre_propietario": "Propietario Continuidad",
                "direccion": "Av. Continuidad 123",
                "distrito_id": str(ubigeo_distrito.id),
                "entidad": {
                    "tipo_documento": "RUC",
                    "numero_documento": "20987654321",
                    "razon_social": "Entidad Continuidad SAC",
                },
            },
        },
        "liquidacion_especifica": {
            "datos": {"cantidad_visitas": 4},
            "tarifa": {"tarifa_visitas_id": str(tarifa_visitas_io.id)},
            "inspector_id": str(inspector_io.id),
            "inspector_operacion_id": str(inspector_io.inspector_operacion_id),
        },
    }


@pytest.fixture
def liquidacion_previa_io(
    db,
    municipalidad,
    ubigeo_distrito,
    tipo_inspeccion_obra,
    create_user,
    tarifa_visitas_io,
):
    """
    Liquidación de IO previa (A) con 10 visitas y 2 ya pagadas.

    A NO tiene fila de continuidad: es una IO normal, su `sub_total` es el valor
    completo del trabajo (10 × 257.50 = 2575.00).
    """
    entidad = None
    from modules.entidades.domain.models import Entidad
    from modules.liquidaciones.domain.models.proyecto import Proyecto

    entidad = Entidad.objects.create(
        tipo_documento="RUC", numero_documento="20111111111"
    )
    proyecto = Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Propietario Previo",
        direccion="Av. Previa 100",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20111111111",
        entidad_razon_social="Propietario Previo",
    )
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        estado=EstadoLiquidacion.PENDIENTE,
        expediente="EXP-IO-PREVIA-001",
        sub_total=Decimal("2575.00"),
        total=Decimal("3038.50"),
        usuario_creador=create_user,
    )
    LiquidacionInspeccionObra.objects.create(liquidacion=lg)
    lcv = LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg,
        cantidad_visitas=10,
        porcentaje_uit=Decimal("0.05"),
        categoria="INSPECCION",
        tarifa_aplicada=tarifa_visitas_io,
    )
    return {"liquidacion": lg, "lcv": lcv}


# ── Fase 1 — Fundación: modelo, re-exports, aritmética y resolver ──────────
#
# Subconjunto de FUNDACIÓN (Explorer, Fase 1): el modelo y su ancla, los
# re-exports obligatorios (contrato Django §4.1), la aritmética monetaria en
# Decimal y el resolver único de base RH. Nada de esto depende de que el
# flujo de IO sepa todavía qué es la continuidad.


def test_continuidad_esta_reexportada_en_los_cuatro_puntos_obligatorios():
    """
    GIVEN: el modelo `LiquidacionContinuidadVisitas` vive en `domain/models/`.
    THEN: los 4 re-exports obligatorios lo exponen y lo incluyen en `__all__`
          (contrato Django §4.1 — `models.py` raiz es re-export puro).
    """
    from modules.liquidaciones import models as models_raiz
    from modules.liquidaciones.domain.models import __all__ as domain_models_all
    from modules.liquidaciones.domain.models.liquidacion import __all__ as liquidacion_all
    from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo import (
        LiquidacionContinuidadVisitas as DelPaqueteLiquidacionTipo,
    )

    assert DelPaqueteLiquidacionTipo is LiquidacionContinuidadVisitas
    assert models_raiz.LiquidacionContinuidadVisitas is LiquidacionContinuidadVisitas
    assert "LiquidacionContinuidadVisitas" in models_raiz.__all__
    assert "LiquidacionContinuidadVisitas" in domain_models_all
    assert "LiquidacionContinuidadVisitas" in liquidacion_all


@pytest.mark.django_db
def test_continuidad_se_ancla_a_la_lcv_de_b_con_un_solo_registro(liquidacion_previa_io):
    """
    GIVEN: la LCV de la liquidación nueva (B).
    THEN: la fila de continuidad se alcanza por `lcv.continuidad` (OneToOne) y
          una segunda fila para la MISMA LCV es inválida en base de datos.
    """
    from django.db import IntegrityError, transaction

    lcv = liquidacion_previa_io["lcv"]

    fila = LiquidacionContinuidadVisitas.objects.create(
        liquidacion_visitas=lcv,
        monto_acumulado=Decimal("1030.00"),
        total_acumulado=Decimal("1215.40"),
    )
    assert lcv.continuidad.id == fila.id

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LiquidacionContinuidadVisitas.objects.create(
                liquidacion_visitas=lcv,
                monto_acumulado=Decimal("1.00"),
                total_acumulado=Decimal("1.18"),
            )


@pytest.mark.django_db
def test_continuidad_protege_la_liquidacion_previa(liquidacion_previa_io):
    """
    GIVEN: una fila de continuidad que referencia la liquidación previa (A).
    THEN: A está protegida (PROTECT): no se puede borrar mientras la
          continuidad viva.
    """
    from django.db.models.deletion import ProtectedError

    lcv = liquidacion_previa_io["lcv"]
    previa = liquidacion_previa_io["liquidacion"]

    LiquidacionContinuidadVisitas.objects.create(
        liquidacion_visitas=lcv,
        liquidacion_previa=previa,
        monto_acumulado=Decimal("1030.00"),
        total_acumulado=Decimal("1215.40"),
    )

    with pytest.raises(ProtectedError) as exc_info:
        previa.delete()

    assert any(
        isinstance(objeto, LiquidacionContinuidadVisitas)
        for objeto in exc_info.value.protected_objects
    )


def test_get_continuidad_es_tolerante_a_una_lcv_sin_fila(liquidacion_previa_io):
    """
    GIVEN: una IO normal (sin fila de continuidad).
    THEN: `get_continuidad` devuelve None en lugar de lanzar DoesNotExist —
          la ausencia de fila es el caso normal, no un error.
    """
    lcv = liquidacion_previa_io["lcv"]

    assert LiquidacionContinuidadVisitasCoreService.get_continuidad(lcv) is None


def test_resolver_base_rh_sin_continuidad_devuelve_el_sub_total_vigente(
    liquidacion_previa_io,
):
    """
    GIVEN: una IO normal (sin fila de continuidad), con `sub_total` = 2575.00.
    THEN: el resolver devuelve exactamente `liquidacion_general.sub_total`
          (comportamiento vigente, bit a bit).
    """
    lcv = liquidacion_previa_io["lcv"]

    base = LiquidacionContinuidadVisitasCoreService.resolver_base_rh(lcv)

    assert base == Decimal("2575.00")
    assert base == Decimal(str(lcv.liquidacion_general.sub_total))


def test_calcular_montos_acumulados_usa_decimal_con_round_half_up():
    """
    GIVEN: el valor neto de las visitas de B y el IGV vigente.
    THEN: `monto_acumulado` se redondea a 2 decimales (ROUND_HALF_UP) y
          `total_acumulado` es exactamente `monto_acumulado * (1 + igv)`
          redondeado al centavo.
    """
    monto, total = LiquidacionContinuidadVisitasCoreService.calcular_montos_acumulados(
        monto_neto_visitas=Decimal("1030.005"),
        igv_valor=Decimal("0.18"),
    )

    assert monto == Decimal("1030.01")
    assert total == Decimal("1215.41")  # 1030.01 × 1.18 = 1215.4118

    monto_exacto, total_exacto = (
        LiquidacionContinuidadVisitasCoreService.calcular_montos_acumulados(
            monto_neto_visitas=Decimal("2575.00"),
            igv_valor=Decimal("0.18"),
        )
    )
    assert monto_exacto == Decimal("2575.00")
    assert total_exacto == Decimal("3038.50")


def test_calcular_diferencia_devuelve_el_neto_y_el_bruto_a_cobrar():
    """
    GIVEN: el valor completo del trabajo y el crédito de la previa.
    THEN: la diferencia neta y la bruta son consistentes entre sí:
          `monto_acumulado − subtotal_credito` y `total_acumulado − total_credito`.
    """
    sub_total, total = LiquidacionContinuidadVisitasCoreService.calcular_diferencia(
        monto_acumulado=Decimal("1030.00"),
        total_acumulado=Decimal("1215.40"),
        subtotal_credito=Decimal("257.50"),
        total_credito=Decimal("303.85"),
    )

    assert sub_total == Decimal("772.50")
    assert total == Decimal("911.55")


def test_bloque_de_continuidad_es_opcional_en_el_schema_de_entrada():
    """
    GIVEN: el payload vigente de IO, sin bloque de continuidad.
    THEN: se valida igual que antes y `continuidad` queda ausente (None) —
          la API de IO no cambia para el cliente vigente.
    """
    import uuid

    from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
        LiquidacionInspeccionObraNuevaRevisionEspecificaIn,
    )

    payload = {
        "datos": {"cantidad_visitas": 2},
        "tarifa": {},
        "inspector_operacion_id": str(uuid.uuid4()),
    }

    parsed = LiquidacionInspeccionObraNuevaRevisionEspecificaIn(**payload)

    assert parsed.continuidad is None
    assert parsed.datos.cantidad_visitas == 2


def test_salida_de_visitas_expone_continuidad_ausente_por_defecto():
    """
    GIVEN: una IO sin continuidad.
    THEN: el bloque `continuidad` de la salida viene ausente (None).
    """
    import uuid

    from modules.liquidaciones.presentation.schemas.liquidacion_tipo.visitas_schemas import (
        LiquidacionPorCategoriaVisitasDatosOut,
    )

    salida = LiquidacionPorCategoriaVisitasDatosOut(
        id=uuid.uuid4(),
        cantidad_visitas=4,
    )

    assert salida.continuidad is None


# ── R7: IO sin continuidad conserva el comportamiento vigente ──────────────


@pytest.mark.django_db
def test_io_sin_continuidad_conserva_el_valor_completo(
    auth_client,
    payload_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO creada SIN bloque de continuidad.
    THEN: sub_total = valor completo del trabajo (4 × 257.50 = 1030.00),
          total = 1030.00 × 1.18 = 1215.40 y NO existe fila de continuidad.
    """
    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["liquidacion_general"]["sub_total"] == 1030.00
    assert data["liquidacion_general"]["total"] == 1215.40
    assert data["liquidacion_tipo"]["continuidad"] is None

    lcv = LiquidacionPorCategoriaVisitas.objects.get(
        id=data["liquidacion_tipo"]["id"]
    )
    assert not LiquidacionContinuidadVisitas.objects.filter(
        liquidacion_visitas=lcv
    ).exists()


# ── R3 + R4: IO con continuidad cobra SOLO la diferencia ───────────────────


@pytest.mark.django_db
def test_io_con_continuidad_cobra_solo_la_diferencia(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: IO nueva (B) con 4 visitas (1030.00 netas) que continúa una previa (A).
    WHEN: se declara un crédito neto de 257.50 (1 visita de A).
    THEN: B.sub_total = 1030.00 − 257.50 = 772.50 (la diferencia neta),
          B.total = total_acumulado − total_credito, y la fila de continuidad
          persiste monto_acumulado=1030.00 / total_acumulado=1215.40 /
          subtotal_credito=257.50 / total_credito=303.85.
    """
    payload_io["liquidacion_especifica"]["continuidad"] = {
        "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
        "visitas_previas_pendientes": 1,
        "subtotal_credito": "257.50",
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    # R2: la cantidad de visitas de B es solo la de las visitas nuevas.
    assert data["liquidacion_tipo"]["cantidad_visitas"] == 4

    # R3: la cabecera cobra la diferencia.
    assert data["liquidacion_general"]["sub_total"] == 772.50
    assert data["liquidacion_general"]["total"] == 911.55

    # R4: el valor completo del trabajo queda congelado en la fila de continuidad.
    continuidad = data["liquidacion_tipo"]["continuidad"]
    assert continuidad is not None
    assert continuidad["monto_acumulado"] == 1030.00
    assert continuidad["total_acumulado"] == 1215.40
    assert continuidad["subtotal_credito"] == 257.50
    # total_credito lo deriva el servidor (257.50 × 1.18 = 303.85).
    assert continuidad["total_credito"] == 303.85
    assert continuidad["visitas_previas_pendientes"] == 1
    # El total de visitas de la previa lo deriva el servidor de la LCV de A.
    assert continuidad["visitas_previas_totales"] == 10
    assert continuidad["liquidacion_previa_id"] == str(
        liquidacion_previa_io["liquidacion"].id
    )

    # Persistencia: una única fila, anclada a la LCV de B.
    lcv = LiquidacionPorCategoriaVisitas.objects.get(
        id=data["liquidacion_tipo"]["id"]
    )
    fila = LiquidacionContinuidadVisitas.objects.get(liquidacion_visitas=lcv)
    assert fila.monto_acumulado == Decimal("1030.00")
    assert fila.total_acumulado == Decimal("1215.40")
    assert fila.subtotal_credito == Decimal("257.50")
    assert fila.total_credito == Decimal("303.85")
    assert fila.liquidacion_previa_id == liquidacion_previa_io["liquidacion"].id

    # La liquidación general de B guarda la diferencia, no el valor completo.
    lg_b = LiquidacionGeneral.objects.get(id=data["liquidacion_general"]["id"])
    assert lg_b.sub_total == Decimal("772.50")
    assert lg_b.total == Decimal("911.55")


@pytest.mark.django_db
def test_io_con_continuidad_credito_cero_cobra_el_valor_completo(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: IO con continuidad pero SIN crédito (0.00).
    THEN: la diferencia es el valor completo del trabajo.
    """
    payload_io["liquidacion_especifica"]["continuidad"] = {
        "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
        "visitas_previas_pendientes": 0,
        "subtotal_credito": "0",
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]
    assert data["liquidacion_general"]["sub_total"] == 1030.00
    assert data["liquidacion_general"]["total"] == 1215.40
    assert data["liquidacion_tipo"]["continuidad"]["subtotal_credito"] == 0.0


# ── Bruto DECLARADO (`total_pagado_previa`) en el ALTA ──────────────────────
#
# El bruto pagado en la IO previa (IGV incluido) es la ENTRADA autoritativa
# del crédito: lo declara el cliente y el servidor lo deriva con el IGV
# vigente (DD-5/DD-6). El camino legacy por `subtotal_credito` (neto) sigue
# vigente cuando no viene el bruto.


@pytest.mark.django_db
def test_io_con_continuidad_acepta_el_bruto_declarado_y_deriva_el_credito(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: IO nueva (B) con 4 visitas (1030.00 netas · 1215.40 brutas).
    WHEN: se DECLARA el bruto pagado en la previa (212.40, IGV incluido).
    THEN: el servidor deriva el crédito (212.40 ÷ 1.18 = 180.00 neto ·
          180.00 × 1.18 = 212.40 bruto) y la cabecera cobra la diferencia
          (1030.00 − 180.00 = 850.00 · 1215.40 − 212.40 = 1003.00).
    """
    payload_io["liquidacion_especifica"]["continuidad"] = {
        "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
        "visitas_previas_pendientes": 1,
        "total_pagado_previa": "212.40",
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    # La cabecera cobra la DIFERENCIA contra el valor completo de B.
    assert data["liquidacion_general"]["sub_total"] == 850.00
    assert data["liquidacion_general"]["total"] == 1003.00

    # El crédito persistido es el DERIVADO del bruto declarado.
    continuidad = data["liquidacion_tipo"]["continuidad"]
    assert continuidad["monto_acumulado"] == 1030.00
    assert continuidad["total_acumulado"] == 1215.40
    assert continuidad["subtotal_credito"] == 180.00
    assert continuidad["total_credito"] == 212.40

    lcv = LiquidacionPorCategoriaVisitas.objects.get(
        id=data["liquidacion_tipo"]["id"]
    )
    fila = LiquidacionContinuidadVisitas.objects.get(liquidacion_visitas=lcv)
    assert fila.subtotal_credito == Decimal("180.00")
    assert fila.total_credito == Decimal("212.40")
    assert fila.monto_acumulado == Decimal("1030.00")
    assert fila.total_acumulado == Decimal("1215.40")


@pytest.mark.django_db
def test_io_con_continuidad_el_bruto_declarado_manda_sobre_el_neto(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: el bloque de continuidad viaja con el bruto declarado (212.40) Y un
           neto obsoleto (999.00).
    THEN: MANDA el bruto: el neto declarado se ignora y el crédito persistido
          es el derivado del bruto.
    """
    payload_io["liquidacion_especifica"]["continuidad"] = {
        "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
        "visitas_previas_pendientes": 1,
        "total_pagado_previa": "212.40",
        "subtotal_credito": "999.00",
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["liquidacion_tipo"]["continuidad"]["subtotal_credito"] == 180.00
    assert data["liquidacion_tipo"]["continuidad"]["total_credito"] == 212.40
    assert data["liquidacion_general"]["sub_total"] == 850.00
    assert data["liquidacion_general"]["total"] == 1003.00


@pytest.mark.django_db
def test_io_con_continuidad_rechaza_un_bruto_declarado_no_positivo(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: el bloque de continuidad con `total_pagado_previa` <= 0.
    THEN: 422 (el dato declarado tiene rango acotado) y NADA se escribe.
    """
    antes = LiquidacionGeneral.objects.count()

    payload_io["liquidacion_especifica"]["continuidad"] = {
        "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
        "visitas_previas_pendientes": 1,
        "total_pagado_previa": "0",
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )

    assert response.status_code == 422, response.content
    assert LiquidacionGeneral.objects.count() == antes


@pytest.mark.django_db
def test_io_con_continuidad_el_camino_legacy_por_neto_sigue_vigente(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: el bloque de continuidad SIN bruto declarado (camino legacy).
    THEN: el neto declarado manda y el bruto se deriva con el IGV vigente
          (257.50 → 303.85): el comportamiento vigente NO se mueve.
    """
    payload_io["liquidacion_especifica"]["continuidad"] = {
        "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
        "visitas_previas_pendientes": 1,
        "subtotal_credito": "257.50",
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    assert data["liquidacion_tipo"]["continuidad"]["subtotal_credito"] == 257.50
    assert data["liquidacion_tipo"]["continuidad"]["total_credito"] == 303.85
    assert data["liquidacion_general"]["sub_total"] == 772.50
    assert data["liquidacion_general"]["total"] == 911.55


@pytest.mark.django_db
def test_continuidad_sin_previa_en_cam_permite_ingreso_manual(
    auth_client,
    payload_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: continuidad SIN referencia a una liquidación previa (previa fuera de CAM).
    THEN: se acepta y se persiste con `liquidacion_previa_id` NULL.
    """
    payload_io["liquidacion_especifica"]["continuidad"] = {
        "visitas_previas_pendientes": 2,
        "visitas_previas_totales": 5,
        "categoria_previa": "2",
        "subtotal_credito": "515.00",
        "observacion": "Previa registrada fuera de CAM",
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]
    continuidad = data["liquidacion_tipo"]["continuidad"]
    assert continuidad["liquidacion_previa_id"] is None
    assert continuidad["visitas_previas_totales"] == 5
    assert continuidad["visitas_previas_pendientes"] == 2
    assert continuidad["categoria_previa"] == "2"
    assert continuidad["subtotal_credito"] == 515.00
    assert continuidad["total_credito"] == 607.70
    assert data["liquidacion_general"]["sub_total"] == 515.00


# ── Validaciones ───────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_continuidad_rechaza_previa_inexistente(auth_client, payload_io, uit_vigente, igv_vigente):
    """
    GIVEN: una referencia a una liquidación previa que no existe.
    THEN: 400 (regla de negocio del bloque de continuidad, Explorer Fase 2).
    """
    import uuid

    payload_io["liquidacion_especifica"]["continuidad"] = {
        "liquidacion_previa_id": str(uuid.uuid4()),
        "visitas_previas_pendientes": 1,
        "subtotal_credito": "100.00",
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )

    assert response.status_code == 400, response.content


@pytest.mark.django_db
def test_continuidad_rechaza_previa_que_no_es_io(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    tipo_edificacion,
    proyecto,
    municipalidad,
    create_user,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: la referencia apunta a una liquidación que NO es de Inspección de Obra.
    THEN: 400 (la previa debe existir y ser IO).
    """
    previa_no_io = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        estado=EstadoLiquidacion.PENDIENTE,
        expediente="EXP-EDIF-001",
        sub_total=Decimal("100.00"),
        total=Decimal("118.00"),
        usuario_creador=create_user,
    )

    payload_io["liquidacion_especifica"]["continuidad"] = {
        "liquidacion_previa_id": str(previa_no_io.id),
        "visitas_previas_pendientes": 1,
        "subtotal_credito": "100.00",
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )

    assert response.status_code == 400, response.content


@pytest.mark.django_db
def test_continuidad_rechaza_pendientes_mayores_que_el_total(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """GIVEN: más visitas pendientes que las visitas totales de la previa → 400."""
    payload_io["liquidacion_especifica"]["continuidad"] = {
        "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
        "visitas_previas_pendientes": 99,
        "subtotal_credito": "100.00",
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )

    assert response.status_code == 400, response.content


@pytest.mark.django_db
def test_continuidad_rechaza_pendientes_sin_referencia_ni_total(
    auth_client,
    payload_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: continuidad sin referencia a una liquidación previa en CAM y sin
           total de visitas informado, pero declarando visitas pendientes.
    THEN: 400 — el servidor no tiene contra qué validar el conteo de
          pendientes. (El ingreso manual de la previa sigue permitido
          informando su total de visitas.)
    """
    payload_io["liquidacion_especifica"]["continuidad"] = {
        "visitas_previas_pendientes": 2,
        "subtotal_credito": "100.00",
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )

    assert response.status_code == 400, response.content


@pytest.mark.django_db
def test_continuidad_rechaza_credito_negativo(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una continuidad con crédito neto negativo.
    THEN: 400 (regla de negocio; NO 422 — la no-negatividad no se valida en
          el schema de entrada).
    """
    payload_io["liquidacion_especifica"]["continuidad"] = {
        "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
        "visitas_previas_pendientes": 1,
        "subtotal_credito": "-100.00",
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )

    assert response.status_code == 400, response.content


@pytest.mark.django_db
def test_continuidad_no_se_admite_en_el_registro_legacy(
    auth_client,
    payload_io,
    inspector_io,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: el registro legacy de IO tiene un bloque específico ESTRICTO.
    THEN: enviar `continuidad` en ese camino es 422 (no existe en el contrato).
    """
    payload = {
        "numero": 1,
        "fecha_registro": "2024-05-10",
        "liquidacion_general": payload_io["liquidacion_general"],
        "liquidacion_especifica": {
            "datos": {"cantidad_visitas": 2},
            "tarifa": {"tarifa_visitas_id": str(tarifa_visitas_io.id)},
            "inspector_id": str(inspector_io.id),
            "inspector_operacion_id": str(inspector_io.inspector_operacion_id),
            "continuidad": {"visitas_previas_pendientes": 1},
        },
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion/legacy",
        json=payload,
    )

    assert response.status_code == 422, response.content


@pytest.mark.django_db
def test_continuidad_no_se_admite_en_la_io_relacionada(
    auth_client,
    payload_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: el bloque de continuidad enviado a `POST /relacionada`
           (IO creada desde una liquidación previa de Edificación/HU).
    THEN: 400 — ese flujo no puede liquidar el crédito de las visitas no
          realizadas de una IO previa; ignorarlo en silencio cobraría el valor
          completo del trabajo.
    """
    import uuid

    payload = {
        "liquidacion_previa_id": str(uuid.uuid4()),
        "liquidacion_especifica": {
            "datos": {"cantidad_visitas": 2},
            "tarifa": {
                "tarifa_visitas_id": payload_io["liquidacion_especifica"]["tarifa"][
                    "tarifa_visitas_id"
                ]
            },
            "inspector_operacion_id": str(uuid.uuid4()),
            "continuidad": {"visitas_previas_pendientes": 1},
        },
    }

    response = auth_client.post(
        "/liquidaciones/inspeccion-obra/relacionada",
        json=payload,
    )

    assert response.status_code == 400, response.content


# ── Lectura: el detalle expone la continuidad ──────────────────────────────


@pytest.mark.django_db
def test_detalle_io_expone_la_continuidad(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """GIVEN: una IO creada con continuidad. THEN: GET /{id} la expone en liquidacion_tipo."""
    payload_io["liquidacion_especifica"]["continuidad"] = {
        "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
        "visitas_previas_pendientes": 1,
        "subtotal_credito": "257.50",
    }
    created = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )
    liquidacion_id = created.json()["data"]["liquidacion_general"]["id"]

    response = auth_client.get(f"/liquidaciones/inspeccion-obra/{liquidacion_id}")

    assert response.status_code == 200, response.content
    continuidad = response.json()["data"]["liquidacion_tipo"]["continuidad"]
    assert continuidad is not None
    assert continuidad["monto_acumulado"] == 1030.00
    assert continuidad["total_acumulado"] == 1215.40
    assert continuidad["subtotal_credito"] == 257.50
    assert continuidad["total_credito"] == 303.85


# ── R8: recálculo explícito al editar B ───────────────────────────────────


@pytest.mark.django_db
def test_patch_recalcula_continuidad_y_diferencia(
    auth_client,
    payload_io,
    liquidacion_previa_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO con continuidad (4 visitas → 1030.00 netas, crédito 257.50).
    WHEN: se edita a 6 visitas (6 × 257.50 = 1545.00 netas).
    THEN: `monto_acumulado` = 1545.00, `total_acumulado` = 1823.10,
          la diferencia pasa a 1287.50 / 1519.25 y el CRÉDITO queda congelado.
    """
    payload_io["liquidacion_especifica"]["continuidad"] = {
        "liquidacion_previa_id": str(liquidacion_previa_io["liquidacion"].id),
        "visitas_previas_pendientes": 1,
        "subtotal_credito": "257.50",
    }
    created = auth_client.post(
        "/liquidaciones/inspeccion-obra/nueva-liquidacion",
        json=payload_io,
    )
    liquidacion_id = created.json()["data"]["liquidacion_general"]["id"]

    response = auth_client.patch(
        f"/liquidaciones/inspeccion-obra/{liquidacion_id}",
        json={
            "liquidacion_tipo": {
                "datos": {"cantidad_visitas": 6},
                "tarifa": {"tarifa_visitas_id": str(payload_io["liquidacion_especifica"]["tarifa"]["tarifa_visitas_id"])},
            }
        },
    )

    assert response.status_code == 200, response.content
    data = response.json()["data"]

    # 6 × 257.50 = 1545.00 netas → total_acumulado = 1545.00 × 1.18 = 1823.10
    assert data["liquidacion_general"]["sub_total"] == 1287.50
    assert data["liquidacion_general"]["total"] == 1519.25

    continuidad = data["liquidacion_tipo"]["continuidad"]
    assert continuidad["monto_acumulado"] == 1545.00
    assert continuidad["total_acumulado"] == 1823.10
    # El crédito pertenece a la previa: queda congelado.
    assert continuidad["subtotal_credito"] == 257.50
    assert continuidad["total_credito"] == 303.85


# ── R5: resolver único de base RH ──────────────────────────────────────────


@pytest.mark.django_db
def test_resolver_base_rh_usa_monto_acumulado_con_continuidad(
    liquidacion_previa_io,
    municipalidad,
    ubigeo_distrito,
    tipo_inspeccion_obra,
    create_user,
    tarifa_visitas_io,
    uit_vigente,
    igv_vigente,
):
    """
    GIVEN: una IO con continuidad (sub_total = diferencia, monto_acumulado = valor completo).
    THEN: el resolver devuelve `monto_acumulado`; sin continuidad devuelve `sub_total`.
    """
    from modules.entidades.domain.models import Entidad
    from modules.liquidaciones.domain.models.proyecto import Proyecto

    entidad = Entidad.objects.create(
        tipo_documento="RUC", numero_documento="20222222222"
    )
    proyecto = Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Propietario Resolver",
        direccion="Av. Resolver 200",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20222222222",
        entidad_razon_social="Propietario Resolver",
    )
    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        estado=EstadoLiquidacion.PENDIENTE,
        expediente="EXP-IO-RESOLVER",
        sub_total=Decimal("772.50"),
        total=Decimal("911.55"),
        usuario_creador=create_user,
    )
    LiquidacionInspeccionObra.objects.create(liquidacion=lg)
    lcv = LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=lg,
        cantidad_visitas=4,
        porcentaje_uit=Decimal("0.05"),
        categoria="INSPECCION",
        tarifa_aplicada=tarifa_visitas_io,
    )

    # Sin continuidad → la base es `liquidacion_general.sub_total`.
    assert (
        LiquidacionContinuidadVisitasCoreService.resolver_base_rh(lcv)
        == Decimal("772.50")
    )

    LiquidacionContinuidadVisitas.objects.create(
        liquidacion_visitas=lcv,
        monto_acumulado=Decimal("1030.00"),
        total_acumulado=Decimal("1215.40"),
        subtotal_credito=Decimal("257.50"),
        total_credito=Decimal("303.85"),
    )

    # Con continuidad → la base es `continuidad.monto_acumulado`.
    assert (
        LiquidacionContinuidadVisitasCoreService.resolver_base_rh(lcv)
        == Decimal("1030.00")
    )
