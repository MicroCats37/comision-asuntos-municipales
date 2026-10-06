"""
FinanzasOrchestrator — fachada ligera para controladores.

Solo delega. Sin lógica de negocio aquí.
"""
import uuid
from decimal import Decimal
from injector import inject
from ninja.errors import HttpError

from modules.finanzas.domain.services.flujos.finanzas_flujo import FinanzasFlujo
from modules.finanzas.domain.services.finanzas_core_service import FinanzasCoreService
from modules.finanzas.domain.services.flujos.rh_inspector_mensual_flujo import (
    RHInspectorMensualCotizarFlujo,
    RHInspectorMensualCrearFlujo,
    RHInspectorMensualListFlujo,
)
from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
    RHDelegadoMensualCotizarFlujo,
    RHDelegadoMensualCrearFlujo,
    RHDelegadoMensualListFlujo,
)
from modules.finanzas.domain.schemas import VariablesVigentesResult
from modules.finanzas.domain.schemas import RHInspectorCotizarIn
from modules.finanzas.domain.schemas import RHDelegadoCotizarIn
from modules.finanzas.domain.results.rh_inspector_mensual_result import (
    RHInspectorCotizarResult,
)
from modules.finanzas.domain.results.rh_inspector_candidatos_result import (
    InspectorCandidatosResult,
    InspectorCandidatosPaginatedResult,
)
from modules.finanzas.domain.results.rh_delegado_mensual_result import (
    RHDelegadoCotizarResult,
    RHDelegadoMensualListItemResult,
)
from modules.finanzas.domain.results.rh_detalle_delegado_result import (
    DetalleDelegadoRowResult,
    DelegadoLiquidacionResult,
    DelegadoMinimalResult,
    EspecialidadMinimalResult,
    LiquidacionGeneralNestedResult,
    MunicipalidadNestedResult,
    TipoLiquidacionNestedResult,
)
from modules.finanzas.domain.services.helpers.liquidacion_helpers import (
    _resolve_liquidacion_especifica_numero,
)
from modules.finanzas.domain.results.rh_detalle_inspector_result import (
    DetalleInspectorRowResult,
    InspectorLiquidacionResult,
    InspectorMinimalResult,
    LiquidacionInspectorNestedResult,
    MunicipalidadNestedResult as InspectorMunicipalidadNestedResult,
    TipoLiquidacionNestedResult as InspectorTipoLiquidacionNestedResult,
)


class FinanzasOrchestrator:
    """
    Fachada —delega a flujos. Sin lógica de negocio aquí.
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
        rh_delegado_mensual_list_flujo: RHDelegadoMensualListFlujo | None = None,
        rh_inspector_mensual_list_flujo: RHInspectorMensualListFlujo | None = None,
    ):
        self.flujo = flujo
        self.core = core
        self.rh_mensual_cotizar_flujo = rh_mensual_cotizar_flujo
        self.rh_mensual_crear_flujo = rh_mensual_crear_flujo
        self.rh_delegado_mensual_cotizar_flujo = rh_delegado_mensual_cotizar_flujo
        self.rh_delegado_mensual_crear_flujo = rh_delegado_mensual_crear_flujo
        self.rh_delegado_mensual_list_flujo = rh_delegado_mensual_list_flujo
        self.rh_inspector_mensual_list_flujo = rh_inspector_mensual_list_flujo

    def obtener_variables_vigentes(self) -> VariablesVigentesResult:
        """
        Obtiene las variables financieras vigentes (IGV y UIT).

        Delega al FinanzasFlujo.

        Returns:
            VariablesVigentesResult con los valores vigentes.
        """
        return self.flujo._proceso_obtener_variables_vigentes()

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

    def _build_rh_mensual_delegado_result(self, recibo_mensual) -> RHDelegadoMensualListItemResult:
        """
        Wrapper backward-compat para tests que llaman _build_rh_mensual_delegado_result
        directamente en el orchestrator.

        Delega al RHDelegadoMensualListFlujo si está disponible.
        """
        if self.rh_delegado_mensual_list_flujo is not None:
            return self.rh_delegado_mensual_list_flujo._build_rh_mensual_delegado_result(recibo_mensual)
        # Fallback inline
        from modules.finanzas.domain.results.rh_delegado_mensual_result import (
            DelegadoRHMinimalResult,
            DelegadoOperacionContextResult,
            RHDelegadoMensualDetalleResult,
            RHDelegadoMensualTotalesResult,
            RHDelegadoVariablesCalculoResult,
        )
        from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
            _resolve_liquidacion_especifica_numero,
            _resolve_comprobante_activo,
        )
        from decimal import Decimal
        delegado_perfil = recibo_mensual.delegado.perfil_ingeniero
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
            renta_cip = d.renta_cip if d.renta_cip is not None else Decimal("0.00")
            aporte_codemu = d.aporte_codemu if d.aporte_codemu is not None else Decimal("0.00")
            fondo_comun = d.fondo_comun if d.fondo_comun is not None else Decimal("0.00")
            neto_honorario = d.neto_honorario if d.neto_honorario is not None else Decimal("0.00")
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
                    renta_cip=renta_cip,
                    aporte_codemu=aporte_codemu,
                    fondo_comun=fondo_comun,
                    neto_honorario=neto_honorario,
                    periodo=ld.periodo,
                    mes=ld.mes,
                    dictamen_revision=ld.dictamen_revision or None,
                    fecha_presentacion=str(ld.fecha_presentacion.isoformat()) if ld.fecha_presentacion else None,
                    delegado_operacion_id=str(ld.delegado_operacion_id) if ld.delegado_operacion_id else None,
                    liquidacion_especifica_numero=_resolve_liquidacion_especifica_numero(lg),
                    comprobante_activo=_resolve_comprobante_activo(lg),
                )
            )
        operatividad_context = None
        if recibo_mensual.delegado_operacion_id:
            op = recibo_mensual.delegado_operacion
            if op:
                operatividad_context = DelegadoOperacionContextResult(
                    id=str(op.id),
                    municipalidad_id=str(op.municipalidad_id),
                    municipalidad_nombre=op.municipalidad.nombre if op.municipalidad else "",
                    tipo_liquidacion_id=str(op.tipo_liquidacion_id) if op.tipo_liquidacion_id else None,
                    tipo_liquidacion_codigo=op.tipo_liquidacion.codigo if op.tipo_liquidacion else None,
                    tipo_liquidacion_nombre=op.tipo_liquidacion.nombre if op.tipo_liquidacion else None,
                    especialidad_id=str(op.especialidad_revision_id),
                    especialidad_nombre=op.especialidad_revision.nombre if op.especialidad_revision else "",
                    tipo=op.tipo or "",
                )
        periodo_year = recibo_mensual.periodo
        mes = recibo_mensual.mes
        if periodo_year is None or mes is None:
            cs = type(self.core)()
            if periodo_year is None:
                periodo_year = cs._parse_periodo_year(recibo_mensual.periodo)
            if mes is None:
                mes = cs._parse_periodo_mes(recibo_mensual.periodo)
        return RHDelegadoMensualListItemResult(
            id=str(recibo_mensual.id),
            periodo=periodo_year,
            mes=mes,
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
                tasa_delegado_id=tasas.id if tasas else None,
            ),
            delegado_operacion_id=str(recibo_mensual.delegado_operacion_id) if recibo_mensual.delegado_operacion_id else None,
            delegado_operacion_context=operatividad_context,
        )

    def _build_rh_inspector_mensual_result(self, recibo_mensual) -> "RHInspectorMensualListItemResult":
        """
        Wrapper para construir RHInspectorMensualListItemResult desde un ORM object.

        Delega al RHInspectorMensualListFlujo si está disponible.
        """
        from modules.finanzas.domain.results.rh_inspector_mensual_result import (
            RHInspectorMensualListItemResult,
        )
        if self.rh_inspector_mensual_list_flujo is not None:
            return self.rh_inspector_mensual_list_flujo._build_rh_mensual_inspector_result(recibo_mensual)
        # Fallback inline (copiado de RHInspectorMensualListFlujo)
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
        from decimal import Decimal
        inspector_perfil = recibo_mensual.inspector.perfil_ingeniero
        tasa_descuento = Decimal(str(recibo_mensual.tasa_descuento)) if recibo_mensual.tasa_descuento is not None else Decimal("0.0000")
        detalles: list[RHInspectorMensualDetalleResult] = []
        total_inspecciones_programadas = 0
        total_inspecciones_liquidadas = 0
        total_inspecciones_pagadas_anterior = 0
        total_saldo_restante = 0
        for d in recibo_mensual.detalles.select_related(
            "liquidacion_por_categoria_visitas__liquidacion_general__proyecto__distrito"
        ).prefetch_related(
            "liquidacion_por_categoria_visitas__inspectores",
            "liquidacion_por_categoria_visitas__liquidacion_general__comprobantes",
        ):
            lcv = d.liquidacion_por_categoria_visitas
            lg = lcv.liquidacion_general
            lg.comprobantes_activos = [c for c in lg.comprobantes.all() if c.activo]
            importe_bruto = d.importe_bruto if d.importe_bruto is not None else Decimal("0")
            inspecciones_programadas = d.inspecciones_programadas if d.inspecciones_programadas is not None else 0
            inspecciones_pagadas_hasta_mes_anterior = d.inspecciones_pagadas_hasta_mes_anterior if d.inspecciones_pagadas_hasta_mes_anterior is not None else 0
            saldo_restante = int(d.saldo_restante) if d.saldo_restante is not None else 0
            total_inspecciones_programadas += inspecciones_programadas
            total_inspecciones_liquidadas += d.inspecciones_liquidadas
            total_inspecciones_pagadas_anterior += inspecciones_pagadas_hasta_mes_anterior
            total_saldo_restante += saldo_restante
            nombre_propietario = ""
            if lg.proyecto:
                nombre_propietario = lg.proyecto.nombre_propietario or ""
            expediente = lg.expediente or ""
            distrito = lg.proyecto.distrito.nombre if lg.proyecto and lg.proyecto.distrito else None
            liquidacion_inspector = None
            for li in lcv.inspectores.all():
                if str(li.inspector_id) == str(recibo_mensual.inspector_id):
                    liquidacion_inspector = li
                    break
            fecha_revision = None
            fecha_presentacion = None
            dictamen_revision = None
            if liquidacion_inspector:
                if liquidacion_inspector.fecha_revision:
                    fecha_revision = str(liquidacion_inspector.fecha_revision.isoformat())
                if liquidacion_inspector.fecha_presentacion:
                    fecha_presentacion = str(liquidacion_inspector.fecha_presentacion.isoformat())
                dictamen_revision = liquidacion_inspector.dictamen_revision or None
            detalles.append(
                RHInspectorMensualDetalleResult(
                    expediente=expediente,
                    nombre_propietario=nombre_propietario,
                    distrito=distrito,
                    importe_bruto=importe_bruto,
                    inspecciones_programadas=inspecciones_programadas,
                    inspecciones_liquidadas=d.inspecciones_liquidadas,
                    inspecciones_pagadas_hasta_mes_anterior=inspecciones_pagadas_hasta_mes_anterior,
                    costo_por_inspeccion=d.costo_por_inspeccion,
                    monto_contribuido=d.monto_contribuido,
                    saldo_restante=saldo_restante,
                    sub_total=d.sub_total,
                    descuento=d.descuento,
                    honorarios=d.honorarios,
                    liquidacion_especifica_numero=_resolve_liquidacion_especifica_numero(lg),
                    comprobante_activo=_resolve_comprobante_activo(lg),
                    fecha_revision=fecha_revision,
                    fecha_presentacion=fecha_presentacion,
                    dictamen_revision=dictamen_revision,
                )
            )
        escala = recibo_mensual.escala_descuento
        rangos_qs = escala.rangos.all()
        rango_aplicado = None
        for rng in rangos_qs:
            if rng.porcentaje_descuento == tasa_descuento:
                rango_aplicado = RangoDescuentoResult(
                    monto_minimo=rng.monto_minimo,
                    monto_maximo=rng.monto_maximo,
                    porcentaje_descuento=rng.porcentaje_descuento,
                )
                break
        if rango_aplicado is None:
            first = rangos_qs.first()
            rango_aplicado = RangoDescuentoResult(
                monto_minimo=first.monto_minimo if first else Decimal("0"),
                monto_maximo=first.monto_maximo if first else None,
                porcentaje_descuento=tasa_descuento,
            )
        variables_calculo = RHInspectorVariablesCalculoResult(
            escala_id=str(escala.id),
            escala_nombre=escala.nombre or "",
            rango_aplicado=rango_aplicado,
        )
        periodo_year = recibo_mensual.periodo
        mes = recibo_mensual.mes
        if periodo_year is None or mes is None:
            cs = type(self.core)()
            if periodo_year is None:
                periodo_year = cs._parse_periodo_year(recibo_mensual.periodo)
            if mes is None:
                mes = cs._parse_periodo_mes(recibo_mensual.periodo)
        return RHInspectorMensualListItemResult(
            id=str(recibo_mensual.id),
            numero=recibo_mensual.numero,
            periodo=periodo_year,
            mes=mes,
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
        # Fallback inline
        from modules.finanzas.domain.results.rh_delegado_mensual_result import (
            DelegadoRHMinimalResult,
            DelegadoOperacionContextResult,
            RHDelegadoMensualDetalleResult,
            RHDelegadoMensualTotalesResult,
            RHDelegadoVariablesCalculoResult,
        )
        from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
            _resolve_liquidacion_especifica_numero,
            _resolve_comprobante_activo,
        )
        delegado_perfil = recibo_mensual.delegado.perfil_ingeniero
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
            renta_cip = d.renta_cip if d.renta_cip is not None else Decimal("0.00")
            aporte_codemu = d.aporte_codemu if d.aporte_codemu is not None else Decimal("0.00")
            fondo_comun = d.fondo_comun if d.fondo_comun is not None else Decimal("0.00")
            neto_honorario = d.neto_honorario if d.neto_honorario is not None else Decimal("0.00")
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
                    renta_cip=renta_cip,
                    aporte_codemu=aporte_codemu,
                    fondo_comun=fondo_comun,
                    neto_honorario=neto_honorario,
                    periodo=ld.periodo,
                    mes=ld.mes,
                    dictamen_revision=ld.dictamen_revision or None,
                    fecha_presentacion=str(ld.fecha_presentacion.isoformat()) if ld.fecha_presentacion else None,
                    delegado_operacion_id=str(ld.delegado_operacion_id) if ld.delegado_operacion_id else None,
                    liquidacion_especifica_numero=_resolve_liquidacion_especifica_numero(lg),
                    comprobante_activo=_resolve_comprobante_activo(lg),
                )
            )
        operatividad_context = None
        if recibo_mensual.delegado_operacion_id:
            op = recibo_mensual.delegado_operacion
            if op:
                operatividad_context = DelegadoOperacionContextResult(
                    id=str(op.id),
                    municipalidad_id=str(op.municipalidad_id),
                    municipalidad_nombre=op.municipalidad.nombre if op.municipalidad else "",
                    tipo_liquidacion_id=str(op.tipo_liquidacion_id) if op.tipo_liquidacion_id else None,
                    tipo_liquidacion_codigo=op.tipo_liquidacion.codigo if op.tipo_liquidacion else None,
                    tipo_liquidacion_nombre=op.tipo_liquidacion.nombre if op.tipo_liquidacion else None,
                    especialidad_id=str(op.especialidad_revision_id),
                    especialidad_nombre=op.especialidad_revision.nombre if op.especialidad_revision else "",
                    tipo=op.tipo or "",
                )
        periodo_year = recibo_mensual.periodo
        mes = recibo_mensual.mes
        if periodo_year is None or mes is None:
            cs = type(self.core)()
            if periodo_year is None:
                periodo_year = cs._parse_periodo_year(recibo_mensual.periodo)
            if mes is None:
                mes = cs._parse_periodo_mes(recibo_mensual.periodo)
        return RHDelegadoMensualListItemResult(
            id=str(recibo_mensual.id),
            periodo=periodo_year,
            mes=mes,
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
                tasa_delegado_id=tasas.id if tasas else None,
            ),
            delegado_operacion_id=str(recibo_mensual.delegado_operacion_id) if recibo_mensual.delegado_operacion_id else None,
            delegado_operacion_context=operatividad_context,
        )

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
        delegado_cip: str | None = None,
        municipalidad_id: uuid.UUID | None = None,
        periodo: int | None = None,
        mes: int | None = None,
    ) -> tuple[list[RHDelegadoMensualListItemResult], int]:
        """
        Lista RecibosHonorariosDelegadoMensuales con paginación.

        Filtros:
        - delegado_cip: CIP del ingeniero delegado (delegado__perfil_ingeniero__cip)
        - municipalidad_id: UUID de la municipalidad (delegado_operacion__municipalidad_id)
        - periodo: Año del periodo (e.g. 2026)
        - mes: Mes (1-12)

        Delega al RHDelegadoMensualListFlujo si está disponible;
        fallback a implementación local para backward-compatibilidad con tests.
        """
        if self.rh_delegado_mensual_list_flujo is not None:
            return self.rh_delegado_mensual_list_flujo.listar_rh_mensuales_delegados_proceso(
                page=page,
                page_size=page_size,
                delegado_cip=delegado_cip,
                municipalidad_id=municipalidad_id,
                periodo=periodo,
                mes=mes,
            )
        # Fallback inline para tests que instancian sin DI
        from modules.finanzas.domain.results.rh_delegado_mensual_result import (
            DelegadoRHMinimalResult,
            DelegadoOperacionContextResult,
            RHDelegadoMensualDetalleResult,
            RHDelegadoMensualTotalesResult,
            RHDelegadoVariablesCalculoResult,
        )
        from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
            _resolve_liquidacion_especifica_numero,
            _resolve_comprobante_activo,
        )
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        ORM_objects, total = self.core.list_rh_mensuales_delegados_paginated(
            page=page,
            page_size=page_size,
            delegado_cip=delegado_cip,
            municipalidad_id=municipalidad_id,
            periodo=periodo,
            mes=mes,
        )
        results: list[RHDelegadoMensualListItemResult] = []
        for r in ORM_objects:
            delegado_perfil = r.delegado.perfil_ingeniero
            operacion = r.delegado_operacion
            tipo_liquidacion = operacion.tipo_liquidacion if operacion else None
            tasas = None
            if tipo_liquidacion is not None:
                tasas = self.core.get_tasa_delegado_vigente(tipo_liquidacion)
            detalles: list[RHDelegadoMensualDetalleResult] = []
            for d in r.detalles.all():
                ld = d.liquidacion_delegado
                lg = ld.liquidacion
                expediente = getattr(lg, "expediente", "") or ""
                renta_cip = d.renta_cip if d.renta_cip is not None else Decimal("0.00")
                aporte_codemu = d.aporte_codemu if d.aporte_codemu is not None else Decimal("0.00")
                fondo_comun = d.fondo_comun if d.fondo_comun is not None else Decimal("0.00")
                neto_honorario = d.neto_honorario if d.neto_honorario is not None else Decimal("0.00")
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
                        renta_cip=renta_cip,
                        aporte_codemu=aporte_codemu,
                        fondo_comun=fondo_comun,
                        neto_honorario=neto_honorario,
                        periodo=ld.periodo,
                        mes=ld.mes,
                        dictamen_revision=ld.dictamen_revision or None,
                        fecha_presentacion=str(ld.fecha_presentacion.isoformat()) if ld.fecha_presentacion else None,
                        delegado_operacion_id=str(ld.delegado_operacion_id) if ld.delegado_operacion_id else None,
                        liquidacion_especifica_numero=_resolve_liquidacion_especifica_numero(lg),
                        comprobante_activo=_resolve_comprobante_activo(lg),
                    )
                )
            operatividad_context = None
            if r.delegado_operacion_id:
                op = r.delegado_operacion
                if op:
                    operatividad_context = DelegadoOperacionContextResult(
                        id=str(op.id),
                        municipalidad_id=str(op.municipalidad_id),
                        municipalidad_nombre=op.municipalidad.nombre if op.municipalidad else "",
                        tipo_liquidacion_id=str(op.tipo_liquidacion_id) if op.tipo_liquidacion_id else None,
                        tipo_liquidacion_codigo=op.tipo_liquidacion.codigo if op.tipo_liquidacion else None,
                        tipo_liquidacion_nombre=op.tipo_liquidacion.nombre if op.tipo_liquidacion else None,
                        especialidad_id=str(op.especialidad_revision_id),
                        especialidad_nombre=op.especialidad_revision.nombre if op.especialidad_revision else "",
                        tipo=op.tipo or "",
                    )
            periodo_year = r.periodo
            mes = r.mes
            if periodo_year is None or mes is None:
                cs = type(self.core)()
                if periodo_year is None:
                    periodo_year = cs._parse_periodo_year(r.periodo)
                if mes is None:
                    mes = cs._parse_periodo_mes(r.periodo)
            results.append(
                RHDelegadoMensualListItemResult(
                    id=str(r.id),
                    periodo=periodo_year,
                    mes=mes,
                    fecha_registro=r.fecha_registro.isoformat() if r.fecha_registro else "",
                    delegado=DelegadoRHMinimalResult(
                        id=str(r.delegado.id),
                        nombre_completo=delegado_perfil.nombre_completo,
                        cip=delegado_perfil.cip or "",
                        dni=delegado_perfil.dni or "",
                    ),
                    totales=RHDelegadoMensualTotalesResult(
                        sub_total=r.sub_total,
                        renta_cip=r.renta_cip,
                        aporte_codemu=r.aporte_codemu,
                        fondo_comun=r.fondo_comun,
                        neto_honorario=r.neto_honorario,
                    ),
                    detalles=detalles,
                    variables_calculo=RHDelegadoVariablesCalculoResult(
                        tasa_renta_cip=tasas.renta_cip if tasas else Decimal("0.25"),
                        tasa_aporte_codemu=tasas.aporte_codemu if tasas else Decimal("0.05"),
                        tasa_fondo_comun=tasas.fondo_comun if tasas else Decimal("0.10"),
                        tasa_delegado_id=tasas.id if tasas else None,
                    ),
                    delegado_operacion_id=str(r.delegado_operacion_id) if r.delegado_operacion_id else None,
                    delegado_operacion_context=operatividad_context,
                )
            )
        return results, total

    def obtener_rh_delegado_detalle_proceso(
        self,
        id: uuid.UUID | None = None,
        delegado_id: uuid.UUID | None = None,
        periodo: int | None = None,
        mes: int | None = None,
    ) -> RHDelegadoMensualListItemResult:
        """
        Obtiene el detalle de un ReciboHonorarioDelegadoMensual por ID o clave compuesta.

        Args:
            id: UUID del recibo (mutuamente excluyente con la clave compuesta).
            delegado_id: UUID del delegado (usado con periodo y mes).
            periodo: Año del periodo (e.g. 2026).
            mes: Mes (1-12).

        Returns:
            RHDelegadoMensualListItemResult con todos los detalles.

        Raises:
            HttpError(400): Se deben proporcionar exactamente id O (delegado_id + periodo + mes).
            HttpError(404): No se encontró el recibo para los criterios dados.
        """
        if id is not None:
            recibo = self.core.get_rh_delegado_mensual_by_id(id)
        elif delegado_id is not None and periodo is not None and mes is not None:
            recibo = self.core.get_rh_delegado_mensual_by_keys(
                delegado_id=int(delegado_id),
                periodo=periodo,
                mes=mes,
            )
        else:
            raise HttpError(
                400,
                "Debe proporcionar 'id' o la tripletas 'delegado_id' + 'periodo' + 'mes'",
            )

        if not recibo:
            raise HttpError(404, "ReciboHonorarioDelegadoMensual no encontrado")

        return self._build_rh_mensual_delegado_result(recibo)

    # ── RH Inspector Mensual — Listado ───────────────────────────────────────────

    def listar_rh_mensual_inspectores_proceso(
        self,
        page: int = 1,
        page_size: int = 10,
        inspector_id: uuid.UUID | None = None,
    ) -> tuple[list, int]:
        """
        Lista RecibosHonorariosInspectorMensuales con paginación.

        Delega al RHInspectorMensualListFlujo si está disponible;
        fallback a implementación local para backward-compatibilidad con tests.
        """
        if self.rh_inspector_mensual_list_flujo is not None:
            return self.rh_inspector_mensual_list_flujo.listar_rh_mensuales_inspectores_proceso(
                page=page,
                page_size=page_size,
                inspector_id=int(inspector_id) if inspector_id is not None else None,
            )
        # Fallback inline para tests que instancian sin DI
        from modules.finanzas.domain.results.rh_inspector_mensual_result import (
            InspectorRHMinimalResult,
            RHInspectorMensualTotalesResult,
            RHInspectorMensualDetalleResult,
            RHInspectorVariablesCalculoResult,
            RangoDescuentoResult,
            RHInspectorMensualListItemResult,
        )
        from modules.finanzas.domain.results.rh_inspector_candidatos_result import (
            InspectorCandidatosResult,
            InspectorCandidataItemResult,
        )
        from modules.finanzas.domain.services.flujos.rh_delegado_mensual_flujo import (
            _resolve_liquidacion_especifica_numero,
            _resolve_comprobante_activo,
        )
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        ORM_objects, total = self.core.list_rh_mensuales_inspectores_paginated(
            page=page,
            page_size=page_size,
            inspector_id=int(inspector_id) if inspector_id is not None else None,
        )
        results: list[RHInspectorMensualListItemResult] = []
        for r in ORM_objects:
            inspector_perfil = r.inspector.perfil_ingeniero
            tasa_descuento = Decimal(str(r.tasa_descuento)) if r.tasa_descuento is not None else Decimal("0.0000")
            detalles: list[RHInspectorMensualDetalleResult] = []
            total_inspecciones_programadas = 0
            total_inspecciones_liquidadas = 0
            total_inspecciones_pagadas_anterior = 0
            total_saldo_restante = 0
            for d in r.detalles.select_related(
                "liquidacion_por_categoria_visitas__liquidacion_general__proyecto__distrito"
            ).prefetch_related(
                "liquidacion_por_categoria_visitas__inspectores",
                "liquidacion_por_categoria_visitas__liquidacion_general__comprobantes",
            ):
                lcv = d.liquidacion_por_categoria_visitas
                lg = lcv.liquidacion_general
                lg.comprobantes_activos = [c for c in lg.comprobantes.all() if c.activo]
                importe_bruto = d.importe_bruto if d.importe_bruto is not None else Decimal("0")
                inspecciones_programadas = d.inspecciones_programadas if d.inspecciones_programadas is not None else 0
                inspecciones_pagadas_hasta_mes_anterior = d.inspecciones_pagadas_hasta_mes_anterior if d.inspecciones_pagadas_hasta_mes_anterior is not None else 0
                saldo_restante = int(d.saldo_restante) if d.saldo_restante is not None else 0
                total_inspecciones_programadas += inspecciones_programadas
                total_inspecciones_liquidadas += d.inspecciones_liquidadas
                total_inspecciones_pagadas_anterior += inspecciones_pagadas_hasta_mes_anterior
                total_saldo_restante += saldo_restante
                nombre_propietario = ""
                if lg.proyecto:
                    nombre_propietario = lg.proyecto.nombre_propietario or ""
                expediente = lg.expediente or ""
                distrito = lg.proyecto.distrito.nombre if lg.proyecto and lg.proyecto.distrito else None
                liquidacion_inspector = None
                for li in lcv.inspectores.all():
                    if str(li.inspector_id) == str(r.inspector_id):
                        liquidacion_inspector = li
                        break
                fecha_revision = None
                fecha_presentacion = None
                dictamen_revision = None
                if liquidacion_inspector:
                    if liquidacion_inspector.fecha_revision:
                        fecha_revision = str(liquidacion_inspector.fecha_revision.isoformat())
                    if liquidacion_inspector.fecha_presentacion:
                        fecha_presentacion = str(liquidacion_inspector.fecha_presentacion.isoformat())
                    dictamen_revision = liquidacion_inspector.dictamen_revision or None
                detalles.append(
                    RHInspectorMensualDetalleResult(
                        expediente=expediente,
                        nombre_propietario=nombre_propietario,
                        distrito=distrito,
                        importe_bruto=importe_bruto,
                        inspecciones_programadas=inspecciones_programadas,
                        inspecciones_liquidadas=d.inspecciones_liquidadas,
                        inspecciones_pagadas_hasta_mes_anterior=inspecciones_pagadas_hasta_mes_anterior,
                        costo_por_inspeccion=d.costo_por_inspeccion,
                        monto_contribuido=d.monto_contribuido,
                        saldo_restante=saldo_restante,
                        sub_total=d.sub_total,
                        descuento=d.descuento,
                        honorarios=d.honorarios,
                        liquidacion_especifica_numero=_resolve_liquidacion_especifica_numero(lg),
                        comprobante_activo=_resolve_comprobante_activo(lg),
                        fecha_revision=fecha_revision,
                        fecha_presentacion=fecha_presentacion,
                        dictamen_revision=dictamen_revision,
                    )
                )
            escala = r.escala_descuento
            rangos_qs = escala.rangos.all()
            rango_aplicado = None
            for rng in rangos_qs:
                if rng.porcentaje_descuento == tasa_descuento:
                    rango_aplicado = RangoDescuentoResult(
                        monto_minimo=rng.monto_minimo,
                        monto_maximo=rng.monto_maximo,
                        porcentaje_descuento=rng.porcentaje_descuento,
                    )
                    break
            if rango_aplicado is None:
                first = rangos_qs.first()
                rango_aplicado = RangoDescuentoResult(
                    monto_minimo=first.monto_minimo if first else Decimal("0"),
                    monto_maximo=first.monto_maximo if first else None,
                    porcentaje_descuento=tasa_descuento,
                )
            variables_calculo = RHInspectorVariablesCalculoResult(
                escala_id=str(escala.id),
                escala_nombre=escala.nombre or "",
                rango_aplicado=rango_aplicado,
            )
            periodo_year = r.periodo
            mes = r.mes
            if periodo_year is None or mes is None:
                cs = type(self.core)()
                if periodo_year is None:
                    periodo_year = cs._parse_periodo_year(r.periodo)
                if mes is None:
                    mes = cs._parse_periodo_mes(r.periodo)
            results.append(
                RHInspectorMensualListItemResult(
                    id=str(r.id),
                    numero=r.numero,
                    periodo=periodo_year,
                    mes=mes,
                    fecha_registro=r.fecha_registro.isoformat() if r.fecha_registro else "",
                    inspector=InspectorRHMinimalResult(
                        id=str(r.inspector.id),
                        nombre_completo=inspector_perfil.nombre_completo,
                        cip=inspector_perfil.cip or "",
                        dni=inspector_perfil.dni or "",
                    ),
                    totales=RHInspectorMensualTotalesResult(
                        inspecciones_programadas=total_inspecciones_programadas,
                        inspecciones_liquidadas=total_inspecciones_liquidadas,
                        inspecciones_pagadas_hasta_mes_anterior=total_inspecciones_pagadas_anterior,
                        saldo_restante=total_saldo_restante,
                        sub_total=r.sub_total,
                        descuento=r.descuento,
                        honorarios=r.honorarios,
                        tasa_descuento_aplicada=tasa_descuento,
                    ),
                    detalles=detalles,
                    variables_calculo=variables_calculo,
                )
            )
        return results, total

    def obtener_rh_inspector_detalle_proceso(
        self,
        id: uuid.UUID | None = None,
        inspector_id: uuid.UUID | None = None,
        periodo: int | None = None,
        mes: int | None = None,
    ) -> "RHInspectorMensualListItemResult":
        """
        Obtiene el detalle de un ReciboHonorarioInspectorMensual por ID o clave compuesta.

        Args:
            id: UUID del recibo (mutuamente excluyente con la clave compuesta).
            inspector_id: UUID del inspector (usado con periodo y mes).
            periodo: Año del periodo (e.g. 2026).
            mes: Mes (1-12).

        Returns:
            RHInspectorMensualListItemResult con todos los detalles.

        Raises:
            HttpError(400): Se deben proporcionar exactamente id O (inspector_id + periodo + mes).
            HttpError(404): No se encontró el recibo para los criterios dados.
        """
        if id is not None:
            recibo = self.core.get_rh_inspector_mensual_by_id(id)
        elif inspector_id is not None and periodo is not None and mes is not None:
            recibo = self.core.get_rh_inspector_mensual_by_keys(
                inspector_id=int(inspector_id),
                periodo=periodo,
                mes=mes,
            )
        else:
            raise HttpError(
                400,
                "Debe proporcionar 'id' o la tripletas 'inspector_id' + 'periodo' + 'mes'",
            )

        if not recibo:
            raise HttpError(404, "ReciboHonorarioInspectorMensual no encontrado")

        return self._build_rh_inspector_mensual_result(recibo)

    def list_candidatos_inspector_proceso(
        self,
        cip: str,
        periodo: str | None = None,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ) -> InspectorCandidatosResult:
        """
        Lista las IOs candidatas (con saldo disponible) para el RH mensual del inspector.

        Delega al RHInspectorMensualListFlujo si está disponible;
        fallback a implementación local para backward-compatibilidad con tests.
        """
        if self.rh_inspector_mensual_list_flujo is not None:
            return self.rh_inspector_mensual_list_flujo.list_candidatos_inspector_proceso(
                cip=cip,
                periodo=periodo,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
            )
        # Fallback inline para tests que instancian sin DI
        from modules.finanzas.domain.results.rh_inspector_candidatos_result import (
            InspectorCandidatosResult,
            InspectorCandidataItemResult,
        )
        inspector = self.core.get_inspector_by_cip(cip)
        if not inspector:
            raise HttpError(404, f"Inspector con CIP '{cip}' no encontrado")

        # Parse periodo string YYYY-MM into (periodo_int, mes_int) for core service
        periodo_int: int | None = None
        mes_int: int | None = None
        if periodo:
            parts = periodo.split("-")
            if len(parts) >= 2:
                try:
                    periodo_int = int(parts[0])
                    mes_int = int(parts[1])
                except ValueError:
                    pass  # Keep None values if parsing fails

        candidatos_data = self.core.list_liquidaciones_inspector_candidatas(
            inspector_id=int(inspector.id),
            periodo=periodo_int,
            mes=mes_int,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        perfil = inspector.perfil_ingeniero
        candidatos = [InspectorCandidataItemResult(**data) for data in candidatos_data]
        return InspectorCandidatosResult(
            inspector_id=str(inspector.id),
            inspector_nombre=perfil.nombre_completo if perfil else "",
            inspector_cip=perfil.cip if perfil else "",
            inspector_dni=perfil.dni if perfil else "",
            periodo=periodo or "",
            candidatos=candidatos,
            total=len(candidatos),
        )

    def list_candidatos_inspector_proceso_paginated(
        self,
        cip: str,
        page: int = 1,
        page_size: int = 10,
        expediente: str | None = None,
        numero: int | None = None,
        propietario: str | None = None,
        direccion: str | None = None,
        periodo: str | None = None,
        fecha_inicio: str | None = None,
        fecha_fin: str | None = None,
    ) -> InspectorCandidatosPaginatedResult:
        """
        Lista las IOs candidatas (con saldo disponible) para el RH mensual del inspector
        con paginación y filtros adicionales.

        Delega al RHInspectorMensualListFlujo si está disponible;
        fallback a implementación local para backward-compatibilidad con tests.
        """
        if self.rh_inspector_mensual_list_flujo is not None:
            return self.rh_inspector_mensual_list_flujo.list_candidatos_inspector_proceso_paginated(
                cip=cip,
                page=page,
                page_size=page_size,
                expediente=expediente,
                numero=numero,
                propietario=propietario,
                direccion=direccion,
                periodo=periodo,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
            )
        # Fallback inline para tests que instancian sin DI
        import math
        from modules.finanzas.domain.results.rh_inspector_candidatos_result import (
            InspectorCandidatosPaginatedResult,
            InspectorCandidataItemResult,
        )
        inspector = self.core.get_inspector_by_cip(cip)
        if not inspector:
            raise HttpError(404, f"Inspector con CIP '{cip}' no encontrado")

        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        # Parse periodo string YYYY-MM into (periodo_int, mes_int) for core service
        periodo_int: int | None = None
        mes_int: int | None = None
        if periodo:
            parts = periodo.split("-")
            if len(parts) >= 2:
                try:
                    periodo_int = int(parts[0])
                    mes_int = int(parts[1])
                except ValueError:
                    pass

        candidatos_data, total = self.core.list_liquidaciones_inspector_candidatas_paginated(
            inspector_id=int(inspector.id),
            page=page,
            page_size=page_size,
            expediente=expediente,
            numero=numero,
            propietario=propietario,
            direccion=direccion,
            periodo=periodo_int,
            mes=mes_int,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        perfil = inspector.perfil_ingeniero
        items = [InspectorCandidataItemResult(**data) for data in candidatos_data]
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return InspectorCandidatosPaginatedResult(
            inspector_id=str(inspector.id),
            inspector_nombre=perfil.nombre_completo if perfil else "",
            inspector_cip=perfil.cip if perfil else "",
            inspector_dni=perfil.dni if perfil else "",
            periodo=periodo or "",
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # ── RH Detalle List (flat detail rows) ─────────────────────────────────────

    def list_rh_detalle_delegados_proceso(
        self,
        page: int = 1,
        page_size: int = 20,
        delegado_id: uuid.UUID | None = None,
        delegado_cip: str | None = None,
        periodo: int | None = None,
        mes: int | None = None,
        municipalidad_id: uuid.UUID | None = None,
        tipo_liquidacion_id: uuid.UUID | None = None,
        numero_liquidacion: int | None = None,
    ) -> tuple[list[DetalleDelegadoRowResult], int]:
        """
        Lista filas de DetalleHonorarioDelegado directamente (flat, sin agrupar por mes).

        Args:
            page: Página (1-indexed).
            page_size: Elementos por página (max 100).
            delegado_id: Filter by delegado UUID.
            delegado_cip: Filter by CIP (from perfil_ingeniero). Takes precedence if both are set.
            periodo: Filter by año (from liquidacion_delegado). REQUIRED.
            mes: Filter by mes (1-12, from liquidacion_delegado).
            municipalidad_id: Filter by liquidacion.municipalidad_id (from the Liquidacion, not the operation).
            tipo_liquidacion_id: Filter by liquidacion.tipo_liquidacion_id (from the Liquidacion). REQUIRED.
            numero_liquidacion: Filter by the type-specific numero field. Requires tipo_liquidacion_id.

        Returns:
            Tuple of (list of DetalleDelegadoRowResult, total count).
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        rows, total = self.core.list_detalle_honorario_delegado_paginated(
            page=page,
            page_size=page_size,
            delegado_id=delegado_id,
            delegado_cip=delegado_cip,
            periodo=periodo,
            mes=mes,
            municipalidad_id=municipalidad_id,
            tipo_liquidacion_id=tipo_liquidacion_id,
            numero_liquidacion=numero_liquidacion,
        )

        results: list[DetalleDelegadoRowResult] = []
        for row in rows:
            ld = row.liquidacion_delegado
            lg = ld.liquidacion
            delegado_perfil = ld.delegado.perfil_ingeniero

            # Build nested LiquidacionGeneral
            lg_nested = None
            if lg:
                municipalidad_nested = None
                if getattr(lg, "municipalidad", None):
                    lg_mun = lg.municipalidad
                    municipalidad_nested = MunicipalidadNestedResult(
                        id=str(lg_mun.id),
                        nombre=getattr(lg_mun, "nombre", None),
                    )
                tipo_liq_nested = None
                if getattr(lg, "tipo_liquidacion", None):
                    lg_tipo = lg.tipo_liquidacion
                    tipo_liq_nested = TipoLiquidacionNestedResult(
                        id=str(lg_tipo.id),
                        codigo=getattr(lg_tipo, "codigo", None),
                        nombre=getattr(lg_tipo, "nombre", None),
                    )
                lg_nested = LiquidacionGeneralNestedResult(
                    id=str(lg.id),
                    expediente=getattr(lg, "expediente", None) or None,
                    numero_revision=getattr(lg, "numero_revision", None),
                    municipalidad=municipalidad_nested,
                    tipo_liquidacion=tipo_liq_nested,
                )

            # Build nested DelegadoLiquidacion
            dlq_nested = DelegadoLiquidacionResult(
                id=str(ld.id),
                numero_rh=ld.numero_rh or None,
                periodo=ld.periodo,
                mes=ld.mes,
                dictamen_revision=ld.dictamen_revision or None,
                fecha_revision=str(ld.fecha_revision.isoformat()) if ld.fecha_revision else None,
                fecha_presentacion=str(ld.fecha_presentacion.isoformat()) if ld.fecha_presentacion else None,
                delegado=DelegadoMinimalResult(
                    id=str(ld.delegado_id),
                    cip=delegado_perfil.cip if delegado_perfil else None,
                    nombre_completo=delegado_perfil.nombre_completo if delegado_perfil else None,
                ),
                liquidacion=lg_nested,
                especialidad=EspecialidadMinimalResult(
                    id=str(ld.especialidad_revision.id),
                    nombre=ld.especialidad_revision.nombre if ld.especialidad_revision else None,
                ) if ld.especialidad_revision else None,
            )

            results.append(
                DetalleDelegadoRowResult(
                    id=str(row.id),
                    imp_bruto=row.imp_bruto,
                    sub_total=row.sub_total,
                    renta_cip=row.renta_cip,
                    aporte_codemu=row.aporte_codemu,
                    fondo_comun=row.fondo_comun,
                    neto_honorario=row.neto_honorario,
                    delegado_liquidacion=dlq_nested,
                )
            )

        return results, total

    def list_rh_detalle_inspectores_proceso(
        self,
        page: int = 1,
        page_size: int = 20,
        inspector_id: uuid.UUID | None = None,
        inspector_cip: str | None = None,
        periodo: int | None = None,
        mes: int | None = None,
        municipalidad_id: uuid.UUID | None = None,
        tipo_liquidacion_id: uuid.UUID | None = None,
        numero_liquidacion: int | None = None,
    ) -> tuple[list[DetalleInspectorRowResult], int]:
        """
        Lista filas de DetalleHonorarioInspector directamente (flat, sin agrupar por mes).

        Args:
            page: Página (1-indexed).
            page_size: Elementos por página (max 100).
            inspector_id: Filter by inspector UUID (from parent receipt).
            inspector_cip: Filter by CIP (from inspector.perfil_ingeniero.cip).
                Takes precedence if both inspector_id and inspector_cip are set.
            periodo: Filter by año (from parent ReciboHonorarioInspectorMensual). REQUIRED.
            mes: Filter by mes (1-12, from parent receipt).
            municipalidad_id: Filter by liquidacion_general.municipalidad_id.
            tipo_liquidacion_id: Filter by liquidacion_general.tipo_liquidacion_id. REQUIRED.
            numero_liquidacion: Filter by the type-specific numero field. Requires tipo_liquidacion_id.

        Returns:
            Tuple of (list of DetalleInspectorRowResult, total count).
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        rows, total = self.core.list_detalle_honorario_inspector_paginated(
            page=page,
            page_size=page_size,
            inspector_id=inspector_id,
            inspector_cip=inspector_cip,
            periodo=periodo,
            mes=mes,
            municipalidad_id=municipalidad_id,
            tipo_liquidacion_id=tipo_liquidacion_id,
            numero_liquidacion=numero_liquidacion,
        )

        results: list[DetalleInspectorRowResult] = []
        for row in rows:
            lcv = row.liquidacion_por_categoria_visitas
            lg = lcv.liquidacion_general
            inspector_perfil = row.recibo_mensual.inspector.perfil_ingeniero

            # Build nested LiquidacionInspectorNestedResult
            lg_insp_nested = None
            if lg:
                municipalidad_nested = None
                if getattr(lg, "municipalidad", None):
                    lg_mun = lg.municipalidad
                    municipalidad_nested = InspectorMunicipalidadNestedResult(
                        id=str(lg_mun.id),
                        nombre=getattr(lg_mun, "nombre", None),
                    )
                tipo_liq_nested = None
                if getattr(lg, "tipo_liquidacion", None):
                    lg_tipo = lg.tipo_liquidacion
                    tipo_liq_nested = InspectorTipoLiquidacionNestedResult(
                        id=str(lg_tipo.id),
                        codigo=getattr(lg_tipo, "codigo", None),
                        nombre=getattr(lg_tipo, "nombre", None),
                    )
                lg_insp_nested = LiquidacionInspectorNestedResult(
                    id=str(lg.id),
                    expediente=getattr(lg, "expediente", None) or None,
                    numero_revision=getattr(lg, "numero_revision", None),
                    nombre_propietario=(
                        lg.proyecto.nombre_propietario
                        if getattr(lg, "proyecto", None) else None
                    ),
                    municipalidad=municipalidad_nested,
                    tipo_liquidacion=tipo_liq_nested,
                )

            # Build nested InspectorLiquidacionResult
            ilq_nested = InspectorLiquidacionResult(
                id=str(lcv.id),
                periodo=row.recibo_mensual.periodo,
                mes=row.recibo_mensual.mes,
                dictamen_revision=getattr(lcv, "dictamen_revision", None) or None,
                fecha_revision=str(lcv.fecha_revision.isoformat()) if getattr(lcv, "fecha_revision", None) else None,
                fecha_presentacion=str(lcv.fecha_presentacion.isoformat()) if getattr(lcv, "fecha_presentacion", None) else None,
                inspector=InspectorMinimalResult(
                    id=str(row.recibo_mensual.inspector_id),
                    cip=inspector_perfil.cip if inspector_perfil else None,
                    nombre_completo=inspector_perfil.nombre_completo if inspector_perfil else None,
                ),
                liquidacion=lg_insp_nested,
            )

            results.append(
                DetalleInspectorRowResult(
                    id=str(row.id),
                    inspecciones_liquidadas=row.inspecciones_liquidadas,
                    costo_por_inspeccion=row.costo_por_inspeccion,
                    monto_contribuido=row.monto_contribuido,
                    saldo_restante=row.saldo_restante,
                    importe_bruto=row.importe_bruto,
                    inspecciones_programadas=row.inspecciones_programadas,
                    inspecciones_pagadas_hasta_mes_anterior=row.inspecciones_pagadas_hasta_mes_anterior,
                    sub_total=row.sub_total,
                    descuento=row.descuento,
                    honorarios=row.honorarios,
                    tasa_descuento=row.tasa_descuento,
                    inspector_liquidacion=ilq_nested,
                )
            )

        return results, total
