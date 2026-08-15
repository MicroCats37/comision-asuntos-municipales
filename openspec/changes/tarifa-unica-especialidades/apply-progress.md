# SDD Apply Progress — tarifa-unica-especialidades

## FASE 1-3: Modelo + Migration + Domain + Core

**Change**: tarifa-unica-especialidades  
**Status**: phase_1_3_complete  
**Date**: 2026-08-14

---

## FASE 1 — Modelo + Migration

### Tarea 1.1: Remove `especialidad` FK from `TarifaPorcentajeObra` ✅

**File**: `backend/modules/liquidaciones/domain/models/liquidacion/liquidacion_tipo/tarifas_reglas.py`

**Change**: Removed the `especialidad = models.ForeignKey(EspecialidadRevision, ...)` field from `TarifaPorcentajeObra` (lines 149-155).

**Retained**: `tarifa_base`, `porcentaje_liquidacion`, `history`, Meta, `__str__`.

**Side effect**: `tarifas_admin.py` `TarifaPorcentajeObraAdmin` referenced `especialidad` in `list_display`, `search_fields`, `list_filter` — fixed those references to unblock `makemigrations`. This is a direct consequence of the model field removal (not a separate admin refactor).

---

### Tarea 1.2: Migration — Remove `especialidad` column + consolidate data ✅

**File**: `backend/modules/liquidaciones/migrations/0020_remove_tarifaporcentajeobra_especialidad.py`

**Migration name**: `0020_remove_tarifaporcentajeobra_especialidad`

**Operations**:
1. `RunPython` — `consolidate_tarifa_porcentaje_obra`: Groups existing `TarifaPorcentajeObra` by `tarifa_base`, keeps 1 record (highest `porcentaje_liquidacion`), deletes duplicates.
2. `RemoveField` — removes `especialidad` from `historicaltarifaporcentajeobra`
3. `RemoveField` — removes `especialidad` from `tarifaporcentajeobra`

**Consolidation logic**: For each `tarifa_base`, keep record with highest `porcentaje_liquidacion`, delete others. User confirmed old values will be ~0.05.

**Current data**: 5 records, 3 sharing the same `tarifa_base` (will be consolidated to 1).

---

## FASE 2 — Domain DTOs

### Tarea 2.1: `TarifaPorcentajeObraAplicada` + `LiquidacionPorcentajeObraData` ✅

**File**: `backend/modules/liquidaciones/domain/schemas/liquidacion_tipo/liquidacion_porcentaje_data.py`

**Change**: Updated docstring to clarify `especialidad_id`/`especialidad_nombre` are passed explicitly from input/DTO, NOT from `tarifa.especialidad` (FK removed). Schema fields unchanged — already correct.

---

### Tarea 2.2: `TarifaPorcentajeObraDetalleResult` ✅

**File**: `backend/modules/liquidaciones/domain/results/tarifas_historicas_results.py`

**Change**: Updated docstring to clarify `especialidad_id`/`especialidad_nombre` come from `LiquidacionEspecialidadDisponibles` at liquidacion creation time, NOT from `TarifaPorcentajeObra.especialidad`. Fields unchanged — already have explicit names.

---

## FASE 3 — Core Service

### Tarea 3.1: `liquidacion_porcentaje_obra_core_service.py` ✅

**File**: `backend/modules/liquidaciones/domain/services/core/liquidacion_tipo/liquidacion_porcentaje_obra_core_service.py`

**Changes**:

1. **`resolver_tarifas`**: Removed `select_related("especialidad")` from both auto-fill and explicit query branches. Returns `List[TarifaPorcentajeObra]` ORM objects for caller validation. Docstring notes caller must build `TarifaPorcentajeObraAplicada` DTOs with explicit especialidad.

2. **`get_tarifas_porcentaje_vigentes`**: Removed `select_related("especialidad")`.

3. **`calcular_cotizacion_po`**: **SIGNATURE CHANGE** — `tarifas: List[TarifaPorcentajeObraAplicada]` (DTOs) instead of `List[TarifaPorcentajeObra]` (ORM objects). The DTO carries explicit `especialidad_id`/`especialidad_nombre` from input. Loop uses `tarifa_dto` directly; `tarifa_aplicada=tarifa_dto` (already built). Formula unchanged — `porcentaje_total = SUM(t.porcentaje_liquidacion for t in tarifas)` still works with 3 identical DTOs.

4. **`create_liquidacion_porcentaje_obra`**: Changed `especialidad=tarifa.especialidad` → `especialidad_id=detalle.tarifa_aplicada.especialidad_id`. Uses explicit ID from DTO instead of FK traversal.

**Verified**: Cotización with 3 DTOs (same tariff, different specialties) → `porcentaje_total=0.0015` (3×0.0005) ✓, 3 details ✓.

---

### Tarea 3.2: `tarifas_historicas_core_service.py` ✅

**File**: `backend/modules/liquidaciones/domain/services/core/liquidacion_tipo/tarifas_historicas_core_service.py`

**Change**: `get_tarifas_porcentaje_obra_por_base`: Removed `select_related("especialidad")`. Changed `order_by("especialidad__nombre")` → `order_by("porcentaje_liquidacion")`. Docstring notes caller/presenter fills especialidad from `LiquidacionEspecialidadDisponibles`.

---

## Pending: Separate Migration Issue

**Issue**: `makemigrations --check` still shows pending changes for:
- `LiquidacionEspecialidadDisponibles`: `periodo_inicio`/`periodo_fin` (from user's manual `VigenciaModel` inheritance — no migration generated)
- `LiquidacionDelegado`: `especialidad_revision` field (user said it was migrated but no migration found)

**Status**: These are separate from `TarifaPorcentajeObra` change. User said NOT to touch these models in these phases. A separate migration will be needed (or user confirms their manual DB changes are applied).

---

## Validation

- `manage.py check`: ✅ No issues
- `migrate --plan`: Shows `0020` as next migration ✅
- Import test: ✅ All modules load
- Cotización formula test: ✅ 3 DTOs → 0.0015 total, 3 details, correct totals

---

## Next Steps (FASE 4-7)

- **FASE 4**: Orchestrators — update `crear_primera_revision_proceso`, `cotizar_proceso`, `crear_nueva_revision_proceso` to build `TarifaPorcentajeObraAplicada` DTOs with explicit especialidad before calling `calcular_cotizacion_po`
- **FASE 5**: Flows — deduplicate tariff IDs when rebuilding ORM
- **FASE 6**: Presentation schemas — update `LiquidacionPorcentajeObraTarifaIn` (confirm input format with user)
- **FASE 7**: Presenters — `present_tarifas_vigkeiten` no longer uses `t.especialidad.nombre`

---

## FASE 4-7: Orchestrators + Flujos + Schemas + Presenters ✅

**Status**: phase_4_7_complete  
**Date**: 2026-08-14

---

### FASE 4 — Orchestrators

#### Tarea 4.1: Edificaciones Orchestrator ✅

**Files**:
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_especifico/liquidacion_edificaciones_orchestrator.py`

**Changes**:
1. **`_validar_tarifa_explicita`**: Unchanged — validates by vigencia, no especialidad check needed
2. **`_obtener_especialidades_vigentes_para_tipo`** (NEW): Fetches `LiquidacionEspecialidadDisponibles` vigentes for a tipo_liquidacion
3. **`crear_primera_revision_proceso`**: 
   - Deduplicate tariff IDs with `dict.fromkeys()` before ORM query
   - Build `tarifa_map` for quick lookup
   - Build `TarifaPorcentajeObraAplicada` DTOs using `especialidad_id` from INPUT (not from ORM)
   - `especialidad_nombre=None` since core doesn't need it
4. **`cotizar_proceso`**: Same pattern — pass DTOs to `calcular_cotizacion_po` (not ORM objects)
5. **`crear_nueva_revision_proceso`**: Same pattern as `crear_primera_revision_proceso`
6. **`obtener_tarifas_vigentes_proceso`**: Returns tuple `(tarifas, especialidades_disponibles)` — presenter needs both

#### Tarea 4.2: Taludes Orchestrator ✅

**Files**:
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_especifico/liquidacion_taludes_orchestrator.py`

**Same changes as Edificaciones**:
- `_obtener_especialidades_vigentes_para_tipo` (NEW)
- `crear_primera_revision_proceso`: DTOs with explicit especialidad from input
- `cotizar_proceso`: Pass DTOs, include `especialidad_id` in result details
- `obtener_tarifas_vigentes_proceso`: Returns tuple

#### Tarea 4.3: Impacto Vial Orchestrator ✅

**Files**:
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_especifico/liquidacion_impacto_vial_orchestrator.py`

**Same changes as Edificaciones**.

---

### FASE 5 — Flujos

#### Tarea 5.1: Edificaciones Flujo ✅

**Files**:
- `backend/modules/liquidaciones/domain/services/flujos/liquidacion_especifico/liquidacion_edificaciones_flujo.py`

**Changes**:
- `_ejecutar_primera_revision_sync`: Removed ORM reconstruction (`TarifaPorcentajeObra.objects.get()`). Pass `po_data.tarifas` (DTOs) directly to `calcular_cotizacion_po`.
- `_ejecutar_nueva_revision_sync`: Same — pass DTOs directly

#### Tarea 5.2: Taludes Flujo ✅

**Files**:
- `backend/modules/liquidaciones/domain/services/flujos/liquidacion_especifico/liquidacion_taludes_flujo.py`

**Changes**: Same as Edificaciones — pass DTOs directly to `calcular_cotizacion_po`

#### Tarea 5.3: Impacto Vial Flujo ✅

**Files**:
- `backend/modules/liquidaciones/domain/services/flujos/liquidacion_especifico/liquidacion_impacto_vial_flujo.py`

**Changes**: Same as Edificaciones — pass DTOs directly to `calcular_cotizacion_po`

---

### FASE 6 — Presentation Schemas

#### Tarea 6.1: `LiquidacionPorcentajeObraTarifaIn` ✅

**File**: `backend/modules/liquidaciones/presentation/schemas/liquidacion_tipo/porcentaje_schemas.py`

**Change**: Added `especialidad_id: uuid.UUID` field alongside `tarifa_porcentaje_obra_id`.

```python
class LiquidacionPorcentajeObraTarifaIn(BaseSchema):
    """Tarifa seleccionada por el usuario con especialidad explícita."""
    tarifa_porcentaje_obra_id: uuid.UUID
    especialidad_id: uuid.UUID
```

#### Tarea 6.2: Cotizar Output Schemas ✅

**Files**:
- `backend/modules/liquidaciones/presentation/schemas/liquidacion_especifico/liquidacion_edificaciones_schemas.py`
- `backend/modules/liquidaciones/presentation/schemas/liquidacion_especifico/liquidacion_taludes_schemas.py`
- `backend/modules/liquidaciones/presentation/schemas/liquidacion_especifico/liquidacion_impacto_vial_schemas.py`

**Change**: Added `especialidad_id: uuid.UUID` to `LiquidacionEdificacionesCotizarDetalleOut`, `LiquidacionTaludesCotizarDetalleOut`, `LiquidacionImpactoVialCotizarDetalleOut`.

---

### FASE 7 — Presenters

#### Tarea 7.1: `present_tarifas_vigentes` in 3 presenters ✅

**Files**:
- `backend/modules/liquidaciones/presentation/presenters/liquidacion_especifico/liquidacion_edificaciones_presenter.py`
- `backend/modules/liquidaciones/presentation/presenters/liquidacion_especifico/liquidacion_taludes_presenter.py`
- `backend/modules/liquidaciones/presentation/presenters/liquidacion_especifico/liquidacion_impacto_vial_presenter.py`

**OLD Response Contract**:
```json
{ "tarifas": [{ "id": uuid, "especialidad": "...", "porcentaje_liquidacion": 0.0005 }] }
```

**NEW Response Contract**:
```json
{
  "tarifas": [{ "id": uuid, "porcentaje_liquidacion": 0.0005 }],
  "especialidades_disponibles": [{ "id": uuid, "codigo": "...", "nombre": "..." }]
}
```

**Change**: `present_tarifas_vigkeiten(tarifas, especialidades_disponibles)` now takes two args. Tarifa no longer has `especialidad` — single tariff applies to all specialties.

#### Tarea 7.2: `present_cotizacion` in 3 presenters ✅

**Files**: Same 3 presenters

**Change**: `present_cotizacion` now maps `d.especialidad_id` from `CotizacionPorcentajeObraDetalleResult` to the output schema's `LiquidacionXxxCotizarDetalleOut`.

#### Tarea 7.3: `tarifas_historicas_orchestrator.py` ✅

**File**: `backend/modules/liquidaciones/domain/services/orchestrators/tarifas_historicas_orchestrator.py`

**Change**: `obtener_tarifas_historicas_proceso` — For `TIPO_LIQUIDACION_PORCENTAJE` types, the grouping now expands each `TarifaPorcentajeObra` into multiple detail results (one per `LiquidacionEspecialidadDisponibles`). Previously: 1 tariff × 1 especialidad. Now: 1 tariff × N especialidades.

---

### Domain Result Change

**File**: `backend/modules/liquidaciones/domain/results/liquidacion_tipo/cotizacion.py`

**Change**: `CotizacionPorcentajeObraDetalleResult` now includes `especialidad_id: str` field (added alongside existing fields).

---

## Validation

- `manage.py check`: ✅ No issues

## Risks

1. **Frontend compatibility**: `useCrearEdificaciones.ts` and similar hooks send `tarifas: [{tarifa_porcentaje_obra_id: id}]` WITHOUT `especialidad_id`. The new schema REQUIRES `especialidad_id`. Frontend update needed separately (not in scope per user instructions).

2. **Response contract change**: `present_tarifas_vigentes` now returns `especialidades_disponibles` array alongside `tarifas`. Frontend components consuming this endpoint will receive new shape — update needed.

## Next Steps (FASE 8-10)

- **FASE 8-10**: Tests, admin, seeds updates (per user instructions: not in scope for this batch)

---

## Decisions Made

1. **`calcular_cotizacion_po` signature**: Changed from ORM objects to DTOs. Caller (orchestrator) now responsible for building `TarifaPorcentajeObraAplicada` with explicit especialidad from input.

2. **Data consolidation strategy**: Keep record with highest `porcentaje_liquidacion` per `tarifa_base`, delete others.

3. **Admin fix**: Fixed `TarifaPorcentajeObraAdmin` references to removed `especialidad` field as a necessary consequence of the model change.
