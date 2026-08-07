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
            fecha_registro="2026-08-07T00:00:00Z", # Placeholder for now as not in DTO
            expediente=general.expediente,
            observacion=general.observacion,
            numero_revision=general.numero_revision,
            sub_total=general.sub_total,
            total=general.total,
            igv_id=uuid.uuid4(), # Placeholder as not in DTO
            uit_id=uuid.uuid4(), # Placeholder as not in DTO
            derecho_id=None,
            proyecto=ProyectoOutput(
                id=uuid.UUID(general.proyecto.id),
                denominacion=general.proyecto.denominacion,
                nombre_propietario=general.proyecto.nombre_propietario,
                direccion=general.proyecto.direccion,
                distrito_id=uuid.uuid4(), # Needs to be passed if needed
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
            derecho_aplicado_id=uuid.uuid4(), # Placeholder
        )

        return LiquidacionHabilitacionUrbanaOutput(
            liquidacion_general=general_out,
            liquidacion_tipo=tipo_out,
            liquidacion_especifica=especifica_out,
        )
