"""
Flujo for Taludes (PorcentajeObra) first revision.

@transaction.atomic coordination of DB record creation.
NO validation, NO business logic — trusts Orchestrator.
"""
from datetime import date
from decimal import Decimal
from django.db import transaction
from injector import inject
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_taludes import (
    LiquidacionTaludes,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    LiquidacionPorcentajeObraCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_legacy.liquidacion_legacy_por_visitas_core_service import (
    LiquidacionLegacyPorVisitasCoreService,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.primera_revision_data import (
    LiquidacionEspecificaPrimeraRevisionData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.primera_revision_result import (
    LiquidacionEspecificaResult,
    LiquidacionEspecificaPrimeraRevisionResult,
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_porcentaje_result import (
    LiquidacionPorcentajeObraResult,
    DetallePorcentajeObraResult,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


class LiquidacionTaludesFlujo:
    """
    Flujo for Taludes primera revisión.

    Order of DB operations:
    1. Entidad (upsert)
    2. Proyecto
    3. LiquidacionGeneral (sub_total=0, total=0 initially)
    4. LiquidacionPorcentajeObra (with detalles) — via Core
    5. LiquidacionTaludes (identity wrapper)

    All in @transaction.atomic.
    """

    @inject
    def __init__(
        self,
        porcentaje_core: LiquidacionPorcentajeObraCoreService,
        general_core: LiquidacionGeneralCoreService,
    ):
        self.porcentaje_core = porcentaje_core
        self.general_core = general_core

    def ejecutar_primera_revision(
        self,
        usuario_id: int,
        data: LiquidacionEspecificaPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        return self._ejecutar_primera_revision_sync(usuario_id, data, igv_porcentaje, derecho, uit_valor)

    @transaction.atomic()
    def _ejecutar_primera_revision_sync(
        self,
        usuario_id: int,
        data: LiquidacionEspecificaPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        gen_data = data.liquidacion_general
        po_data = data.liquidacion_especifica

        # Paso 1: Entidad
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )

        # Paso 2: Proyecto
        proyecto_data = {
            "denominacion": gen_data.proyecto.denominacion,
            "nombre_propietario": gen_data.proyecto.nombre_propietario,
            "direccion": gen_data.proyecto.direccion,
            "distrito_id": gen_data.proyecto.distrito_id,
            "entidad_razon_social": gen_data.proyecto.entidad_razon_social,
            "entidad_tipo_documento": gen_data.proyecto.entidad.tipo_documento,
            "entidad_numero_documento": gen_data.proyecto.entidad.numero_documento,
        }
        proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

        # Paso 3: LiquidacionGeneral (with totals=0 initially)
        from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=gen_data.municipalidad_id,
            expediente=gen_data.expediente,
            observacion=gen_data.observacion,
            proyecto=proyecto,
            tipo_liquidacion=TipoLiquidacionModel.objects.get(codigo=TipoLiquidacion.TALUDES),
            numero_revision=1,
        )

        # Get IGV/UIT FKs for snapshot
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        liquidacion_general.igv_id = igv_vigente
        liquidacion_general.uit_id = uit_vigente
        liquidacion_general.usuario_creador_id = usuario_id

        # Paso 4: Calculate PorcentajeObra
        # With tarifa-unica-especialidades: po_data.tarifas already contains
        # TarifaPorcentajeObraAplicada DTOs with explicit especialidad from input.
        # Pass DTOs directly to calcular_cotizacion_po (no ORM reconstruction needed).
        cotizacion = self.porcentaje_core.calcular_cotizacion_po(
            valor_declarado=po_data.datos.valor_declarado,
            tarifas=po_data.tarifas,  # DTOs with explicit especialidad
            igv_porcentaje=igv_porcentaje,
            derecho=derecho,
            uit_valor=uit_valor,
        )

        # Step 5: Set LiquidacionGeneral totals from cotizacion
        liquidacion_general.sub_total = cotizacion.total_subtotal
        liquidacion_general.total = cotizacion.total
        liquidacion_general.save()

        # Paso 6: Create LiquidacionPorcentajeObra + detalles
        liquidacion_po = self.porcentaje_core.create_liquidacion_porcentaje_obra(
            liquidacion_general=liquidacion_general,
            cotizacion=cotizacion,
            derecho=derecho,
        )

        # Paso 7: LiquidacionTaludes (identity wrapper)
        taludes = LiquidacionTaludes.objects.create(
            liquidacion=liquidacion_general
        )

        # Build Result
        return self._build_result(
            liquidacion_general=liquidacion_general,
            taludes=taludes,
            liquidacion_po=liquidacion_po,
            usuario_id=usuario_id,
        )

    def _build_result(
        self,
        liquidacion_general,
        taludes,
        liquidacion_po,
        usuario_id: int,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """Maps ORM objects to domain Result. Delegates common mapping to core."""
        liquidacion_general.refresh_from_db()

        # Core: builds LiquidacionGeneralResult (delegados included from prefetch)
        general_result = self.general_core.build_general_result(
            liquidacion_general=liquidacion_general,
            usuario_id=usuario_id,
        )

        return LiquidacionEspecificaPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_especifica=LiquidacionEspecificaResult(
                id=str(taludes.id),
                numero=taludes.numero,
            ),
            liquidacion_tipo=LiquidacionPorcentajeObraResult(
                id=str(liquidacion_po.id),
                liquidacion_general_id=str(liquidacion_po.liquidacion_general_id),
                tipo_tramite=liquidacion_po.tipo_tramite,
                valor_declarado=liquidacion_po.valor_declarado,
                porcentaje_liquidacion=liquidacion_po.porcentaje_liquidacion,
                derecho_minimo=liquidacion_po.derecho_minimo,
                derecho_maximo=liquidacion_po.derecho_maximo,
                porcentaje_minimo_uit=liquidacion_po.porcentaje_minimo_uit,
                derecho_aplicado_id=str(liquidacion_po.derecho_aplicado_id),
                detalles=[
                    DetallePorcentajeObraResult(
                        id=str(d.id),
                        tarifa_aplicada_id=str(d.tarifa_aplicada_id),
                        especialidad_id=str(d.especialidad_id),
                        porcentaje_aplicado=d.porcentaje_aplicado,
                        subtotal=d.subtotal,
                    )
                    for d in liquidacion_po.detalles.all()
                ],
            ),
        )

    @transaction.atomic()
    def ejecutar_legacy(
        self,
        usuario_id: int,
        data: LiquidacionEspecificaPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
        numero_revision: int,
        fecha_registro: date,
        legacy_visitas_core: LiquidacionLegacyPorVisitasCoreService,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Legacy first revision for Taludes using historical fecha_registro.

        Mirrors _ejecutar_primera_revision_sync but:
        - Uses passed igv_porcentaje/uit_valor for calculation (resolved by orchestrator)
        - Resolves igv/uit ORM objects via legacy_visitas_core for FKs on liquidacion_general
        - Sets explicit fecha_registro after create_liquidacion_general
        - Sets numero_revision from parameter (not hardcoded to 1)
        - Sets usuario_creador_id
        """
        gen_data = data.liquidacion_general
        po_data = data.liquidacion_especifica

        # Paso 1: Entidad
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )

        # Paso 2: Proyecto
        proyecto_data = {
            "denominacion": gen_data.proyecto.denominacion,
            "nombre_propietario": gen_data.proyecto.nombre_propietario,
            "direccion": gen_data.proyecto.direccion,
            "distrito_id": gen_data.proyecto.distrito_id,
            "entidad_razon_social": gen_data.proyecto.entidad_razon_social,
            "entidad_tipo_documento": gen_data.proyecto.entidad.tipo_documento,
            "entidad_numero_documento": gen_data.proyecto.entidad.numero_documento,
        }
        proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

        # Paso 3: LiquidacionGeneral (with totals=0 initially)
        from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=gen_data.municipalidad_id,
            expediente=gen_data.expediente,
            observacion=gen_data.observacion,
            proyecto=proyecto,
            tipo_liquidacion=TipoLiquidacionModel.objects.get(codigo=TipoLiquidacion.TALUDES),
            numero_revision=numero_revision,
        )

        # Set historical fecha_registro (override default=timezone.now from model)
        liquidacion_general.fecha_registro = fecha_registro

        # Resolve IGV/UIT ORM objects for FK snapshot via legacy core
        igv = legacy_visitas_core.get_igv_por_fecha(fecha_registro)
        uit = legacy_visitas_core.get_uit_por_fecha(fecha_registro)
        liquidacion_general.igv_id = igv
        liquidacion_general.uit_id = uit
        liquidacion_general.usuario_creador_id = usuario_id

        # Paso 4: Calculate PorcentajeObra
        cotizacion = self.porcentaje_core.calcular_cotizacion_po(
            valor_declarado=po_data.datos.valor_declarado,
            tarifas=po_data.tarifas,
            igv_porcentaje=igv_porcentaje,
            derecho=derecho,
            uit_valor=uit_valor,
        )

        # Step 5: Set LiquidacionGeneral totals from cotizacion
        liquidacion_general.sub_total = cotizacion.total_subtotal
        liquidacion_general.total = cotizacion.total
        liquidacion_general.save()

        # Paso 6: Create LiquidacionPorcentajeObra + detalles
        liquidacion_po = self.porcentaje_core.create_liquidacion_porcentaje_obra(
            liquidacion_general=liquidacion_general,
            cotizacion=cotizacion,
            derecho=derecho,
        )

        # Paso 7: LiquidacionTaludes (identity wrapper)
        taludes = LiquidacionTaludes.objects.create(
            liquidacion=liquidacion_general
        )

        # Build Result
        return self._build_result(
            liquidacion_general=liquidacion_general,
            taludes=taludes,
            liquidacion_po=liquidacion_po,
            usuario_id=usuario_id,
        )

