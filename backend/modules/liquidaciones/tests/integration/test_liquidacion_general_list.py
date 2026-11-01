"""
Integration tests for the general liquidaciones listing (GET /liquidaciones/generales/).

The canonical-latest machinery was retired: there is NO "latest revision per project"
listing anymore. The standard paginated listing returns EVERY liquidacion, whatever
its revision number, and the exact `numero_revisiones` filter admits multiple
sibling results.

Tests cover:
- GET /liquidaciones/generales/ returns every liquidacion (no max-revision reduction)
- GET /liquidaciones/generales/ultimas-revisiones is unreachable (endpoint retired)

Fixtures are shared via conftest.py (tests/conftest.py).
"""
import pytest
from decimal import Decimal
from django.contrib import admin
from django.test import RequestFactory

from modules.liquidaciones.admin.liquidacion_admin import LiquidacionEdificacionProxyAdmin
from modules.liquidaciones.domain.constants import EstadoLiquidacion
from modules.liquidaciones.tests.fixtures.http_helpers import status_de_ruta_retirada
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
    LiquidacionEdificacionProxy,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)


def _crear_edificacion_para_numeracion(base, *, legacy=False, numero=None):
    """Create an isolated Edificaciones row while preserving required relations."""
    from modules.liquidaciones.domain.models.proyecto import Proyecto

    proyecto = Proyecto.objects.create(
        nombre_propietario=f"Proyecto numeracion {LiquidacionGeneral.objects.count()}",
        direccion="Av. Numeracion 123",
    )
    liquidacion = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=base.municipalidad,
        usuario_creador=base.usuario_creador,
        expediente=f"EXP-NUM-{LiquidacionGeneral.objects.count()}",
        estado=base.estado,
        tipo_liquidacion=base.tipo_liquidacion,
        sub_total=base.sub_total,
        total=base.total,
        igv_id=base.igv_id,
        uit_id=base.uit_id,
        legacy=legacy,
    )
    return LiquidacionEdificacion.objects.create(liquidacion=liquidacion, numero=numero)


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def liquidaciones_revisiones_del_mismo_proyecto(
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
    """
    Two Edificaciones liquidaciones of the SAME project lineage: revision 1 and
    revision 3.

    `proyecto` is a OneToOneField on LiquidacionGeneral, so the second revision
    lives on a CLONED proyecto — exactly what the backend does when a revision is
    created on top of a previous one.

    Returns (revision_1, revision_3).
    """
    from modules.entidades.domain.models import Entidad
    from modules.liquidaciones.domain.models.proyecto import Proyecto

    user = create_user

    def _crear(proyecto_obj, numero, expediente):
        lg = LiquidacionGeneral.objects.create(
            proyecto=proyecto_obj,
            municipalidad=municipalidad,
            usuario_creador=user,
            expediente=expediente,
            observacion=f"Revision {numero}",
            estado=EstadoLiquidacion.PENDIENTE,
            tipo_liquidacion=tipo_edificacion,
            numero_revision=numero,
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

    entidad_revision_3 = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento="20456789099",
    )
    proyecto_revision_3 = Proyecto.objects.create(
        entidad=entidad_revision_3,
        nombre_propietario="Propietario Test SAC",
        direccion="Av. Test 123",
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789099",
        entidad_razon_social="Propietario Test SAC",
    )

    revision_1 = _crear(proyecto, 1, "EXP-GENERAL-REV-1")
    revision_3 = _crear(proyecto_revision_3, 3, "EXP-GENERAL-REV-3")

    return revision_1, revision_3


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_listado_general_devuelve_todas_las_revisiones(
    auth_client,
    liquidaciones_revisiones_del_mismo_proyecto,
):
    """
    The standard general listing returns EVERY liquidacion — the revision number
    is an editable label, so there is no "latest revision" to reduce to.
    """
    revision_1, revision_3 = liquidaciones_revisiones_del_mismo_proyecto

    response = auth_client.get("/liquidaciones/generales/")

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    result = response.json()["data"]

    assert result["total"] == 2, \
        f"Expected both revisions in the listing, got total={result['total']}"

    revisiones = {
        item["numero_revision"]
        for item in result["items"]
    }
    assert revisiones == {1, 3}, \
        f"Expected revisions 1 and 3 (no canonical reduction), got {revisiones}"


@pytest.mark.django_db
def test_listado_general_conserva_la_total_real(
    auth_client,
    liquidaciones_revisiones_del_mismo_proyecto,
):
    """
    Pagination metadata reflects the real total (2), not a collapsed "latest" set.
    """
    response = auth_client.get("/liquidaciones/generales/?page=1&page_size=10")

    assert response.status_code == 200
    result = response.json()["data"]

    assert result["page"] == 1
    assert result["page_size"] == 10
    assert result["total"] == 2
    assert len(result["items"]) == 2


@pytest.mark.django_db
def test_listados_ordenan_no_legacy_primero_y_por_numero_dentro_del_grupo(
    liquidaciones_revisiones_del_mismo_proyecto,
):
    numero_55163, numero_0 = liquidaciones_revisiones_del_mismo_proyecto
    LiquidacionEdificacion.objects.filter(liquidacion=numero_55163).update(numero=55163)
    LiquidacionEdificacion.objects.filter(liquidacion=numero_0).update(numero=0)

    service = LiquidacionGeneralCoreService()

    generales, _ = service.list_liquidaciones_generales_paginated(
        page=1,
        page_size=10,
    )
    assert [item.id for item in generales] == [
        numero_55163.id,
        numero_0.id,
    ]

    por_tipo, _ = service.list_liquidaciones_by_type_paginated(
        tipo_liquidacion="EDIFICACION",
        page=1,
        page_size=10,
    )
    assert [item.id for item in por_tipo] == [
        numero_55163.id,
        numero_0.id,
    ]

    numero_55163.legacy = True
    numero_55163.save(update_fields=["legacy"])

    por_tipo, _ = service.list_liquidaciones_by_type_paginated(
        tipo_liquidacion="EDIFICACION",
        page=1,
        page_size=10,
    )
    assert [item.id for item in por_tipo] == [numero_0.id, numero_55163.id]


@pytest.mark.django_db
def test_autonumero_de_edificaciones_ignora_legacy_al_crear(
    liquidaciones_revisiones_del_mismo_proyecto,
):
    normal, legacy = liquidaciones_revisiones_del_mismo_proyecto
    LiquidacionEdificacion.objects.filter(liquidacion=normal).update(numero=2)
    legacy.legacy = True
    legacy.save(update_fields=["legacy"])
    LiquidacionEdificacion.objects.filter(liquidacion=legacy).update(numero=9000)

    creada = _crear_edificacion_para_numeracion(normal)

    assert creada.numero == 3


@pytest.mark.django_db
def test_autonumero_de_edificaciones_inicia_en_uno_si_solo_hay_legacy(
    liquidaciones_revisiones_del_mismo_proyecto,
):
    primera, segunda = liquidaciones_revisiones_del_mismo_proyecto
    LiquidacionGeneral.objects.filter(id__in=[primera.id, segunda.id]).update(legacy=True)
    LiquidacionEdificacion.objects.filter(liquidacion=primera).update(numero=35)
    LiquidacionEdificacion.objects.filter(liquidacion=segunda).update(numero=9000)

    creada = _crear_edificacion_para_numeracion(primera)

    assert creada.numero == 1


@pytest.mark.django_db
def test_admin_de_edificaciones_agrupa_no_legacy_antes_de_legacy(
    liquidaciones_revisiones_del_mismo_proyecto,
):
    normal, legacy = liquidaciones_revisiones_del_mismo_proyecto
    LiquidacionEdificacion.objects.filter(liquidacion=normal).update(numero=2)
    legacy.legacy = True
    legacy.save(update_fields=["legacy"])
    LiquidacionEdificacion.objects.filter(liquidacion=legacy).update(numero=9000)

    model_admin = LiquidacionEdificacionProxyAdmin(
        LiquidacionEdificacionProxy, admin.site
    )
    queryset = model_admin.get_queryset(RequestFactory().get("/admin/"))

    assert list(queryset.values_list("id", flat=True)) == [normal.id, legacy.id]


@pytest.mark.django_db
def test_endpoint_ultimas_revisiones_ya_no_existe(auth_client, db):
    """
    GET /liquidaciones/generales/ultimas-revisiones ya no sirve el listado canonico.

    La ruta fue RETIRADA junto con el resto de la maquinaria de "ultima revision".
    Como el controller general expone `/{liquidacion_id}` (PATCH/DELETE) con un
    conversor generico, el path_retirado resuelve contra esa ruta y Django
    responde 405 Method Not Allowed; si algun dia se usara un conversor `uuid:`,
    pasaria a ser 404. En ninguno de los dos casos se devuelve el listado.
    """
    status = status_de_ruta_retirada(
        auth_client,
        "/liquidaciones/generales/ultimas-revisiones?tipo_liquidacion=EDIFICACION",
    )

    assert status in (404, 405), (
        f"Expected the retired endpoint to be unreachable, got {status}"
    )
