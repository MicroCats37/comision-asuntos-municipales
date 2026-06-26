"""
ProyectistaService — operaciones sync de proyectistas.

NOTE: Servicio simplificado para usar PerfilIngeniero referenciado.
Los métodos de búsqueda por DNI/CIP fueron eliminados ya que la identidad
del ingeniero ahora vive en PerfilIngeniero.
"""
from typing import Optional

from ...models import Proyectista
from ...schemas_proyectista import ProyectistaCreateData, ProyectistaResult


class ProyectistaService:
    """
    Servicio core sync para operaciones de Proyectistas.
    """

    def _buscar_por_perfil_y_especialidad(
        self, perfil_ingeniero_id: Optional[str], especialidad_id: str
    ) -> Optional[Proyectista]:
        """Busca proyectista por perfil_ingeniero y especialidad (únicos juntos)."""
        qs = Proyectista.objects.all()
        if perfil_ingeniero_id:
            qs = qs.filter(perfil_ingeniero_id=perfil_ingeniero_id)
        else:
            qs = qs.filter(perfil_ingeniero__isnull=True)
        return qs.filter(especialidad_id=especialidad_id).first()

    def _crear_proyectista(self, data: ProyectistaCreateData) -> Proyectista:
        """Crea un nuevo proyectista."""
        kwargs = {}
        if data.perfil_ingeniero_id:
            kwargs["perfil_ingeniero_id"] = data.perfil_ingeniero_id
        if data.especialidad_id:
            kwargs["especialidad_id"] = data.especialidad_id
        if data.descripcion is not None:
            kwargs["descripcion"] = data.descripcion
        return Proyectista.objects.create(**kwargs)

    def _actualizar_proyectista(self, proyectista: Proyectista, data: ProyectistaCreateData) -> Proyectista:
        """Actualiza un proyectista existente."""
        if data.perfil_ingeniero_id:
            proyectista.perfil_ingeniero_id = data.perfil_ingeniero_id
        if data.especialidad_id:
            proyectista.especialidad_id = data.especialidad_id
        if data.descripcion is not None:
            proyectista.descripcion = data.descripcion
        proyectista.save()
        return proyectista

    def _obtener_por_id(self, proyectista_id: str) -> Optional[Proyectista]:
        """Obtiene proyectista por ID."""
        return Proyectista.objects.filter(id=proyectista_id).first()

    def _to_result(self, proyectista: Proyectista) -> ProyectistaResult:
        """Convierte proyectista a result object."""
        perfil = proyectista.perfil_ingeniero
        nombres = getattr(perfil, 'nombres', None) if perfil else None
        apellidos = f"{getattr(perfil, 'apellido_paterno', '') if perfil else ''} {getattr(perfil, 'apellido_materno', '') if perfil else ''}".strip()
        cip = getattr(perfil, 'cip', None) if perfil else None
        return ProyectistaResult(
            id=str(proyectista.id),
            perfil_ingeniero_id=str(proyectista.perfil_ingeniero_id) if proyectista.perfil_ingeniero_id else None,
            perfil_ingeniero_nombres=nombres,
            perfil_ingeniero_apellidos=apellidos or None,
            perfil_ingeniero_cip=cip,
            especialidad_id=str(proyectista.especialidad_id) if proyectista.especialidad_id else None,
            especialidad_nombre=proyectista.especialidad.nombre if proyectista.especialidad else None,
            descripcion=proyectista.descripcion,
        )
