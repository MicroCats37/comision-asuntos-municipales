"""
related_batch.py - Generic grouped batch processor for related models.

Reusable sync batch processor with grouped shape:
{
    "create": [CreateBody, ...],
    "update": [{"id": "...", "body": UpdateBody}, ...],
    "delete": ["id", ...]
}

Type design:
    - ID generic supports str/UUID/int via TypeVar bounds.
    - Create/update body types are generic (can differ).
    - Result types are generic (can differ).
    - Pydantic Ninja Schema with proper generic support.

Usage:
    from core.services.related_batch import (
        BatchPayload,
        BatchUpdateItem,
        BatchProcessResult,
        process_batch_payload,
    )

    # In a service method (sync, inside transaction.atomic):
    def _sync_fechas_bloqueadas_batch(
        self,
        bungalow: Bungalow,
        payload: BatchPayload[str, FechaBloqueadaCreateIn, FechaBloqueadaUpdateIn],
    ) -> BatchProcessResult[FechaBloqueadaOut, FechaBloqueadaOut, str]:
        def create_fn(body: FechaBloqueadaCreateIn) -> FechaBloqueadaOut:
            instance = BungalowFechaBloqueada.objects.create(
                bungalow=bungalow,
                fecha=body.fecha,
                motivo=body.motivo or "",
            )
            return _map_fecha_bloqueada(instance)

        def update_fn(id_: str, body: FechaBloqueadaUpdateIn) -> FechaBloqueadaOut:
            instance = BungalowFechaBloqueada.objects.get(id=id_)
            if body.fecha:
                instance.fecha = body.fecha
            if body.motivo is not None:
                instance.motivo = body.motivo or ""
            instance.save()
            return _map_fecha_bloqueada(instance)

        def delete_fn(id_: str) -> str:
            instance = BungalowFechaBloqueada.objects.get(id=id_)
            instance.delete()
            return id_

        result = process_batch_payload(
            payload=payload,
            create_fn=create_fn,
            update_fn=update_fn,
            delete_fn=delete_fn,
        )
        return result

Example for BungalowImagen:
    payload = BatchPayload(
        create=[ImagenCreateIn(imagen="file_token", orden=1)],
        update=[BatchUpdateItem(id="uuid-1", body=ImagenUpdateIn(orden=2))],
        delete=["uuid-2"],
    )
    result = process_batch_payload(
        payload=payload,
        create_fn=lambda body: create_image(body),
        update_fn=lambda id_, body: update_image(id_, body),
        delete_fn=lambda id_: delete_image(id_),
    )
    # result.created: list[ImagenOut], result.updated: list[ImagenOut], result.deleted: list[str]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, TypeVar, Union

from ninja import Schema
from pydantic import BaseModel, ConfigDict

# ── ID TypeVar — supports str, UUID, int ──────────────────────────────────────

ID_T = TypeVar("ID_T")

# ── Body TypeVars ─────────────────────────────────────────────────────────────

TCreateBody = TypeVar("TCreateBody")
TUpdateBody = TypeVar("TUpdateBody")

# ── Result TypeVars ────────────────────────────────────────────────────────────

TCreated = TypeVar("TCreated")
TUpdated = TypeVar("TUpdated")
TDeleted = TypeVar("TDeleted")


# ── BatchUpdateItem ────────────────────────────────────────────────────────────
# Using dataclass instead of Pydantic Schema to better support generics
# in Python < 3.12 (Pydantic generic aliases have compatibility issues).


@dataclass(unsafe_hash=True)
class BatchUpdateItem(Generic[ID_T, TUpdateBody]):
    """
    A single update operation: the id to update and the body to apply.

    Type parameters:
        ID_T:  Id type (str, UUID, int, …).
        TUpdateBody:  Schema / dataclass for the update payload.

    Example:
        item = BatchUpdateItem(id="uuid-123", body=FechaBloqueadaUpdateIn(fecha=date(2025, 12, 25)))
    """

    id: ID_T
    body: TUpdateBody


# ── BatchPayload ───────────────────────────────────────────────────────────────


@dataclass
class BatchPayload(Generic[ID_T, TCreateBody, TUpdateBody]):
    """
    Grouped batch payload containing separate create, update, and delete lists.

    Shape:
        {
            "create": [CreateBody, ...],
            "update": [BatchUpdateItem[id, UpdateBody], ...],
            "delete": [id, ...]
        }

    Type parameters:
        ID_T:  Id type (str, UUID, int, …).
        TCreateBody:  Schema / dataclass for create payloads.
        TUpdateBody:  Schema / dataclass for update payloads.

    Example:
        payload = BatchPayload(
            create=[FechaBloqueadaCreateIn(fecha=date(2025, 1, 1), motivo="Maintenance")],
            update=[
                BatchUpdateItem(
                    id="uuid-existing",
                    body=FechaBloqueadaUpdateIn(motivo="Updated reason"),
                )
            ],
            delete=["uuid-to-remove"],
        )
    """

    create: list[TCreateBody] = field(default_factory=list)
    update: list[BatchUpdateItem[ID_T, TUpdateBody]] = field(default_factory=list)
    delete: list[ID_T] = field(default_factory=list)


# ── BatchProcessResult ─────────────────────────────────────────────────────────


@dataclass
class BatchProcessResult(Generic[TCreated, TUpdated, TDeleted]):
    """
    Result of a batch process operation, with grouped created, updated, and deleted items.

    Type parameters:
        TCreated:  Type of each created item result.
        TUpdated:  Type of each updated item result.
        TDeleted:  Type of each deleted id (often just str).

    Example:
        result = BatchProcessResult(
            created=[FechaBloqueadaOut(id="new-1", fecha=date(2025, 1, 1), motivo="...")],
            updated=[FechaBloqueadaOut(id="uuid-existing", fecha=date(2025, 2, 2), motivo="...")],
            deleted=["uuid-removed"],
        )
    """

    created: list[TCreated] = field(default_factory=list)
    updated: list[TUpdated] = field(default_factory=list)
    deleted: list[TDeleted] = field(default_factory=list)


# ── Batch Processor ────────────────────────────────────────────────────────────


# Type aliases for the callable signatures accepted by process_batch_payload.
# Using Protocol would be cleaner but Callable[...] is more compatible across
# Python 3.9–3.12 without extra imports.

CreateFn = Callable[[TCreateBody], TCreated]
UpdateFn = Callable[[ID_T, TUpdateBody], TUpdated]
DeleteFn = Callable[[ID_T], TDeleted]


def process_batch_payload(
    payload: BatchPayload[ID_T, TCreateBody, TUpdateBody],
    create_fn: CreateFn[ID_T, TCreateBody, TUpdateBody, TCreated, TUpdated, TDeleted],
    update_fn: UpdateFn[ID_T, TCreateBody, TUpdateBody, TCreated, TUpdated, TDeleted],
    delete_fn: DeleteFn[ID_T, TCreateBody, TUpdateBody, TCreated, TUpdated, TDeleted],
) -> BatchProcessResult[TCreated, TUpdated, TDeleted]:
    """
    Process a grouped batch payload by calling the supplied functions.

    Exceptions from any create_fn / update_fn / delete_fn call propagate
    immediately — the transaction should be managed by the caller
    (e.g. inside transaction.atomic).

    Args:
        payload: BatchPayload[ID_T, TCreateBody, TUpdateBody] with create/update/delete lists.
        create_fn: Callable[[TCreateBody], TCreated] — called for each create item.
        update_fn: Callable[[ID_T, TUpdateBody], TUpdated] — called for each update item.
        delete_fn: Callable[[ID_T], TDeleted] — called for each delete id.

    Returns:
        BatchProcessResult[TCreated, TUpdated, TDeleted] with grouped results.

    Example (BungalowFechaBloqueada):
        def create_fecha(body: FechaBloqueadaCreateIn) -> FechaBloqueadaOut:
            instance = BungalowFechaBloqueada.objects.create(
                bungalow=bungalow, fecha=body.fecha, motivo=body.motivo or ""
            )
            return _map_fecha(instance)  # presenter mapper

        def update_fecha(id_: str, body: FechaBloqueadaUpdateIn) -> FechaBloqueadaOut:
            instance = BungalowFechaBloqueada.objects.get(id=id_)
            if body.fecha:
                instance.fecha = body.fecha
            if body.motivo is not None:
                instance.motivo = body.motivo or ""
            instance.save()
            return _map_fecha(instance)

        def delete_fecha(id_: str) -> str:
            instance = BungalowFechaBloqueada.objects.get(id=id_)
            instance.delete()
            return id_

        result = process_batch_payload(
            payload=payload,
            create_fn=create_fecha,
            update_fn=update_fecha,
            delete_fn=delete_fecha,
        )
        # result.created: list[FechaBloqueadaOut]
        # result.updated: list[FechaBloqueadaOut]
        # result.deleted: list[str]

    Example (BungalowImagen):
        def create_imagen(body: ImagenCreateIn) -> BungalowImagenOut:
            instance = BungalowImagen.objects.create(
                bungalow=bungalow, imagen=body.imagen, orden=body.orden or 0
            )
            return _map_imagen(instance)

        def update_imagen(id_: str, body: ImagenUpdateIn) -> BungalowImagenOut:
            instance = BungalowImagen.objects.get(id=id_)
            if body.imagen:
                instance.imagen = body.imagen
            if body.orden is not None:
                instance.orden = body.orden or 0
            instance.save()
            return _map_imagen(instance)

        def delete_imagen(id_: str) -> str:
            instance = BungalowImagen.objects.get(id=id_)
            instance.delete()
            return id_

        result = process_batch_payload(
            payload=payload,
            create_fn=create_imagen,
            update_fn=update_imagen,
            delete_fn=delete_imagen,
        )
        # result.created: list[BungalowImagenOut]
        # result.updated: list[BungalowImagenOut]
        # result.deleted: list[str]
    """
    created: list[TCreated] = []
    updated: list[TUpdated] = []
    deleted: list[TDeleted] = []

    # ── Process creates ────────────────────────────────────────────────────────
    for body in payload.create:
        result = create_fn(body)
        created.append(result)

    # ── Process updates ────────────────────────────────────────────────────────
    for item in payload.update:
        result = update_fn(item.id, item.body)
        updated.append(result)

    # ── Process deletes ───────────────────────────────────────────────────────
    for id_ in payload.delete:
        result = delete_fn(id_)
        deleted.append(result)

    return BatchProcessResult[TCreated, TUpdated, TDeleted](
        created=created,
        updated=updated,
        deleted=deleted,
    )