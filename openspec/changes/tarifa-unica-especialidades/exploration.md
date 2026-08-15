# SDD Exploration: Tarifa Única por Periodo + Especialidades Disponibles

## Status
**success**

---

## Executive Summary

Explored the full codebase for the proposed change: transforming `TarifaPorcentajeObra` from "one tariff per especialidad" (current) to "one single general tariff per period" where all 3 specialties point to that same tariff. The exploration confirms the change is substantial — it touches models, core services, orchestrators, schemas, presenters, frontend forms, and tests across 3 liquidacion types (Edificaciones, Taludes, Impacto Vial).

**Key findings:**
1. **Current state**: `TarifaPorcentajeObra` HAS `especialidad` FK — the tariff IS per-especialty. Each specialty has its own `porcentaje_liquidacion`. `LiquidacionPorcentajeObraDetalle` creates one detail record PER `TarifaPorcentajeObra` (so potentially multiple details per specialty if there are multiple tariffs).
2. **User's manual changes**: (a) Added `VigenciaModel` to `LiquidacionEspecialidadDisponibles`, (b) removed `numero_registro`, `telefono`, `email` fields from `InspectorTipoLiquidacion`.
3. **No existing match logic**: The frontend calls `/liquidaciones/delegados/vigentes?revision_id=X` but this endpoint doesn't exist in the backend. The `Delegado` model has `especialidad_revision` FK, but there's no logic matching delegate specialty to liquidacion specialty.
4. **Backend doesn't have `revision_id` endpoint for delegados** — the frontend is calling an endpoint that doesn't exist yet.

---

## 1. Estado Actual de la Tarifa y Detalle Porcentaje de Obra

### 1.1 `TarifaPorcentajeObra` — Modelo (backend/modules/liquidaciones/domain/models/liquidacion/liquidacion_tipo/tarifas_reglas.py:122)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | PK |
| `tarifa_base` | FK → `TarifaLiquidacionBase` | OneToOne (Cabecera de tarifa por periodo) |
| `especialidad` | FK → `EspecialidadRevision` | **Especialidad a la que aplica esta tarifa** |
| `porcentaje_liquidacion` | Decimal(7,4) | Porcentaje (ej: 0.0015 para 0.15%) |
| `created_at`, `updated_at` | DateTime | Auditoría |
| `history` | HistoricalRecords | Tracking histórico |

**Constraint actual**: No unique constraint sobre `(tarifa_base, especialidad)` — permite múltiples tarifas por misma especialidad dentro del mismo periodo base.

**Admin**: Muestra `tarifa_base` + `especialidad` + `porcentaje_liquidacion` (líneas 80-90 de tarifas_admin.py).

### 1.2 `LiquidacionPorcentajeObraDetalle` — Modelo (liquidacion_tipo.py:242)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID | PK |
| `liquidacion_porcentaje` | FK → `LiquidacionPorcentajeObra` | Parent OneToOne |
| `tarifa_aplicada` | FK → `TarifaPorcentajeObra` | Tarifa concreta usada |
| `especialidad` | FK → `EspecialidadRevision` | **Copia de tarifa_aplicada.especialidad** |
| `porcentaje_aplicado` | Decimal(7,4) | Copia de tarifa.porcentaje_liquidacion |
| `subtotal`, `igv`, `uit`, `total` | Decimal(10,2) | Montos calculados |
| `created_at`, `updated_at` | DateTime | Auditoría |

**Constraint actual** (líneas 318-323):
```python
UniqueConstraint(fields=["liquidacion_porcentaje", "especialidad"], name="unique_liquidacion_porcentaje_detalle_especialidad")
```
**YA hay un unique por `(liquidacion_porcentaje, especialidad)`** — ya es "unique key", no "full many". Esto sugiere que el usuario ya tiene la restricción de un detalle por especialidad.

### 1.3 `LiquidacionPorcentajeObra` — Modelo (liquidacion_tipo.py, líneas ~155-239)

OneToOne con `LiquidacionGeneral`. Contiene:
- `tipo_tramite` (nullable, para future)
- `valor_declarado`
- `porcentaje_liquidacion` (SUM de todas las tarifas)
- `derecho_minimo`, `derecho_maximo`, `porcentaje_minimo_uit`
- `tarifas_aplicadas`: ManyToMany con `TarifaPorcentajeObra` (through `LiquidacionPorcentajeObraDetalle`)
- `derecho_aplicado`: FK → `DerechoPorcentajeObra`

**Relación detalle**: `liquidacion_porcentaje.detalles.all()` → devuelve N detalles (uno por especialidad).

### 1.4 `TarifaLiquidacionBase` (la cabecera de periodo)

- `tipo_liquidacion`: FK → `TipoLiquidacion`
- `periodo_inicio`, `periodo_fin`: Fechas de vigencia
- Cada `TarifaPorcentajeObra` tiene FK → `TarifaLiquidacionBase` (OneToOne declarada en línea 137-147 con `null=True, blank=True` temporario)

### 1.5 Conclusion sobre estado actual

> **El usuario dice "ya está prácticamente así" — esto es PARCIALMENTE correcto.**

- ✅ El detalle YA tiene constraint unique por `(liquidacion_porcentaje, especialidad)` — un registro por especialidad.
- ❌ La tarifa NO es única por periodo — hoy `TarifaPorcentajeObra` tiene FK a `especialidad`, lo que significa que cada especialidad tiene su propia tarifa con su propio `porcentaje_liquidacion`.
- Para que sea "tarifa única por periodo", `TarifaPorcentajeObra` debería NO tener FK a especialidad y en su lugar el `porcentaje_liquidacion` sería único/global para el periodo.

---

## 2. Cambios Manuales del Usuario (Working Tree)

### 2.1 `LiquidacionEspecialidadDisponibles` (liquidacion.py:313)

**Antes**:
```python
class LiquidacionEspecialidadDisponibles(BaseModel):
```

**Después** (working tree):
```python
class LiquidacionEspecialidadDisponibles(BaseModel, VigenciaModel):
```

Se le agregó herencia de `VigenciaModel`, lo que le da `periodo_inicio` y `periodo_fin`. Esto permite que las especialidades disponibles tengan vigencia temporal.

**Modelo completo actual**:
- `tipo_liquidacion`: FK → `TipoLiquidacion`
- `especialidad`: FK → `EspecialidadRevision`
- `activo`: BooleanField
- `periodo_inicio`, `periodo_fin`: Heredados de VigenciaModel
- **Constraint**: `unique_together = (tipo_liquidacion, especialidad)` → una sola combinación

### 2.2 `InspectorTipoLiquidacion` (inspector.py:45)

**Eliminado** (campos removidos en working tree):
```python
# ELIMINADO:
numero_registro = models.CharField(max_length=50, ...)
telefono = models.CharField(max_length=20, null=True, blank=True, ...)
email = models.EmailField(max_length=100, null=True, blank=True, ...)
```

**Queda**:
- `inspector`: FK → `Inspector`
- `tipo_liquidacion`: FK → `TipoLiquidacion`
- `categoria`: CharField(1) —留下来

---

## 3. Flujo de Primera Revisión (Porcentaje de Obra)

### Paso a paso: `POST /liquidaciones/edificaciones/nueva-liquidacion/primera-revision`

**Input Schema** (`LiquidacionEdificacionesInput`, liquidacion_edificaciones_schemas.py:31):
```python
class LiquidacionEdificacionesInput(BaseSchema):
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorcentajeObraIn
        # datos: { valor_declarado: Decimal }
        # tarifas: List[LiquidacionPorcentajeObraTarifaIn]
        #   donde LiquidacionPorcentajeObraTarifaIn = { tarifa_porcentaje_obra_id: UUID }
```

**Flujo** (archivo:línea):

1. **Controller** (`liquidacion_edificaciones_controller.py` → `crear_primera_revision`):
   - Recibe `LiquidacionEdificacionesInput`
   - Extrae `usuario_id` del request
   - Llama `orchestrator.crear_primera_revision_proceso(usuario_id, payload)`

2. **Orchestrator** (`liquidacion_edificaciones_orchestrator.py:93` → `crear_primera_revision_proceso`):
   - Valida `valor_declarado > 0`
   - Extrae `payload_tarifas_ids = [t.tarifa_porcentaje_obra_id for t in payload.liquidacion_especifica.tarifas]`
   - **Resolución híbrida** (líneas 114-126):
     - Si `tarifas_ids` vacío → auto-fill: `resolver_tarifas([], TipoLiquidacion.EDIFICACION)` → obtiene TODAS las vigentes
     - Si tiene IDs → validación explícita: solo acepta IDs válidos y vigentes
   - Obtiene `igv_vigente`, `uit_vigente`, `derecho`
   - Construye `EdificacionesPrimeraRevisionData` wrapper
   - **Delegate a Flujo**: `flujo.ejecutar_primera_revision(...)`

3. **Core Service** (`liquidacion_porcentaje_obra_core_service.py:84` → `calcular_cotizacion_po`):
   - Recibe `valor_declarado`, `tarifas: List[TarifaPorcentajeObra]`, `igv_porcentaje`, `derecho`, `uit_valor`
   - **Paso 1-2**: `porcentaje_total = SUM(t.porcentaje_liquidacion for t in tarifas)` — se suman todos los porcentajes
   - **Paso 3-4**: `minimo = uit_valor * derecho.porcentaje_minimo_uit`; `subtotal_total = max(subtotal_bruto, minimo)`
   - **Paso 5**: Clamp a `derecho_maximo` si aplica
   - **Paso 6**: **Reparto proporcional** entre detalles:
     ```python
     for tarifa in tarifas:
         proporcion = tarifa.porcentaje_liquidacion / porcentaje_total
         subtotal_detalle = subtotal_total * proporcion
         # ... crea DetallePorcentajeObraData
     ```
   - **Retorna**: `CotizacionPorcentajeObraData` con `detalles: List[DetallePorcentajeObraData]`

4. **Flujo** (`liquidacion_edificaciones_flujo.py` → `_build_result`):
   - Crea `LiquidacionPorcentajeObra` + N `LiquidacionPorcentajeObraDetalle` en DB
   - Cada detalle copia `tarifa_aplicada.especialidad`

### Punto clave del cálculo

**El cálculo actual SUMA los porcentajes de todas las tarifas** (línea 109 de core_service):
```python
porcentaje_total = sum((t.porcentaje_liquidacion for t in tarifas), Decimal("0"))
```

Si solo hay UNA tarifa con un único `porcentaje_liquidacion`, el cálculo sería ese único valor.

### Endpoint `cotizar` equivalente

- `POST /liquidaciones/edificaciones/cotizar`
- Schema: `LiquidacionEdificacionesCotizarInput` → `LiquidacionPorcentajeObraIn`
- Mismo flujo de resolución híbrida y cálculo

---

## 4. Tarifas Vigentes por Especialidad — Endpoint y Presenter

### Endpoint

`GET /liquidaciones/edificaciones/tarifas/vigentes`

Controller: `liquidacion_edificaciones_controller.py` → `get_tarifas_vigentes`

### Presenter

`LiquidacionImpactoVialPresenter.present_tarifas_vigkeiten()` (líneas 232-247) — usado también para edificaciones:

```python
return {
    "tarifas": [
        {
            "id": str(t.id),
            "especialidad": t.especialidad.nombre,
            "porcentaje_liquidacion": float(t.porcentaje_liquidacion),
        }
        for t in tarifas
    ],
}
```

**Devuelve una lista de tarifas, cada una con su especialidad** — esto es el problema de diseño actual. Si se cambia a tarifa única, el presenter debería devolver UNA sola tarifa por periodo (sin especialidad agrupada).

---

## 5. Mapa del Match Delegados ↔ Especialidad

### Modelos relacionados

**`Delegado`** (delegado.py:14):
- `perfil_ingeniero`: OneToOne → `PerfilIngeniero`
- `especialidad_revision`: FK → `EspecialidadRevision` (nullable, línea 29-36)

**`DelegadoMunicipalidad`** (delegado.py:48):
- `delegado`: FK → `Delegado`
- `municipalidad`: FK → `Municipalidad`
- `liquidacion_revision`: FK → `TipoLiquidacion` (nullable)
- `tipo`: CharField (TITULAR/SUPLENTE)

**`DelegadoMunicipalidadPeriodo`** (delegado.py:100):
- Hereda de `VigenciaModel` → `periodo_inicio`, `periodo_fin`
- `delegado_municipalidad`: FK → `DelegadoMunicipalidad`

**`LiquidacionDelegado`** (delegado.py:122):
- `liquidacion`: FK → `LiquidacionGeneral`
- `delegado`: FK → `Delegado`
- `periodo`, `dictamen_revision`, `fecha_presentacion`, `fecha_revision`

### Match actual (NO existe)

El `Delegado` tiene `especialidad_revision` FK, pero:
1. **No hay lógica en el backend** que filtre `Delegado` por `especialidad_revision == LiquidacionEspecialidadDisponibles.especialidad`.
2. El frontend llama `/liquidaciones/delegados/vigentes?revision_id=X&municipalidad_id=Y&tipo_liquidacion=Z` pero **este endpoint NO existe en el backend** — la ruta actual es `/delegados/` con filtros `cip, municipalidad_id, capitulo_id, especialidad_id, estado` (delegado_controller.py:50-74).

### Backend actual `GET /delegados/` (delegado_controller.py:50)

Parámetros: `cip`, `municipalidad_id`, `capitulo_id`, `especialidad_id`, `estado`

El `especialidad_id` filtra por `Delegado.especialidad_revision_id`, NO por las especialidades disponibles de la liquidación.

### Frontend `GestionarDelegadosModal` (frontend)

Línea 56-62 del modal:
```typescript
const { data } = await api.get("/liquidaciones/delegados/vigentes", {
  params: {
    municipalidad_id: municipalidadId,
    tipo_liquidacion: tipoLiquidacion,
    revision_id: revisionId,  // ← NO EXISTE en backend
  },
});
```

### Match propuesto por el usuario

Cuando se crea una liquidación con especialidades disponibles:
1. Las especialidades aceptadas se guardan en `LiquidacionEspecialidadDisponibles`
2. Se buscan los delegados cuya `especialidad_revision` coincida con alguna de esas especialidades
3. Esos delegados filtrados se muestran en el modal de asignación

**Falta implementar**: endpoint o lógica de match.

---

## 6. Seeds y Tests que tocan esto

### Seeds

- `seed_tarifas_edificacion.py`: Crea `EspecialidadRevision` y `TarifaLiquidacionBase` + `TarifaPorcentajeObra` por especialidad
- `seed_tarifas_all.py`: Invoca todos los seeds por tipo
- `seed_delegados.py`: Crea `Delegado`, `DelegadoMunicipalidad`, `DelegadoMunicipalidadPeriodo`

### Tests relevantes

| Test | Archivo | Qué toca |
|------|---------|---------|
| `test_edificaciones_tarifas_vigentes` | test_edificaciones_tarifas_vigentes.py | `TarifaPorcentajeObra` + `Especialidad` |
| `test_edificaciones_nueva_liquidacion` | test_edificaciones_nueva_liquidacion.py | `crear_primera_revision` + `LiquidacionPorcentajeObra` |
| `test_edificaciones_nueva_revision` | test_edificaciones_nueva_revision.py | `crear_nueva_revision` + detalle |
| `test_delegados` | test_delegados.py | `Delegado`, `DelegadoMunicipalidad` |
| `test_edificaciones_detail` | test_edificaciones_detail.py | `LiquidacionPorcentajeObraDetalle` |
| `test_e2e_edificaciones` | test_e2e_edificaciones.py | Flujo completo |
| `test_tarifas_historicas` | test_tarifas_historicas.py | `TarifaPorcentajeObra` grouping |

### Estimado de tests a tocar

- **Alto impacto**: 4+ tests de integración que crean liquidaciones con tarifas
- **Medio impacto**: tests de detalheo y tarifas vigentes
- **Bajo impacto**: tests de delegados (el modelo no cambia, solo la lógica de match)

---

## 7. Impacto Estimado del Cambio

### Archivos a tocar (backend)

| Capa | Archivo | Cambio |
|------|---------|--------|
| **Modelo** | `tarifas_reglas.py` | Remover `especialidad` FK de `TarifaPorcentajeObra`. Agregar `porcentaje_liquidacion` directo en `TarifaLiquidacionBase` o mantener en `TarifaPorcentajeObra` sin FK especialidad |
| **Modelo** | `liquidacion_tipo.py` | `LiquidacionPorcentajeObraDetalle` — cambiar `especialidad` FK por valor copiado (ya viene de tarifa pero sin FK) |
| **Modelo** | `liquidacion_general/liquidacion.py` | `LiquidacionEspecialidadDisponibles` — ya tiene VigenciaModel, revisar si necesita más campos para el match |
| **Schema** | `porcentaje_schemas.py` | `LiquidacionPorcentajeObraTarifaIn` — cambia de `tarifa_porcentaje_obra_id` a algo nuevo |
| **Schema** | `liquidacion_edificaciones_schemas.py` | Input/output para tarifas |
| **Core Service** | `liquidacion_porcentaje_obra_core_service.py` | `resolver_tarifas` — cambiar lógica de auto-fill, ya no filtra por especialidad |
| **Core Service** | `tarifas_historicas_core_service.py` | Grouping de detalle por especialidad |
| **Orchestrator** | `liquidacion_edificaciones_orchestrator.py` | `crear_primera_revision_proceso`, `cotizar_proceso` — cómo recibe especialidades |
| **Orchestrator** | `liquidacion_taludes_orchestrator.py` | Mismo cambio |
| **Orchestrator** | `liquidacion_impacto_vial_orchestrator.py` | Mismo cambio |
| **Orchestrator** | `delegado_orchestrator.py` | Nuevos filtros por especialidad de liquidación |
| **Presenter** | `liquidacion_porcentaje_presenter.py` / `present_tarifas_vigentes` | Cambiar salida de lista por especialidad → tarifa única |
| **Controller** | `liquidacion_edificaciones_controller.py` | Endpoint para match delegado-especialidad |
| **Admin** | `tarifas_admin.py` | Cambiar inline de `TarifaPorcentajeObra` |
| **Seeds** | `seed_tarifas_edificacion.py` | Cambiar estructura de seeding |
| **Seeds** | `seed_delegados.py` | Asegurar especialidades en delegados |

### Archivos a tocar (frontend)

| Archivo | Cambio |
|---------|--------|
| `TarifasPorcentajeSmartField.tsx` | Ya no muestra lista por especialidad — muestra tarifa única |
| `GestionarDelegadosModal.tsx` | `revision_id` → pasar specialties disponibles para filter |
| `useRevisionesVigentes.ts` | Schema cambia |
| Tipos `liquidacion-edificaciones.types.ts` | Actualizar tipos |

### Migración de datos

- Se necesita una migración para **remover** `especialidad` FK de `TarifaPorcentajeObra`
- Los datos existentes de `TarifaPorcentajeObra` tendrán que consolidarse: múltiples tarifas por mismo periodo/especialidad → 1 tarifa por periodo
- Los `LiquidacionPorcentajeObraDetalle` que referencian especialidades ya están bien (constraint unique)

---

## 8. Decisiones Pendientes (para el usuario)

1. **¿Dónde vive `porcentaje_liquidacion`?** Si la tarifa es "única por periodo", el porcentaje liquidado puede:
   - (A) Moverse a `TarifaLiquidacionBase` directamente (como `costo_por_m2` en M2)
   - (B) Quedar en `TarifaPorcentajeObra` pero sin FK a especialidad (un registro por periodo)
   - **Recomendación**: Opción B — mantiene la estructura parallel a M2 (`TarifaLiquidacionBase` + detalle específico por tipo)

2. **¿Qué pasa con los derechos (min/max)?** Los derechos (`DerechoPorcentajeObra`) siguen igual o también se unifican por periodo?

3. **El `unique_liquidacion_porcentaje_detalle_especialidad`** — ya existe. ¿Se mantiene así? ¿O se quiere un detalle por cada especialidad disponible (posible new field `LiquidacionEspecialidadDisponibles` usada en el detalle)?

4. **Match delegados**: ¿El nuevo endpoint `liquidaciones/delegados/vigentes` con `revision_id` es parte de este cambio o es un cambio separado? El frontend ya lo está llamando.

5. **`InspectorTipoLiquidacion`** — los campos eliminados (`numero_registro`, `telefono`, `email`) también deberían eliminarse del schema de output `InspectorOut` y del frontend. ¿O se van a restaurar de otra forma?

---

## 9. Riesgos

1. **⚠️ Breaking changes en schema API**: `LiquidacionPorcentajeObraTarifaIn` cambia de `tarifa_porcentaje_obra_id` (FK por especialidad) a algo nuevo — rompe el frontend actual que ya envía `tarifa_porcentaje_obra_id`.

2. **⚠️ Frontend desincronizado**: El frontend tiene `TarifasPorcentajeSmartField` que muestra y envía `tarifa.id` por especialidad — esto tendrá que cambiar completamente.

3. **⚠️ Migración compleja**: Consolidar `TarifaPorcentajeObra` de múltiples por especialidad → una por periodo requiere migrate datos existentes.

4. **⚠️ Endpoint inexistente**: El frontend llama `/liquidaciones/delegados/vigentes?revision_id=...` que no existe — si esto es parte del cambio, hay que crearlo.

5. **⚠️ Tests de integración**: 5+ tests que asumen `TarifaPorcentajeObra` con `especialidad` — fallarán hasta ser actualizados.

6. **⚠️ Historial de任何人**: `simple_history` está activo — los cambios de modelo afectarán el tracking histórico.

---

## 10. Next Recommended

---

# Documento de Impacto v2 — Tarifa única por periodo en porcentaje de obra (cambio DESTRUCTIVO)

> Generado: exploration exhaustiva completa. Persistido en Engram: `sdd/tarifa-unica-especialidades/impact-doc`.

---

## 1. Resumen ejecutivo

El cambio transforma `TarifaPorcentajeObra` de "una tarifa por especialidad por periodo" a "una sola tarifa por periodo" (sin FK a especialidad). Las especialidades ya NO viven en la tarifa — se mueven a `LiquidacionEspecialidadDisponibles` y se referencian desde `LiquidacionPorcentajeObraDetalle.especialidad` directamente. El cálculo `SUM(porcentaje_liquidacion)` se mantiene idéntico: si 3 especialidades apuntan a la misma tarifa, la suma del único `porcentaje_liquidacion` × 3 detalles = resultado correcto. El cambio toca 6 capas (modelo → migration → core → orquestador → presenter → frontend), 3 tipos de liquidación (Edificaciones, Taludes, Impacto Vial), y más de 25 archivos backend.

---

## 2. Estado actual vs objetivo

| Pieza | Estado actual | Estado objetivo |
|-------|--------------|-----------------|
| **TarifaPorcentajeObra** | FK `especialidad` → `EspecialidadRevision` (una tarifa por especialidad) | `especialidad` **ELIMINADA** — una sola tarifa por `TarifaLiquidacionBase`/periodo |
| **porcentaje_liquidacion** | En `TarifaPorcentajeObra` (se mantiene) | En `TarifaPorcentajeObra` (sin cambio — confirmado por usuario) |
| **LiquidacionPorcentajeObraDetalle** | `especialidad` copia de `tarifa_aplicada.especialidad` | `especialidad` copiada desde `LiquidacionEspecialidadDisponibles` — la tarifa NO tiene especialidad |
| **Input primera revisión** | `tarifas: List[LiquidacionPorcentajeObraTarifaIn]` — cada elemento con `tarifa_porcentaje_obra_id` (3 IDs, uno por especialidad) | Cambia a: `tarifa_porcentaje_obra_id` (1 ID) + `especialidades_ids: List[UUID]` (3 especialidades) |
| **Tarifas vigentes (GET)** | Devuelve N registros (1 por especialidad), cada uno con `especialidad.nombre` | Devuelve 1 registro (tarifa única), más `especialidades_disponibles` del periodo |
| **LiquidacionEspecialidadDisponibles** | Ya tiene `VigenciaModel` (cambio manual ya hecho) | Sin cambio de estructura — se usa como fuente de especialidades para la liquidación |
| **LiquidacionDelegado** | Ya existe con campos `especialidad_revision`, `periodo`, `dictamen_revision`, `fecha_presentacion`, `fecha_revision` | Ya está migrado según el usuario — verificar que coincide con la definición objetivo (delegado.py:122-181) |

---

## 3. Mapa de impacto por capa

### 3.1 Modelo (DESTRUCTIVO)

| Archivo | Qué cambia | Riesgo | Tipo |
|---------|-----------|--------|------|
| `tarifas_reglas.py:149-155` | **ELIMINAR** `especialidad = FK` de `TarifaPorcentajeObra` + nullable en FK `tarifa_base` | ALTO — rompe FK en todos los registros históricos | Los 3 tipos (Edific., Taludes, IV) |
| `liquidacion_tipo.py:242-323` | `LiquidacionPorcentajeObraDetalle.especialidad` deja de ser copia de `tarifa_aplicada.especialidad` — se popula desde `LiquidacionEspecialidadDisponibles` | ALTO — la constraint unique `(liquidacion_porcentaje, especialidad)` ya existe y es correcta | Los 3 tipos |
| `liquidacion_tipo.py:217-223` | `LiquidacionPorcentajeObra.tarifas_aplicadas` M2M through — puede simplificarse | MEDIO | Los 3 tipos |

### 3.2 Migration (DESTRUCTIVA)

| Archivo | Qué cambia | Riesgo |
|---------|-----------|--------|
| `migrations/0001_initial.py` (futura) | Eliminar columna `especialidad_id` de `TarifaPorcentajeObra` | ALTO — datos existentes se alteran. Requiere migración: 3 registros TarifaPorcentajeObra por periodo → 1 registro |

### 3.3 Core Service

| Archivo | Método | Qué cambia | Tipo |
|---------|--------|-----------|------|
| `liquidacion_porcentaje_obra_core_service.py:31-62` | `resolver_tarifas` | El auto-fill ya no filtra por especialidad (ya funciona así). La validación explícita cambia: ya no verifica `tarifa.especialidad` | Los 3 tipos |
| `liquidacion_porcentaje_obra_core_service.py:84-172` | `calcular_cotizacion_po` | **NO cambia la fórmula SUM** — `porcentaje_total = SUM(...)` sigue igual | Los 3 tipos |
| `tarifas_historicas_core_service.py:52-63` | `get_tarifas_porcentaje_obra_por_base` | El grouping cambia: `TarifaPorcentajeObra` ya no tiene `especialidad` | Los 3 tipos |

### 3.4 Orchestrators (3 archivos)

| Archivo | Qué cambia | Tipo |
|---------|-----------|------|
| `liquidacion_edificaciones_orchestrator.py:93` | `crear_primera_revision_proceso`: extrae `tarifa_id` + `especialidades_ids`. Construye N `TarifaPorcentajeObraAplicada` DTOs repitiendo la misma tarifa. `_validar_tarifa_explicita`: elimina validación `tarifa.especialidad` | Edificaciones |
| `liquidacion_edificaciones_orchestrator.py:204` | `cotizar_proceso`: mismo cambio | Edificaciones |
| `liquidacion_edificaciones_orchestrator.py:508` | `crear_nueva_revision_proceso`: mismo cambio | Edificaciones |
| `liquidacion_taludes_orchestrator.py:88` | `crear_primera_revision_proceso`: mismo patrón | Taludes |
| `liquidacion_taludes_orchestrator.py` | `cotizar_proceso`: mismo patrón | Taludes |
| `liquidacion_impacto_vial_orchestrator.py:88` | `crear_primera_revision_proceso`: mismo patrón | Impacto Vial |
| `liquidacion_impacto_vial_orchestrator.py` | `cotizar_proceso`: mismo patrón | Impacto Vial |

### 3.5 Flows (3 archivos)

| Archivo | Qué cambia | Tipo |
|---------|-----------|------|
| `liquidacion_edificaciones_flujo.py:139-145` | La reconstrucción de tarifas ORM itera sobre `po_data.tarifas` — con N especialidades pero 1 tarifa, se necesita deduplicación de IDs o ajuste del loop | Edificaciones |
| `liquidacion_taludes_flujo.py` | Mismo patrón | Taludes |
| `liquidacion_impacto_vial_flujo.py` | Mismo patrón | Impacto Vial |

### 3.6 Schemas (domain + presentation)

| Archivo | Qué cambia | Tipo |
|---------|-----------|------|
| `liquidacion_porcentaje_data.py:18-33` | `TarifaPorcentajeObraAplicada`: `especialidad_id/nombre` se pasan directamente, no de `tarifa.especialidad`. `LiquidacionPorcentajeObraData`: `tarifas` → `tarifa_id` + `especialidades_ids` | Los 3 tipos |
| `tarifas_historicas_results.py:10-16` | `TarifaPorcentajeObraDetalleResult.especialidad_id/nombre` viene de `LiquidacionEspecialidadDisponibles`, no de tarifa | Los 3 tipos |
| `porcentaje_schemas.py:18-20` | `LiquidacionPorcentajeObraTarifaIn` cambia de `{tarifa_porcentaje_obra_id}` a `{tarifa_porcentaje_obra_id, especialidades_ids}` | Los 3 tipos |
| `liquidacion_edificaciones_schemas.py` | Input/output para tarifas cambia | Edificaciones |
| `liquidacion_taludes_schemas.py` | Mismo | Taludes |
| `liquidacion_impacto_vial_schemas.py` | Mismo | Impacto Vial |

### 3.7 Presenters

| Archivo | Método | Qué cambia | Tipo |
|---------|--------|-----------|------|
| `liquidacion_edificaciones_presenter.py:255-269` | `present_tarifas_vigentes` | Devuelve 1 registro (no N). `especialidad` ya no viene de `t.especialidad.nombre` | Edificaciones |
| `liquidacion_taludes_presenter.py:232-247` | `present_tarifas_vigentes` | Mismo cambio | Taludes |
| `liquidacion_impacto_vial_presenter.py:232-247` | `present_tarifas_vigentes` | Mismo cambio | Impacto Vial |
| `tarifas_historicas_presenter.py` | grouping | `tarifas_porcentaje` ya no tiene especialidad de la tarifa | Los 3 tipos |

### 3.8 Admin

| Archivo | Qué cambia | Tipo |
|---------|-----------|------|
| `tarifas_admin.py:34-90` | `TarifaPorcentajeObraInline` y `TarifaPorcentajeObraAdmin`: eliminar columna `especialidad` | Los 3 tipos |

### 3.9 Seeds

| Archivo | Qué cambia | Tipo |
|---------|-----------|------|
| `seed_tarifas_edificacion.py:354-371` | Ya no itera por especialidad al crear `TarifaPorcentajeObra` | Edificaciones |
| `seed_tarifas_all.py:337-347` | Mismo | Los 3 tipos |
| `seed_tarifas.py:116` | Mismo | Los 3 tipos |

### 3.10 Frontend (SOLO LECTURA — reportar)

| Archivo | Qué hace hoy | Qué necesitará |
|---------|-------------|---------------|
| `TarifasPorcentajeSmartField.tsx:53-58` | `GET /liquidaciones/edificaciones/tarifas/vigentes` → muestra N cards (1 por especialidad) | Mostrar 1 card de tarifa única + selector de especialidades disponibles |
| `TarifasPorcentajePrimeraRevisionSmartField.tsx` | Similar | Mismo cambio |
| `GestionarDelegadosModal.tsx:56-62` | `GET /liquidaciones/delegados/vigentes?revision_id=X` — **endpoint no existe** | Necesita el endpoint backend (SDD separado?) |

---

## 4. Dependencia de cálculo — Explicación precisa

### Cómo funciona HOY (3 tarifas, cada una con especialidad diferente)

```
Input: tarifas_ids = [tarifa_esp1_id, tarifa_esp2_id, tarifa_esp3_id]

resolver_tarifas → [TarifaPO(esp1, 0.05%), TarifaPO(esp2, 0.05%), TarifaPO(esp3, 0.05%)]

calcular_cotizacion_po:
  porcentaje_total = SUM(t.porcentaje_liquidacion for t in tarifas)
                   = 0.05% + 0.05% + 0.05% = 0.15%
  subtotal_bruto = valor_declarado * 0.15%

  Reparto proporcional (step 6):
    - esp1: 0.05%/0.15% = 33.33% → subtotal = subtotal_bruto * 33.33%
    - esp2: igual
    - esp3: igual
```

### Cómo funciona con tarifa ÚNICA (1 tarifa, 3 especialidades apuntan a ella)

```
Input: tarifa_id = [tarifa_unica_id], especialidades = [esp1, esp2, esp3]

Orchestrator:
  - Obtiene la tarifa única: TarifaPO(porcentaje_liquidacion = 0.05%)
  - Construye N TarifaPorcentajeObraAplicada DTOs (N = len(especialidades)):
      TarifaPorcentajeObraAplicada(tarifa_id=tarifa_unica_id,
                                   porcentaje_liquidacion=0.05%,
                                   especialidad_id=esp1_id, ...) × 3

calcular_cotizacion_po (NO CAMBIA):
  porcentaje_total = SUM(t.porcentaje_liquidacion for t in tarifas)
                   = 0.05% + 0.05% + 0.05% = 0.15%  ← ¡MISMO!
  subtotal_bruto = valor_declarado * 0.15%  ← ¡MISMO!
```

**El cálculo NO cambia si las 3 especialidades apuntan a la misma tarifa con el mismo `porcentaje_liquidacion`**. El usuario tenía razón: "si meto 3 tarifas me debería afectar igualmente el cálculo".

### Input: ¿Cómo se pasa?

**Opción A (recomendada)**: `tarifa_id: UUID` + `especialidades_ids: List[UUID]`
- Frontend envía 1 ID de tarifa + lista de especialidades
- Backend construye N detalles, todos con la misma `tarifa_aplicada`
- Flexible: permite al usuario elegir subconjunto de especialidades

**Opción B**: Solo `tarifa_id`, backend deduce especialidades de `LiquidacionEspecialidadDisponibles`
- Menos flexible — no permite subconjunto

---

## 5. Módulos de tareas sugeridos (en orden de dependencia)

### FASE 1: Modelo + Migration

**Tarea 1.1** — `tarifas_reglas.py:149-155`: Eliminar `especialidad = FK` de `TarifaPorcentajeObra`. Mantener `porcentaje_liquidacion`. Sin dependencias. Independendiente: Sí.

**Tarea 1.2** — Migration: Eliminar columna `especialidad_id`. Depende de 1.1. Independendiente: No.

### FASE 2: Domain Schemas + Domain DTOs

**Tarea 2.1** — `liquidacion_porcentaje_data.py`: Cambiar `LiquidacionPorcentajeObraData.tarifas` → `tarifa_id` + `especialidades_ids`. `TarifaPorcentajeObraAplicada` recibe `especialidad_id/nombre` directamente. Depende de 1.1.

**Tarea 2.2** — `tarifas_historicas_results.py`: `TarifaPorcentajeObraDetalleResult.especialidad_id/nombre` ya no viene de `TarifaPorcentajeObra`. Depende de 2.1.

### FASE 3: Core Service

**Tarea 3.1** — `liquidacion_porcentaje_obra_core_service.py`: `resolver_tarifas` cambia validación explícita. `create_liquidacion_porcentaje_obra` recibe `especialidades` directamente en lugar de iterar `tarifa.especialidad`. Depende de 2.1.

**Tarea 3.2** — `tarifas_historicas_core_service.py:52-63`: `get_tarifas_porcentaje_obra_por_base` ya no puede hacer `select_related("especialidad")`. Las especialidades vienen de `LiquidacionEspecialidadDisponibles`. Depende de 2.2.

### FASE 4: Orchestrators (3 archivos, paralelizables)

**Tarea 4.1** — Edificaciones: `crear_primera_revision_proceso`, `cotizar_proceso`, `crear_nueva_revision_proceso`, `_validar_tarifa_explicita`. Depende de 3.1, 2.1.

**Tarea 4.2** — Taludes: mismo patrón. Depende de 3.1, 2.1.

**Tarea 4.3** — Impacto Vial: mismo patrón. Depende de 3.1, 2.1.

### FASE 5: Flows (3 archivos)

**Tarea 5.1** — Los 3 flows: deduplicar IDs de tarifa al reconstruir ORM o ajustar loop. Depende de 4.1, 4.2, 4.3.

### FASE 6: Presentation Schemas

**Tarea 6.1** — `porcentaje_schemas.py`: `LiquidacionPorcentajeObraTarifaIn` cambia a `{tarifa_porcentaje_obra_id, especialidades_ids}`. Depende de 2.1.

**Tarea 6.2** — Los 3 schemas de líquido específico. Depende de 6.1.

### FASE 7: Presenters (paralelizables)

**Tarea 7.1** — Los 3 `present_tarifas_vigentes`: la `especialidad` ya no viene de `t.especialidad.nombre`. Depende de 6.1.

**Tarea 7.2** — `tarifas_historicas_presenter.py`. Depende de 3.2.

### FASE 8: Admin

**Tarea 8.1** — `tarifas_admin.py`: eliminar `especialidad` de inline y admin. Depende de 1.1.

### FASE 9: Seeds

**Tarea 9.1** — Los 3 seed files: ya no itera por especialidad al crear `TarifaPorcentajeObra`. Depende de 1.1.

### FASE 10: Tests

**Tarea 10.1** — ~12 archivos de test que crean `TarifaPorcentajeObra` con `especialidad`. Actualizar fixtures. Depende de 1.1, 2.1.

### FASE 11: Frontend (SOLO REPORTADO — no ejecutar en backend SDD)

**Tarea 11.1** — `TarifasPorcentajeSmartField.tsx`: mostrar 1 tarifa + selector especialidades.

**Tarea 11.2** — `GestionarDelegadosModal.tsx`: el endpoint `/liquidaciones/delegados/vigentes?revision_id=X` no existe en backend.

---

## 6. Decisiones pendientes (para confirmar con el usuario)

1. **Input de especialidades**: ¿Frontend envía `especialidades_ids` explícitamente (Opción A — más flexible) o backend deduce de `LiquidacionEspecialidadDisponibles` (Opción B — más simple)?

2. **`LiquidacionDelegado` ya existe con los campos mencionados** (`delegado.py:122-181`). ¿Confirmar que coincide con la definición objetivo del usuario?

3. **`LiquidacionEspecialidadDisponibles` con `VigenciaModel`**: Las especialidades disponibles se eligen de las vigentes a la fecha de creación, ¿o son fijas por `TipoLiquidacion`?

4. **Migración de datos históricos**: ¿Los registros `TarifaPorcentajeObra` con `especialidad` (históricos) se consolidan a 1 por `TarifaLiquidacionBase`, o se mantienen nullable?

5. **`tarifas_historicas` sin especialidad en tarifa**: Si `TarifaPorcentajeObra` ya no tiene `especialidad`, ¿de dónde viene `especialidad_id/nombre` en el resultado histórico? ¿De `LiquidacionEspecialidadDisponibles` o de `LiquidacionDelegado.especialidad_revision`?

6. **Endpoint `/liquidaciones/delegados/vigentes`**: ¿Es parte de este cambio o un SDD separado?

---

## 7. Riesgos

1. **⚠️ BREAKING CHANGE en schema API**: `LiquidacionPorcentajeObraIn.tarifas` cambia. Frontend actual envía formato antiguo → falla hasta actualización sincronizada.

2. **⚠️ Migration de datos destructiva**: Eliminar `especialidad_id` requiere consolidar 3 registros → 1. Si hay históricos con diferentes `porcentaje_liquidacion` por especialidad, se pierde información.

3. **⚠️ Test suite grande**: 12+ archivos de test asumen `TarifaPorcentajeObra` con `especialidad`.

4. **⚠️ `tarifas_historicas` pierde contexto de especialidad**: Sin `TarifaPorcentajeObra.especialidad`, la vista "tarifas por periodo" pierde la dimensión especialidad en el grouping.

5. **⚠️ Seeds con cambio de paradigma**: Los seeds asumen 1 `TarifaPorcentajeObra` por especialidad — requieren restructure.

6. **⚠️ Frontend desincronizado**: 2 componentes que envían `tarifas_porcentaje_obra_id` y consumen `especialidad.nombre` del response requieren cambio sincronizado.

---

## 8. Estimación

| Dimensión | Estimado |
|-----------|----------|
| **Archivos backend** | ~25 archivos |
| **Líneas de código cambiadas** | ~800-1200 (backend) |
| **Migrations** | 1 (destructiva, elimina FK `especialidad`) |
| **Tests tocados** | ~12 archivos |
| **Seeds tocados** | 3 archivos |

### Orden de ejecución
```
1 → 2 → 3 → 4.1, 4.2, 4.3 (paralelo) → 5 → 6.1 → 6.2 → 7.1, 7.2 (paralelo) → 8 → 9 → 10
```

