"""
HabilitacionUrbanaOrchestrator — fachada asíncrona ligera para controladores.

Solo delega al HabilitacionUrbanaFlujo. Sin lógica de negocio aquí.
Valida XOR proyecto y longitud de tarifas_ids.
"""

from asgiref.sync import sync_to_async
from injector import inject
from ninja.errors import HttpError

from ..flujos.habilitacion_urbana_flujo import HabilitacionUrbanaFlujo
from ...schemas_proyecto import ProyectoInlineData
from ...exceptions import NotFoundError
from ...constants import TramiteAccion


class HabilitacionUrbanaOrchestrator:
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
        flujo: HabilitacionUrbanaFlujo,
    ):
        self.flujo = flujo

    async def crear_primera_revision(
        self,
        proyecto_public_id: str | None,
        municipalidad_id: str,
        area_solicitada: float,
        expediente: str | None,
        observacion: str | None,
        proyecto_inline: ProyectoInlineData | None = None,
        tarifas_ids: list[str] | None = None,
    ):
        """
        Crear primera revisión de Habilitación Urbana.

        Valida XOR proyecto y longitud de tarifas_ids, luego delega a flujo.

        Args:
            proyecto_public_id: ID público del proyecto existente (mutuamente excluyente con proyecto_inline).
            municipalidad_id: ID de la municipalidad (UUID).
            area_solicitada: Área solicitada en m2.
            expediente: Número de expediente (opcional).
            observacion: Observación (opcional).
            proyecto_inline: Datos del proyecto inline a crear (mutuamente excluyente con proyecto_public_id).
            tarifas_ids: IDs de tarifas (exactamente 1 elemento si se proporciona).

        Returns:
            LiquidacionHabilitacionUrbanaResult

        Raises:
            HttpError(400): Si ambos proyecto_public_id y proyecto_inline están presentes,
                           o si ninguno está presente, o si tarifas_ids tiene más de 1 elemento.
            HttpError(404): Si no se encuentra la tarifa para HABILITACION_URBANA.
        """
        # XOR validation: exactamente uno de proyecto_public_id o proyecto_inline debe estar presente
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
                f"de Habilitación Urbana, pero se recibieron {len(tarifas_ids)} elementos."
            )

        # Extraer tarifa_id si se proporcionó
        tarifa_id = tarifas_ids[0] if tarifas_ids else None

        return await self.flujo._proceso_creacion(
            proyecto_public_id=proyecto_public_id if has_public_id else None,
            municipalidad_id=municipalidad_id,
            area_solicitada=area_solicitada,
            expediente=expediente,
            observacion=observacion,
            proyecto_inline=proyecto_inline,
            tarifa_id=tarifa_id,
        )

    async def cotizar_primera_revision(
        self,
        tipo_liquidacion: str,
        area_solicitada: float,
        tarifas_ids: list[str] | None = None,
    ):
        """
        Cotizar primera revisión de Habilitación Urbana sin guardar en BD.

        Args:
            tipo_liquidacion: Tipo de liquidación (debe ser HABILITACION_URBANA).
            area_solicitada: Área solicitada en m2.
            tarifas_ids: IDs de tarifas (exactamente 1 elemento si se proporciona).

        Returns:
            CotizacionM2QuoteData

        Raises:
            HttpError(400): Si tarifas_ids tiene más de 1 elemento.
            HttpError(404): Si no se encuentra la tarifa para HABILITACION_URBANA.
        """
        # Validar exactamente 1 elemento en tarifas_ids si se proporciona
        if tarifas_ids is not None and len(tarifas_ids) != 1:
            raise HttpError(
                400,
                f"tarifas_ids debe contener exactamente 1 elemento para cotización "
                f"de Habilitación Urbana, pero se recibieron {len(tarifas_ids)} elementos."
            )

        # Extraer tarifa_id si se proporcionó
        tarifa_id = tarifas_ids[0] if tarifas_ids else None

        return await self.flujo._proceso_cotizar_primera_revision(
            tipo_liquidacion=tipo_liquidacion,
            area_solicitada=area_solicitada,
            tarifa_id=tarifa_id,
        )

    async def obtener_tarifas_vigentes(
        self,
        tramite_accion: str = TramiteAccion.PRIMERA_REVISION,
    ) -> list[dict]:
        """
        Obtiene las tarifas vigentes de Habilitación Urbana para el formulario.

        Args:
            tramite_accion: Acción de trámite (PRIMERA_REVISION o REVISION).
                Defaults to PRIMERA_REVISION.

        Returns:
            Lista de diccionarios con tarifas M2 vigentes.
            Cada dict contiene: tarifa_id, detalle_id, costo_por_m2, area_minima,
            derecho_minimo, derecho_maximo, habilitada.
        """
        return await sync_to_async(
            self.flujo.core._tarifas_core._obtener_tarifas_m2_vigentes
        )(
            tipo_liquidacion="HABILITACION_URBANA",
            tramite_accion=tramite_accion,
        )
