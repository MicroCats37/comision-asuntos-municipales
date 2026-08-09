"""
Flujo for Impacto Vial (PorcentajeObra) first revision.

@transaction.atomic coordination of DB record creation.
NO validation, NO business logic — trusts Orchestrator.
"""
from decimal import Decimal
from django.db import transaction
from injector import inject
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_impacto_vial import (
    LiquidacionImpactoVial,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    LiquidacionPorcentajeObraCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.impacto_vial_primera_revision_data import (
    ImpactoVialPrimeraRevisionData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.impacto_vial_primera_revision_result import (
    LiquidacionEspecificaImpactoVialResult,
    ImpactoVialPrimeraRevisionResult,
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
    ProyectoResult,
    EntidadResult,
    UsuarioCreadorResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_porcentaje_result import (
    LiquidacionPorcentajeObraResult,
    DetallePorcentajeObraResult,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion


class LiquidacionImpactoVialFlujo:
    """
    Flujo for Impacto Vial primera revisión.

    Order of DB operations:
    1. Entidad (upsert)
    2. Proyecto
    3. LiquidacionGeneral (sub_total=0, total=0 initially)
    4. LiquidacionPorcentajeObra (with detalles) — via Core
    5. LiquidacionImpactoVial (identity wrapper)

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
        data: ImpactoVialPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
    ) -> ImpactoVialPrimeraRevisionResult:
        return self._ejecutar_primera_revision_sync(usuario_id, data, igv_porcentaje, derecho, uit_valor)

    @transaction.atomic()
    def _ejecutar_primera_revision_sync(
        self,
        usuario_id: int,
        data: ImpactoVialPrimeraRevisionData,
        igv_porcentaje: Decimal,
        derecho,
        uit_valor: Decimal,
    ) -> ImpactoVialPrimeraRevisionResult:
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
        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=gen_data.municipalidad_id,
            expediente=gen_data.expediente,
            observacion=gen_data.observacion,
            proyecto=proyecto,
            tipo_liquidacion=TipoLiquidacion.IMPACTO_VIAL,
            numero_revision=1,
        )

        # Get IGV/UIT FKs for snapshot
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        liquidacion_general.igv_id = igv_vigente
        liquidacion_general.uit_id = uit_vigente
        liquidacion_general.usuario_creador_id = usuario_id

        # Paso 4: Calculate PorcentajeObra
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import TarifaPorcentajeObra

        # Reconstruct tarifas from the DTO (for Core)
        tarifas_orm = [
            TarifaPorcentajeObra.objects.get(id=t.tarifa_id)
            for t in po_data.tarifas
        ]

        cotizacion = self.porcentaje_core.calcular_cotizacion_po(
            valor_declarado=po_data.datos.valor_declarado,
            tarifas=tarifas_orm,
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

        # Paso 7: LiquidacionImpactoVial (identity wrapper)
        impacto_vial = LiquidacionImpactoVial.objects.create(
            liquidacion=liquidacion_general
        )

        # Build Result
        return self._build_result(
            liquidacion_general=liquidacion_general,
            impacto_vial=impacto_vial,
            liquidacion_po=liquidacion_po,
            usuario_id=usuario_id,
        )

    def _build_result(
        self,
        liquidacion_general,
        impacto_vial,
        liquidacion_po,
        usuario_id: int,
    ) -> ImpactoVialPrimeraRevisionResult:
        """Maps ORM objects to domain Result."""
        # Refresh to get calculated fields
        liquidacion_general.refresh_from_db()

        # Build EntidadResult
        entidad_result = None
        if hasattr(liquidacion_general, 'proyecto') and liquidacion_general.proyecto:
            proyecto = liquidacion_general.proyecto
            if hasattr(proyecto, 'entidad_razon_social') and proyecto.entidad_razon_social:
                # Fetch entidad for tipo_documento and numero_documento
                entidad_result = EntidadResult(
                    razon_social=proyecto.entidad_razon_social,
                    tipo_documento=getattr(proyecto, 'entidad_tipo_documento', None) or "",
                    numero_documento=getattr(proyecto, 'entidad_numero_documento', None) or "",
                )

        # Build ProyectoResult
        proyecto = liquidacion_general.proyecto
        proyecto_result = ProyectoResult(
            id=str(proyecto.id),
            denominacion=proyecto.denominacion,
            nombre_propietario=proyecto.nombre_propietario,
            direccion=proyecto.direccion,
            distrito_id=str(proyecto.distrito_id),
            entidad=entidad_result,
        )

        return ImpactoVialPrimeraRevisionResult(
            liquidacion_general=LiquidacionGeneralResult(
                id=str(liquidacion_general.id),
                municipalidad_id=str(liquidacion_general.municipalidad_id),
                usuario_creador=UsuarioCreadorResult(id=str(usuario_id)),
                fecha_registro=liquidacion_general.created_at.isoformat(),
                expediente=liquidacion_general.expediente,
                observacion=liquidacion_general.observacion,
                numero_revision=liquidacion_general.numero_revision,
                sub_total=float(liquidacion_general.sub_total),
                total=float(liquidacion_general.total),
                igv_id=str(liquidacion_general.igv_id.id) if liquidacion_general.igv_id else None,
                uit_id=str(liquidacion_general.uit_id.id) if liquidacion_general.uit_id else None,
                proyecto=proyecto_result,
            ),
            liquidacion_especifica=LiquidacionEspecificaImpactoVialResult(
                id=str(impacto_vial.id),
                numero=impacto_vial.numero,
            ),
            liquidacion_tipo=LiquidacionPorcentajeObraResult(
                id=str(liquidacion_po.id),
                liquidacion_general_id=str(liquidacion_po.liquidacion_general_id),
                tipo_tramite=liquidacion_po.tipo_tramite,  # NULL for now
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
                        igv=d.igv,
                        uit=d.uit,
                        total=d.total,
                    )
                    for d in liquidacion_po.detalles.all()
                ],
            ),
        )
