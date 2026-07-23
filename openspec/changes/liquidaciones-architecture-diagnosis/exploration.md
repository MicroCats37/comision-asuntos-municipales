# Exploration: liquidaciones-architecture-diagnosis

**Date**: 2026-07-21
**Phase**: sdd-explore
**Mode**: Diagnosis (no change proposed)
**User hypothesis**: The liquidacion model relates Tarifa IDs directly (via ForeignKey or implicit FK to ReglaTarifa/Tarifa) without an explicit, denormalized field that would let each Liquidacion snapshot the actual tariff variant value at the moment of creation.

---

## 1. Current State

### 1.1 Database Models — Key Finding

**The user's hypothesis is CONFIRMED.** The system does NOT snapshot tariff values at liquidation creation time. Instead, it stores live FK references that are traversed at read time.

#### LiquidacionPorcentajeObra (Edificaciones) — `liquidacion.py:359-401`

```python
class LiquidacionPorcentajeObra(BaseModel):
    liquidacion_general = models.ForeignKey(LiquidacionGeneral, ...)
    valor_proyecto = models.DecimalField(...)  # ✅ PERSISTED
    valor_base_calculo = models.DecimalField(...)  # ✅ PERSISTED
    tarifa_aplicada = models.ForeignKey(TarifaPorcentajeObra, ...)  # ❌ LIVE FK
```

**Stored**: `valor_proyecto`, `valor_base_calculo`, FK to `TarifaPorcentajeObra`
**NOT stored**: `porcentaje_liquidacion`, `derecho_minimo`, `derecho_maximo`, `porcentaje_minimo_uit`

To get tariff values at read time, the system traverses:
```
LiquidacionPorcentajeObra.tarifa_aplicada 
  → TarifaPorcentajeObra.tarifa_base (OneToOne) 
    → TarifaLiquidacionBase.especialidades (M2M)
```

#### LiquidacionPorMetroCuadrado (Habilitación Urbana, Mecánica Suelos, Impacto Vial, Taludes) — `calculos_tarifas.py:17-66`

```python
class LiquidacionPorMetroCuadrado(BaseModel):
    liquidacion_general = models.ForeignKey(LiquidacionGeneral, ...)
    area_solicitada = models.DecimalField(...)  # ✅ PERSISTED
    area_base_calculo = models.DecimalField(...)  # ✅ PERSISTED
    derecho = models.DecimalField(...)  # ✅ PERSISTED (computed value)
    tarifa_aplicada = models.ForeignKey(TarifaPorMetroCuadrado, ...)  # ❌ LIVE FK
```

**Stored**: `area_solicitada`, `area_base_calculo`, `derecho`, FK to `TarifaPorMetroCuadrado`
**NOT stored**: `costo_por_m2`, `derecho_minimo`, `derecho_maximo`

#### LiquidacionPorCategoriaVisitas (Inspección de Obra) — `calculos_tarifas.py:69-120`

```python
class LiquidacionPorCategoriaVisitas(BaseModel):
    liquidacion_general = models.ForeignKey(LiquidacionGeneral, ...)
    cantidad_visitas = models.PositiveIntegerField(...)  # ✅ PERSISTED
    visitas_base_calculo = models.PositiveIntegerField(...)  # ✅ PERSISTED
    derecho = models.DecimalField(...)  # ✅ PERSISTED
    categoria = models.CharField(...)  # ✅ PERSISTED
    tarifa_aplicada = models.ForeignKey(TarifaPorCategoriaVisitas, ...)  # ❌ LIVE FK
```

**NOT stored**: `costo_por_visita`, `visitas_minimas`

### 1.2 Critical Historical Evidence

**There WAS a `LiquidacionSnapshot` model that was deleted.**

- Migration `0019_delete_liquidacionsnapshot.py` (2026-07-01): DELETED `LiquidacionSnapshot`
- Migration `0018_reverse_tarifa_relacion.py` (2026-07-01): REVERSED the FK direction

**Before migration 0018:**
```
TarifaLiquidacionBase.tarifa_porcentaje → FK → TarifaPorcentajeObra
```

**After migration 0018:**
```
TarifaPorcentajeObra.tarifa_base → OneToOne → TarifaLiquidacionBase
```

This is a schema evolution that made the relationship more explicit, but the snapshot model was removed entirely, leaving the live FK problem intact.

### 1.3 Contrast: Proyecto HAS Snapshot Fields

The `Proyecto` model (`proyecto.py:40-60`) shows the intended pattern:

```python
# Campos denormalizados de la entidad para preservar histórico
entidad_razon_social = models.CharField(...)  # "Copia de entidad.razon_social al momento de crear el proyecto."
entidad_tipo_documento = models.CharField(...)
entidad_numero_documento = models.CharField(...)
```

This pattern was correctly applied to `Proyecto` for entity data but was NOT applied to `Liquidacion*` models for tariff data.

### 1.4 Business Logic Flow

In `liquidacion_edificaciones_flujo.py:249-265`, when creating a liquidation:

```python
# 8b. Persistir LiquidacionPorcentajeObra por cada revisión calculada
for rev in revision_results:
    tarifa_pct = TarifaPorcentajeObra.objects.get(id=rev.tarifa.id)
    LiquidacionPorcentajeObra.objects.create(
        liquidacion_general=liquidacion,
        valor_proyecto=valor_proyecto,
        valor_base_calculo=valor_base,
        tarifa_aplicada=tarifa_pct,  # LIVE FK, not snapshot
    )
```

The `rev.tarifa` object is the live TarifaPorcentajeObra at creation time. If that record is later modified, historical liquidations will reflect the new values.

### 1.5 Read-Time Traversal

In `liquidacion_edificaciones_core_service.py:546-574`, reading a liquidation:

```python
for lpo in lpo_list:
    tarifa = lpo.tarifa_aplicada  # LIVE traversal
    if tarifa and hasattr(tarifa, 'tarifa_base') and tarifa.tarifa_base:
        especialidades_orm = list(tarifa.tarifa_base.especialidades.all())
```

The system reads CURRENT tariff values via the FK chain, not snapshots.

---

## 2. Other Scaling Concerns Found

### 2.1 Max 5 Revisions — Hardcoded Ceiling

`liquidacion_edificaciones_flujo.py:53-54`:
```python
REVISIONES_COBRAN = {1, 3, 5}
MAX_REVISIONES = 5
```

The sequence is 1 → 3 → 5 (step +2). Revision 6+ cannot be created. If the client needs more revisions, this is a hard barrier.

### 2.2 N+1 Query Risk

The FK chain at read time requires multiple joins:
```
LiquidacionGeneral 
  → liquidacion_porcentaje_obra 
    → tarifa_aplicada (TarifaPorcentajeObra)
      → tarifa_base (TarifaLiquidacionBase)
        → especialidades (M2M)
```

The code uses `prefetch_related` in some places (`liquidacion_edificaciones_core_service.py:511`) but the chain depth is a maintenance concern.

### 2.3 All Specialty Types Share the Same Problem

Every specialization extends `LiquidacionGeneral` via `OneToOneField` and uses the same pattern:
- `LiquidacionEdificacion` → `LiquidacionPorcentajeObra` (FK to `TarifaPorcentajeObra`)
- `LiquidacionHabilitacionUrbana` → `LiquidacionPorMetroCuadrado` (FK to `TarifaPorMetroCuadrado`)
- `LiquidacionMecanicaSuelos` → `LiquidacionPorMetroCuadrado` (FK to `TarifaPorMetroCuadrado`)
- `LiquidacionInspeccionObra` → `LiquidacionPorCategoriaVisitas` (FK to `TarifaPorCategoriaVisitas`)

### 2.4 UniqueConstraint Limits Tariff Reuse

`ReglaTarifaEdificacion` (`liquidacion.py:481-486`):
```python
UniqueConstraint(
    fields=["tipo_tramite", "tramite_accion", "tarifa_base"],
    name="unique_regla_tarifa_edificacion",
)
```

A `TarifaLiquidacionBase` can only have ONE rule per `(tipo_tramite, tramite_accion)` combination. This limits tariff variant reuse across different trámite types.

### 2.5 Simple History Is Used But Doesn't Solve the Problem

`simple_history` tracks model changes, but `HistoricalTarifaPorcentajeObra` records the historical state of the tariff VALUES themselves — not which tariff was applied to which liquidation. The `tarifa_aplicada` FK still points to the current record.

---

## 3. Summary of Evidence

| File | Line | Finding |
|------|------|---------|
| `liquidacion.py` | 387-393 | `LiquidacionPorcentajeObra.tarifa_aplicada` is a live FK, not a snapshot |
| `liquidacion.py` | 248-307 | `TarifaPorcentajeObra` stores values (`porcentaje_liquidacion`, etc.) but they are NOT copied to `LiquidacionPorcentajeObra` |
| `calculos_tarifas.py` | 53-59 | `LiquidacionPorMetroCuadrado.tarifa_aplicada` is a live FK, `costo_por_m2` etc. NOT stored |
| `calculos_tarifas.py` | 107-113 | `LiquidacionPorCategoriaVisitas.tarifa_aplicada` is a live FK, `costo_por_visita` NOT stored |
| `proyecto.py` | 40-60 | `Proyecto` HAS snapshot fields for entity — proves pattern was known but not applied to tariffs |
| `migrations/0019` | 13 | `LiquidacionSnapshot` model was DELETED — snapshotting was removed, not fixed |
| `migrations/0018` | 22-48 | FK direction reversed but no snapshot fields added |
| `liquidacion_edificaciones_flujo.py` | 255-265 | Creation uses live FK: `tarifa_aplicada=tarifa_pct` |
| `liquidacion_edificaciones_flujo.py` | 53-54 | Hardcoded ceiling: `MAX_REVISIONES = 5` |

---

## 4. Executive Summary

**User hypothesis: CONFIRMED**

The liquidaciones subsystem stores **live FK references** to tariff models (`TarifaPorcentajeObra`, `TarifaPorMetroCuadrado`, `TarifaPorCategoriaVisitas`) without persisting the actual tariff variant values (`porcentaje_liquidacion`, `derecho_minimo`, `costo_por_m2`, etc.) at the moment of liquidation creation.

**Concrete scaling ceiling:**
- If any `TarifaPorcentajeObra` record's `derecho_minimo`, `porcentaje_liquidacion`, or other value is modified, ALL historical `LiquidacionPorcentajeObra` records pointing to it will return different computed `derecho` values when read.
- There is no `tarifa_valor_snapshot`, `porcentaje_snapshot`, or similar denormalized field on any `Liquidacion*` calculation model.
- The maximum revision sequence is 1 → 3 → 5 (hardcoded `MAX_REVISIONES = 5`). The business cannot support a 6th revision without a code change.

**The irony:** The `Proyecto` model already implements this exact snapshot pattern for entity data (`entidad_razon_social`, `entidad_numero_documento`, etc. — see `proyecto.py:40-60`) with explicit comments: "copias denormalizadas... para preservar el histórico." The same pattern was simply never applied to tariff data.

**What WAS tried:**
- There WAS a `LiquidacionSnapshot` model (deleted in migration `0019_delete_liquidacion_snapshot`, 2026-07-01)
- The deletion happened AFTER the FK reversal in migration `0018_reverse_tarifa_relacion`
- The snapshot was removed rather than fixed

**Other risks found:**
1. Hardcoded `MAX_REVISIONES = 5` ceiling
2. N+1 query risk in deep FK chain traversal at read time
3. UniqueConstraint on `(tipo_tramite, tramite_accion, tarifa_base)` limits tariff reuse
4. All 6 specialty types share the same unsnaphotted FK pattern

---

## 5. Next Steps

This is a **diagnosis only** phase. No implementation is recommended here.

If the user decides to refactor, the appropriate SDD phases would be:
1. `sdd-propose` — define the scope of snapshot field additions
2. `sdd-spec` — specify which fields need snapshotting per model
3. `sdd-design` — design the migration strategy (data migration for existing records)
4. `sdd-tasks` — break into implementable tasks
5. `sdd-apply` — implement
6. `sdd-verify` — test

---

## 6. Files Referenced

| File | Role |
|------|------|
| `backend/modules/liquidaciones/domain/models/liquidacion/liquidacion.py` | Core liquidacion models including `LiquidacionPorcentajeObra`, `TarifaPorcentajeObra`, `TarifaLiquidacionBase` |
| `backend/modules/liquidaciones/domain/models/liquidacion/calculos_tarifas.py` | `LiquidacionPorMetroCuadrado`, `LiquidacionPorCategoriaVisitas` |
| `backend/modules/liquidaciones/domain/models/proyecto.py` | `Proyecto` with snapshot fields (contrast) |
| `backend/modules/liquidaciones/domain/services/core/liquidacion_edificaciones_core_service.py` | Core calculation service |
| `backend/modules/liquidaciones/domain/services/flujos/liquidacion_edificaciones_flujo.py` | Business flow, `MAX_REVISIONES` ceiling |
| `backend/modules/liquidaciones/migrations/0018_reverse_tarifa_relacion.py` | FK direction reversal |
| `backend/modules/liquidaciones/migrations/0019_delete_liquidacionsnapshot.py` | Snapshot model deletion |
| `backend/modules/liquidaciones/presentation/presenters/liquidacion_edificaciones_presenter.py` | API output transformation |
