# Edificaciones Naming Conventions Analysis

## Executive Summary

This document catalogs ALL naming occurrences in the Edificaciones implementation where "porcentaje", "po", or "PorcentajeObra" appears vs where "edificaciones" naming appears.

**Key Finding**: The implementation has a **dual-layer naming pattern**:
- **User-facing layer**: Uses `Edificaciones` (correct, user-friendly)
- **Calculation motor layer**: Uses `PorcentajeObra` / `porcentaje` (technical, based on DB model names)

This is **intentional and consistent** with how HU (Habilitación Urbana) and MS (Mecánica de Suelos) use `PorMetroCuadrado` / `m2` as their motor names while using user-facing names like `habilitacion-urbana` and `mecanica-suelos`.

---

## 1. Naming Inventory

### 1.1 Domain Layer (Backend)

#### File: `liquidacion_porcentaje_obra_core_service.py`
| Line | Type | Name | Category |
|------|------|------|----------|
| 27 | Class | `LiquidacionPorcentajeObraCoreService` | Motor class |
| 58 | Method | `get_derecho_porcentaje_vigente()` | Service method |
| 62 | Method | `get_tarifas_porcentaje_vigentes()` | Service method |
| 73 | Method | `calcular_cotizacion_po()` | Service method |
| 173 | Method | `create_liquidacion_porcentaje_obra()` | Service method |

#### File: `liquidacion_porcentaje_data.py`
| Line | Type | Name | Category |
|------|------|------|----------|
| 13 | Class | `DatosPorcentajeObra` | Data DTO |
| 18 | Class | `TarifaPorcentajeObraAplicada` | Data DTO |
| 26 | Class | `LiquidacionPorcentajeObraData` | Data DTO |
| 36 | Class | `DetallePorcentajeObraData` | Data DTO |
| 46 | Class | `CotizacionPorcentajeObraData` | Data DTO |

#### File: `liquidacion_porcentaje_result.py`
| Line | Type | Name | Category |
|------|------|------|----------|
| 9 | Class | `DetallePorcentajeObraResult` | Result DTO |
| 21 | Class | `LiquidacionPorcentajeObraResult` | Result DTO |

#### File: `cotizacion.py`
| Line | Type | Name | Category |
|------|------|------|----------|
| 32 | Class | `CotizacionPorcentajeObraDetalleResult` | Result DTO |
| 42 | Class | `CotizacionPorcentajeObraResult` | Result DTO |

### 1.2 Domain Layer - Edificaciones Specific

#### File: `liquidacion_edificaciones.py` (ORM Model)
| Line | Type | Name | Category |
|------|------|------|----------|
| 17 | Class | `LiquidacionEdificacion` | Identity model |
| 23 | Comment | "Los valores de cálculo...viven en LiquidacionPorcentajeObra" | Documentation |

#### File: `edificaciones_primera_revision_data.py`
| Line | Type | Name | Category |
|------|------|------|----------|
| 10 | Class | `EdificacionesPrimeraRevisionData` | Data wrapper |
| 16 | Field | `liquidacion_especifica: LiquidacionPorcentajeObraData` | Composition |

#### File: `edificaciones_primera_revision_result.py`
| Line | Type | Name | Category |
|------|------|------|----------|
| 9 | Class | `LiquidacionEspecificaEdificacionesResult` | Identity result |
| 15 | Class | `EdificacionesPrimeraRevisionResult` | Result wrapper |
| 18 | Field | `liquidacion_tipo: LiquidacionPorcentajeObraResult` | Composition |

### 1.3 Presentation Layer

#### File: `porcentaje_schemas.py`
| Line | Type | Name | Category |
|------|------|------|----------|
| 13 | Class | `LiquidacionPorcentajeObraDatosIn` | Input schema |
| 18 | Class | `LiquidacionPorcentajeObraTarifaIn` | Input schema |
| 23 | Class | `LiquidacionPorcentajeObraIn` | Input schema |
| 34 | Class | `LiquidacionPorcentajeObraDetalleOut` | Output schema |
| 46 | Class | `LiquidacionPorcentajeObraDatosOut` | Output schema |

#### File: `liquidacion_edificaciones_schemas.py`
| Line | Type | Name | Category |
|------|------|------|----------|
| 2 | Comment | "Presentation schemas for Edificaciones (PorcentajeObra)" | Documentation |
| 28 | Class | `LiquidacionEdificacionesInput` | User-facing wrapper |
| 31 | Field | `liquidacion_especifica: LiquidacionPorcentajeObraIn` | Composition |
| 34 | Class | `LiquidacionEdificacionesOutput` | User-facing wrapper |
| 37 | Field | `liquidacion_especifica: LiquidacionTipoOutput` | Identity output |
| 38 | Field | `liquidacion_tipo: LiquidacionPorcentajeObraDatosOut` | Motor output |
| 41 | Class | `LiquidacionEdificacionesCotizarInput` | Cotizar input |
| 47 | Field | `liquidacion_especifica: LiquidacionPorcentajeObraIn` | Composition |
| 50 | Class | `LiquidacionEdificacionesCotizarTarifaOut` | Tarifa output |
| 57 | Class | `LiquidacionEdificacionesCotizarDetalleOut` | Detalle output |
| 67 | Class | `LiquidacionEdificacionesCotizarOutput` | Cotizar output |

#### File: `liquidacion_edificaciones_presenter.py`
| Line | Type | Name | Category |
|------|------|------|----------|
| 2 | Comment | "Presenter for Edificaciones (PorcentajeObra)" | Documentation |
| 28 | Method | `present_primera_revision()` | Maps to PO result |

#### File: `liquidacion_edificaciones_controller.py`
| Line | Type | Name | Category |
|------|------|------|----------|
| 2 | Comment | "HTTP Controller for Edificaciones (PorcentajeObra)" | Documentation |
| 33 | Route | `/liquidaciones/edificaciones` | User-facing URL |
| 36 | Class | `LiquidacionEdificacionesController` | Controller class |
| 55 | Method | `get_tarifas_vigentes()` | Endpoint |
| 101 | Variable | `tarifa_porcentaje_obra_id` | Field name |

### 1.4 Service Injection (Flujo)

#### File: `liquidacion_edificaciones_flujo.py`
| Line | Type | Name | Category |
|------|------|------|----------|
| 2 | Comment | "Flujo for Edificaciones (PorcentajeObra)" | Documentation |
| 39 | Class | `LiquidacionEdificacionesFlujo` | User-facing class |
| 56 | Variable | `porcentaje_core: LiquidacionPorcentajeObraCoreService` | Motor injection |
| 59 | Variable | `self.porcentaje_core` | Motor instance |

#### File: `liquidacion_edificaciones_orchestrator.py`
| Line | Type | Name | Category |
|------|------|------|----------|
| 2 | Comment | "Orchestrator for Edificaciones (PorcentajeObra)" | Documentation |
| 46 | Class | `LiquidacionEdificacionesOrchestrator` | User-facing class |
| 77 | Variable | `porcentaje_core_service: LiquidacionPorcentajeObraCoreService` | Motor injection |
| 81 | Variable | `self.porcentaje_core` | Motor instance |
| 107 | Variable | `tarifa_porcentaje_obra_id` | Field name |
| 217 | Method | `calcular_cotizacion_po()` | Motor call |

### 1.5 ORM Models (Database)

#### File: Models (via imports in `domain/models/__init__.py`)
| Type | Name | Category |
|------|------|----------|
| Model | `LiquidacionPorcentajeObra` | Motor model |
| Model | `LiquidacionPorcentajeObraDetalle` | Motor model |
| Model | `TarifaPorcentajeObra` | Tarifa model |
| Model | `DerechoPorcentajeObra` | Derecho model |

### 1.6 Tests

#### File: `test_edificaciones_nueva_liquidacion.py`
| Line | Type | Name | Category |
|------|------|------|----------|
| 2 | Comment | "Edificaciones (PorcentajeObra)" | Documentation |
| 30 | Import | `TarifaPorcentajeObra` | Import |
| 31 | Import | `DerechoPorcentajeObra` | Import |
| 134 | Fixture | `tarifa_porcentaje_obra_estructuras` | Test fixture |
| 144 | Fixture | `tarifa_porcentaje_obra_arquitectura` | Test fixture |
| 154 | Fixture | `tarifa_porcentaje_obra_installaciones` | Test fixture |
| 164 | Fixture | `derecho_porcentaje_vigente` | Test fixture |
| 214 | Variable | `valid_tarifa_ids` | Test variable |
| 277 | Field | `tarifa_porcentaje_obra_id` | Field in payload |

#### File: `test_edificaciones_tarifas_vigentes.py`
| Line | Type | Name | Category |
|------|------|------|----------|
| 17 | Import | `TarifaPorcentajeObra` | Import |
| 18 | Import | `DerechoPorcentajeObra` | Import |
| 61 | Fixture | `tarifa_porcentaje_obra_estructuras` | Test fixture |
| 71 | Fixture | `tarifa_porcentaje_obra_arquitectura` | Test fixture |
| 81 | Fixture | `tarifa_porcentaje_obra_installaciones` | Test fixture |
| 91 | Fixture | `derecho_porcentaje_vigente` | Test fixture |

---

## 2. Categorization Table

| Category | Count | Examples |
|----------|-------|----------|
| **Class names with "PorcentajeObra"** | 16 | `LiquidacionPorcentajeObraCoreService`, `LiquidacionPorcentajeObraResult`, `CotizacionPorcentajeObraResult` |
| **Class names with "porcentaje" (not PO)** | 6 | `DatosPorcentajeObra`, `TarifaPorcentajeObraAplicada`, `DetallePorcentajeObraData` |
| **Variable names with "porcentaje"** | 8 | `porcentaje_core`, `porcentaje_liquidacion`, `porcentaje_minimo_uit` |
| **Field names with "porcentaje"** | 5 | `porcentaje_liquidacion`, `porcentaje_minimo_uit`, `porcentaje_aplicado` |
| **User-facing classes (Edificaciones)** | 8 | `LiquidacionEdificacion`, `LiquidacionEdificacionesFlujo`, `LiquidacionEdificacionesOrchestrator` |
| **URL/Endpoint (user-facing)** | 1 | `/liquidaciones/edificaciones` |
| **DB Models (PorcentajeObra)** | 4 | `LiquidacionPorcentajeObra`, `LiquidacionPorcentajeObraDetalle`, `TarifaPorcentajeObra` |
| **Test fixtures** | 4 | `tarifa_porcentaje_obra_*`, `derecho_porcentaje_vigente` |

---

## 3. Consistency Comparison

### 3.1 Pattern: Motor Service Variable Naming

| Concept | HU/MS Naming | Edificaciones Naming | Status |
|---------|-------------|---------------------|--------|
| Motor service class | `LiquidacionPorMetroCuadradoCoreService` | `LiquidacionPorcentajeObraCoreService` | ✅ Consistent (technical) |
| Motor variable | `m2_core` | `porcentaje_core` | ⚠️ Inconsistent - different style |
| Motor method | `calcular_cotizacion_m2()` | `calcular_cotizacion_po()` | ⚠️ Inconsistent - `m2` vs `po` abbreviation |

**Observation**: HU uses `m2_core` and `calcular_cotizacion_m2()` (abbreviated), while Edificaciones uses `porcentaje_core` and `calcular_cotizacion_po()` (also abbreviated). The abbreviations `m2` and `po` are both non-user-facing.

### 3.2 Pattern: User-Facing vs Motor Naming

| Concept | HU/MS | Edificaciones | Same? |
|---------|-------|--------------|-------|
| Identity model | `LiquidacionHabilitacionUrbana` | `LiquidacionEdificacion` | ✅ Consistent |
| Orchestrator class | `LiquidacionHabilitacionUrbanaOrchestrator` | `LiquidacionEdificacionesOrchestrator` | ✅ Consistent |
| Flujo class | `LiquidacionHabilitacionUrbanaFlujo` | `LiquidacionEdificacionesFlujo` | ✅ Consistent |
| Input schema wrapper | `LiquidacionHabilitacionUrbanaInput` | `LiquidacionEdificacionesInput` | ✅ Consistent |
| Output schema wrapper | `LiquidacionHabilitacionUrbanaOutput` | `LiquidacionEdificacionesOutput` | ✅ Consistent |
| Controller class | `LiquidacionHabilitacionUrbanaController` | `LiquidacionEdificacionesController` | ✅ Consistent |
| URL prefix | `/liquidaciones/habilitacion-urbana` | `/liquidaciones/edificaciones` | ✅ Consistent (user-facing) |
| Tag | `"Habilitación Urbana"` | `"Edificaciones"` | ✅ Consistent (user-facing) |

### 3.3 Pattern: Motor Result Naming

| Concept | HU/MS | Edificaciones | Same? |
|---------|-------|--------------|-------|
| Result class | `LiquidacionM2Result` | `LiquidacionPorcentajeObraResult` | ⚠️ Different patterns |
| Cotizacion result | `CotizacionM2Result` | `CotizacionPorcentajeObraResult` | ⚠️ Different patterns |

---

## 4. Recommendations

### 4.1 What CAN Be Renamed (Internal/Non-Breaking)

| Current | Suggested | Why | Risk |
|---------|-----------|-----|------|
| `porcentaje_core` | `po_core` | Matches `m2_core` pattern from HU/MS | Low - internal variable |
| `calcular_cotizacion_po()` | `calcular_cotizacion_po()` | Already uses `po` abbreviation | N/A |
| `self.porcentaje_core` | `self.po_core` | Internal instance variable | Low |

**Note**: Renaming `porcentaje_core` to `po_core` would align with `m2_core` naming convention used in HU/MS.

### 4.2 What CANNOT/Should NOT Be Renamed (DB Constraints)

| Name | Reason |
|------|--------|
| `LiquidacionPorcentajeObra` | Django ORM model - DB constraint |
| `LiquidacionPorcentajeObraDetalle` | Django ORM model - DB constraint |
| `TarifaPorcentajeObra` | Django ORM model - DB constraint |
| `DerechoPorcentajeObra` | Django ORM model - DB constraint |
| `porcentaje_liquidacion` | Field on ORM model |
| `porcentaje_minimo_uit` | Field on ORM model |

### 4.3 What Should Stay As-Is (User-Facing)

| Name | Reason |
|------|--------|
| `/liquidaciones/edificaciones` | User-facing URL |
| `LiquidacionEdificaciones*` | User-facing classes |
| `EdificacionesPrimeraRevisionData` | User-facing domain wrapper |
| `EdificacionesPrimeraRevisionResult` | User-facing result wrapper |
| `LiquidacionEdificacion` | Identity model (short, user-facing) |
| `tags=["Edificaciones"]` | API documentation tag |

---

## 5. Naming Pattern Analysis

### 5.1 The Dual-Layer Architecture

The codebase uses a **dual-layer naming pattern**:

```
User-Facing Layer (Edificaciones)     Motor Layer (PorcentajeObra)
────────────────────────────────────   ─────────────────────────────
LiquidacionEdificacionesOrchestrator → LiquidacionPorcentajeObraCoreService
LiquidacionEdificacionesFlujo        → LiquidacionPorcentajeObraCoreService
LiquidacionEdificacionesInput        → LiquidacionPorcentajeObraIn
LiquidacionEdificacionesOutput       → LiquidacionPorcentajeObraDatosOut
```

This is **consistent with HU/MS**:
```
User-Facing Layer (Habilitación Urbana)    Motor Layer (PorMetroCuadrado)
────────────────────────────────────────   ──────────────────────────────
LiquidacionHabilitacionUrbanaOrchestrator → LiquidacionPorMetroCuadradoCoreService
LiquidacionHabilitacionUrbanaFlujo       → LiquidacionPorMetroCuadradoCoreService
```

### 5.2 Variable Naming Inconsistency

The **only real inconsistency** is in internal variable naming:

**Current (Edificaciones)**:
```python
self.porcentaje_core = porcentaje_core_service
cotizacion = self.porcentaje_core.calcular_cotizacion_po(...)
```

**Current (HU/MS)**:
```python
self.m2_core = m2_core
cotizacion = self.m2_core.calcular_cotizacion_m2(...)
```

If you want full consistency, `porcentaje_core` should become `po_core`.

---

## 6. Field Naming

### 6.1 Fields in `LiquidacionPorcentajeObraDatosOut`

| Field Name | Type | Description |
|------------|------|-------------|
| `id` | UUID | Primary key |
| `valor_declarado` | Decimal | Total project value |
| `porcentaje_liquidacion` | Decimal | Sum of all applied tariffs |
| `tipo_tramite` | Optional[str] | NULL for now |
| `derecho_minimo` | Decimal | Minimum fee |
| `derecho_maximo` | Optional[Decimal] | Maximum fee |
| `porcentaje_minimo_uit` | Decimal | Minimum UIT percentage |
| `derecho_aplicado_id` | UUID | FK to DerechoPorcentajeObra |
| `detalles` | List[LiquidacionPorcentajeObraDetalleOut] | Per-specialty breakdown |

### 6.2 Fields in `LiquidacionPorcentajeObraDetalleOut`

| Field Name | Type | Description |
|------------|------|-------------|
| `id` | UUID | Primary key |
| `tarifa_aplicada_id` | UUID | FK to TarifaPorcentajeObra |
| `especialidad_id` | UUID | FK to Especialidad |
| `porcentaje_aplicado` | Decimal | Applied percentage |
| `subtotal` | Decimal | valor_declarado × porcentaje_aplicado |
| `igv` | Decimal | IGV on subtotal |
| `uit` | Decimal | UIT contribution |
| `total` | Decimal | subtotal + igv |

---

## 7. API Endpoints

| Method | Path | Tag | Description |
|--------|------|-----|-------------|
| GET | `/liquidaciones/edificaciones/tarifas/vigentes` | Edificaciones | Get active tariffs |
| POST | `/liquidaciones/edificaciones/cotizar` | Edificaciones | Calculate quote (no persist) |
| POST | `/liquidaciones/edificaciones/nueva-liquidacion/primera-revision` | Edificaciones | Create first revision |

---

## 8. Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| **User-facing naming** | ✅ Consistent | `Edificaciones`, `LiquidacionEdificaciones*` |
| **Motor naming** | ⚠️ Partial | `PorcentajeObra` is correct but inconsistent with `m2` |
| **Variable naming** | ⚠️ Inconsistent | `porcentaje_core` vs `m2_core` |
| **DB model naming** | ✅ Fixed | Cannot change - DB constraint |
| **URL/Endpoint naming** | ✅ Consistent | `/liquidaciones/edificaciones` |
| **Test naming** | ✅ Consistent | `test_edificaciones_*` |

### Recommendation

**Low Priority**: Consider renaming internal variable `porcentaje_core` → `po_core` to match `m2_core` pattern. This is cosmetic and low-risk but would improve consistency.

**High Priority**: None - the current naming is intentional and follows established patterns.
