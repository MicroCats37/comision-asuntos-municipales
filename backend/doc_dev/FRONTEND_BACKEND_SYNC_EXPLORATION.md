# SDD Exploration: frontend-backend-sync

## Context

The `betha` branch has a heavily refactored backend using clean architecture. The frontend code was replaced with code from `alpha` branch to provide a working UI for a demo. As a result, the frontend is desynchronized from the backend — many frontend API calls target endpoints that don't exist or return incomplete data.

## Current State Analysis

### Frontend Pages & Routes

| Route | View Component | Primary Hook | Expected Endpoint |
|-------|---------------|--------------|-------------------|
| `/liquidaciones` | `LiquidacionesGeneralesView` | `useLiquidacionesGenerales` | `GET /liquidaciones` |
| `/liquidaciones/edificaciones` | `LiquidacionesEdificacionesView` | `useLiquidacionesEdificaciones` | `GET /liquidaciones/edificaciones` |
| `/liquidaciones/edificaciones/[id]` | `LiquidacionDetalleEdificacionPage` | `useLiquidacionDetalleEdificacion` | `GET /liquidaciones/edificaciones/{id}` |
| `/liquidaciones/habilitacion-urbana` | `LiquidacionesHabilitacionUrbanaView` | `useLiquidacionesHabilitacionUrbana` | `GET /liquidaciones/habilitacion-urbana` |
| `/liquidaciones/impacto-vial` | `LiquidacionesImpactoVialView` | `useLiquidacionesImpactoVial` | `GET /liquidaciones/impacto-vial` |
| `/liquidaciones/inspeccion-obra` | `LiquidacionesInspeccionObraView` | `useLiquidacionesInspeccionObra` | `GET /liquidaciones/inspeccion-obra` |
| `/liquidaciones/mecanica-suelos` | `LiquidacionesMecanicaSuelosView` | `useLiquidacionesMecanicaSuelos` | `GET /liquidaciones/mecanica-suelos` |
| `/liquidaciones/taludes` | `LiquidacionesTaludesView` | `useLiquidacionesTaludes` | `GET /liquidaciones/taludes` |
| `/proyectos` | `ProyectosView` | `useProyecto` | `GET /api/proyectos/` |

### Macro Components Used by Pages

**Edificaciones page (`LiquidacionesEdificacionesView`):**
- `LiquidacionGeneralCard` — displays liquidacion summary cards
- `LiquidacionEdificacionesSingleFormModal` — create new liquidacion (stepper form)
- `NuevaRevisionEdificacionesFormModal` — create new revision
- `ConsultarIngenieroDialog` — dialog to consult an engineer

**Form Modals contain:**
- `CotizacionSection` — shows quote calculation
- `DatosDelProyectoSection` — project data entry
- `ContactosSection` — contact management
- `RevisionesVigentesTable` — displays current vigente tarifas
- `DelegadosSection` — manages delegates
- `InspectoresSection` — manages inspectors

### Backend API Inventory

**Registered Controllers (`config/api.py`):**
- `LiquidacionEdificacionesController` — `/liquidaciones/edificaciones`
- `LiquidacionHabilitacionUrbanaController` — `/liquidaciones/habilitacion-urbana`
- `LiquidacionInspeccionObraController` — `/liquidaciones/inspeccion-obra`
- `LiquidacionMecanicaSuelosController` — `/liquidaciones/mecanica-suelos`
- `LiquidacionImpactoVialController` — `/liquidaciones/impacto-vial`
- `LiquidacionTaludesController` — `/liquidaciones/taludes`
- `FinanzasController` — `/finanzas` (PENDING)
- `EntidadesController` — `/entidades`
- `ConsultaController` — `/entidades`
- `IngenieroHabilitadoController` — `/ingenieros`
- `AuthLoginController` — `/auth/login`

**Each Liquidacion Controller ONLY exposes:**
- `GET /tarifas/vigentes` — fetch current tariffs
- `POST /nueva-liquidacion/primera-revision` — create first revision
- `POST /cotizar` — calculate quote without persisting

### Critical API Gaps

#### 1. List Endpoints — ALL MISSING

| Frontend Expects | Backend Has |
|------------------|-------------|
| `GET /liquidaciones/edificaciones` | ❌ NOT FOUND |
| `GET /liquidaciones/habilitacion-urbana` | ❌ NOT FOUND |
| `GET /liquidaciones/impacto-vial` | ❌ NOT FOUND |
| `GET /liquidaciones/inspeccion-obra` | ❌ NOT FOUND |
| `GET /liquidaciones/mecanica-suelos` | ❌ NOT FOUND |
| `GET /liquidaciones/taludes` | ❌ NOT FOUND |
| `GET /liquidaciones` (generales) | ❌ NOT FOUND |

#### 2. Detail Endpoints — ALL MISSING

| Frontend Expects | Backend Has |
|------------------|-------------|
| `GET /liquidaciones/edificaciones/{id}` | ❌ NOT FOUND |
| `GET /liquidaciones/habilitacion-urbana/{id}` | ❌ NOT FOUND |
| `GET /liquidaciones/impacto-vial/{id}` | ❌ NOT FOUND |
| `GET /liquidaciones/inspeccion-obra/{id}` | ❌ NOT FOUND |
| `GET /liquidaciones/mecanica-suelos/{id}` | ❌ NOT FOUND |
| `GET /liquidaciones/taludes/{id}` | ❌ NOT FOUND |

#### 3. Path Mismatch for Primera Revision

| Frontend Calls | Backend Has |
|----------------|-------------|
| `POST /liquidaciones/edificaciones/primera-revision` | `POST /liquidaciones/edificaciones/nueva-liquidacion/primera-revision` |

The frontend sends `{ liquidacion: payload }` wrapper but backend expects flat payload.

#### 4. Cotizar Endpoints — ALL MISSING

| Frontend Expects | Backend Has |
|------------------|-------------|
| `POST /liquidaciones/edificaciones/cotizar/primera-revision` | ❌ NOT FOUND |
| `POST /liquidaciones/edificaciones/cotizar/nueva-revision` | ❌ NOT FOUND |
| `GET /liquidaciones/edificaciones/nueva-revision/formulario` | ❌ NOT FOUND |
| `POST /liquidaciones/edificaciones/nueva-revision` | ❌ NOT FOUND |

#### 5. Delegados API — MISSING ENTIRELY

**Frontend hooks:** `useDelegadosVigentes` → `GET /liquidaciones/delegados/vigentes`

The backend has `Delegado`, `DelegadoMunicipalidad`, `DelegadoMunicipalidadPeriodo` models and `DelegadoStatus` enum, but NO controller/router for exposing delegate endpoints.

#### 6. Inspectores API — MISSING ENTIRELY

**Frontend hooks:**
- `useInspectoresVigentes` → `GET /liquidaciones/{id}/inspectores/vigentes`
- `useInspectoresVigentes` → `GET /liquidaciones/inspectores/vigentes`

The backend has `Inspector`, `InspectorPeriodo`, `LiquidacionInspector` models, but NO controller/router.

#### 7. Revisiones Vigentes — MISSING

**Frontend hooks:** `useRevisionesVigentes` → `GET /liquidaciones/edificaciones/revisiones-vigentes`

Backend has the models but no dedicated endpoint for fetching vigente revisions.

#### 8. Finanzas Variables — Returns NULL

**Frontend hooks:** `useVariablesFinancieras` → `GET /finanzas/variables/vigentes`

Backend `FinanzasController.obtener_variables_vigentes()` returns:
```python
{"igv": None, "uit": None, "message": "FinanzasOrchestrator pendiente de reconstruir"}
```

### Missing Features (User-Noted)

#### 1. Tarifarios Históricos (Matriz de Precios)

**What it is:** Historical tariff matrix showing all past and current tariff values over time.

**Backend status:** No historical tariff endpoint exists. Only `tarifas/vigentes` endpoint returns current active tariffs.

**Frontend expected:** A page/modal to view historical tariff data by date range.

**Needed endpoint:** `GET /liquidaciones/{type}/tarifas/historicas` with date filters.

#### 2. Delegados

**Backend models exist:** `Delegado`, `DelegadoMunicipalidad`, `DelegadoMunicipalidadPeriodo` with `DelegadoStatus` enum.

**Missing API:**
- `GET /liquidaciones/delegados/vigentes?municipalidad_id=&tipo_liquidacion=&revision_id=`
- `GET /liquidaciones/delegados/{id}`

**Frontend components:** `DelegadosSection`, `GestionarDelegadosModal`

#### 3. Inspectores

**Backend models exist:** `Inspector`, `InspectorPeriodo`, `LiquidacionInspector`

**Missing API:**
- `GET /liquidaciones/{liquidacion_id}/inspectores/vigentes`
- `GET /liquidaciones/inspectores/vigentes?tipo_liquidacion=`
- `POST /liquidaciones/{id}/inspectores` (assign inspector)

**Frontend components:** `InspectoresSection`, `InspectorSelectorModal`, `GestionarInspectoresModal`

#### 4. Tablas de Financiación (Finanzas)

**Backend status:** `FinanzasOrchestrator` is commented out with TODO: "rebuild FinanzasOrchestrator".

**Needed:**
- UIT historical table with yearly values
- IGV historical table with date ranges
- Financing tables showing payment plan options

**Frontend expected:** Tables/pages in Finanzas section showing historical financial variables.

### Entidades Module (Working)

The `/entidades` controller IS properly implemented:
- `POST /entidades/instituciones`
- `POST /entidades/personas-naturales`
- `GET /entidades/buscar?numero_documento=`
- `GET /entidades/ubigeo/distritos`
- `GET /entidades/municipalidades`

This is used by `useMunicipalidades` and entity lookup fields.

## Summary of Mismatches

1. **CRITICAL — List/Detail APIs**: Every liquidacion type page (`/liquidaciones/edificaciones`, etc.) calls `GET /{type}` and `GET /{type}/{id}` which do not exist in backend.
2. **CRITICAL — Primera Revision path**: Frontend calls `/primera-revision` but backend uses `/nueva-liquidacion/primera-revision`.
3. **HIGH — Delegados/Inspectores**: Both concepts have backend models but zero API endpoints. Frontend has full UI components for these features.
4. **HIGH — Revisiones Vigentes**: Frontend needs to fetch current revision tariffs but no endpoint exists.
5. **MEDIUM — Finanzas variables**: Endpoint exists but returns null due to pending `FinanzasOrchestrator`.
6. **MEDIUM — Historical Tariffs**: No endpoint for viewing historical tariff data.
7. **LOW — Proyectos endpoint**: Frontend calls `/api/proyectos/` but no `ProyectosController` found in backend.
