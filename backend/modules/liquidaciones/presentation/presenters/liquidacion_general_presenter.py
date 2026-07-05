"""
LiquidacionGeneralPresenter — transforma resultados a esquemas HTTP para liquidaciones generales.
"""
import uuid
from typing import Union

from modules.liquidaciones.domain.schemas import (
    LiquidacionGeneralResult,
    LiquidacionGeneralListItem,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general_schemas import (
    LiquidacionGeneralOut,
    LiquidacionGeneralListItemOut,
    ProyectoGeneralOut,
    EntidadGeneralOut,
)


class LiquidacionGeneralPresenter:
    """
    Transforma objetos de resultado del dominio a esquemas de respuesta HTTP
    para el controlador de liquidaciones generales.
    """

    @staticmethod
    def present(result: LiquidacionGeneralResult) -> LiquidacionGeneralOut:
        """
        Transforma un LiquidacionGeneralResult a LiquidacionGeneralOut.

        Args:
            result: LiquidacionGeneralResult con campos planos

        Returns:
            LiquidacionGeneralOut schema para respuesta HTTP
        """
        # ── Entidad ─────────────────────────────────────────────────────────────
        entidad = None
        if result.entidad_id or result.entidad_nombre:
            entidad = EntidadGeneralOut(
                id=result.entidad_id,
                tipo=result.entidad_tipo,
                nombre=result.entidad_nombre,
                ruc=result.entidad_ruc,
            )

        # ── Proyecto ───────────────────────────────────────────────────────────
        proyecto = None
        if result.proyecto_id or result.proyecto_nombre:
            proyecto = ProyectoGeneralOut(
                id=result.proyecto_id or uuid.UUID('00000000-0000-0000-0000-000000000000'),
                public_id=result.proyecto_public_id or '',
                nombre=result.proyecto_nombre or '',
                direccion=result.proyecto_direccion,
            )

        # ── Valores financieros ───────────────────────────────────────────────
        subtotal = float(result.subtotal) if result.subtotal else 0.0
        igv = float(result.igv) if result.igv else 0.0
        total = float(result.total) if result.total else 0.0
        total_a_pagar = float(result.total_a_pagar) if result.total_a_pagar else 0.0

        # ── Armar LiquidacionGeneralOut ───────────────────────────────────────
        return LiquidacionGeneralOut(
            id=result.id,
            public_id=result.public_id,
            estado=result.estado,
            tipo_liquidacion=result.tipo_liquidacion,
            numero_revision=result.numero_revision,
            fecha_registro=result.fecha_registro,
            expediente=result.expediente,
            observacion=result.observacion,
            municipalidad_nombre=result.municipalidad_nombre,
            proyecto=proyecto,
            entidad=entidad,
            subtotal=subtotal,
            igv=igv,
            total=total,
            total_a_pagar=total_a_pagar,
        )

    @staticmethod
    def present_list_item(result: LiquidacionGeneralListItem) -> LiquidacionGeneralListItemOut:
        """
        Transforma un LiquidacionGeneralListItem a LiquidacionGeneralListItemOut.

        Args:
            result: LiquidacionGeneralListItem de la lista paginada

        Returns:
            LiquidacionGeneralListItemOut schema para respuesta HTTP
        """
        from modules.liquidaciones.presentation.schemas.liquidacion_general_schemas import TotalesListItemOut

        # Construir totales anidados si tenemos datos financieros
        totales = None
        if result.subtotal is not None or result.igv is not None:
            subtotal = result.subtotal if result.subtotal is not None else 0.0
            igv = result.igv if result.igv is not None else 0.0
            total_liq = result.total if result.total is not None else subtotal + igv
            totales = TotalesListItemOut(
                subtotal=subtotal,
                igv=igv,
                total=total_liq,
                liquidacion_total=total_liq,
                total_a_pagar=result.total_a_pagar if result.total_a_pagar is not None else total_liq,
            )

        return LiquidacionGeneralListItemOut(
            id=result.id,
            public_id=result.public_id,
            estado=result.estado,
            tipo_liquidacion=result.tipo_liquidacion,  # Ya viene en slug del core
            numero_revision=result.numero_revision,
            proyecto_denominacion=result.proyecto_denominacion,
            proyecto_public_id=result.proyecto_public_id,
            fecha_registro=result.fecha_registro,
            total=result.total,
            expediente=result.expediente,
            observacion=result.observacion,
            municipalidad_id=result.municipalidad_id,
            municipalidad_nombre=result.municipalidad_nombre,
            valor_caracteristico=result.valor_caracteristico,
            totales=totales,
        )

    @staticmethod
    def present_list(
        results: list[LiquidacionGeneralListItem],
    ) -> list[LiquidacionGeneralListItemOut]:
        """
        Transforma una lista de LiquidacionGeneralListItem a lista de LiquidacionGeneralListItemOut.

        Args:
            results: Lista de LiquidacionGeneralListItem

        Returns:
            Lista de LiquidacionGeneralListItemOut
        """
        return [LiquidacionGeneralPresenter.present_list_item(r) for r in results]
