# Verification Report: `rh-mensual-delegado-candidatas`

## Change Summary
Bug fix: `LiquidacionGeneral` created without `especialidades_revisadas` causes `get_candidatas_for_delegado` to return empty despite delegate being TITULAR for the municipalidad.

## Bug Details
- **User report**: Delegate with CIP `070258` (LUIS ENRIQUE PAREDES MACEDO) is TITULAR for BREÑA, but `GET /liquidaciones/delegados/candidatas?cip=070258` returns nothing for a `LiquidacionGeneral` of type 'Edificaciones'.
- **Secondary question**: Periodo filter correctness in `DelegadoOperacionPeriodo` (using `date.today()`).

---

## Root Cause Analysis

### Investigation via `manage.py shell` diagnostic

**Step 1 — Delegate state for CIP 070258:**
```
Delegado: e93bec4b-1732-490f-9d87-0a4700d0e889 (LUIS ENRIQUE PAREDES MACEDO)
Operaciones TITULAR vigentes (today=2026-08-24):
  - BREÑA (id=37a739d7-...): especialidad_revision = Eléctrica/Mecánica (codigo=03)
  - PUNTA NEGRA (id=a52acacb-...): especialidad_revision = Eléctrica/Mecánica (codigo=03)
Both operations: periodo 2025-08-18 to None → vigente ✓
```

**Step 2 — `LiquidacionGeneral` existence:**
```
TipoLiquidacion.codigo = 'EDIFICACION' (NOT 'EDIFICACIONES')
  ↳ This caused the user's initial search with 'EDIFICACIONES' to return 0 results.
  ↳ The actual codigo used in the DB is singular.

LiquidacionGeneral (id=5db62ed4-ebd8-40f7-bcd9-1153fc8f3ded):
  - tipo_liquidacion: EDIFICACION
  - municipalidad: BREÑA
  - estado: PENDIENTE
  - especialidades_revisadas: []  ← EMPTY ← ROOT CAUSE
```

**Step 3 — `get_candidatas_for_delegado` trace (delegado_core_service.py:466):**

The method builds for each TITULAR `DelegadoOperacion`:
```python
q_filter = Q(municipalidad_id=op.municipalidad_id)          # BREÑA ✓
# op.liquidacion_revision_id is NULL → no tipo_liquidacion filter
q_filter &= Q(especialidades_revisadas=op.especialidad_revision)  # ← silently fails
```
`especialidades_revisadas` is a **ManyToManyField** to `EspecialidadRevision`. An empty M2M produces no JOIN matches → `qs` is empty → liquidacion excluded.

**Step 4 — `DelegadoOperacionPeriodo` date filter:**
```python
Q(periodos__periodo_inicio__lte=fecha, periodos__periodo_fin__isnull=True)
| Q(periodos__periodo_inicio__lte=fecha, periodos__periodo_fin__gte=fecha)
```
This is **correct**. The delegate's period (2025-08-18 to None) is vigente on today (2026-08-24). No bug here.

**Step 5 — Fix verification (before/after):**

| State | `especialidades_revisadas` | `get_candidatas_for_delegado` result |
|---|---|---|
| Before fix | `[]` (empty) | 0 candidates |
| After auto-populate | `[Civil, Sanitaria, Eléctrica/Mecánica]` | 1 candidate (BREÑA, Eléctrica/Mecánica) |

---

## What Was Fixed

### File: `backend/modules/liquidaciones/admin/liquidacion_admin.py`

**Change**: Added `save_model()` to `LiquidacionGeneralAdmin` that auto-populates `especialidades_revisadas` from `LiquidacionEspecialidadDisponibles` (activo=True, vigente) when the field is empty on creation.

**Why this approach**: `especialidades_revisadas` is a manual multi-select (`filter_horizontal`) in the admin with no automatic population. `LiquidacionEspecialidadDisponibles` already defines which `EspecialidadRevision`s are valid for each `TipoLiquidacion` — the fix connects these two existing mechanisms.

**Logic** (only on creation, not edit):
```python
if not change and not obj.especialidades_revisadas.exists() and obj.tipo_liquidacion_id:
    disponibles = LiquidacionEspecialidadDisponibles.objects.filter(
        tipo_liquidacion=obj.tipo_liquidacion_id,
        activo=True,
        periodo_inicio__lte=today,
    ).filter(
        Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=today)
    )
    for disp in disponibles:
        obj.especialidades_revisadas.add(disp.especialidad)
```

**Existing data**: The one existing `LiquidacionGeneral` (id=`5db62ed4-...`) needs manual fix in Django admin: open it, go to "Especialidades Revisadas", select the relevant specialties (e.g., Eléctrica/Mecánica), and save.

---

## Verdict

| Check | Status |
|---|---|
| `DelegadoOperacionPeriodo` date filter uses `date.today()` | ✅ Correct — vigente delegates are properly included |
| `liquidacion_revision` NULL handling in `get_candidatas_for_delegado` | ✅ Correct — NULL means "all tipos", no filter applied |
| `especialidades_revisadas` empty → excluded from candidates | ✅ Expected behavior (not a code bug) |
| `get_candidatas_for_delegado` returns candidates after fix | ✅ PASS — 1 candidate returned for BREÑA |
| Auto-populate in `save_model` | ✅ PASS — `LiquidacionEspecialidadDisponibles` has 3 entries for EDIFICACION, all added |
| Fix only on creation (not on edit) | ✅ PASS — `not change` guard |

**Root cause**: `LiquidacionGeneral` was created without populating `especialidades_revisadas`. This is a **missing auto-population in admin** (not a backend logic bug). The delegate's operation and period were perfectly valid — the liquidation simply had no specialties recorded.

**Verdict: PASS with data-fix required for existing record(s).**
