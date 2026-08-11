"""
IngenieroHabilitacionCoreService — operaciones sync para registro de búsquedas.

NO usa transaction.atomic() internamente — el llamador (flujo) provee la transacción si es necesaria.
"""
from datetime import date
from typing import Optional

from django.utils import timezone

from modules.usuarios.domain.models.perfil_ingeniero import (
    IngenieroHabilitacion,
    PerfilIngeniero,
)


class IngenieroHabilitacionCoreService:
    """
    Servicio core sync para operaciones de IngenieroHabilitacion.
    
    Responsable del registro de búsquedas de ingeniero habilitado con deduplicación diaria.
    """

    def registrar_busqueda(
        self,
        perfil_ingeniero: PerfilIngeniero,
        condicion_cip: Optional[str],
        ultimo_periodo_pagado_cip: Optional[str],
        fecha: Optional[date] = None,
    ) -> IngenieroHabilitacion:
        """
        Registra una búsqueda de ingeniero habilitado con deduplicación diaria.

        Usa update_or_create para:
        - Crear un nuevo registro si no existe para (perfil_ingeniero, fecha)
        - Actualizar condicion_cip y ultimo_periodo_pagado_cip si ya existe
          (el estado de habilitación puede cambiar entre búsquedas del mismo día)

        Args:
            perfil_ingeniero: Instancia de PerfilIngeniero
            condicion_cip: Condición actual del CIP (ej. '1' = habilitado)
            ultimo_periodo_pagado_cip: Último período pagado según CIP
            fecha: Fecha de la búsqueda (default: timezone.localdate())

        Returns:
            Instancia de IngenieroHabilitacion creada o actualizada
        """
        if fecha is None:
            fecha = timezone.localdate()

        obj, _ = IngenieroHabilitacion.objects.update_or_create(
            perfil_ingeniero=perfil_ingeniero,
            fecha_busqueda=fecha,
            defaults={
                "condicion_cip": condicion_cip,
                "ultimo_periodo_pagado_cip": ultimo_periodo_pagado_cip,
            },
        )
        return obj
