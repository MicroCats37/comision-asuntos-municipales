"""
batch.py - Servicio compartido para operaciones de archivos en lote.
Diseñado para modelos que tienen archivos relacionados (ej: Galería, Anexos).
"""

from typing import Callable, Generic, Literal, Optional, TypeVar, Union
from django.db import transaction
from ninja import UploadedFile
from pydantic import BaseModel, ConfigDict

IDType = TypeVar("IDType")


class BatchItemSchema(Generic[IDType], BaseModel):
    """
    Esquema genérico para operaciones en lote sobre archivos.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    action: Literal["CREATE", "UPDATE", "DELETE"]  # CREATE, UPDATE, DELETE
    id: Optional[IDType] = None
    file: Optional[UploadedFile] = None
    descripcion: Optional[str] = None


def process_batch_related_files(
    items: list[BatchItemSchema],
    parent_instance,
    child_model,
    fk_field_name: str,
    file_field_name: str,
    pk_field: str = "id",
    on_create: Optional[Callable] = None,
    on_update: Optional[Callable] = None,
    on_delete: Optional[Callable] = None,
):
    """
    Procesa una lista de operaciones en lote sobre archivos de un modelo hijo.

    Args:
        items: Lista de BatchItemSchema parseados.
        parent_instance: Instancia del modelo padre.
        child_model: Clase del modelo hijo.
        fk_field_name: Nombre del campo FK en el hijo apuntando al padre.
        file_field_name: Nombre del campo de archivo en el hijo.
        on_create: Callback(item_data, nueva_instancia) llamado tras la creación.
        on_update: Callback(item_data, instancia) llamado tras la actualización.
        on_delete: Callback(instancia) llamado antes de la eliminación.
    """
    with transaction.atomic():
        for item in items:
            action = item.action.upper()

            if action == "CREATE":
                # Lógica de creación automática de la instancia hija
                kwargs = {fk_field_name: parent_instance}
                if item.file:
                    kwargs[file_field_name] = item.file
                new_instance = child_model.objects.create(**kwargs)
                if on_create:
                    on_create(item, new_instance)

            elif action == "UPDATE" and item.id:
                # Lógica de actualización de archivo
                try:
                    instance = child_model.objects.get(
                        **{pk_field: getattr(item, "id")}
                    )
                    if item.file:
                        setattr(instance, file_field_name, item.file)
                        instance.save(update_fields=[file_field_name])
                    if on_update:
                        on_update(item, instance)
                except child_model.DoesNotExist:
                    pass

            elif action == "DELETE" and item.id:
                # Lógica de eliminación segura con callback previo
                try:
                    instance = child_model.objects.get(
                        **{pk_field: getattr(item, "id")}
                    )
                    if on_delete:
                        on_delete(instance)
                    instance.delete()
                except child_model.DoesNotExist:
                    pass
