"""
Integration tests for LiquidacionGeneral PATCH proyecto/municipalidad editing.

Tests use Ninja's TestClient for proper async handling.
All tests use @pytest.mark.django_db for database access.

Tests cover:
- First revision (numero_revision==1) with no previas: allows proyecto/municipalidad edit
- Revision > 1: rejects proyecto/municipalidad edit with 409
- Has liquidaciones_previas: rejects proyecto/municipalidad edit with 409
- Changing entidad numero_documento: find-or-create Entidad, reassign FK
- Changing only entidad razon_social: updates Proyecto snapshot only
- PAGADA: still blocks all edits (including proyecto/municipalidad)
- Existing generic PATCH fields still work alongside proyecto fields

Fixtures are shared via conftest.py (tests/conftest.py).
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
from modules.liquidaciones.domain.constants import EstadoLiquidacion
from modules.entidades.domain.models import Entidad
from modules.entidades.domain.models.municipalidad import Municipalidad


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def liquidacion_pendiente_rev1_sin_previas(
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
    Create a LiquidacionGeneral in PENDIENTE, numero_revision=1, with NO liquidaciones_previas.
    This is the ONLY case where proyecto/municipalidad edits ARE allowed.
    """
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-REV1-SIN-PREVIAS",
        observacion="Test liquidation rev1 sin previas",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

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


@pytest.fixture
def liquidacion_pendiente_rev2(
    db,
    municipalidad,
    proyecto,
    create_user,
    igv_vigente,
    uit_vigente,
    tipo_edificacion,
):
    """
    Create a LiquidacionGeneral in PENDIENTE, numero_revision=2.
    proyecto/municipalidad edits should be REJECTED.
    """
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-REV2",
        observacion="Test liquidation rev2",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=2,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

    return lg


@pytest.fixture
def municipalidad_2(db, ubigeo_distrito):
    """Create a second municipalidad for testing municipalidad reassignment."""
    return Municipalidad.objects.create(
        codigo="M002",
        nombre="Municipalidad de San Isidro",
        distrito=ubigeo_distrito,
    )


@pytest.fixture
def another_entidad(db):
    """Create another Entidad for testing entidad reassignment."""
    return Entidad.objects.create(
        tipo_documento="RUC",
        numero_documento="20987654321",
    )


@pytest.fixture
def liquidacion_pagada(
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
    Create a persisted LiquidacionGeneral already in PAGADA state.
    """
    user = create_user

    lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-PAGADA-IDEM-001",
        observacion="Test liquidation already PAGADA",
        estado=EstadoLiquidacion.PAGADA,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )

    LiquidacionEdificacion.objects.create(liquidacion=lg, numero=1)

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


# ── Tests: Revision Rule Allows Edits ──────────────────────────────────────────

@pytest.mark.django_db
def test_primer_revision_sin_previas_permite_editar_proyecto(
    auth_client,
    liquidacion_pendiente_rev1_sin_previas,
):
    """
    PATCH with proyecto fields succeeds when numero_revision==1 and no previas.
    """
    liquidacion_id = liquidacion_pendiente_rev1_sin_previas.id

    patch_payload = {
        "proyecto": {
            "denominacion": "Nuevo Nombre de Proyecto",
            "nombre_propietario": "Nuevo Propietario SAC",
        }
    }

    response = auth_client.patch(
        f"/liquidaciones/generales/{liquidacion_id}",
        json=patch_payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_primer_revision_sin_previas_permite_editar_municipalidad(
    auth_client,
    liquidacion_pendiente_rev1_sin_previas,
    municipalidad_2,
):
    """
    PATCH with municipalidad_id succeeds when numero_revision==1 and no previas.
    """
    liquidacion_id = liquidacion_pendiente_rev1_sin_previas.id

    patch_payload = {
        "municipalidad_id": str(municipalidad_2.id),
    }

    response = auth_client.patch(
        f"/liquidaciones/generales/{liquidacion_id}",
        json=patch_payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_primer_revision_sin_previas_actualiza_proyecto_en_db(
    auth_client,
    liquidacion_pendiente_rev1_sin_previas,
):
    """
    After PATCH with proyecto fields, the proyecto record is actually updated.
    """
    liquidacion_id = liquidacion_pendiente_rev1_sin_previas.id

    patch_payload = {
        "denominacion_de_proyecto": "Proyecto Editado via PATCH",
        "proyecto": {
            "nombre_propietario": "Propietario Editado",
            "direccion": "Nueva Direccion 456",
        }
    }

    response = auth_client.patch(
        f"/liquidaciones/generales/{liquidacion_id}",
        json=patch_payload,
    )
    assert response.status_code == 200

    # Verify DB update
    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.denominacion_de_proyecto == "Proyecto Editado via PATCH"
    assert lg.proyecto.nombre_propietario == "Propietario Editado"
    assert lg.proyecto.direccion == "Nueva Direccion 456"


# ── Tests: Revision Rule Rejects Edits ─────────────────────────────────────────

@pytest.mark.django_db
def test_revision_mayor_a_1_rechaza_edicion_proyecto(
    auth_client,
    liquidacion_pendiente_rev2,
):
    """
    PATCH with proyecto fields returns 409 when numero_revision > 1.
    """
    liquidacion_id = liquidacion_pendiente_rev2.id

    patch_payload = {
        "proyecto": {
            "denominacion": "Nombre Intentado",
        }
    }

    response = auth_client.patch(
        f"/liquidaciones/generales/{liquidacion_id}",
        json=patch_payload,
    )

    assert response.status_code == 409, \
        f"Expected 409 Conflict, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_revision_mayor_a_1_rechaza_edicion_municipalidad(
    auth_client,
    liquidacion_pendiente_rev2,
    municipalidad_2,
):
    """
    PATCH with municipalidad_id returns 409 when numero_revision > 1.
    """
    liquidacion_id = liquidacion_pendiente_rev2.id

    patch_payload = {
        "municipalidad_id": str(municipalidad_2.id),
    }

    response = auth_client.patch(
        f"/liquidaciones/generales/{liquidacion_id}",
        json=patch_payload,
    )

    assert response.status_code == 409, \
        f"Expected 409 Conflict, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_tiene_liquidaciones_previas_rechaza_edicion_proyecto(
    db,
    auth_client,
    municipalidad,
    proyecto,
    create_user,
    igv_vigente,
    uit_vigente,
    tipo_edificacion,
    derecho_porcentaje_vigente,
):
    """
    PATCH with proyecto fields returns 409 when liquidacion has liquidaciones_previas.
    We create a "previous" liquidacion and link it via the liquidaciones_previas M2M.
    """
    user = create_user

    # Create a "previous" liquidacion (revision 1) — must have details for the prefetch chain
    prev_lg = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-PREVIA",
        estado=EstadoLiquidacion.PAGADA,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("500.00"),
        total=Decimal("590.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )
    LiquidacionEdificacion.objects.create(liquidacion=prev_lg, numero=1)

    # Create our test liquidacion (also revision 1 but WITH previas now)
    lg_with_previas = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        usuario_creador=user,
        expediente="EXP-CON-PREVIAS",
        observacion="Test liquidation con previas",
        estado=EstadoLiquidacion.PENDIENTE,
        tipo_liquidacion=tipo_edificacion,
        numero_revision=1,
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
    )
    LiquidacionEdificacion.objects.create(liquidacion=lg_with_previas, numero=1)

    # Link prev_lg as previa
    lg_with_previas.liquidaciones_previas.add(prev_lg)

    patch_payload = {
        "proyecto": {
            "denominacion": "Intento de Editar",
        }
    }

    response = auth_client.patch(
        f"/liquidaciones/generales/{lg_with_previas.id}",
        json=patch_payload,
    )

    assert response.status_code == 409, \
        f"Expected 409 Conflict when has previas, got {response.status_code}: {response.content}"


# ── Tests: Entidad Reassignment ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_cambio_numero_documento_entidad_find_or_create(
    auth_client,
    liquidacion_pendiente_rev1_sin_previas,
    another_entidad,
):
    """
    When entidad numero_documento changes, find-or-create Entidad and reassign FK.
    The old Entidad row must NOT be mutated.
    """
    liquidacion_id = liquidacion_pendiente_rev1_sin_previas.id
    proyecto = liquidacion_pendiente_rev1_sin_previas.proyecto
    old_entidad = proyecto.entidad
    old_entidad_numero = old_entidad.numero_documento

    patch_payload = {
        "proyecto": {
            "entidad": {
                "tipo_documento": "RUC",
                "numero_documento": "20987654321",  # another_entidad's number
                "razon_social": "Nueva Razon Social",
            }
        }
    }

    response = auth_client.patch(
        f"/liquidaciones/generales/{liquidacion_id}",
        json=patch_payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    # Verify FK was reassigned to another_entidad
    proyecto.refresh_from_db()
    assert proyecto.entidad_id == another_entidad.id, \
        "Proyecto.entidad FK should be reassigned to the found Entidad"

    # Verify old Entidad was NOT mutated
    old_entidad.refresh_from_db()
    assert old_entidad.numero_documento == old_entidad_numero, \
        "Old Entidad numero_documento should NOT be mutated"

    # Verify snapshot fields updated
    assert proyecto.entidad_numero_documento == "20987654321"
    assert proyecto.entidad_razon_social == "Nueva Razon Social"


@pytest.mark.django_db
def test_cambio_solo_razon_social_no_reasigna_entidad(
    auth_client,
    liquidacion_pendiente_rev1_sin_previas,
):
    """
    When only entidad razon_social changes (no numero_documento change),
    update Proyecto snapshot only. No Entidad FK reassignment.
    """
    liquidacion_id = liquidacion_pendiente_rev1_sin_previas.id
    proyecto = liquidacion_pendiente_rev1_sin_previas.proyecto
    original_entidad_id = proyecto.entidad_id
    original_numero = proyecto.entidad_numero_documento

    patch_payload = {
        "proyecto": {
            "entidad": {
                "razon_social": "Razon Social Actualizada",
            }
        }
    }

    response = auth_client.patch(
        f"/liquidaciones/generales/{liquidacion_id}",
        json=patch_payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    # Verify FK was NOT reassigned
    proyecto.refresh_from_db()
    assert proyecto.entidad_id == original_entidad_id, \
        "Entidad FK should NOT change when only razon_social updates"

    # Verify snapshot updated
    assert proyecto.entidad_razon_social == "Razon Social Actualizada"
    assert proyecto.entidad_numero_documento == original_numero


@pytest.mark.django_db
def test_nuevo_numero_documento_crea_nueva_entidad(
    auth_client,
    liquidacion_pendiente_rev1_sin_previas,
):
    """
    When entidad numero_documento changes to a non-existent document,
    a NEW Entidad should be created (not an error).
    """
    liquidacion_id = liquidacion_pendiente_rev1_sin_previas.id
    proyecto = liquidacion_pendiente_rev1_sin_previas.proyecto

    # Ensure this numero_documento doesn't exist
    non_existent_numero = "22123456789"
    assert not Entidad.objects.filter(numero_documento=non_existent_numero).exists()

    patch_payload = {
        "proyecto": {
            "entidad": {
                "tipo_documento": "RUC",
                "numero_documento": non_existent_numero,
                "razon_social": "Entidad Recién Creada SAC",
            }
        }
    }

    response = auth_client.patch(
        f"/liquidaciones/generales/{liquidacion_id}",
        json=patch_payload,
    )

    assert response.status_code == 200, \
        f"Expected 200 (new Entidad created), got {response.status_code}: {response.content}"

    # Verify new Entidad was created
    assert Entidad.objects.filter(numero_documento=non_existent_numero).exists(), \
        "New Entidad should be created for non-existent numero_documento"

    # Verify FK points to new Entidad
    proyecto.refresh_from_db()
    assert proyecto.entidad.numero_documento == non_existent_numero


# ── Tests: PAGADA Still Blocks ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_pagada_rechaza_edicion_proyecto(
    auth_client,
    liquidacion_pagada,
):
    """
    PATCH with proyecto fields returns 409 when estado == PAGADA.
    """
    liquidacion_id = liquidacion_pagada.id

    patch_payload = {
        "proyecto": {
            "denominacion": "Intento en PAGADA",
        }
    }

    response = auth_client.patch(
        f"/liquidaciones/generales/{liquidacion_id}",
        json=patch_payload,
    )

    assert response.status_code == 409, \
        f"Expected 409 for PAGADA, got {response.status_code}: {response.content}"


@pytest.mark.django_db
def test_pagada_rechaza_edicion_municipalidad(
    auth_client,
    liquidacion_pagada,
    municipalidad_2,
):
    """
    PATCH with municipalidad_id returns 409 when estado == PAGADA.
    """
    liquidacion_id = liquidacion_pagada.id

    patch_payload = {
        "municipalidad_id": str(municipalidad_2.id),
    }

    response = auth_client.patch(
        f"/liquidaciones/generales/{liquidacion_id}",
        json=patch_payload,
    )

    assert response.status_code == 409, \
        f"Expected 409 for PAGADA, got {response.status_code}: {response.content}"


# ── Tests: Generic Fields Still Work ───────────────────────────────────────────

@pytest.mark.django_db
def test_generic_patch_fields_still_work_with_proyecto_fields(
    auth_client,
    liquidacion_pendiente_rev1_sin_previas,
):
    """
    PATCH with both generic fields (expediente) and proyecto fields succeeds.
    Both are applied.
    """
    liquidacion_id = liquidacion_pendiente_rev1_sin_previas.id

    patch_payload = {
        "expediente": "EXP-MODIFIED-001",
        "denominacion_de_proyecto": "Proyecto Combinado",
    }

    response = auth_client.patch(
        f"/liquidaciones/generales/{liquidacion_id}",
        json=patch_payload,
    )

    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.content}"

    # Verify both updates
    lg = LiquidacionGeneral.objects.get(id=liquidacion_id)
    assert lg.expediente == "EXP-MODIFIED-001"
    assert lg.denominacion_de_proyecto == "Proyecto Combinado"
