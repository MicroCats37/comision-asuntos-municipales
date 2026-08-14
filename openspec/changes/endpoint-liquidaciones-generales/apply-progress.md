# SDD Apply Progress — Endpoint Liquidaciones Generales

## Status
**Change**: endpoint-liquidaciones-generales
**Mode**: Standard
**Phase**: apply (batch 2 — validation fixes)

## Fixes Applied (Batch 2)

### Finding 1: CRITICAL — N+1 Prefetch Over-fetching
**File**: `backend/modules/liquidaciones/domain/services/core/liquidacion_general/liquidacion_general_core_service.py`
**Line**: 763-875 (method `list_liquidaciones_generales_paginated`)
**Problem**: Always prefetched all 6 relations regardless of `tipo` filter → 6 extra queries per result.
**Fix**: Conditional prefetch based on `tipo` parameter:
- When `tipo=EDIFICACION` → prefetch only edificaciones chain
- When `tipo=HABILITACION_URBANA` → prefetch only habilitacion_urbana chain
- When `tipo=MECANICA_SUELOS` → prefetch only mecanica_suelos chain
- When `tipo=TALUDES` → prefetch only taludes chain
- When `tipo=INSPECCION_OBRA` → prefetch only inspeccion_obra chain
- When `tipo=IMPACTO_VIAL` → prefetch only impacto_vial chain
- When `tipo=None` (general listing) → prefetch all 6 (acceptable price)

### Finding 2: WARNING — auth=None Inconsistency
**File**: `backend/modules/liquidaciones/presentation/controllers/liquidacion_general_controller.py`
**Line**: 39-42 (route decorator)
**Problem**: Route had `auth=None` but specific controllers' `list_liquidaciones` routes don't have it (they rely on controller-level `permissions=[AllowAny]`).
**Fix**: Removed `auth=None` from route decorator to match pattern in `liquidacion_edificaciones_controller.py` and other specific controllers.

### Finding 3: WARNING — Presenter None Guard
**File**: `backend/modules/liquidaciones/presentation/presenters/liquidacion_general/liquidacion_general_presenter.py`
**Line**: 76-87 (entidad output building)
**Problem**: Accessed `proyecto.entidad.tipo_documento` directly without proper None guard → potential AttributeError if `proyecto.entidad` is None.
**Fix**: 
1. Added denormalized fields to `ProyectoResult` (`entidad_tipo_documento`, `entidad_numero_documento`, `entidad_razon_social`)
2. Updated orchestrator to populate these denormalized fields via `getattr(proyecto, 'entidad_tipo_documento', None)`
3. Presenter now uses `getattr(general.proyecto, 'entidad_tipo_documento', None)` safe access pattern
4. Guard: `if ent_tipo or ent_numero or ent_razon` before creating EntidadInlineSchema

### Additional Files Changed
| File | Action | Description |
|------|--------|-------------|
| `backend/modules/liquidaciones/domain/results/liquidacion_general/liquidacion_general_result.py` | Modified | Added denormalized `entidad_tipo_documento`, `entidad_numero_documento`, `entidad_razon_social` Optional fields to `ProyectoResult` |

## Validation Results
- `python manage.py check`: **PASS** (0 issues)
- `python manage.py makemigrations --check`: **No changes detected** (correct — Result schema changes don't require migrations)

## Completed Tasks (cumulative)
- [x] Add `list_liquidaciones_generales_paginated()` to core service (batch 1)
- [x] Create `LiquidacionGeneralOrchestrator` (batch 1)
- [x] Create `LiquidacionGeneralPresenter` (batch 1)
- [x] Create `LiquidacionGeneralController` (batch 1)
- [x] Register controller in `config/api.py` (batch 1)
- [x] **Fix N+1: conditional prefetch based on tipo** (batch 2)
- [x] **Fix auth: remove auth=None from route** (batch 2)
- [x] **Fix presenter None guard using denormalized fields** (batch 2)
- [x] **Add denormalized fields to ProyectoResult** (batch 2)
- [x] Validate with Django check and makemigrations --check

## Next Steps
- Ready for verify phase
