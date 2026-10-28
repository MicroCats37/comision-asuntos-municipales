from decimal import Decimal

import pytest

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_visitas_data import (
    DatosVisitas,
    LiquidacionCategoriaVisitasData,
    TarifaVisitas,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_categoria_visitas_core_service import (
    LiquidacionPorCategoriaVisitasCoreService,
)
from modules.liquidaciones.presentation.presenters.liquidacion_tipo.liquidacion_por_categoria_visitas_presenter import (
    LiquidacionPorCategoriaVisitasPresenter,
)


@pytest.fixture
def tarifa_visitas_categoria_3(db, tarifa_liquidacion_base_io):
    return TarifaPorCategoriaVisitas.objects.create(
        tarifa_base=tarifa_liquidacion_base_io,
        porcentaje_uit=Decimal("0.07"),
        categoria_visitas="3",
    )


@pytest.mark.django_db
def test_cotizar_io_funciona_solo_con_tarifa_id(
    api_client,
    tarifa_visitas_categoria_3,
    uit_vigente,
    igv_vigente,
):
    response = api_client.post(
        "/liquidaciones/inspeccion-obra/cotizar",
        json={
            "liquidacion_especifica": {
                "datos": {"cantidad_visitas": 2},
                "tarifa": {
                    "tarifa_visitas_id": str(tarifa_visitas_categoria_3.id)
                },
            }
        },
    )

    assert response.status_code == 200, response.content
    result = response.json()["data"]
    assert result["datos"]["entrada"]["datos"]["categoria"] == "3"


@pytest.mark.django_db
def test_cotizar_io_ignora_categoria_cliente_discordante(
    api_client,
    tarifa_visitas_categoria_3,
    uit_vigente,
    igv_vigente,
):
    response = api_client.post(
        "/liquidaciones/inspeccion-obra/cotizar",
        json={
            "liquidacion_especifica": {
                "datos": {"cantidad_visitas": 2, "categoria": "4"},
                "tarifa": {
                    "tarifa_visitas_id": str(tarifa_visitas_categoria_3.id)
                },
            }
        },
    )

    assert response.status_code == 200, response.content
    result = response.json()["data"]
    assert result["datos"]["entrada"]["datos"]["categoria"] == "3"


@pytest.mark.django_db
def test_present_tarifas_vigentes_multiplica_porcentaje_por_uit(
    tarifa_visitas_categoria_3,
    uit_vigente,
):
    result = LiquidacionPorCategoriaVisitasPresenter.present_tarifas_vigentes(
        tarifas=[tarifa_visitas_categoria_3],
        uit_vigente=uit_vigente,
    )

    assert result.tarifas[0].costo_por_visita == (
        tarifa_visitas_categoria_3.porcentaje_uit * uit_vigente.valor
    )


@pytest.mark.django_db
def test_core_io_legacy_manual_conserva_tarifa_y_categoria_nulas(
    proyecto,
    municipalidad,
    create_user,
    tipo_inspeccion_obra,
):
    liquidacion = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=create_user,
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        sub_total=Decimal("100.00"),
        total=Decimal("100.00"),
    )

    visitas = LiquidacionPorCategoriaVisitasCoreService().crear_liquidacion_tipo_visitas(
        liquidacion_general=liquidacion,
        data=LiquidacionCategoriaVisitasData(
            datos=DatosVisitas(cantidad_visitas=1, categoria=None),
            tarifa=TarifaVisitas(tarifa_visitas_id=None),
        ),
    )

    assert visitas.tarifa_aplicada_id is None
    assert visitas.categoria is None
    assert visitas.porcentaje_uit is None
