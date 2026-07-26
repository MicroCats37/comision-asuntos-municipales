"""
ImpactoVialFlujo — flujo transaccional para creación de liquidaciones de Impacto Vial.

Patrón:Replica la estructura de LiquidacionesEdificacionesFlujo.
El flujo es @transaction.atomic y usa sync_to_async para operaciones ORM.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from asgiref.sync import sync_to_async
from injector import inject

from modules.liquidaciones.domain.services.core.impacto_vial_core import (
    ImpactoVialCoreService,
)
from modules.liquidaciones.domain.services.core.proyecto_core_service import (
    ProyectoService,
)
from modules.liquidaciones.domain.services.builders.impacto_vial_result_builder import (
    ImpactoVialResultBuilder,
)
from modules.liquidaciones.domain.schemas_proyecto import ProyectoInlineData
from modules.liquidaciones.domain.schemas import ProyectistaInlineData
from modules.liquidaciones.domain.constants import TipoLiquidacion, TramiteAccion
from modules.liquidaciones.models import LiquidacionProyectista
from modules.usuarios.infrastructure.services import ICipClient
from modules.usuarios.domain.services.core.perfil_ingeniero_core_service import PerfilIngenieroCoreService


class ImpactoVialFlujo:
    """
    Flujo transaccional para crear liquidaciones de Impacto Vial.

    Coordina: Proyecto (get/upsert) → LiquidacionGeneral →
              LiquidacionImpactoVial → LiquidacionPorcentajeObra.

    Cálculo: porcentaje del valor de obra (Edificaciones-style) con IGV.
    """

    @inject
    def __init__(
        self,
        core: ImpactoVialCoreService,
        proyecto_service: ProyectoService,
        cip_client: ICipClient,
        perfil_ingeniero_core: PerfilIngenieroCoreService,
    ):
        self.core = core
        self._proyecto_service = proyecto_service
        self._cip_client = cip_client
        self._perfil_ingeniero_core = perfil_ingeniero_core

    async def _proceso_creacion(
        self,
        proyecto_public_id: Optional[str],
        municipalidad_id: str,
        valor_proyecto: Decimal,
        expediente: Optional[str],
        observacion: Optional[str],
        proyecto_inline: Optional[ProyectoInlineData] = None,
        tarifa_id: Optional[str] = None,
        proyectistas_inline: Optional[list[ProyectistaInlineData]] = None,
    ):
        """
        Proceso de creación de primera revisión de Impacto Vial.

        1. Obtener o crear proyecto (inline o por public_id)
        2. Buscar municipalidad por ID
        3. Buscar/validar tarifa porcentual:
           - Si tarifa_id proporcionado: usar ese ID y validar que corresponde a IMPACTO_VIAL + tramite_accion
           - Si no: auto-seleccionar por reglas (tipo_liquidacion + tramite_accion)
        4. Si hay proyectistas_inline, validar CIPs (ALL-OR-NOTHING)
        5. En transacción atómica:
           a. Crear LiquidacionGeneral
           b. Crear LiquidacionImpactoVial
           c. Upsert proyectistas si hay
           d. Crear LiquidacionPorcentajeObra
           e. Guardar sub_total en LiquidacionGeneral
        6. Construir y retornar resultado tipado
        """
        # 1. Obtener o crear proyecto
        if proyecto_inline:
            proyecto = await sync_to_async(
                self._proyecto_service._crear_proyecto_inline
            )(proyecto_inline)
        else:
            proyecto = await sync_to_async(
                self._proyecto_service._buscar_por_public_id
            )(proyecto_public_id)
            if not proyecto:
                from modules.liquidaciones.domain.exceptions import (
                    ProyectoNotFoundError,
                )
                raise ProyectoNotFoundError(
                    f"Proyecto con public_id={proyecto_public_id} no encontrado"
                )

        # 2. Buscar municipalidad
        municipalidad = await self._get_municipalidad_model(municipalidad_id)
        if not municipalidad:
            from modules.liquidaciones.domain.exceptions import NotFoundError

            raise NotFoundError(f"Municipalidad con id={municipalidad_id}")

        # 3. Buscar/validar tarifa porcentual
        try:
            if tarifa_id:
                tarifa_porc = await sync_to_async(self.core._validar_tarifa_porcentaje_por_id)(
                    tarifa_id=tarifa_id,
                    tipo_liquidacion=TipoLiquidacion.IMPACTO_VIAL,
                    tramite_accion=TramiteAccion.PRIMERA_REVISION,
                )
            else:
                tarifa_porc = await sync_to_async(self.core._buscar_tarifa_porcentaje)(
                    TramiteAccion.PRIMERA_REVISION
                )
        except ValueError as e:
            from modules.liquidaciones.domain.exceptions import NotFoundError

            raise NotFoundError(str(e))

        # 4. Si hay proyectistas_inline (inline con CIP), validar TODOS los CIPs
        # ALL-OR-NOTHING: si cualquier CIP falla o no está habilitado, se rechaza toda la operación
        if proyectistas_inline:
            await self._validar_proyectistas_inline_cip(proyectistas_inline)

        # Ejecutar bloque transaccional
        def _run_creacion():
            from django.db import transaction

            with transaction.atomic():
                # 5a. Crear LiquidacionGeneral
                liquidacion = self.core._crear_liquidacion_general_nueva(
                    proyecto=proyecto,
                    municipalidad=municipalidad,
                    tipo_liquidacion="IMPACTO_VIAL",
                    expediente=expediente,
                    observacion=observacion,
                    numero_revision=1,
                )

                # 5b. Crear LiquidacionImpactoVial
                liq_iv = self.core._crear_liquidacion_impacto_vial(
                    liquidacion_general=liquidacion,
                    tramite_accion=TramiteAccion.PRIMERA_REVISION,
                )

                # 5c. Upsert proyectistas si hay inline data
                if proyectistas_inline:
                    proyectistas_ids = self._upsert_proyectistas_inline(
                        proyectistas_inline, municipalidad_id
                    )
                    for pid in proyectistas_ids:
                        LiquidacionProyectista.objects.create(
                            liquidacion_general=liq_iv.liquidacion,
                            proyectista_id=pid,
                        )

                # 5d. Crear LiquidacionPorcentajeObra
                # Para Impacto Vial: valor_base_calculo = valor_proyecto (same as Edificaciones)
                valor_proyecto_dec = Decimal(str(valor_proyecto))
                liquidacion_porc = self.core._crear_calculo_porcentaje(
                    liquidacion_general=liquidacion,
                    valor_proyecto=valor_proyecto_dec,
                    valor_base_calculo=valor_proyecto_dec,
                    tarifa_porcentaje=tarifa_porc,
                )

                # 5e. Calcular derecho con mínimo UIT y guardar sub_total
                # monto_base = valor_base_calculo * porcentaje_liquidacion
                monto_base = valor_proyecto_dec * tarifa_porc.porcentaje_liquidacion
                # derecho = clamp(monto_base, derecho_minimo, derecho_maximo)
                derecho = monto_base
                if monto_base < tarifa_porc.derecho_minimo:
                    derecho = tarifa_porc.derecho_minimo
                if tarifa_porc.derecho_maximo is not None and derecho > tarifa_porc.derecho_maximo:
                    derecho = tarifa_porc.derecho_maximo

                liquidacion.sub_total = derecho
                liquidacion.save(update_fields=["sub_total"])

                # 6. Construir resultado
                igv_valor = (
                    Decimal(str(liquidacion.igv.valor))
                    if liquidacion.igv
                    else Decimal("0.18")
                )
                igv_monto = derecho * igv_valor
                total_liquidacion = derecho + igv_monto

                result = ImpactoVialResultBuilder.build_result_porcentaje(
                    liquidacion=liquidacion,
                    proyecto=proyecto,
                    liquidacion_porcentaje=liquidacion_porc,
                    subtotal=derecho,
                    igv_valor=igv_valor,
                    igv_monto=igv_monto,
                    total_liquidacion=total_liquidacion,
                )
                return result

        return await sync_to_async(_run_creacion, thread_sensitive=True)()

    async def _get_municipalidad_model(self, municipalidad_id: str):
        """Obtiene modelo Municipalidad por ID."""
        from modules.entidades.models import Municipalidad

        return await sync_to_async(
            lambda: (
                Municipalidad.objects.filter(id=municipalidad_id)
                .select_related("provincia", "distrito")
                .first()
            )
        )()

    async def _validar_proyectistas_inline_cip(self, proyectistas_inline: list[ProyectistaInlineData]):
        """
        Valida TODOS los CIPs de los proyectistas inline antes de crear la liquidación.

        ALL-OR-NOTHING: Si cualquier CIP falla o no está habilitado, se rechaza toda la operación.
        """
        from core.exceptions import CipNotFoundError, CipServiceUnavailableError
        from modules.usuarios.domain.schemas.ingeniero_habilitado_schemas import CipColegiadoData

        for p in proyectistas_inline:
            cip = p.cip
            if not cip:
                from modules.liquidaciones.domain.exceptions import BusinessError
                raise BusinessError(f"CIP es requerido para cada proyectista")

            # Normalizar CIP
            normalized_cip = self._perfil_ingeniero_core._normalizar_cip(cip)
            if not normalized_cip:
                from modules.liquidaciones.domain.exceptions import BusinessError
                raise BusinessError(f"CIP inválido: {cip}")

            # Llamar al cliente CIP
            try:
                raw_data = await sync_to_async(self._cip_client.get_colegiado)(normalized_cip)
            except CipServiceUnavailableError as e:
                raise

            if raw_data is None:
                raise CipNotFoundError(cip=normalized_cip)

            # Parsear a CipColegiadoData para acceso tipado
            cip_data = CipColegiadoData(**raw_data)

            # Validar que esté habilitado (condicion == '1')
            if not cip_data.habilitado:
                from modules.liquidaciones.domain.exceptions import BusinessError
                raise BusinessError(
                    f"El ingeniero con CIP {normalized_cip} no está habilitado "
                    f"(condicion={cip_data.condicion}). Solo ingenieros habilitados pueden ser agregados."
                )

    def _upsert_proyectistas_inline(
        self,
        proyectistas_inline: list[ProyectistaInlineData],
        municipalidad_id: str,
    ) -> list[str]:
        """
        Crea/actualiza PerfilIngeniero y Proyectista para cada item inline.

        Dentro de transaction.atomic (ya abierto por el llamador).
        """
        from modules.usuarios.domain.schemas.ingeniero_habilitado_schemas import CipColegiadoData
        from modules.liquidaciones.domain.models import Especialidad

        proyectista_ids = []

        for p in proyectistas_inline:
            cip = p.cip
            especialidad_id = p.especialidad_id
            descripcion = p.descripcion

            # Normalizar CIP
            normalized_cip = self._perfil_ingeniero_core._normalizar_cip(cip)

            # Obtener datos del CIP (en este punto ya fueron validados)
            raw_data = self._cip_client.get_colegiado(normalized_cip)
            if not raw_data:
                from core.exceptions import CipNotFoundError
                raise CipNotFoundError(cip=normalized_cip)

            # Mapear a CipColegiadoData
            cip_data = CipColegiadoData(**raw_data)

            # Upsert PerfilIngeniero
            perfil, _ = self._perfil_ingeniero_core._upsert_perfil_from_cip(normalized_cip, cip_data)

            # Obtener especialidad
            try:
                especialidad = Especialidad.objects.get(id=especialidad_id)
            except Especialidad.DoesNotExist:
                from modules.liquidaciones.domain.exceptions import NotFoundError
                raise NotFoundError(f"Especialidad con id={especialidad_id}")

            # Upsert Proyectista
            from modules.liquidaciones.domain.models import Proyectista
            proyectista, created = Proyectista.objects.update_or_create(
                perfil_ingeniero=perfil,
                especialidad=especialidad,
                defaults={'descripcion': descripcion or ''}
            )
            proyectista_ids.append(str(proyectista.id))

        return proyectista_ids

    async def _proceso_cotizar_primera_revision(
        self,
        tipo_liquidacion: str,
        valor_proyecto: float,
        tarifa_id: str | None = None,
    ):
        """
        Cotiza primera revisión de Impacto Vial sin guardar en BD.

        Cálculo: porcentaje del valor de obra (Edificaciones-style) con IGV.

        1. Obtener IGV/UIT vigentes
        2. Buscar/validar tarifa porcentual:
           - Si tarifa_id proporcionado: usar ese ID y validar que corresponde a IMPACTO_VIAL
           - Si no: auto-seleccionar por reglas (tipo_liquidacion + tramite_accion)
        3. Calcular usando helpers (sin persistencia)
        4. Retornar resultado de cotización

        No crea ningún registro en BD.

        Args:
            tipo_liquidacion: Tipo de liquidación (debe ser IMPACTO_VIAL).
            valor_proyecto: Valor del proyecto en soles.
            tarifa_id: ID de la tarifa específica a usar (opcional).

        Returns:
            CotizacionQuoteData (Edificaciones-style con IGV)
        """
        from decimal import Decimal

        from modules.liquidaciones.domain.schemas import (
            CotizacionQuoteData,
            CotizacionRevisionData,
            CotizacionTotalesData,
            CotizacionMetadataData,
            TarifaCalculoData,
        )

        # 1. Obtener IGV/UIT vigentes
        variables = await sync_to_async(self.core._obtener_variables_financieras_vigentes)()
        igv_valor, uit_valor = variables

        # 2. Buscar/validar tarifa porcentual
        try:
            if tarifa_id:
                tarifa_porc = await sync_to_async(self.core._validar_tarifa_porcentaje_por_id)(
                    tarifa_id=tarifa_id,
                    tipo_liquidacion=tipo_liquidacion,
                    tramite_accion=TramiteAccion.PRIMERA_REVISION,
                )
            else:
                tarifa_porc = await sync_to_async(self.core._buscar_tarifa_porcentaje)(
                    TramiteAccion.PRIMERA_REVISION
                )
        except ValueError as e:
            from modules.liquidaciones.domain.exceptions import NotFoundError
            raise NotFoundError(str(e))

        # 3. Calcular (sin persistencia) — Edificaciones-style
        valor_proyecto_dec = Decimal(str(valor_proyecto))
        valor_base_calculo = valor_proyecto_dec  # Para IV: igual al valor_proyecto
        monto_base = valor_base_calculo * tarifa_porc.porcentaje_liquidacion

        # Aplicar derecho mínimo y máximo
        derecho = monto_base
        if monto_base < tarifa_porc.derecho_minimo:
            derecho = tarifa_porc.derecho_minimo
        if tarifa_porc.derecho_maximo is not None and derecho > tarifa_porc.derecho_maximo:
            derecho = tarifa_porc.derecho_maximo

        # Calcular totales con IGV
        subtotal = derecho
        igv_monto = subtotal * igv_valor
        total_liquidacion = subtotal + igv_monto

        # 4. Retornar resultado de cotización (Edificaciones-style)
        return CotizacionQuoteData(
            numero_revision=1,
            revisiones=[
                CotizacionRevisionData(
                    id=tarifa_porc.tarifa_base.id,
                    especialidades=[],
                    tarifa=TarifaCalculoData(
                        id=tarifa_porc.id,
                        derecho_minimo=tarifa_porc.derecho_minimo,
                        derecho_maximo=tarifa_porc.derecho_maximo,
                        porcentaje_minimo_uit=tarifa_porc.porcentaje_minimo_uit,
                        porcentaje_liquidacion=tarifa_porc.porcentaje_liquidacion,
                    ),
                    monto_base=monto_base,
                    cobra=True,
                    derecho=derecho,
                )
            ],
            totales=CotizacionTotalesData(
                subtotal=subtotal,
                igv=igv_monto,
                total=total_liquidacion,
                liquidacion_total=total_liquidacion,
                total_a_pagar=total_liquidacion,
            ),
            metadata=CotizacionMetadataData(
                igv_valor=igv_valor,
                uit_valor=uit_valor,
                cobra=True,
                valor_base_calculo=valor_base_calculo,
            ),
        )
