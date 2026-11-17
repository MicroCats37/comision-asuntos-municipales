"""
Orquestador de Inspeccion de Obra.
Mapea los Schemas de Presentacion (Input) hacia los DTOs de Dominio (Data).
Ejecuta el Flujo de forma sincrona.
"""
import uuid
from dataclasses import dataclass
from datetime import date
from typing import List, Optional
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from injector import inject
from ninja.errors import HttpError

from modules.liquidaciones.domain.constants import (
    ModoContinuidadVisitas,
    ModoCotizacionVisitas,
    TipoLiquidacion,
)
from modules.liquidaciones.domain.exceptions import LiquidacionNotFoundError
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionContinuidadVisitas,
)

from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
    LiquidacionInspeccionObraNuevaRevisionInput,
    LiquidacionInspeccionObraCotizarEspecificaIn,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.inspeccion_obra_primera_revision_data import (
    InspeccionObraNuevaRevisionData,
)
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_visitas_data import (
    ContinuidadCreditoVisitas,
    ContinuidadVisitasData,
    ContinuidadVisitasPatchData,
    LiquidacionCategoriaVisitasData,
    DatosVisitas,
    TarifaVisitas,
)
from modules.liquidaciones.domain.schemas.liquidacion_general.liquidacion_general_data import (
    ContactoData,
    LiquidacionGeneralData,
    ProyectoData,
    EntidadData,
)
from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_inspeccion_obra_flujo import (
    LiquidacionInspeccionObraFlujo,
)
from modules.liquidaciones.domain.services.orchestrators.liquidacion_general_orchestrator import (
    LiquidacionGeneralOrchestrator,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.inspeccion_obra_primera_revision_result import (
    InspeccionObraPrimeraRevisionResult,
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    ContactoResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import (
    CotizacionVisitasResult,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_categoria_visitas_core_service import (
    LiquidacionPorCategoriaVisitasCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_continuidad_visitas_core_service import (
    LiquidacionContinuidadVisitasCoreService,
    quantize_money,
)
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_historico_core_service import (
    LiquidacionHistoricoCoreService,
)
from modules.liquidaciones.domain.schemas.liquidacion_legacy.legacy_registro_data import (
    LegacyRegistroContexto,
)
from modules.liquidaciones.domain.services.orchestrators._shared.legacy_registro_resolution import (
    LegacyRegistroResolutionMixin,
)


@dataclass
class _TransicionContinuidad:
    """
    Resolución interna de una transición de continuidad del PATCH de IO.

    - `modo`: la transición solicitada (activar / mantener / desactivar).
    - `continuidad`: la fila de continuidad PERSISTIDA antes de la transición
      (None si la IO no tenía continuidad).
    - `datos`: el bloque de continuidad ya validado y normalizado (None en el
      modo `desactivar`, que no necesita crédito).
    """

    modo: ModoContinuidadVisitas
    continuidad: Optional[LiquidacionContinuidadVisitas]
    datos: Optional[ContinuidadVisitasData]


class LiquidacionInspeccionObraOrchestrator(LegacyRegistroResolutionMixin):
    @inject
    def __init__(
        self,
        flujo: LiquidacionInspeccionObraFlujo,
        visitas_core: LiquidacionPorCategoriaVisitasCoreService,
        general_core: LiquidacionGeneralCoreService,
        general_orchestrator: LiquidacionGeneralOrchestrator,
        historico_core: LiquidacionHistoricoCoreService,
        continuidad_core: LiquidacionContinuidadVisitasCoreService,
    ):
        self.flujo = flujo
        self.visitas_core = visitas_core
        self.general_core = general_core
        self.general_orchestrator = general_orchestrator
        self.historico_core = historico_core
        self.continuidad_core = continuidad_core

    def cotizar_proceso(
        self,
        especifica: "LiquidacionInspeccionObraCotizarEspecificaIn",
        fecha: Optional[date] = None,
    ) -> CotizacionVisitasResult:
        """
        Preview de cotización de IO por MODO. Does NOT persist.

        Resuelve EXACTAMENTE el mismo contexto que la creación (tarifa, UIT,
        IGV y crédito) y ejecuta el MOTOR ÚNICO: preview y guardado producen
        las mismas cifras.

        El cálculo es: cantidad_visitas × (porcentaje_uit × UIT) + IGV.
        NO aplica clamping de UIT (a diferencia del motor PorcentajeObra) —
        Visitas se cobra por visita según la categoría, sin mínimo de 1 UIT.

        `fecha` es la fecha EFECTIVA opcional del preview: `None` significa hoy
        (comportamiento vigente); con fecha, IGV, UIT y la tarifa de visitas se
        resuelven a esa fecha con el resolver canónico (modo legacy).
        """
        modo = getattr(especifica, "modo_cotizacion", ModoCotizacionVisitas.NORMAL)
        bloque_continuidad = getattr(especifica, "continuidad", None)
        total_pagado_previa = (
            Decimal(str(bloque_continuidad.total_pagado_previa))
            if bloque_continuidad is not None
            else None
        )

        if modo == ModoCotizacionVisitas.CONTINUAR and fecha is not None:
            # El alta legacy no admite bloque de continuidad: no hay ruta de
            # guardado counterpart para la fecha histórica (DD-10).
            raise HttpError(
                400,
                "La continuidad no está disponible en la cotización con fecha "
                "histórica: el registro legacy de Inspección de Obra no admite "
                "bloque de continuidad.",
            )

        if fecha is not None:
            igv_vigente, uit_vigente = self._resolver_igv_uit_historicos(fecha)
            tarifas = self._resolver_tarifas_visitas_historicas(
                TipoLiquidacion.INSPECCION_OBRA, fecha
            )
            tarifa = next(
                (t for t in tarifas if str(t.id) == str(especifica.tarifa.tarifa_visitas_id)),
                None,
            )
            if tarifa is None:
                raise HttpError(404, "No se encontró una tarifa vigente en la fecha indicada.")
        else:
            uit_vigente = self.general_core.get_uit_vigente()
            if not uit_vigente:
                raise HttpError(404, "No hay UIT vigente configurada.")

            igv_vigente = self.general_core.get_igv_vigente()
            if not igv_vigente:
                raise HttpError(404, "No hay IGV vigente configurado.")

            tarifa = self.visitas_core.get_tarifa_por_id(
                str(especifica.tarifa.tarifa_visitas_id)
            )
            if tarifa is None:
                raise HttpError(404, "No se encontró una tarifa válida.")

        contexto = self.visitas_core.construir_contexto_visitas(
            modo=modo,
            cantidad_visitas=especifica.datos.cantidad_visitas,
            porcentaje_uit=Decimal(str(tarifa.porcentaje_uit)),
            uit_valor=Decimal(str(uit_vigente.valor)),
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            categoria=tarifa.categoria_visitas,
            tarifa_id=str(tarifa.id),
            total_pagado_previa=total_pagado_previa,
            uit_id=str(uit_vigente.id),
            igv_id=str(igv_vigente.id),
        )
        estrategia = self.visitas_core.calcular_cotizacion_visitas_estrategia(contexto)

        return self.visitas_core.resultado_desde_estrategia(estrategia)

    def obtener_tarifas_vigentes_proceso(self, fecha: Optional[date] = None) -> tuple:
        """
        Orchestrates fetching vigente tarifas and UIT.
        Returns (tarifas, uit_vigente) tuple.

        `fecha` es la fecha EFECTIVA opcional: `None` significa hoy (comportamiento
        vigente); con fecha, las tarifas y la UIT se resuelven a esa fecha con el
        resolver canónico (modo legacy).
        """
        if fecha is not None:
            uit_vigente = self.historico_core.get_uit_por_fecha(fecha)
            if not uit_vigente:
                raise HttpError(404, "No hay UIT vigente configurada.")
            tarifas = self._resolver_tarifas_visitas_historicas(
                TipoLiquidacion.INSPECCION_OBRA, fecha
            )
            return (tarifas, uit_vigente)

        uit_vigente = self.general_core.get_uit_vigente()
        if not uit_vigente:
            raise HttpError(404, "No hay UIT vigente configurada.")

        tarifas = self.visitas_core.get_tarifas_vigentes()
        return (tarifas, uit_vigente)

    def listar_liquidaciones(
        self, page: int, page_size: int,
        municipalidad_id=None,
        distrito_id=None,
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
        comprobante_serie=None,
        comprobante_numero=None,
    ) -> tuple[List[InspeccionObraPrimeraRevisionResult], int]:
        """
        Returns paginated InspeccionObraPrimeraRevisionResult list.
        Applies pagination defaults/boundaries, iterates ORM objects to build domain DTOs.
        Returns (List[InspeccionObraPrimeraRevisionResult], total_count).
        """
        # Pagination boundary defaults
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        orm_objects, total = self.general_core.list_liquidaciones_io_paginated(
            page=page,
            page_size=page_size,
            municipalidad_id=municipalidad_id,
            distrito_id=distrito_id,
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
            comprobante_serie=comprobante_serie,
            comprobante_numero=comprobante_numero,
        )

        # Build InspeccionObraPrimeraRevisionResult domain DTOs from ORM objects
        domain_results: List[InspeccionObraPrimeraRevisionResult] = []
        for lg in orm_objects:
            domain_results.append(self._build_io_result(lg))

        return domain_results, total

    def _build_io_result(self, lg) -> InspeccionObraPrimeraRevisionResult:
        """
        Maps a LiquidacionGeneral ORM object to InspeccionObraPrimeraRevisionResult domain DTO.

        Delegates LiquidacionGeneralResult construction to general_core.build_general_result().
        Only the type-specific fields (inspeccion_obra, liquidacion_visitas) are built here.
        IO does not use contacto_result or delegados.
        """
        from modules.liquidaciones.domain.results.liquidacion_especifico.inspeccion_obra_primera_revision_result import (
            LiquidacionEspecificaInspeccionObraResult,
        )
        from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_visitas_result import (
            LiquidacionVisitasResult,
        )
        from modules.liquidaciones.domain.services.flujos.liquidacion_especifico.liquidacion_inspeccion_obra_flujo import (
            LiquidacionInspeccionObraFlujo,
        )

        # Delegate general result construction to core (NO more duplicate inline mapping)
        # Map contacto like Edificaciones does
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
        usuario_id = lg.usuario_creador.id if lg.usuario_creador else None
        general_result = self.general_core.build_general_result(
            lg,
            usuario_id=usuario_id,
            contacto_result=contacto_result,
            delegados=[],
            codigo_cta=self.general_core.get_codigo_cta(lg.tipo_liquidacion),
        )

        # Type-specific: Inspeccion Obra
        io = lg.inspeccion_obra
        especifica_result = LiquidacionEspecificaInspeccionObraResult(
            id=str(io.id),
            numero=io.numero,
        )

        lv = lg.liquidacion_visitas.first()
        tipo_result = LiquidacionVisitasResult(
            id=str(lv.id),
            cantidad_visitas=lv.cantidad_visitas,
            porcentaje_uit=lv.porcentaje_uit if lv.porcentaje_uit else Decimal("0"),
            categoria=lv.categoria or "",
            tarifa_aplicada_id=str(lv.tarifa_aplicada_id) if lv.tarifa_aplicada_id else None,
            inspectores=LiquidacionInspeccionObraFlujo._build_inspectores_result(lv),
            registros_pago=LiquidacionInspeccionObraFlujo._build_registros_pago_result(lv),
            continuidad=LiquidacionInspeccionObraFlujo._build_continuidad_result(lv),
        )

        return InspeccionObraPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_especifica=especifica_result,
            liquidacion_tipo=tipo_result,
        )

    def obtener_liquidacion(self, liquidacion_id: uuid.UUID) -> InspeccionObraPrimeraRevisionResult:
        """
        Returns a single InspeccionObraPrimeraRevisionResult for Inspección de Obra by UUID.
        Raises LiquidacionNotFoundError if not found.
        """
        try:
            lg = self.general_core.get_liquidacion_io_by_id(liquidacion_id)
            return self._build_io_result(lg)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError("Liquidación no encontrada.")

    def crear_primera_revision_desde_previa_proceso(
        self,
        usuario_id: int,
        payload_in: LiquidacionInspeccionObraNuevaRevisionInput,
    ) -> InspeccionObraPrimeraRevisionResult:
        """
        Crea una IO primera-revision heredando proyecto/municipalidad/entidad
        de una liquidación previa (Edificación o Habilitación Urbana).

        Validations:
        - liquidacion_previa_id existe y es EDIFICACION o HABILITACION_URBANA
        - tariff exists
        - UIT and IGV are configured
        """
        from modules.liquidaciones.domain.constants import TipoLiquidacion

        # El bloque de continuidad SOLO aplica a `POST /nueva-liquidacion`
        # (flujo `crear_nueva_liquidacion_proceso`). Este flujo crea la IO a
        # partir de una liquidación previa de Edificación/Habilitación Urbana
        # y no sabe liquidar el crédito de las visitas no realizadas de una IO
        # previa: ignorarlo en silencio cobraría el valor COMPLETO del trabajo
        # y el usuario creería que se acreditó. Se rechaza explícitamente.
        if getattr(payload_in.liquidacion_especifica, "continuidad", None):
            raise HttpError(
                400,
                "La continuidad de visitas solo se admite al crear una IO nueva "
                "(POST /inspeccion-obra/nueva-liquidacion).",
            )

        # Step 1: Validate liquidacion_previa exists and is EDIFICACION or HABILITACION_URBANA
        try:
            previa = self.general_core.get_liquidacion_previa_para_io(
                payload_in.liquidacion_previa_id
            )
        except ObjectDoesNotExist:
            raise HttpError(404, "Liquidación previa no encontrada.")

        tipo_previo = previa.tipo_liquidacion.codigo
        if tipo_previo not in (TipoLiquidacion.EDIFICACION, TipoLiquidacion.HABILITACION_URBANA):
            raise HttpError(
                400,
                f"La liquidación previa debe ser Edificación o Habilitación Urbana. "
                f"Se proporcionó: {tipo_previo}"
            )

        # Step 2: Pre-validate UIT and IGV
        uit_vigente = self.general_core.get_uit_vigente()
        if not uit_vigente:
            raise HttpError(404, "No hay UIT vigente configurada.")

        igv_vigente = self.general_core.get_igv_vigente()
        if not igv_vigente:
            raise HttpError(404, "No hay IGV vigente configurado.")

        # Step 3: Pre-validate tariff
        tarifa_visitas_id = str(payload_in.liquidacion_especifica.tarifa.tarifa_visitas_id)
        tarifa = self.visitas_core.get_tarifa_por_id(tarifa_visitas_id)
        if not tarifa:
            raise HttpError(404, "No se encontró una tarifa válida.")

        # Step 4: Pre-validate inspector_operacion exists and matches tipo_previo
        from modules.liquidaciones.domain.models.inspector import InspectorOperacion
        try:
            inspector_operacion = InspectorOperacion.objects.get(
                id=payload_in.liquidacion_especifica.inspector_operacion_id
            )
        except ObjectDoesNotExist:
            raise HttpError(404, "No se encontró la operación del inspector.")

        # Validate tipo_liquidacion matches the previous liquidacion type
        if inspector_operacion.tipo_liquidacion.codigo != tipo_previo:
            raise HttpError(
                400,
                f"El inspector seleccionado no está registrado para el tipo de la "
                f"liquidación previa. Inspector registrado para: "
                f"{inspector_operacion.tipo_liquidacion.codigo}, "
                f"liquidación previa es: {tipo_previo}",
            )

        # Cross-validate inspector_id if provided
        inspector_id_input = getattr(payload_in.liquidacion_especifica, "inspector_id", None)
        if inspector_id_input and inspector_operacion.inspector_id != inspector_id_input:
            raise HttpError(
                400,
                "El inspector_id no coincide con la operación del inspector seleccionada.",
            )

        # Step 5: Build domain data inheriting from previa
        # Entidad and Proyecto are reused from previa (not created new)
        gen_data = payload_in.liquidacion_especifica
        visitas_data = LiquidacionCategoriaVisitasData(
            datos=DatosVisitas(
                cantidad_visitas=gen_data.datos.cantidad_visitas,
                categoria=tarifa.categoria_visitas,
            ),
            tarifa=TarifaVisitas(
                tarifa_visitas_id=str(gen_data.tarifa.tarifa_visitas_id)
            ),
        )

        domain_data = InspeccionObraNuevaRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(previa.municipalidad_id),
                expediente=previa.expediente,
                observacion=previa.observacion,
                denominacion_de_proyecto=previa.denominacion_de_proyecto,
                proyecto=ProyectoData(
                    nombre_propietario=previa.proyecto.nombre_propietario,
                    direccion=previa.proyecto.direccion,
                    distrito_id=str(previa.proyecto.distrito_id) if previa.proyecto.distrito_id else None,
                    entidad_razon_social=getattr(previa.proyecto, 'entidad_razon_social', None),
                    entidad=EntidadData(
                        tipo_documento=getattr(previa.proyecto, 'entidad_tipo_documento', None) or "",
                        numero_documento=getattr(previa.proyecto, 'entidad_numero_documento', None) or "",
                    ),
                ),
                contacto=(
                    ContactoData(
                        nombres=payload_in.contacto.nombres,
                        apellidos=payload_in.contacto.apellidos,
                        dni=payload_in.contacto.dni,
                        cargo=payload_in.contacto.cargo,
                        telefono=payload_in.contacto.telefono,
                        celular=payload_in.contacto.celular,
                        email=payload_in.contacto.email,
                    )
                    if payload_in.contacto
                    else None
                ),
            ),
            liquidacion_especifica=visitas_data,
        )

        # Step 6: Execute in flujo — pass inspector_operacion for direct derivation
        return self.flujo.ejecutar_primera_revision_desde_previa(
            usuario_id=usuario_id,
            data=domain_data,
            liquidacion_previa=previa,
            inspector_operacion=inspector_operacion,
        )

    def _resolver_continuidad(
        self,
        continuidad_in,
        igv_vigente,
    ) -> ContinuidadVisitasData:
        """
        Valida y normaliza el bloque OPCIONAL de continuidad de visitas.

        Reglas:
        - Si se referencia la previa en CAM, debe existir, ser de INSPECCION_OBRA
          y tener registro de visitas. El servidor es la autoridad de su
          cantidad total de visitas.
        - Si NO se referencia (previa fuera de CAM), el total de visitas lo
          informa el usuario.
        - `total_credito` NO lo envía el cliente: lo deriva el servidor aplicando
          el IGV vigente, para que el crédito y el valor completo sean
          consistentes al centavo.

        PRECEDENCIA DEL CRÉDITO (DD-5/DD-6) — la regla vive en UN solo lugar:

        1. `total_pagado_previa` (BRUTO declarado por el cliente) → MANDA. El
           servidor deriva el par (crédito NETO, crédito BRUTO) con el IGV
           efectivo de la ruta, a través del MOTOR
           (`calcular_credito_continuidad`).
           El neto declarado (`subtotal_credito`) se IGNORA.
        2. Sin bruto declarado → se conserva el camino vigente por
           `subtotal_credito` (NETO). El bruto se deriva salvo que venga
           CONGELADO (`total_credito`: el par persistido de la fila vigente en
           modo `mantener`), en cuyo caso NO se re-deriva.

        Todas las reglas de negocio de este bloque responden con **400**
        (Explorer, Fase 2 — "Validaciones devolviendo 400"): la referencia
        inválida, el crédito negativo, las pendientes que superan el total de
        la previa y las pendientes que no se pueden validar contra ningún total.
        """
        liquidacion_previa = None
        previa_visitas = None

        if continuidad_in.liquidacion_previa_id:
            try:
                liquidacion_previa = self.general_core.get_liquidacion_io_by_id(
                    continuidad_in.liquidacion_previa_id
                )
            except ObjectDoesNotExist:
                raise HttpError(
                    400,
                    "La liquidación previa de continuidad no existe o no es de "
                    "Inspección de Obra.",
                )
            previa_visitas = liquidacion_previa.liquidacion_visitas.first()
            if previa_visitas is None:
                raise HttpError(
                    400,
                    "La liquidación previa de continuidad no tiene registro de "
                    "visitas.",
                )

        if previa_visitas is not None:
            # El servidor es la autoridad del total de visitas de la previa:
            # el valor que envíe el cliente se ignora cuando hay referencia.
            visitas_previas_totales = previa_visitas.cantidad_visitas
        else:
            visitas_previas_totales = continuidad_in.visitas_previas_totales

        visitas_previas_pendientes = continuidad_in.visitas_previas_pendientes or 0
        if (
            visitas_previas_totales is not None
            and visitas_previas_pendientes > visitas_previas_totales
        ):
            raise HttpError(
                400,
                "Las visitas pendientes de la previa no pueden superar el total "
                "de visitas de la previa.",
            )

        if (
            liquidacion_previa is None
            and visitas_previas_totales is None
            and visitas_previas_pendientes > 0
        ):
            # Sin referencia a la previa en CAM y sin total informado, el
            # servidor no tiene contra qué validar las pendientes. El ingreso
            # MANUAL de la previa sigue permitido informando su total de
            # visitas (o indicando 0 pendientes y acreditando el crédito como
            # suma global); lo que no se admite es un conteo de pendientes
            # imposible de verificar.
            raise HttpError(
                400,
                "Las visitas pendientes de la continuidad requieren referenciar "
                "la liquidación previa o informar el total de visitas de la "
                "previa.",
            )

        # ── PRECEDENCIA DEL CRÉDITO (DD-5/DD-6) ──────────────────────────────
        igv_porcentaje = Decimal(str(igv_vigente.valor))
        total_pagado_previa = getattr(continuidad_in, "total_pagado_previa", None)

        if total_pagado_previa is not None:
            # El BRUTO declarado MANDA: el servidor es la autoridad de la
            # conversión a crédito neto, con el IGV efectivo de la ruta.
            bruto_declarado = Decimal(str(total_pagado_previa))
            if bruto_declarado <= 0:
                raise HttpError(
                    400,
                    "El monto bruto pagado en la liquidación previa debe ser mayor "
                    "a cero.",
                )
            subtotal_credito, total_credito = (
                self.visitas_core.calcular_credito_continuidad(
                    bruto_declarado,
                    igv_porcentaje,
                )
            )
        else:
            subtotal_credito = Decimal(str(continuidad_in.subtotal_credito or 0))
            if subtotal_credito < 0:
                raise HttpError(
                    400, "El crédito de la continuidad no puede ser negativo."
                )

            # El bruto del crédito se congela si viene resuelto (crédito
            # persistido de la fila vigente en modo `mantener`); si no, se
            # deriva del neto con el IGV de la ruta.
            total_credito_congelado = getattr(continuidad_in, "total_credito", None)
            if total_credito_congelado is None:
                total_credito = quantize_money(
                    subtotal_credito * (Decimal("1") + igv_porcentaje)
                )
            else:
                total_credito = Decimal(str(total_credito_congelado))

        return ContinuidadVisitasData(
            liquidacion_previa=liquidacion_previa,
            liquidacion_previa_id=(
                str(liquidacion_previa.id) if liquidacion_previa else None
            ),
            subtotal_credito=subtotal_credito,
            total_credito=total_credito,
            total_pagado_previa=(
                Decimal(str(total_pagado_previa))
                if total_pagado_previa is not None
                else None
            ),
            visitas_previas_totales=visitas_previas_totales,
            visitas_previas_pendientes=visitas_previas_pendientes,
            categoria_previa=(
                continuidad_in.categoria_previa
                or (previa_visitas.categoria if previa_visitas else None)
            ),
            observacion=continuidad_in.observacion,
        )

    def crear_nueva_liquidacion_proceso(
        self,
        usuario_id: int,
        payload_in,
        registro_legacy: LegacyRegistroContexto | None = None,
    ) -> InspeccionObraPrimeraRevisionResult:
        """
        Crea una IO primera-revision SIN liquidación previa.
        Entidad y Proyecto se crean desde cero a partir de los datos del usuario.

        Validations:
        - UIT and IGV are configured
        - tariff exists (if provided)
        - inspector exists
        - inspector_operacion belongs to inspector (if provided)

        `registro_legacy` (registro manual histórico): se crea SIN liquidación
        previa y SIN vínculo de inspector, con la fecha efectiva explícita y los
        valores financieros resueltos a esa fecha.
        """
        if registro_legacy is not None:
            return self._crear_registro_legacy_proceso(
                usuario_id=usuario_id,
                payload_in=payload_in,
                registro_legacy=registro_legacy,
            )
        from modules.liquidaciones.domain.constants import TipoLiquidacion

        # Step 1: Pre-validate UIT and IGV
        uit_vigente = self.general_core.get_uit_vigente()
        if not uit_vigente:
            raise HttpError(404, "No hay UIT vigente configurada.")

        igv_vigente = self.general_core.get_igv_vigente()
        if not igv_vigente:
            raise HttpError(404, "No hay IGV vigente configurado.")

        # Step 2: inspector_operacion_id is now required in schema
        from modules.liquidaciones.domain.models.inspector import InspectorOperacion
        inspector_operacion_id = payload_in.liquidacion_especifica.inspector_operacion_id
        try:
            inspector_operacion = InspectorOperacion.objects.get(id=inspector_operacion_id)
        except InspectorOperacion.DoesNotExist:
            raise HttpError(404, "No se encontró la operación del inspector.")

        # Cross-validate inspector_id if provided (optional field for backward compat)
        inspector_id_input = getattr(payload_in.liquidacion_especifica, "inspector_id", None)
        if inspector_id_input and inspector_operacion.inspector_id != inspector_id_input:
            raise HttpError(
                400,
                "El inspector_id no coincide con la operación del inspector seleccionada.",
            )

        # Step 3: Pre-validate tariff (optional for legacy CATEGORIA=0 path)
        tarifa_visitas_id = str(payload_in.liquidacion_especifica.tarifa.tarifa_visitas_id) if payload_in.liquidacion_especifica.tarifa.tarifa_visitas_id else None
        tarifa = None
        if tarifa_visitas_id:
            tarifa = self.visitas_core.get_tarifa_por_id(tarifa_visitas_id)
            if not tarifa:
                raise HttpError(404, "No se encontró una tarifa válida.")

        # Step 4: Build domain data from user input (entidad/proyecto created from scratch in flujo)
        gen_data = payload_in.liquidacion_especifica
        visitas_data = LiquidacionCategoriaVisitasData(
            datos=DatosVisitas(
                cantidad_visitas=gen_data.datos.cantidad_visitas,
                categoria=tarifa.categoria_visitas if tarifa else None,
            ),
            tarifa=TarifaVisitas(
                tarifa_visitas_id=tarifa_visitas_id
            ) if tarifa_visitas_id else TarifaVisitas(tarifa_visitas_id=None),
            # Continuidad OPCIONAL: sin el bloque, la IO es normal y su
            # sub_total es el valor completo del trabajo (comportamiento vigente).
            continuidad=(
                self._resolver_continuidad(gen_data.continuidad, igv_vigente)
                if getattr(gen_data, "continuidad", None)
                else None
            ),
        )

        # Build LiquidacionGeneralData from the user-provided liquidacion_general
        lg_in = payload_in.liquidacion_general
        domain_data = InspeccionObraNuevaRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(lg_in.municipalidad_id),
                expediente=lg_in.expediente,
                observacion=lg_in.observacion,
                denominacion_de_proyecto=lg_in.denominacion_de_proyecto,
                proyecto=ProyectoData(
                    nombre_propietario=lg_in.proyecto.nombre_propietario,
                    direccion=lg_in.proyecto.direccion,
                    distrito_id=str(lg_in.proyecto.distrito_id) if lg_in.proyecto.distrito_id else None,
                    entidad_razon_social=getattr(lg_in.proyecto.entidad, "razon_social", None),
                    entidad=EntidadData(
                        tipo_documento=getattr(lg_in.proyecto.entidad, "tipo_documento", None) or "",
                        numero_documento=getattr(lg_in.proyecto.entidad, "numero_documento", None) or "",
                    ),
                ),
                contacto=(
                    ContactoData(
                        nombres=lg_in.contacto.nombres,
                        apellidos=lg_in.contacto.apellidos,
                        dni=lg_in.contacto.dni,
                        cargo=lg_in.contacto.cargo,
                        telefono=lg_in.contacto.telefono,
                        celular=lg_in.contacto.celular,
                        email=lg_in.contacto.email,
                    )
                    if lg_in.contacto
                    else None
                ),
            ),
            liquidacion_especifica=visitas_data,
        )

        # Step 5: Execute in flujo — inspector derived from inspector_operacion
        return self.flujo.ejecutar_nueva_liquidacion(
            usuario_id=usuario_id,
            data=domain_data,
            inspector=inspector_operacion.inspector,
            inspector_operacion=inspector_operacion,
        )

    def _crear_registro_legacy_proceso(
        self,
        usuario_id: int,
        payload_in,
        registro_legacy: "LegacyRegistroContexto",
    ) -> InspeccionObraPrimeraRevisionResult:
        """
        Registro manual histórico de Inspección de Obra.

        Diferencias respecto a `crear_nueva_liquidacion_proceso` (camino normal):
        - la fecha efectiva es `registro_legacy.fecha_registro`: IGV, UIT y la
          tarifa de visitas se resuelven a esa fecha con el resolver canónico
          (sin fallback a los valores de hoy);
        - NO hay liquidación previa (el registro histórico no la tiene);
        - El inspector es opcional. Cuando se entrega una operación existente,
          se conserva aunque ya no esté vigente hoy.
        - los totales SIEMPRE se calculan con la fórmula de visitas: no hay
          bypass ni totales manuales.
        """
        fecha_efectiva = registro_legacy.fecha_registro

        # IGV/UIT efectivos en la fecha del registro (sin fallback a hoy).
        igv, uit = self._resolver_igv_uit_historicos(fecha_efectiva)

        # Tarifa de visitas vigente en la fecha efectiva.
        tarifas = self._resolver_tarifas_visitas_historicas(
            TipoLiquidacion.INSPECCION_OBRA, fecha_efectiva
        )
        tarifa_id = str(payload_in.liquidacion_especifica.tarifa.tarifa_visitas_id)
        tarifa = next((t for t in tarifas if str(t.id) == tarifa_id), None)
        if tarifa is None:
            raise HttpError(
                404,
                "No se encontró una tarifa vigente para la fecha indicada.",
            )

        cantidad_visitas = payload_in.liquidacion_especifica.datos.cantidad_visitas
        if cantidad_visitas < 1:
            raise HttpError(400, "cantidad_visitas debe ser >= 1")

        inspector_id = getattr(payload_in.liquidacion_especifica, "inspector_id", None)
        inspector_operacion_id = getattr(
            payload_in.liquidacion_especifica,
            "inspector_operacion_id",
            None,
        )
        if bool(inspector_id) != bool(inspector_operacion_id):
            raise HttpError(
                400,
                "El inspector y su operación deben seleccionarse juntos.",
            )

        inspector = None
        inspector_operacion = None
        if inspector_operacion_id:
            from modules.liquidaciones.domain.models.inspector import InspectorOperacion

            try:
                inspector_operacion = InspectorOperacion.objects.select_related(
                    "inspector",
                ).get(id=inspector_operacion_id)
            except InspectorOperacion.DoesNotExist:
                raise HttpError(404, "No se encontró la operación del inspector.")

            if inspector_operacion.inspector_id != inspector_id:
                raise HttpError(
                    400,
                    "El inspector no coincide con la operación seleccionada.",
                )
            inspector = inspector_operacion.inspector

        # Domain DTO: entidad y proyecto se crean desde cero.
        visitas_data = LiquidacionCategoriaVisitasData(
            datos=DatosVisitas(
                cantidad_visitas=cantidad_visitas,
                categoria=tarifa.categoria_visitas,
            ),
            tarifa=TarifaVisitas(tarifa_visitas_id=tarifa_id),
        )

        lg_in = payload_in.liquidacion_general
        domain_data = InspeccionObraNuevaRevisionData(
            liquidacion_general=LiquidacionGeneralData(
                municipalidad_id=str(lg_in.municipalidad_id),
                expediente=lg_in.expediente,
                observacion=lg_in.observacion,
                denominacion_de_proyecto=lg_in.denominacion_de_proyecto,
                proyecto=ProyectoData(
                    nombre_propietario=lg_in.proyecto.nombre_propietario,
                    direccion=lg_in.proyecto.direccion,
                    distrito_id=str(lg_in.proyecto.distrito_id) if lg_in.proyecto.distrito_id else None,
                    entidad_razon_social=getattr(lg_in.proyecto.entidad, "razon_social", None),
                    entidad=EntidadData(
                        tipo_documento=getattr(lg_in.proyecto.entidad, "tipo_documento", None) or "",
                        numero_documento=getattr(lg_in.proyecto.entidad, "numero_documento", None) or "",
                    ),
                ),
                contacto=(
                    ContactoData(
                        nombres=lg_in.contacto.nombres,
                        apellidos=lg_in.contacto.apellidos,
                        dni=lg_in.contacto.dni,
                        cargo=lg_in.contacto.cargo,
                        telefono=lg_in.contacto.telefono,
                        celular=lg_in.contacto.celular,
                        email=lg_in.contacto.email,
                    )
                    if lg_in.contacto
                    else None
                ),
            ),
            liquidacion_especifica=visitas_data,
        )

        # Step: Execute in flujo. The selected operation may be historical;
        # validity is a selection concern, not a creation constraint.
        return self.flujo.ejecutar_nueva_liquidacion(
            usuario_id=usuario_id,
            data=domain_data,
            inspector=inspector,
            inspector_operacion=inspector_operacion,
            registro_legacy=registro_legacy.model_copy(
                update={"igv": igv, "uit": uit, "tarifa": tarifa}
            ),
        )

    def recalcular_visitas(
        self,
        liquidacion_id: uuid.UUID,
        cantidad_visitas=None,
        categoria=None,
        tarifa_visitas_id=None,
        liquidacion_general=None,
        liquidacion_tipo=None,
    ):
        """
        PATCH recalculation for Inspeccion de Obra (Visitas motor).

        Supports two input formats:
        1. Flat (legacy): cantidad_visitas + categoria + tarifa_visitas_id directly
        2. Wrapper (current): liquidacion_general + liquidacion_tipo

        If liquidacion_general is provided, calls general update orchestrator.
        If liquidacion_tipo is provided, delegates to LiquidacionPatchVisitasService.
        Both can be provided in one call for atomic update.

        CONTINUIDAD: `liquidacion_tipo.continuidad` (con su discriminador
        `modo`) viaja por este MISMO PATCH y por la MISMA transacción. No existe
        un endpoint dedicado para encender, mantener o apagar la continuidad.

        Orden de las operaciones (Explorer §5.2):
        0. Guard `PAGADA` → 409 (antes de abrir la transacción).
        1. Guard RH/pago → 409, ANTES de cualquier escritura: cuando el PATCH
           trae una operación de continuidad, el PATCH COMPLETO se rechaza
           ("no se escribe nada"), incluidas las visitas/tarifa de B que
           acompañen en la misma petición.
        2. Validación de la transición (modo vs. estado persistido) → 400.
        3. Validación del bloque de continuidad (mismas reglas que la
           creación) → 400.
        4. Escrituras, en el orden que exige cada modo:
           - `desactivar`: (a) eliminar la fila de continuidad; (b) recalcular B
             → al no haber fila, la cabecera cobra el VALOR COMPLETO.
           - `activar`: (a) recalcular B (aún sin fila → valor completo);
             (b) crear la fila con el valor completo y el crédito;
             (c) reaplicar la diferencia.
           - `mantener`: (a) recalcular B; (b) actualizar la fila (crédito,
             pendientes, referencia, observación); (c) reaplicar la diferencia
             con el crédito nuevo.
           - sin bloque: (a) recalcular B con el crédito congelado
             (comportamiento vigente).

        Args:
            liquidacion_id: UUID of the LiquidacionGeneral to recalculate.
            cantidad_visitas: New cantidad_visitas (flat format, None = preserve current).
            categoria: New categoria string (flat format, None = preserve current).
            tarifa_visitas_id: New tarifa UUID (flat format, None = preserve current).
            liquidacion_general: Optional dict with general fields (wrapper format).
            liquidacion_tipo: Optional dict with tipo fields (wrapper format).

        Returns:
            InspeccionObraPrimeraRevisionResult with updated values.

        Raises:
            LiquidacionNotFoundError: If liquidacion not found.
            ConflictError: If estado == PAGADA, or if the continuity operation
                is blocked by an RH mensual / pagos al inspector.
            HttpError(400): If the transition is invalid or the continuity block
                breaks a business rule.
        """
        from django.db import transaction
        from core.exceptions import ConflictError
        from modules.liquidaciones.domain.constants import EstadoLiquidacion
        from modules.liquidaciones.domain.services.core.liquidacion_patch_visitas_service import (
            LiquidacionPatchVisitasService,
            PatchVisitasInput,
        )

        # 1. Fetch the liquidacion
        try:
            lg = self.general_core.get_liquidacion_io_by_id(liquidacion_id)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError("Liquidación no encontrada.")

        # 2. Guard: only PENDIENTE allows updates (applies to BOTH general and tipo)
        if lg.estado == EstadoLiquidacion.PAGADA:
            raise ConflictError(
                message="No se puede editar una liquidación en estado PAGADA.",
                code="LIQUIDACION_PAGADA_NOT_EDITABLE",
            )

        # 3. Handle wrapper format: extract from liquidacion_general + liquidacion_tipo
        if liquidacion_tipo is not None:
            # Wrapper format: extract from nested structure
            tipo_datos = liquidacion_tipo.get("datos") or {}
            tipo_tarifa = liquidacion_tipo.get("tarifa")
            # Map wrapper field names to flat format
            cv_input = tipo_datos.get("cantidad_visitas", cantidad_visitas)
            cat_input = tipo_datos.get("categoria", categoria)
            tv_input = tipo_tarifa.get("tarifa_visitas_id") if tipo_tarifa else tarifa_visitas_id
            inspector_operacion_id = liquidacion_tipo.get("inspector_operacion_id")
            continuidad_in = liquidacion_tipo.get("continuidad")
        else:
            # Flat format: use params directly
            cv_input = cantidad_visitas
            cat_input = categoria
            tv_input = tarifa_visitas_id
            inspector_operacion_id = None
            continuidad_in = None

        # 4. Guard 409 (RH mensual / pagos al inspector) — ANTES de abrir la
        #    transacción y, por tanto, antes de cualquier escritura.
        modo_continuidad = None
        if continuidad_in is not None:
            modo_continuidad = self._resolver_modo_continuidad(continuidad_in)
            liquidacion_visitas = self._get_liquidacion_visitas(lg)
            if liquidacion_visitas is not None:
                self.continuidad_core.guardar_editable_por_rh(liquidacion_visitas)

        # 5. Execute updates in a single transaction
        patch_service = LiquidacionPatchVisitasService()
        with transaction.atomic():
            # 5a. Validate the transition and normalize the continuity block.
            #     Read-only: nothing has been written yet.
            transicion = None
            if modo_continuidad is not None:
                transicion = self._resolver_transicion_continuidad(
                    lg=lg,
                    modo=modo_continuidad,
                    bloque=continuidad_in,
                )

            # 5b. Update general fields if provided
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
                )

            # 5c. Update tipo fields if provided
            if modo_continuidad is not None:
                # La operación de continuidad SIEMPRE reprecia B: incluso sin
                # cambios de visitas/tarifa, la fila de continuidad tiene que
                # reflejar el valor completo vigente (o restaurarlo, en el
                # modo `desactivar`).
                patch_input = PatchVisitasInput(
                    cantidad_visitas=cv_input,
                    categoria=cat_input,
                    tarifa_visitas_id=tv_input,
                )
                self._aplicar_transicion_continuidad(
                    lg=lg,
                    patch_service=patch_service,
                    patch_input=patch_input,
                    transicion=transicion,
                )
            elif cv_input is not None or cat_input is not None or tv_input is not None:
                patch_input = PatchVisitasInput(
                    cantidad_visitas=cv_input,
                    categoria=cat_input,
                    tarifa_visitas_id=tv_input,
                )
                patch_service.recalcular(lg, patch_input)

            # 5d. Update inspector if inspector_operacion_id is provided
            if inspector_operacion_id is not None:
                from modules.liquidaciones.domain.models.inspector import (
                    InspectorOperacion,
                    LiquidacionInspector,
                )
                # Get the liquidacion_visitas (liquidacion tipo)
                lv = lg.liquidacion_visitas.first()
                if lv is not None:
                    # Delete existing LiquidacionInspector for this liquidacion
                    LiquidacionInspector.objects.filter(liquidacion=lv).delete()
                    # Find the InspectorOperacion
                    try:
                        inspector_operacion = InspectorOperacion.objects.get(
                            id=inspector_operacion_id
                        )
                    except ObjectDoesNotExist:
                        raise HttpError(
                            404,
                            "InspectorOperacion no encontrado.",
                        )
                    # Create new LiquidacionInspector
                    LiquidacionInspector.objects.create(
                        liquidacion=lv,
                        inspector=inspector_operacion.inspector,
                        inspector_operacion=inspector_operacion,
                        especialidad_revision=inspector_operacion.especialidad_revision,
                    )

        # 6. Refresh and return built result
        lg.refresh_from_db()
        return self._build_io_result(lg)

    # ── Continuidad de visitas en el PATCH ───────────────────────────────────

    @staticmethod
    def _resolver_modo_continuidad(continuidad_in: dict) -> ModoContinuidadVisitas:
        """
        Resuelve el discriminador de modo del bloque de continuidad.

        El schema de entrada ya valida el valor (`ModoContinuidadVisitas`), así
        que aquí solo se normaliza. Se conserva una comprobación explícita
        para que un payload que se saltara el schema produzca un 400 legible
        en vez de un 500 por `ValueError`.
        """
        modo_raw = continuidad_in.get("modo")
        try:
            return ModoContinuidadVisitas(str(modo_raw))
        except ValueError:
            raise HttpError(
                400,
                f"El modo de continuidad '{modo_raw}' no es válido. "
                "Use 'activar', 'mantener' o 'desactivar'.",
            )

    @staticmethod
    def _get_liquidacion_visitas(liquidacion_general):
        """
        Devuelve la LCV (LiquidacionPorCategoriaVisitas) de la IO o None.

        Se resuelve con una consulta propia (no con la caché de prefetch) para
        que el estado de la fila de continuidad sea siempre el vigente.
        """
        try:
            return liquidacion_general.liquidacion_visitas.get()
        except ObjectDoesNotExist:
            return None

    def _resolver_transicion_continuidad(
        self,
        lg,
        modo: ModoContinuidadVisitas,
        bloque: dict,
    ) -> _TransicionContinuidad:
        """
        Valida la transición de continuidad y normaliza el bloque (400).

        Aplica la matriz de transición del Explorer §5.1:

        | Estado persistido | `modo`       | Resultado                         |
        |--------------------|--------------|-----------------------------------|
        | Sin continuidad    | `activar`    | Crea la fila                      |
        | Sin continuidad    | `mantener`   | 400                               |
        | Sin continuidad    | `desactivar` | 400                               |
        | Con continuidad    | `mantener`   | Actualiza la fila                 |
        | Con continuidad    | `activar`    | 400                               |
        | Con continuidad    | `desactivar` | Elimina la fila                   |

        En `activar` y `mantener` el bloque se valida con las MISMAS reglas de
        negocio de la creación (`_resolver_continuidad`): todas responden 400.
        """
        liquidacion_visitas = self._get_liquidacion_visitas(lg)
        continuidad_actual = (
            self.continuidad_core.get_continuidad(liquidacion_visitas)
            if liquidacion_visitas is not None
            else None
        )

        # ── Matriz de transición ──────────────────────────────────────────────
        if (
            modo == ModoContinuidadVisitas.ACTIVAR
            and continuidad_actual is not None
        ):
            raise HttpError(
                400,
                "La inspección de obra ya tiene la continuidad activada. "
                "Use el modo 'mantener' para actualizarla o 'desactivar' para apagarla.",
            )
        if (
            modo in (ModoContinuidadVisitas.MANTENER, ModoContinuidadVisitas.DESACTIVAR)
            and continuidad_actual is None
        ):
            raise HttpError(
                400,
                "La inspección de obra no tiene continuidad activada. "
                "Use el modo 'activar' para encenderla.",
            )

        if modo == ModoContinuidadVisitas.DESACTIVAR:
            # El resto del bloque se ignora: apagar solo elimina la fila y
            # restaura los montos normales de B.
            return _TransicionContinuidad(
                modo=modo,
                continuidad=continuidad_actual,
                datos=None,
            )

        # ── `activar` / `mantener`: normalizar y validar el bloque ────────────
        patch_data = self._fusionar_bloque_continuidad(bloque, continuidad_actual)

        # El crédito se deriva con el IGV HISTÓRICO de `fecha_registro` (el
        # mismo del recálculo): con él el documento cuadra al centavo (D3).
        igv_historico = self.historico_core.get_igv_por_fecha(lg.fecha_registro.date())
        datos = self._resolver_continuidad(patch_data, igv_historico)

        if datos.liquidacion_previa_id and datos.liquidacion_previa_id == str(lg.id):
            raise HttpError(
                400,
                "La liquidación previa de la continuidad no puede ser la propia "
                "inspección de obra que se está editando.",
            )

        return _TransicionContinuidad(
            modo=modo,
            continuidad=continuidad_actual,
            datos=datos,
        )

    @staticmethod
    def _fusionar_bloque_continuidad(
        bloque: dict,
        continuidad_actual: Optional[LiquidacionContinuidadVisitas],
    ) -> ContinuidadVisitasPatchData:
        """
        Normaliza el bloque de continuidad del PATCH.

        - `activar` (sin fila previa): toma los valores enviados; los omitidos
          valen 0 / None.
        - `mantener` (con fila vigente): reemplaza los campos ENVIADOS y
          conserva los omitidos con el valor vigente del registro. Así el ancla
          a la liquidación previa (A) y el crédito NUNCA se pierden por
          omisión (semántica replace por campo).

        El CRÉDITO se transporta con las dos mitades: el NETO (`subtotal_credito`)
        y el BRUTO (`total_credito`). El bruto vigente se conserva SOLO cuando
        el cliente no envía ningún crédito: en ese caso el crédito queda
        CONGELADO y NO se re-derive con otro IGV. Si el cliente envía un neto
        nuevo, el bruto se re-deriva (comportamiento vigente); si envía el
        bruto DECLARADO, manda el bruto (DD-5/DD-6).

        El BRUTO DECLARADO (`total_pagado_previa`) no tiene contraparte
        persistida (la fila de continuidad no cambia de modelo): si el cliente
        no lo envía, vale None → el crédito vigente queda congelado.
        """
        if continuidad_actual is None:
            return ContinuidadVisitasPatchData(
                liquidacion_previa_id=bloque.get("liquidacion_previa_id"),
                visitas_previas_totales=bloque.get("visitas_previas_totales"),
                visitas_previas_pendientes=bloque.get("visitas_previas_pendientes"),
                categoria_previa=bloque.get("categoria_previa"),
                subtotal_credito=bloque.get("subtotal_credito"),
                total_credito=bloque.get("total_credito"),
                total_pagado_previa=bloque.get("total_pagado_previa"),
                observacion=bloque.get("observacion"),
            )

        def _valor(campo, vigente):
            valor = bloque.get(campo)
            return vigente if valor is None else valor

        # El crédito se CONGELA solo si el cliente no envía ninguno de los dos
        # caminos de crédito (neto ni bruto declarado).
        credito_enviado = bloque.get("subtotal_credito") is not None
        bruto_declarado = bloque.get("total_pagado_previa") is not None
        total_credito = (
            None
            if (credito_enviado or bruto_declarado)
            else continuidad_actual.total_credito
        )

        return ContinuidadVisitasPatchData(
            liquidacion_previa_id=_valor(
                "liquidacion_previa_id", continuidad_actual.liquidacion_previa_id
            ),
            visitas_previas_totales=_valor(
                "visitas_previas_totales", continuidad_actual.visitas_previas_totales
            ),
            visitas_previas_pendientes=_valor(
                "visitas_previas_pendientes", continuidad_actual.visitas_previas_pendientes
            ),
            categoria_previa=_valor(
                "categoria_previa", continuidad_actual.categoria_previa
            ),
            subtotal_credito=_valor(
                "subtotal_credito", continuidad_actual.subtotal_credito
            ),
            # El BRUTO del crédito queda CONGELADO con el registro vigente
            # cuando el cliente no envía crédito: en `mantener` sin bruto
            # declarado el crédito NO se re-deriva.
            total_credito=total_credito,
            total_pagado_previa=bloque.get("total_pagado_previa"),
            observacion=_valor("observacion", continuidad_actual.observacion),
        )

    def _aplicar_transicion_continuidad(
        self,
        lg,
        patch_service,
        patch_input,
        transicion: _TransicionContinuidad,
    ) -> None:
        """
        Aplica la transición de continuidad con el orden de escrituras exigido.

        El orden NO es un detalle: `recalcular_visitas` decide el significado
        de `sub_total`/`total` según exista o no la fila de continuidad, así que
        el modo tiene que orquestarse ALREDEDOR del recálculo y no como un
        ajuste posterior.
        """
        modo = transicion.modo
        datos = transicion.datos

        if modo == ModoContinuidadVisitas.DESACTIVAR:
            # (a) eliminar la fila de continuidad; (b) recalcular B → al no
            #     haber fila, la cabecera vuelve a cobrar el VALOR COMPLETO.
            self.continuidad_core.eliminar_continuidad(transicion.continuidad)
            resultado = patch_service.recalcular_visitas(lg, patch_input)
            patch_service.aplicar_totales_valor_completo(lg, resultado)
            return

        if modo == ModoContinuidadVisitas.ACTIVAR:
            # (a) recalcular B (aún sin fila → valor completo);
            # (b) crear la fila con el valor completo y el crédito;
            # (c) reaplicar la diferencia.
            #
            # El recálculo recibe el CRÉDITO ya resuelto: el MOTOR corre en modo
            # CONTINUAR y devuelve la diferencia que se persiste, de modo que
            # lo guardado es EXACTAMENTE lo que devolvió la cotización.
            resultado = patch_service.recalcular_visitas(
                lg,
                patch_input,
                continuidad_credito=self._credito_continuidad_motor(datos),
            )
            self.continuidad_core.crear_continuidad(
                liquidacion_visitas=resultado.liquidacion_visitas,
                monto_acumulado=resultado.monto_acumulado,
                total_acumulado=resultado.total_acumulado,
                subtotal_credito=datos.subtotal_credito,
                total_credito=datos.total_credito,
                liquidacion_previa=datos.liquidacion_previa,
                visitas_previas_totales=datos.visitas_previas_totales,
                visitas_previas_pendientes=datos.visitas_previas_pendientes,
                categoria_previa=datos.categoria_previa,
                observacion=datos.observacion,
            )
            patch_service.aplicar_totales_diferencia(
                lg,
                resultado,
                subtotal_credito=datos.subtotal_credito,
                total_credito=datos.total_credito,
            )
            return

        # ── MANTENER ───────────────────────────────────────────────────────────
        # (a) recalcular B; (b) actualizar la fila (crédito, pendientes,
        #     referencia, observación) y recalcular `total_credito`;
        # (c) reaplicar la diferencia con el crédito nuevo.
        #
        # El crédito llega al MOTOR con las dos mitades (neto y bruto): el bruto
        # declarado manda si viene; si no, el par vigente queda CONGELADO.
        resultado = patch_service.recalcular_visitas(
            lg,
            patch_input,
            continuidad_credito=self._credito_continuidad_motor(datos),
        )
        self.continuidad_core.actualizar_continuidad(
            transicion.continuidad,
            monto_acumulado=resultado.monto_acumulado,
            total_acumulado=resultado.total_acumulado,
            subtotal_credito=datos.subtotal_credito,
            total_credito=datos.total_credito,
            liquidacion_previa=datos.liquidacion_previa,
            visitas_previas_totales=datos.visitas_previas_totales,
            visitas_previas_pendientes=datos.visitas_previas_pendientes,
            categoria_previa=datos.categoria_previa,
            observacion=datos.observacion,
        )
        patch_service.aplicar_totales_diferencia(
            lg,
            resultado,
            subtotal_credito=datos.subtotal_credito,
            total_credito=datos.total_credito,
        )

    @staticmethod
    def _credito_continuidad_motor(
        datos: ContinuidadVisitasData,
    ) -> ContinuidadCreditoVisitas:
        """
        Traduce el bloque de continuidad NORMALIZADO al INPUT del crédito del
        MOTOR (`ContinuidadCreditoVisitas`).

        El motor aplica la regla de precedencia: el BRUTO declarado manda; si
        no viene, usa el par (neto, bruto) ya resuelto —con el bruto congelado
        cuando el crédito viene de la fila vigente.
        """
        return ContinuidadCreditoVisitas(
            total_pagado_previa=datos.total_pagado_previa,
            credito_neto=datos.subtotal_credito,
            credito_bruto=datos.total_credito,
        )

    def cotizar_edicion_proceso(
        self,
        liquidacion_id: uuid.UUID,
        payload_in: "LiquidacionInspeccionObraCotizarEdicionInput",
    ) -> "CotizacionVisitasResult":
        """
        Read-only quote for editing an existing Inspeccion de Obra liquidacion.

        Uses historical financial values from LiquidacionGeneral.fecha_registro.
        Does NOT persist any changes.

        El MODO viaja dentro de `liquidacion_tipo` (union discriminada
        NORMAL | CONTINUAR). El IGV efectivo es el HISTÓRICO de la fecha de
        registro: es el mismo que usará el PATCH counterpart.

        Args:
            liquidacion_id: UUID of the existing LiquidacionGeneral.
            payload_in: Typed wrapper with the IO quote union.

        Returns:
            CotizacionVisitasResult with the calculated quote.

        Raises:
            LiquidacionNotFoundError: If liquidacion not found.
        """
        from django.core.exceptions import ObjectDoesNotExist
        from modules.liquidaciones.domain.services.core.liquidacion_cotizar_edicion_service import (
            LiquidacionCotizarEdicionVisitasService,
            CotizarEdicionVisitasInput,
        )
        from modules.liquidaciones.presentation.schemas.liquidacion_especifico.liquidacion_inspeccion_obra_schemas import (
            LiquidacionInspeccionObraCotizarEdicionInput,
        )

        # 1. Fetch the liquidacion
        try:
            lg = self.general_core.get_liquidacion_io_by_id(liquidacion_id)
        except ObjectDoesNotExist:
            raise LiquidacionNotFoundError("Liquidación no encontrada.")

        # 2. Extract fields from the typed union (sin ramas por modo en el controller)
        tipo = payload_in.liquidacion_tipo
        modo = getattr(tipo, "modo_cotizacion", ModoCotizacionVisitas.NORMAL)
        bloque_continuidad = getattr(tipo, "continuidad", None)
        total_pagado_previa = (
            Decimal(str(bloque_continuidad.total_pagado_previa))
            if bloque_continuidad is not None
            else None
        )

        cantidad_visitas = tipo.datos.cantidad_visitas
        if cantidad_visitas is not None and cantidad_visitas < 1:
            raise HttpError(400, "cantidad_visitas debe ser >= 1")

        patch_input = CotizarEdicionVisitasInput(
            cantidad_visitas=cantidad_visitas,
            tarifa_visitas_id=str(tipo.tarifa.tarifa_visitas_id) if tipo.tarifa.tarifa_visitas_id else None,
            modo=modo,
            total_pagado_previa=total_pagado_previa,
        )

        # 3. Quote (read-only, no DB mutation)
        quote_service = LiquidacionCotizarEdicionVisitasService()
        return quote_service.cotizar_edicion(lg, patch_input)
