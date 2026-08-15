"""
FinanzasOrchestrator — fachada ligera para controladores.

Solo delega al FinanzasFlujo. Sin lógica de negocio aquí.
"""
import uuid
from injector import inject
from ninja.errors import HttpError

from modules.finanzas.domain.services.flujos.finanzas_flujo import FinanzasFlujo
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.schemas import VariablesVigentesResult
from modules.finanzas.domain.results.recibo_honorario_result import (
    ReciboHonorarioDelegadoResult,
)


class FinanzasOrchestrator:
    """
    Fachada — obtiene variables vigentes desde el FinanzasFlujo.

    Inyecta dependencias vía __init__.
    """

    @inject
    def __init__(self, flujo: FinanzasFlujo, core: FinanzasCoreService):
        self.flujo = flujo
        self.core = core

    def obtener_variables_vigentes(self) -> VariablesVigentesResult:
        """
        Obtiene las variables financieras vigentes (IGV y UIT).

        Delega al FinanzasFlujo.

        Returns:
            VariablesVigentesResult con los valores vigentes
        """
        result = self.flujo._proceso_obtener_variables_vigentes()
        return result

    def crear_recibo_proceso(
        self, liquidacion_delegado_id: uuid.UUID
    ) -> ReciboHonorarioDelegadoResult:
        """
        Crea o actualiza un ReciboHonorarioDelegado para una LiquidacionDelegado.

        Flujo:
        1. Busca LiquidacionDelegado → raise 404 si no existe.
        2. Resuelve imp_bruto según tipo_liquidacion:
           - PORCENTAJE (EDIFICACION/IMPACTO_VIAL/TALUDES): subtotal del
             LiquidacionPorcentajeObraDetalle que coincide con la especialidad.
           - M2/VISITAS (HU/MS/IO): liquidacion.sub_total.
        3. Si no hay imp_bruto resuelto → raise HttpError(400).
        4. Snapshot sub_total de LiquidacionGeneral.
        5. Calcula honorarios con _calcular_honorarios.
        6. Delega al Flujo para crear/actualizar el recibo.
        7. Construye ReciboHonorarioDelegadoResult (con anidados) y lo retorna.

        Args:
            liquidacion_delegado_id: UUID de LiquidacionDelegado.

        Returns:
            ReciboHonorarioDelegadoResult con todos los campos (homogéneo al listado).

        Raises:
            HttpError(404): LiquidacionDelegado no encontrada.
            HttpError(400): No se pudo resolver imp_bruto.
        """
        liquidacion_delegado = self._get_liquidacion_delegado(liquidacion_delegado_id)

        if not liquidacion_delegado:
            raise HttpError(
                404,
                f"LiquidacionDelegado '{liquidacion_delegado_id}' no encontrada",
            )

        imp_bruto, sub_total = self._resolve_imp_bruto(liquidacion_delegado)

        if imp_bruto is None:
            tipo = liquidacion_delegado.liquidacion.tipo_liquidacion.codigo
            if tipo in {"EDIFICACION", "IMPACTO_VIAL", "TALUDES"}:
                raise HttpError(
                    400,
                    "No se encontró LiquidacionPorcentajeObraDetalle para la "
                    "especialidad de esta asignación",
                )
            else:
                raise HttpError(
                    400,
                    "No se encontró imp_bruto para esta asignación",
                )

        from modules.finanzas.domain.models.recibo_honorario import (
            ReciboHonorarioDelegado,
        )
        calc_result = ReciboHonorarioDelegado._calcular_honorarios(imp_bruto)

        recibo = self.flujo._proceso_crear_recibo(
            liquidacion_delegado_id=int(liquidacion_delegado_id),
            sub_total=sub_total,
            imp_bruto=calc_result.imp_bruto,
            renta_cip=calc_result.renta_cip,
            aporte_codemu=calc_result.aporte_codemu,
            fondo_comun=calc_result.fondo_comun,
            neto_honorario=calc_result.neto_honorario,
            honorario=calc_result.honorario,
        )

        recibo_full = self.core.get_recibo_by_id(recibo.id)
        return self._build_recibo_result(recibo_full)

    def listar_recibos_proceso(
        self,
        page: int = 1,
        page_size: int = 10,
        delegado_id: uuid.UUID | None = None,
        liquidacion_id: uuid.UUID | None = None,
    ) -> tuple[list[ReciboHonorarioDelegadoResult], int]:
        """
        Lista recibos de honorarios con paginación.

        Aplica defaults y llama al Core para obtener QuerySet filtrado + total.

        Args:
            page: Número de página (1-indexed).
            page_size: Elementos por página.
            delegado_id: Filter by liquidacion_delegado.delegado_id.
            liquidacion_id: Filter by liquidacion_delegado.liquidacion_id.

        Returns:
            Tuple (list of ReciboHonorarioDelegadoResult, total count).
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        ORM_objects, total = self._list_recibos_orm(
            page=page, page_size=page_size, delegado_id=delegado_id, liquidacion_id=liquidacion_id
        )

        results: list[ReciboHonorarioDelegadoResult] = [
            self._build_recibo_result(r) for r in ORM_objects
        ]
        return results, total

    def _list_recibos_orm(
        self,
        page: int,
        page_size: int,
        delegado_id: uuid.UUID | None,
        liquidacion_id: uuid.UUID | None,
    ):
        """
        Fetch paginated ReciboHonorarioDelegado ORM objects with select_related.

        Returns (ORM_objects, total_count).
        """
        return self.core.list_recibos_paginated(
            page=page,
            page_size=page_size,
            delegado_id=int(delegado_id) if delegado_id is not None else None,
            liquidacion_id=int(liquidacion_id) if liquidacion_id is not None else None,
        )

    def _build_recibo_result(self, recibo) -> ReciboHonorarioDelegadoResult:
        """
        Build ReciboHonorarioDelegadoResult from ORM object.

        Maps nested liquidacion_general summary + delegado summary + especialidad + montos.
        """
        from modules.finanzas.domain.results.recibo_honorario_result import (
            LiquidacionGeneralMinimal,
            TipoLiquidacionMinimal,
            DelegadoMinimal,
            EspecialidadMinimal,
        )

        ld = recibo.liquidacion_delegado
        lg = ld.liquidacion

        tipo_liq = lg.tipo_liquidacion

        return ReciboHonorarioDelegadoResult(
            id=str(recibo.id),
            liquidacion_delegado_id=str(ld.id),
            sub_total=recibo.sub_total,
            imp_bruto=recibo.imp_bruto,
            renta_cip=recibo.renta_cip,
            aporte_codemu=recibo.aporte_codemu,
            fondo_comun=recibo.fondo_comun,
            neto_honorario=recibo.neto_honorario,
            honorario=recibo.honorario,
            created_at=recibo.created_at,
            liquidacion_general=LiquidacionGeneralMinimal(
                id=str(lg.id),
                expediente=lg.expediente or "",
                numero_revision=lg.numero_revision,
                sub_total=lg.sub_total,
                total=lg.total,
                fecha_registro=lg.fecha_registro.isoformat() if lg.fecha_registro else "",
                tipo_liquidacion=TipoLiquidacionMinimal(
                    codigo=tipo_liq.codigo,
                    nombre=tipo_liq.nombre,
                ),
                municipalidad_nombre=lg.municipalidad.nombre,
                proyecto_denominacion=lg.proyecto.denominacion,
            ),
            delegado=DelegadoMinimal(
                id=str(ld.delegado.id),
                nombre_completo=ld.delegado.perfil_ingeniero.nombre_completo,
                cip=ld.delegado.perfil_ingeniero.cip or "",
                dni=ld.delegado.perfil_ingeniero.dni or "",
            ),
            especialidad=EspecialidadMinimal(
                id=str(ld.especialidad_revision.id),
                codigo=ld.especialidad_revision.codigo,
                nombre=ld.especialidad_revision.nombre,
            ),
        )

    def _get_liquidacion_delegado(self, liquidacion_delegado_id: uuid.UUID):
        """
        Fetch LiquidacionDelegado by UUID pk.
        Uses Django ORM directly (cross-app reference).
        """
        from modules.liquidaciones.domain.models.delegado import LiquidacionDelegado

        return LiquidacionDelegado.objects.filter(
            id=int(liquidacion_delegado_id)
        ).select_related(
            "liquidacion",
            "liquidacion__liquidacion_porcentaje_obra",
            "especialidad_revision",
        ).prefetch_related(
            "liquidacion__liquidacion_porcentaje_obra__detalles",
        ).first()

    def _resolve_imp_bruto(self, liquidacion_delegado):
        """
        Resolve imp_bruto based on tipo_liquidacion.

        PORCENTAJE types (EDIFICACION, IMPACTO_VIAL, TALUDES):
            imp_bruto = detalle.subtotal from LiquidacionPorcentajeObraDetalle
            matching liquidacion_delegado.especialidad_revision.
            Returns (None, sub_total) if no matching detail.

        M2 / VISIT types (HABILITACION_URBANA, MECANICA_SUELOS, INSPECCION_OBRA):
            imp_bruto = liquidacion.sub_total (user-confirmed source of truth).

        Returns:
            Tuple (imp_bruto: Decimal, sub_total: Decimal) or (None, sub_total).
        """
        from decimal import Decimal
        from modules.liquidaciones.domain.constants import TipoLiquidacion
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
            LiquidacionPorcentajeObraDetalle,
        )

        tipo = liquidacion_delegado.liquidacion.tipo_liquidacion.codigo
        sub_total = Decimal(str(liquidacion_delegado.liquidacion.sub_total))

        if tipo in {
            TipoLiquidacion.EDIFICACION,
            TipoLiquidacion.IMPACTO_VIAL,
            TipoLiquidacion.TALUDES,
        }:
            especialidad_revision_id = liquidacion_delegado.especialidad_revision_id

            try:
                lpo = liquidacion_delegado.liquidacion.liquidacion_porcentaje_obra
            except Exception:
                return None, sub_total

            # Query details directly instead of relying on prefetch
            detalles = LiquidacionPorcentajeObraDetalle.objects.filter(
                liquidacion_porcentaje=lpo,
                especialidad_id=especialidad_revision_id,
            ).first()

            if detalles:
                return Decimal(str(detalles.subtotal)), sub_total

            return None, sub_total

        else:
            return sub_total, sub_total


