# Tasks: Specific Liquidacion List Typed Responses

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~300 lines |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Not needed |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: stacked-to-main
400-line budget risk: Medium

## Phase 1: Domain & Presentation Models (Backend)

- [x] 1.1 `backend/modules/liquidaciones/domain/schemas.py`: Define `DetalleM2`, `DetalleIO`, `DetalleEdificacion`. Add internal `detalle` to `LiquidacionGeneralListItem`.
- [x] 1.2 `backend/modules/liquidaciones/presentation/schemas/liquidacion_general_schemas.py`: Define `DetalleM2Out`, `DetalleIOOut`, `DetalleEdificacionOut` with literals (`M2`, `INSPECCION_OBRA`, `EDIFICACION`). Do not add `detalle` to `LiquidacionGeneralListItemOut`.
- [x] 1.3 `backend/modules/liquidaciones/presentation/schemas/mecanica_suelos_schemas.py`: Add `LiquidacionM2ListItemOut` extending general base with `detalle: DetalleM2Out`.
- [x] 1.4 `backend/modules/liquidaciones/presentation/schemas/inspeccion_obra_schemas.py`: Add `LiquidacionIOListItemOut` extending general base with `detalle: DetalleIOOut`.

## Phase 2: Core Service Logic (Backend)

- [x] 2.1 `backend/modules/liquidaciones/domain/services/core/liquidaciones_general_core.py`: Update `_listar_liquidaciones_paginado` to populate internal `detalle` dict. Ensure missing calculation rows result in `detalle` with `tipo` but `null` for numeric fields.

## Phase 3: Presenters & Controllers (Backend)

- [x] 3.1 `backend/modules/liquidaciones/presentation/presenters/mecanica_suelos_presenter.py`: Create/modify presenter to map `LiquidacionGeneralListItem` to `LiquidacionM2ListItemOut` exposing `detalle`.
- [x] 3.2 `backend/modules/liquidaciones/presentation/presenters/inspeccion_obra_presenter.py`: Create/modify presenter to map `LiquidacionGeneralListItem` to `LiquidacionIOListItemOut` exposing `detalle`.
- [x] 3.3 `backend/modules/liquidaciones/presentation/controllers/*`: Update specific controllers to use specific presenters and return specific schemas (e.g., `mecanica-suelos`, `inspeccion-obra`).

## Phase 4: Frontend Types & Schemas

- [x] 4.1 `frontend/src/features/liquidaciones/types/liquidacion-general.ts`: Define `LiquidacionDetalle` union type with `EDIFICACION`, `M2`, `INSPECCION_OBRA` literals.
- [x] 4.2 `frontend/src/features/liquidaciones/types/*.types.ts`: Update specific list item interfaces to strictly require `detalle`.
- [x] 4.3 `frontend/src/features/liquidaciones/schemas/*.schema.ts`: Update Zod schemas with `detalle` union and exact literals.

## Phase 5: Frontend UI

- [x] 5.1 `frontend/src/features/liquidaciones/components/*Card.tsx`: Update UI to read `detalle` values instead of placeholders, rendering gracefully for `null` fields. Remove unsafe type casts.

## Phase 6: Testing

- [x] 6.1 Backend unit tests: Verify `detalle` population and safe null handling in paginator.
- [x] 6.2 Backend contract tests: Verify general endpoint does not leak `detalle` and specific endpoints strictly return it.
- [ ] 6.3 Frontend schema tests: Verify Zod parsing for `M2`, `INSPECCION_OBRA`, `EDIFICACION` and `null` fallbacks. (No frontend test harness exists - documented in apply-progress)
