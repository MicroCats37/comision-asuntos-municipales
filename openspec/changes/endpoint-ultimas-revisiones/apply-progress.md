# SDD Apply Progress: Endpoint GET /liquidaciones/generales/ultimas-revisiones

## Status: COMPLETE

## Implementation Summary

### Endpoint Created
**`GET /liquidaciones/generales/ultimas-revisiones`** - Returns only the latest revision per (proyecto, tipo_liquidacion) pair.

### Files Modified/Created

| File | Action | What Was Done |
|------|--------|---------------|
| `backend/modules/liquidaciones/domain/services/core/liquidacion_general/liquidacion_general_core_service.py` | Modified | Added `list_liquidaciones_ultimas_generales_paginated()` method (~135 lines). Fixed prefetch bug in `list_ultimas_revisiones_por_proyecto()` (was hardcoded to Edificaciones only, now uses dynamic prefetch based on `tipo_liquidacion` param). |
| `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_general_orchestrator.py` | Modified | Added `listar_ultimas_liquidaciones_generales()` thin facade method (~25 lines) that validates pagination, delegates to core, reuses `_build_general_result`. |
| `backend/modules/liquidaciones/presentation/controllers/liquidacion_general_controller.py` | Modified | Added `GET /ultimas-revisiones` endpoint (~32 lines) with same query params as general listing. |

### Bug Fix Applied

**Prefetch bug in `list_ultimas_revisiones_por_proyecto` (line 671+)**:
- **Problem**: Prefetch chain was hardcoded to only Edificaciones relations (`edificaciones`, `liquidacion_porcentaje_obra`, etc.) - lines 702-708. This meant other tipos (HU, MS, IO, IV, Taludes) would not prefetch their specific relations, causing N+1 queries.
- **Fix**: Replaced hardcoded prefetch with dynamic prefetch based on `tipo_liquidacion` parameter, matching the exact pattern from `list_liquidaciones_generales_paginated`. Added 6 conditional branches (one per tipo) plus a fallback to prefetch all.
- **Impact**: Caller `liquidacion_edificaciones_orchestrator.py:685` passes `EDIFICACION` and continues to work. The fix is backward-compatible since EDIFICACION path remains unchanged.

### New Core Method Details

**`list_liquidaciones_ultimas_generales_paginated`**:
- Uses subquery: `Max('numero_revision')` grouped by `(proyecto_id, tipo_liquidacion__codigo)` to identify latest revision per project+tipo
- Subquery pattern: `OuterRef('proyecto_id')` + `OuterRef('tipo_liquidacion__codigo')` for correct grouping per tipo
- Conditional prefetch based on `tipo` filter (same strategy as `list_liquidaciones_generales_paginated`)
- Applies same optional filters: `tipo`, `documento`, `razon_social`, `propietario`
- Returns `(queryset, total_count)` tuple

### Verification Results

| Check | Result |
|-------|--------|
| `manage.py check` | 0 issues |
| `makemigrations --check` | No changes detected (code-only) |
| `pytest -k "list" --ignore=e2e/` | 69 passed |
| Smoke test (no auth) | 401 Unauthorized (JWT required - expected) |
| Endpoint registered | Yes - route `liquidaciones/generales/ultimas-revisiones` confirmed in API urls |

### Verification Notes

- Both `GET /liquidaciones/generales/` and `GET /liquidaciones/generales/ultimas-revisiones` return 401 without JWT - this is expected behavior (global JWT auth on the API)
- The endpoint IS being reached and routed correctly (confirmed in logs: `LiquidacionGeneralController[list_ultimas_liquidaciones]`)
- The 404 earlier was due to trailing slash - URL is `/api/liquidaciones/generales/ultimas-revisiones` (no trailing slash)

---

## Filtros adicionales: expediente + nombre_propietario

### Fecha de aplicación
Agregados en batch apply del 2026-08-12.

### Qué se agregó

Dos query params nuevos en AMBOS endpoints generales:
- `GET /liquidaciones/generales/`
- `GET /liquidaciones/generales/ultimas-revisiones/`

#### Params agregados

| Param | Tipo | Descripción |
|-------|------|-------------|
| `expediente` | `str` opcional | Filtra por `LiquidacionGeneral.expediente` con `__icontains` |
| `nombre_propietario` | `str` opcional | Alias explícito de `propietario` — ambos filtran `proyecto__nombre_propietario__icontains` |

**Nota**: `propietario` y `nombre_propietario` son equivalentes (misma semántica). Se exponen ambos porque el usuario los solicitó explícitamente.

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `backend/modules/liquidaciones/presentation/controllers/liquidacion_general_controller.py` | 2 nuevos `Query()` params en cada endpoint (`list_liquidaciones` y `list_ultimas_liquidaciones`); se pasan al orquestador |
| `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_general_orchestrator.py` | Acepta y reenvía `expediente` y `nombre_propietario` a ambos métodos del core |
| `backend/modules/liquidaciones/domain/services/core/liquidacion_general/liquidacion_general_core_service.py` | Filtros `expediente__icontains` y `proyecto__nombre_propietario__icontains` agregados a `list_liquidaciones_generales_paginated` y `list_liquidaciones_ultimas_generales_paginated` (solo cuando el valor no es `None`) |

### Verificación

| Check | Resultado |
|-------|-----------|
| `manage.py check` (dev settings) | 0 issues |
| `ast.parse()` en los 3 archivos | OK — sin errores de sintaxis |

### Skill Resolution
- `sdd-apply` skill: Cargada desde `C:\Users\Usuario\.claude\skills\sdd-apply\SKILL.md`
- `_shared` skill: Cargada desde `C:\Users\Usuario\.config\opencode\skills\_shared\SKILL.md`
- Ambas skills seguidas exactamente según lo especificado.
