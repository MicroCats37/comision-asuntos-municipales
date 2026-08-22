# Exploration: Legacy Liquidaciones

## Contexto / Problema

El sistema actual de liquidaciones solo puede crear liquidaciones con tarifas **vigentes** (al día de hoy). No existe forma de registrar liquidaciones históricas donde las tarifas, IGV, UIT y derechos se resuelvan usando una **fecha de registro histórica** arbitraria proporcionada por el cliente.

El usuario necesita 6 endpoints legacy (uno por tipo) que permitan registrar liquidaciones con fecha_registro histórica, resolviendo todas las variables financieras (tarifas, IGV, UIT, derechos) según la vigencia que tenían en esa fecha histórica.

## Objetivo

Diseñar e implementar 6 endpoints legacy POST `/nueva-liquidacion/primera-revision` (uno por tipo: edificaciones, taludes, impacto-vial [PO], habilitación-urbana, mecánica-suelos [M2], inspección-obra [visitas]) que acepten `fecha_registro` en el payload y resuelvan tarifas/IGV/UIT/derechos históricos por esa fecha.

## Decisiones tomadas (usuario)

1. **100% aditivo** — no se tocan inputs/schemas/presenters/controllers/orchestrators/flujos existentes.
2. **Sin `fecha_registro` en schemas existentes** — `LiquidacionGeneralRevisionIn`, `LiquidacionGeneralData`, `create_liquidacion_general` permanecen intactos.
3. **Modelo `LiquidacionGeneral.fecha_registro`** ya tiene `default=timezone.now` y migración 0010 existe (no tocar migraciones).
4. **Sin lógica de cadena de revisión** — no MAX_REVISIONES, no +2, no previas M2M. `numero_revision` viene del payload (default 1).
5. **`usuario_creador`** = admin autenticado (del request), no del payload.
6. **Fases pequeñas** — cada tarea = apply separado, autónomo y verificable.

## Restricciones (aditivo, sin migraciones, sin tocar existentes)

- **Adición pura**: todo en artefactos nuevos o métodos nuevos añadidos a servicios existentes.
- **Sin modificar schemas de entrada existentes** (`LiquidacionGeneralRevisionIn`, `LiquidacionGeneralData`).
- **Sin modificar `create_liquidacion_general`** (firma existente intacta).
- **Sin modificar presenters existentes**.
- **Sin tocar migraciones** (ni crear nuevas para el modelo).
- **`fecha_registro` del modelo ya tiene `default=timezone.now`** — no requiere cambios.

## Hallazgos de código (verificados, con file:line)

### 1. Modelo `LiquidacionGeneral.fecha_registro`

**Archivo**: `backend/modules/liquidaciones/domain/models/liquidacion/liquidacion_general/liquidacion.py:48-52`

```python
fecha_registro = models.DateTimeField(
    default=timezone.now,
    verbose_name="Fecha de Registro",
    ...
)
```

Confirmado: el campo ya existe con `default=timezone.now`. La migración 0010 que añade/alimenta este campo está en el working tree sin commitear (según el usuario). **No se toca.**

### 2. `VigenciaModel.vigentes(fecha=None)`

**Archivo**: `backend/core_application/models.py:7-23`

```python
def vigentes(self, fecha=None):
    if fecha is None:
        fecha = date.today()
    return self.filter(
        models.Q(periodo_fin__isnull=True)
        | models.Q(periodo_fin__gte=fecha),
        periodo_inicio__lte=fecha,
    )
```

**Confirmado**: el manager Y el QuerySet de `VigenciaModel` YA aceptan `fecha` opcional. Todas las tarifas y derechos que heredan de `VigenciaModel` pueden filtrarse por fecha.

### 3. IGV y UIT: managers NO aceptan fecha

**Archivo**: `backend/modules/finanzas/domain/models/impuestos.py:14-27`

```python
class IGVQuerySet(models.QuerySet):
    def vigente(self) -> Optional["IGV"]:
        return self.filter(periodo_fin__isnull=True).order_by("-periodo_inicio").first()

class UITQuerySet(models.QuerySet):
    def vigente(self) -> Optional["UIT"]:
        return self.filter(periodo_fin__isnull=True).order_by("-periodo_inicio").first()
```

**Confirmado**: `IGV.objects.vigente()` y `UIT.objects.vigente()` NO aceptan parámetro `fecha`. Solo filtran `periodo_fin__isnull=True`. **Para legacy se necesita filtro manual por `fecha_registro`**.

### 4. `create_liquidacion_general` — firma actual

**Archivo**: `backend/modules/liquidaciones/domain/services/core/liquidacion_general/liquidacion_general_core_service.py:125-156`

```python
def create_liquidacion_general(
    self,
    municipalidad_id: str,
    expediente: str,
    observacion: Optional[str],
    proyecto: Proyecto,
    tipo_liquidacion: str,
    numero_revision: int = 1,
    contacto=None,
    retencion: bool = False,
) -> LiquidacionGeneral:
```

**Confirmado**: NO tiene parámetro `fecha_registro`. El campo se alimenta del `default=timezone.now` del modelo. **Estrategia**: en el flujo legacy, después de crear la `LiquidacionGeneral`, hacer `.save()` con `fecha_registro` explícito antes de persistir.

### 5. Core services — métodos `*_por_fecha` NO existen

Los métodos `*_por_fecha` fueron revertidos. Lo que existe hoy:

**`LiquidacionPorMetroCuadradoCoreService`** (`liquidacion_por_metro_cuadrado_core_service.py`):
- `get_tarifa_m2_vigente(tipo_liquidacion)` — filtra `periodo_fin__isnull=True` hardcodeado, NO acepta fecha ❌
- `get_derecho_minimo_m2_vigente()` — misma situación ❌
- `calcular_cotizacion_m2(...)` — usa los métodos above ❌

**`LiquidacionPorCategoriaVisitasCoreService`** (`liquidacion_por_categoria_visitas_core_service.py`):
- `get_tarifa_visitas_vigente()` — sin fecha ❌
- `get_uit_vigente()` — delega a `general_core_service.get_uit_vigente()` ❌
- `get_igv_vigente()` — delega a `general_core_service.get_igv_vigente()` ❌

**`LiquidacionGeneralCoreService`**:
- `get_uit_vigente()` → `UIT.objects.vigente()` (sin fecha) ❌
- `get_igv_vigente()` → `IGV.objects.vigente()` (sin fecha) ❌

**`LiquidacionPorcentajeObraCoreService`** (`liquidacion_porcentaje_obra_core_service.py`):
- `get_derecho_porcentaje_vigente()` → `DerechoPorcentajeObra.objects.vigentes().first()` (sin fecha) ❌
- `get_tarifas_porcentaje_vigentes(tipo_liquidacion)` → `TarifaLiquidacionBase.objects.vigentes()` (sin fecha) ❌

### 6. `TarifasHistoricasCoreService` — infraestructura de fecha YA existe

**Archivo**: `backend/modules/liquidaciones/domain/services/core/liquidacion_tipo/tarifas_historicas_core_service.py`

Este servicio YA tiene métodos que aceptan `fecha`:
- `get_derechos_porcentaje_vigentes(fecha=None)` → línea 129
- `get_derechos_m2_vigentes(fecha=None)` → línea 133
- `get_tarifas_vigentes(tipo_liquidacion, fecha=None)` → línea 137
- `get_tarifas_generales_vigentes(fecha=None)` → línea 144

**Importante**: estos métodos retornan **listas** (primer elemento para el caso de derecho mínimo único). Son la base sobre la que construir los métodos `*_por_fecha` necesarios.

### 7. Controladoras existentes (6 tipos)

| Tipo | Controladora | ¿Tiene POST `/nueva-liquidacion/primera-revision`? |
|------|-------------|---------------------------------------------------|
| Edificaciones | `LiquidacionEdificacionesController` | ✅ Línea 122-138 |
| Taludes | `LiquidacionTaludesController` | ✅ Línea 121-137 |
| Impacto Vial | `LiquidacionImpactoVialController` | ✅ existe |
| Habilitación Urbana | `LiquidacionHabilitacionUrbanaController` | ✅ existente |
| Mecánica Suelos | `LiquidacionMecanicaSuelosController` | ✅ existente |
| Inspección Obra | `LiquidacionInspeccionObraController` | ✅ existente |

Patrón general del controller:
```python
def crear_primera_revision(self, request, payload: InputSchema):
    usuario_id = self.auth_core_service.get_authenticated_user_id(request)
    domain_result = self.orchestrator.crear_primera_revision_proceso(
        usuario_id=usuario_id, payload_in=payload
    )
    result = self.presenter.present_primera_revision(domain_result)
    return success_response(result)
```

### 8. Esquemas de entrada existentes

**`LiquidacionGeneralRevisionIn`** — es el schema de `liquidacion_general` usado en todos los inputs de primera-revisión. **NO se modifica.**

Los inputs por tipo heredan:
```
LiquidacionHabilitacionUrbanaInput = LiquidacionGeneralRevisionIn + LiquidacionPorMetroCuadradoIn
LiquidacionInspeccionObraInput = LiquidacionGeneralRevisionIn + LiquidacionPorCategoriaVisitasIn
LiquidacionEdificacionesInput = LiquidacionGeneralRevisionIn + LiquidacionPorPorcentajeIn
...etc
```

### 9. Flujos existentes — patrón transaccional

| Flujo | `@transaction.atomic` | Métodos clave |
|-------|---------------------|---------------|
| `LiquidacionHabilitacionUrbanaFlujo._ejecutar_primera_revision_sync` | ❌ FALTANTE | 7 ORM writes |
| `LiquidacionInspeccionObraFlujo.ejecutar_primera_revision` | ✅ | 8 ORM writes |
| `LiquidacionPorMetroCuadradoFlujo.crear_liquidacion_m2_transaccional` | ✅ | 5 ORM writes |
| `LiquidacionMecanicaSuelosFlujo._ejecutar_primera_revision_sync` | ❌ FALTANTE | similar a HU |

**Nota**: Los flujos HU y MS no tienen `@transaction.atomic` — deuda técnica existente, no parte del scope legacy.

### 10. Repositorio de tests

`tests/fixtures/` contiene factories y fixtures (po_base_setup, m2_base_setup, io_base_setup). No hay cobertura de tests para los archivos referenciados.

## Alternativas consideradas

### Opción A: Métodos `*_por_fecha` en cada Core Service existente

**Descripción**: Añadir métodos como `get_tarifa_m2_por_fecha(tipo_liquidacion, fecha)` a `LiquidacionPorMetroCuadradoCoreService`, `get_igv_por_fecha(fecha)` a `LiquidacionGeneralCoreService`, etc.

**Pros**:
- Mantiene la ubicación de los métodos junto a sus contrapartes vigentes
- Siguen el mismo patrón de firma existente

**Cons**:
- **Viola la restricción aditiva**: tocar los Core Services existentes (archivos con lógica en uso)
- Mezcla lógica "vigente" y "por fecha" en el mismo servicio
- Más difícil de verificar de forma aislada

**Veredicto**: ❌ RECHAZADO — no es 100% aditivo.

### Opción B: Nuevos métodos `*_por_fecha` en `TarifasHistoricasCoreService` + nuevos Core Services "Legacy"

**Descripción**: Crear una nueva clase `LiquidacionPorMetroCuadradoLegacyCoreService` con los métodos `*_por_fecha` y reutilizar `TarifasHistoricasCoreService` que ya tiene la infraestructura de filtrado por fecha.

**Pros**:
- 100% aditivo — solo archivos nuevos
- `TarifasHistoricasCoreService` ya existe y tiene la lógica de filtrado por `fecha` en `VigenciaModel.vigentes(fecha)`
- Separa claramente la lógica legacy de la vigente

**Cons**:
- Duaplicación parcial de código (los métodos vigentes vs por_fecha)
- Requiere instanciar nuevos servicios en los flujos legacy

**Veredicto**: ✅ ACEPTADO — es la opción que cumple con la restricción 100% aditiva.

### Opción C: Single Flujo con parámetro `fecha_registro` en el orchestrator

**Descripción**: Hacer que el orchestrator existente acepte `fecha_registro` opcional y pasar la fecha a los Core Services.

**Pros**:
- Más DRY

**Cons**:
- **Viola la restricción**: toca orchestrators y flujos existentes
- Mezcla lógica vigente y legacy en el mismo flujo

**Veredicto**: ❌ RECHAZADO.

## Propuesta: arquitectura por capas

### Arquitectura general

```
CLIENTE (payload + fecha_registro)
  │
  ▼
NEW: LegacyInputSchema (fecha_registro + existente Input)
  │
  ▼
NEW: LegacyOrchestrator.crear_primera_revision_proceso(fecha_registro, payload)
  │
  ├─► LegacyCoreService (nuevo, 100% aditivo)
  │     ├─ get_tarifa_por_fecha(tipo, fecha)     ──► VigenciaModel.vigentes(fecha)
  │     ├─ get_derecho_por_fecha(tipo, fecha)     ──► VigenciaModel.vigentes(fecha)
  │     ├─ get_igv_por_fecha(fecha)               ──► filter periodo_inicio__lte=fecha, periodo_fin__gte=fecha
  │     ├─ get_uit_por_fecha(fecha)               ──► filter periodo_inicio__lte=fecha, periodo_fin__gte=fecha
  │     └─ get_tarifa_visitas_por_fecha(tipo, fecha)
  │
  ├─► FlujoLegacy (nuevo, copia del Flujo existente + fecha_registro)
  │     └─ Transaccional (@transaction.atomic)
  │         ├─ create_entidad
  │         ├─ create_proyecto
  │         ├─ LegacyCoreService.get_igv_por_fecha(fecha)
  │         ├─ LegacyCoreService.get_uit_por_fecha(fecha)
  │         ├─ LegacyCoreService.calcular_cotizacion_*(...)
  │         ├─ create_liquidacion_general
  │         │     └─ liquidacion_general.fecha_registro = fecha_registro (explicit save)
  │         ├─ create_liquidacion_tipo
  │         └─ create_liquidacion_especifico
  │
  └─► Presenter.existing.present_primera_revision(domain_result)
        └─ Returns: OutputSchema (reutiliza presenters existentes)
```

### Archivos a crear (100% nuevos)

```
backend/modules/liquidaciones/
├── domain/services/core/liquidacion_legacy/
│   ├── liquidacion_legacy_por_porcentaje_core_service.py   # PO: tarifas %, derecho %
│   ├── liquidacion_legacy_por_m2_core_service.py          # M2: tarifas m2, derecho m2
│   └── liquidacion_legacy_por_visitas_core_service.py       # Visitas: tarifas visitas, IGV, UIT
│
├── domain/services/flujos/liquidacion_legacy/
│   ├── liquidacion_edificaciones_legacy_flujo.py
│   ├── liquidacion_taludes_legacy_flujo.py
│   ├── liquidacion_impacto_vial_legacy_flujo.py
│   ├── liquidacion_habilitacion_urbana_legacy_flujo.py
│   ├── liquidacion_mecanica_suelos_legacy_flujo.py
│   └── liquidacion_inspeccion_obra_legacy_flujo.py
│
├── domain/services/orchestrators/liquidacion_legacy/
│   ├── liquidacion_edificaciones_legacy_orchestrator.py
│   ├── liquidacion_taludes_legacy_orchestrator.py
│   ├── liquidacion_impacto_vial_legacy_orchestrator.py
│   ├── liquidacion_habilitacion_urbana_legacy_orchestrator.py
│   ├── liquidacion_mecanica_suelos_legacy_orchestrator.py
│   └── liquidacion_inspeccion_obra_legacy_orchestrator.py
│
├── presentation/schemas/liquidacion_legacy/
│   ├── liquidacion_edificaciones_legacy_schema.py     # Input: fecha_registro + EdificacionesInput
│   ├── liquidacion_taludes_legacy_schema.py
│   ├── liquidacion_impacto_vial_legacy_schema.py
│   ├── liquidacion_habilitacion_urbana_legacy_schema.py
│   ├── liquidacion_mecanica_suelos_legacy_schema.py
│   └── liquidacion_inspeccion_obra_legacy_schema.py
│
├── presentation/controllers/liquidacion_legacy/
│   ├── liquidacion_edificaciones_legacy_controller.py
│   ├── liquidacion_taludes_legacy_controller.py
│   ├── liquidacion_impacto_vial_legacy_controller.py
│   ├── liquidacion_habilitacion_urbana_legacy_controller.py
│   ├── liquidacion_mecanica_suelos_legacy_controller.py
│   └── liquidacion_inspeccion_obra_legacy_controller.py
│
└── di.py  # AÑADIR bindings para los 6 servicios nuevos (aditivo)
```

**Archivos a modificar (exclusivamente aditivo)**:
- `backend/modules/liquidaciones/di.py` — añadir 18 nuevas bindings (3 por tipo: Orchestrator, Flujo, Presenter/Schema)
- `backend/config/api.py` — registrar 6 nuevas rutas de controllers legacy

**Archivos existentes que NO se tocan**:
- `LiquidacionGeneralRevisionIn`, `LiquidacionGeneralData` — intactos
- `create_liquidacion_general` — firma intacta
- Todos los presenters existentes — intactos
- Todos los orquestadores existentes — intactos
- Todos los flujos existentes — intactos
- Migraciones — no se tocan

## Fases de implementación (TAREAS PEQUEÑAS numeradas)

> Cada tarea = un apply separado, autónomo y verificable. No un mega-apply.

### Tarea 1: Core methods `*_por_fecha` (3 servicios legacy)

**Archivos nuevos**:
- `backend/modules/liquidaciones/domain/services/core/liquidacion_legacy/liquidacion_legacy_por_porcentaje_core_service.py`
- `backend/modules/liquidaciones/domain/services/core/liquidacion_legacy/liquidacion_legacy_por_m2_core_service.py`
- `backend/modules/liquidaciones/domain/services/core/liquidacion_legacy/liquidacion_legacy_por_visitas_core_service.py`

**Métodos a implementar**:

| Servicio | Método | Retorna |
|----------|--------|---------|
| `LiquidacionLegacyPorPorcentajeCoreService` | `get_tarifa_porcentaje_por_fecha(tipo, fecha)` | `TarifaPorcentajeObra` |
| `LiquidacionLegacyPorPorcentajeCoreService` | `get_derecho_porcentaje_por_fecha(fecha)` | `DerechoPorcentajeObra` |
| `LiquidacionLegacyPorM2CoreService` | `get_tarifa_m2_por_fecha(tipo, fecha)` | `TarifaPorMetroCuadrado` |
| `LiquidacionLegacyPorM2CoreService` | `get_derecho_m2_por_fecha(fecha)` | `DerechoPorMetroCuadrado` |
| `LiquidacionLegacyPorVisitasCoreService` | `get_tarifa_visitas_por_fecha(tipo, categoria, fecha)` | `TarifaPorCategoriaVisitas` |
| `LiquidacionLegacyPorVisitasCoreService` | `get_igv_por_fecha(fecha)` | `IGV` (filtro manual) |
| `LiquidacionLegacyPorVisitasCoreService` | `get_uit_por_fecha(fecha)` | `UIT` (filtro manual) |

**Verificación**: tests unitarios de cada método verificando que filtra por fecha correcta.

---

### Tarea 2: Domain legacy data + Legacy In schemas

**Archivos nuevos** (schemas):
- `backend/modules/liquidaciones/presentation/schemas/liquidacion_legacy/liquidacion_edificaciones_legacy_schema.py`
- `backend/modules/liquidaciones/presentation/schemas/liquidacion_legacy/liquidacion_taludes_legacy_schema.py`
- `backend/modules/liquidaciones/presentation/schemas/liquidacion_legacy/liquidacion_impacto_vial_legacy_schema.py`
- `backend/modules/liquidaciones/presentation/schemas/liquidacion_legacy/liquidacion_habilitacion_urbana_legacy_schema.py`
- `backend/modules/liquidaciones/presentation/schemas/liquidacion_legacy/liquidacion_mecanica_suelos_legacy_schema.py`
- `backend/modules/liquidaciones/presentation/schemas/liquidacion_legacy/liquidacion_inspeccion_obra_legacy_schema.py`

**Estructura de cada schema** (ejemplo para HU):
```python
class LiquidacionHabilitacionUrbanaLegacyInput(BaseSchema):
    fecha_registro: date  # ← nuevo campo
    liquidacion_general: LiquidacionGeneralRevisionIn  # ← EXISTENTE, no se toca
    liquidacion_especifica: LiquidacionPorMetroCuadradoIn  # ← EXISTENTE
```

**Verificación**: cada schema hace parseo correcto de `fecha_registro` + todos los campos existentes.

---

### Tarea 3: Orchestrators legacy (6)

**Archivos nuevos**:
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_legacy/liquidacion_edificaciones_legacy_orchestrator.py`
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_legacy/liquidacion_taludes_legacy_orchestrator.py`
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_legacy/liquidacion_impacto_vial_legacy_orchestrator.py`
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_legacy/liquidacion_habilitacion_urbana_legacy_orchestrator.py`
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_legacy/liquidacion_mecanica_suelos_legacy_orchestrator.py`
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_legacy/liquidacion_inspeccion_obra_legacy_orchestrator.py`

**Método principal**:
```python
def crear_primera_revision_proceso(
    self,
    usuario_id: int,
    payload_in: LiquidacionHabilitacionUrbanaLegacyInput,  # nuevo schema con fecha_registro
) -> HabilitacionUrbanaPrimeraRevisionResult:
    fecha_registro = payload_in.fecha_registro
    # Valida fecha_registro
    # Resuelve tarifas/derechos por fecha via LegacyCoreService
    # Assembla domain_data con cotizacion calculada
    # Llama a FlujoLegacy.ejecutar_primera_revision(fecha_registro, domain_data)
```

**Verificación**: el orchestrator recibe `fecha_registro`, la pasa al flujo, y resuelve tarifas por fecha.

---

### Tarea 4: Flujos legacy (6)

**Archivos nuevos**:
- `backend/modules/liquidaciones/domain/services/flujos/liquidacion_legacy/liquidacion_edificaciones_legacy_flujo.py`
- `backend/modules/liquidaciones/domain/services/flujos/liquidacion_legacy/liquidacion_taludes_legacy_flujo.py`
- `backend/modules/liquidaciones/domain/services/flujos/liquidacion_legacy/liquidacion_impacto_vial_legacy_flujo.py`
- `backend/modules/liquidaciones/domain/services/flujos/liquidacion_legacy/liquidacion_habilitacion_urbana_legacy_flujo.py`
- `backend/modules/liquidaciones/domain/services/flujos/liquidacion_legacy/liquidacion_mecanica_suelos_legacy_flujo.py`
- `backend/modules/liquidaciones/domain/services/flujos/liquidacion_legacy/liquidacion_inspeccion_obra_legacy_flujo.py`

**Diferencia crítica vs flujos existentes**:
- Aceptan `fecha_registro: date` como parámetro
- Usan `LegacyCoreService.*_por_fecha()` en lugar de `*_vigente()`
- **Después de `create_liquidacion_general()`, hacen `lg.save()` con `lg.fecha_registro = fecha_registro`** (porque `create_liquidacion_general` no acepta `fecha_registro`)
- **Todos llevan `@transaction.atomic()`** (incluyendo HU y MS que carecen de él en su flujo vigente)

```python
@transaction.atomic  # ← OBLIGATORIO en todos los flujos legacy
def ejecutar_primera_revision(
    self,
    usuario_id: int,
    fecha_registro: date,
    data: HabilitacionUrbanaPrimeraRevisionData,
) -> HabilitacionUrbanaPrimeraRevisionResult:
    igv = self.legacy_visitas_core.get_igv_por_fecha(fecha_registro)
    uit = self.legacy_visitas_core.get_uit_por_fecha(fecha_registro)
    # ... resto del flujo ...
    lg = self.general_core_service.create_liquidacion_general(...)
    lg.fecha_registro = fecha_registro  # ← override tras create
    lg.save()
    # ...continúa...
```

**Verificación**: crear una liquidación con `fecha_registro` de hace 6 meses y verificar que:
1. La tarifa usada es la vigente en esa fecha
2. `LiquidacionGeneral.fecha_registro` = la fecha proporcionada (no `timezone.now`)

---

### Tarea 5: Presenters legacy

**Verificar si se necesitan presenters nuevos**: Los presenters existentes (`present_primera_revision`) reciben `HabilitacionUrbanaPrimeraRevisionResult` (domain DTO) y retornan `LiquidacionHabilitacionUrbanaOutput` (presentation schema). **NO necesitan cambios** porque:
- El domain DTO `HabilitacionUrbanaPrimeraRevisionResult` no cambia
- El flujo legacy retorna el mismo domain DTO

**Decisión**: no se crean presenters legacy nuevos. Se reutilizan los existentes. El presenter recibe el resultado del flujo y lo mapea al output schema existente.

---

### Tarea 6: Controllers legacy endpoints (6)

**Archivos nuevos**:
- `backend/modules/liquidaciones/presentation/controllers/liquidacion_legacy/liquidacion_edificaciones_legacy_controller.py`
- `backend/modules/liquidaciones/presentation/controllers/liquidacion_legacy/liquidacion_taludes_legacy_controller.py`
- `backend/modules/liquidaciones/presentation/controllers/liquidacion_legacy/liquidacion_impacto_vial_legacy_controller.py`
- `backend/modules/liquidaciones/presentation/controllers/liquidacion_legacy/liquidacion_habilitacion_urbana_legacy_controller.py`
- `backend/modules/liquidaciones/presentation/controllers/liquidacion_legacy/liquidacion_mecanica_suelos_legacy_controller.py`
- `backend/modules/liquidaciones/presentation/controllers/liquidacion_legacy/liquidacion_inspeccion_obra_legacy_controller.py`

**Rutas**:
```
POST /api/liquidaciones/edificaciones/legacy/nueva-liquidacion/primera-revision
POST /api/liquidaciones/taludes/legacy/nueva-liquidacion/primera-revision
POST /api/liquidaciones/impacto-vial/legacy/nueva-liquidacion/primera-revision
POST /api/liquidaciones/habilitacion-urbana/legacy/nueva-liquidacion/primera-revision
POST /api/liquidaciones/mecanica-suelos/legacy/nueva-liquidacion/primera-revision
POST /api/liquidaciones/inspeccion-obra/legacy/nueva-liquidacion/primera-revision
```

**Patrón**:
```python
@route.post(
    "/legacy/nueva-liquidacion/primera-revision",
    response={200: ApiResponse[LiquidacionEdificacionesOutput]},  # ← output schema existente
)
def crear_primera_revision(self, request, payload: LiquidacionEdificacionesLegacyInput):
    usuario_id = self.auth_core_service.get_authenticated_user_id(request)
    domain_result = self.orchestrator.crear_primera_revision_proceso(
        usuario_id=usuario_id, payload_in=payload
    )
    result = self.presenter.present_primera_revision(domain_result)  # ← presenter existente
    return success_response(result)
```

**Verificación**: cada endpoint responde correctamente con el output schema existente.

---

### Tarea 7: DI wiring + API routes

**Archivos a modificar** (solo aditivo):
- `backend/modules/liquidaciones/di.py` — añadir bindings para los 18 nuevos artefactos
- `backend/config/api.py` — registrar las 6 nuevas rutas

**Verificación**: hacer un `curl` o test de integración contra cada endpoint y verificar que responde 200.

---

### Tarea 8: Tests

**Tests a crear**:
- Unit tests para cada `*_por_fecha` method en los 3 core services legacy
- Integration tests para cada flujo legacy con fecha hace 6/12 meses
- Tests de verificación de que la `fecha_registro` de la `LiquidacionGeneral` persiste correctamente
- Tests de verificación de que las tarifas/IGV/UIT usados son los históricamente correctos

**Verificación**: `pytest` pasa al 100% para los nuevos archivos.

## Riesgos

### Riesgo 1: Conflictos con migraciones pendientes del working tree
**Severidad**: Alta
**Descripción**: El working tree tiene cambios sin commitear de una tarea previa cancelada (migraciones finanzas 0005 y liquidaciones 0011 de otro agente). La migración 0010 de `fecha_registro` está en el working tree.
**Mitigación**: IGNORAR explícitamente esas migraciones. La implementación legacy NO toca migraciones de ningún tipo.

### Riesgo 2: `create_liquidacion_general` no acepta `fecha_registro`
**Severidad**: Media
**Descripción**: `create_liquidacion_general` (línea 125 del core service) no tiene parámetro `fecha_registro`. El campo se alimenta con `default=timezone.now` del modelo.
**Mitigación**: En el flujo legacy, después de llamar `create_liquidacion_general()`, hacer `lg.fecha_registro = fecha_registro; lg.save()` con el `fecha_registro` del payload antes de continuar. Es un override seguro porque `fecha_registro` no está en la firma original (no rompe nada existente).

### Riesgo 3: IGV y UIT no tienen filtro por fecha en sus managers
**Severidad**: Media
**Descripción**: `IGV.objects.vigente()` y `UIT.objects.vigente()` no aceptan `fecha`. Solo filtran `periodo_fin__isnull=True`.
**Mitigación**: En `LiquidacionLegacyPorVisitasCoreService.get_igv_por_fecha()` y `get_uit_por_fecha()`, hacer QuerySet filter manual:
```python
def get_igv_por_fecha(self, fecha):
    return IGV.objects.filter(
        periodo_inicio__lte=fecha,
    ).filter(
        models.Q(periodo_fin__isnull=True) | models.Q(periodo_fin__gte=fecha)
    ).order_by("-periodo_inicio").first()
```

### Riesgo 4: Debt técnica — HU y MS flujos existentes carecen de `@transaction.atomic`
**Severidad**: Baja (no es parte del scope legacy)
**Descripción**: Los flujos HU y MS existentes no tienen `@transaction.atomic` decorador. Los flujos legacy SÍ lo tendrán.
**Mitigación**: Los flujos legacy son 100% nuevos, no se modifican los existentes. No hay acción requerida.

### Riesgo 5: Repetición de código entre flujos vigentes y legacy
**Severidad**: Baja
**Descripción**: Los flujos legacy son casi idénticos a los vigentes, solo cambia la fuente de tarifas (`*_por_fecha` vs `*_vigente`) y el override de `fecha_registro`.
**Mitigación**: Aceptable por ahora. Futuro refactor: extraer un base class `BaseLiquidacionFlujo` con templates method para `resolve_tarifa()`, `resolve_derecho()`, `resolve_igv()`, `resolve_uit()` — pero NO es parte del scope actual.

## Dependencias entre tareas

```
Tarea 1 (Core *por_fecha)
  ├─ Tarea 2 (Legacy schemas) ──────► (schemas dependen de los core services para tipado)
  │     └─ Tarea 3 (Legacy orchestrators)
  │           └─ Tarea 4 (Legacy flujos)
  │                 └─ Tarea 6 (Controllers legacy)
  │                       └─ Tarea 7 (DI + API routes)
  └─ Tarea 8 (Tests) — puede correr en paralelo desde Tarea 4
```

**Orden recomendado**:
1. Tarea 1 (Core)
2. Tarea 2 (Schemas) — en paralelo con T1
3. Tarea 3 (Orchestrators) — después de T2
4. Tarea 4 (Flujos) — después de T1+T3
5. Tarea 6 (Controllers) — después de T3+T4
6. Tarea 7 (DI + Routes) — después de T6
7. Tarea 8 (Tests) — después de T4, en paralelo con T6/T7

**Decisión pendiente del usuario**: ¿Tareas 2 y 1 pueden ejecutarse en paralelo o hay que esperar Tarea 1 completa antes de definir los schemas?
