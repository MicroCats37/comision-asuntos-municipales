# Exploration: Reuse Liquidaciones Municipalidad Selector for Finanzas Filters

## Current State

### 1. Liquidaciones Municipality Selection Pattern

**Hook** (`frontend/src/features/liquidaciones/hooks/useMunicipalidades.ts`):
- Calls `GET /entidades/municipalidades?v=2` via `useApiQuery`
- Returns `MunicipalidadData[]` with shape: `{ id, nombre, codigo, provincia: {id,nombre}, distrito: {id,nombre} }`
- 1-minute cache, supports both flat array and `{ items: [...] }` envelope

**UI Component** (`frontend/src/components/ui/searchable-select.tsx`):
- `SearchableSelect`: fully featured searchable dropdown
- Keyboard navigation (Arrow Up/Down, Enter, Escape)
- `useDeferredValue` for debounced search (avoids freeze on typing)
- Popover with sticky search input, max 240px scroll
- Shows selected label, clear button (X), loading/disabled states

**Form Integration** (`frontend/src/features/liquidaciones/components/forms/LiquidacionFormBodyBase.tsx` — `MunicipalidadField`):
- Wraps `SearchableSelect` via `GenericInput` (`type: "searchable-select"`)
- Option label: `codigo ? "${codigo} - ${nombre}" : nombre` — shows code + name
- Value: municipalidad UUID string
- Also used in `LiquidacionFiltroModal` and `DelegadosFiltroModal` (liquidaciones feature)

### 2. Backend API Source

- **Endpoint**: `GET /entidades/municipalidades` — `EntidadesController.obtener_municipalidades()` at `backend/modules/entidades/presentation/controllers/entidad_controller.py:125`
- **Presenter**: `EntidadPresenter.present_municipalidades()` → `MunicipalidadesResponseOut`
- **Orchestrator**: `EntidadesOrchestrator.obtener_municipalidades()` — no filters, returns all
- **No search/pagination** — returns full list (potential issue for scale)
- **Schema** (`MunicipalidadesResponseOut`): `id: UUID`, `nombre: str`, `codigo: str | None`, `provincia: {...} | None`, `distrito: {...} | None`

### 3. Finanzas Filter Modals — Current State

**`RecibosDelegadosFiltroModal.tsx`** (line 107–118):
```tsx
// Raw Input — no selector, asks for UUID
<Input
  id="recibos-delegado-filter-municipalidad"
  placeholder="UUID de la municipalidad"
  {...methods.register("municipalidad_id")}
/>
```

**`RHDetalleDelegadosFiltroModal.tsx`** (line 135–145):
```tsx
// Same raw Input pattern
<Input
  id="rh-delegado-detalle-filter-municipalidad"
  placeholder="UUID de la municipalidad"
  {...methods.register("municipalidad_id")}
/>
```

**Active filter display** (both views) shows raw UUID:
```tsx
<span>Municipalidad ID: {filtros.municipalidad_id}</span>
```

**Backend** already accepts `municipalidad_id` as UUID query param in `RHDelegadoMensualController` and `RHDelegadoDetalleController` — no backend changes needed.

### 4. Other Inspector Filter Modals

- `RecibosInspectoresFiltroModal` and `RHDetalleInspectoresFiltroModal` use `inspector_id` (different field, not municipalidad) — not in scope.

---

## Approaches

| Approach | Description | Pros | Cons | Effort |
|---------|-------------|------|------|--------|
| **A — Direct component swap** | Replace `Input` with `SearchableSelect` + `useMunicipalidades` in both Finanzas filter modals. Display name in active filters badge. | Simple, no new files, direct reuse | Modals import from liquidaciones schema/hook (cross-feature import) | Low |
| **B — Extract shared `MunicipalidadSelect` component** | Create a shared `MunicipalidadSelect` component in `frontend/src/components/` that encapsulates `useMunicipalidades` + `SearchableSelect`. Both Finanzas modals and Liquidaciones use it. | Proper separation, single source of truth for the pattern | New file, more work | Medium |
| **C — Thin Finanzas wrapper only** | Keep `useMunicipalidades` in liquidaciones (it's already generic), add `MunicipalidadSelect` in Finanzas components only. No shared component. | Minimal work, isolated to Finanzas | Duplicates the pattern setup in two places | Low-Medium |

**Recommendation: Approach A** — Direct swap with cross-feature import is acceptable here since:
- The `useMunicipalidades` hook and `MunicipalidadSchema` are already schema-only, no business logic coupling
- The `SearchableSelect` is a generic UI component
- The scope is small and contained

---

## Contract Alignment

| Contract | Status |
|----------|--------|
| **Filters submit `municipalidad_id` UUID** | ✅ Already the case — `municipalidad_id: z.string()` in Finanzas hooks passes UUID to API |
| **UI shows user-friendly name, not UUID** | ❌ Currently shows raw UUID in `Input` placeholder and active filter badge |
| **URL filter remains `municipalidad_id`** | ✅ Already aligned — no URL param changes needed |
| **API wrapper/presenter pattern** | ✅ Backend already returns `MunicipalidadSchema` with `id`, `nombre`, `codigo` — no backend changes |

---

## Test Plan

| Layer | Expectation |
|-------|-------------|
| **Frontend component** | No existing tests for filter modals. Manual verification: select municipalidad, verify label appears (not UUID), verify URL param is set, verify clear works. |
| **Biome / TypeScript** | No type errors expected — `municipalidad_id` remains `string` throughout |
| **Backend** | No changes. Existing tests for Finanzas endpoints should not break. |
| **E2E / Integration** | If `liquidaciones` tests cover the `useMunicipalidades` hook, no new tests needed for Finanzas reuse. |

---

## Risks and Edge Cases

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Large municipalidad list** — endpoint returns ALL without server-side filter/search | Medium | Current production list is small; if scale becomes an issue, add `?search=` param to endpoint |
| **Stale selected label when URL has `municipalidad_id` but data not yet loaded** | Low-Medium | `isLoading` from `useMunicipalidades` → show "Cargando..." placeholder; `SearchableSelect` already handles `disabled` during load |
| **Loading state in filter modal** | Low | Pass `isLoading` to `SearchableSelect` (already supports `disabled` prop) |
| **Clearing filter** | Low | `SearchableSelect` already has clear (X) button; pass `null` to `onValueChange` |
| **Display name in active filter badge** | Low | The badge needs a lookup from `useMunicipalidades` data to resolve name from ID. Need to store `municipalidades` state in the view or pass name through the filter object |

---

## Affected Files (for Apply Phase)

### Frontend — must change:
- `frontend/src/features/finanzas/components/filtros/RecibosDelegadosFiltroModal.tsx` — replace `Input` with `SearchableSelect`
- `frontend/src/features/finanzas/components/filtros/RHDetalleDelegadosFiltroModal.tsx` — same
- `frontend/src/features/finanzas/views/RecibosDelegadosView.tsx` — update active filter badge to show name instead of UUID
- `frontend/src/features/finanzas/views/RHDetalleDelegadosView.tsx` (if exists) — same for RH Detalle

### Frontend — must import:
- `useMunicipalidades` from `frontend/src/features/liquidaciones/hooks/useMunicipalidades.ts`
- `SearchableSelect` from `frontend/src/components/ui/searchable-select.tsx`
- `MunicipalidadSchema` (if needed for type) from `frontend/src/features/liquidaciones/schemas/municipalidad.schema.ts`

### Backend — no changes needed

### Test — no new tests needed (manual verification sufficient)

---

## Recommended Next Phase

**`sdd-propose`**: Define the scope for replacing raw UUID inputs with `SearchableSelect` in both Finanzas filter modals, plus updating the active filter badge display in both views.

The change is low-complexity: 2 modals + 2 views, cross-feature import of liquidaciones hook, no backend changes, no schema changes.
