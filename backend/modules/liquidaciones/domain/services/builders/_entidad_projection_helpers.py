"""
Helpers de proyección de entidad — extrae datos de entidad desde un proyecto.

Este módulo contiene funciones puras sin dependencias ORM para proyectar
los datos de entidad desde una instancia de proyecto.
"""

from __future__ import annotations

from typing import Optional, Tuple


def _proyectar_entidad_desde_proyecto(proyecto) -> Tuple[Optional[int], Optional[str], Optional[str], Optional[str]]:
    """
    Proyecta los datos de entidad desde una instancia de proyecto.

    Args:
        proyecto: Instancia de Proyecto (ORM) con atributos de entidad.

    Returns:
        Tuple de (entidad_id, entidad_tipo, entidad_nombre, entidad_ruc):
        - entidad_id: ID de la entidad (entidad_id)
        - entidad_tipo: Tipo de documento (entidad_tipo_documento)
        - entidad_nombre: Razón social (entidad_razon_social)
        - entidad_ruc: Número de documento solo si tipo es 'RUC', sino None
    """
    entidad_id = getattr(proyecto, 'entidad_id', None)
    entidad_tipo = getattr(proyecto, 'entidad_tipo_documento', None)
    entidad_nombre = getattr(proyecto, 'entidad_razon_social', None)
    entidad_ruc = getattr(proyecto, 'entidad_numero_documento', None) if entidad_tipo == 'RUC' else None

    return entidad_id, entidad_tipo, entidad_nombre, entidad_ruc
