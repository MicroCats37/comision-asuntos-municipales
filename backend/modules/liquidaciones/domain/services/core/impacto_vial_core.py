"""Impacto Vial Core — lógica de negocio para Impacto Vial."""
from datetime import date
from decimal import Decimal
from typing import Optional
from django.utils import timezone

from modules.liquidaciones.models import (
    LiquidacionGeneral,
    LiquidacionImpactoVial,
    LiquidacionPorMetroCuadrado,
    LiquidacionPorcentajeObra,
    TarifaPorMetroCuadrado,
    TarifaPorcentajeObra,
    TarifaLiquidacionBase,
    ReglaTarifaEdificacion,
)
from modules.liquidaciones.domain.constants import (
    TipoLiquidacion,
    TipoTramiteEdificaciones,
    TramiteAccion,
)
from modules.liquidaciones.domain.services.core.calculos_helpers import (
    _calcular_monto_m2,
    _aplicar_derecho_minimo,
    _aplicar_derecho_maximo,
)
from core.utils import esta_vigente
from modules.finanzas.models import IGV, UIT

# Import domain schemas for RevisionVigenteResult
from modules.liquidaciones.domain.schemas import (
    RevisionVigenteResult,
    EspecialidadBasicaResult,
)


class ImpactoVialCoreService:
    """
    Servicio core sync para liquidaciones de Impacto Vial.

    Crea LiquidacionGeneral + LiquidacionImpactoVial + LiquidacionPorMetroCuadrado.
    """

    def _crear_liquidacion_impacto_vial(
        self,
        liquidacion_general: LiquidacionGeneral,
        tramite_accion: str = TramiteAccion.PRIMERA_REVISION,
    ) -> LiquidacionImpactoVial:
        """
        Crea el registro específico LiquidacionImpactoVial.

        Args:
            liquidacion_general: LiquidacionGeneral asociada.
            tramite_accion: Acción de trámite.

        Returns:
            LiquidacionImpactoVial creada.
        """
        return LiquidacionImpactoVial.objects.create(
            liquidacion=liquidacion_general,
            tramite_accion=tramite_accion,
        )

    def _buscar_tarifa_m2(self, tramite_accion: str) -> TarifaPorMetroCuadrado:
        """
        Busca y valida una tarifa M2 vigente para Impacto Vial.

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
            tarifa_base__tipo_liquidacion=TipoLiquidacion.IMPACTO_VIAL,
        ).select_related("tarifa_base", "tarifa_base__detalle_m2").first()

        if regla is None:
            raise ValueError(
                f"No existe ReglaTarifaLiquidacion para "
                f"tipo_liquidacion={TipoLiquidacion.IMPACTO_VIAL} y tramite_accion={tramite_accion}. "
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
            tipo_liquidacion: Valor de TipoLiquidacion esperado (ej. IMPACTO_VIAL).
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

    def _buscar_tarifa_porcentaje(self, tramite_accion: str) -> TarifaPorcentajeObra:
        """
        Busca y valida una tarifa porcentual vigente para Impacto Vial.

        Args:
            tramite_accion: PRIMERA_REVISION o REVISION.

        Returns:
            TarifaPorcentajeObra vigente.

        Raises:
            ValueError: Si no existe o no está vigente.
        """
        regla = ReglaTarifaEdificacion.objects.filter(
            tipo_tramite=TipoTramiteEdificaciones.OBRA_NUEVA,
            tramite_accion=tramite_accion,
            tarifa_base__tipo_liquidacion=TipoLiquidacion.IMPACTO_VIAL,
        ).select_related("tarifa_base", "tarifa_base__detalle_porcentual").first()

        if regla is None:
            raise ValueError(
                f"No existe ReglaTarifaEdificacion para "
                f"tipo_tramite={TipoTramiteEdificaciones.OBRA_NUEVA} y "
                f"tipo_liquidacion={TipoLiquidacion.IMPACTO_VIAL} y tramite_accion={tramite_accion}. "
                f"Verifique que la tarifa esté configurada en el admin."
            )

        tarifa_base = regla.tarifa_base

        if not esta_vigente(tarifa_base.periodo_inicio, tarifa_base.periodo_fin):
            raise ValueError(
                f"La tarifa base {tarifa_base.id} no está vigente "
                f"(periodo: {tarifa_base.periodo_inicio} - {tarifa_base.periodo_fin}). "
                f"Verifique que la fecha actual esté dentro del período."
            )

        try:
            detalle_porcentual = tarifa_base.detalle_porcentual
        except TarifaPorcentajeObra.DoesNotExist:
            raise ValueError(
                f"La tarifa base {tarifa_base.id} no tiene detalle TarifaPorcentajeObra. "
                f"Verifique que la tarifa porcentual esté configurada."
            )

        if detalle_porcentual is None:
            raise ValueError(
                f"La tarifa base {tarifa_base.id} no tiene detalle TarifaPorcentajeObra asociado."
            )

        return detalle_porcentual

    def _validar_tarifa_porcentaje_por_id(
        self,
        tarifa_id: str,
        tipo_liquidacion: str,
        tramite_accion: str,
    ) -> TarifaPorcentajeObra:
        """
        Valida y retorna una tarifa porcentual por su ID.

        Args:
            tarifa_id: ID de la TarifaLiquidacionBase seleccionada.
            tipo_liquidacion: Valor de TipoLiquidacion esperado (ej. IMPACTO_VIAL).
            tramite_accion: Valor de TramiteAccion esperado (ej. PRIMERA_REVISION).

        Returns:
            TarifaPorcentajeObra validada.

        Raises:
            ValueError: Si la tarifa no existe, no está vigente, o no es porcentual.
        """
        try:
            tarifa_base = TarifaLiquidacionBase.objects.select_related(
                "detalle_porcentual"
            ).get(id=tarifa_id)
        except TarifaLiquidacionBase.DoesNotExist:
            raise ValueError(f"La tarifa con id={tarifa_id} no existe.")

        if not esta_vigente(tarifa_base.periodo_inicio, tarifa_base.periodo_fin):
            raise ValueError(
                f"La tarifa {tarifa_id} no está vigente "
                f"(periodo: {tarifa_base.periodo_inicio} - {tarifa_base.periodo_fin})."
            )

        try:
            detalle_porcentual = tarifa_base.detalle_porcentual
        except TarifaPorcentajeObra.DoesNotExist:
            raise ValueError(
                f"La tarifa {tarifa_id} no es una tarifa porcentual "
                f"(no tiene detalle TarifaPorcentajeObra)."
            )

        if detalle_porcentual is None:
            raise ValueError(
                f"La tarifa {tarifa_id} no tiene detalle TarifaPorcentajeObra asociado."
            )

        regla = ReglaTarifaEdificacion.objects.filter(
            tipo_tramite=TipoTramiteEdificaciones.OBRA_NUEVA,
            tarifa_base=tarifa_base,
            tramite_accion=tramite_accion,
        ).select_related("tarifa_base").first()

        if regla is None:
            raise ValueError(
                f"La tarifa {tarifa_id} no tiene ReglaTarifaEdificacion para "
                f"tipo_tramite={TipoTramiteEdificaciones.OBRA_NUEVA} y "
                f"tramite_accion={tramite_accion}."
            )

        if tarifa_base.tipo_liquidacion != tipo_liquidacion:
            raise ValueError(
                f"La tarifa {tarifa_id} corresponde a tipo_liquidacion="
                f"{tarifa_base.tipo_liquidacion}, pero se esperaba "
                f"tipo_liquidacion={tipo_liquidacion}."
            )

        return detalle_porcentual

    def _crear_calculo_porcentaje(
        self,
        liquidacion_general: LiquidacionGeneral,
        valor_proyecto: Decimal,
        valor_base_calculo: Decimal,
        tarifa_porcentaje: TarifaPorcentajeObra,
    ) -> LiquidacionPorcentajeObra:
        """
        Crea registro de cálculo LiquidacionPorcentajeObra.

        Args:
            liquidacion_general: LiquidacionGeneral asociada.
            valor_proyecto: Valor total del proyecto.
            valor_base_calculo: Valor base de cálculo (aplicar %).
            tarifa_porcentaje: TarifaPorcentajeObra a aplicar.

        Returns:
            LiquidacionPorcentajeObra creada.
        """
        liquidacion_porc = LiquidacionPorcentajeObra.objects.create(
            liquidacion_general=liquidacion_general,
            valor_proyecto=valor_proyecto,
            valor_base_calculo=valor_base_calculo,
            tarifa_aplicada=tarifa_porcentaje,
        )

        return liquidacion_porc

    def _obtener_igv_vigente(self):
        """Obtiene el IGV vigente. Lanza ValueError si no existe."""
        igv = IGV.objects.vigente()
        if igv is None:
            raise ValueError(
                "No hay IGV vigente configurado. Ejecute: python manage.py seed_finanzas"
            )
        return igv

    def _obtener_uit_vigente(self):
        """Obtiene la UIT vigente. Lanza ValueError si no existe."""
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
            public_id__startswith=f"IV-{year}-"
        ).count()
        return f"IV-{year}-{count + 1:05d}"

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
        Crea LiquidacionGeneral para Impacto Vial.

        Args:
            proyecto: Proyecto asociado.
            municipalidad: Municipaliddad asociada.
            tipo_liquidacion: Valor de TipoLiquidacion (IMPACTO_VIAL).
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

    def obtener_tarifas_vigentes(
        self,
        tipo_tramite: str | None = None,
        tramite_accion: str = TramiteAccion.PRIMERA_REVISION,
    ) -> list[dict]:
        """
        Obtiene las tarifas vigentes de Impacto Vial para el formulario.

        Si tipo_tramite es provisto, filtra usando ReglaTarifaEdificacion.
        Si tipo_tramite es None, retorna todas las tarifas IMPACTO_VIAL vigentes.

        Args:
            tipo_tramite: Tipo de trámite de edificación (opcional).
            tramite_accion: Acción de trámite (PRIMERA_REVISION o REVISION).

        Returns:
            Lista de diccionarios con tarifas porcentuales vigentes.
            Cada dict contiene: tarifa_id, detalle_id, porcentaje_liquidacion,
            porcentaje_minimo_uit, derecho_minimo, derecho_maximo, habilitada.
        """
        reglas_qs = ReglaTarifaEdificacion.objects.filter(
            tramite_accion=tramite_accion,
            tarifa_base__tipo_liquidacion=TipoLiquidacion.IMPACTO_VIAL,
        )
        if tipo_tramite is not None:
            reglas_qs = reglas_qs.filter(tipo_tramite=tipo_tramite)

        reglas = reglas_qs.select_related("tarifa_base", "tarifa_base__detalle_porcentual")

        result = []
        for regla in reglas:
            tarifa_base = regla.tarifa_base
            if not esta_vigente(tarifa_base.periodo_inicio, tarifa_base.periodo_fin):
                continue
            try:
                detalle_porcentual = tarifa_base.detalle_porcentual
            except TarifaPorcentajeObra.DoesNotExist:
                continue
            if detalle_porcentual is None:
                continue
            result.append({
                "tarifa_id": str(tarifa_base.id),
                "detalle_id": str(detalle_porcentual.id),
                "porcentaje_liquidacion": float(detalle_porcentual.porcentaje_liquidacion),
                "porcentaje_minimo_uit": float(detalle_porcentual.porcentaje_minimo_uit),
                "derecho_minimo": float(detalle_porcentual.derecho_minimo),
                "derecho_maximo": float(detalle_porcentual.derecho_maximo) if detalle_porcentual.derecho_maximo is not None else None,
                "habilitada": esta_vigente(tarifa_base.periodo_inicio, tarifa_base.periodo_fin),
            })

        return result

    def obtener_revisiones_vigentes(
        self,
        tipo_tramite: str | None = None,
        tramite_accion: str = TramiteAccion.PRIMERA_REVISION,
    ) -> list[RevisionVigenteResult]:
        """
        Obtiene las revisiones vigentes de Impacto Vial para el formulario.

        A diferencia de obtener_tarifas_vigentes, este método devuelve
        objetos RevisionVigenteResult con especialidades M2M incluidas,
        similar al patrón de Edificaciones.

        Si tipo_tramite es provisto, filtra usando ReglaTarifaEdificacion.
        Si tipo_tramite es None, retorna todas las tarifas IMPACTO_VIAL vigentes
        (sin filtro de tipo_tramite), replicando el patrón de Edificaciones.

        Args:
            tipo_tramite: Tipo de trámite de edificación (opcional).
            tramite_accion: Acción de trámite (PRIMERA_REVISION o REVISION).

        Returns:
            Lista de RevisionVigenteResult con especialidades populadas.
        """
        reglas_qs = ReglaTarifaEdificacion.objects.filter(
            tramite_accion=tramite_accion,
            tarifa_base__tipo_liquidacion=TipoLiquidacion.IMPACTO_VIAL,
        )
        if tipo_tramite is not None:
            reglas_qs = reglas_qs.filter(tipo_tramite=tipo_tramite)

        reglas = reglas_qs.select_related(
            "tarifa_base",
            "tarifa_base__detalle_porcentual",
        ).prefetch_related(
            "tarifa_base__especialidades",
        )

        result = []
        for regla in reglas:
            tarifa_base = regla.tarifa_base

            # Skip if not vigente
            if not esta_vigente(tarifa_base.periodo_inicio, tarifa_base.periodo_fin):
                continue

            # Get detalle porcentual
            try:
                detalle_porcentual = tarifa_base.detalle_porcentual
            except TarifaPorcentajeObra.DoesNotExist:
                continue
            if detalle_porcentual is None:
                continue

            # Build especialidades list from M2M
            especialidades = [
                EspecialidadBasicaResult(
                    id=esp.id,
                    nombre=esp.nombre,
                )
                for esp in tarifa_base.especialidades.all()
            ]

            result.append(RevisionVigenteResult(
                id=str(tarifa_base.id),
                especialidades=especialidades,
                tarifa_id=str(tarifa_base.id),
                porcentaje_liquidacion=detalle_porcentual.porcentaje_liquidacion,
                derecho_minimo=detalle_porcentual.derecho_minimo,
                derecho_maximo=detalle_porcentual.derecho_maximo,
                porcentaje_minimo_uit=detalle_porcentual.porcentaje_minimo_uit,
                habilitada=esta_vigente(tarifa_base.periodo_inicio, tarifa_base.periodo_fin),
            ))

        return result
