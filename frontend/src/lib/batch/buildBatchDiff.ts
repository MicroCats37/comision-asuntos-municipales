/**
 * Generic batch operations — core engine.
 *
 * Provides the batch diff algorithm that works with any domain
 * via a feature adapter. The adapter knows how to extract IDs,
 * compare objects, and build create/update/delete payloads.
 *
 * Feature adapters live under features/*[/]adapters/.
 */

import type { BatchAdapter, BatchDiffResult, BatchPayload } from "./types";

/**
 * Computes the batch diff between original and edited collections
 * using a feature adapter for domain-specific operations.
 *
 * - Items in edited but not in original → create (via adapter.buildCreate)
 * - Items in original but not in edited → delete (via adapter.buildDelete)
 * - Items in both but body differs → update (via adapter.buildUpdate)
 *
 * @param original - Original items (e.g., from API response)
 * @param edited - Edited items (e.g., from form state)
 * @param adapter - Feature-specific adapter with buildCreate/buildUpdate/buildDelete
 * @returns BatchDiffResult with typed create, update, delete arrays
 */
export function buildBatchDiff<
  TOriginal,
  TEdited,
  TCreate,
  TUpdate,
  TDelete extends { id: string | number },
  TId extends string | number,
>(
  original: TOriginal[],
  edited: TEdited[],
  adapter: BatchAdapter<TOriginal, TEdited, TCreate, TUpdate, TDelete, TId>,
): BatchDiffResult<TCreate, TUpdate, TDelete, TId> {
  const result: BatchDiffResult<TCreate, TUpdate, TDelete, TId> = {
    create: [],
    update: [],
    delete: [],
  };

  // Index original items by their ID
  const originalById = new Map<TId, TOriginal>();
  for (const item of original) {
    const id = adapter.getOriginalId(item);
    if (id !== undefined) {
      originalById.set(id, item);
    }
  }

  // Index edited items by their ID (undefined ID = new item)
  const editedById = new Map<TId | "NEW", TEdited>();
  for (const item of edited) {
    const id = adapter.getEditedId(item);
    if (id !== undefined) {
      editedById.set(id, item);
    } else {
      editedById.set("NEW", item);
    }
  }

  // Find deleted items (in original but not in edited, or marked deleted)
  for (const [id, originalItem] of originalById) {
    const editedItem = editedById.get(id);
    if (editedItem === undefined) {
      // Not in edited collection — delete
      const deleteItem = adapter.buildDelete(originalItem);
      if (deleteItem !== null) {
        result.delete.push(deleteItem as TDelete);
      }
    } else if (adapter.isDeleted?.(editedItem)) {
      // Marked as deleted — delete
      const deleteItem = adapter.buildDelete(originalItem);
      if (deleteItem !== null) {
        result.delete.push(deleteItem as TDelete);
      }
    }
  }

  // Find creates and updates
  for (const editedItem of edited) {
    // Skip soft-deleted items — they were already handled above
    if (adapter.isDeleted?.(editedItem)) {
      continue;
    }

    const editedId = adapter.getEditedId(editedItem);
    if (editedId === undefined) {
      // No ID = new item
      result.create.push(adapter.buildCreate(editedItem));
    } else {
      // Has ID = check if changed
      const originalItem = originalById.get(editedId);
      if (originalItem !== undefined) {
        const updateBody = adapter.buildUpdate(originalItem, editedItem);
        if (updateBody !== null) {
          result.update.push({
            id: editedId,
            body: updateBody as Partial<TUpdate>,
          });
        }
      }
    }
  }

  return result;
}

/**
 * Builds a Map from items using a key function.
 */
export function buildMap<T, K extends string | number>(
  items: T[],
  getKey: (item: T) => K,
): Map<K, T> {
  const map = new Map<K, T>();
  for (const item of items) {
    map.set(getKey(item), item);
  }
  return map;
}

/**
 * Converts a BatchDiffResult to a BatchPayload, filtering out empty arrays.
 * Returns null if all arrays are empty.
 */
export function toBatchPayload<
  TCreate,
  TUpdate,
  TDelete,
  TId extends string | number,
>(
  diff: BatchDiffResult<TCreate, TUpdate, TDelete, TId>,
): BatchPayload<TCreate, TUpdate, TDelete, TId> | null {
  const hasCreate = diff.create.length > 0;
  const hasUpdate = diff.update.length > 0;
  const hasDelete = diff.delete.length > 0;

  if (!hasCreate && !hasUpdate && !hasDelete) {
    return null;
  }

  return {
    create: diff.create,
    update: diff.update,
    delete: diff.delete,
  };
}

/**
 * Shorthand to build a batch diff and convert to payload in one step.
 * Returns null if nothing changed.
 */
export function computeBatchPayload<
  TOriginal,
  TEdited,
  TCreate,
  TUpdate,
  TDelete extends { id: string | number },
  TId extends string | number,
>(
  original: TOriginal[],
  edited: TEdited[],
  adapter: BatchAdapter<TOriginal, TEdited, TCreate, TUpdate, TDelete, TId>,
): BatchPayload<TCreate, TUpdate, TDelete, TId> | null {
  const diff = buildBatchDiff(original, edited, adapter);
  return toBatchPayload(diff);
}

// ── Legacy compat exports ──────────────────────────────────────────────────────

export type {
  BatchAdapter,
  BatchDiffResult,
  BatchPayload,
  BatchUpdateItem,
} from "./types";
