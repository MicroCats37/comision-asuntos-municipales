/**
 * Generic batch operations — public API.
 *
 * Core engine and types are generic/domain-agnostic.
 * Feature adapters live under features/*[/]adapters/.
 */

export type {
  BatchAdapter,
  BatchDiffResult,
  BatchPayload,
  BatchUpdateItem,
  TCreate,
  TDelete,
  TId,
  TUpdate,
} from "./types";

export {
  buildBatchDiff,
  buildMap,
  computeBatchPayload,
  toBatchPayload,
} from "./buildBatchDiff";
