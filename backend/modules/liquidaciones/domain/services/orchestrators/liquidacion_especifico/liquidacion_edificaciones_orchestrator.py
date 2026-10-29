"""
Orchestrator for Edificaciones (PorcentajeObra) first revision.

Validates input, applies per-detail clamping,
maps Presentation Schema -> Domain DTO.

Architecture: Orchestrator owns business rules (clamping). No @transaction.atomic.
"""
from decimal import Decimal
from typing import List, Optional
from datetime import date
import uuid
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from injector import inject
from ninja.errors import HttpError
from modules.liquidaciones.domain.constants import EstrategiaCotizacionPO, TipoLiquidacion
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import (
    CotizacionPOContexto,
    CotizacionPOEstrategiaData,
    LiquidacionPorcentajeObraCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_edificaciones_flujo import (
    LiquidacionEdificacionesFlujo,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_general_orchestrator import (
    LiquidacionGeneralOrchestrator,
)
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    EntidadData,
    LiquidacionGeneralData,
    ProyectoData,
    ContactoData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_porcentaje_data import (
    DatosPorcentajeObra,
    LiquidacionPorcentajeObraData,
    TarifaPorcentajeObraAplicada,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.primera_revision_data import (
    LiquidacionEspecificaPrimeraRevisionData,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.primera_revision_result import (
    LiquidacionEspecificaPrimeraRevisionResult,
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    ContactoResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import (
    CotizacionPorcentajeObraResult,
    CotizacionPorcentajeObraDetalleResult,
    EspecialidadResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_porcentaje_result import (
    AcumulacionPorcentajeObraResult,
)
from modules.liquidaciones.presentation.schemas.liquidacion_tipo.porcentaje_schemas import (
    LiquidacionPorcentajeObraTarifaIn,
)
from modules.liquidaciones.domain.exceptions import LiquidacionNotFoundError
from modules.liquidaciones.domain.services.orchestrators._shared import LiquidacionPOValidationMixin
from modules.liquidaciones.domain.services.orchestrators._shared.vigencia_validation import validar_tarifa_unica_por_base
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision

class LiquidacionEdificacionesOrchestrator(LiquidacionPOValidationMixin):
    """
    Orchestrator for Edificaciones (PorcentajeObra).
    
    Mirrors the MecanicaSuelos pattern but:
    - Uses PorcentajeObra Core service (not M2)
    - Handles hybrid resolution (auto-fill vs explicit tarifas)
    - tipo_tramite stays NULL for now (FUTURE comment)
    
    Uses LiquidacionPOValidationMixin for shared validation helpers.
    """

    @inject
    def __init__(
        self,
        porcentaje_core_service: LiquidacionPorcentajeObraCoreService,
        general_core_service: LiquidacionGeneralCoreService,
        general_orchestrator: LiquidacionGeneralOrchestrator,
        flujo: LiquidacionEdificacionesFlujo,
    ):
        self.porcentaje_core = porcentaje_core_service
        self.general_core = general_core_service
        self.general_orchestrator = general_orchestrator
        self.flujo = flujo
    
    def crear_primera_revision_proceso(
        self,
        usuario_id: int,
        payload_in,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Validates input, resolves the quotation context, delegates to Flujo.

        Flow:
        1. Validate the strategy payload (valor declarado / total explícito)
        2. Resolve tarifas (hybrid) → participantes
        3. Resolve H (habilitadas del catálogo) — NUNCA desde los participantes
        4. Validate IGV/UIT/derecho vigentes exist
        5. Build domain DTO
        6. Delegate to Flujo (el motor único corre dentro de la transacción)
        """
        estrategia_in = payload_in.liquidacion_especifica
        estrategia = estrategia_in.estrategia_cotizacion
        valor_declarado, total_explicito = self._resolver_datos_estrategia(estrategia_in)

        # Step 1: Validation
        if valor_declarado is None or valor_declarado <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")

        # Step 2: Hybrid resolution → participantes (la especialidad viene del input)
        tarifas_aplicadas = self._resolver_tarifas_aplicadas(estrategia_in.tarifas)

        # Step 3: H desde el catálogo (fecha efectiva = hoy en creación)
        count_habilitadas = self._resolver_count_habilitadas(estrategia)

        # Step 4: Get vigente IGV and UIT
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        if not igv_vigente or not uit_vigente:
            raise HttpError(400, "No hay IGV o UIT vigente configurado")

        derecho = self.porcentaje_core.get_derecho_porcentaje_vigente()
        if not derecho:
            raise HttpError(400, "No hay DerechoPorcentajeObra vigente")

        # Step 5: Build domain DTOs with explicit especialidad from INPUT
        # (not from TarifaPorcentajeObra.especialidad which no longer exists)
        domain_data = LiquidacionEspecificaPrimeraRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                  municipalidad_id=str(payload_in.liquidacion_general.municipalidad_id),
                  expediente=payload_in.liquidacion_general.expediente,
                  observacion=payload_in.liquidacion_general.observacion,
                  denominacion_de_proyecto=payload_in.liquidacion_general.denominacion_de_proyecto,
                  numero_revision=payload_in.numero_revision,
                proyecto=ProyectoData(
                    nombre_propietario=payload_in.liquidacion_general.proyecto.nombre_propietario,
                    direccion=payload_in.liquidacion_general.proyecto.direccion,
                    distrito_id=str(payload_in.liquidacion_general.proyecto.distrito_id) if payload_in.liquidacion_general.proyecto.distrito_id else None,
                    entidad_razon_social=payload_in.liquidacion_general.proyecto.entidad.razon_social,
                    entidad=EntidadData(
                        tipo_documento=payload_in.liquidacion_general.proyecto.entidad.tipo_documento,
                        numero_documento=payload_in.liquidacion_general.proyecto.entidad.numero_documento,
                    ),
                ),
                contacto=(
                    ContactoData(
                        nombres=payload_in.liquidacion_general.contacto.nombres,
                        apellidos=payload_in.liquidacion_general.contacto.apellidos,
                        dni=payload_in.liquidacion_general.contacto.dni,
                        cargo=payload_in.liquidacion_general.contacto.cargo,
                        telefono=payload_in.liquidacion_general.contacto.telefono,
                        celular=payload_in.liquidacion_general.contacto.celular,
                        email=payload_in.liquidacion_general.contacto.email,
                    )
                    if payload_in.liquidacion_general.contacto
                    else None
                ),
                # FUTURE: when tipo_tramite is added, pass payload_in.tipo_tramite here
            ),
            liquidacion_especifica=LiquidacionPorcentajeObraData(
                datos=DatosPorcentajeObra(valor_declarado=valor_declarado),
                tarifas=tarifas_aplicadas,
                tipo_tramite=estrategia_in.tipo_tramite,
                estrategia_cotizacion=estrategia,
                count_habilitadas=count_habilitadas,
                total_explicito=total_explicito,
            ),
        )

        # Step 6: Delegate to Flujo
        return self.flujo.ejecutar_primera_revision(
            usuario_id=usuario_id,
            data=domain_data,
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            derecho=derecho,
            uit_valor=Decimal(str(uit_vigente.valor)),
        )

    def obtener_tarifas_vigentes_proceso(self, fecha=None):
        """
        Fetches currently active (or historical at fecha) TarifaPorcentajeObra list
        and available LiquidacionEspecialidadDisponibles for Edificaciones.

        With tarifa-unica-especialidades: returns a tuple of
        (tarifas, especialidades_disponibles) since the single tariff
        no longer carries an especialidad FK.

        Args:
            fecha: Optional date to fetch vigentes at that date. Defaults to today.
        """
        tarifas = self.porcentaje_core.get_tarifas_porcentaje_vigentes(
            TipoLiquidacion.EDIFICACION, fecha=fecha
        )
        if fecha is None:
            validar_tarifa_unica_por_base(tarifas, TipoLiquidacion.EDIFICACION)
        especialidades = self._obtener_especialidades_vigentes_para_tipo(
            TipoLiquidacion.EDIFICACION, fecha=fecha
        )
        return tarifas, especialidades

    def cotizar_proceso(
        self,
        estrategia_in,
    ) -> CotizacionPorcentajeObraResult:
        """
        Preview de cotización PO de Edificaciones por estrategia. Does NOT persist.

        Resuelve EXACTAMENTE el mismo contexto que la creación (estrategia,
        participantes, H del catálogo, IGV, UIT y derechos vigentes) y ejecuta el
        MOTOR ÚNICO: preview y guardado producen las mismas cifras.

        Returns CotizacionPorcentajeObraResult with totals, per-detalle breakdown,
        the applied strategy, its snapshots and the ephemeral accumulation
        projection (que el preview NUNCA persiste).
        """
        estrategia = estrategia_in.estrategia_cotizacion
        valor_declarado, total_explicito = self._resolver_datos_estrategia(estrategia_in)

        # Step 1: Validation
        if valor_declarado is None or valor_declarado <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")

        # Step 2: Hybrid resolution → participantes
        tarifas_aplicadas = self._resolver_tarifas_aplicadas(estrategia_in.tarifas)

        # Step 3: H desde el catálogo (fecha efectiva = hoy en preview)
        count_habilitadas = self._resolver_count_habilitadas(estrategia)

        # Step 4: Get vigente IGV, UIT and derecho
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        if not igv_vigente:
            raise HttpError(400, "No hay IGV vigente")
        if not uit_vigente:
            raise HttpError(400, "No hay UIT vigente configurado")

        derecho = self.porcentaje_core.get_derecho_porcentaje_vigente()
        if not derecho:
            raise HttpError(400, "No hay DerechoPorcentajeObra vigente")

        # Step 5: Motor único (sin acceso a BD: el contexto llega resuelto)
        contexto = CotizacionPOContexto(
            estrategia=estrategia,
            participantes=tarifas_aplicadas,
            count_habilitadas=count_habilitadas,
            valor_declarado=valor_declarado,
            total_explicito=total_explicito,
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            uit_valor=Decimal(str(uit_vigente.valor)),
            derecho=self.porcentaje_core.derecho_a_contexto(derecho),
        )
        cotizacion = self.porcentaje_core.calcular_cotizacion_po_estrategia(contexto)

        # Step 6: Build result
        return self._build_cotizacion_result(cotizacion)

    # ── Resolución del contexto de cotización (compartida por preview y create) ──

    @staticmethod
    def _resolver_datos_estrategia(estrategia_in):
        """
        Devuelve (valor_declarado, total_explicito) según la estrategia del payload.

        En TOTAL_EXPLICITO el total con IGV es autoritativo para el cálculo y el
        valor declarado se conserva sólo como información de la obra.
        """
        if estrategia_in.estrategia_cotizacion == EstrategiaCotizacionPO.TOTAL_EXPLICITO:
            return (
                estrategia_in.datos.valor_declarado,
                estrategia_in.datos.total_explicito,
            )
        return estrategia_in.datos.valor_declarado, None

    def _resolver_tarifas_aplicadas(
        self,
        input_tarifas: List[LiquidacionPorcentajeObraTarifaIn],
    ) -> List[TarifaPorcentajeObraAplicada]:
        """
        Resolución híbrida de tarifas → participantes de la cotización.

        - `tarifas` vacío: auto-fill con las tarifas vigentes × especialidades vigentes.
        - `tarifas` con elementos: se validan explícitamente (vigencia + tipo).

        With tarifa-unica-especialidades: la especialidad se toma SIEMPRE del input
        (el modelo de tarifa única ya no tiene FK a especialidad).
        """
        payload_tarifas_ids = list(
            dict.fromkeys(str(t.tarifa_porcentaje_obra_id) for t in input_tarifas)
        )
        tarifas = self.porcentaje_core.resolver_tarifas(
            payload_tarifas_ids, TipoLiquidacion.EDIFICACION
        )

        # Validate explicit mode
        if payload_tarifas_ids:
            for tarifa in tarifas:
                self._validar_tarifa_explicita(tarifa, TipoLiquidacion.EDIFICACION)

        if not tarifas:
            raise HttpError(400, "No hay tarifas vigentes para edificaciones")

        # Build a map of tarifa_id -> ORM object for quick lookup
        tarifa_map = {str(t.id): t for t in tarifas}

        if input_tarifas:
            especialidad_nombres = {
                str(esp.id): esp.nombre
                for esp in EspecialidadRevision.objects.filter(
                    id__in=[t.especialidad_id for t in input_tarifas]
                )
            }
            return [
                TarifaPorcentajeObraAplicada(
                    tarifa_id=str(t.tarifa_porcentaje_obra_id),
                    porcentaje_liquidacion=tarifa_map[
                        str(t.tarifa_porcentaje_obra_id)
                    ].porcentaje_liquidacion,
                    especialidad_id=str(t.especialidad_id),
                    especialidad_nombre=especialidad_nombres.get(str(t.especialidad_id)),
                )
                for t in input_tarifas
            ]

        # Auto-fill: combine one tarifa per base x every vigente especialidad.
        # In tarifa-unica design there is ONE tarifa per TarifaLiquidacionBase/periodo,
        # so deduplicate by tarifa_base to avoid duplicate (liquidacion_porcentaje, especialidad).
        especialidades = self._obtener_especialidades_vigentes_para_tipo(
            TipoLiquidacion.EDIFICACION
        )
        tarifas_dedup = list({t.tarifa_base_id: t for t in tarifas}.values())
        return [
            TarifaPorcentajeObraAplicada(
                tarifa_id=str(t.id),
                porcentaje_liquidacion=t.porcentaje_liquidacion,
                especialidad_id=str(esp.especialidad_id),
                especialidad_nombre=esp.especialidad.nombre if esp.especialidad else None,
            )
            for t in tarifas_dedup
            for esp in especialidades
        ]

    def _resolver_count_habilitadas(
        self, estrategia: str, fecha: Optional[date] = None
    ) -> Optional[int]:
        """
        Resuelve H (habilitadas del catálogo) para la fecha efectiva.

        H es el UNIVERSO DE COBRO: nunca se deduce de los participantes, porque
        si se dedujera n == H y la diferencia nunca se acumularía. En creación y
        preview la fecha efectiva es hoy; en edición la resuelve el snapshot
        persistido o la fecha de registro (Module 5).

        - En TARIFA_HABILITADAS_PARTICIPANTES y TOTAL_EXPLICITO el catálogo DEBE
          tener habilitadas: sin H el modo no es calculable (400).
        - En NORMAL_SELECCIONADAS H es sólo informativo (el padre cobra las
          seleccionadas) y su ausencia NO invalida la operación: se deja NULL.
        """
        habilitadas = self._obtener_especialidades_vigentes_para_tipo(
            TipoLiquidacion.EDIFICACION, fecha=fecha
        )
        if not habilitadas:
            if estrategia == EstrategiaCotizacionPO.NORMAL_SELECCIONADAS:
                return None
            raise HttpError(
                400,
                "No hay especialidades habilitadas vigentes para edificaciones",
            )
        return len(habilitadas)

    def _resolver_habilitadas_edicion(self, liq_po, fecha: date) -> Optional[int]:
        """
        Resuelve H para un camino de EDICIÓN (fecha efectiva = fecha_registro).

        Contrato de snapshot/catálogo, en este orden:

        1. el SNAPSHOT persistido (`count_habilitadas`): es el H con el que se
           cobró la liquidación y no depende de que el catálogo cambie después;
        2. el CATÁLOGO de habilitadas vigentes en la fecha efectiva (para los
           registros históricos creados antes del snapshot).

        NUNCA se deduce de los participantes: si H fuera n, la diferencia nunca
        se acumularía y la estrategia TARIFA_HABILITADAS_PARTICIPANTES sería
        indistinguible de NORMAL_SELECCIONADAS.
        """
        snapshot = getattr(liq_po, "count_habilitadas", None)
        if snapshot:
            return snapshot
        return self._resolver_count_habilitadas(
            EstrategiaCotizacionPO.NORMAL_SELECCIONADAS, fecha=fecha
        )

    @staticmethod
    def _build_cotizacion_result(
        cotizacion: CotizacionPOEstrategiaData,
    ) -> CotizacionPorcentajeObraResult:
        """Proyecta el resultado del motor único al DTO de cotización de la API."""
        acumulacion = cotizacion.acumulacion
        return CotizacionPorcentajeObraResult(
            valor_declarado=cotizacion.valor_declarado,
            porcentaje_liquidacion=cotizacion.porcentaje_liquidacion,
            derecho_minimo=cotizacion.derecho_minimo,
            derecho_maximo=cotizacion.derecho_maximo,
            porcentaje_minimo_uit=cotizacion.porcentaje_minimo_uit,
            derecho_aplicado_id=cotizacion.derecho_aplicado_id,
            estrategia_cotizacion=str(cotizacion.estrategia),
            count_habilitadas=cotizacion.count_habilitadas,
            total_explicito=cotizacion.total_explicito,
            porcentaje_tarifa=cotizacion.porcentaje_tarifa,
            acumulacion=(
                AcumulacionPorcentajeObraResult(
                    porcentaje_acumulado=acumulacion.porcentaje_acumulado,
                    subtotal_acumulado=acumulacion.subtotal_acumulado,
                )
                if acumulacion is not None
                else None
            ),
            detalles=[
                CotizacionPorcentajeObraDetalleResult(
                    tarifa_id=d.tarifa_aplicada.tarifa_id,
                    especialidad=EspecialidadResult(
                        id=d.tarifa_aplicada.especialidad_id,
                        nombre=d.tarifa_aplicada.especialidad_nombre or "",
                    ) if d.tarifa_aplicada.especialidad_id else None,
                    porcentaje_aplicado=d.porcentaje_aplicado,
                    subtotal=d.subtotal,
                )
                for d in cotizacion.detalles
            ],
            total_subtotal=cotizacion.total_subtotal,
            total=cotizacion.total,
        )

    def listar_liquidaciones(
        self, page: int, page_size: int,
        municipalidad_id=None,
        propietario=None,
        razon_social=None,
        creador_username=None,
        fecha_desde=None,
        fecha_hasta=None,
        numero=None,
        numero_revision=None,
        direccion=None,
        documento=None,
        expediente=None,
    ) -> tuple[List[LiquidacionEspecificaPrimeraRevisionResult], int]:
        """
        Returns paginated LiquidacionEspecificaPrimeraRevisionResult list.
        Applies pagination defaults/boundaries, iterates ORM objects to build domain DTOs.
        Returns (List[LiquidacionEspecificaPrimeraRevisionResult], total_count).
        """
        # Pagination boundary defaults
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.general_core.list_liquidaciones_by_type_paginated(
            tipo_liquidacion=TipoLiquidacion.EDIFICACION,
            page=page,
            page_size=page_size,
            municipalidad_id=municipalidad_id,
            propietario=propietario,
            razon_social=razon_social,
            creador_username=creador_username,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            numero=numero,
            numero_revision=numero_revision,
            direccion=direccion,
            documento=documento,
            expediente=expediente,
        )

        # Build LiquidacionEspecificaPrimeraRevisionResult domain DTOs from ORM objects
        domain_results: List[LiquidacionEspecificaPrimeraRevisionResult] = []
        for lg in orm_objects:
            domain_results.append(self._build_edificaciones_result(lg))

        return domain_results, total

    def _build_edificaciones_result(self, lg) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Maps a LiquidacionGeneral ORM object to LiquidacionEspecificaPrimeraRevisionResult domain DTO.

        Delegates LiquidacionGeneralResult construction to general_core.build_general_result().
        Only the type-specific fields (edificaciones, liquidacion_porcentaje_obra) are built here.
        """
        from modules.liquidaciones.domain.results.liquidacion_especifico.primera_revision_result import (
            LiquidacionEspecificaResult,
        )
        from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_porcentaje_result import (
            LiquidacionPorcentajeObraResult,
            DetallePorcentajeObraResult,
            EspecialidadResult,
        )

        # Delegate general result construction to core (NO more duplicate inline mapping)
        usuario_id = lg.usuario_creador.id if lg.usuario_creador else 0

        # Build contacto_result from lg.contacto (same pattern as Flujo)
        contacto_result = None
        if lg.contacto:
            contacto_result = ContactoResult(
                id=str(lg.contacto.id),
                nombres=lg.contacto.nombres,
                apellidos=lg.contacto.apellidos,
                dni=lg.contacto.dni,
                cargo=lg.contacto.cargo,
                telefono=lg.contacto.telefono,
                celular=lg.contacto.celular,
                email=lg.contacto.email,
            )

        general_result = self.general_core.build_general_result(
            lg,
            usuario_id=usuario_id,
            contacto_result=contacto_result,
            codigo_cta=self.general_core.get_codigo_cta(lg.tipo_liquidacion),
        )

        # Type-specific: Edificaciones
        edificacion = lg.edificaciones
        especifica_result = LiquidacionEspecificaResult(
            id=str(edificacion.id),
            numero=edificacion.numero,
        )

        lpo = lg.liquidacion_porcentaje_obra
        tipo_result = LiquidacionPorcentajeObraResult(
            id=str(lpo.id),
            liquidacion_general_id=str(lpo.liquidacion_general_id),
            tipo_tramite=lpo.tipo_tramite,
            valor_declarado=lpo.valor_declarado,
            porcentaje_liquidacion=lpo.porcentaje_liquidacion,
            derecho_minimo=lpo.derecho_minimo,
            derecho_maximo=lpo.derecho_maximo,
            porcentaje_minimo_uit=lpo.porcentaje_minimo_uit,
            derecho_aplicado_id=str(lpo.derecho_aplicado_id) if lpo.derecho_aplicado_id else None,
            estrategia_cotizacion=lpo.estrategia_cotizacion,
            count_habilitadas=lpo.count_habilitadas,
            total_explicito=lpo.total_explicito,
            porcentaje_tarifa=lpo.porcentaje_tarifa,
            tarifa_aplicada_id=str(lpo.tarifa_aplicada_id) if lpo.tarifa_aplicada_id else None,
            acumulacion=self._acumulacion_result(lpo),
            detalles=[
                DetallePorcentajeObraResult(
                    id=str(d.id),
                    tarifa_aplicada_id=str(d.tarifa_aplicada_id) if d.tarifa_aplicada_id else None,
                    especialidad=EspecialidadResult(
                        id=str(d.especialidad_id),
                        nombre=getattr(d.especialidad, 'nombre', '') or '',
                    ) if d.especialidad_id else None,
                    porcentaje_aplicado=d.porcentaje_aplicado,
                    subtotal=d.subtotal,
                )
                for d in lpo.detalles.all()
            ],
        )

        return LiquidacionEspecificaPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_especifica=especifica_result,
            liquidacion_tipo=tipo_result,
        )

    @staticmethod
    def _acumulacion_result(lpo) -> Optional[AcumulacionPorcentajeObraResult]:
        """Proyecta la fila de acumulación vigente del PO (None si no hay diferencia)."""
        try:
            acumulacion = lpo.acumulacion
        except ObjectDoesNotExist:
            return None
        return AcumulacionPorcentajeObraResult(
            porcentaje_acumulado=acumulacion.porcentaje_acumulado,
            subtotal_acumulado=acumulacion.subtotal_acumulado,
        )

    def obtener_liquidacion(self, liquidacion_id: uuid.UUID) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Returns a single LiquidacionEspecificaPrimeraRevisionResult for Edificaciones by UUID.
        Raises LiquidacionNotFoundError if not found.
        """
        try:
            lg = self.general_core.get_liquidacion_edificaciones_by_id(liquidacion_id)
            return self._build_edificaciones_result(lg)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError("Liquidación no encontrada.")

    def crear_nueva_revision_proceso(
        self,
        usuario_id: int,
        payload_in,
        liquidacion_previa_id: uuid.UUID,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Validates and creates a new revision for an existing Edificaciones liquidacion.

        Validations:
        - liquidacion_previa_id exists and is Edificaciones
        - Same proyecto as previa
        - Tarifas vigentes

        `numero_revision` comes from the client (validated against {1, 3, 5} and
        MAX_REVISIONES by the input contract). The backend never derives it from
        the previa and never rejects a repeated revision number: several liquidaciones
        may be active siblings sharing the same revision number.
        """
        # Step 1: Validate liquidacion_previa exists and is Edificaciones
        try:
            previa = self.general_core.get_liquidacion_edificaciones_by_id(liquidacion_previa_id)
        except ObjectDoesNotExist:
            raise HttpError(404, "Liquidación previa no encontrada.")

        proyecto = previa.proyecto
        previa_po = previa.liquidacion_porcentaje_obra

        # Step 2: Same proyecto (already implicit since we're using previa's proyecto)

        # Step 3: Estrategia de la nueva revisión.
        # Se HEREDA de la previa salvo que el payload declare otra (una revisión
        # puede cambiar de estrategia). Los datos que exige la estrategia se
        # heredan de la previa y sólo se sustituyen si el payload los envía.
        estrategia = (
            payload_in.liquidacion_especifica.estrategia_cotizacion
            or previa_po.estrategia_cotizacion
            or EstrategiaCotizacionPO.NORMAL_SELECCIONADAS
        )
        datos_in = payload_in.liquidacion_especifica.datos
        if estrategia == EstrategiaCotizacionPO.TOTAL_EXPLICITO:
            valor_declarado = (
                datos_in.valor_declarado
                if datos_in is not None and datos_in.valor_declarado is not None
                else previa_po.valor_declarado
            )
            total_explicito = (
                datos_in.total_explicito
                if datos_in is not None and datos_in.total_explicito is not None
                else previa_po.total_explicito
            )
            if total_explicito is None or total_explicito <= 0:
                raise HttpError(400, "total_explicito debe ser mayor a 0")
        else:
            total_explicito = None
            valor_declarado = previa_po.valor_declarado
            if datos_in is not None and datos_in.valor_declarado is not None:
                if datos_in.valor_declarado > 0:
                    valor_declarado = datos_in.valor_declarado
            if valor_declarado is None or valor_declarado <= 0:
                raise HttpError(400, "valor_declarado debe ser mayor a 0")

        if valor_declarado is None or valor_declarado <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")

        # Step 4: Resolve tarifas (same as primera revision)
        # With tarifa-unica-especialidades: each input entry brings its own
        # especialidad_id (from LiquidacionEspecialidadDisponibles).
        # NOTA: nueva revision NO auto-completa — exige tarifas explicitas del frontend.
        input_tarifas = payload_in.liquidacion_especifica.tarifas
        if not input_tarifas:
            raise HttpError(400, "Debe especificar al menos una tarifa en la nueva revisión")

        payload_tarifas_ids = list(dict.fromkeys(str(t.tarifa_porcentaje_obra_id) for t in input_tarifas))
        tarifas = self.porcentaje_core.resolver_tarifas(payload_tarifas_ids, TipoLiquidacion.EDIFICACION)

        if payload_tarifas_ids:
            for tarifa in tarifas:
                self._validar_tarifa_explicita(tarifa, TipoLiquidacion.EDIFICACION)

        if not tarifas:
            raise HttpError(400, "No hay tarifas vigentes para edificaciones")

        # Build a map of tarifa_id -> ORM object for quick lookup
        tarifa_map = {str(t.id): t for t in tarifas}

        # Step 5: Get vigente IGV, UIT and derecho
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        if not igv_vigente or not uit_vigente:
            raise HttpError(400, "No hay IGV o UIT vigente configurado")

        derecho = self.porcentaje_core.get_derecho_porcentaje_vigente()
        if not derecho:
            raise HttpError(400, "No hay DerechoPorcentajeObra vigente")

        # Step 6: H del catálogo — la nueva revisión se registra HOY, su fecha
        # efectiva es hoy (IGV/UIT/derechos de hoy, igual que la creación).
        count_habilitadas = self._resolver_count_habilitadas(estrategia)

        # Step 7: Build domain DTOs with explicit especialidad from INPUT
        tarifas_aplicadas = [
            TarifaPorcentajeObraAplicada(
                tarifa_id=str(t.tarifa_porcentaje_obra_id),
                porcentaje_liquidacion=tarifa_map[str(t.tarifa_porcentaje_obra_id)].porcentaje_liquidacion,
                especialidad_id=str(t.especialidad_id),
                especialidad_nombre=None,
            )
            for t in input_tarifas
        ]

        domain_data = LiquidacionEspecificaPrimeraRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(previa.municipalidad_id),
                expediente=payload_in.liquidacion_general.expediente or previa.expediente,
                observacion=payload_in.liquidacion_general.observacion,
                denominacion_de_proyecto=payload_in.liquidacion_general.denominacion_de_proyecto
                if payload_in.liquidacion_general.denominacion_de_proyecto is not None
                else previa.denominacion_de_proyecto,
                numero_revision=payload_in.numero_revision,
                proyecto=ProyectoData(
                    nombre_propietario=proyecto.nombre_propietario,
                    direccion=proyecto.direccion,
                    distrito_id=str(proyecto.distrito_id) if proyecto.distrito_id else None,
                    entidad_razon_social=proyecto.entidad_razon_social,
                    entidad=EntidadData(
                        tipo_documento=proyecto.entidad_tipo_documento,
                        numero_documento=proyecto.entidad_numero_documento,
                    ),
                ),
                contacto=(
                    ContactoData(
                        nombres=payload_in.liquidacion_general.contacto.nombres,
                        apellidos=payload_in.liquidacion_general.contacto.apellidos,
                        dni=payload_in.liquidacion_general.contacto.dni,
                        cargo=payload_in.liquidacion_general.contacto.cargo,
                        telefono=payload_in.liquidacion_general.contacto.telefono,
                        celular=payload_in.liquidacion_general.contacto.celular,
                        email=payload_in.liquidacion_general.contacto.email,
                    )
                    if payload_in.liquidacion_general.contacto
                    else None
                ),
            ),
            liquidacion_especifica=LiquidacionPorcentajeObraData(
                datos=DatosPorcentajeObra(valor_declarado=valor_declarado),
                tarifas=tarifas_aplicadas,
                tipo_tramite=payload_in.liquidacion_especifica.tipo_tramite,
                estrategia_cotizacion=estrategia,
                count_habilitadas=count_habilitadas,
                total_explicito=total_explicito,
            ),
        )

        # Step 7: Delegate to Flujo with the previous liquidacion (transient reference)
        return self.flujo.ejecutar_nueva_revision(
            usuario_id=usuario_id,
            data=domain_data,
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            derecho=derecho,
            uit_valor=Decimal(str(uit_vigente.valor)),
            liquidacion_previa=previa,
        )

    def recalcular_po(
        self,
        liquidacion_id: uuid.UUID,
        valor_declarado=None,
        tarifas=None,
        liquidacion_general=None,
        liquidacion_tipo=None,
    ):
        """
        PATCH recalculation for Edificaciones (PO motor).

        Supports two input formats:
        1. Flat (legacy): valor_declarado + tarifas directly
        2. Wrapper (current): liquidacion_general + liquidacion_tipo

        If liquidacion_general is provided, calls general update orchestrator.
        If liquidacion_tipo is provided, delegates to LiquidacionPatchPorcentajeObraService.
        Both can be provided in one call for atomic update.

        Soporta las TRES estrategias de cotización (Module 5):

        - la estrategia persistida es la que se recalcula cuando el payload no
          declara otra (modo "preservar");
        - si el payload declara otra estrategia, se TRANSICIONA: se recalcula
          con el motor único, se reemplazan los detalles y sus snapshots, y la
          fila de acumulación se crea, actualiza o elimina según la diferencia;
        - la fecha efectiva es siempre `fecha_registro`: IGV, UIT y derechos se
          resuelven a esa fecha (histórico).

        Args:
            liquidacion_id: UUID of the LiquidacionGeneral to recalculate.
            valor_declarado: New valor_declarado (flat format, None = preserve current).
            tarifas: List of TarifaPatchInput (flat format, None = preserve current).
            liquidacion_general: Optional dict with general fields (wrapper format).
            liquidacion_tipo: Optional dict with tipo fields (wrapper format).

        Returns:
            LiquidacionEspecificaPrimeraRevisionResult with updated values.

        Raises:
            LiquidacionNotFoundError: If liquidacion not found.
            ConflictError: If estado == PAGADA.
        """
        from django.db import transaction
        from core.exceptions import ConflictError
        from modules.liquidaciones.domain.constants import EstadoLiquidacion
        from modules.liquidaciones.domain.services.core.liquidacion_patch_porcentaje_obra_service import (
            LiquidacionPatchPorcentajeObraService,
            PatchPorcentajeObraInput,
            TarifaPatchInput,
        )

        # 1. Fetch the liquidacion
        try:
            lg = self.general_core.get_liquidacion_edificaciones_by_id(liquidacion_id)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError("Liquidación no encontrada.")

        # 2. Guard: only PENDIENTE allows updates (applies to BOTH general and tipo)
        if lg.estado == EstadoLiquidacion.PAGADA:
            raise ConflictError(
                message="No se puede editar una liquidación en estado PAGADA.",
                code="LIQUIDACION_PAGADA_NOT_EDITABLE",
            )

        # 3. Handle wrapper format: extract from liquidacion_general + liquidacion_tipo
        tipo_tramite = None  # PO-only field
        estrategia_solicitada = None
        total_explicito = None
        if liquidacion_tipo is not None:
            # Wrapper format: extract from nested structure
            tipo_datos = liquidacion_tipo.get("datos") or {}
            tipo_tarifas = liquidacion_tipo.get("tarifas")
            # Map wrapper field names to flat format
            vd = tipo_datos.get("valor_declarado", valor_declarado)
            tipo_tramite = (
                liquidacion_tipo.get("tipo_tramite")
                or tipo_datos.get("tipo_tramite")
            )  # PO-only: preserve or update
            estrategia_solicitada = liquidacion_tipo.get("estrategia_cotizacion")
            total_explicito = tipo_datos.get("total_explicito")
            # Map wrapper tarifa field names (tarifa_porcentaje_obra_id -> tarifa_id)
            if tipo_tarifas is not None:
                tarifas_input = [
                    TarifaPatchInput(
                        tarifa_id=str(t.get("tarifa_porcentaje_obra_id") or t.get("tarifa_id")),
                        especialidad_id=str(t["especialidad_id"]),
                    )
                    for t in tipo_tarifas
                ]
            else:
                tarifas_input = tarifas
        else:
            # Flat format: use params directly
            vd = valor_declarado
            if tarifas is not None:
                tarifas_input = [
                    TarifaPatchInput(tarifa_id=str(t.tarifa_id), especialidad_id=str(t.especialidad_id))
                    for t in tarifas
                ]
            else:
                tarifas_input = None

        # 4. Execute updates in a single transaction
        patch_service = LiquidacionPatchPorcentajeObraService()
        with transaction.atomic():
            # 4a. Row lock (SELECT ... FOR UPDATE) at the EARLIEST boundary of the
            # transaction: two concurrent PATCH calls on the same liquidacion are
            # serialized, so the second one never writes stale details on top of
            # the first one's commit. The lock is taken INSIDE the transaction
            # opened here (this orchestrator owns it; the core service never
            # opens one — django-app-architecture-contract.md §4.3).
            lg = patch_service.bloquear_liquidacion_general(lg)

            # 4b. Update general fields if provided
            # Pass lg directly to avoid re-fetch which creates stale reference bug
            # when combined with tipo update (Bug #general-wrapper-bug)
            if liquidacion_general is not None:
                self.general_orchestrator.actualizar_liquidacion_general_proyecto_municipalidad(
                    liquidacion=lg,
                    expediente=liquidacion_general.get("expediente"),
                    observacion=liquidacion_general.get("observacion"),
                    municipalidad_id=liquidacion_general.get("municipalidad_id"),
                    proyecto_data=liquidacion_general.get("proyecto"),
                    denominacion_de_proyecto=liquidacion_general.get("denominacion_de_proyecto"),
                    contacto_data=liquidacion_general.get("contacto"),
                    numero_revision=liquidacion_general.get("numero_revision"),
                )

            # 4c. Update tipo fields if provided
            requiere_recalculo = (
                vd is not None
                or total_explicito is not None
                or tarifas_input is not None
                or tipo_tramite is not None
                or estrategia_solicitada is not None
            )
            if requiere_recalculo:
                # Guard explícito de MANUAL (edge): el servicio de patch lo
                # levanta con 409 (no es recalculable por tarifa). Se comprueba
                # ANTES de resolver la estrategia para que el error sea el del
                # guard y no un 400 de datos.
                patch_service.verificar_editable(lg)

                estrategia, valor_efectivo, total_efectivo = self._resolver_estrategia_patch(
                    lg=lg,
                    estrategia_solicitada=estrategia_solicitada,
                    valor_declarado=vd,
                    total_explicito=total_explicito,
                )
                patch_input = PatchPorcentajeObraInput(
                    valor_declarado=valor_efectivo,
                    tarifas=tarifas_input,
                    tipo_tramite=tipo_tramite,
                    estrategia=estrategia,
                    total_explicito=total_efectivo,
                    count_habilitadas=self._resolver_habilitadas_patch(lg),
                )
                patch_service.recalcular(lg, patch_input)

        # 5. Refresh and return built result
        lg.refresh_from_db()
        return self._build_edificaciones_result(lg)

    def _resolver_estrategia_patch(
        self,
        lg,
        estrategia_solicitada: Optional[str],
        valor_declarado,
        total_explicito,
    ):
        """
        Resuelve la estrategia efectiva del PATCH y sus datos de entrada.

        Devuelve `(estrategia, valor_declarado, total_explicito)`:

        - la estrategia es la solicitada o, si no se declara, la PERSISTIDA
          (modo "preservar": recalcular lo mismo con los valores históricos);
        - todas las estrategias conservan el valor declarado; TOTAL_EXPLICITO
          además usa el total final autoritativo para el cálculo;
        - lo que el payload omite se preserva del PO persistido.

        Mezclar campos de estrategias es un error de negocio (400) y no se
        escribe nada: la transacción del orchestrator se revierte.
        """
        liq_po = self._po_de_edificaciones(lg)
        persistida = getattr(liq_po, "estrategia_cotizacion", None) or (
            EstrategiaCotizacionPO.NORMAL_SELECCIONADAS
        )
        estrategia = estrategia_solicitada or persistida

        if estrategia == EstrategiaCotizacionPO.TOTAL_EXPLICITO:
            valor_resuelto = (
                valor_declarado
                if valor_declarado is not None
                else getattr(liq_po, "valor_declarado", None)
            )
            if valor_resuelto is None or valor_resuelto <= 0:
                raise HttpError(400, "valor_declarado debe ser mayor a 0")
            total_resuelto = (
                total_explicito
                if total_explicito is not None
                else getattr(liq_po, "total_explicito", None)
            )
            if total_resuelto is None or total_resuelto <= 0:
                raise HttpError(400, "total_explicito debe ser mayor a 0")
            return estrategia, valor_resuelto, total_resuelto

        if total_explicito is not None:
            raise HttpError(
                400,
                "total_explicito sólo aplica en la estrategia TOTAL_EXPLICITO.",
            )

        valor_resuelto = (
            valor_declarado
            if valor_declarado is not None
            else getattr(liq_po, "valor_declarado", None)
        )
        if valor_resuelto is None or valor_resuelto <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")
        return estrategia, valor_resuelto, None

    @staticmethod
    def _po_de_edificaciones(lg):
        """Devuelve el registro PO de la liquidación (None si no existe)."""
        try:
            return lg.liquidacion_porcentaje_obra
        except ObjectDoesNotExist:
            return None

    def _resolver_habilitadas_patch(self, lg) -> Optional[int]:
        """
        H para el PATCH: snapshot persistido primero, catálogo en la fecha
        efectiva como respaldo (contrato de snapshot/catálogo).

        NUNCA se deduce de los participantes.
        """
        fecha = lg.fecha_registro.date()
        return self._resolver_habilitadas_edicion(self._po_de_edificaciones(lg), fecha)

    def cotizar_edicion_proceso(
        self,
        liquidacion_id: uuid.UUID,
        payload_in: "LiquidacionEdificacionesCotizarEdicionIn",
    ) -> "CotizacionPorcentajeObraResult":
        """
        Read-only quote for editing an existing Edificaciones liquidacion.

        Usa el MISMO motor único que el preview de creación y que el PATCH:
        `cotizar-edicion` y el guardado producen las mismas cifras.

        Fecha efectiva: `LiquidacionGeneral.fecha_registro.date()` — el IGV, la
        UIT y los derechos se resuelven a esa fecha (histórico), nunca a hoy.
        H (habilitadas) se resuelve con el contrato de snapshot/catálogo.

        Does NOT persist any changes (la acumulación es efímera: el preview
        nunca la persiste).

        Args:
            liquidacion_id: UUID of the existing LiquidacionGeneral.
            payload_in: Typed wrapper con la union discriminado de estrategias.

        Returns:
            CotizacionPorcentajeObraResult con la cotización, la estrategia,
            sus snapshots y la acumulación efímera.

        Raises:
            LiquidacionNotFoundError: If liquidacion not found.
        """
        from django.core.exceptions import ObjectDoesNotExist
        from modules.liquidaciones.domain.services.core.liquidacion_cotizar_edicion_service import (
            LiquidacionCotizarEdicionPOService,
            CotizarEdicionPOEstrategiaInput,
            CotizarEdicionPOTarifaInput,
        )

        # 1. Fetch the liquidacion
        try:
            lg = self.general_core.get_liquidacion_edificaciones_by_id(liquidacion_id)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError("Liquidación no encontrada.")

        # 2. Extract fields from the discriminated union
        estrategia_in = payload_in.liquidacion_tipo
        estrategia = estrategia_in.estrategia_cotizacion
        valor_declarado, total_explicito = self._resolver_datos_estrategia(
            estrategia_in
        )

        if valor_declarado is None or valor_declarado <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")
        if (
            estrategia == EstrategiaCotizacionPO.TOTAL_EXPLICITO
            and (total_explicito is None or total_explicito <= 0)
        ):
            raise HttpError(400, "total_explicito debe ser mayor a 0")

        # 3. Fecha efectiva = fecha de registro (IGV/UIT/derechos históricos)
        fecha = lg.fecha_registro.date()

        # 4. H por el contrato de snapshot/catálogo (nunca desde los participantes)
        try:
            liq_po = lg.liquidacion_porcentaje_obra
        except ObjectDoesNotExist:
            # Sin registro PO no hay cotización que editar: lo rechaza el
            # servicio de cotizar-edición con su error de dominio.
            liq_po = None
        count_habilitadas = self._resolver_habilitadas_edicion(liq_po, fecha)
        if (
            estrategia != EstrategiaCotizacionPO.NORMAL_SELECCIONADAS
            and count_habilitadas is None
        ):
            raise HttpError(
                400,
                "No hay especialidades habilitadas vigentes para edificaciones",
            )

        # 5. Participantes cotizados (obligatorios en edición)
        tarifas_input = [
            CotizarEdicionPOTarifaInput(
                tarifa_id=str(t.tarifa_porcentaje_obra_id),
                especialidad_id=str(t.especialidad_id),
            )
            for t in estrategia_in.tarifas
        ]
        if not tarifas_input:
            raise HttpError(400, "Se requiere al menos una tarifa para cotizar la liquidacion.")

        patch_input = CotizarEdicionPOEstrategiaInput(
            estrategia=estrategia,
            valor_declarado=valor_declarado,
            total_explicito=total_explicito,
            tarifas=tarifas_input,
            count_habilitadas=count_habilitadas,
        )

        # 6. Quote (read-only, no DB mutation)
        quote_service = LiquidacionCotizarEdicionPOService()
        cotizacion = quote_service.cotizar_edicion_estrategia(lg, patch_input)
        return self._build_cotizacion_result(cotizacion)

    def crear_relacionada_proceso(
        self,
        usuario_id: int,
        payload_in,
        liquidacion_previa_id: uuid.UUID,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Validates and creates a related liquidacion for an existing Edificaciones
        liquidacion.

        The new liquidacion joins the relation group of the previous one, using the
        `numero_revision` chosen by the client (validated against {1, 3, 5} and
        MAX_REVISIONES by the input contract).

        Validations:
        - liquidacion_previa_id exists and is Edificaciones
        - Same validation as primera_revision (tarifas vigentes, IGV/UIT, etc.)
        """
        # Step 1: Validate liquidacion_previa exists and is Edificaciones
        try:
            previa = self.general_core.get_liquidacion_edificaciones_by_id(liquidacion_previa_id)
        except ObjectDoesNotExist:
            raise HttpError(404, "Liquidación previa no encontrada.")

        # Step 2: Estrategia de la relacionada (union discriminado). Una
        # relacionada es un input COMPLETO: sus valores son los de hoy.
        estrategia_in = payload_in.liquidacion_especifica
        estrategia = estrategia_in.estrategia_cotizacion
        valor_declarado, total_explicito = self._resolver_datos_estrategia(estrategia_in)
        if valor_declarado is None or valor_declarado <= 0:
            raise HttpError(400, "valor_declarado debe ser mayor a 0")
        if (
            estrategia == EstrategiaCotizacionPO.TOTAL_EXPLICITO
            and (total_explicito is None or total_explicito <= 0)
        ):
            raise HttpError(400, "total_explicito debe ser mayor a 0")

        # Step 3: Hybrid resolution
        input_tarifas = estrategia_in.tarifas
        payload_tarifas_ids = list(dict.fromkeys(str(t.tarifa_porcentaje_obra_id) for t in input_tarifas))
        tarifas = self.porcentaje_core.resolver_tarifas(payload_tarifas_ids, TipoLiquidacion.EDIFICACION)

        if payload_tarifas_ids:
            for tarifa in tarifas:
                self._validar_tarifa_explicita(tarifa, TipoLiquidacion.EDIFICACION)

        if not tarifas:
            raise HttpError(400, "No hay tarifas vigentes para edificaciones")

        tarifa_map = {str(t.id): t for t in tarifas}

        # Step 4: Get vigente IGV and UIT
        igv_vigente = self.general_core.get_igv_vigente()
        uit_vigente = self.general_core.get_uit_vigente()
        if not igv_vigente or not uit_vigente:
            raise HttpError(400, "No hay IGV o UIT vigente configurado")

        derecho = self.porcentaje_core.get_derecho_porcentaje_vigente()
        if not derecho:
            raise HttpError(400, "No hay DerechoPorcentajeObra vigente")

        # Step 5: H del catálogo (fecha efectiva = hoy, como la creación)
        count_habilitadas = self._resolver_count_habilitadas(estrategia)

        # Step 6: Build domain DTOs with explicit especialidad from INPUT
        if input_tarifas:
            tarifas_aplicadas = [
                TarifaPorcentajeObraAplicada(
                    tarifa_id=str(t.tarifa_porcentaje_obra_id),
                    porcentaje_liquidacion=tarifa_map[str(t.tarifa_porcentaje_obra_id)].porcentaje_liquidacion,
                    especialidad_id=str(t.especialidad_id),
                    especialidad_nombre=None,
                )
                for t in input_tarifas
            ]
        else:
            especialidades = self._obtener_especialidades_vigentes_para_tipo(TipoLiquidacion.EDIFICACION)
            tarifas_dedup = list({t.tarifa_base_id: t for t in tarifas}.values())
            tarifas_aplicadas = [
                TarifaPorcentajeObraAplicada(
                    tarifa_id=str(t.id),
                    porcentaje_liquidacion=t.porcentaje_liquidacion,
                    especialidad_id=str(esp.especialidad_id),
                    especialidad_nombre=esp.especialidad.nombre if esp.especialidad else None,
                )
                for t in tarifas_dedup
                for esp in especialidades
            ]

        domain_data = LiquidacionEspecificaPrimeraRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(payload_in.liquidacion_general.municipalidad_id),
                expediente=payload_in.liquidacion_general.expediente,
                observacion=payload_in.liquidacion_general.observacion,
                denominacion_de_proyecto=payload_in.liquidacion_general.denominacion_de_proyecto,
                numero_revision=payload_in.numero_revision,
                proyecto=ProyectoData(
                    nombre_propietario=payload_in.liquidacion_general.proyecto.nombre_propietario,
                    direccion=payload_in.liquidacion_general.proyecto.direccion,
                    distrito_id=str(payload_in.liquidacion_general.proyecto.distrito_id) if payload_in.liquidacion_general.proyecto.distrito_id else None,
                    entidad_razon_social=payload_in.liquidacion_general.proyecto.entidad.razon_social,
                    entidad=EntidadData(
                        tipo_documento=payload_in.liquidacion_general.proyecto.entidad.tipo_documento,
                        numero_documento=payload_in.liquidacion_general.proyecto.entidad.numero_documento,
                    ),
                ),
                contacto=(
                    ContactoData(
                        nombres=payload_in.liquidacion_general.contacto.nombres,
                        apellidos=payload_in.liquidacion_general.contacto.apellidos,
                        dni=payload_in.liquidacion_general.contacto.dni,
                        cargo=payload_in.liquidacion_general.contacto.cargo,
                        telefono=payload_in.liquidacion_general.contacto.telefono,
                        celular=payload_in.liquidacion_general.contacto.celular,
                        email=payload_in.liquidacion_general.contacto.email,
                    )
                    if payload_in.liquidacion_general.contacto
                    else None
                ),
            ),
            liquidacion_especifica=LiquidacionPorcentajeObraData(
                datos=DatosPorcentajeObra(valor_declarado=valor_declarado),
                tarifas=tarifas_aplicadas,
                tipo_tramite=payload_in.liquidacion_especifica.tipo_tramite,
                estrategia_cotizacion=estrategia,
                count_habilitadas=count_habilitadas,
                total_explicito=total_explicito,
            ),
        )

        # Step 6: Delegate to Flujo with previa for relation group
        return self.flujo.ejecutar_relacionada(
            usuario_id=usuario_id,
            data=domain_data,
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            derecho=derecho,
            uit_valor=Decimal(str(uit_vigente.valor)),
            liquidacion_previa=previa,
        )

    def crear_edge_proceso(
        self,
        usuario_id: int,
        payload_in,
    ) -> LiquidacionEspecificaPrimeraRevisionResult:
        """
        Create an edge (manual) PO liquidacion for Edificaciones.

        Differences from crear_primera_revision_proceso:
        - modo_calculo = MANUAL (explicit)
        - subtotal_manual is pre-IGV; distributed equally among vigente specialties
        - No tarifas, no valor_declarado, no derecho
        - numero_revision is given explicitly (1, 3, or 5)
        - No relation group creation (standalone)
        """
        # Step 1: Validate subtotal_manual > 0
        subtotal_manual = payload_in.subtotal_manual
        if subtotal_manual <= 0:
            raise HttpError(400, "subtotal_manual debe ser mayor a 0")

        # Step 2: Validate numero_revision in {1, 3, 5}
        numero_revision = payload_in.numero_revision
        if numero_revision not in (1, 3, 5):
            raise HttpError(400, "numero_revision debe ser 1, 3 o 5")

        # Step 3: Resolve IGV vigente
        igv_vigente = self.general_core.get_igv_vigente()
        if not igv_vigente:
            raise HttpError(400, "No hay IGV vigente configurado")

        # Step 4: Resolve vigentes/habilitadas specialties for EDIFICACION
        especialidades = self._obtener_especialidades_vigentes_para_tipo(
            TipoLiquidacion.EDIFICACION
        )
        if not especialidades:
            raise HttpError(400, "No hay especialidades vigentes para edificaciones")

        # Step 5: Calculate edge cotizacion (equal distribution, last absorbs remainder)
        cotizacion = self.porcentaje_core.calcular_cotizacion_po_edge(
            subtotal_manual=subtotal_manual,
            especialidades=especialidades,
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
        )

        # Step 6: Build domain DTOs
        domain_data = LiquidacionEspecificaPrimeraRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(payload_in.liquidacion_general.municipalidad_id),
                expediente=payload_in.liquidacion_general.expediente,
                observacion=payload_in.liquidacion_general.observacion,
                denominacion_de_proyecto=payload_in.liquidacion_general.denominacion_de_proyecto,
                proyecto=ProyectoData(
                    nombre_propietario=payload_in.liquidacion_general.proyecto.nombre_propietario,
                    direccion=payload_in.liquidacion_general.proyecto.direccion,
                    distrito_id=str(payload_in.liquidacion_general.proyecto.distrito_id) if payload_in.liquidacion_general.proyecto.distrito_id else None,
                    entidad_razon_social=payload_in.liquidacion_general.proyecto.entidad.razon_social,
                    entidad=EntidadData(
                        tipo_documento=payload_in.liquidacion_general.proyecto.entidad.tipo_documento,
                        numero_documento=payload_in.liquidacion_general.proyecto.entidad.numero_documento,
                    ),
                ),
                contacto=(
                    ContactoData(
                        nombres=payload_in.liquidacion_general.contacto.nombres,
                        apellidos=payload_in.liquidacion_general.contacto.apellidos,
                        dni=payload_in.liquidacion_general.contacto.dni,
                        cargo=payload_in.liquidacion_general.contacto.cargo,
                        telefono=payload_in.liquidacion_general.contacto.telefono,
                        celular=payload_in.liquidacion_general.contacto.celular,
                        email=payload_in.liquidacion_general.contacto.email,
                    )
                    if payload_in.liquidacion_general.contacto
                    else None
                ),
            ),
            liquidacion_especifica=LiquidacionPorcentajeObraData(
                datos=DatosPorcentajeObra(valor_declarado=None),  # null for edge
                tarifas=[],  # empty, not used in edge
            ),
        )

        # Step 7: Delegate to Flujo edge
        return self.flujo.ejecutar_edge(
            usuario_id=usuario_id,
            data=domain_data,
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            numero_revision=numero_revision,
            cotizacion=cotizacion,
        )
