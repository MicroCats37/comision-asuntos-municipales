"""
LiquidacionesNuevas Core — servicios core sync para los 5 nuevos formularios.

Cada servicio maneja CRUD de LiquidacionGeneral + LiquidacionEspecifica + Cálculo
para su tipo de liquidación correspondiente.

Servicios:
- HabilitacionUrbanaCoreService
- MecanicaSuelosCoreService
- ImpactoVialCoreService
- TaludesCoreService
- InspeccionObraCoreService

NO usa transaction.atomic internamente — el flujo (Phase 4) lo provee si es necesario.
"""

from decimal import Decimal
from typing import Optional
from django.utils import timezone

from modules.liquidaciones.models import (
    LiquidacionGeneral,
    LiquidacionHabilitacionUrbana,
    LiquidacionMecanicaSuelos,
    LiquidacionImpactoVial,
    LiquidacionTaludes,
    LiquidacionInspeccionObra,
    LiquidacionPorMetroCuadrado,
    LiquidacionPorCategoriaVisitas,
    TarifaPorMetroCuadrado,
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.constants import (
    TipoLiquidacion,
    TramiteAccion,
)
from modules.liquidaciones.domain.services.core.tarifas_nuevas_core import (
    TarifasNuevasCoreService,
)
from modules.entidades.models import Municipalidad


class HabilitacionUrbanaCoreService:
    """
    Servicio core sync para liquidaciones de Habilitación Urbana.

    Crea LiquidacionGeneral + LiquidacionHabilitacionUrbana + LiquidacionPorMetroCuadrado.
    """

    def __init__(self):
        self._tarifas_core = TarifasNuevasCoreService()

    def _generar_public_id_habilitacion_urbana(self) -> str:
        """Genera public_id único para LiquidacionHabilitacionUrbana."""
        year = timezone.now().year
        count = LiquidacionHabilitacionUrbana.objects.filter(
            public_id__startswith=f"HU-{year}-"
        ).count()
        return f"HU-{year}-{count + 1:05d}"

    def _crear_liquidacion_habilitacion_urbana(
        self,
        liquidacion_general: LiquidacionGeneral,
        tramite_accion: str = TramiteAccion.PRIMERA_REVISION,
    ) -> LiquidacionHabilitacionUrbana:
        """
        Crea el registro específico LiquidacionHabilitacionUrbana.

        Args:
            liquidacion_general: LiquidacionGeneral asociada.
            tramite_accion: Acción de trámite (PRIMERA_REVISION o REVISION).

        Returns:
            LiquidacionHabilitacionUrbana creada.
        """
        public_id = self._generar_public_id_habilitacion_urbana()
        return LiquidacionHabilitacionUrbana.objects.create(
            liquidacion=liquidacion_general,
            public_id=public_id,
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
        return self._tarifas_core._buscar_tarifa_m2_por_tipo_liquidacion(
            tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
            tramite_accion=tramite_accion,
        )

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
            tipo_liquidacion: Valor de TipoLiquidacion esperado (ej. HABILITACION_URBANA).
            tramite_accion: Valor de TramiteAccion esperado (ej. PRIMERA_REVISION).

        Returns:
            TarifaPorMetroCuadrado validada.

        Raises:
            ValueError: Si la tarifa no existe, no está vigente, no tiene detalle_m2,
                        o su regla no corresponde al tipo_liquidacion + tramite_accion dados.
        """
        return self._tarifas_core._validar_tarifa_m2_por_id(
            tarifa_id=tarifa_id,
            tipo_liquidacion=tipo_liquidacion,
            tramite_accion=tramite_accion,
        )

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
        return self._tarifas_core._crear_liquidacion_m2(
            liquidacion_general=liquidacion_general,
            area_solicitada=area_solicitada,
            tarifa_m2=tarifa_m2,
        )

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
        Crea LiquidacionGeneral para Habilitación Urbana delegando a TarifasNuevasCoreService.
        """
        return self._tarifas_core._crear_liquidacion_general_nueva(
            proyecto=proyecto,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liquidacion,
            expediente=expediente,
            observacion=observacion,
            numero_revision=numero_revision,
        )

    def _obtener_variables_financieras_vigentes(self) -> tuple[Decimal, Decimal]:
        """
        Obtiene IGV y UIT vigentes delegando a TarifasNuevasCoreService.
        """
        return self._tarifas_core._obtener_variables_financieras_vigentes()


class MecanicaSuelosCoreService:
    """
    Servicio core sync para liquidaciones de Mecánica de Suelos.

    Crea LiquidacionGeneral + LiquidacionMecanicaSuelos + LiquidacionPorMetroCuadrado.
    """

    def __init__(self):
        self._tarifas_core = TarifasNuevasCoreService()

    def _generar_public_id_mecanica_suelos(self) -> str:
        """Genera public_id único para LiquidacionMecanicaSuelos."""
        year = timezone.now().year
        count = LiquidacionMecanicaSuelos.objects.filter(
            public_id__startswith=f"MS-{year}-"
        ).count()
        return f"MS-{year}-{count + 1:05d}"

    def _crear_liquidacion_mecanica_suelos(
        self,
        liquidacion_general: LiquidacionGeneral,
        tramite_accion: str = TramiteAccion.PRIMERA_REVISION,
    ) -> LiquidacionMecanicaSuelos:
        """
        Crea el registro específico LiquidacionMecanicaSuelos.

        Args:
            liquidacion_general: LiquidacionGeneral asociada.
            tramite_accion: Acción de trámite.

        Returns:
            LiquidacionMecanicaSuelos creada.
        """
        public_id = self._generar_public_id_mecanica_suelos()
        return LiquidacionMecanicaSuelos.objects.create(
            liquidacion=liquidacion_general,
            public_id=public_id,
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
        return self._tarifas_core._buscar_tarifa_m2_por_tipo_liquidacion(
            tipo_liquidacion=TipoLiquidacion.MECANICA_SUELOS,
            tramite_accion=tramite_accion,
        )

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
            tipo_liquidacion: Valor de TipoLiquidacion esperado (ej. MECANICA_SUELOS).
            tramite_accion: Valor de TramiteAccion esperado (ej. PRIMERA_REVISION).

        Returns:
            TarifaPorMetroCuadrado validada.

        Raises:
            ValueError: Si la tarifa no existe, no está vigente, no tiene detalle_m2,
                        o su regla no corresponde al tipo_liquidacion + tramite_accion dados.
        """
        return self._tarifas_core._validar_tarifa_m2_por_id(
            tarifa_id=tarifa_id,
            tipo_liquidacion=tipo_liquidacion,
            tramite_accion=tramite_accion,
        )

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
        return self._tarifas_core._crear_liquidacion_m2(
            liquidacion_general=liquidacion_general,
            area_solicitada=area_solicitada,
            tarifa_m2=tarifa_m2,
        )

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
        Crea LiquidacionGeneral para Mecánica de Suelos delegando a TarifasNuevasCoreService.
        """
        return self._tarifas_core._crear_liquidacion_general_nueva(
            proyecto=proyecto,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liquidacion,
            expediente=expediente,
            observacion=observacion,
            numero_revision=numero_revision,
        )

    def _obtener_variables_financieras_vigentes(self) -> tuple[Decimal, Decimal]:
        """
        Obtiene IGV y UIT vigentes delegando a TarifasNuevasCoreService.
        """
        return self._tarifas_core._obtener_variables_financieras_vigentes()


class ImpactoVialCoreService:
    """
    Servicio core sync para liquidaciones de Impacto Vial.

    Crea LiquidacionGeneral + LiquidacionImpactoVial + LiquidacionPorMetroCuadrado.
    """

    def __init__(self):
        self._tarifas_core = TarifasNuevasCoreService()

    def _generar_public_id_impacto_vial(self) -> str:
        """Genera public_id único para LiquidacionImpactoVial."""
        year = timezone.now().year
        count = LiquidacionImpactoVial.objects.filter(
            public_id__startswith=f"IV-{year}-"
        ).count()
        return f"IV-{year}-{count + 1:05d}"

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
        public_id = self._generar_public_id_impacto_vial()
        return LiquidacionImpactoVial.objects.create(
            liquidacion=liquidacion_general,
            public_id=public_id,
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
        return self._tarifas_core._buscar_tarifa_m2_por_tipo_liquidacion(
            tipo_liquidacion=TipoLiquidacion.IMPACTO_VIAL,
            tramite_accion=tramite_accion,
        )

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
        return self._tarifas_core._validar_tarifa_m2_por_id(
            tarifa_id=tarifa_id,
            tipo_liquidacion=tipo_liquidacion,
            tramite_accion=tramite_accion,
        )

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
        return self._tarifas_core._crear_liquidacion_m2(
            liquidacion_general=liquidacion_general,
            area_solicitada=area_solicitada,
            tarifa_m2=tarifa_m2,
        )

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
        Crea LiquidacionGeneral para Impacto Vial delegando a TarifasNuevasCoreService.
        """
        return self._tarifas_core._crear_liquidacion_general_nueva(
            proyecto=proyecto,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liquidacion,
            expediente=expediente,
            observacion=observacion,
            numero_revision=numero_revision,
        )

    def _obtener_variables_financieras_vigentes(self) -> tuple[Decimal, Decimal]:
        """
        Obtiene IGV y UIT vigentes delegando a TarifasNuevasCoreService.
        """
        return self._tarifas_core._obtener_variables_financieras_vigentes()


class TaludesCoreService:
    """
    Servicio core sync para liquidaciones de Taludes.

    Crea LiquidacionGeneral + LiquidacionTaludes + LiquidacionPorMetroCuadrado.
    """

    def __init__(self):
        self._tarifas_core = TarifasNuevasCoreService()

    def _generar_public_id_taludes(self) -> str:
        """Genera public_id único para LiquidacionTaludes."""
        year = timezone.now().year
        count = LiquidacionTaludes.objects.filter(
            public_id__startswith=f"TAL-{year}-"
        ).count()
        return f"TAL-{year}-{count + 1:05d}"

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
        public_id = self._generar_public_id_taludes()
        return LiquidacionTaludes.objects.create(
            liquidacion=liquidacion_general,
            public_id=public_id,
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
        return self._tarifas_core._buscar_tarifa_m2_por_tipo_liquidacion(
            tipo_liquidacion=TipoLiquidacion.TALUDES,
            tramite_accion=tramite_accion,
        )

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
        return self._tarifas_core._validar_tarifa_m2_por_id(
            tarifa_id=tarifa_id,
            tipo_liquidacion=tipo_liquidacion,
            tramite_accion=tramite_accion,
        )

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
        return self._tarifas_core._crear_liquidacion_m2(
            liquidacion_general=liquidacion_general,
            area_solicitada=area_solicitada,
            tarifa_m2=tarifa_m2,
        )

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
        Crea LiquidacionGeneral para Taludes delegando a TarifasNuevasCoreService.
        """
        return self._tarifas_core._crear_liquidacion_general_nueva(
            proyecto=proyecto,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liquidacion,
            expediente=expediente,
            observacion=observacion,
            numero_revision=numero_revision,
        )

    def _obtener_variables_financieras_vigentes(self) -> tuple[Decimal, Decimal]:
        """
        Obtiene IGV y UIT vigentes delegando a TarifasNuevasCoreService.
        """
        return self._tarifas_core._obtener_variables_financieras_vigentes()


class InspeccionObraCoreService:
    """
    Servicio core sync para liquidaciones de Inspección de Obra.

    Crea LiquidacionGeneral + LiquidacionInspeccionObra + LiquidacionPorCategoriaVisitas.
    """

    def __init__(self):
        self._tarifas_core = TarifasNuevasCoreService()

    def _generar_public_id_inspeccion_obra(self) -> str:
        """Genera public_id único para LiquidacionInspeccionObra."""
        year = timezone.now().year
        count = LiquidacionInspeccionObra.objects.filter(
            public_id__startswith=f"IO-{year}-"
        ).count()
        return f"IO-{year}-{count + 1:05d}"

    def _crear_liquidacion_inspeccion_obra(
        self,
        liquidacion_general: LiquidacionGeneral,
        tramite_accion: str = TramiteAccion.PRIMERA_REVISION,
    ) -> LiquidacionInspeccionObra:
        """
        Crea el registro específico LiquidacionInspeccionObra.

        Args:
            liquidacion_general: LiquidacionGeneral asociada.
            tramite_accion: Acción de trámite.

        Returns:
            LiquidacionInspeccionObra creada.
        """
        public_id = self._generar_public_id_inspeccion_obra()
        return LiquidacionInspeccionObra.objects.create(
            liquidacion=liquidacion_general,
            public_id=public_id,
            tramite_accion=tramite_accion,
        )

    def _buscar_tarifa_inspeccion(
        self,
        categoria: str,
        tramite_accion: str,
    ) -> TarifaPorCategoriaVisitas:
        """
        Busca tarifa inspección por ReglaTarifaInspeccionObra.

        Args:
            categoria: Categoría de inspección (A, B, C, etc.).
            tramite_accion: PRIMERA_REVISION o REVISION.

        Returns:
            TarifaPorCategoriaVisitas vigente.

        Raises:
            ValueError: Si no existe o no está vigente.
        """
        return self._tarifas_core._buscar_tarifa_inspeccion_por_categoria(
            categoria=categoria,
            tramite_accion=tramite_accion,
        )

    def _validar_tarifa_inspeccion_por_id(
        self,
        tarifa_id: str,
        categoria: str,
        tramite_accion: str,
    ) -> TarifaPorCategoriaVisitas:
        """
        Valida y retorna una tarifa de inspección por su ID, verificando que
        corresponda a la categoria + tramite_accion esperados.

        Args:
            tarifa_id: ID de la TarifaLiquidacionBase seleccionada.
            categoria: Categoría de inspección esperada (A, B, C, etc.).
            tramite_accion: Valor de TramiteAccion esperado (ej. PRIMERA_REVISION).

        Returns:
            TarifaPorCategoriaVisitas validada.

        Raises:
            ValueError: Si la tarifa no existe, no está vigente, no tiene detalle_visitas,
                        o su regla no corresponde a la categoria + tramite_accion dados.
        """
        return self._tarifas_core._validar_tarifa_inspeccion_por_id(
            tarifa_id=tarifa_id,
            categoria=categoria,
            tramite_accion=tramite_accion,
        )

    def _crear_calculo_visitas(
        self,
        liquidacion_general: LiquidacionGeneral,
        cantidad_visitas: int,
        categoria: str,
        tarifa_visitas: TarifaPorCategoriaVisitas,
    ) -> LiquidacionPorCategoriaVisitas:
        """
        Crea registro de cálculo LiquidacionPorCategoriaVisitas.

        Args:
            liquidacion_general: LiquidacionGeneral asociada.
            cantidad_visitas: Número de visitas.
            categoria: Categoría de inspección.
            tarifa_visitas: TarifaPorCategoriaVisitas a aplicar.

        Returns:
            LiquidacionPorCategoriaVisitas creada.
        """
        return self._tarifas_core._crear_liquidacion_visitas(
            liquidacion_general=liquidacion_general,
            cantidad_visitas=cantidad_visitas,
            categoria=categoria,
            tarifa_visitas=tarifa_visitas,
        )

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
        Crea LiquidacionGeneral para Inspección de Obra delegando a TarifasNuevasCoreService.
        """
        return self._tarifas_core._crear_liquidacion_general_nueva(
            proyecto=proyecto,
            municipalidad=municipalidad,
            tipo_liquidacion=tipo_liquidacion,
            expediente=expediente,
            observacion=observacion,
            numero_revision=numero_revision,
        )

    def _obtener_variables_financieras_vigentes(self) -> tuple[Decimal, Decimal]:
        """
        Obtiene IGV y UIT vigentes delegando a TarifasNuevasCoreService.
        """
        return self._tarifas_core._obtener_variables_financieras_vigentes()
