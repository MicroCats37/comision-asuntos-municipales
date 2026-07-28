"""Inspección de Obra Core — lógica de negocio para Inspección de Obra."""
from datetime import date
from decimal import Decimal
from typing import Optional
from django.utils import timezone

from modules.liquidaciones.models import (
    LiquidacionGeneral,
    LiquidacionInspeccionObra,
    LiquidacionPorCategoriaVisitas,
    TarifaPorCategoriaVisitas,
    TarifaLiquidacionBase,
    ReglaTarifaInspeccionObra,
)
from modules.liquidaciones.domain.constants import (
    TipoLiquidacion,
    TramiteAccion,
)
from modules.liquidaciones.domain.services.core.calculos_helpers import (
    _calcular_monto_visitas,
)
from core.utils import esta_vigente


class InspeccionObraCoreService:
    """
    Servicio core sync para liquidaciones de Inspección de Obra.

    Crea LiquidacionGeneral + LiquidacionInspeccionObra + LiquidacionPorCategoriaVisitas.
    """

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
        return LiquidacionInspeccionObra.objects.create(
            liquidacion=liquidacion_general,
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
            public_id__startswith=f"IO-{year}-"
        ).count()
        return f"IO-{year}-{count + 1:05d}"

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
        Crea LiquidacionGeneral para Inspección de Obra.

        Args:
            proyecto: Proyecto asociado.
            municipalidad: Municipaliddad asociada.
            tipo_liquidacion: Valor de TipoLiquidacion (INSPECCION_OBRA).
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
        tramite_accion: str,
        categoria: str | None = None,
    ) -> list[dict]:
        """
        Obtiene las tarifas vigentes de Inspección de Obra para el formulario.

        Args:
            tramite_accion: Acción de trámite (PRIMERA_REVISION o REVISION).
            categoria: Filter by inspection category (e.g. CATEGORIA_A, CATEGORIA_B).
                Optional — if not provided, returns tariffs for all categories.

        Returns:
            Lista de diccionarios con tarifas de inspección vigentes.
            Cada dict contiene: tarifa_id, detalle_id, costo_por_visita,
            visitas_minimas, categoria, habilitada.
        """
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

    def _buscar_liquidaciones_previas_por_documento(
        self,
        numero_documento: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        """
        Busca liquidaciones previas de Inspección de Obra por número de documento de entidad.

        Las liquidaciones previas de IO son aquellas con:
        - tipo_liquidacion = "INSPECCION_OBRA"
        - numero_revision = 0 (registros preliminares que sirven de base para nueva IO)

        Args:
            numero_documento: DNI o RUC de la entidad asociada al proyecto.
            page: Número de página (1-indexed).
            page_size: Elementos por página.

        Returns:
            (lista_de_datos_materializados, total)
        """
        from django.db.models import Max, OuterRef, Subquery

        qs = LiquidacionGeneral.objects.filter(
            tipo_liquidacion="INSPECCION_OBRA",
            numero_revision=0,
        )

        # Filtro por número de documento de la entidad del proyecto
        if numero_documento:
            qs = qs.filter(proyecto__entidad__numero_documento=numero_documento)

        # Latest per project: para cada proyecto, retornar solo la liquidación más reciente
        # (por id más alto = más reciente en caso de múltiples revision=0)
        # Usamos un subquery que obtiene el max id por proyecto
        latest_id_subquery = LiquidacionGeneral.objects.filter(
            tipo_liquidacion="INSPECCION_OBRA",
            numero_revision=0,
            proyecto=OuterRef('proyecto'),
        ).order_by('-id').values('id')[:1]
        qs = qs.filter(id=Subquery(latest_id_subquery))

        qs = qs.select_related(
            'proyecto', 'proyecto__entidad', 'municipalidad', 'igv',
        ).prefetch_related(
            'liquidacion_visitas',
            'edificaciones',
            'liquidacion_proyectistas__proyectista__perfil_ingeniero',
            'liquidacion_proyectistas__proyectista__especialidad',
            'liquidacion_delegados__delegado__perfil_ingeniero',
            'liquidacion_delegados__delegado__especialidad',
            'contactos__contacto',
        ).order_by('-created_at')

        total = qs.count()
        offset = (page - 1) * page_size
        qs = qs[offset:offset + page_size]

        liquidaciones = list(qs)
        if not liquidaciones:
            return [], total

        items = []
        for liq in liquidaciones:
            subtotal_val = float(liq.sub_total) if liq.sub_total else 0.0
            igv_valor = float(liq.igv.valor) if liq.igv and liq.igv.valor else 0.0
            igv_amount = subtotal_val * igv_valor
            total_liquidacion = subtotal_val + igv_amount
            total_a_pagar = total_liquidacion

            # Entidad
            entidad_dict = None
            if liq.proyecto and liq.proyecto.entidad:
                entidad_dict = {
                    'id': str(liq.proyecto.entidad.id),
                    'tipo': liq.proyecto.entidad.tipo_documento,
                    'nombre': liq.proyecto.entidad.razon_social,
                    'ruc': liq.proyecto.entidad.numero_documento,
                }

            # Valores
            valores_dict = {
                'subtotal': subtotal_val,
                'igv': igv_amount,
                'total': total_liquidacion,
                'total_a_pagar': total_a_pagar,
            }

            items.append({
                'id': str(liq.id),
                'public_id': str(liq.public_id) if liq.public_id else None,
                'tipo_liquidacion': liq.tipo_liquidacion,
                'estado': liq.estado,
                'numero_revision': liq.numero_revision,
                'fecha_registro': liq.created_at.isoformat() if liq.created_at else '',
                'proyecto': {
                    'id': str(liq.proyecto.id) if liq.proyecto else '',
                    'public_id': str(liq.proyecto.public_id) if liq.proyecto and liq.proyecto.public_id else '',
                    'nombre': liq.proyecto.denominacion if liq.proyecto else '',
                    'direccion': liq.proyecto.direccion if liq.proyecto else None,
                    'valor_proyecto': 0.0,
                    'entidad': entidad_dict,
                },
                'entidad': entidad_dict,
                'municipalidad': {
                    'id': str(liq.municipalidad.id) if liq.municipalidad else '',
                    'nombre': liq.municipalidad.nombre if liq.municipalidad else '',
                    'codigo': liq.municipalidad.codigo if liq.municipalidad else None,
                    'provincia': None,
                    'distrito': None,
                },
                'valores': valores_dict,
                'proyectistas': [],
                'delegados': [],
                'contactos': [],
                'revisiones': [],
            })

        return items, total
