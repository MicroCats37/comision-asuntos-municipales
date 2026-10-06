"""
Integration tests for RH Detalle Delegado — list detail rows with CIP filtering.

Tests the core service and orchestrator for the flat detail list endpoint:
GET /finanzas/recibos-delegados/detalle

Covers:
- list_detalle_honorario_delegado_paginated with delegado_cip filter
- list_rh_detalle_delegados_proceso with delegado_cip filter
- Precedence: delegado_cip wins over delegado_id when both are provided
- Filter chip display in frontend uses CIP
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date

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
from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.services.finanzas_orchestrator import FinanzasOrchestrator
from modules.finanzas.domain.services.flujos.finanzas_flujo import FinanzasFlujo
from django.contrib.auth import get_user_model


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def ubigeo_departamento(db):
    return UbigeoDepartamento.objects.create(nombre="Lima")

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
def segunda_municipalidad(db, ubigeo_distrito):
    return Municipalidad.objects.create(
        codigo="M002",
        nombre="Municipalidad de San Isidro",
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
        username="delegado_detalle",
        email="delegado_detalle@test.com",
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
        cip="118318",
        dni="87654321",
    )

@pytest.fixture
def delegado(db, perfil_ingeniero_delegado):
    return Delegado.objects.create(
        perfil_ingeniero=perfil_ingeniero_delegado,
    )

@pytest.fixture
def segundo_usuario_delegado(db):
    User = get_user_model()
    return User.objects.create_user(
        username="delegado_detalle_2",
        email="delegado_detalle_2@test.com",
        password="testpass123",
        dni="11223344",
    )

@pytest.fixture
def segundo_perfil_ingeniero_delegado(db, segundo_usuario_delegado):
    return PerfilIngeniero.objects.create(
        usuario=segundo_usuario_delegado,
        apellido_paterno="López",
        apellido_materno="Martínez",
        nombres="Pedro",
        cip="223344",
        dni="11223344",
    )

@pytest.fixture
def segundo_delegado(db, segundo_perfil_ingeniero_delegado):
    return Delegado.objects.create(
        perfil_ingeniero=segundo_perfil_ingeniero_delegado,
    )

@pytest.fixture
def especialidad_estructuras(db):
    return EspecialidadRevision.objects.create(
        slug="estructuras", nombre="Estructuras",
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
    db, proyecto, municipalidad, tipo_edificacion, usuario_delegado, igv_vigente, uit_vigente
):
    return LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_edificacion,
        usuario_creador=usuario_delegado,
        expediente="EXP-DEL-DET-001",
        estado="REGISTRADO",
        sub_total=Decimal("5000.00"),
        total=Decimal("5900.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
        numero_revision=1,
    )

@pytest.fixture
def liquidacion_porcentaje_obra(db, liquidacion_general_porcentaje, derecho_porcentaje_vigente):
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
    return LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=liquidacion_porcentaje_obra,
        tarifa_aplicada=tarifa_porcentaje_obra,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("1000.00"),
        importe_parcial=Decimal("1000.00"),
        ajuste_redondeo=Decimal("0.00"),
    )

@pytest.fixture
def segundo_proyecto(db, municipalidad, ubigeo_distrito):
    """Second proyecto for the second delegado's liquidacion."""
    return Proyecto.objects.create(
        nombre_propietario="Propietario Dos SAC",
        direccion="Av. Segunda 456",
        distrito_id=ubigeo_distrito.id,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789013",
        entidad_razon_social="Propietario Dos SAC",
    )

@pytest.fixture
def segundo_liquidacion_general_porcentaje(
    db, segundo_proyecto, segunda_municipalidad, tipo_edificacion, usuario_delegado, igv_vigente, uit_vigente
):
    """Liquidacion for segundo delegado."""
    return LiquidacionGeneral.objects.create(
        proyecto=segundo_proyecto,
        municipalidad=segunda_municipalidad,
        tipo_liquidacion=tipo_edificacion,
        usuario_creador=usuario_delegado,
        expediente="EXP-DEL-DET-002",
        estado="REGISTRADO",
        sub_total=Decimal("3000.00"),
        total=Decimal("3540.00"),
        igv_id=igv_vigente,
        uit_id=uit_vigente,
        numero_revision=1,
    )

@pytest.fixture
def segunda_liquidacion_porcentaje_obra(
    db, segundo_liquidacion_general_porcentaje, derecho_porcentaje_vigente
):
    return LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=segundo_liquidacion_general_porcentaje,
        tipo_tramite="OBRA_NUEVA",
        valor_declarado=Decimal("60000.00"),
        porcentaje_liquidacion=Decimal("0.0010"),
        derecho_minimo=Decimal("500.00"),
        derecho_maximo=Decimal("50000.00"),
        porcentaje_minimo_uit=Decimal("0.10"),
        derecho_aplicado=derecho_porcentaje_vigente,
    )

@pytest.fixture
def segunda_liquidacion_porcentaje_detalle(
    db, segunda_liquidacion_porcentaje_obra, tarifa_porcentaje_obra, especialidad_estructuras
):
    return LiquidacionPorcentajeObraDetalle.objects.create(
        liquidacion_porcentaje=segunda_liquidacion_porcentaje_obra,
        tarifa_aplicada=tarifa_porcentaje_obra,
        especialidad=especialidad_estructuras,
        porcentaje_aplicado=Decimal("0.0010"),
        subtotal=Decimal("600.00"),
        importe_parcial=Decimal("600.00"),
        ajuste_redondeo=Decimal("0.00"),
    )

@pytest.fixture
def delegado_operacion(db, delegado, municipalidad, especialidad_estructuras, tipo_edificacion):
    return DelegadoOperacion.objects.create(
        delegado=delegado,
        municipalidad=municipalidad,
        especialidad_revision=especialidad_estructuras,
        tipo_liquidacion=tipo_edificacion,
    )

@pytest.fixture
def segundo_delegado_operacion(db, segundo_delegado, municipalidad, especialidad_estructuras, tipo_edificacion):
    return DelegadoOperacion.objects.create(
        delegado=segundo_delegado,
        municipalidad=municipalidad,
        especialidad_revision=especialidad_estructuras,
        tipo_liquidacion=tipo_edificacion,
    )


@pytest.fixture
def delegado_operacion_segunda_municipalidad(
    db, segundo_delegado, segunda_municipalidad, especialidad_estructuras, tipo_edificacion
):
    return DelegadoOperacion.objects.create(
        delegado=segundo_delegado,
        municipalidad=segunda_municipalidad,
        especialidad_revision=especialidad_estructuras,
        tipo_liquidacion=tipo_edificacion,
    )

@pytest.fixture
def core_service(db):
    return FinanzasCoreService()

@pytest.fixture
def orquestador(core_service):
    flujo = FinanzasFlujo(core=core_service)
    return FinanzasOrchestrator(flujo=flujo, core=core_service)


# ── Setup helpers ───────────────────────────────────────────────────────────────

def _crear_liquidacion_delegado(db, liquidacion_general, delegado, especialidad, periodo, mes, operacion=None):
    """Helper to create a LiquidacionDelegado assignment."""
    return LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_general,
        delegado=delegado,
        especialidad_revision=especialidad,
        numero_rh=f"RH-{periodo}-{mes:02d}",
        periodo=periodo,
        mes=mes,
        dictamen_revision="FAVORABLE",
        fecha_presentacion=date(2026, mes, 15),
        fecha_revision=date(2026, mes, 20),
        delegado_operacion=operacion,
    )

def _crear_detalle_delegado(db, recibo_mensual, liquidacion_delegado, imp_bruto=Decimal("1000.00")):
    """Helper to create a DetalleHonorarioDelegado row."""
    return DetalleHonorarioDelegado.objects.create(
        recibo_mensual=recibo_mensual,
        liquidacion_delegado=liquidacion_delegado,
        imp_bruto=imp_bruto,
        sub_total=imp_bruto,
        renta_cip=imp_bruto * Decimal("0.25"),
        aporte_codemu=imp_bruto * Decimal("0.05"),
        fondo_comun=imp_bruto * Decimal("0.10"),
        neto_honorario=imp_bruto * Decimal("0.60"),
    )


# ── Tests ────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_detalle_delegado_filtro_por_cip(
    db,
    core_service,
    perfil_ingeniero_delegado,
    segundo_perfil_ingeniero_delegado,
    delegado,
    segundo_delegado,
    liquidacion_general_porcentaje,
    segundo_liquidacion_general_porcentaje,
    especialidad_estructuras,
    tasa_delegado_vigente,
):
    """
    GIVEN: Two delegado records with different CIPs, each with DetalleHonorarioDelegado rows
    WHEN:  list_detalle_honorario_delegado_paginated is called with delegado_cip="118318"
    THEN:  Only rows belonging to the CIP 118318 delegado are returned
    """
    # Create liquidaciones for both delegados
    ld1 = LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_general_porcentaje,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
        numero_rh="RH-2026-01",
        periodo=2026,
        mes=1,
        dictamen_revision="FAVORABLE",
    )
    ld2 = LiquidacionDelegado.objects.create(
        liquidacion=segundo_liquidacion_general_porcentaje,
        delegado=segundo_delegado,
        especialidad_revision=especialidad_estructuras,
        numero_rh="RH-2026-01",
        periodo=2026,
        mes=1,
        dictamen_revision="FAVORABLE",
    )

    # Create a ReciboHonorarioDelegadoMensual for each
    recibo1 = ReciboHonorarioDelegadoMensual.objects.create(
        delegado=delegado,
        periodo=2026,
        mes=1,
        sub_total=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )
    recibo2 = ReciboHonorarioDelegadoMensual.objects.create(
        delegado=segundo_delegado,
        periodo=2026,
        mes=1,
        sub_total=Decimal("600.00"),
        renta_cip=Decimal("150.00"),
        aporte_codemu=Decimal("30.00"),
        fondo_comun=Decimal("60.00"),
        neto_honorario=Decimal("360.00"),
    )

    # Create detalle rows
    detalle1 = DetalleHonorarioDelegado.objects.create(
        recibo_mensual=recibo1,
        liquidacion_delegado=ld1,
        imp_bruto=Decimal("1000.00"),
        sub_total=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )
    detalle2 = DetalleHonorarioDelegado.objects.create(
        recibo_mensual=recibo2,
        liquidacion_delegado=ld2,
        imp_bruto=Decimal("600.00"),
        sub_total=Decimal("600.00"),
        renta_cip=Decimal("150.00"),
        aporte_codemu=Decimal("30.00"),
        fondo_comun=Decimal("60.00"),
        neto_honorario=Decimal("360.00"),
    )

    # Filter by CIP 118318
    rows, total = core_service.list_detalle_honorario_delegado_paginated(
        page=1,
        page_size=20,
        delegado_cip="118318",
    )

    assert total == 1
    assert len(rows) == 1
    assert rows[0].id == detalle1.id


@pytest.mark.django_db
def test_detalle_delegado_cip_toma_precedencia_sobre_delegado_id(
    db,
    core_service,
    perfil_ingeniero_delegado,
    segundo_perfil_ingeniero_delegado,
    delegado,
    segundo_delegado,
    liquidacion_general_porcentaje,
    segundo_liquidacion_general_porcentaje,
    especialidad_estructuras,
):
    """
    GIVEN: Two delegado records with different CIPs and UUIDs
    WHEN:  list_detalle_honorario_delegado_paginated is called with BOTH delegado_cip and delegado_id
           (but the UUID corresponds to the OTHER delegado)
    THEN:  The CIP filter takes precedence and rows for the other delegado are returned
    """
    # Create liquidaciones for both delegados
    ld1 = LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_general_porcentaje,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
        numero_rh="RH-2026-01",
        periodo=2026,
        mes=1,
        dictamen_revision="FAVORABLE",
    )
    ld2 = LiquidacionDelegado.objects.create(
        liquidacion=segundo_liquidacion_general_porcentaje,
        delegado=segundo_delegado,
        especialidad_revision=especialidad_estructuras,
        numero_rh="RH-2026-01",
        periodo=2026,
        mes=1,
        dictamen_revision="FAVORABLE",
    )

    # Create recibos
    delegado1_id = delegado.id
    delegado2_id = segundo_delegado.id

    recibo1 = ReciboHonorarioDelegadoMensual.objects.create(
        delegado_id=delegado1_id,
        periodo=2026,
        mes=1,
        sub_total=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )
    recibo2 = ReciboHonorarioDelegadoMensual.objects.create(
        delegado_id=delegado2_id,
        periodo=2026,
        mes=1,
        sub_total=Decimal("600.00"),
        renta_cip=Decimal("150.00"),
        aporte_codemu=Decimal("30.00"),
        fondo_comun=Decimal("60.00"),
        neto_honorario=Decimal("360.00"),
    )

    detalle1 = DetalleHonorarioDelegado.objects.create(
        recibo_mensual=recibo1,
        liquidacion_delegado=ld1,
        imp_bruto=Decimal("1000.00"),
        sub_total=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )
    detalle2 = DetalleHonorarioDelegado.objects.create(
        recibo_mensual=recibo2,
        liquidacion_delegado=ld2,
        imp_bruto=Decimal("600.00"),
        sub_total=Decimal("600.00"),
        renta_cip=Decimal("150.00"),
        aporte_codemu=Decimal("30.00"),
        fondo_comun=Decimal("60.00"),
        neto_honorario=Decimal("360.00"),
    )

    # Call with both params — CIP takes precedence
    rows, total = core_service.list_detalle_honorario_delegado_paginated(
        page=1,
        page_size=20,
        delegado_id=delegado2_id,  # This is the OTHER delegado
        delegado_cip="118318",       # CIP 118318 = delegado1
    )

    # Should return rows for CIP 118318, NOT for delegado2_id
    assert total == 1
    assert rows[0].id == detalle1.id


@pytest.mark.django_db
def test_detalle_delegado_orchestrator_filtro_cip(
    db,
    orquestador,
    perfil_ingeniero_delegado,
    segundo_perfil_ingeniero_delegado,
    delegado,
    segundo_delegado,
    liquidacion_general_porcentaje,
    segundo_liquidacion_general_porcentaje,
    especialidad_estructuras,
):
    """
    GIVEN: Two delegados with different CIPs, each with detalle rows
    WHEN:  list_rh_detalle_delegados_proceso is called with delegado_cip
    THEN:  Only rows matching the CIP are returned, with correcto CIP in output
    """
    # Setup liquidaciones
    ld1 = LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_general_porcentaje,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
        numero_rh="RH-2026-02",
        periodo=2026,
        mes=2,
        dictamen_revision="FAVORABLE",
    )
    ld2 = LiquidacionDelegado.objects.create(
        liquidacion=segundo_liquidacion_general_porcentaje,
        delegado=segundo_delegado,
        especialidad_revision=especialidad_estructuras,
        numero_rh="RH-2026-02",
        periodo=2026,
        mes=2,
        dictamen_revision="FAVORABLE",
    )

    recibo1 = ReciboHonorarioDelegadoMensual.objects.create(
        delegado=delegado,
        periodo=2026,
        mes=2,
        sub_total=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )
    recibo2 = ReciboHonorarioDelegadoMensual.objects.create(
        delegado=segundo_delegado,
        periodo=2026,
        mes=2,
        sub_total=Decimal("600.00"),
        renta_cip=Decimal("150.00"),
        aporte_codemu=Decimal("30.00"),
        fondo_comun=Decimal("60.00"),
        neto_honorario=Decimal("360.00"),
    )

    DetalleHonorarioDelegado.objects.create(
        recibo_mensual=recibo1,
        liquidacion_delegado=ld1,
        imp_bruto=Decimal("1000.00"),
        sub_total=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )
    DetalleHonorarioDelegado.objects.create(
        recibo_mensual=recibo2,
        liquidacion_delegado=ld2,
        imp_bruto=Decimal("600.00"),
        sub_total=Decimal("600.00"),
        renta_cip=Decimal("150.00"),
        aporte_codemu=Decimal("30.00"),
        fondo_comun=Decimal("60.00"),
        neto_honorario=Decimal("360.00"),
    )

    results, total = orquestador.list_rh_detalle_delegados_proceso(
        page=1,
        page_size=20,
        delegado_cip="118318",
    )

    assert total == 1
    assert len(results) == 1
    assert results[0].delegado_liquidacion.delegado.cip == "118318"
    assert results[0].delegado_liquidacion.delegado.nombre_completo == "Juan Pérez García"


@pytest.mark.django_db
def test_detalle_delegado_filtra_por_municipalidad(
    db,
    core_service,
    delegado,
    segundo_delegado,
    liquidacion_general_porcentaje,
    segundo_liquidacion_general_porcentaje,
    especialidad_estructuras,
    delegado_operacion,
    delegado_operacion_segunda_municipalidad,
    municipalidad,
):
    ld1 = _crear_liquidacion_delegado(
        db,
        liquidacion_general_porcentaje,
        delegado,
        especialidad_estructuras,
        periodo=2026,
        mes=4,
        operacion=delegado_operacion,
    )
    ld2 = _crear_liquidacion_delegado(
        db,
        segundo_liquidacion_general_porcentaje,
        segundo_delegado,
        especialidad_estructuras,
        periodo=2026,
        mes=4,
        operacion=delegado_operacion_segunda_municipalidad,
    )
    recibo1 = ReciboHonorarioDelegadoMensual.objects.create(
        delegado=delegado,
        delegado_operacion=delegado_operacion,
        periodo=2026,
        mes=4,
        sub_total=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )
    recibo2 = ReciboHonorarioDelegadoMensual.objects.create(
        delegado=segundo_delegado,
        delegado_operacion=delegado_operacion_segunda_municipalidad,
        periodo=2026,
        mes=4,
        sub_total=Decimal("600.00"),
        renta_cip=Decimal("150.00"),
        aporte_codemu=Decimal("30.00"),
        fondo_comun=Decimal("60.00"),
        neto_honorario=Decimal("360.00"),
    )
    detalle1 = _crear_detalle_delegado(db, recibo1, ld1, Decimal("1000.00"))
    _crear_detalle_delegado(db, recibo2, ld2, Decimal("600.00"))

    rows, total = core_service.list_detalle_honorario_delegado_paginated(
        page=1,
        page_size=20,
        municipalidad_id=municipalidad.id,
    )

    assert total == 1
    assert len(rows) == 1
    assert rows[0].id == detalle1.id


@pytest.mark.django_db
def test_detalle_delegado_filtro_cip_sin_resultados(
    db,
    core_service,
    perfil_ingeniero_delegado,
    delegado,
    liquidacion_general_porcentaje,
    especialidad_estructuras,
):
    """
    GIVEN: DetalleHonorarioDelegado rows exist for CIP 118318
    WHEN:  list_detalle_honorario_delegado_paginated is called with non-existent CIP
    THEN:  Empty result is returned
    """
    ld1 = LiquidacionDelegado.objects.create(
        liquidacion=liquidacion_general_porcentaje,
        delegado=delegado,
        especialidad_revision=especialidad_estructuras,
        numero_rh="RH-2026-03",
        periodo=2026,
        mes=3,
        dictamen_revision="FAVORABLE",
    )

    recibo1 = ReciboHonorarioDelegadoMensual.objects.create(
        delegado=delegado,
        periodo=2026,
        mes=3,
        sub_total=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )

    DetalleHonorarioDelegado.objects.create(
        recibo_mensual=recibo1,
        liquidacion_delegado=ld1,
        imp_bruto=Decimal("1000.00"),
        sub_total=Decimal("1000.00"),
        renta_cip=Decimal("250.00"),
        aporte_codemu=Decimal("50.00"),
        fondo_comun=Decimal("100.00"),
        neto_honorario=Decimal("600.00"),
    )

    rows, total = core_service.list_detalle_honorario_delegado_paginated(
        page=1,
        page_size=20,
        delegado_cip="NONEXISTENT",
    )

    assert total == 0
    assert len(rows) == 0
