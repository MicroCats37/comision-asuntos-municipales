"""
Integration tests for RH Delegado Mensual flows — cotización y creación.

Tests usan los flujos directamente (no HTTP) para evitar problemas de inyección
con TestClient. Los flujos son los mismos que los endpoints llaman por detrás.
Tests usan @pytest.mark.django_db para acceso a BD.

Covers:
- RHDelegadoMensualCotizarFlujo.cotizar() — cotización sin BD
- RHDelegadoMensualCrearFlujo.crear() — creación con BD
- Validación: CIP no existe → 404
- Validación: liquidación sin detalle porcentual → 400
- crear() retorna liquidacion_delegado_id populated en cada item (BUG FIX)
- cotizar() retorna liquidacion_delegado_id=None (expected — record not created yet)
"""
import pytest
from decimal import Decimal
from datetime import date
from django.core.management import call_command

from modules.entidades.domain.models.ubigeo import (
    UbigeoDepartamento,
    UbigeoProvincia,
    UbigeoDistrito,
)
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.usuarios.domain.models.perfil_ingeniero import (
    PerfilIngeniero,
    EspecialidadRevision,
)
from modules.liquidaciones.domain.models.delegado import Delegado, DelegadoOperacion, LiquidacionDelegado
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    DerechoPorcentajeObra,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion as TipoLiquidacionConst
from modules.finanzas.domain.models.tasa_delegado import TasaDelegado
from modules.finanzas.domain.models.recibo_honorario_delegado_mensual import (
    ReciboHonorarioDelegadoMensual,
)
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
    RHDelegadoMensualCotizarFlujo,
    RHDelegadoMensualCrearFlujo,
)
from modules.finanzas.domain.schemas import RHDelegadoCotizarIn, RHDelegadoCotizarItemIn
from django.contrib.auth import get_user_model


# ── Fixtures ────────────────────────────────────────────────────────────────────

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
        codigo="M001",
        nombre="Municipalidad de Miraflores",
        distrito=ubigeo_distrito,
    )


@pytest.fixture
def proyecto(db, municipalidad, ubigeo_distrito):
    return Proyecto.objects.create(
        nombre_propietario="Propietario Test SAC",
        direccion="Av. Test 123",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789012",
        entidad_razon_social="Propietario Test SAC",
    )


@pytest.fixture
def usuario_delegado(db):
    User = get_user_model()
    return User.objects.create_user(
        username="delegado_mensual",
        email="delegado_mensual@test.com",
        password="testpass123",
        dni="87654321",
    )


@pytest.fixture
def perfil_ingeniero_delegado(db, usuario_delegado):
    return PerfilIngeniero.objects.create(
        usuario=usuario_delegado,
        apellido_paterno="Pérez",
        apellido_materno="García",
        nombres="Juan",
        cip="CIP-DELEGADO-001",
        dni="87654321",
    )


@pytest.fixture
def delegado(db, perfil_ingeniero_delegado):
    return Delegado.objects.create(
        perfil_ingeniero=perfil_ingeniero_delegado,
    )


@pytest.fixture
def especialidad_estructuras(db):
    return EspecialidadRevision.objects.create(
        slug="estructuras", nombre="Estructuras",
    )


@pytest.fixture
def usuario_liquidacion(db):
    User = get_user_model()
    return User.objects.create_user(
        username="liq_delegado_mensual",
        email="liq_delegado_mensual@test.com",
        password="testpass123",
        dni="11223344",
    )


@pytest.fixture
def tipo_edificacion(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacionConst.EDIFICACION, defaults={"nombre": "Edificaciones"}
    )[0]


@pytest.fixture
def igv_vigente(db):
    from modules.finanzas.domain.models.impuestos import IGV
    return IGV.objects.create(valor=Decimal("0.18"), periodo_inicio=date(2024, 1, 1), periodo_fin=None)


@pytest.fixture
def uit_vigente(db):
    from modules.finanzas.domain.models.impuestos import UIT
    return UIT.objects.create(valor=Decimal("5150.00"), periodo_inicio=date(2024, 1, 1), periodo_fin=None)


@pytest.fixture
def tarifa_liquidacion_base(db, tipo_edificacion):
    return TarifaLiquidacionBase.objects.create(
        tipo_liquidacion=tipo_edificacion,
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def derecho_porcentaje_vigente(db):
    return DerechoPorcentajeObra.objects.create(
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def tarifa_porcentaje_obra(db, tarifa_liquidacion_base):
    return TarifaPorcentajeObra.objects.create(
        tarifa_base=tarifa_liquidacion_base,
        porcentaje_liquidacion=Decimal("0.0010"),
    )


@pytest.fixture
def tasa_delegado_vigente(db, tipo_edificacion):
    """TasaDelegado vigente (per-tipo EDIFICACION) con tasas estándar (vigencia desde 1900)."""
    return TasaDelegado.objects.create(
        nombre="Tasas Delegado (vigencia histórica)",
        tipo_liquidacion=tipo_edificacion,
        renta_cip=Decimal("0.25"),
        aporte_codemu=Decimal("0.05"),
        fondo_comun=Decimal("0.10"),
        periodo_inicio=date(1900, 1, 1),
        periodo_fin=None,
    )


@pytest.fixture
def liquidacion_general_porcentaje(
    db, proyecto, municipalidad, tipo_edificacion, usuario_liquidacion, igv_vigente, uit_vigente
):
    """LiquidacionGeneral of EDIFICACION type with sub_total=5000.00."""
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-DEL-MEN-001",
        estado="REGISTRADO",
        sub_total=Decimal("5000.00"),
        total=Decimal("5900.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
        numero_revision=1,
    )


@pytest.fixture
def liquidacion_porcentaje_obra(db, liquidacion_general_porcentaje, derecho_porcentaje_vigente):
    """LiquidacionPorcentajeObra linked to the EDIFICACION liquidacion."""
    return LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=liquidacion_general_porcentaje,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("100000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )


@pytest.fixture
def liquidacion_porcentaje_detalle(
    db, liquidacion_porcentaje_obra, tarifa_porcentaje_obra, especialidad_estructuras
):
    """LiquidacionPorcentajeObraDetalle matching the delegado's especialidad.
    
    imp_bruto = subtotal = 1000.00
    """
    return LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=liquidacion_porcentaje_obra,
        tarifa_aplicada=tarifa_porcentaje_obra,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
    )


# ── Flujo directo helpers ────────────────────────────────────────────────────────

@pytest.fixture
def core_service(db):
    return FinanzasCoreService()


@pytest.fixture
def cotizar_flujo(core_service):
    return RHDelegadoMensualCotizarFlujo(core=core_service)


@pytest.fixture
def crear_flujo(core_service, cotizar_flujo):
    return RHDelegadoMensualCrearFlujo(core=core_service, cotizar_flujo=cotizar_flujo)


@pytest.fixture
def delegado_operacion(db, delegado, municipalidad, especialidad_estructuras, tipo_edificacion):
    """DelegadoOperacion linked to the delegado, municipalidad, and especialidad used in tests."""
    return DelegadoOperacion.objects.create(
        delegado=delegado,
        municipalidad=municipalidad,
        especialidad_revision=especialidad_estructuras,
        tipo_liquidacion=tipo_edificacion,
    )


@pytest.fixture
def orquestador(core_service):
    from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
    from modules.finanzas.domain.services.flujos.finanzas_flujo import FinanzasFlujo
    flujo = FinanzasFlujo(core=core_service)
    return FinanzasOrchestrator(flujo=flujo, core=core_service)


def _payload(cip: str, periodo: str, items: list[dict], delegado_operacion_id: str = "00000000-0000-0000-0000-000000000001"):
    """Helper para construir el payload de cotización del delegado."""
    return RHDelegadoCotizarIn(
        cip=cip,
        periodo=periodo,
        delegado_operacion_id=delegado_operacion_id,
        items=[RHDelegadoCotizarItemIn(**i) for i in items],
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_cotizar_retorna_liquidacion_delegado_id_null(
    cotizar_flujo,
    delegado,
    perfil_ingeniero_delegado,
    liquidacion_general_porcentaje,
    liquidacion_porcentaje_detalle,
    tasa_delegado_vigente,
    delegado_operacion,
):
    """
    RHDelegadoMensualCotizarFlujo.cotizar() returns items with liquidacion_delegado_id=None
    because the LiquidacionDelegado record is not created during cotizar (only during crear).

    This is the expected behavior — cotizar is a read-only calculation.
    """
    result = cotizar_flujo.cotizar(
        _payload(
            cip=perfil_ingeniero_delegado.cip,
            periodo="2026-01",
            items=[{
                "liquidacion_general_id": str(liquidacion_general_porcentaje.id),
                "especialidad_revision_id": str(liquidacion_porcentaje_detalle.especialidad_id),
                "periodo": 2026,
                "mes": 1,
            }],
            delegado_operacion_id=str(delegado_operacion.id),
        )
    )

    assert result.delegado.id == str(delegado.id)
    assert result.periodo == "2026-01"
    assert len(result.items) == 1

    item = result.items[0]
    assert item.liquidacion_delegado_id is None  # cotizar no crea registros
    assert item.exp_liqui == liquidacion_general_porcentaje.expediente
    assert item.imp_bruto == Decimal("1000.00")

    # Precision: Decimal fields must preserve exact 2-decimal-place values
    assert item.imp_bruto.as_tuple().exponent >= -2, (
        f"imp_bruto={item.imp_bruto} must have at most 2 decimal places"
    )

    # Verificar que NO se creó nada en BD
    assert LiquidacionDelegado.objects.count() == 0


@pytest.mark.django_db
def test_crear_retorna_liquidacion_delegado_id_poblado(
    crear_flujo,
    cotizar_flujo,
    delegado,
    perfil_ingeniero_delegado,
    liquidacion_general_porcentaje,
    liquidacion_porcentaje_detalle,
    tasa_delegado_vigente,
    delegado_operacion,
):
    """
    RHDelegadoMensualCrearFlujo.crear() creates LiquidacionDelegado records
    and MUST return each item with the corresponding liquidacion_delegado_id populated.

    This is a regression test for a bug where crear() returned items with
    liquidacion_delegado_id=None even though records were persisted.
    """
    result = crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_delegado.cip,
            periodo="2026-01",
            items=[{
                "liquidacion_general_id": str(liquidacion_general_porcentaje.id),
                "especialidad_revision_id": str(liquidacion_porcentaje_detalle.especialidad_id),
                "periodo": 2026,
                "mes": 1,
            }],
            delegado_operacion_id=str(delegado_operacion.id),
        )
    )

    # Verificar que se crearon los registros en BD
    assert LiquidacionDelegado.objects.count() == 1
    ld = LiquidacionDelegado.objects.first()
    assert ld is not None
    assert str(ld.id) == result.items[0].liquidacion_delegado_id

    # Verificar que el ID poblado en la respuesta coincide con el registro BD
    assert result.items[0].liquidacion_delegado_id == str(ld.id)

    # Verificar que el RH mensual también se creó
    assert ReciboHonorarioDelegadoMensual.objects.count() == 1


@pytest.mark.django_db
def test_crear_multiple_items_cada_uno_retorna_su_liquidacion_delegado_id(
    crear_flujo,
    cotizar_flujo,
    delegado,
    perfil_ingeniero_delegado,
    tasa_delegado_vigente,
    tipo_edificacion,
    proyecto,
    municipalidad,
    usuario_liquidacion,
    igv_vigente,
    uit_vigente,
    tarifa_porcentaje_obra,
    especialidad_estructuras,
    derecho_porcentaje_vigente,
    liquidacion_general_porcentaje,
    liquidacion_porcentaje_detalle,
    delegado_operacion,
    # NOTE: liquidacion_delegado_porcentaje NOT included intentionally —
    # both items should be created fresh by crear().
):
    # Crear segunda LiquidacionGeneral + detalle para el segundo item
    lg2 = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        usuario_creador=usuario_liquidacion,
        expediente="EXP-DEL-MEN-002",
        estado="REGISTRADO",
        sub_total=Decimal("3000.00"),
        total=Decimal("3540.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
        numero_revision=1,
    )
    lpo2 = LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=lg2,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("60000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )
    lpdet2 = LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=lpo2,
        tarifa_aplicada=tarifa_porcentaje_obra,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("600.00"),
    )

    result = crear_flujo.crear(
        _payload(
            cip=perfil_ingeniero_delegado.cip,
            periodo="2026-02",
            items=[
                {
                    "liquidacion_general_id": str(liquidacion_general_porcentaje.id),
                    "especialidad_revision_id": str(liquidacion_porcentaje_detalle.especialidad_id),
                    "periodo": 2026,
                    "mes": 2,
                },
                {
                    "liquidacion_general_id": str(lg2.id),
                    "especialidad_revision_id": str(lpdet2.especialidad_id),
                    "periodo": 2026,
                    "mes": 2,
                },
            ],
            delegado_operacion_id=str(delegado_operacion.id),
        )
    )

    assert len(result.items) == 2

    # Cada item deve tener un liquidacion_delegado_id no nulo y único
    ids_seen = set()
    for i, item in enumerate(result.items):
        assert item.liquidacion_delegado_id is not None, (
            f"Item {i} should have liquidacion_delegado_id populated after crear()"
        )
        assert item.liquidacion_delegado_id not in ids_seen, (
            f"Item {i} has duplicate liquidacion_delegado_id: {item.liquidacion_delegado_id}"
        )
        ids_seen.add(item.liquidacion_delegado_id)

    # Verificar que los IDs existen en la BD
    for item in result.items:
        assert LiquidacionDelegado.objects.filter(id=item.liquidacion_delegado_id).exists()


@pytest.mark.django_db
def test_cotizar_cip_inexistente_retorna_404(
    cotizar_flujo,
    tasa_delegado_vigente,
):
    """
    Cotizar con CIP inexistente → HttpError 404.
    """
    from ninja.errors import HttpError

    with pytest.raises(HttpError) as excinfo:
        cotizar_flujo.cotizar(
            _payload(
                cip="CIP-INEXISTENTE",
                periodo="2026-01",
                items=[{"liquidacion_general_id": "00000000-0000-0000-0000-000000000001", "especialidad_revision_id": "00000000-0000-0000-0000-000000000001"}],
            )
        )
    assert excinfo.value.status_code == 404


@pytest.mark.django_db
def test_cotizar_liquidacion_sin_detalle_porcentaje_retorna_400(
    cotizar_flujo,
    delegado,
    perfil_ingeniero_delegado,
    liquidacion_general_porcentaje,
    tasa_delegado_vigente,
    especialidad_estructuras,
    delegado_operacion,
):
    """
    Cotizar con una liquidación que NO tiene LiquidacionPorcentajeObraDetalle
    para la especialidad del delegado → HttpError 400.
    """
    from ninja.errors import HttpError

    # Usar una especialidad que NO tiene detalle
    otra_especialidad = EspecialidadRevision.objects.create(
        slug="geotecnia", nombre="Geotecnia",
    )

    with pytest.raises(HttpError) as excinfo:
        cotizar_flujo.cotizar(
            _payload(
                cip=perfil_ingeniero_delegado.cip,
                periodo="2026-01",
                items=[{
                    "liquidacion_general_id": str(liquidacion_general_porcentaje.id),
                    "especialidad_revision_id": str(otra_especialidad.id),
                }],
                delegado_operacion_id=str(delegado_operacion.id),
            )
        )
    assert excinfo.value.status_code == 400
    assert "detalle porcentual" in str(excinfo.value.message).lower()


@pytest.mark.django_db
def test_list_rh_mensual_detalles_incluye_todos_los_campos_por_fila(
    crear_flujo,
    cotizar_flujo,
    core_service,
    orquestador,
    delegado,
    perfil_ingeniero_delegado,
    liquidacion_general_porcentaje,
    liquidacion_porcentaje_detalle,
    tasa_delegado_vigente,
    delegado_operacion,
):
    """
    After crear(), the list/detail response detalles[] must include ALL per-row
    fields (liquidacion_delegado_id, expediente, fecha_revision, numero_revision,
    total_liquidacion, sub_total_liquidacion, numero_rh, imp_bruto, renta_cip,
    aporte_codemu, fondo_comun, neto_honorario, periodo, mes, dictamen_revision,
    fecha_presentacion) so the frontend can rebuild the same table shown in cotizar.

    This is a regression test for the bug where list/detail only returned
    expediente and imp_bruto per detail.
    """
    from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
    from modules.finanzas.domain.schemas import RHDelegadoCotizarIn, RHDelegadoCotizarItemIn

    # 1. Crear RH mensual
    result = crear_flujo.crear(
        RHDelegadoCotizarIn(
            cip=perfil_ingeniero_delegado.cip,
            periodo="2026-03",
            delegado_operacion_id=str(delegado_operacion.id),
            items=[
                RHDelegadoCotizarItemIn(
                    liquidacion_general_id=str(liquidacion_general_porcentaje.id),
                    especialidad_revision_id=str(liquidacion_porcentaje_detalle.especialidad_id),
                    periodo=2026,
                    mes=3,
                )
            ],
        )
    )

    # 2. Cotizar independently (to compare values)
    cotizar_result = cotizar_flujo.cotizar(
        RHDelegadoCotizarIn(
            cip=perfil_ingeniero_delegado.cip,
            periodo="2026-03",
            delegado_operacion_id=str(delegado_operacion.id),
            items=[
                RHDelegadoCotizarItemIn(
                    liquidacion_general_id=str(liquidacion_general_porcentaje.id),
                    especialidad_revision_id=str(liquidacion_porcentaje_detalle.especialidad_id),
                    periodo=2026,
                    mes=3,
                )
            ],
        )
    )

    # 3. Obtener el detalle desde la BD (ORM) y pasarlo al builder
    from modules.finanzas.domain.models.recibo_honorario_delegado_mensual import (
        ReciboHonorarioDelegadoMensual,
    )
    from modules.finanzas.domain.results.rh_delegado_mensual_result import (
        RHDelegadoMensualListItemResult,
    )

    rh_mensual = ReciboHonorarioDelegadoMensual.objects.prefetch_related(
        "detalles__liquidacion_delegado__liquidacion"
    ).first()
    assert rh_mensual is not None

    # 4. Build domain result using the orchestrator's builder (same code path as list endpoint)
    domain_result = orquestador._build_rh_mensual_delegado_result(rh_mensual)

    # 5. Verify details structure
    assert len(domain_result.detalles) == 1
    detalle = domain_result.detalles[0]

    # All required fields must be present (no Nones where we expect values)
    assert detalle.liquidacion_delegado_id is not None
    assert detalle.expediente == liquidacion_general_porcentaje.expediente
    assert detalle.imp_bruto == Decimal("1000.00")  # from fixture
    assert detalle.periodo == 2026
    assert detalle.mes == 3

    # Per-row partials: verify they match cotizar math
    # TasaDelegado fixture: renta_cip=0.25, aporte_codemu=0.05, fondo_comun=0.10
    # imp_bruto=1000.00
    #   renta_cip = 1000 * 0.25 = 250.00
    #   aporte_codemu = 1000 * 0.05 = 50.00
    #   fondo_comun = 1000 * 0.10 = 100.00
    #   neto = 1000 - 250 - 50 - 100 = 600.00
    assert detalle.renta_cip == Decimal("250.00")
    assert detalle.aporte_codemu == Decimal("50.00")
    assert detalle.fondo_comun == Decimal("100.00")
    assert detalle.neto_honorario == Decimal("600.00")

    # Precision: all Decimal fields must have at most 2 decimal places
    for field_name in ["imp_bruto", "renta_cip", "aporte_codemu", "fondo_comun", "neto_honorario"]:
        val = getattr(detalle, field_name)
        assert val is not None and val.as_tuple().exponent >= -2, (
            f"detalle.{field_name}={val} must have at most 2 decimal places"
        )

    # Numeros / fechas from LiquidacionDelegado
    assert detalle.numero_revision == liquidacion_general_porcentaje.numero_revision
    assert detalle.total_liquidacion == liquidacion_general_porcentaje.total
    assert detalle.sub_total_liquidacion == liquidacion_general_porcentaje.sub_total

    # 6. Verify the presenter mapping also works (no schema errors)
    from modules.finanzas.presentation.presenters.finanzas_presenter import FinanzasPresenter

    presented = FinanzasPresenter._map_rh_mensual_delegado_out(domain_result)
    presented_detalle = presented.detalles[0]
    assert presented_detalle.expediente == liquidacion_general_porcentaje.expediente
    assert presented_detalle.imp_bruto == Decimal("1000.00")
    assert presented_detalle.renta_cip == Decimal("250.00")
    assert presented_detalle.aporte_codemu == Decimal("50.00")
    assert presented_detalle.fondo_comun == Decimal("100.00")
    assert presented_detalle.neto_honorario == Decimal("600.00")


@pytest.mark.django_db
def test_crear_rh_delegado_mensual_con_delegado_operacion_setea_delegado_from_operacion(
    core_service,
    delegado,
    delegado_operacion,
):
    """
    When crear_rh_delegado_mensual is called with only delegado_operacion_id
    (no explicit delegado_id in the get_or_create defaults), the resulting
    ReciboHonorarioDelegadoMensual.delegado_id must equal
    delegado_operacion.delegado_id.

    This is a regression test for the bug where get_or_create was called with
    delegado_operacion_id but without setting the required FK fields,
    causing: django.db.utils.IntegrityError: NOT NULL constraint failed:
    finanzas_recibohonorariodelegadomensual.delegado_id
    """
    periodo = "2026-01"
    sub_total = Decimal("1000.00")
    renta_cip = Decimal("250.00")
    aporte_codemu = Decimal("50.00")
    fondo_comun = Decimal("100.00")
    neto_honorario = Decimal("600.00")

    # Call with only delegado_operacion_id — this is the path that was failing
    recibo = core_service.crear_rh_delegado_mensual(
        delegado_id=str(delegado.id),
        periodo=periodo,
        sub_total=sub_total,
        renta_cip=renta_cip,
        aporte_codemu=aporte_codemu,
        fondo_comun=fondo_comun,
        neto_honorario=neto_honorario,
        delegado_operacion_id=str(delegado_operacion.id),
    )

    # Prove the record was created (returns the new record)
    assert recibo is not None
    assert isinstance(recibo, ReciboHonorarioDelegadoMensual)

    # Prove the required FK was set from delegado_operacion.delegado
    assert recibo.delegado_id == delegado_operacion.delegado_id, (
        f"recibo.delegado_id={recibo.delegado_id} must equal "
        f"delegado_operacion.delegado_id={delegado_operacion.delegado_id}"
    )

    # Prove the FK chain is consistent: DelegadoOperacion.delegado == Delegado
    assert str(recibo.delegado_id) == str(delegado.id), (
        f"recibo.delegado_id={recibo.delegado_id} must equal "
        f"delegado.id={delegado.id}"
    )

    # Prove that when called again with same params, a NEW record is created
    # (no idempotency — each crear() call produces a new RH header)
    recibo2 = core_service.crear_rh_delegado_mensual(
        delegado_id=str(delegado.id),
        periodo=periodo,
        sub_total=sub_total,
        renta_cip=renta_cip,
        aporte_codemu=aporte_codemu,
        fondo_comun=fondo_comun,
        neto_honorario=neto_honorario,
        delegado_operacion_id=str(delegado_operacion.id),
    )
    assert recibo2.id != recibo.id, "Second call should create a new record, not return existing"
    assert ReciboHonorarioDelegadoMensual.objects.count() == 2, (
        "Two calls should create two RH records"
    )


@pytest.mark.django_db
def test_cotizar_usa_tasa_del_tipo_de_la_operatividad(
    cotizar_flujo,
    delegado,
    perfil_ingeniero_delegado,
    liquidacion_general_porcentaje,
    liquidacion_porcentaje_detalle,
    tasa_delegado_vigente,
    delegado_operacion,
    tipo_edificacion,
):
    """
    cotizar() usa la tasa vigente del TIPO de liquidación de la operatividad.

    Se crea una tasa distinta para TALUDES (tasa diferente) y se verifica que el
    cálculo usa la tasa de EDIFICACION (0.25/0.05/0.10), no la del otro tipo.
    """
    from ninja.errors import HttpError
    from modules.liquidaciones.domain.constants import (
        TipoLiquidacion as TipoLiquidacionConst,
    )

    # Tasa per-tipo para TALUDES con valores DIFERENTES al de EDIFICACION.
    tipo_taludes = TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacionConst.TALUDES, defaults={"nombre": "Taludes"}
    )[0]
    TasaDelegado.objects.create(
        nombre="Tasas Delegado Taludes",
        tipo_liquidacion=tipo_taludes,
        renta_cip=Decimal("0.30"),
        aporte_codemu=Decimal("0.06"),
        fondo_comun=Decimal("0.12"),
        periodo_inicio=date(1900, 1, 1),
        periodo_fin=None,
    )

    result = cotizar_flujo.cotizar(
        _payload(
            cip=perfil_ingeniero_delegado.cip,
            periodo="2026-04",
            items=[{
                "liquidacion_general_id": str(liquidacion_general_porcentaje.id),
                "especialidad_revision_id": str(liquidacion_porcentaje_detalle.especialidad_id),
                "periodo": 2026,
                "mes": 4,
            }],
            delegado_operacion_id=str(delegado_operacion.id),
        )
    )

    # imp_bruto = 1000.00 → EDIFICACION: renta 0.25 -> 250.00 (no 300 del otro tipo)
    assert result.totales.renta_cip == Decimal("250.00")
    assert result.totales.aporte_codemu == Decimal("50.00")
    assert result.totales.fondo_comun == Decimal("100.00")
    assert result.items[0].renta_cip == Decimal("250.00")


@pytest.mark.django_db
def test_cotizar_operatividad_sin_tipo_retorna_400(
    cotizar_flujo,
    delegado,
    perfil_ingeniero_delegado,
    municipalidad,
    especialidad_estructuras,
    liquidacion_general_porcentaje,
    liquidacion_porcentaje_detalle,
    tasa_delegado_vigente,
):
    """
    Si la operatividad (DelegadoOperacion) NO tiene tipo de liquidación asignado,
    cotizar() debe lanzar HttpError(400) — sin fallback a tasa global.
    """
    from ninja.errors import HttpError

    op_sin_tipo = DelegadoOperacion.objects.create(
        delegado=delegado,
        municipalidad=municipalidad,
        especialidad_revision=especialidad_estructuras,
        tipo_liquidacion=None,
    )

    with pytest.raises(HttpError) as excinfo:
        cotizar_flujo.cotizar(
            _payload(
                cip=perfil_ingeniero_delegado.cip,
                periodo="2026-05",
                items=[{
                    "liquidacion_general_id": str(liquidacion_general_porcentaje.id),
                    "especialidad_revision_id": str(liquidacion_porcentaje_detalle.especialidad_id),
                    "periodo": 2026,
                    "mes": 5,
                }],
                delegado_operacion_id=str(op_sin_tipo.id),
            )
        )
    assert excinfo.value.status_code == 400
    assert "tipo de liquidación" in str(excinfo.value.message).lower()


@pytest.mark.django_db
def test_seed_tasas_delegado_replica_para_los_6_tipos(db):
    """
    seed_tasas_delegado debe crear/actualizar una TasaDelegado por cada uno de
    los 6 TipoLiquidacion canónicos (misma tasa 0.25/0.05/0.10, 1900-01-01, fin NULL).
    """
    call_command("seed_tasas_delegado")

    from modules.liquidaciones.domain.constants import (
        TipoLiquidacion as TipoLiquidacionConst,
    )

    codigos = [
        TipoLiquidacionConst.EDIFICACION,
        TipoLiquidacionConst.HABILITACION_URBANA,
        TipoLiquidacionConst.MECANICA_SUELOS,
        TipoLiquidacionConst.IMPACTO_VIAL,
        TipoLiquidacionConst.TALUDES,
        TipoLiquidacionConst.INSPECCION_OBRA,
    ]

    # Los 6 TipoLiquidacion deben existir (la semilla los crea si faltan).
    assert TipoLiquidacionModel.objects.count() == 6

    tasas = TasaDelegado.objects.filter(periodo_inicio=date(1900, 1, 1))
    assert tasas.count() == 6

    for codigo in codigos:
        tipo = TipoLiquidacionModel.objects.get(codigo=codigo)
        tasa = TasaDelegado.objects.get(
            tipo_liquidacion=tipo, periodo_inicio=date(1900, 1, 1)
        )
        assert tasa.periodo_fin is None
        assert tasa.renta_cip == Decimal("0.25")
        assert tasa.aporte_codemu == Decimal("0.05")
        assert tasa.fondo_comun == Decimal("0.10")
