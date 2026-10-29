"""
Presenter for Edificaciones (PorcentajeObra).

Inherits common logic from LiquidacionPorcentajeObraPresenter.

Añade la proyección de la estrategia PO: `estrategia_cotizacion`, sus snapshots
(`count_habilitadas`, `total_explicito`, `porcentaje_tarifa`, `tarifa_aplicada_id`)
y la acumulación vigente. Son campos EXCLUSIVOS de Edificaciones: Taludes,
Impacto Vial, edge y legacy conservan el wrapper PO compartido sin cambios.

El presenter sólo transforma: no consulta la base de datos.
"""
import uuid

from modules.liquidaciones.presentation.presenters.liquidacion_especifico.liquidacion_porcentaje_obra_presenter import (
    LiquidacionPorcentajeObraPresenter,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_edificaciones_schemas import (
    LiquidacionEdificacionesOutput,
    LiquidacionEdificacionesCotizarOutput,
    LiquidacionEdificacionesCotizarDetalleOut,
    LiquidacionEdificacionesPorcentajeObraDatosOut,
    LiquidacionEdificacionesAcumulacionOut,
)


class LiquidacionEdificacionesPresenter(LiquidacionPorcentajeObraPresenter):
    """Concrete presenter for Edificaciones tipo."""

    OUTPUT_SCHEMA = LiquidacionEdificacionesOutput
    COTIZAR_OUTPUT_SCHEMA = LiquidacionEdificacionesCotizarOutput
    COTIZAR_DETALLE_SCHEMA = LiquidacionEdificacionesCotizarDetalleOut
    TIPO_DATOS_SCHEMA = LiquidacionEdificacionesPorcentajeObraDatosOut

    @staticmethod
    def _acumulacion_out(acumulacion):
        """Proyecta la acumulación (result de dominio → schema Out)."""
        if acumulacion is None:
            return None
        return LiquidacionEdificacionesAcumulacionOut(
            porcentaje_acumulado=acumulacion.porcentaje_acumulado,
            subtotal_acumulado=acumulacion.subtotal_acumulado,
        )

    @classmethod
    def _campos_estrategia(cls, tipo) -> dict:
        """Campos propios de la estrategia PO de Edificaciones."""
        return {
            "estrategia_cotizacion": getattr(tipo, "estrategia_cotizacion", None),
            "count_habilitadas": getattr(tipo, "count_habilitadas", None),
            "total_explicito": getattr(tipo, "total_explicito", None),
            "porcentaje_tarifa": getattr(tipo, "porcentaje_tarifa", None),
            "tarifa_aplicada_id": (
                uuid.UUID(tipo.tarifa_aplicada_id) if getattr(tipo, "tarifa_aplicada_id", None) else None
            ),
            "acumulacion": cls._acumulacion_out(getattr(tipo, "acumulacion", None)),
        }

    @classmethod
    def _build_tipo_datos_out(cls, tipo, extra: dict | None = None):
        """Wrapper de cálculo de Edificaciones: wrapper PO + estrategia y snapshots."""
        return super()._build_tipo_datos_out(
            tipo,
            extra=cls._campos_estrategia(tipo),
        )

    @classmethod
    def _build_cotizacion_out(cls, domain_result, extra: dict | None = None):
        """Wrapper de cotización (preview) de Edificaciones: wrapper PO + estrategia."""
        campos = cls._campos_estrategia(domain_result)
        # El preview expone la acumulación sin la tarifa del padre (no hay PO persistido).
        campos.pop("tarifa_aplicada_id", None)
        return super()._build_cotizacion_out(domain_result, extra=campos)
