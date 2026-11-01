# -*- coding: utf-8 -*-
"""
RHReparticionEstacionalPresenter — maps domain results to HTTP schemas.
"""

from modules.finanzas.domain.results.rh_reparticion_estacional_result import (
    RHReparticionEstacionalCotizarResult,
    RHReparticionEstacionalResult,
)
from modules.finanzas.presentation.schemas.rh_reparticion_estacional_schemas import (
    RHReparticionEstacionalCotizarOut,
    RHReparticionEstacionalDelegadoOut,
    RHReparticionEstacionalCapituloOut,
    EspecialidadRevisionMinimalOut,
    RHReparticionEstacionalIdentidadOut,
    RHReparticionEstacionalGeneralOut,
    RHReparticionEstacionalDistribucionOut,
    RHReparticionEstacionalOut,
    RHReparticionEstacionalDeleteOut,
)


class RHReparticionEstacionalPresenter:
    """Presenter for reparticion estacional — transforms domain results to HTTP schemas."""

    @staticmethod
    def present_cotizar(
        result: RHReparticionEstacionalCotizarResult,
    ) -> RHReparticionEstacionalCotizarOut:
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
    def present_reparticion(
        result: RHReparticionEstacionalResult,
    ) -> RHReparticionEstacionalOut:
        """Compose a persisted reparticion for the list endpoint."""
        return RHReparticionEstacionalOut(
            identidad=RHReparticionEstacionalIdentidadOut(
                id=result.id,
                created_at=result.created_at,
            ),
            general=RHReparticionEstacionalGeneralOut(
                especialidad_revision=EspecialidadRevisionMinimalOut(
                    id=result.especialidad_revision_id,
                    nombre=result.especialidad_revision_nombre,
                ),
                periodo=result.periodo,
                mes_desde=result.mes_desde,
                mes_hasta=result.mes_hasta,
            ),
            distribucion=RHReparticionEstacionalDistribucionOut(
                total_fondo_comun=float(result.total_fondo_comun),
                numero_capitulos=result.numero_capitulos,
                numero_delegados=result.numero_delegados,
                monto_por_participacion=float(result.monto_por_participacion),
                residual=float(result.residual),
                detalles_delegados=[
                    RHReparticionEstacionalDelegadoOut(
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
                        capitulo={
                            "id": c.capitulo.id,
                            "nombre": c.capitulo.nombre,
                        },
                        monto=float(c.monto),
                    )
                    for c in result.detalles_capitulos
                ],
            ),
        )

    @staticmethod
    def present_delete(reparticion_id: str) -> RHReparticionEstacionalDeleteOut:
        """Map the soft-deleted reparticion id to the HTTP delete schema."""
        return RHReparticionEstacionalDeleteOut(id=reparticion_id)
