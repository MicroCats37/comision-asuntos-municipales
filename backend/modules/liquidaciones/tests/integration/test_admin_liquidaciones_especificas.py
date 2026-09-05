"""
Smoke tests for admin change views of all 6 proxy-based liquidacion types.

Verifies that the Django admin change view renders without errors for all
LiquidacionGeneral proxy admin classes (filtered by tipo_liquidacion__codigo),
covering the readonly field rendering path.

Run with: pytest backend/modules/liquidaciones/tests/integration/test_admin_liquidaciones_especificas.py -v
"""
import pytest
from decimal import Decimal
from datetime import date

from django.test import Client, override_settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.storage import staticfiles_storage

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_mecanica_suelos import (
    LiquidacionMecanicaSuelos,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_taludes import (
    LiquidacionTaludes,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_impacto_vial import (
    LiquidacionImpactoVial,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorMetroCuadrado,
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.entidades.domain.models.ubigeo import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.entidades.domain.models import Entidad
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorcentajeObra,
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
    TarifaPorCategoriaVisitas,
    DerechoPorMetroCuadrado,
)


# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def admin_client(db):
    """Django test client with a superuser logged in for admin tests."""
    User = get_user_model()
    user = User.objects.create_superuser(
        username="admin_smoke",
        email="admin_smoke@test.com",
        dni="12345678",
        password="testpass123",
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def igv(db):
    return IGV.objects.create(
        valor=Decimal("0.18"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def uit(db):
    return UIT.objects.create(
        valor=Decimal("5150.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


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
        codigo="M001", nombre="Municipalidad de Miraflores", distrito=ubigeo_distrito
    )


@pytest.fixture
def entidad(db):
    return Entidad.objects.create(tipo_documento="RUC", numero_documento="20456789012")


@pytest.fixture
def proyecto(db, entidad, ubigeo_distrito):
    return Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Propietario Test SAC",
        direccion="Av. Test 123",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789012",
        entidad_razon_social="Propietario Test SAC",
    )


# ── Shared PO (porcentaje obra) fixtures ────────────────────────────────────────


@pytest.fixture
def tipo_edificacion(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo="EDIFICACION", defaults={"nombre": "Edificaciones"}
    )[0]


@pytest.fixture
def tipo_taludes(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo="TALUDES", defaults={"nombre": "Taludes"}
    )[0]


@pytest.fixture
def tipo_impacto_vial(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo="IMPACTO_VIAL", defaults={"nombre": "Impacto Vial"}
    )[0]


@pytest.fixture
def tipo_habilitacion_urbana(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo="HABILITACION_URBANA", defaults={"nombre": "Habilitación Urbana"}
    )[0]


@pytest.fixture
def tipo_mecanica_suelos(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo="MECANICA_SUELOS", defaults={"nombre": "Mecánica de Suelos"}
    )[0]


@pytest.fixture
def tipo_inspeccion_obra(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo="INSPECCION_OBRA", defaults={"nombre": "Inspección de Obra"}
    )[0]


@pytest.fixture
def derecho_porcentaje(db):
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def derecho_m2(db):
    return DerechoPorMetroCuadrado.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_base_po(db, tipo_edificacion):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


# ── Edificaciones (PO) ─────────────────────────────────────────────────────────


@pytest.fixture
def liquidacion_general_edificaciones(db, municipalidad, proyecto, tipo_edificacion, igv, uit):
    return LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        expediente="EXP-SMOKE-EDIF-001",
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("5150.00"),
        igv_id=igv,
        uit_id=uit,
    )


@pytest.fixture
def edificacion_obj(db, liquidacion_general_edificaciones, derecho_porcentaje, tarifa_base_po):
    LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=liquidacion_general_edificaciones,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        derecho_aplicado=derecho_porcentaje,
    )
    return LiquidacionEdificacion.objects.create(liquidacion=liquidacion_general_edificaciones)


# ── Habilitación Urbana (M2) ───────────────────────────────────────────────────


@pytest.fixture
def tarifa_base_hu(db, tipo_habilitacion_urbana):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_habilitacion_urbana,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_m2_hu(db, tarifa_base_hu):
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_hu,
        costo_por_m2=Decimal("150.00"),
    )


@pytest.fixture
def liquidacion_general_hu(db, municipalidad, proyecto, tipo_habilitacion_urbana, igv, uit):
    return LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        expediente="EXP-SMOKE-HU-001",
        tipo_liquidacion=tipo_habilitacion_urbana,
        numero_revision=1,
        sub_total=Decimal("15000.00"),
        total=Decimal("17700.00"),
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("5150.00"),
        igv_id=igv,
        uit_id=uit,
    )


@pytest.fixture
def hu_obj(db, liquidacion_general_hu, tarifa_m2_hu, derecho_m2):
    LiquidacionPorMetroCuadrado.objects.create(
        liquidacion_general=liquidacion_general_hu,
        area_m2=Decimal("100.00"),
        costo_por_m2=Decimal("150.00"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        tarifa_aplicada=tarifa_m2_hu,
        derecho=derecho_m2,
    )
    return LiquidacionHabilitacionUrbana.objects.create(liquidacion=liquidacion_general_hu)


# ── Mecánica de Suelos (M2) ───────────────────────────────────────────────────


@pytest.fixture
def tarifa_base_ms(db, tipo_mecanica_suelos):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_mecanica_suelos,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_m2_ms(db, tarifa_base_ms):
    return TarifaPorMetroCuadrado.objects.create(
        tarifa_base=tarifa_base_ms,
        costo_por_m2=Decimal("125.00"),
    )


@pytest.fixture
def liquidacion_general_ms(db, municipalidad, proyecto, tipo_mecanica_suelos, igv, uit):
    return LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        expediente="EXP-SMOKE-MS-001",
        tipo_liquidacion=tipo_mecanica_suelos,
        numero_revision=1,
        sub_total=Decimal("10000.00"),
        total=Decimal("11800.00"),
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("5150.00"),
        igv_id=igv,
        uit_id=uit,
    )


@pytest.fixture
def ms_obj(db, liquidacion_general_ms, tarifa_m2_ms, derecho_m2):
    LiquidacionPorMetroCuadrado.objects.create(
        liquidacion_general=liquidacion_general_ms,
        area_m2=Decimal("80.00"),
        costo_por_m2=Decimal("125.00"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        tarifa_aplicada=tarifa_m2_ms,
        derecho=derecho_m2,
    )
    return LiquidacionMecanicaSuelos.objects.create(liquidacion=liquidacion_general_ms)


# ── Taludes (PO) ────────────────────────────────────────────────────────────────


@pytest.fixture
def tarifa_base_taludes(db, tipo_taludes):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_taludes,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def liquidacion_general_taludes(db, municipalidad, proyecto, tipo_taludes, igv, uit):
    return LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        expediente="EXP-SMOKE-TAL-001",
        tipo_liquidacion=tipo_taludes,
        numero_revision=1,
        sub_total=Decimal("800.00"),
        total=Decimal("944.00"),
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("5150.00"),
        igv_id=igv,
        uit_id=uit,
    )


@pytest.fixture
def taludes_obj(db, liquidacion_general_taludes, derecho_porcentaje, tarifa_base_taludes):
    LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=liquidacion_general_taludes,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("80000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        derecho_aplicado=derecho_porcentaje,
    )
    return LiquidacionTaludes.objects.create(liquidacion=liquidacion_general_taludes)


# ── Inspección de Obra (IO) ────────────────────────────────────────────────────


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
        categoria_visitas="INSPECCION",
        porcentaje_uit=Decimal("0.10"),
    )


@pytest.fixture
def liquidacion_general_io(db, municipalidad, proyecto, tipo_inspeccion_obra, igv, uit):
    return LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        expediente="EXP-SMOKE-IO-001",
        tipo_liquidacion=tipo_inspeccion_obra,
        numero_revision=1,
        sub_total=Decimal("3000.00"),
        total=Decimal("3540.00"),
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("5150.00"),
        igv_id=igv,
        uit_id=uit,
    )


@pytest.fixture
def io_obj(db, liquidacion_general_io, tarifa_visitas_io):
    LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=liquidacion_general_io,
        cantidad_visitas=3,
        categoria="INSPECCION",
        porcentaje_uit=Decimal("0.10"),
        tarifa_aplicada=tarifa_visitas_io,
    )
    return LiquidacionInspeccionObra.objects.create(liquidacion=liquidacion_general_io)


# ── Impacto Vial (PO) ─────────────────────────────────────────────────────────


@pytest.fixture
def tarifa_base_iv(db, tipo_impacto_vial):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_impacto_vial,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def liquidacion_general_iv(db, municipalidad, proyecto, tipo_impacto_vial, igv, uit):
    return LiquidacionGeneral.objects.create(
        municipalidad=municipalidad,
        proyecto=proyecto,
        expediente="EXP-SMOKE-IV-001",
        tipo_liquidacion=tipo_impacto_vial,
        numero_revision=1,
        sub_total=Decimal("1200.00"),
        total=Decimal("1416.00"),
        igv_snapshot=Decimal("0.18"),
        uit_snapshot=Decimal("5150.00"),
        igv_id=igv,
        uit_id=uit,
    )


@pytest.fixture
def iv_obj(db, liquidacion_general_iv, derecho_porcentaje, tarifa_base_iv):
    LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=liquidacion_general_iv,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("120000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        derecho_aplicado=derecho_porcentaje,
    )
    return LiquidacionImpactoVial.objects.create(liquidacion=liquidacion_general_iv)


# ── Smoke tests ────────────────────────────────────────────────────────────────


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
@pytest.mark.django_db
def test_admin_edificaciones_change_view_renders_200(admin_client, edificacion_obj, proyecto, municipalidad, tipo_edificacion):
    """Verify LiquidacionEdificacionProxy admin change view renders without errors."""
    # Use LiquidacionGeneral ID (from the specific model's liquidacion FK)
    lg_id = edificacion_obj.liquidacion_id
    url = f"/admin/liquidaciones/liquidacionedificacionproxy/{lg_id}/change/"
    response = admin_client.get(url)
    assert response.status_code == 200, (
        f"Expected 200 for Edificaciones proxy change view, got {response.status_code}: {response.content[:500]}"
    )
    # Verify admin links are present for related objects
    content = response.content.decode("utf-8")
    assert f"/admin/liquidaciones/proyecto/{proyecto.pk}/change/" in content, (
        "proyecto admin link not found in Edificaciones change view"
    )
    assert f"/admin/entidades/municipalidad/{municipalidad.pk}/change/" in content, (
        "municipalidad admin link not found in Edificaciones change view"
    )
    assert f"/admin/liquidaciones/tipoliquidacion/{tipo_edificacion.pk}/change/" in content, (
        "tipo_liquidacion admin link not found in Edificaciones change view"
    )


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
@pytest.mark.django_db
def test_admin_habilitacion_urbana_change_view_renders_200(admin_client, hu_obj, proyecto, municipalidad, tipo_habilitacion_urbana):
    """Verify LiquidacionHabilitacionUrbanaProxy admin change view renders without errors."""
    lg_id = hu_obj.liquidacion_id
    url = f"/admin/liquidaciones/liquidacionhabilitacionurbanaproxy/{lg_id}/change/"
    response = admin_client.get(url)
    assert response.status_code == 200, (
        f"Expected 200 for HU proxy change view, got {response.status_code}: {response.content[:500]}"
    )
    content = response.content.decode("utf-8")
    assert f"/admin/liquidaciones/proyecto/{proyecto.pk}/change/" in content
    assert f"/admin/entidades/municipalidad/{municipalidad.pk}/change/" in content
    assert f"/admin/liquidaciones/tipoliquidacion/{tipo_habilitacion_urbana.pk}/change/" in content


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
@pytest.mark.django_db
def test_admin_mecanica_suelos_change_view_renders_200(admin_client, ms_obj):
    """Verify LiquidacionMecanicaSuelosProxy admin change view renders without errors."""
    lg_id = ms_obj.liquidacion_id
    url = f"/admin/liquidaciones/liquidacionmecanicasuelosproxy/{lg_id}/change/"
    response = admin_client.get(url)
    assert response.status_code == 200, (
        f"Expected 200 for MS proxy change view, got {response.status_code}: {response.content[:500]}"
    )


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
@pytest.mark.django_db
def test_admin_taludes_change_view_renders_200(admin_client, taludes_obj):
    """Verify LiquidacionTaludesProxy admin change view renders without errors."""
    lg_id = taludes_obj.liquidacion_id
    url = f"/admin/liquidaciones/liquidaciontaludesproxy/{lg_id}/change/"
    response = admin_client.get(url)
    assert response.status_code == 200, (
        f"Expected 200 for Taludes proxy change view, got {response.status_code}: {response.content[:500]}"
    )


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
@pytest.mark.django_db
def test_admin_inspeccion_obra_change_view_renders_200(admin_client, io_obj):
    """Verify LiquidacionInspeccionObraProxy admin change view renders without errors."""
    lg_id = io_obj.liquidacion_id
    url = f"/admin/liquidaciones/liquidacioninspeccionobraproxy/{lg_id}/change/"
    response = admin_client.get(url)
    assert response.status_code == 200, (
        f"Expected 200 for IO proxy change view, got {response.status_code}: {response.content[:500]}"
    )


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
@pytest.mark.django_db
def test_admin_impacto_vial_change_view_renders_200(admin_client, iv_obj):
    """Verify LiquidacionImpactoVialProxy admin change view renders without errors."""
    lg_id = iv_obj.liquidacion_id
    url = f"/admin/liquidaciones/liquidacionimpactovialproxy/{lg_id}/change/"
    response = admin_client.get(url)
    assert response.status_code == 200, (
        f"Expected 200 for IV proxy change view, got {response.status_code}: {response.content[:500]}"
    )


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
@pytest.mark.django_db
def test_admin_edificaciones_changelist_renders_200(admin_client, edificacion_obj):
    """Verify LiquidacionEdificacionProxy admin changelist renders without errors."""
    url = "/admin/liquidaciones/liquidacionedificacionproxy/"
    response = admin_client.get(url)
    assert response.status_code == 200, (
        f"Expected 200 for Edificaciones proxy changelist, got {response.status_code}: {response.content[:500]}"
    )
