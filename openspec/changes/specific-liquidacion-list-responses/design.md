# Design: Specific Liquidacion List Typed Responses

## Technical Approach

The design solves the untyped response issue for specific liquidacion list endpoints by injecting a discriminated `detalle` object strictly into the specific query responses. The general `/liquidaciones/` endpoint contract remains unchanged and unpolluted. The shared domain service builds the internal detail, but the specific presenters control the exposure, ensuring `detalle` is only present in specific endpoint responses (e.g., `LiquidacionM2ListItemOut`). This ensures end-to-end type safety and eliminates unsafe type casts in frontend card components without bloating the general list response.

## Architecture Decisions

### Decision: Protect General Endpoint Contract

**Choice**: Do not add `detalle` to the base `LiquidacionGeneralListItemOut` schema. The `detalle` field will only exist on specific output schemas (e.g., `LiquidacionM2ListItemOut`).
**Alternatives considered**: Adding a polymorphic `detalle` to the base schema used by all endpoints.
**Rationale**: Prevents polluting the general `/liquidaciones/` endpoint with unnecessary data. Strict separation ensures the general endpoint remains lightweight, while specific endpoints return strictly typed details.

### Decision: Explicit Presenter Mapping

**Choice**: The domain DTO (`LiquidacionGeneralListItem`) will hold the `detalle` dictionary internally. Specific presenters (e.g., `MecanicaSuelosListPresenter`) will be created or updated to explicitly map this internal `detalle` into the specific output schema (e.g., `LiquidacionM2ListItemOut`). The general presenter will explicitly ignore the `detalle` field.
**Alternatives considered**: Dynamic dict unpacking in a single generic presenter.
**Rationale**: Explicit presenters guarantee that the presentation layer strictly controls data exposure, fulfilling the requirement that presenters control exposure.

### Decision: Stable English Discriminator Literals

**Choice**: Use exact stable constant-style literals for the discriminator field: `EDIFICACION`, `M2`, `INSPECCION_OBRA` across backend and frontend.
**Alternatives considered**: Using slug-style or lowercase types (e.g., `m2`, `inspeccion-obra`).
**Rationale**: Aligns backend schemas with frontend Zod/TS using robust, constant-style constants, reducing mismatch errors and ensuring standard naming conventions.

### Decision: Missing Calculation-Row Behavior (Alpha-Safe)

**Choice**: If the calculation snapshot row (e.g., `liquidacion_m2` or `liquidacion_visitas`) is missing in the database, the backend will return the `detalle` object with the correct discriminator type, but all data fields set to `null`.
**Alternatives considered**: Raise a 500 error or omit the `detalle` field entirely.
**Rationale**: Minimal alpha-safe behavior. Omitting the field or raising an error would break the frontend list view or specific schemas that strictly require `detalle`. Returning safe null fields degrades gracefully (showing blanks in the UI) without breaking the paginated list or the strict type contract.

## Data Flow

Data flows from the existing prefetched relations in the core list query builder directly into the new internal `detalle` dictionary, which is then explicitly mapped by specific presenters.

    DB (liquidacion_m2 / liquidacion_visitas)
          │ (prefetched)
          ▼
    LiquidacionesGeneralService._listar_liquidaciones_paginado
          │ (constructs internal `detalle` dict based on tipo)
          ▼
    LiquidacionGeneralListItem (Domain DTO)
          │
    Specific Presenter (e.g. MecanicaSuelosListPresenter)
          │ (maps internal detalle to specific schema)
          ▼
    LiquidacionM2ListItemOut (Presentation Schema)
          │
    Frontend (React Query)
          │
    LiquidacionMecanicaSuelosListItem (TypeScript Interface)
          │
    LiquidacionMecanicaSuelosCard (React Component)

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/modules/liquidaciones/domain/schemas.py` | Modify | Define `DetalleM2`, `DetalleIO`, `DetalleEdificacion`. Add internal `detalle` field to `LiquidacionGeneralListItem`. |
| `backend/modules/liquidaciones/domain/services/core/liquidaciones_general_core.py` | Modify | Populate the `detalle` dict in `_listar_liquidaciones_paginado` loop (handling missing rows with safe nulls). |
| `backend/modules/liquidaciones/presentation/schemas/liquidacion_general_schemas.py` | Modify | Define `DetalleM2Out`, `DetalleIOOut`, `DetalleEdificacionOut` with exact literals (`M2`, `INSPECCION_OBRA`, `EDIFICACION`). (Do NOT modify base `LiquidacionGeneralListItemOut`). |
| `backend/modules/liquidaciones/presentation/schemas/mecanica_suelos_schemas.py` | Modify | Add `LiquidacionM2ListItemOut` schema extending general base. |
| `backend/modules/liquidaciones/presentation/schemas/inspeccion_obra_schemas.py` | Modify | Add `LiquidacionIOListItemOut` schema extending general base. |
| `backend/modules/liquidaciones/presentation/presenters/` | Create/Modify | Create/update specific presenters (e.g., `mecanica_suelos_presenter.py`) to map `LiquidacionGeneralListItem` -> `LiquidacionM2ListItemOut`. |
| `backend/modules/liquidaciones/presentation/controllers/*.py` | Modify | Update controllers to use specific presenters and return specific schemas. |
| `frontend/src/features/liquidaciones/types/liquidacion-general.ts` | Modify | Define `LiquidacionDetalle` union (`EDIFICACION`, `M2`, `INSPECCION_OBRA`). |
| `frontend/src/features/liquidaciones/types/*.types.ts` | Modify | Update specific list item interfaces to strictly require `detalle`. |
| `frontend/src/features/liquidaciones/schemas/*.schema.ts` | Modify | Update Zod schemas with `detalle` union and exact literals. |
| `frontend/src/features/liquidaciones/components/*Card.tsx` | Modify | Use `detalle` values instead of placeholders; remove unsafe type casts. |

## Interfaces / Contracts

**Backend Schema Example:**
```python
class DetalleBaseOut(BaseSchema):
    tipo: str

class DetalleM2Out(DetalleBaseOut):
    tipo: Literal["M2"] = "M2"
    area_solicitada: Optional[float]
    area_base_calculo: Optional[float]
    # ... other numeric fields

class LiquidacionM2ListItemOut(LiquidacionGeneralListItemOut):
    # Extends the base schema without polluting it
    detalle: DetalleM2Out
```

**Frontend Type Example:**
```typescript
export interface DetalleM2 {
  tipo: "M2";
  area_solicitada: number | null;
  area_base_calculo: number | null;
  // ... other numeric fields
}

export interface LiquidacionMecanicaSuelosListItem extends Omit<LiquidacionGeneralListItem, 'detalle'> {
  tipo_liquidacion: "mecanica-suelos";
  detalle: DetalleM2;
}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Core paginator `detalle` population | Modify `test_listar_liquidaciones_paginado` to verify `detalle` is built correctly internally. |
| Unit | General endpoint non-regression | Verify that the general `/liquidaciones/` endpoint does **not** leak the `detalle` property. |
| Unit | Endpoint contract tests | Assert specific controllers (e.g., MS) strictly return `detalle` shaped as `DetalleM2Out`. |
| Unit | Empty/null cases (Alpha-safe) | Mock a missing calculation row in DB; assert response returns `detalle` with discriminator but `null` fields. |
| Unit | Frontend Zod/Type checks | Verify Zod schemas parse exact literals (`M2`, `INSPECCION_OBRA`, `EDIFICACION`) and null fields without failing. |
| E2E | Card Rendering | Verify UI renders blanks gracefully when calculation rows are missing and shows numbers correctly otherwise. |

## Migration / Rollout

No migration required. This is an additive presentation layer contract upgrade. Missing data gracefully defaults to `null` fields within the `detalle` object.

## Open Questions

- None
