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
from django.test.client import RequestFactory
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils import timezone

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
    LiquidacionEdificacionProxy,
    LiquidacionHabilitacionUrbanaProxy,
    LiquidacionMecanicaSuelosProxy,
    LiquidacionTaludesProxy,
    LiquidacionInspeccionObraProxy,
    LiquidacionImpactoVialProxy,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorMetroCuadrado,
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
from modules.liquidaciones.domain.models.delegado import LiquidacionDelegado
from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.finanzas.domain.models.registro_pago_inspector import RegistroPagoInspector
from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.finanzas.domain.models.detalle_honorario_inspector import (
    DetalleHonorarioInspector,
)
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
from modules.liquidaciones.admin.liquidacion_admin import (
    LiquidacionDelegadoInline,
    LiquidacionComprobanteInline,
    LiquidacionEdificacionInline,
    LiquidacionEdificacionProxyAdmin,
    LiquidacionHabilitacionUrbanaInline,
    LiquidacionHabilitacionUrbanaProxyAdmin,
    LiquidacionImpactoVialInline,
    LiquidacionImpactoVialProxyAdmin,
    LiquidacionInspeccionObraInline,
    LiquidacionInspeccionObraProxyAdmin,
    LiquidacionMecanicaSuelosInline,
    LiquidacionMecanicaSuelosProxyAdmin,
    LiquidacionPorCategoriaVisitasInline,
    LiquidacionPorMetroCuadradoInline,
    LiquidacionPorcentajeObraInline,
    LiquidacionTaludesInline,
    LiquidacionTaludesProxyAdmin,
    RegistroPagoInspectorInline,
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
        categoria="1",
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
    visitas = io_obj.liquidacion.liquidacion_visitas.get()
    RegistroPagoInspector.objects.create(
        liquidacion_por_categoria_visitas=visitas,
        periodo=2026,
        mes=10,
        inspecciones_pagadas=2,
    )
    lg_id = io_obj.liquidacion_id
    url = f"/admin/liquidaciones/liquidacioninspeccionobraproxy/{lg_id}/change/"
    response = admin_client.get(url)
    assert response.status_code == 200, (
        f"Expected 200 for IO proxy change view, got {response.status_code}: {response.content[:500]}"
    )
    content = response.content.decode("utf-8")
    assert "Programadas" in content
    assert "Pagadas" in content
    assert "Saldo pendiente" in content
    assert 'name="categoria_inspeccion"' in content
    assert '<option value="1" selected>Categoría 1</option>' in content
    assert 'id="registros_pago_inspector-group"' in content
    assert "Registros de visitas" in content
    assert "empty-form" in content
    assert "addText" in content
    model_admin = response.context["adminform"].model_admin
    original = response.context["original"]
    assert model_admin.visitas_programadas(original) == 3
    assert model_admin.inspecciones_pagadas(original) == 2
    assert model_admin.saldo_inspecciones(original) == 1
    model_admin._save_categoria(original, "2")
    visitas.refresh_from_db()
    assert visitas.categoria == "2"

    inline = next(
        inline
        for inline in model_admin.get_inline_instances(response.wsgi_request, original)
        if inline.model is RegistroPagoInspector
    )
    formset_class = inline.get_formset(response.wsgi_request, original)
    prefix = formset_class.get_default_prefix()
    registro_existente = visitas.registros_pago.get(periodo=2026, mes=10)
    formset = formset_class(
        data={
            f"{prefix}-TOTAL_FORMS": "2",
            f"{prefix}-INITIAL_FORMS": "1",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-id": str(registro_existente.id),
            f"{prefix}-0-periodo": "2026",
            f"{prefix}-0-mes": "10",
            f"{prefix}-0-inspecciones_pagadas": "2",
            f"{prefix}-1-periodo": "2026",
            f"{prefix}-1-mes": "10",
            f"{prefix}-1-inspecciones_pagadas": "1",
        },
        instance=original,
        prefix=prefix,
    )
    assert formset.is_valid(), formset.errors
    formset.save()
    registro_nuevo = visitas.registros_pago.get(
        periodo=2026,
        mes=10,
        inspecciones_pagadas=1,
    )

    future_year = timezone.localdate().year + 1
    future_formset = formset_class(
        data={
            f"{prefix}-TOTAL_FORMS": "3",
            f"{prefix}-INITIAL_FORMS": "2",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-id": str(registro_existente.id),
            f"{prefix}-0-periodo": "2026",
            f"{prefix}-0-mes": "10",
            f"{prefix}-0-inspecciones_pagadas": "2",
            f"{prefix}-1-id": str(registro_nuevo.id),
            f"{prefix}-1-periodo": "2026",
            f"{prefix}-1-mes": "10",
            f"{prefix}-1-inspecciones_pagadas": "1",
            f"{prefix}-2-periodo": str(future_year),
            f"{prefix}-2-mes": "1",
            f"{prefix}-2-inspecciones_pagadas": "1",
        },
        instance=original,
        prefix=prefix,
    )
    assert not future_formset.is_valid()
    assert "No se pueden registrar visitas en un período futuro." in str(
        future_formset.errors
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


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("admin_class", "proxy_model", "obj_fixture", "expected_inlines"),
    [
        (
            LiquidacionEdificacionProxyAdmin,
            LiquidacionEdificacionProxy,
            "edificacion_obj",
            [LiquidacionEdificacionInline, LiquidacionPorcentajeObraInline],
        ),
        (
            LiquidacionHabilitacionUrbanaProxyAdmin,
            LiquidacionHabilitacionUrbanaProxy,
            "hu_obj",
            [LiquidacionHabilitacionUrbanaInline, LiquidacionPorMetroCuadradoInline],
        ),
        (
            LiquidacionMecanicaSuelosProxyAdmin,
            LiquidacionMecanicaSuelosProxy,
            "ms_obj",
            [LiquidacionMecanicaSuelosInline, LiquidacionPorMetroCuadradoInline],
        ),
        (
            LiquidacionTaludesProxyAdmin,
            LiquidacionTaludesProxy,
            "taludes_obj",
            [LiquidacionTaludesInline, LiquidacionPorcentajeObraInline],
        ),
        (
            LiquidacionInspeccionObraProxyAdmin,
            LiquidacionInspeccionObraProxy,
            "io_obj",
            [
                LiquidacionInspeccionObraInline,
                LiquidacionPorCategoriaVisitasInline,
                RegistroPagoInspectorInline,
            ],
        ),
        (
            LiquidacionImpactoVialProxyAdmin,
            LiquidacionImpactoVialProxy,
            "iv_obj",
            [LiquidacionImpactoVialInline, LiquidacionPorcentajeObraInline],
        ),
    ],
)
def test_proxy_admins_include_only_related_inlines_and_allow_deletion(
    request, admin_client, admin_class, proxy_model, obj_fixture, expected_inlines
):
    obj = request.getfixturevalue(obj_fixture).liquidacion
    admin_request = RequestFactory().get("/")
    admin_request.user = admin_client.session.get("_auth_user_id")
    admin_request.user = get_user_model().objects.get(pk=admin_request.user)
    model_admin = admin_class(proxy_model, admin.site)

    inlines = model_admin.get_inlines(admin_request, obj)

    assert inlines == [
        *expected_inlines[:2],
        LiquidacionComprobanteInline,
        LiquidacionDelegadoInline,
        *expected_inlines[2:],
    ]
    # The RH detail inlines are never exposed by the liquidation proxies.
    assert not {DetalleHonorarioDelegado, DetalleHonorarioInspector} & {
        inline.model for inline in inlines
    }
    for inline_class in [LiquidacionDelegadoInline]:
        inline = inline_class(obj.__class__, admin.site)
        assert inline.get_formset(admin_request, obj).can_delete


def test_liquidacion_delegado_inline_uses_bounded_widgets():
    """The delegate inline is a direct FK: no empty rows, bounded FK widgets."""
    inline = LiquidacionDelegadoInline(LiquidacionGeneral, admin.site)

    assert inline.extra == 0
    assert inline.autocomplete_fields == [
        "delegado",
        "especialidad_revision",
        "delegado_operacion",
    ]
    for field_name in inline.autocomplete_fields:
        related_admin = admin.site._registry.get(
            LiquidacionDelegado._meta.get_field(field_name).remote_field.model
        )
        assert related_admin is not None, (
            f"'{field_name}' has no registered admin, autocomplete would fail"
        )
        assert related_admin.search_fields, (
            f"'{field_name}' admin has no search_fields, autocomplete would fail"
        )


@pytest.mark.parametrize(
    ("admin_class", "proxy_model"),
    [
        (LiquidacionEdificacionProxyAdmin, LiquidacionEdificacionProxy),
        (LiquidacionHabilitacionUrbanaProxyAdmin, LiquidacionHabilitacionUrbanaProxy),
        (LiquidacionMecanicaSuelosProxyAdmin, LiquidacionMecanicaSuelosProxy),
        (LiquidacionTaludesProxyAdmin, LiquidacionTaludesProxy),
        (LiquidacionInspeccionObraProxyAdmin, LiquidacionInspeccionObraProxy),
        (LiquidacionImpactoVialProxyAdmin, LiquidacionImpactoVialProxy),
    ],
)
def test_proxy_admins_allow_editing_subtotal_and_total(admin_class, proxy_model):
    model_admin = admin_class(proxy_model, admin.site)
    form_class = model_admin.get_form(RequestFactory().get("/admin/"))

    assert "sub_total" in model_admin.fields
    assert "total" in model_admin.fields
    assert "sub_total" not in model_admin.readonly_fields
    assert "total" not in model_admin.readonly_fields
    assert "sub_total" in form_class.base_fields
    assert "total" in form_class.base_fields


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("admin_class", "proxy_model", "obj_fixture", "numero"),
    [
        (LiquidacionEdificacionProxyAdmin, LiquidacionEdificacionProxy, "edificacion_obj", 101),
        (LiquidacionHabilitacionUrbanaProxyAdmin, LiquidacionHabilitacionUrbanaProxy, "hu_obj", 102),
        (LiquidacionMecanicaSuelosProxyAdmin, LiquidacionMecanicaSuelosProxy, "ms_obj", 103),
        (LiquidacionTaludesProxyAdmin, LiquidacionTaludesProxy, "taludes_obj", 104),
        (LiquidacionInspeccionObraProxyAdmin, LiquidacionInspeccionObraProxy, "io_obj", 105),
        (LiquidacionImpactoVialProxyAdmin, LiquidacionImpactoVialProxy, "iv_obj", 106),
    ],
)
def test_proxy_admin_searches_exact_specific_liquidacion_number(
    request, admin_client, admin_class, proxy_model, obj_fixture, numero
):
    specific = request.getfixturevalue(obj_fixture)
    specific.numero = numero
    specific.save(update_fields=["numero"])
    model_admin = admin_class(proxy_model, admin.site)
    admin_request = RequestFactory().get("/admin/", {"q": str(numero)})
    admin_request.user = get_user_model().objects.get(
        pk=admin_client.session["_auth_user_id"]
    )

    queryset = model_admin.get_queryset(admin_request)
    matches, may_have_duplicates = model_admin.get_search_results(
        admin_request, queryset, str(numero)
    )

    assert list(matches.values_list("id", flat=True)) == [specific.liquidacion_id]
    assert not may_have_duplicates


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("admin_class", "proxy_model", "obj_fixture", "related_name"),
    [
        (LiquidacionEdificacionProxyAdmin, LiquidacionEdificacionProxy, "edificacion_obj", "edificaciones"),
        (LiquidacionHabilitacionUrbanaProxyAdmin, LiquidacionHabilitacionUrbanaProxy, "hu_obj", "habilitacion_urbana"),
        (LiquidacionMecanicaSuelosProxyAdmin, LiquidacionMecanicaSuelosProxy, "ms_obj", "mecanica_suelos"),
        (LiquidacionTaludesProxyAdmin, LiquidacionTaludesProxy, "taludes_obj", "taludes"),
        (LiquidacionInspeccionObraProxyAdmin, LiquidacionInspeccionObraProxy, "io_obj", "inspeccion_obra"),
        (LiquidacionImpactoVialProxyAdmin, LiquidacionImpactoVialProxy, "iv_obj", "impacto_vial"),
    ],
)
def test_proxy_admin_changelist_keeps_performance_configuration(
    request, admin_class, proxy_model, obj_fixture, related_name
):
    obj = request.getfixturevalue(obj_fixture).liquidacion
    model_admin = admin_class(proxy_model, admin.site)
    queryset = model_admin.get_queryset(RequestFactory().get("/admin/"))

    assert model_admin.show_full_result_count is False
    assert model_admin.numero.admin_order_field is None
    assert queryset.query.order_by == ("legacy", "-fecha_registro")
    assert related_name in queryset.query.select_related
    assert obj.pk in queryset.values_list("pk", flat=True)
