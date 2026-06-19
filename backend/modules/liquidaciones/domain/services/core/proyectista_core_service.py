"""
ProyectistaService — operaciones sync de proyectistas.
"""
from typing import Optional

from ...models import Proyectista
from ...schemas_proyectista import ProyectistaCreateData, ProyectistaResult


class ProyectistaService:
    """
    Servicio core sync para operaciones de Proyectistas.
    """

    def _buscar_por_dni(self, dni: str) -> Optional[Proyectista]:
        """Busca proyectista por DNI."""
        if not dni:
            return None
        return Proyectista.objects.filter(dni=dni).first()

    def _buscar_por_cip(self, cip: str) -> Optional[Proyectista]:
        """Busca proyectista por CIP."""
        if not cip:
            return None
        return Proyectista.objects.filter(cip=cip).first()

    def _crear_proyectista(self, data: ProyectistaCreateData) -> Proyectista:
        """Crea un nuevo proyectista."""
        return Proyectista.objects.create(
            nombres=data.nombres,
            apellidos=data.apellidos,
            cip=data.cip,
            dni=data.dni,
            cap=data.cap,
        )

    def _actualizar_proyectista(self, proyectista: Proyectista, data: ProyectistaCreateData) -> Proyectista:
        """Actualiza un proyectista existente."""
        proyectista.nombres = data.nombres
        proyectista.apellidos = data.apellidos
        if data.cip:
            proyectista.cip = data.cip
        if data.dni:
            proyectista.dni = data.dni
        if data.cap:
            proyectista.cap = data.cap
        proyectista.save()
        return proyectista

    def _obtener_por_id(self, proyectista_id: str) -> Optional[Proyectista]:
        """Obtiene proyectista por ID."""
        return Proyectista.objects.filter(id=proyectista_id).first()

    def _to_result(self, proyectista: Proyectista) -> ProyectistaResult:
        """Convierte proyectista a result object."""
        return ProyectistaResult(
            id=str(proyectista.id),
            nombres=proyectista.nombres,
            apellidos=proyectista.apellidos,
            cip=proyectista.cip,
            dni=proyectista.dni,
            cap=proyectista.cap,
        )
