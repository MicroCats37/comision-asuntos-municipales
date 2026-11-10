from datetime import date

import pytest
from django.core.exceptions import ValidationError

from modules.liquidaciones.domain.models import (
    Delegado,
    DelegadoOperacion,
    DelegadoOperacionPeriodo,
    Inspector,
    InspectorOperacion,
    InspectorOperacionPeriodo,
)
from modules.liquidaciones.domain.resources import (
    DelegadoOperacionResource,
    InspectorOperacionResource,
)
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision, PerfilIngeniero


@pytest.fixture(params=["delegado", "inspector"])
def periodo_operacion(request, db, municipalidad, tipo_edificacion):
    especialidad = EspecialidadRevision.objects.create(
        slug=f"civil-{request.param}",
        nombre=f"Ingeniería Civil {request.param}",
    )
    perfil = PerfilIngeniero.objects.create(
        cip="100001" if request.param == "delegado" else "100002",
        dni="70000001" if request.param == "delegado" else "70000002",
        nombres="Periodo",
        apellido_paterno=request.param.title(),
    )

    if request.param == "delegado":
        parent = DelegadoOperacion.objects.create(
            delegado=Delegado.objects.create(perfil_ingeniero=perfil),
            municipalidad=municipalidad,
            especialidad_revision=especialidad,
        )
        return DelegadoOperacionPeriodo, "delegado_municipalidad", parent

    parent = InspectorOperacion.objects.create(
        inspector=Inspector.objects.create(perfil_ingeniero=perfil),
        tipo_liquidacion=tipo_edificacion,
        categoria="1",
        especialidad_revision=especialidad,
    )
    return InspectorOperacionPeriodo, "inspector_tipo_liquidacion", parent


def create_periodo(periodo_operacion, inicio, fin):
    model, parent_field, parent = periodo_operacion
    return model.objects.create(**{parent_field: parent, "periodo_inicio": inicio, "periodo_fin": fin})


@pytest.mark.django_db
def test_permite_periodos_no_superpuestos(periodo_operacion):
    create_periodo(periodo_operacion, date(2026, 1, 1), date(2026, 1, 31))
    create_periodo(periodo_operacion, date(2026, 2, 1), None)


@pytest.mark.django_db
def test_rechaza_solapamiento_acotado_e_inclusivo(periodo_operacion):
    create_periodo(periodo_operacion, date(2026, 1, 1), date(2026, 1, 31))

    with pytest.raises(ValidationError, match="se superpone"):
        create_periodo(periodo_operacion, date(2026, 1, 31), date(2026, 2, 15))


@pytest.mark.django_db
def test_rechaza_solapamiento_con_periodo_abierto(periodo_operacion):
    create_periodo(periodo_operacion, date(2026, 1, 1), None)

    with pytest.raises(ValidationError, match="se superpone"):
        create_periodo(periodo_operacion, date(2026, 2, 1), date(2026, 2, 28))


@pytest.mark.django_db
def test_permite_actualizar_la_misma_instancia(periodo_operacion):
    periodo = create_periodo(periodo_operacion, date(2026, 1, 1), date(2026, 1, 31))

    periodo.periodo_fin = date(2026, 1, 30)
    periodo.save()

    periodo.refresh_from_db()
    assert periodo.periodo_fin == date(2026, 1, 30)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("resource_class", "period_model"),
    [
        (DelegadoOperacionResource, DelegadoOperacionPeriodo),
        (InspectorOperacionResource, InspectorOperacionPeriodo),
    ],
)
def test_reimportacion_con_mismo_inicio_actualiza_el_periodo_existente(
    periodo_operacion, resource_class, period_model
):
    model, current_parent_field, parent = periodo_operacion
    if model is not period_model:
        pytest.skip("Caso cubierto por la otra parametrización de operación.")

    resource = resource_class()
    resource.after_save_instance(
        parent,
        {"vigencia_inicio": "2026-01-01", "vigencia_fin": "2026-01-31"},
    )
    resource.after_save_instance(
        parent,
        {"vigencia_inicio": "2026-01-01", "vigencia_fin": "2026-02-15"},
    )

    periods = model.objects.filter(**{current_parent_field: parent})
    assert periods.count() == 1
    assert periods.get().periodo_fin == date(2026, 2, 15)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("resource_class", "period_model"),
    [
        (DelegadoOperacionResource, DelegadoOperacionPeriodo),
        (InspectorOperacionResource, InspectorOperacionPeriodo),
    ],
)
def test_importacion_reporta_error_de_solapamiento(
    periodo_operacion, resource_class, period_model
):
    model, current_parent_field, parent = periodo_operacion
    if model is not period_model:
        pytest.skip("Caso cubierto por la otra parametrización de operación.")

    model.objects.create(
        **{
            current_parent_field: parent,
            "periodo_inicio": date(2026, 1, 1),
            "periodo_fin": date(2026, 1, 31),
        }
    )

    with pytest.raises(ValidationError, match="se superpone"):
        resource_class().after_save_instance(
            parent,
            {"vigencia_inicio": "2026-01-31", "vigencia_fin": "2026-02-15"},
        )
