"""
LiquidacionHabilitacionUrbanaPresenter — Presenter específico para Habilitación Urbana.

Solo mapea la primera-revisión (ensamblaje final).
Cotizar y tarifas vigentes se delegan al LiquidacionPorMetroCuadradoPresenter.
NO business logic.
"""
import uuid

from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_habilitacion_urbana_schemas import (
    LiquidacionHabilitacionUrbanaOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
    UsuarioCreadorOutput,
    ProyectoOutput,
    EntidadInlineSchema,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    LiquidacionTipoOutput,
    LiquidacionPorMetroCuadradoDatosOut,
)

from modules.liquidaciones.domain.results.liquidacion_especifico.habilitacion_urbana_primera_revision_result import (
    HabilitacionUrbanaPrimeraRevisionResult,
)


class LiquidacionHabilitacionUrbanaPresenter:
    """
    Presenter específico para Habilitación Urbana.
    Solo maneja el mapeo de primera-revisión.
    """

    @staticmethod
    def present_primera_revision(
        result: HabilitacionUrbanaPrimeraRevisionResult,
    ) -> LiquidacionHabilitacionUrbanaOutput:
        """Assembles the final HU output from the Result."""
        general = result.liquidacion_general
        tipo = result.liquidacion_tipo
        especifica = result.liquidacion_especifica

        general_out = LiquidacionGeneralOutput(
            id=uuid.UUID(general.id),
            municipalidad_id=uuid.UUID(general.municipalidad_id),
            usuario_creador=UsuarioCreadorOutput(id=uuid.UUID(general.usuario_creador.id)),
            fecha_registro=general.fecha_registro,
            expediente=general.expediente,
            observacion=general.observacion,
            numero_revision=general.numero_revision,
            sub_total=general.sub_total,
            total=general.total,
            igv_id=uuid.UUID(general.igv_id) if general.igv_id else None,
            uit_id=uuid.UUID(general.uit_id) if general.uit_id else None,
            proyecto=ProyectoOutput(
                id=uuid.UUID(general.proyecto.id),
                denominacion=general.proyecto.denominacion,
                nombre_propietario=general.proyecto.nombre_propietario,
                direccion=general.proyecto.direccion,
                distrito_id=uuid.UUID(general.proyecto.distrito_id),
                entidad=EntidadInlineSchema(
                    tipo_documento=general.proyecto.entidad.tipo_documento,
                    numero_documento=general.proyecto.entidad.numero_documento,
                    razon_social=general.proyecto.entidad.razon_social,
                ) if general.proyecto.entidad else None,
            ),
        )

        tipo_out = LiquidacionTipoOutput(
            id=uuid.UUID(especifica.id),
            numero=especifica.numero,
        )

        especifica_out = LiquidacionPorMetroCuadradoDatosOut(
            id=uuid.UUID(tipo.id),
            area_m2=tipo.area_m2,
            costo_por_m2=tipo.costo_por_m2,
            derecho_minimo=tipo.derecho_minimo,
            derecho_maximo=tipo.derecho_maximo or 0.0,
            tarifa_aplicada_id=uuid.UUID(tipo.tarifa_aplicada_id),
            derecho_aplicado_id=uuid.UUID(tipo.derecho_aplicado_id),
        )

        return LiquidacionHabilitacionUrbanaOutput(
            liquidacion_general=general_out,
            liquidacion_especifica=tipo_out,
            liquidacion_tipo=especifica_out,
        )
