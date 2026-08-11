# Exploration: liquidaciones-query-filters

## 1. Contrato (citas relevantes)

### PLAN_REFACTORIZACION.md — Reglas aplicables a filtros en controllers

**Sección 1.A — Los Controladores son "Sagrados" (Cero Lógica):**
> El controlador solo hace 3 cosas: Parsear la entrada, llamar al Orquestador, y retornar el éxito formateado por un Presenter.
> PROHIBIDO: Usar `if`, `for`, o variables de estado. PROHIBIDO: Tocar el ORM.

**Sección 2 — Patrones de Firmas de Controladores:**
> La firma de un controlador solo puede aceptar `self`, `request`, el `payload` (o `data`/`files`), y **parámetros de ruta/query**. Cualquier otra variable suelta en la firma es un error arquitectónico.

**Implicación para filtros query:** Los query params de filtrado se parsean en el controller (firmas tipo Query[...] de Ninja) y se pasan directamente al orchestrator. No hay lógica de filtrado en el controller.

### django-app-architecture-contract.md — Parametrización de queries:
> Params de query con `Query[...]` de Ninja. (línea 322)

**Implicación:** El patrón es `from ninja import Query` + `Optional[T] = Query(None, description="...")`.

---

## 2. Inventario de controllers/listados

### Endpoints GET de listado en `backend/modules/liquidaciones/presentation/controllers/`:

| Controller | Método | Ruta | Query Params HOY |
|---|---|---|---|
| `LiquidacionTaludesController.listar_liquidaciones` | GET | `/liquidaciones/taludes/` | `page`, `page_size` |
| `LiquidacionMecanicaSuelosController.list_liquidaciones` | GET | `/liquidaciones/mecanica-suelos/` | `page`, `page_size` |
| `LiquidacionInspeccionObraController.list_liquidaciones` | GET | `/liquidaciones/inspeccion-obra/` | `page`, `page_size` |
| `LiquidacionImpactoVialController.listar_liquidaciones` | GET | `/liquidaciones/impacto-vial/` | `page`, `page_size` |
| `LiquidacionHabilitacionUrbanaController.list_liquidaciones` | GET | `/liquidaciones/habilitacion-urbana/` | `page`, `page_size` |
| `LiquidacionEdificacionesController.list_liquidaciones` | GET | `/liquidaciones/edificaciones/` | `page`, `page_size` |
| `TarifasHistoricasController.get_tarifas_historicas` | GET | `/liquidaciones/{tipo}/tarifas/historicas` | `fecha_desde`, `fecha_hasta`, `page`, `page_size` |
| `TarifasHistoricasController.get_derechos_historicos` | GET | `/liquidaciones/derechos/historicos` | `tipo`, `fecha_desde`, `fecha_hasta` |
| `InspectorController.list_inspectores` | GET | `/inspectores/` | `page`, `page_size` |
| `InspectorController.list_inspectores_vigentes` | GET | `/inspectores/vigentes` | `tipo_liquidacion`, `page`, `page_size` |
| `DelegadoController.list_delegados` | GET | `/delegados/` | `page`, `page_size` |
| `DelegadoController.list_delegados_por_municipalidad` | GET | `/delegados/municipalidad/{id}` | `vigente` (opcional), `page`, `page_size` |

### Patrón existente de filtrado en otros módulos

**Módulo `entidades` — `entidad_controller.py` (líneas 101-103):**
```python
search: Optional[str] = Query(None, description="Texto para filtrar por nombre de distrito")
provincia_id: Optional[str] = Query(None, description="ID de provincia para filtrar")
departamento_id: Optional[str] = Query(None, description="ID de departamento para filtrar")
```
Este es el patrón de referencia: `from ninja import Query`, query params optional tipados como `Optional[T] = Query(None, ...)`, pasados directamente al orchestrator.

**Módulo `liquidaciones` — `tarifas_historicas_schemas.py` (líneas 16-28):**
```python
class TarifasHistoricasQueryParams(BaseSchema):
    fecha_desde: date
    fecha_hasta: date
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
```
Patrón de schema query params tipado con `BaseSchema` (para casos más complejos).

---

## 3. Estado actual de filtros

**Ningún endpoint de listado de liquidaciones por tipo soporta filtros más allá de paginación.**

- 6 controllers de liquidaciones específico (taludes, mecánica suelos, inspección obra, impacto vial, habilitación urbana, edificaciones) → solo `page` y `page_size`
- El frontend YA tiene UI de búsqueda textual (Input con `searchQuery` en los UI stores) pero **filtra en memoria** (client-side), no en el backend
- `TarifasHistoricasController` SÍ soporta filtros de fecha (`fecha_desde`, `fecha_hasta`) — es el único patrón de filtrado query params existente en liquidaciones

---

## 4. Patrón de filtrado existente en el repo

| Patrón | Ubicación | Descripción |
|---|---|---|
| `Query(...)` de Ninja | `modules/entidades/presentation/controllers/entidad_controller.py` | `Optional[str] = Query(None)` para filtros textuales y por ID |
| `BaseSchema` como QueryParams | `modules/liquidaciones/presentation/schemas/tarifas_historicas_schemas.py` | `TarifasHistoricasQueryParams(BaseSchema)` con `Field(...)` de Ninja |
| Custom managers filtrados | `modules/entidades/domain/models/municipalidad.py` | `MunicipalidadManager` con `get_queryset().filter(...)` para proxy models |
| Vigencia filter | `modules/liquidaciones/domain/services/orchestrators/delegado_orchestrator.py` | `vigente` param con filtro `periodo_inicio <= today AND (periodo_fin IS NULL OR periodo_fin >= today)` |

**No existe `FilterSet` de Django ni библиотека de filtros dedicada.** El filtrado es manual en los orquestadores.

---

## 5. Modelos y campos filtrables

### `LiquidacionGeneral` (dominio: `liquidacion_general`)
Campos con potencial de filtrado:
- `estado` — CharField con choices `EstadoLiquidacion`: `PENDIENTE`, `APROBADA`, `REINGRESADA`, `RECHAZADA`
- `fecha_registro` — DateTimeField (auto_now_add)
- `expediente` — CharField (número de expediente, texto libre)
- `numero_revision` — PositiveIntegerField (1 = primera revisión)
- `retencion` — BooleanField
- `tipo_liquidacion` — ForeignKey a `TipoLiquidacion`
- `municipalidad` — ForeignKey a `entidades.Municipalidad`
- `proyecto` — ForeignKey a `Proyecto`

### `Proyecto` (dominio: `proyecto`)
Campos con potencial de filtrado:
- `denominacion` — CharField (nombre del proyecto, **búsqueda textual**)
- `entidad_razon_social` — CharField (snapshot de razón social, **búsqueda textual**)
- `entidad_numero_documento` — CharField (RUC/DNI)
- `distrito` — ForeignKey a `UbigeoDistrito`
- `direccion` — CharField

### `LiquidacionPorcentajeObra` (dominio: específico — Edificaciones, IV, Taludes)
- `tipo_tramite` — CharField con choices `TipoTramiteEdificaciones`: `OBRA_NUEVA`, `DEMOLICION`, `AMPLIACION`, `REMODELACION`, etc.
- `valor_declarado` — DecimalField

### `LiquidacionPorMetroCuadrado` (dominio: HU, MS)
- `area_m2` — DecimalField

### `LiquidacionPorCategoriaVisitas` (dominio: IO)
- `cantidad_visitas` — PositiveIntegerField
- `categoria` — CharField (A, B, C...)

---

## 6. Frontend expectations

### hooks/useLiquidacionList.ts
```typescript
url: `${url}?page=${paginationParams.page}&page_size=${paginationParams.page_size}`
```
Hoy solo envía `page` y `page_size`. **No envía search ni estado.**

### UI Stores (e.g., `taludes-ui-list.store.ts`)
```typescript
interface TaludesUIState {
  page: number;
  pageSize: number;
  searchQuery: string;  // ← YA EXISTE pero NO se envía al backend
  isFormModalOpen: boolean;
  selectedItemId: string | null;
}
```
El `searchQuery` se mantiene en el store pero **filtra en memoria**:
```typescript
const filteredItems = items.filter((item) =>
  item.liquidacion_general.proyecto.denominacion.toLowerCase().includes(searchInput.toLowerCase())
);
```

### LiquidacionesTaludesView.tsx (líneas 38-42)
```typescript
const filteredItems = items.filter((item) =>
  item.liquidacion_general.proyecto.denominacion.toLowerCase().includes(searchInput.toLowerCase())
);
```
**Client-side filtering on denominacion — ineficiente para grandes volúmenes.**

### Frontend UI que SÍ tiene filtros en otros features
- `entidades` → `search`, `provincia_id`, `departamento_id` (enviados al backend)
- Inspectores → `tipo_liquidacion` (enviado al backend)
- Delegados → `vigente` (enviado al backend)

---

## 7. Recomendaciones iniciales

### Filtros valiosos por implementar (prioridad sugerida)

| Filtro | Campo del modelo | Tipo | Descripción |
|---|---|---|---|
| Búsqueda textual | `proyecto.denominacion` / `proyecto.entidad_razon_social` | `str` | Busca en nombre de proyecto o razón social |
| Estado | `liquidacion_general.estado` | `str` (enum) | `PENDIENTE`, `APROBADA`, `REINGRESADA`, `RECHAZADA` |
| Fecha desde/hasta | `liquidacion_general.fecha_registro` | `date` | Rango de fecha de registro |
| Expediente | `liquidacion_general.expediente` | `str` | Número de expediente exacto o parcial |
| Orden | — | `str` | `fecha_registro`, `estado`, `total` (asc/desc) |

### Patrón recomendado (siguiendo el contrato)

1. **Crear schema QueryParams** en `presentation/schemas/` por cada controller:
   - `LiquidacionTaludesQueryParams(BaseSchema)` con `Field(...)` de Ninja
   - O usar `Query(...)` directo en la firma del controller (más simple para params pocos)

2. **Firma del controller** (Patrón 3 del contrato — JSON Estricto):
   ```python
   def listar_liquidaciones(
       self,
       request,
       page: int = 1,
       page_size: int = 10,
       search: Optional[str] = Query(None, description="Búsqueda por denominacion de proyecto"),
       estado: Optional[str] = Query(None, description="Estado: PENDIENTE, APROBADA, REINGRESADA, RECHAZADA"),
       orden_por: Optional[str] = Query("fecha_registro", description="Campo de ordenamiento"),
       orden_dir: Optional[str] = Query("desc", description="Dirección: asc o desc"),
   ):
   ```

3. **Pasar al orchestrator** — sin lógica en controller:
   ```python
   liquidaciones, total = self.orchestrator.listar_liquidaciones(
       page=page,
       page_size=page_size,
       search=search,
       estado=estado,
       orden_por=orden_por,
       orden_dir=orden_dir,
   )
   ```

4. **En el orchestrator** — aplicar filtros al queryset base.

### Consideraciones de arquitectura

- **6 controllers** de liquidaciones específico necesitan filtros (taludes, ms, io, iv, hu, edificaciones)
- **Patrón uniforme** es deseable: mismo schema de query params para los 6
- **Losorchestrator de cada tipo** (`listar_liquidaciones_proceso`) recibe los filtros y los aplica al `qs.filter(...)`
- **No usar Django Filter** — filtrado manual en los orchestors es consistente con el resto del codebase
- **Contrato de refactorización**: los filtros van en query params del controller, se delegan al orchestrator sin `if`/`for` en el controller

---

## 8. Riesgos encontrados

| Riesgo | Descripción |
|---|---|
| **Fragilización del orchestrator** | Si los orchestors reciben muchos parámetros de filtro, el método `listar_liquidaciones` crece. Considerar un objeto `LiquidacionListFilters` o QueryParams schema como único parámetro. |
| **Inconsistencia entre 6 controllers** | Cada controller tiene su propio `listar_liquidaciones`. Si los 6 implementan filtros, asegurar que los schemas yparams sean consistentes (misma semántica de `search`, `estado`, `orden`). |
| **Ordenamiento injection** | Si `orden_por` se usa directamente en `.order_by()`, sanitizar contra campos válidos para evitar SQL injection (Django ORM es seguro pero un valor inesperado causaría error). |
| **Front-end no consume los filtros** | Hoy el frontend NO envía `search`/`estado`/`orden` al backend. Se requiere cambios paralelos en `useLiquidacionList` y los UI stores para construir la query string con los filtros. |
| **Tests existentes** | Los 6 `test_*_list.py` asumen solo `page`/`page_size`. Agregar filtros requiere actualizar los tests. |
