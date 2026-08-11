# SDD Apply Progress: registro-busquedas-ingeniero-habilitado

## Status
**success** — Implementation complete. Fix validation applied.

## Summary
Implemented daily search deduplication for `IngenieroHabilitacion` model by reusing the existing model (not creating a new one). Added `fecha_busqueda` field with partial unique constraint for PostgreSQL compatibility (NULL values from seed data don't violate the constraint).

## Files Modified/Created

| File | Action | Description |
|------|--------|-------------|
| `backend/modules/usuarios/domain/models/perfil_ingeniero.py` | Modified | Added `fecha_busqueda` field + `UniqueConstraint` with condition to `IngenieroHabilitacion` |
| `backend/modules/usuarios/domain/services/core/ingeniero_habilitacion_core_service.py` | Created | New core service with `registrar_busqueda()` method using `update_or_create` |
| `backend/modules/usuarios/domain/services/flujos/ingeniero_habilitado_flujo.py` | Modified | Added `_registrar_busqueda_async()` call after successful CIP data retrieval, wrapped in try/except |
| `backend/modules/usuarios/di.py` | Modified | Added `IngenieroHabilitacionCoreService` binding |
| `backend/modules/usuarios/migrations/0002_add_fecha_busqueda_to_ingeniero_habilitacion.py` | Created | Migration for new field and constraint |

## Key Design Decisions

1. **Constraint with condition**: Used `condition=models.Q(fecha_busqueda__isnull=False)` in `UniqueConstraint` so that seed data with `fecha_busqueda=None` doesn't violate uniqueness (PostgreSQL treats NULLs as distinct).

2. **update_or_create**: Core service uses `update_or_create` instead of `get_or_create` to update `condicion_cip`/`ultimo_periodo_pagado_cip` when the same CIP is searched on the same day.

3. **timezone.localdate()**: Used `timezone.localdate()` as default for `fecha` parameter (not naive `date.today()`).

4. **Silent failure**: Registration errors are logged but don't break the endpoint response.

## Fix Validación: Atomic + Delegación Core

Applied two architectural fixes per contract/PLAN_REFACTORIZACION.md:

### 1. Added `@transaction.atomic` to `_registrar_busqueda_async`
- **File**: `backend/modules/usuarios/domain/services/flujos/ingeniero_habilitado_flujo.py`
- **Change**: Wrapped both writes (PerfilIngeniero get_or_create + registrar_busqueda) in `transaction.atomic()` block
- **Why**: If `registrar_busqueda` failed, `PerfilIngeniero` would be left orphaned without the transaction

### 2. Moved `get_or_create` to Core Service
- **File**: `backend/modules/usuarios/domain/services/core/perfil_ingeniero_core_service.py`
- **Change**: Added `obtener_o_crear_perfil_por_cip(cip)` method that does `PerfilIngeniero.objects.get_or_create(cip=normalized)`
- **File**: `backend/modules/usuarios/domain/services/flujos/ingeniero_habilitado_flujo.py`
- **Change**: Replaced direct `PerfilIngeniero.objects.get_or_create()` with `self._core.obtener_o_crear_perfil_por_cip()`
- **Why**: Contract Section 4 says Core = "Transaccionalidad pura del ORM"; Flujo = "único lugar donde existe @transaction.atomic"

### Implementation Pattern
```python
@sync_to_async
def _atomic_registrar():
    with transaction.atomic():
        perfil = self._core.obtener_o_crear_perfil_por_cip(normalized_cip)
        self._habilitacion_core.registrar_busqueda(...)
await _atomic_registrar()
```

## Tests
- 196 tests passed in `modules/liquidaciones/tests/integration/`
- 6 e2e errors (pre-existing, not related to this change)
- No existing `IngenieroHabilitacion` tests found
- Imports verified OK for modified modules

## Next Recommended
`sdd-verify` — Run full verification suite to confirm implementation matches specs.
