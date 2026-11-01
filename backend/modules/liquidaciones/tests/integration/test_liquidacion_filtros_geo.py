"""
Integration tests for the geographic filters of the liquidaciones listings.

Covers `entidad_id` (municipalidad) and `distrito_id` (proyecto.distrito) as
independent query filters on the per-type listings and on the general listing.

Fixtures are shared via conftest.py (tests/conftest.py).
"""

import pytest
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)


@pytest.fixture
def dos_liquidaciones_en_distritos(
    db,
    municipalidad,
    proyecto,
    create_user,
    derecho_porcentaje_vigente,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra_estructuras,
    especialidad_estructuras,
    tipo_edificacion,
):
    from modules.entidades.domain.models import Entidad, UbigeoDistrito
    from modules.liquidaciones.domain.models.proyecto import Proyecto

    otro_distrito = UbigeoDistrito.objects.create(
        provincia=proyecto.distrito.provincia,
        nombre="Distrito Verificacion",
        ubigeo="990101",
    )
    otra_entidad = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento="20999999999",
    )
    otro_proyecto = Proyecto.objects.create(
        entidad=otra_entidad,
        nombre_propietario="Propietario Otro",
        direccion="Otra direccion",
        distrito_id=otro_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20999999999",
        entidad_razon_social="Propietario Otro SAC",
    )

    def _crear(proyecto_obj, numero, expediente):
        lg = LiquidacionGeneral.objects.create(
            proyecto=proyecto_obj,
            municipalidad=municipalidad,
            usuario_creador=create_user,
            expediente=expediente,
            observacion="Test",
            estado="PENDIENTE",
            tipo_liquidacion=tipo_edificacion,
            numero_revision=1,
            sub_total=Decimal("1000.00"),
            total=Decimal("1180.00"),
            igv_id=igv_vigente,
            uit_id=uit_vigente,
        )
        LiquidacionEdificacion.objects.create(liquidacion=lg, numero=numero)
        lpo = LiquidacionPorcentajeObra.objects.create(
            liquidacion_general=lg,
            tipo_tramite="OBRA_NUEVA",
            valor_declarado=Decimal("100000.00"),
            porcentaje_liquidacion=Decimal("0.0010"),
            derecho_minimo=Decimal("500.00"),
            derecho_maximo=Decimal("50000.00"),
            porcentaje_minimo_uit=Decimal("0.10"),
            derecho_aplicado=derecho_porcentaje_vigente,
        )
        LiquidacionPorcentajeObraDetalle.objects.create(
            liquidacion_porcentaje=lpo,
            tarifa_aplicada=tarifa_porcentaje_obra_estructuras,
            especialidad=especialidad_estructuras,
            porcentaje_aplicado=Decimal("0.0010"),
            subtotal=Decimal("1000.00"),
        )
        return lg

    lg_a = _crear(proyecto, 1, "EXP-ORIGINAL")
    lg_b = _crear(otro_proyecto, 2, "EXP-OTRO")
    return lg_a, lg_b, otro_distrito


@pytest.mark.django_db
def test_listado_filtra_por_distrito_y_municipalidad(
    auth_client,
    municipalidad,
    dos_liquidaciones_en_distritos,
):
    lg_a, lg_b, otro_distrito = dos_liquidaciones_en_distritos

    resp = auth_client.get(
        f"/liquidaciones/edificaciones/?entidad_id={municipalidad.id}&distrito_id={otro_distrito.id}"
    )
    assert resp.status_code == 200, resp.content
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["liquidacion_general"]["expediente"] == "EXP-OTRO"

    resp_solo_muni = auth_client.get(
        f"/liquidaciones/edificaciones/?entidad_id={municipalidad.id}"
    )
    assert resp_solo_muni.status_code == 200
    assert len(resp_solo_muni.json()["data"]["items"]) == 2

    resp_solo_distrito = auth_client.get(
        f"/liquidaciones/edificaciones/?distrito_id={otro_distrito.id}"
    )
    assert resp_solo_distrito.status_code == 200
    assert len(resp_solo_distrito.json()["data"]["items"]) == 1

    otro_muni_id = "00000000-0000-0000-0000-000000000000"
    resp_muni_inexistente = auth_client.get(
        f"/liquidaciones/edificaciones/?entidad_id={otro_muni_id}"
    )
    assert resp_muni_inexistente.status_code == 200
    assert len(resp_muni_inexistente.json()["data"]["items"]) == 0

    assert lg_a.id != lg_b.id


@pytest.mark.django_db
def test_listado_general_filtra_por_distrito_y_municipalidad(
    auth_client,
    municipalidad,
    dos_liquidaciones_en_distritos,
):
    _lg_a, _lg_b, otro_distrito = dos_liquidaciones_en_distritos

    resp = auth_client.get(
        f"/liquidaciones/generales/?entidad_id={municipalidad.id}&distrito_id={otro_distrito.id}"
    )
    assert resp.status_code == 200, resp.content
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["expediente"] == "EXP-OTRO"

    resp_solo_muni = auth_client.get(
        f"/liquidaciones/generales/?entidad_id={municipalidad.id}"
    )
    assert resp_solo_muni.status_code == 200
    assert len(resp_solo_muni.json()["data"]["items"]) == 2

    resp_solo_distrito = auth_client.get(
        f"/liquidaciones/generales/?distrito_id={otro_distrito.id}"
    )
    assert resp_solo_distrito.status_code == 200
    assert len(resp_solo_distrito.json()["data"]["items"]) == 1
