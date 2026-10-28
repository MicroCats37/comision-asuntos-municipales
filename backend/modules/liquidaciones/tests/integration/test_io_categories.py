from types import SimpleNamespace

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model

from modules.liquidaciones.admin.tarifas_admin import TarifaPorCategoriaVisitasAdmin
from modules.liquidaciones.domain.models.inspector import Inspector, InspectorOperacion
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
from modules.liquidaciones.management.commands.import_legacy_inspeccion_obra import (
    _resolve_inspector_operacion_for_legacy_io,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    PerfilIngeniero,
)


EXPECTED_CHOICES = [
    ("1", "Categoría 1"),
    ("2", "Categoría 2"),
    ("3", "Categoría 3"),
    ("4", "Categoría 4"),
]


def test_tarifa_categoria_choices_are_canonical_in_model_and_admin():
    field = TarifaPorCategoriaVisitas._meta.get_field("categoria_visitas")
    assert list(field.choices) == EXPECTED_CHOICES

    model_admin = TarifaPorCategoriaVisitasAdmin(
        TarifaPorCategoriaVisitas,
        admin.site,
    )
    form_field = model_admin.formfield_for_dbfield(field, request=None)
    assert list(form_field.choices)[1:] == EXPECTED_CHOICES


@pytest.mark.django_db
@pytest.mark.parametrize("categoria", ["2", "3", "4"])
def test_resolve_inspector_operacion_reuses_matching_category(categoria):
    user = get_user_model().objects.create_user(
        username=f"legacy-io-{categoria}",
        password="testpass123",
        dni=f"7000000{categoria}",
    )
    perfil = PerfilIngeniero.objects.create(
        usuario=user,
        apellido_paterno="Legacy",
        apellido_materno="Inspector",
        nombres=f"Categoría {categoria}",
        cip=f"9000{categoria}",
        dni=f"7000000{categoria}",
    )
    inspector = Inspector.objects.create(perfil_ingeniero=perfil)
    especialidad = EspecialidadRevision.objects.create(
        slug=f"legacy-io-{categoria}",
        nombre=f"Legacy IO {categoria}",
    )
    tipo = TipoLiquidacion.objects.get_or_create(
        codigo="EDIFICACION",
        defaults={"nombre": "Edificación"},
    )[0]
    InspectorOperacion.objects.create(
        inspector=inspector,
        tipo_liquidacion=tipo,
        categoria="1",
        especialidad_revision=especialidad,
    )
    expected = InspectorOperacion.objects.create(
        inspector=inspector,
        tipo_liquidacion=tipo,
        categoria=categoria,
        especialidad_revision=especialidad,
    )

    result = _resolve_inspector_operacion_for_legacy_io(
        inspector,
        SimpleNamespace(categoria_mapped=categoria),
    )

    assert result == expected
