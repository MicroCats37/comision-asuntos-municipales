"""
FinanzasOrchestrator — fachada ligera para controladores.

Solo delega al FinanzasFlujo. Sin lógica de negocio aquí.
"""
import uuid
from decimal import ROUND_HALF_UP, Decimal
from injector import inject
from ninja.errors import HttpError

from modules.finanzas.domain.services.flujos.finanzas_flujo import FinanzasFlujo
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.services.rh_inspector_mensual_flujo import (
    RHInspectorMensualCotizarFlujo,
    RHInspectorMensualCrearFlujo,
)
from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
    RHDelegadoMensualCotizarFlujo,
    RHDelegadoMensualCrearFlujo,
)
from modules.finanzas.domain.schemas import VariablesVigentesResult
from modules.finanzas.domain.schemas import RHInspectorCotizarIn
from modules.finanzas.domain.schemas import RHDelegadoCotizarIn
from modules.finanzas.domain.results.recibo_honorario_result import (
    ReciboHonorarioDelegadoResult,
    ReciboHonorarioInspectorResult,
)
from modules.finanzas.domain.results.rh_inspector_mensual_result import (
    RHInspectorCotizarResult,
    RHInspectorMensualListItemResult,
    RHInspectorMensualDetalleResult,
    RHInspectorMensualTotalesResult,
    InspectorRHMinimalResult,
    RHInspectorVariablesCalculoResult,
    RangoDescuentoResult,
)
from modules.finanzas.domain.results.rh_inspector_candidatos_result import (
    InspectorCandidatosResult,
    InspectorCandidataItemResult,
)
from modules.finanzas.domain.results.rh_delegado_mensual_result import (
    DelegadoRHMinimalResult,
    DelegadoOperacionContextResult,
    RHDelegadoCotizarResult,
    RHDelegadoMensualListItemResult,
    RHDelegadoMensualDetalleResult,
    RHDelegadoMensualTotalesResult,
    RHDelegadoVariablesCalculoResult,
)


class FinanzasOrchestrator:
    """
    Fachada — obtiene variables vigentes desde el FinanzasFlujo.

    Inyecta dependencias vía __init__.
    """

    @inject
    def __init__(
        self,
        flujo: FinanzasFlujo,
        core: FinanzasCoreService,
        rh_mensual_cotizar_flujo: RHInspectorMensualCotizarFlujo | None = None,
        rh_mensual_crear_flujo: RHInspectorMensualCrearFlujo | None = None,
        rh_delegado_mensual_cotizar_flujo: RHDelegadoMensualCotizarFlujo | None = None,
        rh_delegado_mensual_crear_flujo: RHDelegadoMensualCrearFlujo | None = None,
    ):
        self.flujo = flujo
        self.core = core
        self.rh_mensual_cotizar_flujo = rh_mensual_cotizar_flujo
        self.rh_mensual_crear_flujo = rh_mensual_crear_flujo
        self.rh_delegado_mensual_cotizar_flujo = rh_delegado_mensual_cotizar_flujo
        self.rh_delegado_mensual_crear_flujo = rh_delegado_mensual_crear_flujo

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

        # Resolve vigente tasas from DB, scoped by the asignación's tipo de
        # liquidación. Sin tipo no hay tasa per-tipo — se propaga el 400
        # (no se permite fallback a una tasa global).
        operacion = liquidacion_delegado.delegado_operacion
        tipo_liquidacion = operacion.tipo_liquidacion if operacion else None
        tasas = self.core.get_tasa_delegado_vigente(tipo_liquidacion)
        if not tasas:
            raise HttpError(400, "No hay tasas de delegado vigentes")

        calc_result = ReciboHonorarioDelegado._calcular_honorarios(imp_bruto, tasas=tasas)

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
            ReciboHonorarioCalculoResult,
            LiquidacionEspecificaMinimalResult,
        )

        ld = recibo.liquidacion_delegado
        lg = ld.liquidacion

        tipo_liq = lg.tipo_liquidacion

        esp_id, esp_numero = str(lg.id), 0
        for rel_name in ["edificaciones", "habilitaciones_urbanas", "inspecciones_obra", "mecanicas_suelos", "impactos_viales", "taludes_muros"]:
            if hasattr(lg, rel_name):
                esp = getattr(lg, rel_name)
                if esp:
                    esp_id = str(esp.id)
                    esp_numero = getattr(esp, "numero", 0)
                    break

        return ReciboHonorarioDelegadoResult(
            id=str(recibo.id),
            liquidacion_delegado_id=str(ld.id),
            calculo=ReciboHonorarioCalculoResult(
                sub_total=recibo.sub_total,
                imp_bruto=recibo.imp_bruto,
                renta_cip=recibo.renta_cip,
                aporte_codemu=recibo.aporte_codemu,
                fondo_comun=recibo.fondo_comun,
                neto_honorario=recibo.neto_honorario,
                honorario=recibo.honorario,
            ),
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
                proyecto_denominacion=lg.denominacion_de_proyecto or "",
            ),
            liquidacion_especifica=LiquidacionEspecificaMinimalResult(
                id=esp_id,
                numero=esp_numero,
            ),
            delegado=DelegadoMinimal(
                id=str(ld.delegado.id),
                nombre_completo=ld.delegado.perfil_ingeniero.nombre_completo,
                cip=ld.delegado.perfil_ingeniero.cip or "",
                dni=ld.delegado.perfil_ingeniero.dni or "",
            ),
            especialidad=EspecialidadMinimal(
                id=str(ld.especialidad_revision.id),
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

    # ── ReciboHonorarioInspector ────────────────────────────────────────────────

    def crear_recibo_inspector_proceso(
        self,
        liquidacion_inspector_id: uuid.UUID,
        inspecciones_mes: int,
    ) -> ReciboHonorarioInspectorResult:
        """
        Crea un ReciboHonorarioInspector para una LiquidacionInspector.

        Flujo:
        1. Delega al FinanzasFlujo el cálculo y la creación transaccional.
        2. Recarga el recibo con relaciones (select_related).
        3. Construye ReciboHonorarioInspectorResult (con anidados) y lo retorna.

        Args:
            liquidacion_inspector_id: UUID de LiquidacionInspector.
            inspecciones_mes: Inspecciones liquidadas en el mes.

        Returns:
            ReciboHonorarioInspectorResult con todos los campos (homogéneo al listado).

        Raises:
            HttpError(404): LiquidacionInspector no encontrada.
            HttpError(400): Sin visitas programadas, sin escala o sin rango.
        """
        recibo = self.flujo._proceso_crear_recibo_inspector(
            liquidacion_inspector_id=liquidacion_inspector_id,
            inspecciones_mes=inspecciones_mes,
        )

        recibo_full = self.core.get_recibo_inspector_by_id(recibo.id)
        return self._build_recibo_inspector_result(recibo_full)

    def listar_recibos_inspectores_proceso(
        self,
        page: int = 1,
        page_size: int = 10,
        inspector_id: uuid.UUID | None = None,
        liquidacion_id: uuid.UUID | None = None,
    ) -> tuple[list[ReciboHonorarioInspectorResult], int]:
        """
        Lista recibos de honorarios de inspectores con paginación.

        Aplica defaults y llama al Core para obtener QuerySet filtrado + total.

        Args:
            page: Número de página (1-indexed).
            page_size: Elementos por página.
            inspector_id: Filter by liquidacion_inspector.inspector_id.
            liquidacion_id: Filter by liquidacion_general id.

        Returns:
            Tuple (list of ReciboHonorarioInspectorResult, total count).
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        ORM_objects, total = self.core.list_recibos_inspectores_paginated(
            page=page,
            page_size=page_size,
            inspector_id=inspector_id,
            liquidacion_id=liquidacion_id,
        )

        results: list[ReciboHonorarioInspectorResult] = [
            self._build_recibo_inspector_result(r) for r in ORM_objects
        ]
        return results, total

    def _build_recibo_inspector_result(
        self, recibo
    ) -> ReciboHonorarioInspectorResult:
        """
        Build ReciboHonorarioInspectorResult from ORM object.

        Mapea liquidacion_general summary + inspector summary + especialidad + montos.
        La liquidacion_especifica es la LiquidacionInspeccionObra (vía
        liquidacion_general.inspeccion_obra) — no se itera como con delegados.
        """
        from modules.finanzas.domain.results.recibo_honorario_result import (
            LiquidacionGeneralMinimal,
            TipoLiquidacionMinimal,
            InspectorMinimal,
            EspecialidadMinimal,
            ReciboHonorarioInspectorCalculoResult,
            LiquidacionEspecificaMinimalResult,
        )

        li = recibo.liquidacion_inspector
        lg = li.liquidacion.liquidacion_general
        io = lg.inspeccion_obra
        perfil = li.inspector.perfil_ingeniero

        tipo_liq = lg.tipo_liquidacion

        return ReciboHonorarioInspectorResult(
            id=str(recibo.id),
            liquidacion_inspector_id=str(li.id),
            calculo=ReciboHonorarioInspectorCalculoResult(
                inspecciones_programadas=recibo.inspecciones_programadas,
                costo_por_inspeccion=recibo.costo_por_inspeccion,
                inspecciones_mes=recibo.inspecciones_mes,
                monto_bruto=recibo.monto_bruto,
                inspecciones_pagadas=recibo.inspecciones_pagadas,
                saldo_inspecciones=recibo.saldo_inspecciones,
                sub_total=recibo.sub_total,
                tasa_descuento_aplicada=recibo.tasa_descuento_aplicada,
                descuento=recibo.descuento,
                honorarios=recibo.honorarios,
            ),
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
                proyecto_denominacion=lg.denominacion_de_proyecto or "",
            ),
            liquidacion_especifica=LiquidacionEspecificaMinimalResult(
                id=str(io.id),
                numero=io.numero,
            ),
            inspector=InspectorMinimal(
                id=str(li.inspector.id),
                nombre_completo=perfil.nombre_completo,
                cip=perfil.cip or "",
                dni=perfil.dni or "",
            ),
            especialidad=EspecialidadMinimal(
                id=str(li.especialidad_revision.id),
                nombre=li.especialidad_revision.nombre,
            ),
        )

    # ── RH Inspector Mensual ─────────────────────────────────────────────────────

    def cotizar_rh_inspector_mensual_proceso(
        self, payload: RHInspectorCotizarIn
    ) -> RHInspectorCotizarResult:
        """
        Cotiza el RH mensual del inspector (sin persistir).

        Delega al RHInspectorMensualCotizarFlujo.

        Args:
            payload: Datos de cotización con CIP, periodo e items.

        Returns:
            RHInspectorCotizarResult con el detalle de cálculos.
        """
        resultado = self.rh_mensual_cotizar_flujo.cotizar(payload)
        return resultado

    def crear_rh_inspector_mensual_proceso(
        self, payload: RHInspectorCotizarIn
    ) -> RHInspectorCotizarResult:
        """
        Crea el RH mensual del inspector (persiste maestra + detalles + registro pago).

        Delega al RHInspectorMensualCrearFlujo.

        Args:
            payload: Datos de cotización con CIP, periodo e items.

        Returns:
            RHInspectorCotizarResult con los datos persistidos.
        """
        resultado = self.rh_mensual_crear_flujo.crear(payload)
        return resultado

    def list_candidatos_inspector_proceso(
        self,
        cip: str,
        periodo: str | None = None,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ) -> InspectorCandidatosResult:
        """
        Lista las IOs candidatas (con saldo disponible) para el RH mensual del inspector.

        Args:
            cip: CIP del inspector.
            periodo: Optional periodo en formato YYYY-MM.
                Si se proporciona, calcula inspecciones pagadas acumuladas de todos
                los periodos STRICTLY anteriores a este. Si es None, suma todos
                los periodos históricamente.
            fecha_inicio: Optional filter — fecha_registro >= fecha_inicio (inclusive).
            fecha_fin: Optional filter — fecha_registro <= fecha_fin (inclusive).

        Returns:
            InspectorCandidatosResult con la lista de candidatas.

        Raises:
            HttpError(404): Inspector con CIP no encontrado.
        """
        inspector = self.core.get_inspector_by_cip(cip)
        if not inspector:
            raise HttpError(404, f"Inspector con CIP '{cip}' no encontrado")

        candidatos_data = self.core.list_liquidaciones_inspector_candidatas(
            inspector_id=int(inspector.id),
            periodo=periodo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )

        perfil = inspector.perfil_ingeniero
        candidatos = [
            InspectorCandidataItemResult(**data) for data in candidatos_data
        ]

        return InspectorCandidatosResult(
            inspector_id=str(inspector.id),
            inspector_nombre=perfil.nombre_completo if perfil else "",
            inspector_cip=perfil.cip if perfil else "",
            inspector_dni=perfil.dni if perfil else "",
            periodo=periodo or "",
            candidatos=candidatos,
            total=len(candidatos),
        )

    # ── RH Delegado Mensual ─────────────────────────────────────────────────────

    def cotizar_rh_delegado_mensual_proceso(
        self, payload: RHDelegadoCotizarIn
    ) -> RHDelegadoCotizarResult:
        """
        Cotiza el RH mensual del delegado (sin persistir).

        Delega al RHDelegadoMensualCotizarFlujo.

        Args:
            payload: Datos de cotización con CIP, periodo e items.

        Returns:
            RHDelegadoCotizarResult con el detalle de cálculos.
        """
        resultado = self.rh_delegado_mensual_cotizar_flujo.cotizar(payload)
        return resultado

    def crear_rh_delegado_mensual_proceso(
        self, payload: RHDelegadoCotizarIn
    ) -> RHDelegadoCotizarResult:
        """
        Crea el RH mensual del delegado (persiste maestra + detalles).

        Delega al RHDelegadoMensualCrearFlujo.

        Args:
            payload: Datos de cotización con CIP, periodo e items.

        Returns:
            RHDelegadoCotizarResult con los datos persistidos.
        """
        resultado = self.rh_delegado_mensual_crear_flujo.crear(payload)
        return resultado

    def listar_rh_mensual_delegados_proceso(
        self,
        page: int = 1,
        page_size: int = 10,
        delegado_id: uuid.UUID | None = None,
    ) -> tuple[list[RHDelegadoMensualListItemResult], int]:
        """
        Lista RecibosHonorariosDelegadoMensuales con paginación.

        Args:
            page: Número de página (1-indexed).
            page_size: Elementos por página.
            delegado_id: Filter by delegado_id.

        Returns:
            Tuple (list of RHDelegadoMensualListItemResult, total count).
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        ORM_objects, total = self.core.list_rh_mensuales_delegados_paginated(
            page=page,
            page_size=page_size,
            delegado_id=int(delegado_id) if delegado_id is not None else None,
        )

        results: list[RHDelegadoMensualListItemResult] = [
            self._build_rh_mensual_delegado_result(r) for r in ORM_objects
        ]
        return results, total

    def _build_rh_mensual_delegado_result(
        self, recibo_mensual
    ) -> RHDelegadoMensualListItemResult:
        """
        Build RHDelegadoMensualListItemResult from ORM object.

        Maps: id, periodo, fecha_registro, delegado, totales, detalles.
        Los detalles incluyen todos los campos por fila (liquidacion_delegado_id,
        expediente, imp_bruto, partials, fechas, numeros) para que el frontend
        pueda reconstruir la misma tabla que muestra cotizar.

        Los parciales por item (renta_cip, aporte_codemu, fondo_comun,
        neto_honorario) se recalculan desde imp_bruto usando las tasas vigentes
        de TasaDelegado, igual que en el flujo cotizar.
        """
        from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
            _resolve_liquidacion_especifica_numero,
            _resolve_comprobante_activo,
        )

        delegado_perfil = recibo_mensual.delegado.perfil_ingeniero

        # Obtener tasas vigentes para calcular parciales por item, scoped por el
        # tipo de liquidación de la operatividad. Si no hay tipo asignado no se
        # recalcula (se conservan los valores almacenados/cero) — no crashea.
        operacion = recibo_mensual.delegado_operacion
        tipo_liquidacion = operacion.tipo_liquidacion if operacion else None
        tasas = None
        if tipo_liquidacion is not None:
            tasas = self.core.get_tasa_delegado_vigente(tipo_liquidacion)

        detalles: list[RHDelegadoMensualDetalleResult] = []
        for d in recibo_mensual.detalles.all():
            ld = d.liquidacion_delegado
            lg = ld.liquidacion
            expediente = getattr(lg, "expediente", "") or ""

            # Calcular parciales por item usando tasas vigentes
            imp_bruto_dec = Decimal(str(d.imp_bruto))
            if tasas:
                TWO_PLACES = Decimal("0.01")
                item_renta_cip = (imp_bruto_dec * tasas.renta_cip).quantize(
                    TWO_PLACES, rounding=ROUND_HALF_UP
                )
                item_aporte_codemu = (imp_bruto_dec * tasas.aporte_codemu).quantize(
                    TWO_PLACES, rounding=ROUND_HALF_UP
                )
                item_fondo_comun = (imp_bruto_dec * tasas.fondo_comun).quantize(
                    TWO_PLACES, rounding=ROUND_HALF_UP
                )
                item_neto = (
                    imp_bruto_dec - item_renta_cip - item_aporte_codemu - item_fondo_comun
                ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            else:
                # Sin tasas vigentes — cero todos los campos
                item_renta_cip = Decimal("0")
                item_aporte_codemu = Decimal("0")
                item_fondo_comun = Decimal("0")
                item_neto = Decimal("0")

            detalles.append(
                RHDelegadoMensualDetalleResult(
                    liquidacion_delegado_id=str(ld.id),
                    expediente=expediente,
                    fecha_revision=str(ld.fecha_revision.isoformat()) if ld.fecha_revision else None,
                    numero_revision=lg.numero_revision if hasattr(lg, "numero_revision") else None,
                    total_liquidacion=lg.total,
                    sub_total_liquidacion=lg.sub_total,
                    numero_rh=ld.numero_rh or None,
                    imp_bruto=d.imp_bruto,
                    renta_cip=item_renta_cip,
                    aporte_codemu=item_aporte_codemu,
                    fondo_comun=item_fondo_comun,
                    neto_honorario=item_neto,
                    periodo=ld.periodo,
                    mes=ld.mes,
                    dictamen_revision=ld.dictamen_revision or None,
                    fecha_presentacion=str(ld.fecha_presentacion.isoformat()) if ld.fecha_presentacion else None,
                    delegado_operacion_id=str(ld.delegado_operacion_id) if ld.delegado_operacion_id else None,
                    liquidacion_especifica_numero=_resolve_liquidacion_especifica_numero(lg),
                    comprobante_activo=_resolve_comprobante_activo(lg),
                )
            )

        # Build operatividad context if DelegadoOperacion is set on the receipt
        operatividad_context = None
        if recibo_mensual.delegado_operacion_id:
            op = recibo_mensual.delegado_operacion
            if op:
                operatividad_context = DelegadoOperacionContextResult(
                    id=str(op.id),
                    municipalidad_id=str(op.municipalidad_id),
                    municipalidad_nombre=op.municipalidad.nombre if op.municipalidad else "",
                    tipo_liquidacion_id=str(op.tipo_liquidacion_id) if op.tipo_liquidacion_id else None,
                    tipo_liquidacion_codigo=(
                        op.tipo_liquidacion.codigo
                        if op.tipo_liquidacion
                        else None
                    ),
                    tipo_liquidacion_nombre=(
                        op.tipo_liquidacion.nombre
                        if op.tipo_liquidacion
                        else None
                    ),
                    especialidad_id=str(op.especialidad_revision_id),
                    especialidad_nombre=(
                        op.especialidad_revision.nombre
                        if op.especialidad_revision
                        else ""
                    ),
                    tipo=op.tipo or "",
                )

        return RHDelegadoMensualListItemResult(
            id=str(recibo_mensual.id),
            periodo=recibo_mensual.periodo,
            fecha_registro=recibo_mensual.fecha_registro.isoformat() if recibo_mensual.fecha_registro else "",
            delegado=DelegadoRHMinimalResult(
                id=str(recibo_mensual.delegado.id),
                nombre_completo=delegado_perfil.nombre_completo,
                cip=delegado_perfil.cip or "",
                dni=delegado_perfil.dni or "",
            ),
            totales=RHDelegadoMensualTotalesResult(
                sub_total=recibo_mensual.sub_total,
                renta_cip=recibo_mensual.renta_cip,
                aporte_codemu=recibo_mensual.aporte_codemu,
                fondo_comun=recibo_mensual.fondo_comun,
                neto_honorario=recibo_mensual.neto_honorario,
            ),
            detalles=detalles,
            variables_calculo=RHDelegadoVariablesCalculoResult(
                tasa_renta_cip=tasas.renta_cip if tasas else Decimal("0.25"),
                tasa_aporte_codemu=tasas.aporte_codemu if tasas else Decimal("0.05"),
                tasa_fondo_comun=tasas.fondo_comun if tasas else Decimal("0.10"),
            ),
            delegado_operacion_id=(
                str(recibo_mensual.delegado_operacion_id)
                if recibo_mensual.delegado_operacion_id
                else None
            ),
            delegado_operacion_context=operatividad_context,
        )

    # ── RH Inspector Mensual — Listado ───────────────────────────────────────────

    def listar_rh_mensual_inspectores_proceso(
        self,
        page: int = 1,
        page_size: int = 10,
        inspector_id: uuid.UUID | None = None,
    ) -> tuple[list[RHInspectorMensualListItemResult], int]:
        """
        Lista RecibosHonorariosInspectorMensuales con paginación.

        Args:
            page: Número de página (1-indexed).
            page_size: Elementos por página.
            inspector_id: Filter by inspector_id.

        Returns:
            Tuple (list of RHInspectorMensualListItemResult, total count).
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        ORM_objects, total = self.core.list_rh_mensuales_inspectores_paginated(
            page=page,
            page_size=page_size,
            inspector_id=int(inspector_id) if inspector_id is not None else None,
        )

        results: list[RHInspectorMensualListItemResult] = [
            self._build_rh_mensual_inspector_result(r) for r in ORM_objects
        ]
        return results, total

    def _build_rh_mensual_inspector_result(
        self, recibo_mensual
    ) -> RHInspectorMensualListItemResult:
        """
        Build RHInspectorMensualListItemResult from ORM object.

        Maps: id, periodo, fecha_registro, inspector, totales, detalles, variables_calculo.
        Los detalles incluyen expediente, nombre_propietario, importe_bruto,
        inspecciones_programadas, inspecciones_liquidadas, inspecciones_pagadas_hasta_mes_anterior,
        costo_por_inspeccion, monto_contribuido, saldo_restante.
        """
        from modules.finanzas.domain.results.rh_inspector_mensual_result import (
            InspectorRHMinimalResult,
            RHInspectorMensualTotalesResult,
            RHInspectorMensualDetalleResult,
            RHInspectorVariablesCalculoResult,
            RangoDescuentoResult,
        )
        from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
            _resolve_liquidacion_especifica_numero,
            _resolve_comprobante_activo,
        )

        inspector_perfil = recibo_mensual.inspector.perfil_ingeniero

        # Calcular tasa de descuento aplicada: tasa = 1 - (honorarios / sub_total)
        # Ya que: honorarios = sub_total * (1 - tasa) → tasa = 1 - (honorarios / sub_total)
        sub_total_val = Decimal(str(recibo_mensual.sub_total)) if recibo_mensual.sub_total else Decimal("0")
        honorarios_val = Decimal(str(recibo_mensual.honorarios)) if recibo_mensual.honorarios else Decimal("0")
        if sub_total_val and sub_total_val != 0:
            tasa_descuento = (Decimal("1") - (honorarios_val / sub_total_val)).quantize(Decimal("0.0001"))
        else:
            tasa_descuento = Decimal("0")

        detalles: list[RHInspectorMensualDetalleResult] = []
        total_inspecciones_programadas = 0
        total_inspecciones_liquidadas = 0
        total_inspecciones_pagadas_anterior = 0
        total_saldo_restante = 0

        for d in recibo_mensual.detalles.all():
            lcv = d.liquidacion_por_categoria_visitas
            lg = lcv.liquidacion_general

            # Pre-compute active comprobantes from prefetched queryset (avoids extra DB query)
            lg.comprobantes_activos = [
                c for c in lg.comprobantes.all() if c.activo
            ]

            # Obtener inspecciones pagadas hasta el periodo anterior al actual
            # periodo del recibo actual: YYYY-MM, queremos todas las pago anteriores a este periodo
            # Actually for the list item, we need the cumulative paid before this RH's period
            # For simplicity we compute from RegistroPagoInspector for this LCV before current periodo
            from modules.finanzas.domain.models.registro_pago_inspector import (
                RegistroPagoInspector,
            )
            registros_previos = RegistroPagoInspector.objects.filter(
                liquidacion_por_categoria_visitas=lcv,
                periodo__lt=recibo_mensual.periodo,
            )
            inspecciones_pagadas_hasta_mes_anterior = sum(
                r.inspecciones_pagadas for r in registros_previos
            )

            inspecciones_programadas = lcv.cantidad_visitas or 0
            saldo_restante = inspecciones_programadas - inspecciones_pagadas_hasta_mes_anterior - d.inspecciones_liquidadas

            total_inspecciones_programadas += inspecciones_programadas
            total_inspecciones_liquidadas += d.inspecciones_liquidadas
            total_inspecciones_pagadas_anterior += inspecciones_pagadas_hasta_mes_anterior
            total_saldo_restante += saldo_restante

            nombre_propietario = ""
            if lg.proyecto:
                nombre_propietario = lg.proyecto.nombre_propietario or ""

            expediente = lg.expediente or ""

            distrito = None
            if lg.proyecto and lg.proyecto.distrito:
                distrito = lg.proyecto.distrito.nombre or None

            detalles.append(
                RHInspectorMensualDetalleResult(
                    expediente=expediente,
                    nombre_propietario=nombre_propietario,
                    distrito=distrito,
                    importe_bruto=lg.sub_total if lg.sub_total else Decimal("0"),
                    inspecciones_programadas=inspecciones_programadas,
                    inspecciones_liquidadas=d.inspecciones_liquidadas,
                    inspecciones_pagadas_hasta_mes_anterior=inspecciones_pagadas_hasta_mes_anterior,
                    costo_por_inspeccion=d.costo_por_inspeccion,
                    monto_contribuido=d.monto_contribuido,
                    saldo_restante=saldo_restante,
                    liquidacion_especifica_numero=_resolve_liquidacion_especifica_numero(lg),
                    comprobante_activo=_resolve_comprobante_activo(lg),
                )
            )

        # Build variables_calculo from escala_descuento relationship.
        # rango_aplicado is found by matching tasa_descuento against rango.porcentaje_descuento.
        escala = recibo_mensual.escala_descuento
        rangos_qs = escala.rangos.all()
        rango_aplicado = None
        for r in rangos_qs:
            if r.porcentaje_descuento == tasa_descuento:
                rango_aplicado = RangoDescuentoResult(
                    monto_minimo=r.monto_minimo,
                    monto_maximo=r.monto_maximo,
                    porcentaje_descuento=r.porcentaje_descuento,
                )
                break
        if rango_aplicado is None:
            # Fallback: use first rango if no exact match (should not happen with correct data)
            first = rangos_qs.first()
            rango_aplicado = RangoDescuentoResult(
                monto_minimo=first.monto_minimo if first else Decimal("0"),
                monto_maximo=first.monto_maximo if first else None,
                porcentaje_descuento=tasa_descuento,
            )
        rangos_result = [
            RangoDescuentoResult(
                monto_minimo=r.monto_minimo,
                monto_maximo=r.monto_maximo,
                porcentaje_descuento=r.porcentaje_descuento,
            )
            for r in rangos_qs
        ]
        variables_calculo = RHInspectorVariablesCalculoResult(
            escala_id=str(escala.id),
            escala_nombre=escala.nombre or "",
            rango_aplicado=rango_aplicado,
            rangos=rangos_result,
        )

        return RHInspectorMensualListItemResult(
            id=str(recibo_mensual.id),
            periodo=recibo_mensual.periodo,
            fecha_registro=recibo_mensual.fecha_registro.isoformat() if recibo_mensual.fecha_registro else "",
            inspector=InspectorRHMinimalResult(
                id=str(recibo_mensual.inspector.id),
                nombre_completo=inspector_perfil.nombre_completo,
                cip=inspector_perfil.cip or "",
                dni=inspector_perfil.dni or "",
            ),
            totales=RHInspectorMensualTotalesResult(
                inspecciones_programadas=total_inspecciones_programadas,
                inspecciones_liquidadas=total_inspecciones_liquidadas,
                inspecciones_pagadas_hasta_mes_anterior=total_inspecciones_pagadas_anterior,
                saldo_restante=total_saldo_restante,
                sub_total=recibo_mensual.sub_total,
                descuento=recibo_mensual.descuento,
                honorarios=recibo_mensual.honorarios,
                tasa_descuento_aplicada=tasa_descuento,
            ),
            detalles=detalles,
            variables_calculo=variables_calculo,
        )

