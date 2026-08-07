# SDD Explore: liquidaciones-modelado-objetivo

## Status
success

## Executive Summary
Audited all liquidaciones domain models (24 tables/classes). Found 6 must-fix bugs, 5 design violations against stated architecture intent, 4 orphaned/dead tables, and 3 missing tables that block services/endpoints. The main structural problem is `TarifaLiquidacionBase` storing `tipo_liquidacion` as a CharField instead of being the identity header with a proper FK to a `TipoLiquidacion` catalog. Also found `periodo_incio` typo, a broken `__str__`, and missing periodized minimum-right tables without FKs to tariff base.

## Model/Table Inventory

### 1. General Entity / Core Tables

| # | Model/Table | File | Architecture | Notes |
|---|-------------|-------|--------------|-------|
| 1 | `LiquidacionGeneral` | `liquidacion/liquidacion.py` | Core entity | Main liquidation record. Has `periodo_incio` typo (should be `periodo_inicio`). Has snapshots of IGV/UIT. Has self-referencing M2M for `liquidaciones_previas` (unclear purpose). |
| 2 | `LiquidacionGeneralCodigo` | `liquidacion/liquidacion.py` | **ORPHAN** | Defined but no FK anywhere points to it. Should be deleted or wired. |
| 3 | `LiquidacionContacto` | `liquidacion/liquidacion.py` | Bridge table | Links Liquidacion to Contacto. `unique_together` constraint present. OK. |
| 4 | `LiquidacionDocumentos` | `liquidacion/liquidacion.py` | **ORPHAN** | No FK from any model points to it. Should be deleted. |
| 5 | `LiquidacionProyectista` | `liquidacion/liquidacion.py` | Bridge table | Links LiquidacionGeneral to Proyectista. Has unique constraint. OK. |
| 6 | `LiquidacionEspecialidadDisponibles` | `liquidacion/liquidacion.py` | Bridge table | Links LiquidacionGeneral to Especialidad. Lacks metadata fields (`aplica_por_defecto`, `obligatoria`, `orden`, `activo`) the user wants for `TipoLiquidacionEspecialidad`. |
| 7 | `LiquidacionTarifaAplicada` | `liquidacion/liquidacion.py` | Bridge table | Links LiquidacionGeneral to TarifaLiquidacionBase. OK structurally. |

### 2. Tariff Catalog Tables

| # | Model/Table | File | Architecture | Notes |
|---|-------------|-------|--------------|-------|
| 8 | `TarifaLiquidacionBase` | `liquidacion/tarifas_reglas.py` | **Design violation** | Stores `tipo_liquidacion` as CharField(choices) instead of FK to `TipoLiquidacion` catalog. This is the root of the modeling problem — it should be the stable identity header. |
| 9 | `TarifaPorcentajeObra` | `liquidacion/tarifas_reglas.py` | Tariff detail | OneToOne to `TarifaLiquidacionBase`. Has `null=True` on FK temporarily. Contains percentage and derecho_minimo/maximo. Missing periodization. |
| 10 | `TarifaPorMetroCuadrado` | `liquidacion/tarifas_reglas.py` | Tariff detail | OneToOne to `TarifaLiquidacionBase`. Has `costo_por_m2` and `area_m2`. |
| 11 | `TarifaPorCategoriaVisitas` | `liquidacion/tarifas_reglas.py` | Tariff detail | OneToOne to `TarifaLiquidacionBase`. Has `costo_por_visita` and `visitas_minimas`. |
| 12 | `DerechoMinimoPorcentajeObra` | `liquidacion/tarifas_reglas.py` | **ORPHAN** | Has `periodo_inicio`/`periodo_fin` for periodization but NO FK to `TarifaLiquidacionBase`. Dead table. |
| 13 | `DerechoMinimoPorMetroCuadrado` | `liquidacion/tarifas_reglas.py` | **ORPHAN** | Same issue — NO FK to `TarifaLiquidacionBase`. Dead table. |

### 3. Percentage-of-Work (Obra) Tables

| # | Model/Table | File | Architecture | Notes |
|---|-------------|-------|--------------|-------|
| 14 | `LiquidacionPorcentajeObra` | `liquidacion/liquidacion_tipo.py` | Calculation result | FK to LiquidacionGeneral. Stores `valor_declarado`, `porcentaje_liquidacion`, `derecho_minimo`, `derecho_maximo`, `porcentaje_minimo_uit`. **Stores applied values, not references to TarifaPorcentajeObra** — cannot audit which tariff row was used. |

### 4. m² Tables (Habilitación Urbana, Mecánica Suelos, Impacto Vial, Taludes)

| # | Model/Table | File | Architecture | Notes |
|---|-------------|-------|--------------|-------|
| 15 | `LiquidacionPorMetroCuadrado` | `liquidacion/liquidacion_tipo.py` | Calculation result | FK to LiquidacionGeneral. Stores `area_m2`, `costo_por_m2`, `derecho_minimo`, `derecho_maximo`. Stores applied values, not references to TarifaPorMetroCuadrado. |
| 16 | `LiquidacionHabilitacionUrbana` | `liquidacion/liquidacion_habilitacion_urbana.py` | OneToOne extension | OneToOne to LiquidacionGeneral. Has its own `numero` field (redundant with `LiquidacionGeneral.numero_revision`). |
| 17 | `LiquidacionMecanicaSuelos` | `liquidacion/liquidacion_mecanica_suelos.py` | OneToOne extension | Same pattern as above. |
| 18 | `LiquidacionImpactoVial` | `liquidacion/liquidacion_impacto_vial.py` | OneToOne extension | Same pattern. |
| 19 | `LiquidacionTaludes` | `liquidacion/liquidacion_taludes.py` | OneToOne extension | Same pattern. |

### 5. Visit/Inspection Tables

| # | Model/Table | File | Architecture | Notes |
|---|-------------|-------|--------------|-------|
| 20 | `LiquidacionPorCategoriaVisitas` | `liquidacion/liquidacion_tipo.py` | Calculation result | FK to LiquidacionGeneral. Stores `cantidad_visitas`, `porcentaje_uit`, `categoria`. |
| 21 | `LiquidacionInspeccionObra` | `liquidacion/liquidacion_inspeccion_obra.py` | OneToOne extension | OneToOne to LiquidacionGeneral. Has `numero` field. |

### 6. Specialty/Delegate/Supervisor Tables

| # | Model/Table | File | Architecture | Notes |
|---|-------------|-------|--------------|-------|
| 22 | `LiquidacionEdificacion` | `liquidacion/liquidacion_edificaciones.py` | OneToOne extension | OneToOne to LiquidacionGeneral. Has `numero` and `tipo_tramite`. |
| 23 | `Delegado` | `delegado.py` | Delegate entity | FK to PerfilIngeniero. OK. |
| 24 | `DelegadoMunicipalidad` | `delegado.py` | Delegate-Municipalidad link | FK to Delegado and Municipalidad. Has `tipo` and `categoria`. |
| 25 | `DelegadoMunicipalidadPeriodo` | `delegado.py` | Period for Delegate-Municipalidad | FK to DelegadoMunicipalidad. Has `periodo_inicio`/`periodo_fin`. Orphan (no parent points to it from DelegadoMunicipalidad's reverse). |
| 26 | `LiquidacionDelegado` | `liquidacion_delegado.py` | Liquidacion-Delegate bridge | **BUG: `__str__` references `self.perfil_ingeniero` which does not exist on this model** — should be `self.delegado.perfil_ingeniero`. |

### 7. Project Tables (cross-domain FK targets)

| # | Model/Table | File | Architecture | Notes |
|---|-------------|-------|--------------|-------|
| 27 | `Proyecto` | `proyecto.py` | Project entity | FK to Entidad. Has denormalized entity snapshots. Proxy models for empresarial/persona natural. OK. |
| 28 | `ProyectoEmpresarial` | `proyecto.py` | Proxy of Proyecto | OK. |
| 29 | `ProyectoPersonaNatural` | `proyecto.py` | Proxy of Proyecto | OK. |

### 8. External Shared Catalog

| # | Model/Table | Location | Architecture | Notes |
|---|-------------|----------|--------------|-------|
| 30 | `Especialidad` | `usuarios.PerfilIngeniero` | Shared catalog | Defined in usuarios module, imported into liquidaciones. Has `codigo`, `nombre`. This is the right place for it. |

---

## Findings Table

| Severity | Current Model/Table/Field | Evidence | Why It Matters | Recommended Direction |
|----------|---------------------------|----------|----------------|----------------------|
| 🔴 Critical | `LiquidacionDelegado.__str__` | `return f"{self.perfil_ingeniero}..."` — field does not exist | Runtime AttributeError when Django renders this object string | Fix: `self.delegado.perfil_ingeniero.nombre_completo` |
| 🔴 Critical | `DerechoMinimoPorcentajeObra` | No FK to `TarifaLiquidacionBase` | Orphan table. Periodized minimums have no connection to the tariff they belong to. Cannot be queried by tariff. | Add `tarifa_base = ForeignKey(TarifaLiquidacionBase)` or delete if not needed |
| 🔴 Critical | `DerechoMinimoPorMetroCuadrado` | No FK to `TarifaLiquidacionBase` | Same orphan issue as above | Same fix |
| 🔴 Critical | `LiquidacionGeneralCodigo` | No FK from any model | Dead/orphan table. Cannot be used. | Delete unless used via undocumented path |
| 🔴 High | `LiquidacionGeneral.periodo_incio` | Typo: `periodo_incio` | Field name is misspelled (`incio` vs `inicio`). Will cause bugs in services that try to use the correctly-spelled field. | Rename to `periodo_inicio` |
| 🔴 High | `TarifaLiquidacionBase.tipo_liquidacion` | CharField with choices instead of FK | Violates design intent #1: tariff catalog should be separated from applied history. `tipo_liquidacion` is a CharField choice, not a relation. No table for `TipoLiquidacion` catalog itself. | Create `TipoLiquidacion` as a proper catalog model/table, add FK from `TarifaLiquidacionBase` |
| 🔴 High | `TarifaPorcentajeObra.tarifa_base` | `null=True, blank=True` | Allows TarifaPorcentajeObra rows without a TarifaLiquidacionBase parent. Data integrity issue. | Remove null=True once migration is stable |
| 🟡 Medium | `LiquidacionEspecialidadDisponibles` | Missing metadata fields | User wants `aplica_por_defecto`, `obligatoria`, `orden`, `activo` on `TipoLiquidacionEspecialidad` (the through table for specialty↔tariff-type). This model links liquidation↔specialty, not tariff-type↔specialty. | Create proper `TipoLiquidacionEspecialidad` with FK to `TipoLiquidacion` and FK to `Especialidad`, with metadata fields |
| 🟡 Medium | `LiquidacionPorcentajeObra` | Stores applied values, not FK to `TarifaPorcentajeObra` | Cannot audit which tariff row was applied. If tariff changes, historical record is opaque. | Add FK to `TarifaPorcentajeObra` as `tarifa_aplicada` |
| 🟡 Medium | `LiquidacionPorMetroCuadrado` | Same — stores applied values | Same audit problem as above | Add FK to `TarifaPorMetroCuadrado` |
| 🟡 Medium | `LiquidacionPorCategoriaVisitas` | Same | Same audit problem | Add FK to `TarifaPorCategoriaVisitas` |
| 🟡 Medium | OneToOne extension tables (`LiquidacionEdificacion`, `LiquidacionHabilitacionUrbana`, etc.) | Each has `numero` field | Redundant with `LiquidacionGeneral.numero_revision` — which is one per liquidation, not one per type extension. If a single liquidation goes through multiple types, which `numero` wins? | Deprecate `numero` field in extensions, use `LiquidacionGeneral.numero_revision` only |
| 🟡 Medium | `LiquidacionDocumentos` | No FK from anywhere | Orphan — cannot be reached from ORM | Delete |
| 🟡 Medium | `LiquidacionDelegado.periodo` | `CharField` with max_length=100 | Period stored as free-text string instead of date range. Cannot query by date range. | Replace with FK to a period table, or use `periodo_inicio`/`periodo_fin` dates |
| 🟡 Medium | `DelegadoMunicipalidadPeriodo` | Orphan — no reverse FK from `DelegadoMunicipalidad` | The `periodos` reverse relation exists but nothing populates it because the child model has no parent pointer wired from the parent | Wire it: ensure service layer creates `DelegadoMunicipalidadPeriodo` records; currently the model exists but is unused |
| 🟢 Low | `LiquidacionGeneralCodigo` | Has no relations | Dead code | Delete |
| 🟢 Low | Naming inconsistency | `LiquidacionPorMetroCuadrado` vs `TarifaPorCategoriaVisitas` | Some use Spanish plural, some English singular | Not critical but should standardize |
| 🟢 Low | `TarifaLiquidacionBase` direction | OneToOne from child tariff → base | The design intent (#3) says "tarifa_base is a stable identity/concept/header only". But the FK direction is child→parent. Actually this is correct — the child details (m2, percentage) point to the header. However the header lacks `nombre` or descriptive fields to be a real identity header. | Add `nombre`, `descripcion`, and `activo` fields to `TarifaLiquidacionBase` |

---

## Proposed Canonical Names

| Current Name | Proposed Name | Reason |
|-------------|--------------|--------|
| `TarifaLiquidacionBase` | Keep (rename `tipo_liquidacion` FK field to `tipo_liquidacion`) | Good name, header concept is right |
| `TarifaPorcentajeObra` | Keep | Good name |
| `TarifaPorMetroCuadrado` | Keep | Good name |
| `TarifaPorCategoriaVisitas` | Keep | Good name |
| `LiquidacionPorMetroCuadrado` | Keep | Good name |
| `LiquidacionPorCategoriaVisitas` | Keep | Good name |
| `LiquidacionPorcentajeObra` | Keep | Good name |
| `LiquidacionEspecialidadDisponibles` | `LiquidacionEspecialidad` or merge into `TipoLiquidacionEspecialidad` | The "Disponibles" suffix is awkward; this may become the specialty link at liquidation creation time |
| `LiquidacionDelegado` | Keep | OK, explicit bridge name |
| `DelegadoMunicipalidadPeriodo` | Keep | OK |
| `periodo_incio` (in LiquidacionGeneral) | `periodo_inicio` | Typo fix |

---

## Clean Target Diagram (Model Layer Only)

```
CATALOG / CONFIGURATION TABLES
═══════════════════════════════

Especialidad (from usuarios — shared catalog)
  └── codigo, nombre

TipoLiquidacion [NEW — needs to be created as FK target]
  └── nombre, codigo, activo, descripcion

TarifaLiquidacionBase [REFACTOR: tipo_liquidacion → FK to TipoLiquidacion]
  └── tipo_liquidacion (FK → TipoLiquidacion)  ← currently CharField choices
  └── nombre, descripcion, activo

TarifaPorcentajeObra
  └── tarifa_base (FK → TarifaLiquidacionBase, 1:1)
  └── porcentaje_liquidacion, derecho_minimo, derecho_maximo, porcentaje_minimo_uit

DerechoMinimoPorcentajeObra [REFACTOR: add FK to TarifaLiquidacionBase]
  └── tarifa_base (FK → TarifaLiquidacionBase)  ← MISSING, needs to be added
  └── derecho_minimo, porcentaje_minimo_uit, periodo_inicio, periodo_fin

TarifaPorMetroCuadrado
  └── tarifa_base (FK → TarifaLiquidacionBase, 1:1)
  └── costo_por_m2, area_m2

DerechoMinimoPorMetroCuadrado [REFACTOR: add FK to TarifaLiquidacionBase]
  └── tarifa_base (FK → TarifaLiquidacionBase)  ← MISSING, needs to be added
  └── derecho_minimo, derecho_maximo, periodo_inicio, periodo_fin

TarifaPorCategoriaVisitas
  └── tarifa_base (FK → TarifaLiquidacionBase, 1:1)
  └── costo_por_visita, visitas_minimas

TipoLiquidacionEspecialidad [NEW — explicit through table with metadata]
  └── tipo_liquidacion (FK → TipoLiquidacion)
  └── especialidad (FK → Especialidad)
  └── aplica_por_defecto, obligatoria, orden, activo

Delegado
  └── perfil_ingeniero (FK → PerfilIngeniero)

DelegadoMunicipalidad
  └── delegado (FK → Delegado)
  └── municipalidad (FK → Municipalidad)
  └── tipo, categoria

DelegadoMunicipalidadPeriodo
  └── delegado_municipalidad (FK → DelegadoMunicipalidad)
  └── periodo_inicio, periodo_fin

Proyecto
  └── entidad (FK → Entidad)
  └── entidad_razon_social, entidad_tipo_documento, entidad_numero_documento (denormalized snapshots)
  └── nombre_propietario, denominacion, distrito, direccion, descripcion

Proyectista
  └── perfil_ingeniero (FK → PerfilIngeniero)


ACTUAL LIQUIDATION TABLES
═════════════════════════

LiquidacionGeneral
  └── proyecto (FK → Proyecto)
  └── municipalidad (FK → Municipalidad, null)
  └── igv_id (FK → IGV), uit_id (FK → UIT)
  └── igv_snapshot, uit_snapshot
  └── estado, total, sub_total, observacion, expediente
  └── tipo_liquidacion (CharField choices — but should reference tariff)
  └── numero_revision, periodo_inicio (← typo: periodo_incio), periodo_fin
  └── liquidaciones_previas (M2M → self)

LiquidacionContacto [bridge]
  └── liquidacion (FK → LiquidacionGeneral)
  └── contacto (FK → Contacto)
  └── principal (bool)

LiquidacionProyectista [bridge]
  └── liquidacion_general (FK → LiquidacionGeneral)
  └── proyectista (FK → Proyectista)

LiquidacionDelegado [bridge]
  └── liquidacion (FK → LiquidacionGeneral)
  └── delegado (FK → Delegado)
  └── periodo (CharField — should be date range), dictamen_revision, fecha_presentacion, fecha_revision

LiquidacionTarifaAplicada [bridge]
  └── liquidacion_general (FK → LiquidacionGeneral)
  └── tarifa_aplicada (FK → TarifaLiquidacionBase)

LiquidacionEdificacion [OneToOne extension]
  └── liquidacion (FK → LiquidacionGeneral, 1:1)
  └── numero, tipo_tramite

LiquidacionHabilitacionUrbana [OneTo1 extension]
  └── liquidacion (FK → LiquidacionGeneral, 1:1)
  └── numero  ← redundant with LiquidacionGeneral.numero_revision

LiquidacionMecanicaSuelos [OneTo1 extension]
  └── liquidacion (FK → LiquidacionGeneral, 1:1)
  └── numero  ← redundant

LiquidacionImpactoVial [OneTo1 extension]
  └── liquidacion (FK → LiquidacionGeneral, 1:1)
  └── numero  ← redundant

LiquidacionTaludes [OneTo1 extension]
  └── liquidacion (FK → LiquidacionGeneral, 1:1)
  └── numero  ← redundant

LiquidacionInspeccionObra [OneTo1 extension]
  └── liquidacion (FK → LiquidacionGeneral, 1:1)
  └── numero  ← redundant


CALCULATION RESULT TABLES (applied, reference tariff rows)
══════════════════════════════════════════════════════

LiquidacionPorcentajeObra [REFACTOR: add FK to TarifaPorcentajeObra]
  └── liquidacion_general (FK → LiquidacionGeneral)
  └── valor_declarado, porcentaje_liquidacion, derecho_minimo, derecho_maximo, porcentaje_minimo_uit
  └── tarifa_porcentaje (FK → TarifaPorcentajeObra)  ← MISSING, add for auditability

LiquidacionPorMetroCuadrado [REFACTOR: add FK to TarifaPorMetroCuadrado]
  └── liquidacion_general (FK → LiquidacionGeneral)
  └── area_m2, costo_por_m2, derecho_minimo, derecho_maximo
  └── tarifa_m2 (FK → TarifaPorMetroCuadrado)  ← MISSING

LiquidacionPorCategoriaVisitas [REFACTOR: add FK to TarifaPorCategoriaVisitas]
  └── liquidacion_general (FK → LiquidacionGeneral)
  └── cantidad_visitas, porcentaje_uit, categoria
  └── tarifa_visitas (FK → TarifaPorCategoriaVisitas)  ← MISSING


FUTURE / NOT NOW
════════════════

LiquidacionEspecialidadDisponibles — will be superseded by TipoLiquidacionEspecialidad
  (currently links LiquidacionGeneral → Especialidad — needed at creation time,
   but the tariff↔specialty link is TipoLiquidacionEspecialidad)
```

---

## Must-Fix Before Services/Endpoints Checklist

### Bugs (must fix immediately)
- [ ] `periodo_incio` → rename to `periodo_inicio` in `LiquidacionGeneral`
- [ ] Fix `LiquidacionDelegado.__str__` — change `self.perfil_ingeniero` to `self.delegado.perfil_ingeniero.nombre_completo`
- [ ] Add `tarifa_base = ForeignKey(TarifaLiquidacionBase)` to `DerechoMinimoPorcentajeObra` OR delete if not needed
- [ ] Add `tarifa_base = ForeignKey(TarifaLiquidacionBase)` to `DerechoMinimoPorMetroCuadrado` OR delete if not needed
- [ ] Verify `LiquidacionGeneralCodigo` is truly orphan; delete if no FK points to it
- [ ] Verify `LiquidacionDocumentos` is truly orphan; delete if no FK points to it

### Design corrections (before building services)
- [ ] Create `TipoLiquidacion` catalog table and change `TarifaLiquidacionBase.tipo_liquidacion` from CharField to FK
- [ ] Add `nombre`, `descripcion`, `activo` fields to `TarifaLiquidacionBase` to make it a proper identity header
- [ ] Create `TipoLiquidacionEspecialidad` through table with FK to `TipoLiquidacion`, FK to `Especialidad`, and fields: `aplica_por_defecto`, `obligatoria`, `orden`, `activo`
- [ ] Add `tarifa_porcentaje = ForeignKey(TarifaPorcentajeObra)` to `LiquidacionPorcentajeObra` for auditability
- [ ] Add `tarifa_m2 = ForeignKey(TarifaPorMetroCuadrado)` to `LiquidacionPorMetroCuadrado` for auditability
- [ ] Add `tarifa_visitas = ForeignKey(TarifaPorCategoriaVisitas)` to `LiquidacionPorCategoriaVisitas` for auditability
- [ ] Remove `null=True` from `TarifaPorcentajeObra.tarifa_base` once data is stable
- [ ] `LiquidacionDelegado.periodo` (CharField) → replace with proper date FK or `DelegadoMunicipalidadPeriodo` reference

### Cleanup (can do in same pass)
- [ ] Delete `LiquidacionGeneralCodigo` (orphan)
- [ ] Delete `LiquidacionDocumentos` (orphan)
- [ ] Remove redundant `numero` field from all OneToOne extension tables (`LiquidacionEdificacion`, `LiquidacionHabilitacionUrbana`, `LiquidacionMecanicaSuelos`, `LiquidacionImpactoVial`, `LiquidacionTaludes`, `LiquidacionInspeccionObra`) — use `LiquidacionGeneral.numero_revision` instead
- [ ] Wire `DelegadoMunicipalidadPeriodo` into service layer or mark for deletion if genuinely unused

---

## Can Ignore/Delete Because Old History Is Irrelevant

These tables/models are dead weight from the old alpha/betha schema and should be deleted without preservation concern:

| Model/Table | Reason to Delete |
|-------------|------------------|
| `LiquidacionGeneralCodigo` | No relations. Dead code. |
| `LiquidacionDocumentos` | No relations. Dead code. |
| `DerechoMinimoPorcentajeObra` (in current form) | Orphan — no FK to `TarifaLiquidacionBase`. Redesign with proper FK or delete. |
| `DerechoMinimoPorMetroCuadrado` (in current form) | Same. Orphan without FK. |
| All `HistoricalRecords` fields in liquidaciones models | simple-history audit trail; user explicitly discarding old history. Can be removed in migration cleanup pass (but not blocking for services). |

---

## Questions for User

1. **`LiquidacionDelegado.periodo`**: Currently a free-text CharField. Should this be replaced with a date range pointing to `DelegadoMunicipalidadPeriodo`? Or is the current string-per-period pattern intentional for backward compatibility with legacy data?

2. **`DelegadoMunicipalidadPeriodo`**: Currently defined but no service creates records for it. Is it actively used, or should it be removed/deleted as dead code?

3. **`TipoLiquidacionEspecialidad` metadata**: The user wants `aplica_por_defecto`, `obligatoria`, `orden`, `activo` on the specialty↔tariff-type through table. Are there existing values for these flags, or should they default to what? (e.g., `activo=True`, `orden=0`, `obligatoria=False`, `aplica_por_defecto=False`?)

4. **`LiquidacionEspecialidadDisponibles` vs `TipoLiquidacionEspecialidad`**: Should `LiquidacionEspecialidadDisponibles` (which links a specific `LiquidacionGeneral` to `Especialidad`) be kept as the per-liquidation specialty selection, while `TipoLiquidacionEspecialidad` is the tariff-type↔specialty catalog? Or should they be merged?

5. **Minimum-right tables (`DerechoMinimoPorcentajeObra`, `DerechoMinimoPorMetroCuadrado`)**: Are these intended to be periodized value tables (with `periodo_inicio`/`periodo_fin`) that get selected by calculation date? If so, they need the FK to `TarifaLiquidacionBase` added. If not, they should be deleted.
