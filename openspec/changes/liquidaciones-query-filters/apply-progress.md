# Apply Progress: liquidaciones-query-filters

**Status**: ✅ Completed

**Date**: 2026-08-11

---

## Implementation Summary

Implemented query param filters for all 6 GET `/liquidaciones/{type}/` endpoints following exploration v3 guide.

## Files Modified

### Core Service (1 file)
- `backend/modules/liquidaciones/domain/services/core/liquidacion_general/liquidacion_general_core_service.py`
  - Updated `list_liquidaciones_by_type_paginated` with filter kwargs and chained `.filter()` calls
  - Updated `list_liquidaciones_hu_paginated` with filter kwargs and chained `.filter()` calls
  - Updated `list_liquidaciones_ms_paginated` with filter kwargs and chained `.filter()` calls
  - Updated `list_liquidaciones_taludes_paginated` with filter kwargs and chained `.filter()` calls
  - Updated `list_liquidaciones_io_paginated` with filter kwargs and chained `.filter()` calls
  - Updated `list_liquidaciones_iv_paginated` with filter kwargs and chained `.filter()` calls

### Orchestrators (6 files)
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_especifico/liquidacion_edificaciones_orchestrator.py`
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_especifico/liquidacion_taludes_orchestrator.py`
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_especifico/liquidacion_habilitacion_urbana_orchestrator.py`
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_especifico/liquidacion_impacto_vial_orchestrator.py`
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_especifico/liquidacion_inspeccion_obra_orchestrator.py`
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_especifico/liquidacion_mecanica_suelos_orchestrator.py`

All orchestrators: updated `listar_liquidaciones` method to accept filter kwargs and pass them to core service.

### Controllers (6 files)
- `backend/modules/liquidaciones/presentation/controllers/liquidacion_especifico/liquidacion_edificaciones_controller.py`
- `backend/modules/liquidaciones/presentation/controllers/liquidacion_especifico/liquidacion_taludes_controller.py`
- `backend/modules/liquidaciones/presentation/controllers/liquidacion_especifico/liquidacion_habilitacion_urbana_controller.py`
- `backend/modules/liquidaciones/presentation/controllers/liquidacion_especifico/liquidacion_impacto_vial_controller.py`
- `backend/modules/liquidaciones/presentation/controllers/liquidacion_especifico/liquidacion_inspeccion_obra_controller.py`
- `backend/modules/liquidaciones/presentation/controllers/liquidacion_especifico/liquidacion_mecanica_suelos_controller.py`

All controllers: updated `list_liquidaciones` to parse optional query params with `Query(...)` and pass to orchestrator.

## Filters Supported

| Param | Type | Django ORM | Notes |
|-------|------|------------|-------|
| `entidad_id` | UUID | `municipalidad_id` (exact) | Filter by municipalidad |
| `propietario` | str | `proyecto__nombre_propietario__icontains` | Case-insensitive partial match |
| `fecha_desde` | date | `fecha_registro__date__gte` | Greater than or equal |
| `fecha_hasta` | date | `fecha_registro__date__lte` | Less than or equal |
| `numero` | int | `{tipo}__numero` (exact) | Type-specific join filter |
| `razon_social` | str | `proyecto__entidad_razon_social__icontains` | Case-insensitive partial match |
| `creado_por` | str | `usuario_creador__username__icontains` | Case-insensitive partial match |
| `numero_revisiones` | int | `numero_revision` (exact) | Exact match on revision count |

## Tests

All 60 list tests pass:
- `test_edificaciones_list.py`: 9 passed
- `test_taludes_list.py`: 9 passed
- `test_hu_list.py`: 8 passed
- `test_ms_list.py`: 7 passed
- `test_io_list.py`: 7 passed
- `test_iv_list.py`: 9 passed

## Notes

- All params are optional with default `None`
- Controller param `entidad_id` maps to core service `municipalidad_id`
- Controller param `creado_por` maps to orchestrator `creador_username`
- Controller param `numero_revisiones` maps to core service `numero_revision`
- `numero` filter uses type-specific join: `edificaciones__numero`, `taludes__numero`, `habilitacion_urbana__numero`, `impacto_vial__numero`, `inspeccion_obra__numero`, `mecanica_suelos__numero`
- Pagination params (`page`, `page_size`) remain unchanged
- Architecture rule (§1.A from PLAN_REFACTORIZACION.md) respected: controller only parses input and delegates to orchestrator
