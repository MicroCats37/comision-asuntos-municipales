# Mapa de Rutas — Backend Liquidaciones

## Fase 1: IMPLEMENTADO ✅

### Listados Paginados
| Método | Ruta | Controlador |
|--------|------|-------------|
| GET | `/api/liquidaciones/edificaciones/` | `LiquidacionEdificacionesController` |
| GET | `/api/liquidaciones/habilitacion-urbana/` | `LiquidacionHabilitacionUrbanaController` |
| GET | `/api/liquidaciones/mecanica-suelos/` | `LiquidacionMecanicaSuelosController` |
| GET | `/api/liquidaciones/impacto-vial/` | `LiquidacionImpactoVialController` |
| GET | `/api/liquidaciones/taludes/` | `LiquidacionTaludesController` |
| GET | `/api/liquidaciones/inspeccion-obra/` | `LiquidacionInspeccionObraController` |

Query params: `page`, `page_size`
Response: `ApiResponse[PaginatedData[LiquidacionXxxOutput]]`

### Detalle
| Método | Ruta | Controlador |
|--------|------|-------------|
| GET | `/api/liquidaciones/edificaciones/{uuid:liquidacion_id}` | `LiquidacionEdificacionesController` |
| GET | `/api/liquidaciones/habilitacion-urbana/{uuid:liquidacion_id}` | `LiquidacionHabilitacionUrbanaController` |
| GET | `/api/liquidaciones/mecanica-suelos/{uuid:liquidacion_id}` | `LiquidacionMecanicaSuelosController` |
| GET | `/api/liquidaciones/impacto-vial/{uuid:liquidacion_id}` | `LiquidacionImpactoVialController` |
| GET | `/api/liquidaciones/taludes/{uuid:liquidacion_id}` | `LiquidacionTaludesController` |
| GET | `/api/liquidaciones/inspeccion-obra/{uuid:liquidacion_id}` | `LiquidacionInspeccionObraController` |

Response: `ApiResponse[LiquidacionXxxOutput]` (mismo schema que creación)

### Creación (existente)
| Método | Ruta |
|--------|------|
| POST | `/api/liquidaciones/edificaciones/nueva-liquidacion/primera-revision` |
| POST | `/api/liquidaciones/habilitacion-urbana/nueva-liquidacion/primera-revision` |
| POST | `/api/liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision` |
| POST | `/api/liquidaciones/impacto-vial/nueva-liquidacion/primera-revision` |
| POST | `/api/liquidaciones/taludes/nueva-liquidacion/primera-revision` |
| POST | `/api/liquidaciones/inspeccion-obra/nueva-liquidacion/primera-revision` |

### Cotización (existente)
| Método | Ruta |
|--------|------|
| POST | `/api/liquidaciones/edificaciones/cotizar` |
| POST | `/api/liquidaciones/habilitacion-urbana/cotizar` |
| POST | `/api/liquidaciones/mecanica-suelos/cotizar` |
| POST | `/api/liquidaciones/impacto-vial/cotizar` |
| POST | `/api/liquidaciones/taludes/cotizar` |
| POST | `/api/liquidaciones/inspeccion-obra/cotizar` |

### Finanzas
| Método | Ruta | Estado |
|--------|------|--------|
| GET | `/api/finanzas/variables/vigentes` | ✅ Reconstruido |

---

## Fase 2: Delegados (FUTURO)

| Método | Ruta | Query Params |
|--------|------|-------------|
| GET | `/api/delegados/` | `page`, `page_size` |
| GET | `/api/delegados/{id}/municipalidades` | — |
| GET | `/api/delegados/municipalidad/{id}` | `?vigente=true` |

**Nota:** La vigencia del delegado está atada a `DelegadoMunicipalidadPeriodo`. El filtro `vigente=true` verifica `periodo_inicio <= today AND (periodo_fin IS NULL OR periodo_fin >= today)`.

---

## Fase 3: Inspectores (FUTURO)

| Método | Ruta | Query Params |
|--------|------|-------------|
| GET | `/api/inspectores/vigentes` | `?tipo_liquidacion=EDIFICACION\|HABILITACION_URBANA` |
| GET | `/api/inspectores/` | `page`, `page_size` |
| GET | `/api/inspectores/{id}` | — |

**Nota:** `InspectorPeriodo` NO tiene relación con Municipalidad (el docstring miente). La vigencia es propia del inspector.

**Pendiente corregir:** Docstring de `InspectorPeriodo` — borrar "Relación muchos-a-muchos entre Inspector y Municipalidad".

---

## Exclusiones explícitas
- Nueva Revisión (`POST /cotizar/nueva-revision`, `POST /nueva-revision`): fase posterior
- Tarifario Histórico: fase posterior
