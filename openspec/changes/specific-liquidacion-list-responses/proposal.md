# Proposal: Specific Liquidacion List Typed Responses

## Intent

The specific liquidacion list endpoints (e.g., `/liquidaciones/mecanica-suelos`, `/liquidaciones/inspeccion-obra`) currently return a flat, type-agnostic `LiquidacionGeneralListItemOut` shape. The frontend is forced to cast these items and render placeholder text instead of real type-specific data (like `area_solicitada` for M2 or `cantidad_visitas` for IO). This change will extend the response contracts with a single, typed `detalle` object discriminated by `tipo`, providing the exact data needed without polluting the general endpoint with optional variant properties.

## Scope

### In Scope
- Add a single `detalle` object to the core backend DTO (`LiquidacionGeneralListItem`) to hold type-specific calculation data.
- The `detalle` object will be discriminated by `tipo` (or equivalent) and can be one of: `EdificacionDetalle`, `M2Detalle`, or `InspeccionObraDetalle`.
- Populate this `detalle` object in the general liquidacion core list query builder.
- Create typed specific list response schemas (e.g., `LiquidacionM2ListItemOut`, `LiquidacionIOListItemOut`) for MS, IO, HU, IV, and Taludes controllers, typed to their specific `detalle` variant.
- Update frontend TypeScript types and Zod schemas for Mecanica Suelos and Inspeccion Obra to use the discriminated `detalle` object.
- Update `LiquidacionMecanicaSuelosCard` and `LiquidacionInspeccionObraCard` to render real calculation values from the `detalle` object instead of placeholders.
- Remove unsafe type casts in frontend MS and IO card wrappers.

### Out of Scope
- Modifying the Edificaciones list endpoint (already works via a detail-per-item pattern).
- Creating new dedicated card components for HU, IV, and Taludes (they will continue to use the base `LiquidacionGeneralCard` for now; fixing them is deferred to a future beta cleanup).
- Complex schema deduplication (extracting fully shared sub-schemas) beyond the immediate need of fixing the contracts.

## Capabilities

### New Capabilities
- `typed-liquidacion-lists`: Returns type-specific differential fields encapsulated in a discriminated `detalle` object in the specific liquidacion list endpoints.
- `typed-liquidacion-cards`: Frontend cards for Mecanica Suelos and Inspeccion Obra rendering real differential values from the `detalle` object directly from the API response without type-casting workarounds.

### Modified Capabilities
- None

## Approach

We will use the **Discriminated Detalle Object** approach.
1. The backend `liquidaciones_general_core.py` already prefetches the needed relationships. We will expose these inside a single `detalle` dictionary on the `LiquidacionGeneralListItem` DTO.
2. The `detalle` object will use a discriminator (like `tipo`) to differentiate between `M2Detalle` and `InspeccionObraDetalle`.
3. The general/base schema will NOT be hardcoded with optional concrete variant properties (no `edificacion?: ...`, `calculo_m2?: ...`).
4. In `presentation/schemas`, we will create specific output schemas like `LiquidacionM2ListItemOut` and `LiquidacionIOListItemOut` where `detalle` is strictly typed.
5. The specific controllers will return these typed schemas instead of the general schema.
6. On the frontend, we will update the types for MS and IO list items to match the backend and consume the `detalle` fields in the React cards.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/modules/liquidaciones/domain/schemas.py` | Modified | Add a single discriminated `detalle` object to `LiquidacionGeneralListItem` |
| `backend/modules/liquidaciones/domain/services/core/liquidaciones_general_core.py` | Modified | Populate `detalle` in `_listar_liquidaciones_paginado` |
| `backend/modules/liquidaciones/presentation/schemas/*` | Modified | Add `LiquidacionM2ListItemOut` and `LiquidacionIOListItemOut` schemas |
| `backend/modules/liquidaciones/presentation/controllers/*` | Modified | Update MS, IO, HU, IV, Taludes endpoints to use specific schemas |
| `frontend/src/features/liquidaciones/types/*` | Modified | Update TypeScript interfaces for MS and IO list items to use `detalle` |
| `frontend/src/features/liquidaciones/schemas/*` | Modified | Update Zod schemas |
| `frontend/src/features/liquidaciones/components/*` | Modified | Update MS and IO card components |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Breaking frontend list views due to schema mismatch | High | Update frontend TS types/Zod concurrently with backend schemas; rely on `tsc --noEmit`. |
| Query performance degradation | Low | The relations are already prefetched by the current query builder. |

## Rollback Plan

Revert the PR containing these schema and frontend changes. The database itself requires no migrations since the fields are generated from existing prefetched relations.

## Dependencies

- None

## Success Criteria

- [ ] `GET /liquidaciones/mecanica-suelos` returns an item containing a `detalle` block for M2 data.
- [ ] `GET /liquidaciones/inspeccion-obra` returns an item containing a `detalle` block for Inspeccion Obra data.
- [ ] `LiquidacionMecanicaSuelosCard` and `LiquidacionInspeccionObraCard` render real values from the `detalle` object instead of "TODO" placeholders.
- [ ] Frontend compiles cleanly (`npx tsc --noEmit` passes) without unsafe casts in specific cards.