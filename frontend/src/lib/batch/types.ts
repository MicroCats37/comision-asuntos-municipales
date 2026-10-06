/**
 * Generic typed batch operations — TypeScript types.
 *
 * These types are domain-agnostic. They define the shape of batch payloads
 * and the adapter interface for converting domain objects to/from batch ops.
 *
 * Feature adapters (not these types) live under features/*[/]adapters/.
 */

/**
 * Marker type for create operations — items being added have no ID yet.
 */
export interface TCreate {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  [key: string]: unknown;
}

/**
 * Marker type for update operations — partial update body.
 */
export interface TUpdate {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  [key: string]: unknown;
}

/**
 * Marker type for delete operations — identifies what to delete.
 */
export interface TDelete {
  readonly id: string;
}

/**
 * Identifies a record by its stable ID type.
 */
export interface TId {
  readonly id: string;
}

/**
 * Single update item: ID + partial body.
 */
export interface BatchUpdateItem<TId extends string | number, TUpdate> {
  id: TId;
  body: Partial<TUpdate>;
}

/**
 * Batch payload returned by the batch engine.
 * Contains create, update, and delete operations ready for the API.
 */
export interface BatchPayload<
  TCreate,
  TUpdate,
  TDelete,
  TId extends string | number,
> {
  create: TCreate[];
  update: BatchUpdateItem<TId, TUpdate>[];
  delete: TDelete[];
}

/**
 * Adapter interface for converting domain objects to batch operations.
 *
 * @template TOriginal - The original domain object (from API response)
 * @template TEdited - The edited domain object (from form/UI state)
 * @template TCreate - Shape of a create payload item
 * @template TUpdate - Shape of an update body (partial)
 * @template TDelete - Shape of a delete item (must have id)
 * @template TId - Type of the ID field
 */
export interface BatchAdapter<
  TOriginal,
  TEdited,
  TCreate,
  TUpdate,
  TDelete,
  TId extends string | number,
> {
  /** Extract ID from an original object */
  getOriginalId: (item: TOriginal) => TId | undefined;
  /** Extract ID from an edited object */
  getEditedId: (item: TEdited) => TId | undefined;
  /** Whether this item is marked as deleted (soft-delete flag) */
  isDeleted?: (item: TEdited) => boolean;
  /** Build a create payload from an edited item */
  buildCreate: (item: TEdited) => TCreate;
  /** Build an update body from an edited item (partial, only changed fields) */
  buildUpdate: (
    original: TOriginal,
    edited: TEdited,
  ) => Partial<TUpdate> | null;
  /** Build a delete item from an original item */
  buildDelete: (original: TOriginal) => TDelete | null;
}

/**
 * Result of comparing original vs edited collections.
 */
export interface BatchDiffResult<
  TCreate,
  TUpdate,
  TDelete,
  TId extends string | number,
> {
  create: TCreate[];
  update: BatchUpdateItem<TId, TUpdate>[];
  delete: TDelete[];
}
