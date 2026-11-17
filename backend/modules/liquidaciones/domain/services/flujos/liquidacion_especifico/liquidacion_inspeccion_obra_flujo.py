"""
Flujo para Inspección de Obra (Transaccional).
"""
from datetime import date
from typing import Optional
from django.db import IntegrityError, transaction
from injector import inject
from ninja.errors import HttpError
import uuid

from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_general_core_service import (
    LiquidacionGeneralCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_por_categoria_visitas_core_service import (
    LiquidacionPorCategoriaVisitasCoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_continuidad_visitas_core_service import (
    LiquidacionContinuidadVisitasCoreService,
)
from modules.liquidaciones.domain.schemas.liquidacion_especifico.inspeccion_obra_primera_revision_data import (
    InspeccionObraNuevaRevisionData,
)
from modules.liquidaciones.domain.schemas.liquidacion_legacy.legacy_registro_data import (
    LegacyRegistroContexto,
)
from modules.liquidaciones.domain.results.liquidacion_especifico.inspeccion_obra_primera_revision_result import (
    InspeccionObraPrimeraRevisionResult,
    LiquidacionEspecificaInspeccionObraResult,
)
from modules.liquidaciones.domain.results.liquidacion_general.liquidacion_general_result import (
    LiquidacionGeneralResult,
    ContactoResult,
)
from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_visitas_result import (
    LiquidacionVisitasResult,
    LiquidacionContinuidadVisitasResult,
    RegistroPagoResult,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.constants import (
    ModoCalculoLiquidacion,
    ModoCotizacionVisitas,
    TipoLiquidacion,
)


class LiquidacionInspeccionObraFlujo:
    """
    Flujo transaccional que orquesta la creación completa de Inspección de Obra.
    Usa el Core de General y el Core de Visitas.
    """

    @inject
    def __init__(
        self,
        general_core: LiquidacionGeneralCoreService,
        visitas_core: LiquidacionPorCategoriaVisitasCoreService,
        continuidad_core: LiquidacionContinuidadVisitasCoreService,
    ):
        self.general_core = general_core
        self.visitas_core = visitas_core
        self.continuidad_core = continuidad_core

    @transaction.atomic()
    def ejecutar_primera_revision_desde_previa(
        self,
        usuario_id: int,
        data: InspeccionObraNuevaRevisionData,
        liquidacion_previa,
        inspector_operacion,
    ) -> InspeccionObraPrimeraRevisionResult:
        """
        Crea una IO primera-revision heredando proyecto/municipalidad/entidad
        de una liquidación previa (Edificación o Habilitación Urbana).

        Diferencias respecto a ejecutar_primera_revision:
        - Entidad y Proyecto se HEREDAN de la liquidación previa (no se crean nuevos)
        - numero_revision = 1 (siempre)
        - Se crea LiquidacionInspector para asociar el inspector
        - No se usa upsert_contacto (el contacto viene en el dominio, no se pide en el input)

        inspector_operacion se pasa desde el orchestrator con la especialidad ya validada
        contra el tipo de la liquidación previa. Ya no se hace lookup ambiguo con .first().
        """
        # 1. Traer tarifa, UIT y calcular
        tarifa = self.visitas_core.get_tarifa_por_id(data.liquidacion_especifica.tarifa.tarifa_visitas_id)
        uit_vigente = self.general_core.get_uit_vigente()
        igv_vigente = self.general_core.get_igv_vigente()

        subtotal = self.visitas_core.calcular_subtotal_visitas(
            cantidad_visitas=data.liquidacion_especifica.datos.cantidad_visitas,
            tarifa=tarifa,
            uit_vigente=uit_vigente,
        )

        # 2. Entidad y Proyecto ya existen — clonar proyecto para aislar la revision
        proyecto = self.general_core.clone_proyecto_for_liquidacion(liquidacion_previa)
        entidad = proyecto.entidad if hasattr(proyecto, 'entidad') and proyecto.entidad else None

        # Contacto upsert by ALL fields (convert ContactoData to Contacto model instance)
        contacto = None
        if data.liquidacion_general.contacto:
            contacto = self.general_core.upsert_contacto(
                data.liquidacion_general.contacto.model_dump()
                if hasattr(data.liquidacion_general.contacto, "model_dump")
                else data.liquidacion_general.contacto.__dict__
            )

        # 3. Crear LiquidacionGeneral con totales finales (quote-first pattern).
        # sub_total and total include IGV in this flow.
        from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
        from modules.liquidaciones.domain.models.inspector import LiquidacionInspector

        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=str(liquidacion_previa.municipalidad_id),
            expediente=liquidacion_previa.expediente,
            observacion=liquidacion_previa.observacion,
            proyecto=proyecto,
            tipo_liquidacion=TipoLiquidacionModel.objects.get(codigo=TipoLiquidacion.INSPECCION_OBRA),
            numero_revision=1,
            denominacion_de_proyecto=liquidacion_previa.denominacion_de_proyecto,
            contacto=contacto,
            sub_total=subtotal,
            total=subtotal * (1 + igv_vigente.valor),
            igv_id=igv_vigente,
            uit_id=uit_vigente,
            usuario_creador_id=usuario_id,
        )

        # 5. Crear Tipo: LiquidacionPorCategoriaVisitas
        liquidacion_visitas = self.visitas_core.crear_liquidacion_tipo_visitas(
            liquidacion_general=liquidacion_general,
            data=data.liquidacion_especifica,
        )

        # 6. Crear Específico: LiquidacionInspeccionObra
        liquidacion_io = LiquidacionInspeccionObra.objects.create(
            liquidacion=liquidacion_general,
        )

        # 7. Crear LiquidacionInspector (asocia el inspector a la IO)
        # especialidad_revision, inspector y inspector_operacion vienen directamente
        # de inspector_operacion (ya validado en el orchestrator contra tipo_previo).
        LiquidacionInspector.objects.create(
            liquidacion=liquidacion_visitas,
            inspector=inspector_operacion.inspector,
            inspector_operacion=inspector_operacion,
            especialidad_revision_id=inspector_operacion.especialidad_revision_id,
        )

        # 8. Mapear a Result puro (reutiliza la lógica de mapeo de ejecutar_primera_revision)
        liquidacion_general.refresh_from_db()
        return self._build_result_from_orm(
            liquidacion_general=liquidacion_general,
            liquidacion_io=liquidacion_io,
            liquidacion_visitas=liquidacion_visitas,
            proyecto=proyecto,
            entidad=entidad,
            usuario_id=usuario_id,
        )

    @transaction.atomic()
    def ejecutar_nueva_liquidacion(
        self,
        usuario_id: int,
        data: InspeccionObraNuevaRevisionData,
        inspector,
        inspector_operacion=None,
        registro_legacy: LegacyRegistroContexto | None = None,
    ) -> InspeccionObraPrimeraRevisionResult:
        """
        Crea una IO primera-revision SIN liquidación previa.
        Entidad y Proyecto se crean desde cero a partir de los datos del usuario.
        Numero_revision = 1. No requiere liquidacion_previa_id.

        Diferencias respecto a ejecutar_primera_revision_desde_previa:
        - Entidad y Proyecto se CREAN desde cero (no se heredan de previa).
        - La especialidad_revision del inspector se resuelve desde inspector_operacion
          cuando está disponible (passed from mutation input, obtained from
          /seleccionables endpoint). Ya NO se consulta por tipo INSPECCION_OBRA.
          Los inspectores NO se registran con tipo INSPECCION_OBRA — se registran
          con el tipo del trámite que pueden revisar (EDIFICACION/HABILITACION_URBANA).

        Registro legacy (`registro_legacy`):
        - usa el IGV/UIT y la tarifa de visitas resueltos por el orchestrator
          para `fecha_registro` (nunca los vigentes de hoy);
        - persiste `fecha_registro` explícita y `legacy=True`;
        - persiste el `numero` explícito del registro;
        - NO crea vínculo de inspector (`LiquidacionInspector`): el registro
          legacy no tiene `inspector_operacion_id`.
        """
        from decimal import Decimal

        # 1. Traer tarifa, UIT y IGV
        if registro_legacy is not None:
            # Registro legacy: valores YA resueltos por el orchestrator para la
            # fecha efectiva del registro (nunca los vigentes de hoy).
            tarifa = registro_legacy.tarifa
            uit_vigente = registro_legacy.uit
            igv_vigente = registro_legacy.igv
        else:
            tarifa = self.visitas_core.get_tarifa_por_id(data.liquidacion_especifica.tarifa.tarifa_visitas_id) if data.liquidacion_especifica.tarifa.tarifa_visitas_id else None
            uit_vigente = self.general_core.get_uit_vigente()
            igv_vigente = self.general_core.get_igv_vigente()

        # 2. Calcular subtotal (si hay tarifa — legacy CATEGORIA=0 path may have None)
        if tarifa:
            subtotal = self.visitas_core.calcular_subtotal_visitas(
                cantidad_visitas=data.liquidacion_especifica.datos.cantidad_visitas,
                tarifa=tarifa,
                uit_vigente=uit_vigente,
            )
        else:
            # Legacy path: subtotal will be 0; caller should handle override via separate path
            subtotal = Decimal("0")

        # 3. Crear Entidad desde cero
        gen_data = data.liquidacion_general
        entidad = self.general_core.create_entidad(
            tipo_documento=gen_data.proyecto.entidad.tipo_documento,
            numero_documento=gen_data.proyecto.entidad.numero_documento,
        )

        # 4. Crear Proyecto desde cero
        proyecto_data = {
            "nombre_propietario": gen_data.proyecto.nombre_propietario,
            "direccion": gen_data.proyecto.direccion,
            "distrito_id": gen_data.proyecto.distrito_id,
            "entidad_razon_social": gen_data.proyecto.entidad_razon_social,
            "entidad_tipo_documento": gen_data.proyecto.entidad.tipo_documento,
            "entidad_numero_documento": gen_data.proyecto.entidad.numero_documento,
        }
        proyecto = self.general_core.create_proyecto(proyecto_data, entidad)

        # 5. Upsert contacto si está presente
        contacto = None
        if gen_data.contacto:
            contacto = self.general_core.upsert_contacto(
                gen_data.contacto.model_dump()
                if hasattr(gen_data.contacto, "model_dump")
                else gen_data.contacto.__dict__
            )

        # 6. Crear LiquidacionGeneral con totales (quote-first pattern)
        from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
        from modules.liquidaciones.domain.models.inspector import LiquidacionInspector

        total = subtotal * (1 + igv_vigente.valor)

        # ── CONTINUIDAD (opcional) ────────────────────────────────────────────
        # Sin continuidad: `sub_total` = valor completo del trabajo (vigente).
        # Con continuidad: `sub_total`/`total` = la DIFERENCIA a cobrar, y el
        # valor completo del trabajo queda congelado en la fila de continuidad.
        #
        # El MOTOR ÚNICO (C-6) resuelve valor completo, crédito y diferencia en
        # UN solo lugar: lo que se persiste es EXACTAMENTE lo que devolvió la
        # cotización (paridad al céntavo, DD-3/R2).
        continuidad = data.liquidacion_especifica.continuidad
        sub_total = subtotal
        monto_acumulado = None
        total_acumulado = None
        if continuidad is not None and tarifa is not None:
            contexto = self.visitas_core.construir_contexto_visitas(
                modo=ModoCotizacionVisitas.CONTINUAR,
                cantidad_visitas=data.liquidacion_especifica.datos.cantidad_visitas,
                porcentaje_uit=Decimal(str(tarifa.porcentaje_uit)),
                uit_valor=Decimal(str(uit_vigente.valor)),
                igv_porcentaje=Decimal(str(igv_vigente.valor)),
                categoria=tarifa.categoria_visitas,
                tarifa_id=str(tarifa.id),
                # El BRUTO declarado MANDA: el motor deriva el par (neto, bruto)
                # con el IGV vigente. Si no viene, el motor usa el par ya
                # resuelto por el orquestador (neto + bruto congelado).
                total_pagado_previa=continuidad.total_pagado_previa,
                credito_neto=(
                    None
                    if continuidad.total_pagado_previa is not None
                    else continuidad.subtotal_credito
                ),
                credito_bruto=(
                    None
                    if continuidad.total_pagado_previa is not None
                    else continuidad.total_credito
                ),
                uit_id=str(uit_vigente.id),
                igv_id=str(igv_vigente.id),
            )
            estrategia = self.visitas_core.calcular_cotizacion_visitas_estrategia(
                contexto
            )
            bloque = estrategia.continuidad
            monto_acumulado = bloque.valor_completo_neto
            total_acumulado = bloque.valor_completo_bruto
            sub_total = bloque.diferencia_neto
            total = bloque.diferencia_bruto
        elif continuidad is not None:
            # Registro manual/legacy (CATEGORIA=0): no hay tarifa que repreciar
            # y, por tanto, no hay valor completo que el MOTOR pueda resolver.
            # Se conserva la aritmética vigente.
            monto_acumulado, total_acumulado = (
                self.continuidad_core.calcular_montos_acumulados(
                    monto_neto_visitas=subtotal,
                    igv_valor=igv_vigente.valor,
                )
            )
            sub_total, total = self.continuidad_core.calcular_diferencia(
                monto_acumulado=monto_acumulado,
                total_acumulado=total_acumulado,
                subtotal_credito=continuidad.subtotal_credito,
                total_credito=continuidad.total_credito,
            )

        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=str(gen_data.municipalidad_id),
            expediente=gen_data.expediente,
            observacion=gen_data.observacion,
            proyecto=proyecto,
            tipo_liquidacion=TipoLiquidacionModel.objects.get(codigo=TipoLiquidacion.INSPECCION_OBRA),
            numero_revision=1,
            denominacion_de_proyecto=gen_data.denominacion_de_proyecto,
            contacto=contacto,
            sub_total=sub_total,
            total=total,
            igv_id=igv_vigente,
            uit_id=uit_vigente,
            usuario_creador_id=usuario_id,
            fecha_registro=(
                registro_legacy.fecha_registro if registro_legacy is not None else None
            ),
            legacy=registro_legacy is not None,
        )

        # 7. Crear Tipo: LiquidacionPorCategoriaVisitas
        liquidacion_visitas = self.visitas_core.crear_liquidacion_tipo_visitas(
            liquidacion_general=liquidacion_general,
            data=data.liquidacion_especifica,
        )

        # 7b. Crear la fila de continuidad (misma transaction.atomic que B).
        #     La fila es la que congela el valor completo del trabajo y el
        #     crédito de la previa, y la que habilita la base RH condicional.
        continuidad_row = None
        if continuidad is not None:
            continuidad_row = self.continuidad_core.crear_continuidad(
                liquidacion_visitas=liquidacion_visitas,
                monto_acumulado=monto_acumulado,
                total_acumulado=total_acumulado,
                subtotal_credito=continuidad.subtotal_credito,
                total_credito=continuidad.total_credito,
                liquidacion_previa=continuidad.liquidacion_previa,
                visitas_previas_totales=continuidad.visitas_previas_totales,
                visitas_previas_pendientes=continuidad.visitas_previas_pendientes,
                categoria_previa=continuidad.categoria_previa,
                observacion=continuidad.observacion,
            )

        # 8. Crear Específico: LiquidacionInspeccionObra
        liquidacion_io = LiquidacionInspeccionObra.objects.create(
            liquidacion=liquidacion_general,
            numero=(
                registro_legacy.numero if registro_legacy is not None else None
            ),
        )

        # 9. Crear LiquidacionInspector
        # La especialidad_revision se resuelve desde inspector_operacion cuando
        # está disponible (inyectado desde el input, obtenido de /seleccionables).
        # Ya NO se consulta por tipo INSPECCION_OBRA.
        # El registro legacy NO tiene inspector_operacion_id: en ese caso no se
        # crea el vínculo (LiquidacionInspector exige inspector y especialidad).
        if inspector is not None:
            LiquidacionInspector.objects.create(
                liquidacion=liquidacion_visitas,
                inspector=inspector,
                inspector_operacion=inspector_operacion,
                especialidad_revision_id=(
                    inspector_operacion.especialidad_revision_id
                    if inspector_operacion else None
                ),
            )

        # 10. Mapear a Result
        liquidacion_general.refresh_from_db()
        return self._build_result_from_orm(
            liquidacion_general=liquidacion_general,
            liquidacion_io=liquidacion_io,
            liquidacion_visitas=liquidacion_visitas,
            proyecto=proyecto,
            entidad=entidad,
            usuario_id=usuario_id,
            continuidad_row=continuidad_row,
        )

    def _build_result_from_orm(
        self,
        liquidacion_general,
        liquidacion_io,
        liquidacion_visitas,
        proyecto,
        entidad,
        usuario_id: int,
        continuidad_row=None,
    ) -> InspeccionObraPrimeraRevisionResult:
        """
        Construye InspeccionObraPrimeraRevisionResult a partir de objetos ORM.
        Delegates common ORM→Result mapping to core.
        """
        # Build ContactoResult inline (specific mapping not extracted to core)
        contacto_result = None
        if liquidacion_general.contacto:
            contacto = liquidacion_general.contacto
            contacto_result = ContactoResult(
                id=str(contacto.id),
                nombres=contacto.nombres,
                apellidos=contacto.apellidos,
                dni=contacto.dni,
                cargo=contacto.cargo,
                telefono=contacto.telefono,
                celular=contacto.celular,
                email=contacto.email,
            )

        # Delegates common mapping to core (uses denormalized proyecto fields)
        general_result = self.general_core.build_general_result(
            liquidacion_general=liquidacion_general,
            usuario_id=usuario_id,
            contacto_result=contacto_result,
            codigo_cta=self.general_core.get_codigo_cta(
                liquidacion_general.tipo_liquidacion
            ),
        )

        tipo_result = LiquidacionVisitasResult(
            id=str(liquidacion_visitas.id),
            cantidad_visitas=liquidacion_visitas.cantidad_visitas,
            porcentaje_uit=liquidacion_visitas.porcentaje_uit,
            categoria=liquidacion_visitas.categoria,
            tarifa_aplicada_id=str(liquidacion_visitas.tarifa_aplicada_id) if liquidacion_visitas.tarifa_aplicada_id else None,
            inspectores=self._build_inspectores_result(liquidacion_visitas),
            registros_pago=self._build_registros_pago_result(liquidacion_visitas),
            continuidad=self._build_continuidad_result(liquidacion_visitas, continuidad_row),
        )

        especifico_result = LiquidacionEspecificaInspeccionObraResult(
            id=str(liquidacion_io.id),
            numero=liquidacion_io.numero,
        )

        return InspeccionObraPrimeraRevisionResult(
            liquidacion_general=general_result,
            liquidacion_tipo=tipo_result,
            liquidacion_especifica=especifico_result,
        )

    @staticmethod
    def _build_continuidad_result(liquidacion_visitas, continuidad_row=None):
        """
        Construye el LiquidacionContinuidadVisitasResult de la IO.

        Devuelve None cuando la IO NO tiene fila de continuidad (caso normal:
        IO sin continuidad → comportamiento idéntico al vigente).

        `continuidad_row` permite evitar una consulta extra cuando la fila
        acaba de crearse en el mismo flujo.
        """
        if continuidad_row is None:
            from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
                LiquidacionContinuidadVisitas,
            )

            try:
                continuidad_row = liquidacion_visitas.continuidad
            except LiquidacionContinuidadVisitas.DoesNotExist:
                return None

        if continuidad_row is None:
            return None

        return LiquidacionContinuidadVisitasResult(
            id=str(continuidad_row.id),
            liquidacion_previa_id=(
                str(continuidad_row.liquidacion_previa_id)
                if continuidad_row.liquidacion_previa_id
                else None
            ),
            monto_acumulado=continuidad_row.monto_acumulado,
            total_acumulado=continuidad_row.total_acumulado,
            subtotal_credito=continuidad_row.subtotal_credito,
            total_credito=continuidad_row.total_credito,
            visitas_previas_totales=continuidad_row.visitas_previas_totales,
            visitas_previas_pendientes=continuidad_row.visitas_previas_pendientes,
            categoria_previa=continuidad_row.categoria_previa,
            observacion=continuidad_row.observacion,
        )

    @staticmethod
    def _build_inspectores_result(liquidacion_visitas) -> list:
        """
        Construye los LiquidacionInspectorResult de la IO (asociados al tipo
        LiquidacionPorCategoriaVisitas, no a la general). Retorna [] si no hay.

        Reutiliza PerfilIngenieroResult (dominio de inspector) en lugar de
        duplicar los campos del perfil de ingeniero.
        """
        from modules.liquidaciones.domain.results.liquidacion_tipo.liquidacion_visitas_result import (
            LiquidacionInspectorResult,
            EspecialidadRevisionResult,
        )
        from modules.liquidaciones.domain.results.inspector.inspector_result import (
            PerfilIngenieroResult,
        )
        from modules.liquidaciones.domain.models.inspector import LiquidacionInspector

        inspectores = (
            LiquidacionInspector.objects
            .filter(liquidacion=liquidacion_visitas)
            .select_related(
                "inspector__perfil_ingeniero",
                "especialidad_revision",
            )
            .order_by("created_at")
        )

        resultados = []
        for li in inspectores:
            if not li.inspector_id:
                continue
            perfil = li.inspector.perfil_ingeniero
            resultados.append(
                LiquidacionInspectorResult(
                    id=str(li.id),
                    inspector_id=str(li.inspector_id),
                    inspector_operacion_id=str(li.inspector_operacion_id) if li.inspector_operacion else None,
                    perfil_ingeniero=PerfilIngenieroResult(
                        id=str(perfil.id),
                        cip=perfil.cip,
                        dni=perfil.dni,
                        nombres=perfil.nombres,
                        apellido_paterno=perfil.apellido_paterno,
                        apellido_materno=perfil.apellido_materno,
                        nombre_completo=perfil.nombre_completo,
                        correo_personal=perfil.correo_personal,
                        correo_institucional=perfil.correo_institucional,
                    ),
                    especialidad_revision=(
                        EspecialidadRevisionResult(
                            id=str(li.especialidad_revision.id),
                            nombre=li.especialidad_revision.nombre,
                        )
                        if li.especialidad_revision
                        else None
                    ),
                    dictamen_revision=li.dictamen_revision,
                    fecha_presentacion=str(li.fecha_presentacion) if li.fecha_presentacion else None,
                    fecha_revision=str(li.fecha_revision) if li.fecha_revision else None,
                )
            )
        return resultados

    @staticmethod
    def _build_registros_pago_result(liquidacion_visitas) -> list:
        """
        Construye los RegistroPagoResult de la IO (asociados al tipo
        LiquidacionPorCategoriaVisitas). Retorna [] si no hay.

        Los registros_pago vienen prefetched desde el core service
        (liquidacion_visitas__registros_pago).
        """
        resultados = []
        # Use prefetched relation if available, otherwise query
        if hasattr(liquidacion_visitas, 'registros_pago'):
            # If it's a prefetched queryset, use it; otherwise iterate
            try:
                registros = liquidacion_visitas.registros_pago.all()
            except AttributeError:
                # Not prefetched, access the related manager
                registros = liquidacion_visitas.registros_pago.all()
        else:
            return resultados

        for rp in registros:
            periodo = rp.periodo
            mes = rp.mes
            if isinstance(periodo, str) and "-" in periodo:
                year_part, month_part = periodo.split("-", 1)
                periodo = int(year_part) if year_part.isdigit() else None
                mes = mes or (int(month_part) if month_part.isdigit() else None)
            if mes is None and rp.fecha_registro:
                mes = rp.fecha_registro.month
            resultados.append(
                RegistroPagoResult(
                    id=str(rp.id),
                    periodo=periodo,
                    mes=mes,
                    inspecciones_pagadas=rp.inspecciones_pagadas,
                    fecha_registro=rp.fecha_registro,
                )
            )
        return resultados

    @transaction.atomic()
    def ejecutar_legacy_desde_previa(
        self,
        usuario_id: int,
        data: InspeccionObraNuevaRevisionData,
        liquidacion_previa,
        inspector,
        igv,
        uit,
        numero_revision: int,
        fecha_registro: date,
        override_subtotal: "Decimal | None" = None,
        override_total: "Decimal | None" = None,
    ) -> InspeccionObraPrimeraRevisionResult:
        """
        Legacy first revision for Inspección de Obra using historical fecha_registro.

        Mirrors ejecutar_primera_revision_desde_previa but:
        - Uses passed igv/uit ORM objects for FKs on liquidacion_general (not vigente lookup)
        - Sets explicit fecha_registro after create_liquidacion_general
        - Sets numero_revision from parameter (not hardcoded to 1)
        - Sets usuario_creador_id
        - When override_subtotal/override_total are provided: bypasses the IO formula
          (subtotal = cantidad_visitas * porcentaje_uit * uit) and uses the legacy values directly

        The override bypass is used when `cotizacion_legacy` is present in the legacy input
        payload — the source legacy sub_total/total are persisted as-is (verification/
        comparison is done via cotizar_legacy_proceso separately).
        """
        # 1. Traer tarifa, UIT y calcular
        # When tarifa_visitas_id is None (legacy CATEGORIA=0 path), tarifa stays None
        # and the caller must provide override_subtotal/override_total.
        tarifa_id = data.liquidacion_especifica.tarifa.tarifa_visitas_id
        tarifa = self.visitas_core.get_tarifa_por_id(tarifa_id) if tarifa_id else None

        is_null_tariff_path = (
            override_subtotal is not None
            and override_total is not None
            and tarifa is None
        )

        if override_subtotal is not None and override_total is not None:
            # Bypass IO formula — use legacy totals directly (cotizacion_legacy was provided)
            subtotal = override_subtotal
            total = override_total
        else:
            # Normal path: calculate subtotal via IO formula
            if tarifa is None:
                raise HttpError(
                    400,
                    "No se proporcionó tarifa y no hay totales override para legacy. "
                    "No se puede calcular el subtotal para Inspección de Obra.",
                )
            subtotal = self.visitas_core.calcular_subtotal_visitas(
                cantidad_visitas=data.liquidacion_especifica.datos.cantidad_visitas,
                tarifa=tarifa,
                uit_vigente=uit,
            )
            total = subtotal * (1 + igv.valor)

        # 2. Entidad y Proyecto ya existen — clonar proyecto para aislar la revision
        proyecto = self.general_core.clone_proyecto_for_liquidacion(liquidacion_previa)
        entidad = proyecto.entidad if hasattr(proyecto, 'entidad') and proyecto.entidad else None

        # 3. Crear LiquidacionGeneral con totales finales (quote-first pattern).
        # sub_total and total include IGV in this flow.
        # When is_null_tariff_path: set modo_calculo=MANUAL to flag this as a legacy
        # record with no associated tariff (CATEGORIA=0 or unmatched tariff).
        from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
        from modules.liquidaciones.domain.models.inspector import LiquidacionInspector

        modo_calculo = (
            ModoCalculoLiquidacion.MANUAL if is_null_tariff_path else None
        )

        liquidacion_general = self.general_core.create_liquidacion_general(
            municipalidad_id=str(liquidacion_previa.municipalidad_id),
            expediente=liquidacion_previa.expediente,
            observacion=liquidacion_previa.observacion,
            retencion=liquidacion_previa.retencion,
            proyecto=proyecto,
            tipo_liquidacion=TipoLiquidacionModel.objects.get(codigo=TipoLiquidacion.INSPECCION_OBRA),
            numero_revision=numero_revision,
            denominacion_de_proyecto=data.liquidacion_general.denominacion_de_proyecto,
            descripcion_legacy=data.liquidacion_general.descripcion_legacy,
            sub_total=subtotal,
            total=total,
            igv_id=igv,
            uit_id=uit,
            usuario_creador_id=usuario_id,
            fecha_registro=fecha_registro,
            modo_calculo=modo_calculo,
        )

        # 5. Crear Tipo: LiquidacionPorCategoriaVisitas
        liquidacion_visitas = self.visitas_core.crear_liquidacion_tipo_visitas(
            liquidacion_general=liquidacion_general,
            data=data.liquidacion_especifica,
        )

        # 6. Crear Específico: LiquidacionInspeccionObra
        liquidacion_io = LiquidacionInspeccionObra.objects.create(
            liquidacion=liquidacion_general,
        )

        # 7. Crear LiquidacionInspector (asocia el inspector a la IO)
        from modules.liquidaciones.domain.models.inspector import InspectorOperacion

        tipo_previa = liquidacion_previa.tipo_liquidacion.codigo
        especialidad_revision = (
            InspectorOperacion.objects
            .filter(
                inspector=inspector,
                tipo_liquidacion__codigo=tipo_previa,
            )
            .values_list("especialidad_revision_id", flat=True)
            .first()
        )
        if not especialidad_revision:
            raise HttpError(
                400,
                f"El inspector no tiene una operación vigente con especialidad "
                f"para el tipo '{tipo_previa}' de la liquidación previa.",
            )
        LiquidacionInspector.objects.create(
            liquidacion=liquidacion_visitas,
            inspector=inspector,
            especialidad_revision_id=especialidad_revision,
        )

        # 8. Mapear a Result puro
        liquidacion_general.refresh_from_db()
        return self._build_result_from_orm(
            liquidacion_general=liquidacion_general,
            liquidacion_io=liquidacion_io,
            liquidacion_visitas=liquidacion_visitas,
            proyecto=proyecto,
            entidad=entidad,
            usuario_id=usuario_id,
        )
