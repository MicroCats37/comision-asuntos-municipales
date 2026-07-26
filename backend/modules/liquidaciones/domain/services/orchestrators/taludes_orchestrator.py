"""
TaludesOrchestrator — fachada asíncrona ligera para controladores.

Solo delega al TaludesFlujo. Sin lógica de negocio aquí.
Valida XOR proyecto y longitud de tarifas_ids.
"""

from asgiref.sync import sync_to_async
from injector import inject
from ninja.errors import HttpError

from ..flujos.taludes_flujo import TaludesFlujo
from ...schemas_proyecto import ProyectoInlineData
from ...schemas import ProyectistaInlineData, RevisionVigenteResult
from ...constants import TramiteAccion


class TaludesOrchestrator:
    """
    Fachada asíncrona ligera — delega lógica a Flujo.

    Valida:
    - XOR proyecto: exactamente uno de proyecto_public_id o proyecto_inline debe estar presente
    - tarifas_ids: exactamente 1 elemento si se proporciona

    Inyecta flujo vía __init__.
    """

    @inject
    def __init__(
        self,
        flujo: TaludesFlujo,
    ):
        self.flujo = flujo

    async def crear_primera_revision(
        self,
        proyecto_public_id: str | None,
        municipalidad_id: str,
        valor_proyecto: float,
        expediente: str | None,
        observacion: str | None,
        proyecto_inline: ProyectoInlineData | None = None,
        tarifas_ids: list[str] | None = None,
        proyectistas_inline: list[ProyectistaInlineData] | None = None,
    ):
        """
        Crear primera revisión de Taludes.

        Valida XOR proyecto y longitud de tarifas_ids, luego delega a flujo.

        Args:
            proyecto_public_id: ID público del proyecto existente (mutuamente excluyente con proyecto_inline).
            municipalidad_id: ID de la municipalidad (UUID).
            valor_proyecto: Valor del proyecto en soles para el cálculo porcentual.
            expediente: Número de expediente (opcional).
            observacion: Observación (opcional).
            proyecto_inline: Datos del proyecto inline a crear (mutuamente excluyente con proyecto_public_id).
            tarifas_ids: IDs de tarifas (exactamente 1 elemento si se proporciona).
            proyectistas_inline: Lista de proyectistas inline con CIP (opcional).

        Returns:
            Tuple of (LiquidacionTaludesResult, LiquidacionPorcentajeObra)

        Raises:
            HttpError(400): Si ambos proyecto_public_id y proyecto_inline están presentes,
                           o si ninguno está presente, o si tarifas_ids tiene más de 1 elemento.
            HttpError(404): Si no se encuentra la tarifa para TALUDES.
        """
        # XOR validation
        has_public_id = proyecto_public_id is not None and proyecto_public_id != ""
        has_inline = proyecto_inline is not None

        if has_public_id and has_inline:
            raise HttpError(
                400,
                "No se puede enviar ambos proyecto_public_id y proyecto_inline. "
                "Solo uno debe estar presente."
            )
        if not has_public_id and not has_inline:
            raise HttpError(
                400,
                "Debe enviarse proyecto_public_id o proyecto_inline. "
                "Uno de los dos es requerido."
            )

        # Validar exactamente 1 elemento en tarifas_ids si se proporciona
        if tarifas_ids is not None and len(tarifas_ids) != 1:
            raise HttpError(
                400,
                f"tarifas_ids debe contener exactamente 1 elemento para primera revisión "
                f"de Taludes, pero se recibieron {len(tarifas_ids)} elementos."
            )

        # Extraer tarifa_id si se proporcionó
        tarifa_id = tarifas_ids[0] if tarifas_ids else None

        return await self.flujo._proceso_creacion(
            proyecto_public_id=proyecto_public_id if has_public_id else None,
            municipalidad_id=municipalidad_id,
            valor_proyecto=valor_proyecto,
            expediente=expediente,
            observacion=observacion,
            proyecto_inline=proyecto_inline,
            tarifa_id=tarifa_id,
            proyectistas_inline=proyectistas_inline,
        )

    async def cotizar_primera_revision(
        self,
        tipo_liquidacion: str,
        valor_proyecto: float,
        tarifas_ids: list[str] | None = None,
    ):
        """
        Cotizar primera revisión de Taludes sin guardar en BD.

        Args:
            tipo_liquidacion: Tipo de liquidación (debe ser TALUDES).
            valor_proyecto: Valor del proyecto en soles para el cálculo porcentual.
            tarifas_ids: IDs de tarifas (exactamente 1 elemento si se proporciona).

        Returns:
            CotizacionQuoteData

        Raises:
            HttpError(400): Si tarifas_ids tiene más de 1 elemento.
            HttpError(404): Si no se encuentra la tarifa para TALUDES.
        """
        # Validar exactamente 1 elemento en tarifas_ids si se proporciona
        if tarifas_ids is not None and len(tarifas_ids) != 1:
            raise HttpError(
                400,
                f"tarifas_ids debe contener exactamente 1 elemento para cotización "
                f"de Taludes, pero se recibieron {len(tarifas_ids)} elementos."
            )

        # Extraer tarifa_id si se proporcionó
        tarifa_id = tarifas_ids[0] if tarifas_ids else None

        return await self.flujo._proceso_cotizar_primera_revision(
            tipo_liquidacion=tipo_liquidacion,
            valor_proyecto=valor_proyecto,
            tarifa_id=tarifa_id,
        )

    async def obtener_tarifas_vigentes(
        self,
        tipo_tramite: str | None = None,
        tramite_accion: str = TramiteAccion.PRIMERA_REVISION,
    ) -> list[dict]:
        """
        Obtiene las tarifas vigentes de Taludes para el formulario.

        Args:
            tipo_tramite: Tipo de trámite de edificación (opcional).
                Si se provee, filtra usando ReglaTarifaEdificacion.
            tramite_accion: Acción de trámite (PRIMERA_REVISION o REVISION).
                Defaults to PRIMERA_REVISION.

        Returns:
            Lista de diccionarios con tarifas M2 vigentes.
            Cada dict contiene: tarifa_id, detalle_id, costo_por_m2, area_m2,
            derecho_minimo, derecho_maximo, habilitada.
        """
        return await sync_to_async(
            self.flujo.core.obtener_tarifas_vigentes
        )(
            tipo_tramite=tipo_tramite,
            tramite_accion=tramite_accion,
        )

    async def obtener_revisiones_vigentes(
        self,
        tipo_tramite: str | None = None,
        tramite_accion: str = TramiteAccion.PRIMERA_REVISION,
    ) -> list[RevisionVigenteResult]:
        """
        Obtiene las revisiones vigentes de Taludes para el formulario.

        Devuelve objetos RevisionVigenteResult con especialidades M2M incluidas,
        similar al patrón de Edificaciones.

        Args:
            tipo_tramite: Tipo de trámite de edificación (opcional).
                Si se provee, filtra usando ReglaTarifaEdificacion.
            tramite_accion: Acción de trámite (PRIMERA_REVISION o REVISION).
                Defaults to PRIMERA_REVISION.

        Returns:
            Lista de RevisionVigenteResult con especialidades populadas.
        """
        return await sync_to_async(
            self.flujo.core.obtener_revisiones_vigentes
        )(
            tipo_tramite=tipo_tramite,
            tramite_accion=tramite_accion,
        )
