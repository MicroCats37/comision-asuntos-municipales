# Exploration: Endpoint de Últimas Revisiones de Liquidaciones Generales

## 1. Cómo funciona hoy "última revisión"

### Patrón existente en el código

El patrón "última revisión" ya existe en dos lugares:

**A) `list_ultimas_revisiones_por_proyecto`** (`liquidacion_general_core_service.py:671`)
- Subquery exacto en línea 721-726:
  ```python
  max_rev_subquery = LiquidacionGeneral.objects.filter(
      proyecto_id=OuterRef('proyecto_id'),
      tipo_liquidacion__codigo=tipo_liquidacion,
  ).order_by().values('proyecto_id').annotate(
      max_rev=Max('numero_revision')
  ).values('max_rev')[:1]
  
  qs = qs.filter(numero_revision=Subquery(max_rev_subquery))
  ```
- Agrupado por `proyecto_id` + `tipo_liquidacion__codigo` (dos campos)
- Filtra a solo la fila con `numero_revision = max(numero_revision)` por proyecto+tipo
- **BUG CONOCIDO**: El prefetch chain está hardcodeado SOLO para Edificaciones (líneas 702-708: solo `edificaciones` + `liquidacion_porcentaje_obra`). NO sirve para HU, MS, IO, IV, Taludes.

**B) `get_ultima_revision_por_proyecto`** (`liquidacion_general_core_service.py:734`)
- Uso simple: `qs.order_by('-numero_revision').first()`
- Para un proyecto + tipo específicos (no paginado, solo retorna 1 o None)

**C) En flujos de nueva revisión** (`liquidacion_edificaciones_orchestrator.py:662` → `obtener_ultima_revision_proceso`)
- Llama a `list_ultimas_revisiones_por_proyecto` del core service
- Construye el resultado con `_build_edificaciones_result`

---

## 2. Modelo de datos: cómo se identifica la "última revisión"

### Modelo `LiquidacionGeneral` (`liquidacion.py:19`)

```
LiquidacionGeneral
├── proyecto (FK → Proyecto)           ← Cada proyecto puede tener N liquidaciones
├── numero_revision (PositiveInteger)   ← 1, 2, 3... (secuencial por proyecto)
├── tipo_liquidacion (FK → TipoLiquidacion)
├── liquidaciones_previas (M2M self)   ← Referencias a revisiones anteriores
├── estado, total, sub_total, expediente, ...
```

**Cada fila = una revisión.** Un proyecto puede tener filas con `numero_revision` = 1, 2, 3, etc.

La "última" se identifica como la fila con el **mayor `numero_revision`** para cada par `(proyecto_id, tipo_liquidacion)`.

El campo `liquidaciones_previas` (M2M) linking a otras `LiquidacionGeneral` permite construir `revisiones_previas` en la respuesta.

---

## 3. Diseño de datos del endpoint actual vs. nuevo

### Endpoint existente: `GET /liquidaciones/generales`
- **Filtros**: `tipo`, `documento`, `razon_social`, `propietario` + paginación
- **NO filtra por última revisión** — devuelve TODAS las filas
- Un proyecto con 3 revisiones aparece 3 veces (una por fila)
- El orden es `-fecha_registro`

### Endpoint nuevo: `GET /liquidaciones/generales/ultimas-revisiones`
- **Filtros**: los mismos del general (`tipo`, `documento`, `razon_social`, `propietario`) + paginación
- **SÍ filtra**: solo la fila con `max(numero_revision)` por proyecto+tipo
- Un proyecto con 3 revisiones aparece 1 vez (solo la última)
- El orden es `-fecha_registro` (entre las últimas)

### Diferencia clave de subquery
La subquery actual de `list_ultimas_revisiones_por_proyecto` agrupa por `proyecto_id` + `tipo_liquidacion__codigo`. Esto significa que si un proyecto tiene EDIFICACION (rev 3) e HABILITACION_URBANA (rev 1), devuelve ambas como "últimas" respective a su tipo. Esto es correcto — son liquidaciones independientes.

---

## 4. Recomendación de diseño

### Arquitectura: Nuevo método core + nuevo método orchestrator + nuevo endpoint

**Nombre del endpoint**: `GET /liquidaciones/generales/ultimas-revisiones`

### A) Core Service: nuevo método `list_liquidaciones_ultimas_generales_paginated`

Ubicación: `liquidacion_general_core_service.py`

El método debe:
1. Usar la MISMA subquery `max_rev_subquery` de `list_ultimas_revisiones_por_proyecto` pero **SIN filtrar por `tipo_liquidacion` en el subquery** para permitir todos los tipos
2. Aplicar la MISMA conditional prefetch strategy de `list_liquidaciones_generales_paginated` (no hardcodear un solo tipo)
3. Aceptar los mismos filtros que `list_liquidaciones_generales_paginated`: `tipo`, `documento`, `razon_social`, `propietario`

**Subquery ajustada** (para agrupar por proyecto+tipo_liquidacion):
```python
from django.db.models import Max, OuterRef, Subquery

max_rev_subquery = LiquidacionGeneral.objects.filter(
    proyecto_id=OuterRef('proyecto_id'),
    tipo_liquidacion__codigo=OuterRef('tipo_liquidacion__codigo'),
).order_by().values('proyecto_id', 'tipo_liquidacion__codigo').annotate(
    max_rev=Max('numero_revision')
).values('max_rev')[:1]

qs = qs.filter(numero_revision=Subquery(max_rev_subquery))
```

**Problema con prefetch condicional**: Cuando se combina `tipo` filter + ultimas_revisiones, hay que hacer prefetch específico por tipo (igual que `list_liquidaciones_generales_paginated`). Cuando NO hay `tipo` filter, hacer prefetch de todos (también igual).

### B) Orchestrator: nuevo método `listar_ultimas_liquidaciones_generales`

Ubicación: `liquidacion_general_orchestrator.py`

Reutiliza `_build_general_result` existente (no necesita cambios, ya mapea `liquidaciones_previas` M2M a `revisiones_previas`).

### C) Controller: nuevo endpoint

Ubicación: `liquidacion_general_controller.py`

Nuevo endpoint similar al existente `GET /liquidaciones/generales` pero apuntando al nuevo método del orchestrator.

### D) Schema de salida

**Reutilizar `LiquidacionGeneralOutput`** — no requiere cambios. El schema ya incluye `revisiones_previas: list[LiquidacionPreviaOutput]`.

---

## 5. Archivos que se tocarían

| Capa | Archivo | Cambio |
|------|---------|--------|
| Core Service | `backend/modules/liquidaciones/domain/services/core/liquidacion_general/liquidacion_general_core_service.py` | Nuevo método `list_liquidaciones_ultimas_generales_paginated` (~40-50 líneas) |
| Orchestrator | `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_general_orchestrator.py` | Nuevo método `listar_ultimas_liquidaciones_generales` (~20 líneas), reutiliza `_build_general_result` |
| Controller | `backend/modules/liquidaciones/presentation/controllers/liquidacion_general_controller.py` | Nuevo endpoint `GET /liquidaciones/generales/ultimas-revisiones` (~15 líneas) |
| Frontend Hook | `frontend/src/features/liquidaciones/hooks/useLiquidacionesGenerales.ts` | Nuevo hook o parámetro `ultimas=true` |
| Frontend View | `frontend/src/features/liquidaciones/views/LiquidacionesGeneralesView.tsx` | Integración UI del nuevo endpoint |

---

## 6. Risks

1. **Subquery performance**: El subquery con `Max` + `OuterRef` por `proyecto_id` + `tipo_liquidacion__codigo` puede ser costoso en tablas grandes. Debería tener índices en `(proyecto_id, tipo_liquidacion_id, numero_revision)`. Verificar que el modelo `LiquidacionGeneral.Meta.ordering` o un índice explícito cubra este caso.

2. **Bug en `list_ultimas_revisiones_por_proyecto`**: El prefetch chain hardcodeado para Edificaciones debe ser corregido si se reutiliza ese método. Pero para el NUEVO endpoint, usaremos la conditional prefetch strategy de `list_liquidaciones_generales_paginated`.

3. **Interacción con filtros**: Si el usuario filtra por `tipo=X` y `ultimas=true`, la subquery sigue agrupando por `tipo_liquidacion__codigo` correctamente. Si filtra por `tipo` y la subquery no incluye `tipo_liquidacion__codigo`, podría devolver liquidaciones de OTRO tipo por proyecto. **La subquery DEBE incluir `tipo_liquidacion__codigo`** para mantener la separación por tipo.

4. **`liquidaciones_previas` M2M**: Cuando se filtra a la última revisión, la M2M `liquidaciones_previas` en el objeto ya trae las referencias correctas (porque apunta a otras `LiquidacionGeneral`). No se necesita cambio aquí.

---

## 7. Reusso vs. método nuevo

| Opción | Descripción | Pros | Cons |
|--------|-------------|------|------|
| **A) Método nuevo** | `list_liquidaciones_ultimas_generales_paginated` en core service | Código más limpio, separado del listing general; fácil de testear; mismo prefetch strategy condicional | Duplicación de ~60% del código de `list_liquidaciones_generales_paginated` |
| **B) Parámetro `ultima_only=True`** | Agregar parámetro a `list_liquidaciones_generales_paginated` | Menos código duplicado; una sola query method | Mezcla dos responsabilidades; lógica condicional más compleja dentro del mismo método |
| **C) Reutilizar `list_ultimas_revisiones_por_proyecto`** | Corregir el prefetch chain y llamar sin `tipo_liquidacion` filter | Reutiliza código existente | NO funciona para "general" (todos los tipos) porque está diseñado para un solo tipo |

**Recomendación: Opción A (método nuevo)** — La duplicación de código es controlada (~40-50 líneas) y el prefetch condicional ya existe como patrón. El código es más mantenible y testeable.

---

## 8. Siguiente paso

`apply` — crear los tasks para implementar el nuevo endpoint.
