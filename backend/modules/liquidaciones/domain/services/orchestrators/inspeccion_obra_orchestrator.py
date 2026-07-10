"""
InspeccionObraOrchestrator — fachada asíncrona ligera para controladores.

Solo delega al InspeccionObraFlujo. Sin lógica de negocio aquí.
Valida XOR proyecto, longitud de tarifas_ids y categoría requerida.
"""

from asgiref.sync import sync_to_async
from injector import inject
from ninja.errors import HttpError

from ..flujos.inspeccion_obra_flujo import InspeccionObraFlujo
from ...schemas_proyecto import ProyectoInlineData
from ...schemas import ProyectistaInlineData
from ...constants import TramiteAccion


class InspeccionObraOrchestrator:
    """
    Fachada asíncrona ligera — delega lógica a Flujo.

    Valida:
    - XOR proyecto: exactamente uno de proyecto_public_id o proyecto_inline debe estar presente
    - tarifas_ids: exactamente 1 elemento si se proporciona
    - categoria: no vacía (requerida para resolver tarifa)

    Inyecta flujo vía __init__.
    """

    @inject
    def __init__(
        self,
        flujo: InspeccionObraFlujo,
    ):
        self.flujo = flujo

    async def crear_primera_revision(
        self,
        proyecto_public_id: str | None,
        municipalidad_id: str,
        cantidad_visitas: int,
        categoria: str,
        expediente: str | None,
        observacion: str | None,
        proyecto_inline: ProyectoInlineData | None = None,
        tarifas_ids: list[str] | None = None,
        proyectistas_inline: list[ProyectistaInlineData] | None = None,
    ):
        """
        Crear primera revisión de Inspección de Obra.

        Valida XOR proyecto, longitud de tarifas_ids y categoría, luego delega a flujo.

        Args:
            proyecto_public_id: ID público del proyecto existente (mutuamente excluyente con proyecto_inline).
            municipalidad_id: ID de la municipalidad (UUID).
            cantidad_visitas: Cantidad de visitas de inspección (mínimo 1).
            categoria: Categoría de inspección (A, B, C, etc.). Requerida para resolver la tarifa.
            expediente: Número de expediente (opcional).
            observacion: Observación (opcional).
            proyecto_inline: Datos del proyecto inline a crear (mutuamente excluyente con proyecto_public_id).
            tarifas_ids: IDs de tarifas (exactamente 1 elemento si se proporciona).
            proyectistas_inline: Lista de proyectistas inline con CIP (opcional).

        Returns:
            LiquidacionInspeccionObraResult

        Raises:
            HttpError(400): Si ambos proyecto_public_id y proyecto_inline están presentes,
                           o si ninguno está presente, o si tarifas_ids tiene más de 1 elemento,
                           o si categoria está vacía.
            HttpError(404): Si no se encuentra la tarifa para la categoría e InspectionObra.
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
                f"de Inspección de Obra, pero se recibieron {len(tarifas_ids)} elementos."
            )

        # Validar que categoria no esté vacía
        if not categoria or categoria.strip() == "":
            raise HttpError(
                400,
                "categoria es requerida para Inspección de Obra y no puede estar vacía."
            )

        # Extraer tarifa_id si se proporcionó
        tarifa_id = tarifas_ids[0] if tarifas_ids else None

        return await self.flujo._proceso_creacion(
            proyecto_public_id=proyecto_public_id if has_public_id else None,
            municipalidad_id=municipalidad_id,
            cantidad_visitas=cantidad_visitas,
            categoria=categoria.strip(),
            expediente=expediente,
            observacion=observacion,
            proyecto_inline=proyecto_inline,
            tarifa_id=tarifa_id,
            proyectistas_inline=proyectistas_inline,
        )

    async def cotizar_primera_revision(
        self,
        cantidad_visitas: int,
        categoria: str,
        tarifas_ids: list[str] | None = None,
    ):
        """
        Cotizar primera revisión de Inspección de Obra sin guardar en BD.

        Args:
            cantidad_visitas: Cantidad de visitas de inspección.
            categoria: Categoría de inspección (A, B, C, etc.).
            tarifas_ids: IDs de tarifas (exactamente 1 elemento si se proporciona).

        Returns:
            CotizacionVisitasQuoteData

        Raises:
            HttpError(400): Si tarifas_ids tiene más de 1 elemento o categoria está vacía.
            HttpError(404): Si no se encuentra la tarifa para la categoría e Inspección de Obra.
        """
        # Validar exactamente 1 elemento en tarifas_ids si se proporciona
        if tarifas_ids is not None and len(tarifas_ids) != 1:
            raise HttpError(
                400,
                f"tarifas_ids debe contener exactamente 1 elemento para cotización "
                f"de Inspección de Obra, pero se recibieron {len(tarifas_ids)} elementos."
            )

        # Validar que categoria no esté vacía
        if not categoria or categoria.strip() == "":
            raise HttpError(
                400,
                "categoria es requerida para cotizar Inspección de Obra y no puede estar vacía."
            )

        # Extraer tarifa_id si se proporcionó
        tarifa_id = tarifas_ids[0] if tarifas_ids else None

        return await self.flujo._proceso_cotizar_primera_revision(
            cantidad_visitas=cantidad_visitas,
            categoria=categoria.strip(),
            tarifa_id=tarifa_id,
        )

    async def obtener_tarifas_vigentes(
        self,
        tramite_accion: str = TramiteAccion.PRIMERA_REVISION,
        categoria: str | None = None,
    ) -> list[dict]:
        """
        Obtiene las tarifas vigentes de Inspección de Obra para el formulario.

        Args:
            tramite_accion: Acción de trámite (PRIMERA_REVISION o REVISION).
                Defaults to PRIMERA_REVISION.
            categoria: Filter by inspection category (e.g. CATEGORIA_A, CATEGORIA_B).
                Optional — if not provided, returns tariffs for all categories.

        Returns:
            Lista de diccionarios con tarifas de inspección vigentes.
            Cada dict contiene: tarifa_id, detalle_id, costo_por_visita,
            visitas_minimas, categoria, habilitada.
        """
        return await sync_to_async(
            self.flujo.core.obtener_tarifas_vigentes
        )(
            tramite_accion=tramite_accion,
            categoria=categoria,
        )
