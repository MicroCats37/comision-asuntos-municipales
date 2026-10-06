"""
EntidadesCoreService — operaciones sync de entidades.
"""
from typing import Optional

from ..models import Entidad
from ..schemas import EntidadCreateData, EntidadResult


class EntidadesCoreService:
    """
    Servicio core sync para operaciones de Entidades.
    """

    def _buscar_por_numero_documento(self, numero_documento: str) -> Optional[Entidad]:
        """Busca entidad por número de documento."""
        return Entidad.objects.filter(numero_documento=numero_documento).first()

    def _crear_entidad(self, data: EntidadCreateData) -> Entidad:
        """Crea una nueva entidad."""
        return Entidad.objects.create(
            tipo_documento=data.tipo_documento,
            numero_documento=data.numero_documento,
            razon_social=data.razon_social,
            nombre_comercial=data.nombre_comercial,
            direccion=data.direccion,
        )

    def _actualizar_entidad(self, entidad: Entidad, data: EntidadCreateData) -> Entidad:
        """Actualiza una entidad existente."""
        entidad.razon_social = data.razon_social
        entidad.nombre_comercial = data.nombre_comercial
        entidad.direccion = data.direccion
        entidad.save()
        return entidad

    def _obtener_por_id(self, entidad_id: str) -> Optional[Entidad]:
        """Obtiene entidad por ID."""
        return Entidad.objects.filter(id=entidad_id).first()

    def _to_result(self, entidad: Entidad) -> EntidadResult:
        """Convierte entidad a result object."""
        return EntidadResult(
            id=str(entidad.id),
            tipo_documento=entidad.tipo_documento,
            numero_documento=entidad.numero_documento,
            razon_social=entidad.razon_social,
            nombre_completo=entidad.nombre_completo,
            direccion=entidad.direccion,
        )

    def _obtener_distritos(
        self,
        search: str | None = None,
        provincia_id: str | None = None,
        departamento_id: str | None = None,
    ) -> list:
        """
        Obtiene distritos con filtros opcionales (sync).

        Args:
            search: Texto para filtrar por nombre de distrito
            provincia_id: ID de provincia para filtrar
            departamento_id: ID de departamento para filtrar

        Returns:
            Lista de distritos que cumplen los filtros
        """
        from modules.entidades.domain.models.ubigeo import UbigeoDistrito

        queryset = UbigeoDistrito.objects.all()

        if search:
            queryset = queryset.filter(nombre__icontains=search)

        if provincia_id:
            queryset = queryset.filter(provincia_id=provincia_id)

        if departamento_id:
            queryset = queryset.filter(provincia__departamento_id=departamento_id)

        # Materializar QuerySet ANTES de retornar (obligatorio en contexto sync-to-async)
        return list(
            queryset.select_related("provincia__departamento").order_by(
                "provincia__departamento__nombre", "provincia__nombre", "nombre"
            )
        )

    def _obtener_municipalidades(self) -> list:
        """Obtiene todas las municipalidades registradas."""
        from modules.entidades.domain.models import Municipalidad

        return list(
            Municipalidad.objects.all()
            .select_related("provincia", "distrito__provincia")
            .order_by("nombre")
        )
