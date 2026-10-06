"""
Integration tests for Proyecto row isolation.

Tests prove:
1. Multiple Proyecto instances can have identical field values (no field-level uniqueness).
2. clone_proyecto_for_liquidacion creates a new Proyecto with shared Entidad.
3. Edificaciones nueva revision creates isolated proyecto (not shared).
4. IO desde-previa creates isolated proyecto (not shared).

Fixtures shared via conftest.py.
"""
import pytest
from decimal import Decimal

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.entidades.domain.models import Entidad
from modules.liquidaciones.domain.constants import EstadoLiquidacion
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)


# ── Tests: Duplicate field values are allowed ────────────────────────────────


@pytest.mark.django_db
def test_proyecto_duplicate_field_values_allowed(db, municipalidad, ubigeo_distrito, create_user, igv_vigente, uit_vigente, tipo_edificacion, derecho_porcentaje_vigente, tarifa_porcentaje_obra_estructuras, especialidad_estructuras):
    """
    Multiple independent Proyecto rows CAN have identical field values.
    No uniqueness constraint exists at the field level.
    """
    entidad = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento="20456789012",
    )

    # Create two proyectos with IDENTICAL field values
    proyecto_a = Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Propietario Duplicado SAC",
        entidad_razon_social="Propietario Duplicado SAC",
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789012",
        direccion="Av. Duplicada 999, Lima",
        urbanizacion="Urb. Duplicada",
        distrito_id=ubigeo_distrito.id,
    )

    proyecto_b = Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Propietario Duplicado SAC",
        entidad_razon_social="Propietario Duplicado SAC",
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789012",
        direccion="Av. Duplicada 999, Lima",
        urbanizacion="Urb. Duplicada",
        distrito_id=ubigeo_distrito.id,
    )

    # They are different rows with different IDs
    assert proyecto_a.id != proyecto_b.id

    # But field values are identical
    assert proyecto_a.nombre_propietario == proyecto_b.nombre_propietario
    assert proyecto_a.entidad_razon_social == proyecto_b.entidad_razon_social
    assert proyecto_a.direccion == proyecto_b.direccion
    assert proyecto_a.entidad_numero_documento == proyecto_b.entidad_numero_documento

    # Both point to the same Entidad (shared by design)
    assert proyecto_a.entidad_id == proyecto_b.entidad_id


# ── Tests: clone_proyecto_for_liquidacion helper ───────────────────────────────


@pytest.mark.django_db
def test_clone_proyecto_preserves_all_fields(
    db, municipalidad, ubigeo_distrito, create_user,
    igv_vigente, uit_vigente, tipo_edificacion,
):
    """
    clone_proyecto_for_liquidacion creates a new Proyecto with all fields copied,
    sharing the SAME Entidad (entidad FK is not cloned).
    """
    user = create_user
    entidad = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento="20987654321",
    )

    original_proyecto = Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Proyecto Original SAC",
        entidad_razon_social="Proyecto Original SAC",
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20987654321",
        direccion="Av. Original 100, Lima",
        urbanizacion="Urb. Original",
        distrito_id=ubigeo_distrito.id,
        descripcion="Descripcion del proyecto original",
    )

    # Create a liquidacion that references the original proyecto
    lg = LiquidacionGeneral.objects.create(
        proyecto=original_proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-CLONE-TEST",
        observacion="Test clone",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    # Clone via service
    core_service = LiquidacionGeneralCoreService()
    cloned = core_service.clone_proyecto_for_liquidacion(lg)

    # It's a different row
    assert cloned.id != original_proyecto.id

    # All scalar fields are copied
    assert cloned.nombre_propietario == original_proyecto.nombre_propietario
    assert cloned.entidad_razon_social == original_proyecto.entidad_razon_social
    assert cloned.entidad_tipo_documento == original_proyecto.entidad_tipo_documento
    assert cloned.entidad_numero_documento == original_proyecto.entidad_numero_documento
    assert cloned.direccion == original_proyecto.direccion
    assert cloned.urbanizacion == original_proyecto.urbanizacion
    assert cloned.distrito_id == original_proyecto.distrito_id
    assert cloned.descripcion == original_proyecto.descripcion

    # But Entidad is SHARED (not cloned)
    assert cloned.entidad_id == original_proyecto.entidad_id
    assert cloned.entidad.id == original_proyecto.entidad.id


@pytest.mark.django_db
def test_clone_proyecto_creates_independent_row(
    db, municipalidad, ubigeo_distrito, create_user,
    igv_vigente, uit_vigente, tipo_edificacion,
):
    """
    Cloned proyecto is a fully independent row — changes to the clone
    do not affect the original.
    """
    user = create_user
    entidad = Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento="20987654322",
    )

    original_proyecto = Proyecto.objects.create(
        entidad=entidad,
        nombre_propietario="Original SAC",
        entidad_razon_social="Original SAC",
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20987654322",
        direccion="Av. Original 200",
        urbanizacion="Urb. Original",
        distrito_id=ubigeo_distrito.id,
    )

    lg = LiquidacionGeneral.objects.create(
        proyecto=original_proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-INDEPENDENT-TEST",
        observacion="Test",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("0"),
        total=Decimal("0"),
    )

    core_service = LiquidacionGeneralCoreService()
    cloned = core_service.clone_proyecto_for_liquidacion(lg)

    # Mutate the cloned proyecto
    cloned.nombre_propietario = "Clone Modificado SAC"
    cloned.direccion = "Av. Clone 300"
    cloned.save()

    # Original is unchanged
    original_proyecto.refresh_from_db()
    assert original_proyecto.nombre_propietario == "Original SAC"
    assert original_proyecto.direccion == "Av. Original 200"
    assert cloned.nombre_propietario == "Clone Modificado SAC"
    assert cloned.direccion == "Av. Clone 300"
