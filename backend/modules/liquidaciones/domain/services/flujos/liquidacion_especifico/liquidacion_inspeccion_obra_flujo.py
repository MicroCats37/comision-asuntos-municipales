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
from modules.liquidaciones.domain.schemas.liquidacion_especifico.inspeccion_obra_primera_revision_data import (
    InspeccionObraNuevaRevisionData,
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
    RegistroPagoResult,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion, ModoCalculoLiquidacion


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
    ):
        self.general_core = general_core
        self.visitas_core = visitas_core

    @transaction.atomic()
    def ejecutar_primera_revision_desde_previa(
        self,
        usuario_id: int,
        data: InspeccionObraNuevaRevisionData,
        liquidacion_previa,
        inspector,
    ) -> InspeccionObraPrimeraRevisionResult:
        """
        Crea una IO primera-revision heredando proyecto/municipalidad/entidad
        de una liquidación previa (Edificación o Habilitación Urbana).

        Diferencias respecto a ejecutar_primera_revision:
        - Entidad y Proyecto se HEREDAN de la liquidación previa (no se crean nuevos)
        - numero_revision = 1 (siempre)
        - Se crea LiquidacionInspector para asociar el inspector
        - No se usa upsert_contacto (el contacto viene en el dominio, no se pide en el input)
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
            retencion=liquidacion_previa.retencion,
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
        # La especialidad_revision se resuelve desde la operación del inspector
        # para el TIPO DE LA LIQUIDACIÓN PREVIA (EDIFICACION/HABILITACION_URBANA).
        # Los inspectores NO se registran con tipo INSPECCION_OBRA — se registran
        # con el tipo del trámite que pueden revisar (el de la previa).
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

    def _build_result_from_orm(
        self,
        liquidacion_general,
        liquidacion_io,
        liquidacion_visitas,
        proyecto,
        entidad,
        usuario_id: int,
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
        )

        tipo_result = LiquidacionVisitasResult(
            id=str(liquidacion_visitas.id),
            cantidad_visitas=liquidacion_visitas.cantidad_visitas,
            porcentaje_uit=liquidacion_visitas.porcentaje_uit,
            categoria=liquidacion_visitas.categoria,
            tarifa_aplicada_id=str(liquidacion_visitas.tarifa_aplicada_id) if liquidacion_visitas.tarifa_aplicada_id else None,
            inspectores=self._build_inspectores_result(liquidacion_visitas),
            registros_pago=self._build_registros_pago_result(liquidacion_visitas),
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
