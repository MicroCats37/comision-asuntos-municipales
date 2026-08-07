"""
LiquidacionHabilitacionUrbanaPresenter — Presenter específico para Habilitación Urbana.

Solo mapea la primera-revisión (ensamblaje final).
Cotizar y tarifas vigentes se delegan al LiquidacionPorMetroCuadradoPresenter.
NO business logic.
"""
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


class LiquidacionHabilitacionUrbanaPresenter:
    """
    Presenter específico para Habilitación Urbana.
    Solo maneja el mapeo de primera-revisión.
    """

    @staticmethod
    def present_primera_revision(
        liquidacion_general,
        liquidacion_tipo,
        liquidacion_m2,
    ) -> LiquidacionHabilitacionUrbanaOutput:
        """Assembles the final HU output from the 3 domain objects."""
        general_out = LiquidacionGeneralOutput(
            id=liquidacion_general.id,
            municipalidad_id=liquidacion_general.municipalidad_id,
            usuario_creador=UsuarioCreadorOutput(id=liquidacion_general.usuario_creador_id),
            fecha_registro=str(liquidacion_general.fecha_registro),
            expediente=liquidacion_general.expediente,
            observacion=liquidacion_general.observacion,
            numero_revision=liquidacion_general.numero_revision,
            sub_total=float(liquidacion_general.sub_total),
            total=float(liquidacion_general.total),
            igv_id=liquidacion_general.igv_id_id,
            uit_id=liquidacion_general.uit_id_id,
            derecho_id=None,
            proyecto=ProyectoOutput(
                id=liquidacion_general.proyecto.id,
                denominacion=liquidacion_general.proyecto.denominacion,
                nombre_propietario=liquidacion_general.proyecto.nombre_propietario,
                direccion=liquidacion_general.proyecto.direccion,
                distrito_id=liquidacion_general.proyecto.distrito_id,
                entidad=EntidadInlineSchema(
                    tipo_documento=liquidacion_general.proyecto.entidad.tipo_documento,
                    numero_documento=liquidacion_general.proyecto.entidad.numero_documento,
                    razon_social=liquidacion_general.proyecto.entidad.razon_social,
                ),
            ),
        )

        tipo_out = LiquidacionTipoOutput(
            id=liquidacion_tipo.id,
            numero=liquidacion_tipo.numero,
        )

        especifica_out = LiquidacionPorMetroCuadradoDatosOut(
            id=liquidacion_m2.id,
            area_m2=float(liquidacion_m2.area_m2),
            costo_por_m2=float(liquidacion_m2.costo_por_m2),
            derecho_minimo=float(liquidacion_m2.derecho_minimo),
            derecho_maximo=float(liquidacion_m2.derecho_maximo) if liquidacion_m2.derecho_maximo else 0.0,
            tarifa_aplicada_id=liquidacion_m2.tarifa_aplicada_id,
            derecho_aplicado_id=liquidacion_m2.derecho_id,
        )

        return LiquidacionHabilitacionUrbanaOutput(
            liquidacion_general=general_out,
            liquidacion_tipo=tipo_out,
            liquidacion_especifica=especifica_out,
        )
