# SDD Exploration: `liquidaciones-tablas-consistencia`

**Phase**: Explore  
**Project**: `comision-asuntos-municipales` (`betha` branch)  
**Focus**: Backend database model layer consistency audit  
**Date**: 2026-07-30  
**Language**: English (technical artifacts)

---

## 1. Model/Table Inventory

### 1.1 Operational Tables (Django models with live data intent)

| Model Class | DB Table (auto) | File | Notes |
|---|---|---|---|
| `LiquidacionGeneral` | `liquidaciones_liquidaciongeneral` | `liquidacion/liquidacion.py` | Core operational record |
| `LiquidacionContacto` | `liquidaciones_liquidacioncontacto` | `liquidacion/liquidacion.py` | Bridge: liquidacion ↔ contacto |
| `LiquidacionDocumentos` | `liquidaciones_liquidaciondocumentos` | `liquidacion/liquidacion.py` | Document attachments |
| `LiquidacionProyectista` | `liquidaciones_liquidacionproyectista` | `liquidacion/liquidacion.py` | Bridge: liquidacion ↔ proyectista |
| `LiquidacionDelegado` | `liquidaciones_liquidaciondelegado` | `liquidacion_delegado.py` | Bridge: liquidacion ↔ delegado (explicit M2M) |
| `LiquidacionEdificacion` | `liquidaciones_liquidacionedificacion` | `liquidacion/liquidacion_edificaciones.py` | OneToOne extension for EDIFICACION regime |
| `LiquidacionEdificacionProxy` | *(inherits `liquidaciongeneral`)* | `liquidacion/__init__.py` import — **MISSING from source** | Proxy of `LiquidacionGeneral` |
| `LiquidacionHabilitacionUrbana` | `liquidaciones_liquidacionhabilitacionurbana` | `liquidacion/liquidacion_habilitacion_urbana.py` | OneToOne extension for HU regime |
| `LiquidacionMecanicaSuelos` | `liquidaciones_liquidacionmecanicasuelos` | `liquidacion/liquidacion_mecanica_suelos.py` | OneToOne extension for MS regime |
| `LiquidacionImpactoVial` | `liquidaciones_liquidacionimpactovial` | `liquidacion/liquidacion_impacto_vial.py` | OneToOne extension for IV regime |
| `LiquidacionTaludes` | `liquidaciones_liquidaciontaludes` | `liquidacion/liquidacion_taludes.py` | OneToOne extension for TALUDES regime |
| `LiquidacionInspeccionObra` | `liquidaciones_liquidacioninspeccionobra` | `liquidacion/liquidacion_inspeccion_obra.py` | OneToOne extension for INSPECCION_OBRA regime |
| `LiquidacionPorMetroCuadrado` | `liquidaciones_liquidacionpormetrocuadrado` | `liquidacion_tipo.py` | Calculation detail: M2 regime |
| `LiquidacionPorCategoriaVisitas` | `liquidaciones_liquidacionporcategoriavisitas` | `liquidacion_tipo.py` | Calculation detail: visits regime |
| `LiquidacionPorcentajeObra` | `liquidaciones_liquidacionporcentajeobra` | `liquidacion_tipo.py` | Calculation detail: percentage regime |
| `Delegado` | `liquidaciones_delegado` | `delegado.py` | Delegate engineer |
| `DelegadoMunicipalidad` | `liquidaciones_delegadomunicipalidad` | `delegado.py` | Delegate × municipalidad assignment |
| `DelegadoMunicipalidadPeriodo` | `liquidaciones_delegadomunicipalidadperiodo` | `delegado.py` | Period of delegation per municipalidad |
| `Proyecto` | `liquidaciones_proyecto` | `proyecto.py` | Project (denormalized entity snapshot) |
| `ProyectoEmpresarial` | *(inherits `proyecto`)* | `proyecto.py` | Proxy: RUC entities |
| `ProyectoPersonaNatural` | *(inherits `proyecto`)* | `proyecto.py` | Proxy: DNI entities |
| `Proyectista` | `liquidaciones_proyectista` | `proyectista.py` | Professional responsible |
| `LiquidacionGeneralCodigo` | `liquidaciones_liquidaciongeneralcodigo` | `liquidacion/liquidacion.py` | Account code mapping |
| `LiquidacionTarifaAplicada` | `liquidaciones_liquidaciontarifaaplicada` | `liquidacion/liquidacion.py` | Bridge: liquidacion ↔ tarifa (catalog resolution) |

### 1.2 Catalog Tables (tariff/configuration, no applied data intent)

| Model Class | DB Table (auto) | File | Notes |
|---|---|---|---|
| `TarifaLiquidacionBase` | `liquidaciones_tarifaliquidacionbase` | `tarifas_reglas.py` | **MISSING required source fields** |
| `TarifaPorMetroCuadrado` | `liquidaciones_tarifapormetrocuadrado` | `tarifas_reglas.py` | M2 rate with min/max clamps |
| `TarifaPorCategoriaVisitas` | `liquidaciones_tarifaporcategoriavisitas` | `tarifas_reglas.py` | Visits rate |
| `TarifaPorcentajeObra` | `liquidaciones_tarifaporcentajeobra` | `tarifas_reglas.py` | Percentage rate with derecho_min/max |
| `DerechoMinimoPorcentajeObra` | *(not in any migration)* | `tarifas_reglas.py` | **Dead code — never migrated** |
| `DerechoMinimoPorMetroCuadrado` | *(not in any migration)* | `tarifas_reglas.py` | **Dead code — never migrated** |
| `ReglaTarifaLiquidacion` | *(not in any migration)* | `tarifas_reglas.py` | **Dead code — never migrated** |
| `ReglaTarifaInspeccionObra` | *(not in any migration)* | `tarifas_reglas.py` | **Dead code — never migrated** |
| `ReglaTarifaEdificacion` | `liquidaciones_reglatarifaedificacion` | Migration-only (0020) | **MISSING from source** |
| `EspecialidadesLiquidacion` | `liquidaciones_especialidadesliquidacion` | Migration-only (0014) | **MISSING from source** |
| `Especialidad` | *(external module)* | `usuarios.domain.models.perfil_ingeniero` | Source of truth for specialty catalog |

---

## 2. Inconsistency Findings Table

### 2.1 CRITICAL — Missing Model Class Definitions

> These models are referenced in `__init__.py` re-exports and would cause `ImportError` at runtime. The classes exist only as Django migration artifacts, not as Python source.

| Severity | Model/Table | Evidence | Why Inconsistent | Recommended Direction |
|---|---|---|---|---|
| **CRITICAL** | `EspecialidadesLiquidacion` | `domain/models/__init__.py` line 4 and 13 imports it; `models.py` line 17; `liquidacion/__init__.py` line 14 — but **no Python class definition exists** in any `.py` file under `domain/models/` | Migration `0014` created it, but no source `.py` file defines `class EspecialidadesLiquidacion`. Any `from .domain.models import EspecialidadesLiquidacion` will raise `ImportError`. | **Action required**: Either (a) write the model class definition in a source file (e.g., `liquidacion/especialidades_liquidacion.py`) matching the migration schema, or (b) remove from all `__init__.py` re-exports if the model is truly dead code. |
| **CRITICAL** | `ReglaTarifaEdificacion` | `domain/models/__init__.py` line 14; `models.py` line 18; `liquidacion/__init__.py` line 15 — but **no Python class definition exists** | Migration `0020` created it, but no source `.py` defines `class ReglaTarifaEdificacion`. Import chain will fail. | **Action required**: Either (a) write the model class in `tarifas_reglas.py` (it belongs semantically there), or (b) remove from re-exports if truly dead. |
| **CRITICAL** | `LiquidacionEdificacionProxy` | Re-exported in `liquidacion/__init__.py` line 24; `domain/models/__init__.py` line 19; `models.py` line 12 — but **no class definition exists** in `liquidacion_edificaciones.py` | `liquidacion_edificaciones.py` only defines `LiquidacionEdificacion`. The proxy is imported from `__init__.py` but never defined. Django will raise `ImportError`. | **Action required**: Add `class LiquidacionEdificacionProxy(LiquidacionGeneral): class Meta: proxy = True` to `liquidacion_edificaciones.py`. |
| **CRITICAL** | `TramiteAccion` (as model class) | `liquidacion/__init__.py` line 22 exports `TramiteAccion` — but `TramiteAccion` is a `TextChoices` constant in `constants.py`, NOT a model class. This is a naming collision. | The `__init__.py` re-exports `TramiteAccion` alongside model classes. `TramiteAccion` is a Django `TextChoices` enum, not a `BaseModel`. Code that imports thinking it's a model will get the enum, not a model. | **Action required**: Remove `TramiteAccion` from `liquidacion/__init__.py` model re-exports. It belongs in `constants.py` only. |
| **CRITICAL** | `TipoTramiteEdificaciones` (as model class) | `liquidacion/__init__.py` line 21 exports `TipoTramiteEdificaciones` — but this is also a `TextChoices` enum from `constants.py`, not a model. | Same issue as `TramiteAccion`. | **Action required**: Remove from model re-exports in `liquidacion/__init__.py`. |

### 2.2 HIGH — Source Model vs. Migration DB Shape Drift

> The Python source classes differ from what the migrations created in the database.

| Severity | Model/Table/Field | Evidence | Why Inconsistent | Recommended Direction |
|---|---|---|---|---|
| **HIGH** | `TarifaLiquidacionBase` — missing fields vs. DB | **Source** (`tarifas_reglas.py`): only has `tipo_liquidacion` field. **DB** (migration `0014` + `0018`): has `periodo_inicio`, `periodo_fin`, and a **removed** `tarifa_porcentaje` FK (reversed in `0018`). | The source model is a stripped-down stub. The DB has columns `periodo_inicio`, `periodo_fin` (from migration `0014`) that the source does NOT define. Django `makemigrations` would generate a migration to remove these columns. | Align source `TarifaLiquidacionBase` with the intended clean catalog design: remove `periodo_inicio`/`periodo_fin` (vigency belongs in a separate `TarifaVigencia` or `ValorTarifa` table). Remove `tarifa_porcentaje` FK entirely (already reversed in DB). Source matches DB for `tipo_liquidacion` only. |
| **HIGH** | `TarifaLiquidacionBase` — M2M to `Especialidad` missing in source | **DB**: `TarifaLiquidacionBase` has M2M `especialidades` field (created in migration `0014`). **Source**: `tarifas_reglas.py` defines no M2M. | The M2M exists in the DB but no source field maps to it. | User's intended design says specialty applicability is SEPARATE from tariff values. The M2M should be removed from `TarifaLiquidacionBase` and replaced with a separate `EspecialidadTarifaApplicability` bridge table if needed. |
| **HIGH** | `TarifaPorcentajeObra` — `tarifa_base` is `null=True` in source but unique constraint depends on it | Source: `tarifa_base = OneToOneField(..., null=True, blank=True)`. DB: `ReglaTarifaEdificacion` unique constraint `unique_regla_tarifa_edificacion` on `(tipo_tramite, tramite_accion, tarifa_base)` — if `tarifa_base` is null for some rows, uniqueness is not enforced on those rows. | The source allows null but the FK target is referenced in a unique constraint. | Fix: either make `tarifa_base` non-nullable (`null=False`) with a default or a sentinel, or drop the unique constraint and handle dedup in application logic. |
| **HIGH** | `LiquidacionPorcentajeObra` — field set mismatch | **Source** (`liquidacion_tipo.py`): has `valor_declarado`, `porcentaje_liquidacion`, `derecho_minimo`, `derecho_maximo`, `porcentaje_minimo_uit`. **Migration `0014`**: has `valor_proyecto`, `valor_base_calculo` and no `porcentaje_liquidacion`/`derecho_*` fields. **Migration `0024`**: adds `derecho`, `visitas_base_calculo` to `LiquidacionPorCategoriaVisitas` and `LiquidacionPorMetroCuadrado` but NOT to `LiquidacionPorcentajeObra`. | The source calculation model diverges from the DB shape. The DB table still has `valor_proyecto`/`valor_base_calculo` from migration `0014`. The source uses `valor_declarado` and different field names. | `LiquidacionPorcentajeObra` source fields need to be aligned with DB columns. Either rename source fields to match DB (`valor_proyecto`, `valor_base_calculo`) or write a migration to rename them to match source design. Recommend: adopt source naming (`valor_declarado`) and write migration. |
| **HIGH** | `LiquidacionPorMetroCuadrado` — `derecho` and `visitas_base_calculo` missing in source | **Migration `0024`** adds `derecho` and `visitas_base_calculo` to DB. **Source** (`liquidacion_tipo.py`): `LiquidacionPorMetroCuadrado` has `area_m2`, `costo_por_m2`, `derecho_minimo`, `derecho_maximo` — but NO `derecho` (calculated result) and NO `visitas_base_calculo` (the visits analog is not applicable here). | The DB has a `derecho` column; the source model has `derecho_minimo`/`derecho_maximo` (these are clamps, not the result). `visitas_base_calculo` doesn't make sense for M2 — it was likely meant for the visitas model. | The `visitas_base_calculo` field in `liquidacionpormetrocuadrado` is a mistake — it should only be in `LiquidacionPorCategoriaVisitas`. The `derecho` field should probably live on the calculation detail model, not the M2 model. Verify intent: is `derecho` the final computed value or a copy? |
| **HIGH** | `LiquidacionPorCategoriaVisitas` — `derecho` and `visitas_base_calculo` added in migration `0024` but missing in source | **Migration `0024`** adds `derecho` and `visitas_base_calculo` to `liquidacionporcategoriavisitas` table. **Source** (`liquidacion_tipo.py`): has `cantidad_visitas`, `porcentaje_uit`, `categoria` — no `derecho` or `visitas_base_calculo`. | The source is missing these two fields that the DB already has. `derecho` is the computed result; `visitas_base_calculo` is `max(cantidad_visitas, visitas_minimas)`. | Add both fields to `LiquidacionPorCategoriaVisitas` source model. |
| **HIGH** | `LiquidacionGeneral` — `periodo_incio` typo | Source: `periodo_incio` (line 133, missing `i`). DB: column name is `periodo_incio` (migrations `0003`, `0010`). | Typo in field name — should be `periodo_inicio`. This will confuse any developer reading or querying the DB. | Write a migration to rename `periodo_incio` → `periodo_inicio`. This is safe since the typo is consistent (both in source and all migrations). |

### 2.3 MEDIUM — Naming/Architecture Inconsistencies

| Severity | Model/Table/Field | Evidence | Why Inconsistent | Recommended Direction |
|---|---|---|---|---|
| **MEDIUM** | `TarifaLiquidacionBase` conceptually mixes concerns | `TarifaLiquidacionBase` in source has `tipo_liquidacion` only. The DB version has `periodo_inicio`/`periodo_fin` and M2M to `Especialidad`. | User's intended architecture: `tarifa_base` = stable identity only, no vigency/values. The DB shape violates this. | Align with user's intent: strip `TarifaLiquidacionBase` to just identity (`id`, `tipo_liquidacion`, timestamps). Move `periodo_inicio`/`periodo_fin` to a separate `TarifaValor` (value table) linked by `tarifa_base`. Move M2M `especialidades` to a separate `EspecialidadTarifaApplicability` bridge. |
| **MEDIUM** | `LiquidacionGeneral.tipo_liquidacion` vs. OneToOne extension tables | `LiquidacionGeneral` has `tipo_liquidacion` field (set of 6 values). Each specialty also has a OneToOne extension (`LiquidacionHabilitacionUrbana`, etc.). | The `tipo_liquidacion` on `LiquidacionGeneral` and the OneToOne extensions are redundant. A `LiquidacionGeneral` with `tipo_liquidacion='HABILITACION_URBANA'` should have a `LiquidacionHabilitacionUrbana` row; there's no enforced consistency between the two. | Decide: either keep `tipo_liquidacion` on `LiquidacionGeneral` and drop the OneToOne extensions, OR keep extensions and remove/redundancy-guard the `tipo_liquidacion` field. Current design uses both. |
| **MEDIUM** | `LiquidacionPorMetroCuadrado` and `LiquidacionPorCategoriaVisitas` carry calculation clamps as model fields | Both models have `derecho_minimo`/`derecho_maximo` fields directly on the calculation model. | The user's intended architecture says minimum rights should be periodized value tables, not fields directly on the calculation model. These values change over time (different UITs). | Move `derecho_minimo`/`derecho_maximo` to a separate `ValorMinimoTarifa` catalog table selected by calculation date, not stored per liquidation row. |
| **MEDIUM** | `CategoriaDelegado` choices mixing domain | `CategoriaDelegado.choices`: `EDIFICACIONES` = "Edificaciones", `HABILITACIONES_URBANAS` = "Habilitaciones Urbanas". This maps to `TipoLiquidacion` values but is stored as a separate enum. | Delegate category should probably just use `TipoLiquidacion` directly rather than maintaining parallel enums. | Deprecate `CategoriaDelegado` in favor of `TipoLiquidacion` or create a mapping. |
| **MEDIUM** | `LiquidacionGeneralCodigo` — orphan model | Model exists in source (`liquidacion.py` lines 165-179) with `tipo_liquidacion` and `codigo_cta`. No migration creates a table for it. | This model is not persisted to the DB — no migration references it. It's either dead code or pre-migration stub. | Either write a migration to create it or delete the model if unused. |
| **MEDIUM** | `Delegado.categoria` on `DelegadoMunicipalidad` | Field `DelegadoMunicipalidad.categoria` uses `CategoriaDelegado` choices. But `Delegado` model itself has no `categoria` field. | The category belongs to the assignment (delegado × municipalidad), which makes sense, but the enum name implies it categorizes the delegate's specialty. | Clarify: is `categoria` a specialty category or an assignment category? If specialty, it should potentially be on `Delegado` directly referencing `Especialidad`. |

### 2.4 MINOR — Semantic/Naming Issues

| Severity | Finding | Recommended Direction |
|---|---|---|
| **MINOR** | `LiquidacionPorCategoriaVisitas.categoria` is a free `CharField(max_length=20)` with no choices — inconsistent with `TipoTramiteEdificaciones` which has proper `TextChoices`. | Add `TextChoices` for inspection category (A, B, C, etc.) or use a ForeignKey to a `CategoriaInspeccion` catalog table. |
| **MINOR** | `LiquidacionDelegado.__str__` references `self.perfil_ingeniero` but `LiquidacionDelegado` has no `perfil_ingeniero` field — it has `delegado` (FK to `Delegado`) which has `perfil_ingeniero`. | Fix `__str__` to `self.delegado.perfil_ingeniero`. |
| **MINOR** | `TarifaPorMetroCuadrado.__str__` references `self.derecho_minimo` but the model has no `derecho_minimo` field (only `costo_por_m2` and `area_m2`). | Fix `__str__` to not reference non-existent field, or add the field if it was intended to be there. |
| **MINOR** | `ReglaTarifaEdificacion` is imported from `tarifas_reglas.py` in `__init__.py` line 33 but the source file does not define it. | Add `ReglaTarifaEdificacion` to `tarifas_reglas.py` or remove from re-exports. |

---

## 3. Clean Target Catalog-Only Diagram (Tariffs + Specialties)

```
┌─────────────────────────────────────────────────────────┐
│  Especialidad (usuarios.PerfilIngeniero.Especialidad)  │
│  — codigo, nombre                                       │
│  Source of truth for specialty catalog                  │
└───────────────────────┬─────────────────────────────────┘
                        │ M2M (separate applicability table)
                        ▼
┌─────────────────────────────────────────────────────────┐
│  TipoLiquidacion (TextChoices enum, not a model)       │
│  — EDIFICACION, HABILITACION_URBANA, MECANICA_SUELOS, │
│    IMPACTO_VIAL, TALUDES, INSPECCION_OBRA              │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────────────────────┐
        │               │                               │
        ▼               ▼                               ▼
┌───────────────┐ ┌──────────────────┐ ┌──────────────────────┐
│TarifaLiquidacionBase│TarifaPorMetroCuadrado│TarifaPorCategoriaVisitas│
│ (identity only) │ │ (OneToOne → base)│ │ (OneToOne → base)   │
│ id             │ │ costo_por_m2     │ │ costo_por_visita     │
│ tipo_liquidacion│ │ area_m2         │ │ visitas_minimas      │
│ created/updated │ │ (no min/max here│ │ (no min/max here —  │
│                │ │  those are in    │ │  those are in the    │
│                │ │  DerechoMinimo*) │ │  DerechoMinimo*)     │
└────────────────┘ └──────────────────┘ └──────────────────────┘
        ▲
        │ OneToOne (detail tables)
        │
        ┌──────────────────────────────────┐
        │                                  │
┌───────┴───────┐              ┌───────────┴───────────┐
│TarifaPorcentajeObra│              │ (future: DerechoMinimo*) │
│ (OneToOne → base) │              │ — periodized values     │
│ porcentaje_liquidacion│           │ — FK to base             │
│ porcentaje_minimo_uit │           │ — derecho_minimo/max      │
│ (derecho_min/max were │           │ — periodo_inicio/fin      │
│  on base in old design│           └──────────────────────────┘
└─────────────────────┘
        │
        │ referenced by
        ▼
┌─────────────────────────┐
│ReglaTarifaEdificacion   │  ← MISSING FROM SOURCE
│ FK → TarifaLiquidacionBase
│ tipo_tramite (choices)
│ tramite_accion (choices)
│ unique(tipo_tramite, tramite_accion, tarifa_base)
└─────────────────────────┘
```

**Note**: `DerechoMinimoPorcentajeObra` and `DerechoMinimoPorMetroCuadrado` in source are **dead code** — they have no migration. The right pattern per user's architecture is a periodized `DerechoMinimo` table with `periodo_inicio`/`periodo_fin` linked to `TarifaLiquidacionBase`.

---

## 4. Missing Catalog Tables (Suggested by Current Shape)

| Suggested Table | Why Needed | Suggested Model Name |
|---|---|---|
| `CategoriaInspeccion` | `LiquidacionPorCategoriaVisitas.categoria` is a free string. A proper catalog would make it a ForeignKey. | `CategoriaInspeccion` |
| `TarifaVigencia` (or `ValorTarifa`) | `TarifaLiquidacionBase` currently mixes identity with period/vigency. Per user intent, vigency should be a separate table. | `TarifaVigencia` — FK to `TarifaLiquidacionBase`, `periodo_inicio`, `periodo_fin`, `is_active` |
| `EspecialidadTarifaApplicability` | M2M between `TarifaLiquidacionBase` and `Especialidad` currently lives on `TarifaLiquidacionBase` directly (but missing in source). Should be a separate bridge. | `EspecialidadTarifaApplicability` |

---

## 5. Model Truncation/Invalidity Check

| Model | Status | Issue |
|---|---|---|
| `LiquidacionGeneralCodigo` | **Invalid — no migration** | Model class exists in source but no migration creates its table. Would fail ` migrate`. |
| `DerechoMinimoPorcentajeObra` | **Dead code — no migration** | Model exists in source only. No migration creates a table. |
| `DerechoMinimoPorMetroCuadrado` | **Dead code — no migration** | Model exists in source only. No migration creates a table. |
| `ReglaTarifaLiquidacion` | **Dead code — no migration** | Model exists in source only. No migration creates a table. |
| `ReglaTarifaInspeccionObra` | **Dead code — no migration** | Model exists in source only. No migration creates a table. |
| `EspecialidadesLiquidacion` | **Model exists in migration only** | DB table exists, but no source Python class. Would fail at import time. |
| `ReglaTarifaEdificacion` | **Model exists in migration only** | DB table exists, but no source Python class. Would fail at import time. |

---

## 6. Alignment with User's Intended Catalog Separation

| User Intended Design | Current State | Alignment |
|---|---|---|
| `tarifa_base` = stable identity only, no vigency/values | `TarifaLiquidacionBase` in DB has `periodo_inicio`/`periodo_fin`; source has no vigency fields but also doesn't match DB. | **PARTIALLY ALIGNED** — Source is cleaner but DB still has period columns. Need migration to remove from DB, or trust `makemigrations`. |
| Vigency in detail/value tables | `TarifaPorMetroCuadrado`, `TarifaPorCategoriaVisitas`, `TarifaPorcentajeObra` have no `periodo_inicio`/`periodo_fin` fields. The M2M `especialidades` from migration `0014` is the only period-ish thing. | **NOT ALIGNED** — The period columns were put on `TarifaLiquidacionBase` (in DB), not on detail tables. Detail tables have no vigency. |
| Specialty applicability separate from tariff values | `EspecialidadesLiquidacion` (M2M on `TarifaLiquidacionBase`) exists in DB but is missing in source. The user's intent suggests a separate bridge table. | **PARTIALLY ALIGNED** — The concept exists (M2M on base), but is missing from source and the design may want it as a separate bridge, not directly on base. |
| Percentage specialty percentages separate from m2 and visit categories | `TarifaPorcentajeObra` is separate from `TarifaPorMetroCuadrado` and `TarifaPorCategoriaVisitas`. `LiquidacionPorcentajeObra`, `LiquidacionPorMetroCuadrado`, `LiquidacionPorCategoriaVisitas` are separate calculation models. | **WELL ALIGNED** — The separation is clean. The issue is field-level drift (derecho_min/max mixing). |
| Minimum rights should be periodized value tables | `TarifaPorcentajeObra` has `derecho_minimo`/`derecho_maximo` as direct fields (not periodized). `DerechoMinimoPorcentajeObra` exists in source but has no DB table. | **NOT ALIGNED** — Currently minimum rights are hardcoded per tariff row, not periodized. The `DerechoMinimoPorcentajeObra` model (dead code) was the right direction. |

---

## 7. Ignore for Now (Frontend/Controllers/Import Cleanup)

These are **explicitly out of scope** for this phase per user instruction:

- Any frontend React/TypeScript components under `frontend/`
- API serializers under `presentation/schemas/`
- Controllers under `presentation/controllers/`
- Import/export utilities (the user says these are "expected to be deleted later")
- `management/commands/` seed scripts (seed data is temporary)
- Any frontend-specific naming or bad practices

---

## 8. Decisions Needed Before Apply

The following decisions must be resolved before `sdd-spec` / `sdd-design` can proceed:

1. **`EspecialidadesLiquidacion` and `ReglaTarifaEdificacion` — write source class or remove from re-exports?**  
   These models have DB tables (migrations exist) but no source Python class. The `__init__.py` re-exports will fail at import time. Either write the model classes to match the migration schemas, or remove them from all re-exports.

2. **`TarifaLiquidacionBase` period columns — remove from DB or keep?**  
   The user's intended architecture says vigency belongs in a separate value table, not on `TarifaLiquidacionBase` itself. This means `periodo_inicio`/`periodo_fin` should be removed from `TarifaLiquidacionBase` and migrated to a `TarifaValor` table. Decision needed: proceed with removing these columns or keep them for now.

3. **`LiquidacionPorcentajeObra` field rename — `valor_proyecto`/`valor_base_calculo` (DB) vs. `valor_declarado` (source)?**  
   The DB has different column names than the source model. One must be renamed to match the other. Recommend adopting source naming (`valor_declarado`) and writing a rename migration.

4. **`LiquidacionPorMetroCuadrado` — `derecho` field (DB) and `visitas_base_calculo` (DB, wrong table)?**  
   `0024` migration added `derecho` to the M2 table (probably correct) but also added `visitas_base_calculo` to the M2 table (wrong — should only be on visitas table). Need to verify intent and fix.

5. **`LiquidacionEdificacionProxy` — write the proxy class definition?**  
   The proxy model exists in migration `0017` but is not defined in any source `.py` file. Write it in `liquidacion_edificaciones.py`.

6. **`periodo_incio` typo — rename to `periodo_inicio`?**  
   The typo is consistent across source and all migrations. Safe to rename via migration. Confirm: yes.

7. **`CategoriaDelegado` enum vs `TipoLiquidacion` — consolidate?**  
   The delegate's category uses a parallel enum that maps 1:1 to `TipoLiquidacion`. Either deprecate `CategoriaDelegado` or document why it's distinct.

8. **`TarifaPorcentajeObra.tarifa_base` nullable — accept or enforce non-null?**  
   The `null=True` on the `tarifa_base` OneToOneField creates orphan rows and weakens the unique constraint on `ReglaTarifaEdificacion`. Decide: make it non-nullable (requires data migration to fill nulls first) or keep nullable.

---

## 9. Risk Summary

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Runtime `ImportError`** on any code path that imports `EspecialidadesLiquidacion`, `ReglaTarifaEdificacion`, or `LiquidacionEdificacionProxy` | **HIGH** | App fails to start | Write missing model class definitions or remove from re-exports |
| **Django `makemigrations` generates destructive migration** removing DB columns that are actually in use | **HIGH** | Data loss of `periodo_inicio`/`periodo_fin` on `TarifaLiquidacionBase`, M2M `especialidades`, `valor_proyecto`/`valor_base_calculo` columns | Review `TarifaLiquidacionBase` and `LiquidacionPorcentajeObra` source vs. DB shape before running `makemigrations` |
| **`LiquidacionGeneralCodigo` — app crashes on migrate** | **HIGH** | Model exists with no table | Write migration for it or delete the model |
| **Field name mismatch** causes calculation service to read wrong column | **MEDIUM** | Wrong liquidation amounts computed | Align `LiquidacionPorcentajeObra` DB columns with source fields |
| **`__str__` on `LiquidacionDelegado` references non-existent field** | **LOW** | Admin/preview shows `LiquidacionDelegado` object instead of readable string | Fix `__str__` method |
| **`TarifaPorMetroCuadrado.__str__` references non-existent `derecho_minimo`** | **LOW** | Admin/preview crashes for tariff objects | Fix `__str__` method |

---

## 10. Migration Sequence Notes (for reference)

```
0001 — Initial
0002 — LiquidacionEdificaciones, Delegados
0003 — HistoricalPeriodoDelegado
0004-0006 — Tipo on DelegadoMunicipalidad
0007-0009 — Expediente, cleanups
0010 — Move valor fields to LiquidacionEdificaciones
0011 — Require valor_base_calculo
0012 — Uppercase status
0013 — Data migrate status
0014 — CREATE: TarifaPorcentajeObra, TarifaLiquidacionBase(+FK→TarifaPorcentajeObra), EspecialidadesLiquidacion, LiquidacionPorcentajeObra, LiquidacionProyectista
0015 — Clean numero_revision
0016 — Remove revisiones M2M
0017 — Recreate LiquidacionEdificacion (singular), LiquidacionEdificacionProxy, delete old plural form
0018 — REVERSE: Remove FK tarifa_porcentaje from TarifaLiquidacionBase; Add OneToOne tarifa_base to TarifaPorcentajeObra
0019 — Delete LiquidacionSnapshot
0020 — CREATE: ReglaTarifaEdificacion (with FK → TarifaLiquidacionBase)
0021 — Add entidad snapshot fields to Proyecto
0022 — (MISSING FILE — check actual migration sequence)
0023 — Fix tipo_liquidacion choices (was wrong in 0014 — used TipoTramiteEdificaciones choices instead of TipoLiquidacion)
0024 — Add derecho + visitas_base_calculo to LiquidacionPorMetroCuadrado and LiquidacionPorCategoriaVisitas
```
**Note**: Migration 0022 file (`0022_alter_historicalperiododelegado_periodo_fin_and_more.py`) is missing from the filesystem — its absence may indicate an uncommitted or renamed migration.

---

*Exploration artifact — `liquidaciones-tablas-consistencia` change — SDD Explore phase*
