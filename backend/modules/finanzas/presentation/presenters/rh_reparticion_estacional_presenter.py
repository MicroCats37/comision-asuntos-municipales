# -*- coding: utf-8 -*-
"""
RHReparticionEstacionalPresenter — maps domain results to HTTP schemas.
"""
from modules.finanzas.domain.results.rh_reparticion_estacional_result import (
    RHReparticionEstacionalCotizarResult,
    RHReparticionEstacionalListItemResult,
    RHReparticionEstacionalDetalleResult,
)
from modules.finanzas.presentation.schemas.rh_reparticion_estacional_schemas import (
    RHReparticionEstacionalCotizarOut,
    RHReparticionEstacionalDelegadoOut,
    RHReparticionEstacionalCapituloOut,
    RHReparticionEstacionalListItemOut,
    RHReparticionEstacionalDetalleOut,
)


class RHReparticionEstacionalPresenter:
    """Presenter for reparticion estacional — transforms domain results to HTTP schemas."""

    @staticmethod
    def present_cotizar(result: RHReparticionEstacionalCotizarResult) -> RHReparticionEstacionalCotizarOut:
        """Map cotizar result to HTTP schema."""
        return RHReparticionEstacionalCotizarOut(
            especialidad_revision_id=result.especialidad_revision_id,
            especialidad_revision_nombre=result.especialidad_revision_nombre,
            periodo=result.periodo,
            mes_desde=result.mes_desde,
            mes_hasta=result.mes_hasta,
            total_fondo_comun=float(result.total_fondo_comun),
            numero_capitulos=result.numero_capitulos,
            numero_delegados=result.numero_delegados,
            divisor_total=result.divisor_total,
            monto_por_participacion=float(result.monto_por_participacion),
            residual=float(result.residual),
            detalles_delegados=[
                RHReparticionEstacionalDelegadoOut(
                    delegado_id=d.delegado_id,
                    delegado={
                        "id": d.delegado.id,
                        "cip": d.delegado.cip,
                        "dni": d.delegado.dni,
                        "nombre_completo": d.delegado.nombre_completo,
                    },
                    monto=float(d.monto),
                )
                for d in result.detalles_delegados
            ],
            detalles_capitulos=[
                RHReparticionEstacionalCapituloOut(
                    capitulo_id=c.capitulo_id,
                    capitulo={
                        "id": c.capitulo.id,
                        "nombre": c.capitulo.nombre,
                    },
                    monto=float(c.monto),
                )
                for c in result.detalles_capitulos
            ],
        )

    @staticmethod
    def present_list_item(result: RHReparticionEstacionalListItemResult) -> RHReparticionEstacionalListItemOut:
        """Map list item result to HTTP schema."""
        return RHReparticionEstacionalListItemOut(
            id=result.id,
            especialidad_revision_id=result.especialidad_revision_id,
            especialidad_revision_nombre=result.especialidad_revision_nombre,
            periodo=result.periodo,
            total_fondo_comun=float(result.total_fondo_comun),
            numero_delegados=result.numero_delegados,
            numero_capitulos=result.numero_capitulos,
            monto_por_participacion=float(result.monto_por_participacion),
            residual=float(result.residual),
            is_deleted=result.is_deleted,
            created_at=result.created_at,
        )

    @staticmethod
    def present_detalle(result: RHReparticionEstacionalDetalleResult) -> RHReparticionEstacionalDetalleOut:
        """Map detalle result to HTTP schema."""
        return RHReparticionEstacionalDetalleOut(
            id=result.id,
            especialidad_revision_id=result.especialidad_revision_id,
            especialidad_revision_nombre=result.especialidad_revision_nombre,
            periodo=result.periodo,
            mes_desde=result.mes_desde,
            mes_hasta=result.mes_hasta,
            total_fondo_comun=float(result.total_fondo_comun),
            numero_capitulos=result.numero_capitulos,
            numero_delegados=result.numero_delegados,
            monto_por_participacion=float(result.monto_por_participacion),
            residual=float(result.residual),
            is_deleted=result.is_deleted,
            created_at=result.created_at,
            detalles_delegados=[
                RHReparticionEstacionalDelegadoOut(
                    delegado_id=d.delegado_id,
                    delegado={
                        "id": d.delegado.id,
                        "cip": d.delegado.cip,
                        "dni": d.delegado.dni,
                        "nombre_completo": d.delegado.nombre_completo,
                    },
                    monto=float(d.monto),
                )
                for d in result.detalles_delegados
            ],
            detalles_capitulos=[
                RHReparticionEstacionalCapituloOut(
                    capitulo_id=c.capitulo_id,
                    capitulo={
                        "id": c.capitulo.id,
                        "nombre": c.capitulo.nombre,
                    },
                    monto=float(c.monto),
                )
                for c in result.detalles_capitulos
            ],
        )