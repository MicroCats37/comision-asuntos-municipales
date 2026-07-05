"""
Tarifas y Cálculos Core — servicios core sync para los nuevos formularios.

Provee operaciones de:
- Búsqueda y validación de tarifa M2 por ReglaTarifaLiquidacion.
- Búsqueda y validación de tarifa inspección por ReglaTarifaInspeccionObra.
- Creación de registros de cálculo LiquidacionPorMetroCuadrado.
- Creación de registros de cálculo LiquidacionPorCategoriaVisitas.

NO usa transaction.atomic internamente — el flujo (Phase 4) lo provee si es necesario.
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from django.utils import timezone

from modules.liquidaciones.models import (
    LiquidacionGeneral,
    TarifaLiquidacionBase,
    TarifaPorMetroCuadrado,
    TarifaPorCategoriaVisitas,
    LiquidacionPorMetroCuadrado,
    LiquidacionPorCategoriaVisitas,
    ReglaTarifaLiquidacion,
    ReglaTarifaInspeccionObra,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion, TramiteAccion
from modules.liquidaciones.domain.services.core.calculos_helpers import (
    _calcular_monto_m2,
    _calcular_monto_visitas,
)
from core.utils import esta_vigente


class TarifasNuevasCoreService:
    """
    Servicio core sync para búsquedas de tarifas y cálculos de los nuevos formularios.

    Implementa búsqueda de tarifas por reglas y creación de registros de cálculo.
    """

    # Prefijo para public_ids de cada tipo
    PUBLIC_ID_PREFIXES = {
        TipoLiquidacion.HABILITACION_URBANA: "HU",
        TipoLiquidacion.MECANICA_SUELOS: "MS",
        TipoLiquidacion.IMPACTO_VIAL: "IV",
        TipoLiquidacion.TALUDES: "TAL",
        TipoLiquidacion.INSPECCION_OBRA: "IO",
    }

    # Modelos específicos por tipo de liquidación
    MODELOS_POR_TIPO = {
        TipoLiquidacion.HABILITACION_URBANA: "habilitacion_urbana",
        TipoLiquidacion.MECANICA_SUELOS: "mecanica_suelos",
        TipoLiquidacion.IMPACTO_VIAL: "impacto_vial",
        TipoLiquidacion.TALUDES: "taludes",
        TipoLiquidacion.INSPECCION_OBRA: "inspeccion_obra",
    }

    def _obtener_variables_financieras_vigentes(self) -> tuple[Decimal, Decimal]:
        """
        Obtiene IGV y UIT vigentes.

        Returns:
            Tuple of (igv_valor, uit_valor)

        Raises:
            ValueError: Si IGV o UIT no están configurados.
        """
        from modules.finanzas.models import IGV, UIT

        igv = IGV.objects.vigente()
        uit = UIT.objects.vigente()

        if igv is None:
            raise ValueError(
                "No hay IGV vigente configurado. Ejecute: python manage.py seed_finanzas"
            )
        if uit is None:
            raise ValueError(
                "No hay UIT vigente configurada. Ejecute: python manage.py seed_finanzas"
            )

        return Decimal(str(igv.valor)), Decimal(str(uit.valor))

    def _generar_public_id_liquidacion_especifica(
        self,
        tipo_liquidacion: str,
        ModeloEspecifico: type,
    ) -> str:
        """
        Genera un public_id único para una liquidación específica.

        Formato: {TIPO}-{year}-{count:05d}
        Ejemplo: HU-2026-00001, IV-2026-00001, MS-2026-00001

        Args:
            tipo_liquidacion: Valor de TipoLiquidacion (ej. HABILITACION_URBANA).
            ModeloEspecifico: Clase del modelo específico (ej. LiquidacionHabilitacionUrbana).

        Returns:
            public_id generado.
        """
        year = timezone.now().year
        prefijo = self.PUBLIC_ID_PREFIXES.get(tipo_liquidacion, "LIQ")
        count = ModeloEspecifico.objects.filter(
            public_id__startswith=f"{prefijo}-{year}-"
        ).count()
        return f"{prefijo}-{year}-{count + 1:05d}"

    # ==========================================================================
    # Búsqueda y validación de tarifas M2 por ReglaTarifaLiquidacion
    # ==========================================================================

    def _buscar_tarifa_m2_por_tipo_liquidacion(
        self,
        tipo_liquidacion: str,
        tramite_accion: str,
    ) -> TarifaPorMetroCuadrado:
        """
        Busca y valida una tarifa M2 vigente para el tipo de liquidación y acción.

        Busca la única tarifa M2 (TarifaPorMetroCuadrado) vigente que tenga:
        1. Una ReglaTarifaLiquidacion para la combinación tipo_liquidacion + tramite_accion
        2. Una TarifaLiquidacionBase vigente (periodo_fin IS NULL o >= hoy)

        Args:
            tipo_liquidacion: Valor de TipoLiquidacion (ej. HABILITACION_URBANA).
            tramite_accion: Valor de TramiteAccion (PRIMERA_REVISION o REVISION).

        Returns:
            TarifaPorMetroCuadrado encontrada y vigente.

        Raises:
            ValueError: Si no se encuentra regla, si la tarifa no es vigente,
                        o si no tiene detalle_m2.
        """
        today = date.today()

        # Buscar la regla para esta combinación
        regla = ReglaTarifaLiquidacion.objects.filter(
            tramite_accion=tramite_accion,
            tarifa_base__tipo_liquidacion=tipo_liquidacion,
        ).select_related("tarifa_base", "tarifa_base__detalle_m2").first()

        if regla is None:
            raise ValueError(
                f"No existe ReglaTarifaLiquidacion para "
                f"tipo_liquidacion={tipo_liquidacion} y tramite_accion={tramite_accion}. "
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

    def _validar_tarifa_m2_existe(
        self,
        tipo_liquidacion: str,
        tramite_accion: str,
    ) -> bool:
        """
        Valida que exista una tarifa M2 vigente para la combinación dada.

        Args:
            tipo_liquidacion: Valor de TipoLiquidacion.
            tramite_accion: Valor de TramiteAccion.

        Returns:
            True si existe y es válida, False en caso contrario.
        """
        try:
            self._buscar_tarifa_m2_por_tipo_liquidacion(tipo_liquidacion, tramite_accion)
            return True
        except ValueError:
            return False

    def _obtener_tarifas_m2_vigentes(
        self,
        tipo_liquidacion: str,
        tramite_accion: str,
    ) -> list[dict]:
        """
        Obtiene todas las tarifas M2 vigentes para el tipo de liquidación y acción

        Busca todas las tarifas M2 (TarifaPorMetroCuadrado) vigentes que tengan
        una ReglaTarifaLiquidacion para la combinación tipo_liquidacion + tramite_accion.

        Args:
            tipo_liquidacion: Valor de TipoLiquidacion (ej. HABILITACION_URBANA).
            tramite_accion: Valor de TramiteAccion (PRIMERA_REVISION o REVISION).

        Returns:
            Lista de diccionarios con:
            - tarifa_id: UUID de TarifaLiquidacionBase
            - detalle_id: UUID de TarifaPorMetroCuadrado
            - costo_por_m2: float
            - area_minima: float
            - derecho_minimo: float
            - derecho_maximo: Optional[float]
            - habilitada: bool
        """
        today = date.today()

        reglas = ReglaTarifaLiquidacion.objects.filter(
            tramite_accion=tramite_accion,
            tarifa_base__tipo_liquidacion=tipo_liquidacion,
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
                "area_minima": float(detalle_m2.area_minima),
                "derecho_minimo": float(detalle_m2.derecho_minimo),
                "derecho_maximo": float(detalle_m2.derecho_maximo) if detalle_m2.derecho_maximo is not None else None,
                "habilitada": esta_vigente(tarifa_base.periodo_inicio, tarifa_base.periodo_fin),
            })

        return result

    def _obtener_tarifas_visitas_vigentes(
        self,
        tramite_accion: str,
        categoria: str | None = None,
    ) -> list[dict]:
        """
        Obtiene todas las tarifas de inspección de obra vigentes.

        Busca todas las tarifas de visitas (TarifaPorCategoriaVisitas) vigentes
        que tengan una ReglaTarifaInspeccionObra para tramite_accion.

        Args:
            tramite_accion: Valor de TramiteAccion (PRIMERA_REVISION o REVISION).
            categoria: Filter by categoria (e.g. CATEGORIA_A, CATEGORIA_B).
                Optional - if not provided, returns all categories.

        Returns:
            Lista de diccionarios con:
            - tarifa_id: UUID de TarifaLiquidacionBase
            - detalle_id: UUID de TarifaPorCategoriaVisitas
            - costo_por_visita: float
            - visitas_minimas: int
            - categoria: str
            - habilitada: bool
        """
        today = date.today()

        filtros = {"tramite_accion": tramite_accion}
        if categoria is not None:
            filtros["categoria"] = categoria

        reglas = ReglaTarifaInspeccionObra.objects.filter(
            **filtros,
        ).select_related("tarifa_base", "tarifa_base__detalle_visitas")

        result = []
        for regla in reglas:
            tarifa_base = regla.tarifa_base
            if not esta_vigente(tarifa_base.periodo_inicio, tarifa_base.periodo_fin):
                continue
            try:
                detalle_visitas = tarifa_base.detalle_visitas
            except TarifaPorCategoriaVisitas.DoesNotExist:
                continue
            if detalle_visitas is None:
                continue
            result.append({
                "tarifa_id": str(tarifa_base.id),
                "detalle_id": str(detalle_visitas.id),
                "costo_por_visita": float(detalle_visitas.costo_por_visita),
                "visitas_minimas": int(detalle_visitas.visitas_minimas),
                "categoria": regla.categoria,
                "habilitada": esta_vigente(tarifa_base.periodo_inicio, tarifa_base.periodo_fin),
            })

        return result

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
        today = date.today()

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
        today = date.today()

        # Buscar la tarifa base por ID
        try:
            tarifa_base = TarifaLiquidacionBase.objects.select_related(
                "detalle_visitas"
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

        # Validar que tenga detalle visitas
        try:
            detalle_visitas = tarifa_base.detalle_visitas
        except TarifaPorCategoriaVisitas.DoesNotExist:
            raise ValueError(
                f"La tarifa {tarifa_id} no es una tarifa por categoría de visitas "
                f"(no tiene detalle TarifaPorCategoriaVisitas)."
            )

        if detalle_visitas is None:
            raise ValueError(
                f"La tarifa {tarifa_id} no tiene detalle TarifaPorCategoriaVisitas asociado."
            )

        # Validar que la regla corresponda a categoria + tramite_accion
        regla = ReglaTarifaInspeccionObra.objects.filter(
            tarifa_base=tarifa_base,
            categoria=categoria,
            tramite_accion=tramite_accion,
        ).select_related("tarifa_base").first()

        if regla is None:
            raise ValueError(
                f"La tarifa {tarifa_id} no tiene ReglaTarifaInspeccionObra para "
                f"categoria={categoria} y tramite_accion={tramite_accion}."
            )

        return detalle_visitas

    # ==========================================================================
    # Búsqueda y validación de tarifa inspección por ReglaTarifaInspeccionObra
    # ==========================================================================

    def _buscar_tarifa_inspeccion_por_categoria(
        self,
        categoria: str,
        tramite_accion: str,
    ) -> TarifaPorCategoriaVisitas:
        """
        Busca y valida una tarifa de inspección vigente para categoría y acción.

        Busca la única tarifa de visitas (TarifaPorCategoriaVisitas) vigente que tenga:
        1. Una ReglaTarifaInspeccionObra para categoria + tramite_accion
        2. Una TarifaLiquidacionBase vigente

        Args:
            categoria: Categoría de inspección (A, B, C, etc.).
            tramite_accion: Valor de TramiteAccion (PRIMERA_REVISION o REVISION).

        Returns:
            TarifaPorCategoriaVisitas encontrada y vigente.

        Raises:
            ValueError: Si no se encuentra regla, si la tarifa no es vigente,
                        o si no tiene detalle_visitas.
        """
        today = date.today()

        # Buscar la regla para esta combinación
        regla = ReglaTarifaInspeccionObra.objects.filter(
            categoria=categoria,
            tramite_accion=tramite_accion,
        ).select_related("tarifa_base", "tarifa_base__detalle_visitas").first()

        if regla is None:
            raise ValueError(
                f"No existe ReglaTarifaInspeccionObra para "
                f"categoria={categoria} y tramite_accion={tramite_accion}. "
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

        # Obtener el detalle visitas (OneToOne desde TarifaLiquidacionBase)
        try:
            detalle_visitas = tarifa_base.detalle_visitas
        except TarifaPorCategoriaVisitas.DoesNotExist:
            raise ValueError(
                f"La tarifa base {tarifa_base.id} no tiene detalle TarifaPorCategoriaVisitas."
            )

        if detalle_visitas is None:
            raise ValueError(
                f"La tarifa base {tarifa_base.id} no tiene detalle TarifaPorCategoriaVisitas asociado."
            )

        return detalle_visitas

    def _validar_tarifa_inspeccion_existe(
        self,
        categoria: str,
        tramite_accion: str,
    ) -> bool:
        """
        Valida que exista una tarifa de inspección vigente para la combinación dada.

        Args:
            categoria: Categoría de inspección.
            tramite_accion: Valor de TramiteAccion.

        Returns:
            True si existe y es válida, False en caso contrario.
        """
        try:
            self._buscar_tarifa_inspeccion_por_categoria(categoria, tramite_accion)
            return True
        except ValueError:
            return False

    # ==========================================================================
    # Creación de registros de cálculo
    # ==========================================================================

    def _crear_liquidacion_m2(
        self,
        liquidacion_general: LiquidacionGeneral,
        area_solicitada: Decimal,
        tarifa_m2: TarifaPorMetroCuadrado,
    ) -> LiquidacionPorMetroCuadrado:
        """
        Crea un registro de cálculo LiquidacionPorMetroCuadrado.

        Aplica el helper de cálculo M2 para determinar area_base_calculo y derecho.

        Args:
            liquidacion_general: LiquidacionGeneral asociada.
            area_solicitada: Área total solicitada en m2.
            tarifa_m2: TarifaPorMetroCuadrado a aplicar.

        Returns:
            LiquidacionPorMetroCuadrado creada y persistida.
        """
        # Convertir area_solicitada a Decimal si viene como float/int
        # (el schema permite float pero el helper espera Decimal)
        area_solicitada_dec = Decimal(str(area_solicitada))

        area_calculo, derecho = _calcular_monto_m2(
            area_solicitada=area_solicitada_dec,
            costo_m2=tarifa_m2.costo_por_m2,
            area_minima=tarifa_m2.area_minima,
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

    def _crear_liquidacion_visitas(
        self,
        liquidacion_general: LiquidacionGeneral,
        cantidad_visitas: int,
        categoria: str,
        tarifa_visitas: TarifaPorCategoriaVisitas,
    ) -> LiquidacionPorCategoriaVisitas:
        """
        Crea un registro de cálculo LiquidacionPorCategoriaVisitas.

        Aplica el helper de cálculo de visitas para determinar visitas_base_calculo y derecho.

        Args:
            liquidacion_general: LiquidacionGeneral asociada.
            cantidad_visitas: Número de visitas de inspección.
            categoria: Categoría de inspección.
            tarifa_visitas: TarifaPorCategoriaVisitas a aplicar.

        Returns:
            LiquidacionPorCategoriaVisitas creada y persistida.
        """
        visitas_calculo, derecho = _calcular_monto_visitas(
            cantidad_visitas=cantidad_visitas,
            costo_visita=tarifa_visitas.costo_por_visita,
            visitas_minimas=tarifa_visitas.visitas_minimas,
        )

        liquidacion_visitas = LiquidacionPorCategoriaVisitas.objects.create(
            liquidacion_general=liquidacion_general,
            cantidad_visitas=cantidad_visitas,
            visitas_base_calculo=visitas_calculo,
            derecho=derecho,
            categoria=categoria,
            tarifa_aplicada=tarifa_visitas,
        )

        return liquidacion_visitas

    # ==========================================================================
    # helpers de creación de LiquidacionGeneral para los nuevos tipos
    # ==========================================================================

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
        Crea una LiquidacionGeneral para los nuevos formularios.

        Args:
            proyecto: Proyecto asociado.
            municipalidad: Municipaliddad asociada.
            tipo_liquidacion: Valor de TipoLiquidacion (HABILITACION_URBANA, etc.).
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

    def _generar_public_id_liquidacion_general(self) -> str:
        """
        Genera un public_id único para una LiquidacionGeneral.

        Formato: LIQ-{year}-{count:05d}

        Returns:
            public_id generado.
        """
        year = timezone.now().year
        count = LiquidacionGeneral.objects.filter(
            public_id__startswith=f"LIQ-{year}-"
        ).count()
        return f"LIQ-{year}-{count + 1:05d}"
