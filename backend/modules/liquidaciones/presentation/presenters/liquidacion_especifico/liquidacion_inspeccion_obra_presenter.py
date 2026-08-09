"""
Presenter de Inspección de Obra.
Mapea el Result del Dominio al Schema final de Presentación.
"""
import uuid

from modules.liquidaciones.domain.results.liquidacion_especifico.inspeccion_obra_primera_revision_result import (
    InspeccionObraPrimeraRevisionResult,
)
from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
    LiquidacionInspeccionObraOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_general.general_schemas import (
    LiquidacionGeneralOutput,
    UsuarioCreadorOutput,
    ProyectoOutput,
    EntidadInlineSchema,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.tipo_schemas import (
    LiquidacionTipoOutput,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.visitas_schemas import (
    LiquidacionPorCategoriaVisitasDatosOut,
)


class LiquidacionInspeccionObraPresenter:
    @staticmethod
    def present_primera_revision(
        result: InspeccionObraPrimeraRevisionResult,
    ) -> LiquidacionInspeccionObraOutput:
        """Assembles the final Inspeccion Obra output from the Result."""
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
            igv_id=uuid.UUID(general.igv_id) if general.igv_id else uuid.uuid4(),
            uit_id=uuid.UUID(general.uit_id) if general.uit_id else uuid.uuid4(),
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

        especifica_out = LiquidacionPorCategoriaVisitasDatosOut(
            id=uuid.UUID(tipo.id),
            cantidad_visitas=tipo.cantidad_visitas,
            porcentaje_uit=tipo.porcentaje_uit,
            categoria=tipo.categoria,
            tarifa_aplicada_id=uuid.UUID(tipo.tarifa_aplicada_id),
        )

        return LiquidacionInspeccionObraOutput(
            liquidacion_general=general_out,
            liquidacion_especifica=tipo_out,
            liquidacion_tipo=especifica_out,
        )
