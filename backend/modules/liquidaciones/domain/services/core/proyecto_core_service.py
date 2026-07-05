"""
ProyectoService — lógica de negocio síncrona para proyectos.
"""
from decimal import Decimal
from django.utils import timezone

from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.models import LiquidacionGeneral, LiquidacionEdificacion
from modules.entidades.models import Entidad

from ...schemas_proyecto import (
    EntidadSimpleData,
    EntidadConNumeroDocumentoData,
    EdificacionData,
    LiquidacionesData,
    ProyectoConLiquidacionesData,
    ProyectoCreateData,
    ProyectoInlineData,
    ProyectoPaginatedResult,
    ProyectoResult,
)


class ProyectoService:
    """
    Servicio core para operaciones de Proyecto.

    Solo lógica de negocio síncrona.
    """

    def _generar_public_id(self) -> str:
        """
        Genera un public_id único para un proyecto.

        Formato: PROY-{year}-{count:05d}

        Returns:
            public_id generado
        """
        year = timezone.now().year
        count = Proyecto.objects.filter(
            public_id__startswith=f"PROY-{year}-"
        ).count()
        return f"PROY-{year}-{count + 1:05d}"

    def _crear_proyecto(self, data: ProyectoCreateData) -> Proyecto:
        """
        Crea un nuevo proyecto.

        Args:
            data: Datos de creación del proyecto

        Returns:
            Proyecto creado
        """
        entidad = None
        if data.entidad_id:
            entidad = Entidad.objects.get(id=data.entidad_id)

        public_id = self._generar_public_id()

        # Copiar campos denormalizados de entidad para preservar histórico
        entidad_razon_social = entidad.razon_social if entidad else None
        entidad_tipo_documento = entidad.tipo_documento if entidad else None
        entidad_numero_documento = entidad.numero_documento if entidad else None

        proyecto = Proyecto(
            denominacion=data.denominacion,
            direccion=data.direccion,
            distrito_id=data.distrito_id,
            entidad=entidad,
            entidad_razon_social=entidad_razon_social,
            entidad_tipo_documento=entidad_tipo_documento,
            entidad_numero_documento=entidad_numero_documento,
            nombre_propietario=entidad.nombre_completo if entidad else "Sinpropietario",
            public_id=public_id,
        )
        proyecto.save()

        return proyecto

    def _crear_proyecto_inline(self, data: "ProyectoInlineData") -> Proyecto:
        """
        Crea un proyecto desde datos inline (proyecto_inline).

        Implementa upsert de Entidad por numero_documento:
        - Si no existe, crea una nueva Entidad con los datos proporcionados.
        - Si existe, actualiza tipo_documento y razon_social si cambian.

        Luego crea el Proyecto con FK a la Entidad y copia los campos
        denormalizados entidad_razon_social, entidad_tipo_documento,
        entidad_numero_documento desde la Entidad resultante.

        Args:
            data: Datos inline del proyecto (denominacion, direccion, distrito_id, entidad)

        Returns:
            Proyecto creado
        """
        from modules.entidades.models import Entidad

        # Upsert Entidad por numero_documento
        entidad, _created = Entidad.objects.update_or_create(
            numero_documento=data.entidad.numero_documento,
            defaults={
                'tipo_documento': data.entidad.tipo_documento,
                'razon_social': data.entidad.razon_social,
            }
        )

        # Copiar campos denormalizados de entidad para preservar histórico
        entidad_razon_social = entidad.razon_social
        entidad_tipo_documento = entidad.tipo_documento
        entidad_numero_documento = entidad.numero_documento

        # Usar nombre_propietario del payload (viene a nivel proyecto_inline, no de entidad)
        nombre_propietario = data.nombre_propietario

        public_id = self._generar_public_id()

        proyecto = Proyecto(
            denominacion=data.denominacion,
            direccion=data.direccion,
            distrito_id=data.distrito_id,
            entidad=entidad,
            entidad_razon_social=entidad_razon_social,
            entidad_tipo_documento=entidad_tipo_documento,
            entidad_numero_documento=entidad_numero_documento,
            nombre_propietario=nombre_propietario,
            public_id=public_id,
        )
        proyecto.save()
        return proyecto

    def _buscar_por_public_id(self, public_id: str) -> Proyecto | None:
        """
        Busca un proyecto por su public_id.

        Args:
            public_id: ID público del proyecto (ej. PROY-2026-00001)

        Returns:
            Proyecto si existe, None si no
        """
        try:
            return Proyecto.objects.get(public_id=public_id)
        except Proyecto.DoesNotExist:
            return None

    def _to_result(self, proyecto: Proyecto) -> ProyectoResult:
        """
        Convierte un Proyecto a ProyectoResult con objetos anidados.

        Args:
            proyecto: Instancia del modelo

        Returns:
            ProyectoResult

        Note:
            proyectista FK fue removido de Proyecto — ahora vive en LiquidacionEdificaciones.proyectistas M2M
            Los campos de entidad usan los valores denormalizados para preservar histórico.
        """
        # Build nested entidad if exists - usar campos denormalizados del proyecto
        entidad = None
        if proyecto.entidad_id:
            entidad = EntidadSimpleData(
                id=proyecto.entidad.id,
                tipo=proyecto.entidad_tipo_documento,
                nombre=proyecto.entidad_razon_social,
            )

        return ProyectoResult(
            id=str(proyecto.id),
            public_id=proyecto.public_id or "",
            denominacion=proyecto.denominacion,
            direccion=proyecto.direccion,
            distrito=proyecto.distrito.nombre if proyecto.distrito else None,
            distrito_id=proyecto.distrito_id if proyecto.distrito else None,
            entidad=entidad,
        )

    def _listar_proyectos_con_liquidaciones_paginado(
        self,
        page: int,
        page_size: int,
    ) -> ProyectoPaginatedResult:
        """
        Lista TODOS los proyectos con sus liquidaciones de edificaciones,
        usando prefetch/select_related para evitar N+1.

        Args:
            page: Número de página (1-indexed)
            page_size: Elementos por página

        Returns:
            ProyectoPaginatedResult con items y total
        """
        # Query base: todos los proyectos, ordenados por created_at descendente
        qs = Proyecto.objects.select_related(
            'entidad',
            'distrito',
        ).prefetch_related(
            'liquidaciones__edificaciones',
        ).order_by('-created_at')

        total = qs.count()
        offset = (page - 1) * page_size
        qs = qs[offset:offset + page_size]

        proyectos = list(qs)
        if not proyectos:
            return ProyectoPaginatedResult(items=[], total=total)

        # Bulk fetch de todas las liquidaciones de estos proyectos (solo edificaciones)
        proyecto_ids = [p.id for p in proyectos]
        liquidaciones_qs = LiquidacionGeneral.objects.filter(
            proyecto_id__in=proyecto_ids,
            edificaciones__isnull=False,
        ).select_related(
            'proyecto',
        ).prefetch_related(
            'edificaciones',
        )
        liquidaciones_by_proyecto = {}
        for liq in liquidaciones_qs:
            if liq.proyecto_id not in liquidaciones_by_proyecto:
                liquidaciones_by_proyecto[liq.proyecto_id] = []
            liquidaciones_by_proyecto[liq.proyecto_id].append(liq)

        # Construir items
        items = []
        for proyecto in proyectos:
            # Entidad - usar campos denormalizados del proyecto para preservar histórico
            entidad_data = None
            if proyecto.entidad_id:
                entidad_data = EntidadConNumeroDocumentoData(
                    id=proyecto.entidad.id,
                    tipo_documento=proyecto.entidad_tipo_documento,
                    numero_documento=proyecto.entidad_numero_documento,
                    nombre=proyecto.entidad_razon_social,
                )

            # Liquidaciones
            edificaciones_list = []
            proyecto_liquidaciones = liquidaciones_by_proyecto.get(proyecto.id, [])
            for liq in proyecto_liquidaciones:
                edif = liq.edificaciones
                if edif:
                    # Obtener total desde LiquidacionGeneral.sub_total con IGV
                    total_liquidacion = Decimal('0')
                    if liq.sub_total:
                        # Calcular total con IGV desde sub_total
                        igv_valor = Decimal(str(liq.igv.valor)) if liq.igv else Decimal('0')
                        total_liquidacion = liq.sub_total * (1 + igv_valor)

                    edificaciones_list.append(EdificacionData(
                        id=edif.id,
                        public_id=edif.public_id or '',
                        numero_revision=edif.numero_revision,
                        estado=liq.estado,
                        fecha_registro=liq.created_at.isoformat() if liq.created_at else '',
                        total=total_liquidacion,
                        tipo_tramite=edif.tipo_tramite,
                        tramite_accion=edif.tramite_accion,
                    ))

            liquidaciones_data = LiquidacionesData(edificaciones=edificaciones_list)

            items.append(ProyectoConLiquidacionesData(
                id=proyecto.id,
                public_id=proyecto.public_id or '',
                denominacion=proyecto.denominacion,
                direccion=proyecto.direccion,
                distrito=proyecto.distrito.nombre if proyecto.distrito else None,
                entidad=entidad_data,
                liquidaciones=liquidaciones_data,
            ))

        return ProyectoPaginatedResult(items=items, total=total)
