"""
ProyectoService — lógica de negocio síncrona para proyectos.
"""
from django.utils import timezone

from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.entidades.models import Entidad

from ...schemas_proyecto import (
    EntidadSimpleData,
    ProyectoCreateData,
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

        proyecto = Proyecto(
            denominacion=data.denominacion,
            direccion=data.direccion,
            distrito_id=data.distrito_id,
            entidad=entidad,
            nombre_propietario=entidad.nombre_completo if entidad else "Sinpropietario",
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
        """
        # Build nested entidad if exists
        entidad = None
        if proyecto.entidad:
            entidad = EntidadSimpleData(
                id=proyecto.entidad.id,
                tipo=proyecto.entidad.tipo_documento,
                nombre=proyecto.entidad.nombre_completo,
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
