"""
LiquidacionHistoricoCoreService — resolver canónico de valores históricos.

ÚNICO dueño de la resolución histórica de IGV, UIT, tarifas base, tarifas
hijas (porcentaje de obra, metro cuadrado, categoría de visitas) y derechos
por fecha de vigencia.

Reglas clave:
- ORM PURO — sin mutaciones, sin transaction.atomic(), sin lógica de negocio.
- Los managers vigente() de IGV/UIT ignoran la fecha — filtrado manual.
- VigenciaModel.vigentes(fecha=fecha) resuelve el resto correctamente.
- Períodos superpuestos: gana el MÁS NUEVO en la fecha
  (order_by("-periodo_inicio").first()).
- SIN fallback silencioso a valores actuales: se lanza un error de dominio.

Consumidores:
- PATCH recalculation (porcentaje de obra, M2, visitas).
- Cotización de edición (PO, M2, visitas).
- Adaptadores legacy (porcentaje de obra, M2, visitas), que conservan su
  contrato nullable para los importadores.
"""
from datetime import date
from typing import Optional

from django.db import models

from core.exceptions import BusinessError
from modules.finanzas.domain.models.impuestos import IGV, UIT
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    DerechoPorMetroCuadrado,
    DerechoPorcentajeObra,
    TarifaLiquidacionBase,
    TarifaPorCategoriaVisitas,
    TarifaPorMetroCuadrado,
    TarifaPorcentajeObra,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.tarifas_historicas_core_service import (
    TarifasHistoricasCoreService,
)


class NoIGVVigenteError(BusinessError):
    """Raised when no IGV record is vigente at the given fecha."""

    def __init__(self, fecha: date):
        super().__init__(
            f"No existe IGV vigente para la fecha {fecha}. "
            "No se puede calcular sin valores históricos."
        )


class NoUITVigenteError(BusinessError):
    """Raised when no UIT record is vigente at the given fecha."""

    def __init__(self, fecha: date):
        super().__init__(
            f"No existe UIT vigente para la fecha {fecha}. "
            "No se puede calcular sin valores históricos."
        )


class NoTarifaVigenteError(BusinessError):
    """Raised when no TarifaLiquidacionBase is vigente at the given fecha."""

    def __init__(self, tipo_liquidacion: str, fecha: date):
        super().__init__(
            f"No existe tarifa base vigente para {tipo_liquidacion} en la fecha {fecha}. "
            "No se puede calcular sin valores históricos."
        )


class NoDerechoVigenteError(BusinessError):
    """Raised when no DerechoPorcentajeObra/DerechoPorMetroCuadrado is vigente."""

    def __init__(self, tipo: str, fecha: date):
        super().__init__(
            f"No existe derecho ({tipo}) vigente para la fecha {fecha}. "
            "No se puede calcular sin valores históricos."
        )


class LiquidacionHistoricoCoreService:
    """
    Canonical read-only resolver of financial values effective at a given fecha.

    All methods are PURE READ-ONLY ORM — no business logic, no mutations.
    Missing historical coverage raises a domain error instead of silently
    falling back to the values currently in force.

    Usage:
        service = LiquidacionHistoricoCoreService()
        fecha = liquidacion.liquidacion_general.fecha_registro.date()
        igv = service.get_igv_por_fecha(fecha)                    # raises if not found
        uit = service.get_uit_por_fecha(fecha)                    # raises if not found
        base = service.get_tarifa_base_vigente(tipo_liq, fecha)    # raises if not found
    """

    def __init__(
        self,
        tarifas_service: TarifasHistoricasCoreService | None = None,
    ) -> None:
        self._tarifas_service = tarifas_service or TarifasHistoricasCoreService()

    # ── IGV ─────────────────────────────────────────────────────────────────

    def get_igv_por_fecha(self, fecha: date) -> IGV:
        """
        Get the IGV vigente at the given fecha.

        IGV.objects.vigente() ignores fecha — manual filter required.
        Uses periodo_inicio <= fecha AND (periodo_fin is null OR periodo_fin >= fecha),
        ordered by periodo_inicio DESC with pk as tiebreaker for deterministic
        results when periods overlap.

        Raises:
            NoIGVVigenteError: If no IGV covers the given fecha.

        Returns:
            IGV instance vigente at fecha.
        """
        result = (
            IGV.objects.filter(periodo_inicio__lte=fecha)
            .filter(
                models.Q(periodo_fin__isnull=True) | models.Q(periodo_fin__gte=fecha)
            )
            .order_by("-periodo_inicio", "pk")
            .first()
        )
        if result is None:
            raise NoIGVVigenteError(fecha)
        return result

    # ── UIT ─────────────────────────────────────────────────────────────────

    def get_uit_por_fecha(self, fecha: date) -> UIT:
        """
        Get the UIT vigente at the given fecha.

        UIT.objects.vigente() ignores fecha — manual filter required.
        Same pattern as get_igv_por_fecha.

        Raises:
            NoUITVigenteError: If no UIT covers the given fecha.

        Returns:
            UIT instance vigente at fecha.
        """
        result = (
            UIT.objects.filter(periodo_inicio__lte=fecha)
            .filter(
                models.Q(periodo_fin__isnull=True) | models.Q(periodo_fin__gte=fecha)
            )
            .order_by("-periodo_inicio", "pk")
            .first()
        )
        if result is None:
            raise NoUITVigenteError(fecha)
        return result

    # ── TarifaLiquidacionBase ────────────────────────────────────────────────

    def get_tarifa_base_vigente(
        self,
        tipo_liquidacion: str,
        fecha: date,
    ) -> TarifaLiquidacionBase:
        """
        Get the TarifaLiquidacionBase vigente at the given fecha for a tipo_liquidacion.

        Uses VigenciaModel.vigentes(fecha=fecha) which correctly filters by date.
        Returns the NEWEST overlapping record (order_by("-periodo_inicio").first()).

        Raises:
            NoTarifaVigenteError: If no base tariff is vigente at fecha.

        Returns:
            TarifaLiquidacionBase instance vigente at fecha.
        """
        result = (
            TarifaLiquidacionBase.objects.filter(
                tipo_liquidacion__codigo=tipo_liquidacion
            )
            .vigentes(fecha=fecha)
            .order_by("-periodo_inicio")
            .first()
        )
        if result is None:
            raise NoTarifaVigenteError(tipo_liquidacion, fecha)
        return result

    def get_tarifa_base_vigente_list(
        self,
        tipo_liquidacion: str,
        fecha: date,
    ) -> list[TarifaLiquidacionBase]:
        """
        Get ALL TarifaLiquidacionBase records vigente at fecha for a tipo_liquidacion.

        Returns a list (caller decides which to use or validates for overlap).
        Order is DESC by periodo_inicio (newest first).

        Returns:
            List of TarifaLiquidacionBase instances (may be empty).
        """
        return self._tarifas_service.get_tarifas_vigentes(tipo_liquidacion, fecha)

    # ── TarifaPorcentajeObra ────────────────────────────────────────────────

    def get_tarifa_porcentaje_obra(
        self,
        tarifa_base_ids: list[str],
    ) -> list[TarifaPorcentajeObra]:
        """
        Get TarifaPorcentajeObra records for the given TarifaLiquidacionBase IDs.

        Returns:
            List of TarifaPorcentajeObra instances (may be empty).
        """
        if not tarifa_base_ids:
            return []
        return self._tarifas_service.get_tarifas_porcentaje_obra_por_base(
            tarifa_base_ids
        )

    # ── TarifaPorMetroCuadrado ──────────────────────────────────────────────

    def get_tarifa_m2(
        self,
        tarifa_base_id: str,
    ) -> Optional[TarifaPorMetroCuadrado]:
        """
        Get TarifaPorMetroCuadrado for a single TarifaLiquidacionBase.

        Returns:
            TarifaPorMetroCuadrado instance or None if not found.
        """
        return self._tarifas_service.get_tarifa_m2_por_base(tarifa_base_id)

    # ── TarifaPorCategoriaVisitas ───────────────────────────────────────────

    def get_tarifa_categoria_visitas(
        self,
        tarifa_base_ids: list[str],
    ) -> list[TarifaPorCategoriaVisitas]:
        """
        Get TarifaPorCategoriaVisitas records for the given TarifaLiquidacionBase IDs.

        Returns:
            List of TarifaPorCategoriaVisitas instances (may be empty).
        """
        if not tarifa_base_ids:
            return []
        return self._tarifas_service.get_tarifas_categoria_visitas_por_base(
            tarifa_base_ids
        )

    # ── DerechoPorcentajeObra ───────────────────────────────────────────────

    def get_derechos_porcentaje_vigentes(
        self,
        fecha: date,
    ) -> list[DerechoPorcentajeObra]:
        """
        Get ALL DerechoPorcentajeObra records vigente at the given fecha.

        Order is DESC by periodo_inicio (newest first).

        Returns:
            List of DerechoPorcentajeObra instances (may be empty).
        """
        return self._tarifas_service.get_derechos_porcentaje_vigentes(fecha)

    def get_derecho_porcentaje_vigente(
        self,
        fecha: date,
    ) -> DerechoPorcentajeObra:
        """
        Get the DerechoPorcentajeObra vigente at the given fecha.

        NEWEST at fecha = order_by("-periodo_inicio").first()

        Raises:
            NoDerechoVigenteError: If no derecho is vigente at fecha.

        Returns:
            DerechoPorcentajeObra instance vigente at fecha.
        """
        derechos = self.get_derechos_porcentaje_vigentes(fecha)
        if not derechos:
            raise NoDerechoVigenteError("porcentaje obra", fecha)
        return derechos[0]

    # ── DerechoPorMetroCuadrado ─────────────────────────────────────────────

    def get_derechos_m2_vigentes(
        self,
        fecha: date,
    ) -> list[DerechoPorMetroCuadrado]:
        """
        Get ALL DerechoPorMetroCuadrado records vigente at the given fecha.

        Order is DESC by periodo_inicio (newest first).

        Returns:
            List of DerechoPorMetroCuadrado instances (may be empty).
        """
        return self._tarifas_service.get_derechos_m2_vigentes(fecha)

    def get_derecho_m2_vigente(self, fecha: date) -> DerechoPorMetroCuadrado:
        """
        Get the DerechoPorMetroCuadrado vigente at the given fecha.

        NEWEST at fecha = order_by("-periodo_inicio").first()

        Raises:
            NoDerechoVigenteError: If no derecho is vigente at fecha.

        Returns:
            DerechoPorMetroCuadrado instance vigente at fecha.
        """
        derechos = self.get_derechos_m2_vigentes(fecha)
        if not derechos:
            raise NoDerechoVigenteError("por metro cuadrado", fecha)
        return derechos[0]
