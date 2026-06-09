"""
m2m.py - Procesamiento de cambios de relaciones Many-to-Many (Deltas).
Útil para evitar recrear toda la tabla intermedia en cada guardado.
"""

from django.db import transaction
from core.schemas import M2MDiffSchema


def process_m2m_diff(
    instance,
    data: M2MDiffSchema,
    intermediate_model,
    target_field_name: str,
    source_field_name: str,
):
    """
    Procesamiento transaccional de diferencias en una relación M2M.

    Args:
        instance: Instancia principal (el padre).
        data: Esquema validado de diferencias (add/remove).
        intermediate_model: Clase de la tabla intermedia.
        target_field_name: Nombre del campo FK destino.
        source_field_name: Nombre del campo FK origen (apunta a 'instance').
    """
    if not data.add and not data.remove:
        return

    with transaction.atomic():
        # Insertar nuevas relaciones (Evitando duplicados con get_or_create)
        for target_id in data.add:
            intermediate_model.objects.get_or_create(
                **{source_field_name: instance, target_field_name: target_id}
            )

        # Eliminar relaciones marcadas
        if data.remove:
            intermediate_model.objects.filter(
                **{source_field_name: instance, f"{target_field_name}__in": data.remove}
            ).delete()
