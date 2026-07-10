# Exploration: Specific Liquidacion List Typed Responses

## Current State

**Problem**: Each specific liquidacion list endpoint (`/liquidaciones/mecanica-suelos`, `/liquidaciones/inspeccion-obra`, `/liquidaciones/habilitacion-urbana`, `/liquidaciones/impacto-vial`, `/liquidaciones/taludes`) returns `LiquidacionGeneralListItemOut` — a flat, type-agnostic shape. Frontend cards (`LiquidacionMecanicaSuelosCard`, `LiquidacionInspeccionObraCard`) cast items to `LiquidacionGeneralListItem` and render placeholder text instead of real type-specific data.

The TODO comments in the frontend are explicit:
- `LiquidacionMecanicaSuelosCard.tsx` line 16: "TODO: Backend list response should include area_solicitada / area_base_calculo fields; when available, display them here instead of the placeholder text."
- `LiquidacionInspeccionObraCard.tsx` line 16: "TODO: Backend list response should include cantidad_visitas and categoria fields"

**Architecture today**:
```
Specific Controller (GET /) 
  → LiquidacionesGeneralOrchestrator.listar_liquidaciones(tipo_liquidacion=FILTER)
    → LiquidacionesGeneralFlujo._proceso_listar_liquidaciones
      → LiquidacionesGeneralService._listar_liquidaciones_paginated
        → LiquidacionGeneralPresenter.present_list  (transforms to LiquidacionGeneralListItemOut)
```

All five specific list endpoints funnel through the same general orchestrator and return the same `LiquidacionGeneralListItemOut` shape.

---

## Affected Areas

### Backend (all in `backend/modules/liquidaciones/`)

| File | Role | Change Needed |
|------|------|--------------|
| `presentation/schemas/liquidacion_general_schemas.py` | Shared base schemas | Extend `LiquidacionGeneralListItemOut` with optional differential fields, OR create type-specific list schemas |
| `domain/schemas.py` | Domain DTO `LiquidacionGeneralListItem` | Add optional `calculo_m2`, `calculo_visitas` nested objects |
| `domain/services/core/liquidaciones_general_core.py` | List query builder | Already prefetches `liquidacion_m2` and `liquidacion_visitas` — data exists. Extend `_listar_liquidaciones_paginado` to include M2/IO snapshot fields in output dict |
| `presentation/presenters/liquidacion_general_presenter.py` | List item presenter | Add `present_list_item_m2(item, m2_calculo)` and `present_list_item_io(item, io_calculo)` variants, OR extend `present_list_item` to conditionally include differential |
| `presentation/controllers/mecanica_suelos_controller.py` | MS list endpoint | Switch from `LiquidacionGeneralListItemOut` to new MS-specific list schema |
| `presentation/controllers/inspeccion_obra_controller.py` | IO list endpoint | Switch to IO-specific list schema |
| `presentation/controllers/habilitacion_urbana_controller.py` | HU list endpoint | Switch to HU-specific list schema |
| `presentation/controllers/impacto_vial_controller.py` | IV list endpoint | Switch to IV-specific list schema |
| `presentation/controllers/taludes_controller.py` | Taludes list endpoint | Switch to Taludes-specific list schema |
| `presentation/schemas/mecanica_suelos_schemas.py` | MS schemas | Add `LiquidacionM2ListItemOut` schema with `calculo_m2` differential |
| `presentation/schemas/inspeccion_obra_schemas.py` | IO schemas | Add `LiquidacionIOListItemOut` schema with `calculo_visitas` differential |
| `presentation/schemas/habilitacion_urbana_schemas.py` | HU schemas | Add HU-specific list schema |
| `presentation/schemas/impacto_vial_schemas.py` | IV schemas | Add IV-specific list schema |
| `presentation/schemas/taludes_schemas.py` | Taludes schemas | Add Taludes-specific list schema (reuse M2 shape) |

**Edificaciones is already correct**: `LiquidacionEdificacionesController.listar_liquidaciones` calls `orchestrator.obtener_liquidacion_por_id` per item to build full `LiquidacionEdificacionOut` — it does NOT go through the general list flow. Edificaciones already returns rich type-specific data in list.

### Frontend (all in `frontend/src/features/liquidaciones/`)

| File | Change Needed |
|------|--------------|
| `types/liquidacion-mecanica-suelos.types.ts` | Add `calculo_m2` snapshot to `LiquidacionMecanicaSuelosListItem` |
| `types/liquidacion-inspeccion-obra.types.ts` | Add `calculo_visitas` snapshot to `LiquidacionInspeccionObraListItem` |
| `types/liquidacion-taludes.types.ts` | Add M2 differential to Taludes list item |
| `types/liquidacion-habilitacion-urbana.types.ts` | Add M2 differential to HU list item |
| `types/liquidacion-impacto-vial.types.ts` | Add M2 differential to IV list item |
| `schemas/liquidacion-mecanica-suelos.schema.ts` | Add `calculo_m2` fields to list item schema |
| `schemas/liquidacion-inspeccion-obra.schema.ts` | Add `calculo_visitas` fields to list item schema |
| `schemas/liquidacion-taludes.schema.ts` | Add M2 fields to Taludes list schema |
| `schemas/liquidacion-habilitacion-urbana.schema.ts` | Add M2 fields to HU list schema |
| `schemas/liquidacion-impacto-vial.schema.ts` | Add M2 fields to IV list schema |
| `hooks/useLiquidacionesMecanicaSuelos.ts` | Update response schema reference if type changes |
| `hooks/useLiquidacionesInspeccionObra.ts` | Update response schema reference if type changes |
| `components/LiquidacionMecanicaSuelosCard.tsx` | Render real `calculo_m2` fields instead of placeholder |
| `components/LiquidacionInspeccionObraCard.tsx` | Render real `calculo_visitas` fields instead of placeholder |
| `components/LiquidacionTaludesCard.tsx` | Render real M2 fields |
| `components/LiquidacionHabilitacionUrbanaCard.tsx` | Render real M2 fields |
| `components/LiquidacionImpactoVialCard.tsx` | Render real M2 fields |

---

## Data Source for Calculation Snapshots

### M2 Types (HU, MS, IV, Taludes)

Data already accessible via `prefetch_related('liquidacion_m2')` in `liquidaciones_general_core.py`:

```python
# In _listar_liquidaciones_paginado (line 233-254):
m2_data = liq.liquidacion_m2.first()
if m2_data and m2_data.tarifa_aplicada:
    t = m2_data.tarifa_aplicada
    # m2_data.area_solicitada      -> float
    # m2_data.area_base_calculo    -> float  
    # m2_data.derecho              -> Decimal
    # t.costo_por_m2               -> Decimal
    # t.tarifa_base.derecho_minimo -> Decimal
    # t.tarifa_base.derecho_maximo -> Decimal or None
```

Model: `LiquidacionPorMetroCuadrado` (calculos_tarifas.py)
Fields: `area_solicitada`, `area_base_calculo`, `derecho`, FK to `TarifaPorMetroCuadrado`
Tarifa fields needed: `costo_por_m2`, `area_m2`, `derecho_minimo`, `derecho_maximo`

### IO Type (InspeccionObra)

Data already accessible via `prefetch_related('liquidacion_visitas')`:

```python
# In _listar_liquidaciones_paginado (line 255-277):
v_data = liq.liquidacion_visitas.first()
if v_data and v_data.tarifa_aplicada:
    t = v_data.tarifa_aplicada
    # v_data.cantidad_visitas        -> int
    # v_data.visitas_base_calculo    -> int
    # v_data.derecho                 -> Decimal
    # v_data.categoria               -> str ("A", "B", "C", etc.)
    # t.costo_por_visita             -> Decimal
    # t.visitas_minimas             -> int
```

Model: `LiquidacionPorCategoriaVisitas` (calculos_tarifas.py)
Fields: `cantidad_visitas`, `visitas_base_calculo`, `derecho`, `categoria`, FK to `TarifaPorCategoriaVisitas`

---

## Proposed Response Contracts

### Common Base Schema (LiquidacionGeneralListItemOut)

Keep all current fields. Add optional differential:

```python
class LiquidacionGeneralListItemOut(BaseSchema):
    # ... all existing fields ...
    
    # NEW: Optional differential objects — populated based on tipo_liquidacion
    edificacion: Optional[EdificacionDifferentialOut] = None   # EDIFICACION
    m2: Optional[M2DifferentialOut] = None                     # HU, MS, IV, TAL
    inspeccion_obra: Optional[IO DifferentialOut] = None       # INSPECCION_OBRA
```

**Alternative approach (cleaner, no nullable on main schema)**:

Create new typed list schemas per type, each with:
- All common fields
- One differential object

### Edificación List Item

```json
{
  "id": "uuid",
  "public_id": "E-2026-00001",
  "estado": "PENDIENTE",
  "tipo_liquidacion": "edificacion",
  "numero_revision": 1,
  "fecha_registro": "2026-07-09T10:00:00Z",
  "tramite_accion": "PRIMERA_REVISION",
  "tipo_tramite": "OBRA_NUEVA",
  "expediente": "EXP-2026-001",
  "observacion": null,
  "proyecto": { ... },
  "entidad": { ... },
  "municipalidad": { ... },
  "valores": { ... },
  "proyectistas": [ ... ],
  "delegados": [ ... ],
  "contactos": [ ... ],
  "revisiones": [ ... ],
  "subtotal": 15000.00,
  "igv": 2700.00,
  "total": 17700.00,
  "total_a_pagar": 17700.00,
  "edificacion": {
    "valor_proyecto": 500000.00,
    "valor_base_calculo": 500000.00,
    "tramite_accion": "PRIMERA_REVISION",
    "tipo_tramite": "OBRA_NUEVA",
    "porcentaje_liquidacion": 0.0015,
    "derecho": 750.00,
    "tarifa": {
      "id": "uuid",
      "derecho_minimo": 500.00,
      "derecho_maximo": 5000.00,
      "porcentaje_minimo_uit": 0.05
    }
  }
}
```

### M2 List Item (HU, MS, IV, Taludes)

```json
{
  "id": "uuid",
  "public_id": "MS-2026-00001",
  "estado": "PENDIENTE",
  "tipo_liquidacion": "mecanica-suelos",
  "numero_revision": 1,
  "fecha_registro": "2026-07-09T10:00:00Z",
  "tramite_accion": "PRIMERA_REVISION",
  "tipo_tramite": null,
  "expediente": "EXP-2026-001",
  "observacion": null,
  "proyecto": { ... },
  "entidad": { ... },
  "municipalidad": { ... },
  "valores": { ... },
  "proyectistas": [ ... ],
  "delegados": [ ... ],
  "contactos": [ ... ],
  "revisiones": [ ... ],
  "subtotal": 500.00,
  "igv": 90.00,
  "total": 590.00,
  "total_a_pagar": 590.00,
  "m2": {
    "area_solicitada": 250.00,
    "area_base_calculo": 250.00,
    "costo_m2": 2.00,
    "derecho": 500.00,
    "derecho_minimo": 200.00,
    "derecho_maximo": 2000.00,
    "tarifa": {
      "id": "uuid",
      "costo_por_m2": 2.00,
      "area_m2": 100.00
    }
  }
}
```

### IO List Item

```json
{
  "id": "uuid",
  "public_id": "IO-2026-00001",
  "estado": "PENDIENTE",
  "tipo_liquidacion": "inspeccion-obra",
  "numero_revision": 1,
  "fecha_registro": "2026-07-09T10:00:00Z",
  "tramite_accion": "PRIMERA_REVISION",
  "tipo_tramite": null,
  "expediente": "EXP-2026-001",
  "observacion": null,
  "proyecto": { ... },
  "entidad": { ... },
  "municipalidad": { ... },
  "valores": { ... },
  "proyectistas": [ ... ],
  "delegados": [ ... ],
  "contactos": [ ... ],
  "revisiones": [ ... ],
  "subtotal": 800.00,
  "igv": 144.00,
  "total": 944.00,
  "total_a_pagar": 944.00,
  "inspeccion_obra": {
    "categoria": "C",
    "cantidad_visitas": 4,
    "visitas_base_calculo": 4,
    "costo_por_visita": 200.00,
    "derecho": 800.00,
    "tarifa": {
      "id": "uuid",
      "costo_por_visita": 200.00,
      "visitas_minimas": 2
    }
  }
}
```

---

## Approaches

### Approach A: Extend LiquidacionGeneralListItemOut with Optional Differential Objects

Add nullable differential objects to the existing shared schema.

- **Pros**: Minimal schema churn; backwards compatible; frontend can read `item.m2?.area_solicitada` safely
- **Cons**: Schema has many nullable fields; not truly typed per type
- **Effort**: Low-Medium

### Approach B: Type-Specific List Schemas (Recommended)

Create new schemas per type: `LiquidacionM2ListItemOut`, `LiquidacionIOListItemOut`. Each contains common fields + one differential object.

- **Pros**: Clean typed contracts; each endpoint returns exactly what it needs; no casting
- **Cons**: More schema duplication initially; requires updating each controller's response type
- **Effort**: Medium

### Approach C: Union Type Response

Return `LiquidacionGeneralListItemOut | LiquidacionM2ListItemOut | LiquidacionIOListItemOut` with discriminated union on `tipo_liquidacion`.

- **Pros**: Maximum flexibility; full type safety with discriminated union
- **Cons**: Complex; requires TS union type handling on frontend
- **Effort**: High

---

## Recommendation

**Approach B** (Type-Specific List Schemas) for alpha implementation:

1. Extend `LiquidacionGeneralListItemOut` with optional differential fields (backwards compat for general endpoint)
2. Create `LiquidacionM2ListItemOut` for HU/MS/IV/Taludes — replaces `LiquidacionGeneralListItemOut` in those specific controllers
3. Create `LiquidacionIOListItemOut` for IO
4. Edificaciones keeps using full `LiquidacionEdificacionOut` via detail-per-item pattern (already works)

This approach:
- Doesn't break existing general list endpoint (`/liquidaciones`)
- Fixes specific endpoints cleanly
- Frontend cards get typed fields without casting
- No DB migration needed — data already in prefetch

---

## Risks

1. **Breaking frontend**: Any frontend code that assumes `LiquidacionMecanicaSuelosListItem === LiquidacionGeneralListItem` will break (currently does `as unknown as LiquidacionGeneralListItem`). Must update types and remove unsafe casts.

2. **Query performance**: Adding M2/IO snapshot fields to the list query adds marginal cost but already prefetched — acceptable.

3. **Schema proliferation**: Each type gets its own list schema with duplicated common fields. Mitigation: share common sub-schemas.

4. **Edificaciones list is deprecated**: `LiquidacionesEdificacionesView` uses `LiquidacionGeneralCard` with cast — but the underlying data flow is already detail-per-item. Consider unifying Edificaciones to use the same pattern as other types.

5. **HU, IV, Taludes cards**: These don't have dedicated card components yet — they reuse `LiquidacionGeneralCard` directly. They will need the same treatment as MS and IO once cards are created.

---

## Minimal Alpha Implementation Plan

**Backend changes**:
1. Add `calculo_m2` and `calculo_visitas` snapshot fields to `LiquidacionGeneralListItem` DTO in `domain/schemas.py`
2. Populate these in `liquidaciones_general_core.py`'s `_listar_liquidaciones_paginado`
3. Add optional differential to `LiquidacionGeneralListItemOut` in `presentation/schemas/liquidacion_general_schemas.py`
4. Add new schemas `LiquidacionM2ListItemOut` and `LiquidacionIOListItemOut` in their respective schema files

**Frontend changes**:
1. Update `LiquidacionMecanicaSuelosListItem` type with `calculo_m2` fields
2. Update `LiquidacionInspeccionObraListItem` type with `calculo_visitas` fields  
3. Update Zod schemas
4. Update `LiquidacionMecanicaSuelosCard` to render real fields
5. Update `LiquidacionInspeccionObraCard` to render real fields
6. Remove unsafe `as unknown as LiquidacionGeneralListItem` casts in card wrappers

**Beta cleanup** (separate change):
- HU, IV, Taludes cards (currently use base card directly)
- Schema deduplication via shared base sub-schemas
- `LiquidacionGeneralCard` `typeSpecificSummary` and `typeSpecificValues` slots become unnecessary once all types render their own differential

---

## Verification Plan

### Backend
1. **pytest**: Add or extend existing tests for `_listar_liquidaciones_paginado` to assert M2/IO snapshot fields are populated
2. **Manual API test**: `GET /liquidaciones/mecanica-suelos?page=1&page_size=10` returns `area_solicitada`, `costo_m2`, `derecho` in each item
3. **Manual API test**: `GET /liquidaciones/inspeccion-obra?page=1&page_size=10` returns `cantidad_visitas`, `categoria`, `costo_por_visita` in each item

### Frontend
1. **TypeScript typecheck**: `npx tsc --noEmit` passes with no casting errors
2. **Build**: `next build` succeeds
3. **Visual verification**: MS list shows "250 m²" not "Cálculo por área"; IO list shows "C3 · 4 visitas" not "Cálculo por visitas"

---

## Ready for Proposal

**Yes** — the exploration is complete. The scope is clear: extend the list response contracts with typed differential objects for M2 and IO types, backed by data already available in prefetched relations, then update frontend cards to render real values.

Orchestrator should proceed to `sdd-propose` for change `specific-liquidacion-list-responses`.
