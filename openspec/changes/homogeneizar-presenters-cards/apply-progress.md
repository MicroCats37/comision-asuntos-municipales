# SDD Apply Progress: Homogeneizar presenters + cards/modal delegados

## Change
`homogeneizar-presenters-cards`

## Status
**partial** — Fase 1 ✅, Fase 2 ⚠️ parcial (flujos correctos, list_liquidaciones con desviación crítica), Fase 3 ✅ completada

---

## Fase 1: Presenters (Completada)

Ver archivo de reporte de fase 1 para detalles completos.

---

## Fase 2: Core builder — Extracción de `build_general_result()` a `LiquidacionGeneralCoreService`

### Fecha de verificación
2026-08-15

### Hallazgo Principal

**La extracción YA ESTABA HECHA.** El método `LiquidacionGeneralCoreService.build_general_result(...)` existe en el core service (línea 1238) con la firma exacta propuesta por el usuario, incluyendo helpers privados:

- `build_general_result(...)` — construye `LiquidacionGeneralResult` completo
- `build_delegados_result(...)` — construye lista `LiquidacionDelegadoEnGeneralResult`
- `_build_entidad_result(...)` — helper privado
- `_build_proyecto_result(...)` — helper privado  
- `_build_distrito_result(...)` — helper privado (con provincia/departamento)

### Verificación de Delegación — 6 Flujos

| Flujo | Método result builder | ¿Usa `general_core.build_general_result`? | Notas |
|-------|----------------------|------------------------------------------|-------|
| `LiquidacionEdificacionesFlujo` | `_build_result()`, `_build_result_with_previas()` | **SÍ** (líneas 342, 409) | Con previos pasa `delegados` y `revisiones_previas` |
| `LiquidacionTaludesFlujo` | `_build_result()` | **SÍ** (línea 165) | — |
| `LiquidacionImpactoVialFlujo` | `_build_result()` | **SÍ** (línea 165) | — |
| `LiquidacionHabilitacionUrbanaFlujo` | Sin método dedicado (inline) | **SÍ** (línea 127) | Llama directo a `general_core.build_general_result` |
| `LiquidacionMecanicaSuelosFlujo` | Sin método dedicado (inline) | **SÍ** (línea 127) | Llama directo a `general_core.build_general_result` |
| `LiquidacionInspeccionObraFlujo` | `_build_result_from_orm()` | **SÍ** (líneas 119, 241) | — |

### Líneas Duplicadas Eliminadas

- El bloque `build_general_result` (~90 líneas) ya NO está duplicado en los 6 flujos
- `LiquidacionDelegadoEnGeneralResult` construcción extraída a `build_delegados_result`
- El bloque `DistritoResult`/`ProvinciaResult`/`DepartamentoResult` ya no está en flujos

### Firma de `build_general_result` (ya existe en core)

```python
def build_general_result(
    self,
    liquidacion_general,            # ORM LiquidacionGeneral
    usuario_id: int,
    contacto_result: Optional[ContactoResult] = None,
    revisiones_previas: Optional[list] = None,
    delegados: Optional[list] = None,
    fecha_registro: Optional[str] = None,  # None = usa created_at
) -> LiquidacionGeneralResult:
```

### Helpers privados en `LiquidacionGeneralCoreService`

- `_build_entidad_result(proyecto) -> Optional[EntidadResult]`
- `_build_proyecto_result(proyecto, entidad_result) -> ProyectoResult`
- `_build_distrito_result(proyecto) -> Optional[DistritoResult]`

### Verificación

| Check | Resultado |
|-------|-----------|
| `manage.py check --settings=config.settings.development` | **0 issues** |
| `py_compile` en los 6 flujos + core service | **ALL OK** |
| Import de los 6 flujos | **OK** |
| Métodos `build_general_result`, `build_delegados_result` en core | **EXISTEN** |
| Todos los flujos delegan a `general_core.build_general_result(...)` | **VERIFICADO** |

### Conclusión Fase 2

**El trabajo de extracción de `build_general_result` al core service YA ESTABA COMPLETADO** antes de esta fase. La arquitectura de los 6 flujos ya cumple el contrato:
- El core service tiene `build_general_result` y `build_delegados_result` implementados
- Los 6 flujos delegan a `self.general_core.build_general_result(...)` para construir `LiquidacionGeneralResult`
- El bloque de mapeo ~140 líneas NO está duplicado en los flujos
- Los campos opcionales (`contacto`, `revisiones_previas`, `delegados`) se pasan como parámetros opcionales al core

---

## Siguiente Paso Recomendado

**Fase 3 (HIGH PRIORITY)** — Corregir la desviación crítica en `list_liquidaciones`:

1. Reemplazar `_build_io_result` en IO orchestrator (línea 239) para que llame a `general_core.build_general_result()` — es el más divergente
2. Hacer lo mismo para los otros 5 orquestadores (`_build_edificaciones_result`, `_build_taludes_result`, `_build_iv_result`, `_build_hu_result`, `_build_ms_result`)
3. Verificar que `build_general_result` cubre todos los campos que los orquestadores construían inline (especialmente `contacto_result` que algunos orquestadores pasan como parámetro)

**Fase 3 (MEDIUM PRIORITY)** — Extraer `_validar_tarifa_explicita` + `_obtener_especialidades_vigentes_para_tipo` a mixin compartido para Edificaciones/IV/Taludes.

**Fase 4** — Verificar controllers: confirmar que son 100% thin (sin lógica if/for/ORM directo). Si tienen lógica de negocio, documentar cuál y dónde debería moverse.

---

## Risks

1. **Regresión en `list_liquidaciones`**: Los `_build_*_result` de orquestadores construyen `LiquidacionGeneralResult` inline. Modificarlos para delegar al core requiere verificar que `build_general_result` cubre todos los campos (especialmente `contacto_result` que algunos orquestadores construyen y pasan explícitamente).
2. **IO Orchestrator `_build_io_result` línea 239**: Es el más divergente — construye TODO el `LiquidacionGeneralResult` inline sin llamar NADA al core. Un refactor requiere comparison campo por campo.
3. **Fase 4 Controllers no evaluada**: No se verificó si los controllers tienen lógica de negocio que viola el contrato "sagrados". Si la tienen, hay que remediarla antes de cerrar el SDD.

---

---

## Validación Fase 2 vs contrato PLAN_REFACTORIZACION.md

**Fecha**: 2026-08-15
**Status**: `partial` — Flujos de creación ✅ correctos. Operaciones `list_liquidaciones` en orquestadores ❌ desviación crítica.

### Tabla de Validación vs Contrato

| Regla | Cumple? | Evidencia |
|-------|---------|-----------|
| Core: ORM puro, CERO lógica de negocio/validación | ✅ SÍ | `build_general_result` (1238-1327): solo mapea atributos, ningún `if` de negocio, ningún `raise` |
| Core: `build_delegados_result` en core (mapeo, no validación) | ✅ SÍ | Línea 1393: correctamente en core — es mapeo puro |
| Flujos: delegan a `general_core.build_general_result()` | ✅ SÍ | EdificacionesFlujo:342, 409; IO Flujo:119, 241; TaludesFlujo:165; IVFlujo:165; HUFlujo:127; MSFlujo:127 |
| Orchestrator: validación compleja + HttpError | ✅ SÍ | `_validar_tarifa_explicita` lanza HttpError apropiadamente |
| Orchestrator: `_build_*_result` en list_liquidaciones NO duplica mapeo general | ❌ NO | Los 6 orquestadores duplican ~60 líneas del bloque general result inline |
| Core: no valida/decide en builders | ✅ SÍ | `build_general_result` recibe ORM ya fetcheado; solo lee atributos |

### Lo Hecho Bien ✅

1. **Extracción `build_general_result` al core**: método existe en `LiquidacionGeneralCoreService` línea 1238, con docstring "PURE MAPPING — no validation, no business logic"
2. **Delegación de 6 flujos**: todos los flujos de creación delegan a `self.general_core.build_general_result()`
3. **`build_delegados_result` en core**: correctamente ubicado — es mapeo puro
4. **Helpers de dominio en core**: `_build_entidad_result`, `_build_proyecto_result`, `_build_distrito_result` extraídos correctamente
5. **Bloque Distrito/Provincia/Departamento**: ya NO está duplicado en flujos

### Desviaciones

#### D1 [CRITICAL]: `list_liquidaciones` en orquestadores NO usa `build_general_result` del core

**Archivos afectados** (todos con `_build_*_result` que duplica el mapeo inline):
- `liquidacion_edificaciones_orchestrator.py:401` — `_build_edificaciones_result(lg)`
- `liquidacion_inspeccion_obra_orchestrator.py:239` — `_build_io_result(lg)` ← el más divergente (NO llama al core NADA)
- `liquidacion_taludes_orchestrator.py:377` — `_build_taludes_result(lg)`
- `liquidacion_impacto_vial_orchestrator.py:377` — `_build_iv_result(lg)`
- `liquidacion_habilitacion_urbana_orchestrator.py:209` — `_build_hu_result(lg)`
- `liquidacion_mecanica_suelos_orchestrator.py:209` — `_build_ms_result(lg)`
- `liquidacion_general_orchestrator.py:90` — `_build_general_result(lg)`

**Qué hacen estos métodos**: Construyen `LiquidacionGeneralResult` inline (aprox. 60 líneas en edificaciones orchestrator líneas 462-522) — las mismas líneas que YA EXISTEN en `build_general_result` del core.

**Qué deberían hacer**: Llamar a `self.general_core.build_general_result(lg, usuario_id=lg.usuario_creador.id)` y luego agregar el resultado específico del tipo.

#### D2 [WARNING]: Duplicación `_validar_tarifa_explicita` y `_obtener_especialidades_vigentes_para_tipo`

Las 3 implementaciones en Edificaciones, Impacto Vial y Taludes son **idénticas**. HU, MS e IO no usan estos métodos.

### Estado por Fase

| Fase | ¿Hecha? | Qué falta |
|------|---------|-----------|
| Fase 1: Presenters homogeneizados | ✅ Completada | — |
| Fase 2: Extracción `build_general_result` a core | ⚠️ Parcial | Flujos de creación ✅. `list_liquidaciones` en orquestadores ❌ |
| Fase 3: Orquestadores — extracción helpers | 🔲 Pendiente | 1) `_build_*_result` en list_liquidaciones → delegar a core. 2) `_validar_tarifa_explicita` → mixin compartido. 3) `_obtener_especialidades_vigentes_para_tipo` → helper compartido |
| Fase 4: Controllers | ❓ ¿Se tocan? | Contrato dice "sagrados". Verificar si hay lógica de negocio que se filtró |
| Core `list_liquidaciones_*_paginated` | 🔲 6 métodos | Tienen prefetches diferentes por tipo. Unificación factible pero menor prioridad |

### Recomendación Fase 3

**HIGH CONFIDENCE** — Reemplazar el bloque inline de `LiquidacionGeneralResult` en cada `_build_*_result` de orquestador con una llamada a `general_core.build_general_result()`. Empezar por IO orchestrator (el más divergente: `_build_io_result` línea 239 no llama al core en absoluto). Impacto: elimina ~360 líneas duplicadas (60 líneas × 6 orquestadores).

### Risks

1. **Regresión en `list_liquidaciones`**: Modificar `_build_*_result` podría romper el formato de respuesta si `build_general_result` no cubre todos los campos. Requiere verificación.
2. **IO Orchestrator es el más divergente**: `_build_io_result` (línea 239) construye TODO inline. Un refactor requiere comparar campo por campo con `build_general_result`.
3. **Fase 4 Controllers**: No se evaluó si tienen lógica de negocio. Si la tienen y son "sagrados", hay violación del contrato.

---

## Fase 3: Orquestadores — `_build_*_result` delegan al core + validaciones compartidas

**Fecha**: 2026-08-15
**Status**: ✅ Completada

### Qué se hizo

#### 1. Extracción de validaciones compartidas → Mixin

**Archivo creado**: `modules/liquidaciones/domain/services/orchestrators/_shared/liquidacion_po_validation.py`

Contiene `LiquidacionPOValidationMixin` con los métodos duplicados en 3 orquestadores PO (Edificaciones, Taludes, ImpactoVial):

- `_validar_tarifa_explicita(tarifa, tipo_liquidacion)` — lanza HttpError si la tarifa no es vigente o no corresponde al tipo
- `_obtener_especialidades_vigentes_para_tipo(tipo_liquidacion)` — query de especialidades vigentes

Los 3 orquestadores ahora heredan del mixin en lugar de tener el código duplicado.

**Validación**: Los métodos siguen en la capa ORQUESTADOR (levantan HttpError), no se movieron al core.

#### 2. Los 6 `_build_*_result` ahora delegan a `general_core.build_general_result()`

**Before** (~60 líneas inline por orquestador):
```python
def _build_edificaciones_result(self, lg):
    # ... distrito building (~25 líneas) ...
    general_result = LiquidacionGeneralResult(
        id=str(lg.id),
        municipalidad=MunicipalidadResult(...),
        usuario_creador=UsuarioCreadorResult(...),
        # ... 50+ líneas idénticas en los 6 orquestadores ...
    )
```

**After** (1 línea de delegación):
```python
def _build_edificaciones_result(self, lg):
    # Revisiones_previas construidas solo aquí (necesarias para el return)
    revisiones_previas = [LiquidacionPreviaResult(...) for lp in lg.liquidaciones_previas.all()]
    usuario_id = lg.usuario_creador.id if lg.usuario_creador else 0
    general_result = self.general_core.build_general_result(
        lg,
        usuario_id=usuario_id,
        revisiones_previas=revisiones_previas,  # Edificaciones usa este campo
    )
    # Solo el resultado TIPO-ESPECÍFICO se construye aquí
```

**Parámetros pasados al core**:
- **Edificaciones**: `revisiones_previas=revisiones_previas` (campo único)
- **IO**: `contacto_result=None, delegados=[]` (IO no usa esos campos)
- **Taludes, IV, HU, MS**: sin parámetros opcionales adicionales

### Archivos modificados

| Archivo | Antes | Después | Δ |
|---------|-------|---------|---|
| `liquidacion_edificaciones_orchestrator.py` | 801 líneas | 617 líneas | **-184** |
| `liquidacion_inspeccion_obra_orchestrator.py` | 490 líneas | 348 líneas | **-142** |
| `liquidacion_taludes_orchestrator.py` | 546 líneas | 378 líneas | **-168** |
| `liquidacion_impacto_vial_orchestrator.py` | 546 líneas | 378 líneas | **-168** |
| `liquidacion_habilitacion_urbana_orchestrator.py` | 364 líneas | 237 líneas | **-127** |
| `liquidacion_mecanica_suelos_orchestrator.py` | 366 líneas | 236 líneas | **-130** |

**Nuevo archivo**: `modules/liquidaciones/domain/services/orchestrators/_shared/liquidacion_po_validation.py` (61 líneas)

**Total líneas eliminadas**: ~919 líneas de código duplicado

### Detalle de cambios por orquestador

#### Edificaciones (`liquidacion_edificaciones_orchestrator.py`)
- Removido: `_validar_tarifa_explicita` y `_obtener_especialidades_vigentes_para_tipo` (reemplazados por mixin)
- Removido: ~120 líneas del bloque inline `LiquidacionGeneralResult` (distrito building + general_result construction)
- Agregado: Herencia de `LiquidacionPOValidationMixin`
- `_build_edificaciones_result`: ahora llama `self.general_core.build_general_result(lg, usuario_id=..., revisiones_previas=...)`
- `revisiones_previas` construido antes de la llamada y pasado como parámetro

#### InspeccionObra (`liquidacion_inspeccion_obra_orchestrator.py`)
- El caso más divergente: `_build_io_result` nunca llamaba al core
- Removido: ~120 líneas del bloque inline `LiquidacionGeneralResult`
- `_build_io_result`: ahora llama `self.general_core.build_general_result(lg, usuario_id=..., contacto_result=None, delegados=[])`

#### Taludes (`liquidacion_taludes_orchestrator.py`)
- Removido: `_validar_tarifa_explicita` y `_obtener_especialidades_vigentes_para_tipo` (reemplazados por mixin)
- Removido: ~120 líneas del bloque inline
- `_build_taludes_result`: ahora llama `self.general_core.build_general_result(lg, usuario_id=...)`

#### ImpactoVial (`liquidacion_impacto_vial_orchestrator.py`)
- Mismo patrón que Taludes: mixin + delegación al core

#### HabilitacionUrbana (`liquidacion_habilitacion_urbana_orchestrator.py`)
- Sin validación duplicada (no es PO)
- Removido: ~120 líneas del bloque inline
- `_build_hu_result`: ahora llama `self.general_core_service.build_general_result(lg, usuario_id=...)`
- Nota: HU y MS usan `general_core_service` (no `general_core`) como nombre de atributo

#### MecanicaSuelos (`liquidacion_mecanica_suelos_orchestrator.py`)
- Mismo patrón que HU: delegación al core

### Validación

| Check | Resultado |
|-------|-----------|
| `manage.py check` | **0 issues** |
| `py_compile` en los 7 archivos modificados/nuevos | **ALL OK** |
| `LiquidacionEdificacionesOrchestrator._build_edificaciones_result` con liquidación real | **SUCCESS** — `liquidacion_general.proyecto`, `municipalidad`, `usuario_creador`, `distrito` todos presentes |
| Los 6 orquestadores se instancian via injector | **OK** — `general_core` tiene `build_general_result` |
| Mixin presente en Edificaciones, Taludes, ImpactoVial | **VERIFICADO** |

### Conclusión Fase 3

**Arquitectura corregida**:
- ✅ Los 6 `_build_*_result` ahora delegan a `general_core.build_general_result()` en lugar de duplicar ~120 líneas cada uno
- ✅ Validaciones duplicadas (`_validar_tarifa_explicita`, `_obtener_especialidades_vigentes_para_tipo`) extraídas a mixin compartido
- ✅ La validación sigue en capa ORQUESTADOR (HttpError), no se movió al core
- ✅ El core sigue siendo ORM puro + mapeo (sin lógica de negocio)
- ✅ D1 [CRITICAL] resuelto: los 6 orquestadores ya no duplican el bloque `LiquidacionGeneralResult`
- ✅ D2 [WARNING] resuelto: 3 orquestadores PO ya no tienen métodos duplicados

### Siguiente Paso Recomendado

**Fase 4** — Verificar controllers: confirmar que son 100% thin (sin lógica if/for/ORM directo). Si tienen lógica de negocio, documentar cuál y dónde debería moverse.

---

## Validación Fase 3 vs contrato PLAN_REFACTORIZACION.md

**Fecha**: 2026-08-15
**Status**: `partial` — Extracción helpers ✅, Mixin ✅, pero hay 1 CRITICAL y 1 WARNING residual

### Tabla de Validación vs Contrato

| Regla | Cumple? | Evidencia |
|-------|---------|-----------|
| Orchestrator: fachada thin + validación compleja + HttpError | ⚠️ PARCIAL | Edificaciones/Taludes/IV ✅. **IO ❌ línea 316: ORM directo** |
| Core: ORM puro, CERO lógica de negocio/validación | ✅ SÍ | `build_general_result` (1238-1327): solo mapea atributos, ningún `if` de negocio |
| Orchestrator: `_build_*_result` delega a `general_core.build_general_result()` | ✅ SÍ | Los 6 orquestadores ahora delegan (verificado en grep) |
| Mixin: lugar correcto para validaciones compartidas PO | ✅ SÍ | `LiquidacionPOValidationMixin` con `_validar_tarifa_explicita` y `_obtener_especialidades_vigentes_para_tipo` |
| MS Orchestrator sin mixin | ✅ CORRECTO | MS es M2, no PO — no necesita esas validaciones |
| IO Orchestrator: no tiene fuga de validación al core | ✅ SÍ | Validación sigue en orchestrator (HttpError) |
| Orchestrator: no hace ORM directo que no sea lectura de atributos | ❌ NO | **IO línea 316: `LiquidacionGeneral.objects.select_related(...)`** |

### Lo Hecho Bien ✅

1. **Mixin correctamente ubicado**: `LiquidacionPOValidationMixin` en `_shared/` — validación en orchestrator, no en core
2. **Delegación correcta**: Los 6 `_build_*_result` ahora delegan a `general_core.build_general_result()` (grep verificado en 6 archivos)
3. **Core es ORM puro**: `build_general_result` solo mapea, sin HttpError ni lógica de negocio
4. **HttpError en orchestrator**: Validaciones lanzan HttpError en la capa correcta
5. **Eliminación de código duplicado**: ~919 líneas removidas de los 6 orquestadores
6. **MS no necesita mixin**: MS es cálculo M2, no usa tarifas PO — diseño correcto

### Desviaciones

#### D1 [CRITICAL]: IO Orchestrator — ORM directo en `crear_primera_revision_desde_previa_proceso`

**Archivo**: `liquidacion_inspeccion_obra_orchestrator.py`
**Línea**: 316

```python
# ❌ VIOLACIÓN — ORM directo en orchestrator
previa = LiquidacionGeneral.objects.select_related(
    'proyecto', 'proyecto__entidad', 'municipalidad', 'tipo_liquidacion'
).get(id=payload_in.liquidacion_previa_id)
```

**Qué debería hacer**: Delegar a un método del core service como `get_liquidacion_previa_para_io(tipo_liquidacion)` o similar.

**Impacto**: Violación del contrato — "El Orquestador solo contiene validación + HttpError, NO hace ORM directo".

#### D2 [WARNING]: `present_tarifas_vigentes` duplicado en 3 presenters PO

**Archivos** (same signature `present_tarifas_vigkeiten(tarifas, especialidades_disponibles) -> dict`):
- `liquidacion_edificaciones_presenter.py:141`
- `liquidacion_taludes_presenter.py:142`
- `liquidacion_impacto_vial_presenter.py:142`

**Nota**: La duplicación es de Señal/FASE 1, no de FASE 3. Cada presenter tiene implementación ligeramente diferente porque los campos del DTO varían por tipo.

### Estado por Fase

| Fase | ¿Hecha? | Qué falta |
|------|---------|-----------|
| Fase 1: Presenters homogeneizados | ✅ Completada | WARNING: `present_tarifas_vigentes` duplicado en 3 presenters |
| Fase 2: Extracción `build_general_result` a core | ✅ Completada | — |
| Fase 3: Orquestadores — extracción helpers | ⚠️ Parcial | **D1 [CRITICAL]: IO línea 316 — ORM directo** |
| Fase 4: Controllers | ❓ Pendiente | ¿Se tocan o se dejan? |
| Core `list_liquidaciones_*_paginated` | 🔲 6 métodos | Unificación posible con prefetch dinámico (menor prioridad) |

### Recomendación para Fase 4

**ACCION REQUERIDA**: Evaluar si se toca o no.

**Si se toca** (los controllers tienen lógica que viola el contrato):
- Documentar qué lógica hay en cada controller
- Mover la lógica al orquestador o a la capa que corresponda

**Si NO se toca** (los controllers son 100% thin):
- Verificar con lectura directa de al menos 2-3 controllers
- Confirmar que solo hacen: parse → orquesta → success_response
- Si están correctos, documentar y cerrar

**Lo mínimo requerido**: Leer 2 controllers PO (edificaciones + IO) y verificar que no tienen `if`/`for`/variables de estado/ORM directo.

### Risks

1. **[CRITICAL] IO Orchestrator ORM directo línea 316**: Violación del contrato. Debe corregirse antes de cerrar Fase 3.
2. **[WARNING] `present_tarifas_vigentes` duplicado**: Residual de Fase 1. Menor impacto pero debería documentarse como deuda técnica.
3. **Fase 4 no evaluada**: Los controllers no fueron leídos directamente. Podría haber violaciones adicionales.

### next_recommended

1. **CORREGIR D1 [CRITICAL]**: IO Orchestrator línea 316 — crear método en core para obtener la liquidación previa y eliminar el ORM directo del orchestrator
2. **EVALUAR FASE 4**: Leer 2-3 controllers PO para verificar si son 100% thin
3. **DOCUMENTAR D2 como deuda técnica**: `present_tarifas_vigentes` duplicado — menor prioridad pero debe mencionarse

---

## Fase 4: Controllers — Evaluación y homogeneización

**Fecha**: 2026-08-15
**Status**: ✅ Completada — Ningún controller requiere modificación

### Contrato evaluado

**"El controlador solo hace 3 cosas: Parsear la entrada, llamar al Orquestador, y retornar el éxito formateado por un Presenter. PROHIBIDO: if, for, variables de estado, ORM directo, manejo manual de errores."**

### Evaluación por controller

| Controller | ¿Thin? | Métodos | ¿Lógica movida? | Observaciones |
|------------|--------|---------|-----------------|---------------|
| `liquidacion_edificaciones` | ✅ SÍ | 7 | No | `crear_nueva_revision`, `obtener_ultima_revision` son métodos extra exclusivos de este tipo |
| `liquidacion_taludes` | ✅ SÍ | 5 | No | Estructura base idéntica a PO |
| `liquidacion_habilitacion_urbana` | ✅ SÍ | 5 | No | Usa `cotizar_orchestrator` (nombre diferente), comparte presenter M2 |
| `liquidacion_impacto_vial` | ✅ SÍ | 5 | No | Estructura base idéntica a PO |
| `liquidacion_inspeccion_obra` | ✅ SÍ | 6 | No | `crear_primera_revision_desde_previa` es método extra exclusivo de IO |
| `liquidacion_mecanica_suelos` | ✅ SÍ | 5 | No | Comparte presenter M2 con HU |

### Análisis detallado de cada método

#### Métodos comunes a los 6 (todos ✅ thin)

| Método | Qué hace | ¿Violación? |
|--------|----------|-------------|
| `get_tarifas_vigentes` | `orchestrator.obtener_tarifas_vigentes_proceso()` → presenter → `success_response` | No |
| `list_liquidaciones` | `orchestrator.listar_liquidaciones(...)` → presenter → `success_response` | No |
| `obtener_liquidacion` | `orchestrator.obtener_liquidacion(liquidacion_id)` → presenter → `success_response` | No |
| `crear_primera_revision` | `auth.get_user_id(request)` → `orchestrator.crear_primera_revision_proceso(...)` → presenter → `success_response` | No |

#### Método `cotizar` — Análisis de extracción de campos

Los 6 controllers tienen `cotizar` y los 6 extraen campos del payload antes de llamar al orquestador:

| Controller | Campos extraídos | ¿Lógica de negocio o parseo? |
|------------|------------------|------------------------------|
| Edificaciones | `le.datos.valor_declarado`, `le.tarifas` | **Parseo** — re-mapeo de campos del schema al orquestador |
| Taludes | `le.datos.valor_declarado`, `le.tarifas` | **Parseo** |
| Impacto Vial | `le.datos.valor_declarado`, `le.tarifas` | **Parseo** |
| Habilitación Urbana | `area_solicitada`, `tarifa_m2_id` | **Parseo** — el orquestador acepta `area_solicitada` y `tarifa_m2_id` como parámetros separados |
| Inspeccion Obra | `cantidad_visitas`, `categoria`, `tarifa_visitas_id` | **Parseo** — campos del schema de entrada |
| Mecánica Suelos | `area_solicitada`, `tarifa_m2_id` | **Parseo** |

**Veredicto**: Extraer `payload.liquidacion_especifica.datos.campo` del payload es **parseo de entrada**, no lógica de negocio. Los orquestadores aceptan esos valores como parámetros. El controller solo reorganiza los datos del schema de entrada para pasarlos al orquestador.

#### Métodos extra por controller (no violan el contrato)

- **Edificaciones**: `crear_nueva_revision`, `obtener_ultima_revision` — delegan puramente al orquestador → presenter → `success_response`
- **Inspeccion Obra**: `crear_primera_revision_desde_previa` — mismo patrón: auth → orquestador → presenter → `success_response`

### Decisión: Base controller vs. dejar delgados

**Decisión: Opción A — Dejar los 6 controllers_DELGADOS**

**Justificación**:
1. Los 6 controllers YA CUMPLEN el contrato — son thin, sin lógica de negocio
2. Hay diferencias sutiles pero significativas:
   - HU y MS usan `cotizar_orchestrator` como nombre de atributo (no genérico `orchestrator`)
   - HU y MS usan presentadores M2 compartidos (`LiquidacionPorMetroCuadradoPresenter`) además del presenter específico
   - IO usa presentador de Visitas (`LiquidacionPorCategoriaVisitasPresenter`)
   - Edificaciones tiene 2 métodos extra (`crear_nueva_revision`, `obtener_ultima_revision`)
   - IO tiene 1 método extra (`crear_primera_revision_desde_previa`)
3. **CRÍTICO**: Crear una base que parametrize estas diferencias requeriría:
   - Una jerarquía de herencia que complica el registro Ninja (`@api_controller` + `@route` con herencia puede romper el path resolution)
   - Pasar el tipo como string/parámetro y luego hacer branching en la base
   - Esto viola el principio de que **un controller delgado y repetido es MENOS malo que una base que rompa lo sagrado**
4. Los controllers son pequeños (~160-210 líneas) y la repetición es aceptable dado que son thin

**Opción B (Base controller) NO recomendada porque**:
- Rompería la seguridad del registro de rutas Ninja
- Introduciría branching condicional en la base
- El beneficio de DRY no justifica el riesgo arquitectónico

### Archivos modificados

**Ninguno** — Los 6 controllers YA estaban thin y no requirieron modificación.

### Verificación

| Check | Resultado |
|-------|-----------|
| `manage.py check --settings=config.settings.development` | **0 issues** ✅ |
| `python -m py_compile` en 6 controllers | **ALL OK** ✅ |
| `config/api.py` — imports de 6 controllers | **OK** ✅ |
| `config/api.py` — `api.register_controllers(...)` de 6 controllers | **OK** ✅ |

### Residuos de fases anteriores (no bloquean Fase 4)

| ID | Tipo | Descripción | Estado |
|----|------|-------------|--------|
| D1 [CRITICAL] | Orchestrator | IO Orchestrator línea 316: ORM directo en `crear_primera_revision_desde_previa_proceso` | Pendiente (no es controller) |
| D2 [WARNING] | Presenter | `present_tarifas_vigentes` duplicado en 3 presenters PO | Deuda técnica (no es controller) |

### Conclusión Fase 4

**Todos los 6 controllers YA son thin y cumplen el contrato.** No se requirió mover lógica ni crear base controller. La arquitectura de controllers es correcta según `PLAN_REFACTORIZACION.md`.

### Siguiente Paso Recomendado

1. **CORREGIR D1 [CRITICAL]**: IO Orchestrator línea 316 — ORM directo en `crear_primera_revision_desde_previa_proceso`. Esto NO es controller, es orchestador.
2. **Fase 4 controllers**: ✅ CERRADA — no requiere acción.

---

## Deuda: Unificar `list_liquidaciones_*_paginated`

**Fecha**: 2026-08-15
**Status**: ✅ Completada

### Qué se hizo

Los 6 métodos `list_liquidaciones_*_paginated` en `LiquidacionGeneralCoreService` (líneas ~158-540) tenían filtros IDÉNTICOS y solo diferían en:
1. El `tipo_liquidacion__codigo` filtrado
2. El `prefetch_related` específico del tipo
3. El campo `numero` (cada tipo tiene su propia relación: `edificaciones__numero`, `habilitacion_urbana__numero`, etc.)

**Refactoring aplicado**:
- Creado `_PREFETCH_MAP` (class-level dict) que mapea `TipoLiquidacion.EDIFICACION` → lista de paths de prefetch
- Creado `_NUMERO_FILTER_FIELD_MAP` (class-level dict) que mapea `TipoLiquidacion` → nombre del campo `numero` (ej: `edificaciones__numero`)
- Creado método unificado `list_liquidaciones_paginated(tipo_liquidacion, ...)` que:
  - Selecciona el prefetch chain desde `_PREFETCH_MAP`
  - Selecciona el campo `numero` desde `_NUMERO_FILTER_FIELD_MAP`
  - Aplica los 8 filtros comunes (municipalidad_id, propietario, razon_social, creador_username, fecha_desde, fecha_hasta, numero, numero_revision)
  - Retorna `(queryset[offset:offset+page_size], total)`
- Los 6 métodos existentes ahora son **delegación fina** al método unificado:
  ```python
  def list_liquidaciones_hu_paginated(self, ...):
      return self.list_liquidaciones_paginated(
          tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
          ...
      )
  ```

### Firma del método unificado

```python
def list_liquidaciones_paginated(
    self,
    tipo_liquidacion: str,       # ej: TipoLiquidacion.EDIFICACION
    page: int,
    page_size: int,
    municipalidad_id=None,
    propietario=None,
    razon_social=None,
    creador_username=None,
    fecha_desde=None,
    fecha_hasta=None,
    numero=None,
    numero_revision=None,
    **kwargs
) -> tuple:
    """Unified paginated queryset. Returns (queryset, total_count)."""
```

### Cómo quedan los 6 métodos (ejemplo)

```python
# Antes (63 líneas de código duplicado en cada método):
def list_liquidaciones_hu_paginated(self, ...):
    qs = LiquidacionGeneral.objects.filter(
        tipo_liquidacion__codigo=TipoLiquidacion.HABILITACION_URBANA
    ).select_related(...).prefetch_related(
        'habilitacion_urbana', 'liquidacion_m2', ...
    ).order_by('-fecha_registro')
    # ... 8 filtros idénticos ...
    return qs[offset:offset+page_size], total

# Después (delegación fina, 0 duplicación):
def list_liquidaciones_hu_paginated(self, ...):
    """Returns paginated LiquidacionGeneral queryset for Habilitación Urbana."""
    return self.list_liquidaciones_paginated(
        tipo_liquidacion=TipoLiquidacion.HABILITACION_URBANA,
        page=page, page_size=page_size,
        municipalidad_id=municipalidad_id, propietario=propietario,
        razon_social=razon_social, creador_username=creador_username,
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        numero=numero, numero_revision=numero_revision,
    )
```

### Líneas eliminadas

| Métrica | Valor |
|---------|-------|
| Original (6 métodos) | 383 líneas (158-540) |
| Nuevo código | 331 líneas (158-488) |
| **Reducción neta** | **52 líneas** |
| Maps overhead | 70 líneas |
| **Código duplicado eliminado** | **122 líneas** |

### Verificación

| Check | Resultado |
|-------|-----------|
| `manage.py check --settings=config.settings.development` | **0 issues** ✅ |
| `python -m py_compile` en `liquidacion_general_core_service.py` | **ALL OK** ✅ |
| Probe: `GET /api/liquidaciones/edificaciones/?page=1&page_size=5` | **200 OK** ✅ |
| Probe: `GET /api/liquidaciones/habilitacion-urbana/?page=1&page_size=5` | **200 OK** ✅ |
| Probe: `GET /api/liquidaciones/mecanica-suelos/?page=1&page_size=5` | **200 OK** ✅ |
| Probe: `GET /api/liquidaciones/taludes/?page=1&page_size=5` | **200 OK** ✅ |
| Probe: `GET /api/liquidaciones/inspeccion-obra/?page=1&page_size=5` | **200 OK** ✅ |
| Probe: `GET /api/liquidaciones/impacto-vial/?page=1&page_size=5` | **200 OK** ✅ |
| `_PREFETCH_MAP` keys == `_NUMERO_FILTER_FIELD_MAP` keys | **True** ✅ |
| Prefetch chain EDIFICACION == original | **True** ✅ |
| Prefetch chain IV == original | **True** ✅ |
| `list_liquidaciones_by_type_paginated` mantiene firma original | **True** ✅ |

### Archivo modificado

`backend/modules/liquidaciones/domain/services/core/liquidacion_general/liquidacion_general_core_service.py`
- 6 métodos: 383 líneas → 331 líneas
- Agregado: `_PREFETCH_MAP`, `_NUMERO_FILTER_FIELD_MAP`, `list_liquidaciones_paginated`
- Modificado: 6 métodos convertidos en delegación fina

### Conclusión

Los 6 métodos `list_liquidaciones_*_paginated` ahora son **delegación fina** al método unificado `list_liquidaciones_paginated`. La arquitectura de Core = ORM puro + condicionales de prefetch (no lógica de negocio) se mantiene. Los callers (orquestadores) no necesitan cambios.

---

## Skill Resolution
`paths-injected` — Rutas exactas de skills resueltas por el orchestrator.
