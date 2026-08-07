"""
LiquidacionGeneralCoreService — sync ORM operations for general liquidacion entities.

PURE ORM — no business logic, no conditionals.
Handles: Entidad, Proyecto, LiquidacionGeneral.
"""
from decimal import Decimal
from typing import Optional

from modules.liquidaciones.domain.models.liquidacion.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.entidades.domain.models import Entidad
from modules.liquidaciones.domain.constants import EstadoLiquidacion


class LiquidacionGeneralCoreService:
    """
    Core sync service for general liquidacion ORM operations.
    Pure ORM — no business logic.
    """

    def create_entidad(
        self,
        tipo_documento: str,
        numero_documento: str,
        razon_social: Optional[str] = None,
        direccion: Optional[str] = None,
    ) -> Entidad:
        """
        Creates or returns existing Entidad by numero_documento.
        """
        existente = Entidad.objects.filter(numero_documento=numero_documento).first()
        if existente:
            return existente
        return Entidad.objects.create(
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            razon_social=razon_social,
            direccion=direccion,
        )

    def create_proyecto(
        self,
        proyecto_data: dict,
        entidad: Optional[Entidad] = None,
    ) -> Proyecto:
        """
        Creates a new Proyecto with denormalized entity data.
        """
        return Proyecto.objects.create(
            entidad=entidad,
            denominacion=proyecto_data["denominacion"],
            nombre_propietario=proyecto_data["nombre_propietario"],
            entidad_razon_social=proyecto_data.get("entidad_razon_social"),
            entidad_tipo_documento=proyecto_data.get("entidad_tipo_documento"),
            entidad_numero_documento=proyecto_data.get("entidad_numero_documento"),
            direccion=proyecto_data.get("direccion"),
            urbanizacion=proyecto_data.get("urbanizacion"),
        )

    def create_liquidacion_general(
        self,
        municipalidad_id: str,
        expediente: str,
        observacion: Optional[str],
        proyecto: Proyecto,
        tipo_liquidacion: str,
        numero_revision: int = 1,
    ) -> LiquidacionGeneral:
        """
        Creates a LiquidacionGeneral base record.
        """
        return LiquidacionGeneral.objects.create(
            proyecto=proyecto,
            municipalidad_id=municipalidad_id,
            expediente=expediente,
            observacion=observacion,
            estado=EstadoLiquidacion.PENDIENTE,
            tipo_liquidacion=tipo_liquidacion,
            numero_revision=numero_revision,
            sub_total=Decimal("0"),
            total=Decimal("0"),
        )
