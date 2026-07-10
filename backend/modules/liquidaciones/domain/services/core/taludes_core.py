"""Taludes Core — lógica de negocio para Taludes."""
from decimal import Decimal
from typing import Optional
from django.utils import timezone

from modules.liquidaciones.models import (
    LiquidacionGeneral,
    LiquidacionTaludes,
    LiquidacionPorMetroCuadrado,
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
    ReglaTarifaLiquidacion,
)
from modules.liquidaciones.domain.constants import (
    TipoLiquidacion,
    TramiteAccion,
)
from modules.liquidaciones.domain.services.core.calculos_helpers import (
    _calcular_monto_m2,
)
from core.utils import esta_vigente


class TaludesCoreService:
    """
    Servicio core sync para liquidaciones de Taludes.

    Crea LiquidacionGeneral + LiquidacionTaludes + LiquidacionPorMetroCuadrado.
    """

    def _crear_liquidacion_taludes(
        self,
        liquidacion_general: LiquidacionGeneral,
        tramite_accion: str = TramiteAccion.PRIMERA_REVISION,
    ) -> LiquidacionTaludes:
        """
        Crea el registro específico LiquidacionTaludes.

        Args:
            liquidacion_general: LiquidacionGeneral asociada.
            tramite_accion: Acción de trámite.

        Returns:
            LiquidacionTaludes creada.
        """
        return LiquidacionTaludes.objects.create(
            liquidacion=liquidacion_general,
            tramite_accion=tramite_accion,
        )

    def _buscar_tarifa_m2(self, tramite_accion: str) -> TarifaPorMetroCuadrado:
        """
        Busca tarifa M2 por ReglaTarifaLiquidacion.

        Args:
            tramite_accion: PRIMERA_REVISION o REVISION.

        Returns:
            TarifaPorMetroCuadrado vigente.

        Raises:
            ValueError: Si no existe o no está vigente.
        """
        # Buscar la regla para esta combinación
        regla = ReglaTarifaLiquidacion.objects.filter(
            tramite_accion=tramite_accion,
            tarifa_base__tipo_liquidacion=TipoLiquidacion.TALUDES,
        ).select_related("tarifa_base", "tarifa_base__detalle_m2").first()

        if regla is None:
            raise ValueError(
                f"No existe ReglaTarifaLiquidacion para "
                f"tipo_liquidacion={TipoLiquidacion.TALUDES} y tramite_accion={tramite_accion}. "
                f"Verifique que la tarifa esté configurada en el admin."
            )

        tarifa_base = regla.tarifa_base

        # Validar vigencia de la tarifa base
        if not esta_vigente(tarifa_base.periodo_inicio, tarifa_base.periodo_fin):
            raise ValueError(
                f"La tarifa base {tarifa_base.id} no está vigente "
                f"(periodo: {tarifa_base.periodo_inicio} - {tarifa_base.periodo_fin}). "
                f"Verifique que la fecha actual esté dentro del período."
            )

        # Obtener el detalle M2 (OneToOne desde TarifaLiquidacionBase)
        try:
            detalle_m2 = tarifa_base.detalle_m2
        except TarifaPorMetroCuadrado.DoesNotExist:
            raise ValueError(
                f"La tarifa base {tarifa_base.id} no tiene detalle TarifaPorMetroCuadrado. "
                f"Verifique que la tarifa M2 esté configurada."
            )

        if detalle_m2 is None:
            raise ValueError(
                f"La tarifa base {tarifa_base.id} no tiene detalle TarifaPorMetroCuadrado asociado."
            )

        return detalle_m2

    def _validar_tarifa_m2_por_id(
        self,
        tarifa_id: str,
        tipo_liquidacion: str,
        tramite_accion: str,
    ) -> TarifaPorMetroCuadrado:
        """
        Valida y retorna una tarifa M2 por su ID, verificando que corresponda
        al tipo_liquidacion + tramite_accion esperados.

        Args:
            tarifa_id: ID de la TarifaLiquidacionBase seleccionada.
            tipo_liquidacion: Valor de TipoLiquidacion esperado (ej. TALUDES).
            tramite_accion: Valor de TramiteAccion esperado (ej. PRIMERA_REVISION).

        Returns:
            TarifaPorMetroCuadrado validada.

        Raises:
            ValueError: Si la tarifa no existe, no está vigente, no tiene detalle_m2,
                        o su regla no corresponde al tipo_liquidacion + tramite_accion dados.
        """
        # Buscar la tarifa base por ID
        try:
            tarifa_base = TarifaLiquidacionBase.objects.select_related(
                "detalle_m2"
            ).get(id=tarifa_id)
        except TarifaLiquidacionBase.DoesNotExist:
            raise ValueError(
                f"La tarifa con id={tarifa_id} no existe."
            )

        # Validar vigencia
        if not esta_vigente(tarifa_base.periodo_inicio, tarifa_base.periodo_fin):
            raise ValueError(
                f"La tarifa {tarifa_id} no está vigente "
                f"(periodo: {tarifa_base.periodo_inicio} - {tarifa_base.periodo_fin})."
            )

        # Validar que tenga detalle M2
        try:
            detalle_m2 = tarifa_base.detalle_m2
        except TarifaPorMetroCuadrado.DoesNotExist:
            raise ValueError(
                f"La tarifa {tarifa_id} no es una tarifa por metro cuadrado "
                f"(no tiene detalle TarifaPorMetroCuadrado)."
            )

        if detalle_m2 is None:
            raise ValueError(
                f"La tarifa {tarifa_id} no tiene detalle TarifaPorMetroCuadrado asociado."
            )

        # Validar que la regla corresponda al tipo_liquidacion + tramite_accion
        regla = ReglaTarifaLiquidacion.objects.filter(
            tarifa_base=tarifa_base,
            tramite_accion=tramite_accion,
        ).select_related("tarifa_base").first()

        if regla is None:
            raise ValueError(
                f"La tarifa {tarifa_id} no tiene ReglaTarifaLiquidacion para "
                f"tramite_accion={tramite_accion}."
            )

        if tarifa_base.tipo_liquidacion != tipo_liquidacion:
            raise ValueError(
                f"La tarifa {tarifa_id} corresponde a tipo_liquidacion="
                f"{tarifa_base.tipo_liquidacion}, pero se esperaba "
                f"tipo_liquidacion={tipo_liquidacion}."
            )

        return detalle_m2

    def _crear_calculo_m2(
        self,
        liquidacion_general: LiquidacionGeneral,
        area_solicitada: Decimal,
        tarifa_m2: TarifaPorMetroCuadrado,
    ) -> LiquidacionPorMetroCuadrado:
        """
        Crea registro de cálculo LiquidacionPorMetroCuadrado.

        Args:
            liquidacion_general: LiquidacionGeneral asociada.
            area_solicitada: Área solicitada en m2.
            tarifa_m2: TarifaPorMetroCuadrado a aplicar.

        Returns:
            LiquidacionPorMetroCuadrado creada.
        """
        # Convertir area_solicitada a Decimal si viene como float/int
        area_solicitada_dec = Decimal(str(area_solicitada))

        area_calculo, derecho = _calcular_monto_m2(
            area_solicitada=area_solicitada_dec,
            costo_m2=tarifa_m2.costo_por_m2,
            area_m2=tarifa_m2.area_m2,
            derecho_minimo=tarifa_m2.derecho_minimo,
            derecho_maximo=tarifa_m2.derecho_maximo,
        )

        liquidacion_m2 = LiquidacionPorMetroCuadrado.objects.create(
            liquidacion_general=liquidacion_general,
            area_solicitada=area_solicitada,
            area_base_calculo=area_calculo,
            derecho=derecho,
            tarifa_aplicada=tarifa_m2,
        )

        return liquidacion_m2

    def _crear_liquidacion_general_nueva(
        self,
        proyecto,
        municipalidad,
        tipo_liquidacion: str,
        expediente: Optional[str] = None,
        observacion: Optional[str] = None,
        numero_revision: int = 1,
    ) -> LiquidacionGeneral:
        """
        Crea una LiquidacionGeneral para Taludes.

        Args:
            proyecto: Proyecto asociado.
            municipalidad: Municipaliddad asociada.
            tipo_liquidacion: Valor de TipoLiquidacion (TALUDES).
            expediente: Número de expediente (opcional).
            observacion: Observaciones (opcional).
            numero_revision: Número de revisión (default 1 para primera).

        Returns:
            LiquidacionGeneral creada.

        Raises:
            ValueError: Si IGV o UIT no están configurados.
        """
        igv = self._obtener_igv_vigente()
        uit = self._obtener_uit_vigente()

        public_id = self._generar_public_id_liquidacion_general()

        liquidacion = LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad=municipalidad,
            igv=igv,
            uit=uit,
            expediente=expediente,
            observacion=observacion,
            public_id=public_id,
            numero_revision=numero_revision,
            tipo_liquidacion=tipo_liquidacion,
        )

        return liquidacion

    def _obtener_igv_vigente(self):
        """Obtiene el IGV vigente. Lanza ValueError si no existe."""
        from modules.finanzas.models import IGV

        igv = IGV.objects.vigente()
        if igv is None:
            raise ValueError(
                "No hay IGV vigente configurado. Ejecute: python manage.py seed_finanzas"
            )
        return igv

    def _obtener_uit_vigente(self):
        """Obtiene la UIT vigente. Lanza ValueError si no existe."""
        from modules.finanzas.models import UIT

        uit = UIT.objects.vigente()
        if uit is None:
            raise ValueError(
                "No hay UIT vigente configurada. Ejecute: python manage.py seed_finanzas"
            )
        return uit

    def _obtener_variables_financieras_vigentes(self) -> tuple[Decimal, Decimal]:
        """
        Obtiene IGV y UIT vigentes.

        Returns:
            Tuple of (igv_valor, uit_valor)

        Raises:
            ValueError: Si IGV o UIT no están configurados.
        """
        igv = self._obtener_igv_vigente()
        uit = self._obtener_uit_vigente()

        return Decimal(str(igv.valor)), Decimal(str(uit.valor))

    def _generar_public_id_liquidacion_general(self) -> str:
        """
        Genera un public_id único para una LiquidacionGeneral.

        Formato: LIQ-{year}-{count:05d}

        Returns:
            public_id generado.
        """
        year = timezone.now().year
        count = LiquidacionGeneral.objects.filter(
            public_id__startswith=f"TAL-{year}-"
        ).count()
        return f"TAL-{year}-{count + 1:05d}"

    def obtener_tarifas_vigentes(self, tramite_accion: str) -> list[dict]:
        """
        Obtiene las tarifas vigentes de Taludes para el formulario.

        Args:
            tramite_accion: Acción de trámite (PRIMERA_REVISION o REVISION).

        Returns:
            Lista de diccionarios con tarifas M2 vigentes.
            Cada dict contiene: tarifa_id, detalle_id, costo_por_m2, area_m2,
            derecho_minimo, derecho_maximo, habilitada.
        """
        reglas = ReglaTarifaLiquidacion.objects.filter(
            tramite_accion=tramite_accion,
            tarifa_base__tipo_liquidacion=TipoLiquidacion.TALUDES,
        ).select_related("tarifa_base", "tarifa_base__detalle_m2")

        result = []
        for regla in reglas:
            tarifa_base = regla.tarifa_base
            if not esta_vigente(tarifa_base.periodo_inicio, tarifa_base.periodo_fin):
                continue
            try:
                detalle_m2 = tarifa_base.detalle_m2
            except TarifaPorMetroCuadrado.DoesNotExist:
                continue
            if detalle_m2 is None:
                continue
            result.append({
                "tarifa_id": str(tarifa_base.id),
                "detalle_id": str(detalle_m2.id),
                "costo_por_m2": float(detalle_m2.costo_por_m2),
                "area_m2": float(detalle_m2.area_m2),
                "derecho_minimo": float(detalle_m2.derecho_minimo),
                "derecho_maximo": float(detalle_m2.derecho_maximo) if detalle_m2.derecho_maximo is not None else None,
                "habilitada": esta_vigente(tarifa_base.periodo_inicio, tarifa_base.periodo_fin),
            })

        return result
