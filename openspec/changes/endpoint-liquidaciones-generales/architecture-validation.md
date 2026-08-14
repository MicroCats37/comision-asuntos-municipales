# SDD Architecture Validation: Endpoint GET /liquidaciones/generales

## Metadata
- **change-name**: endpoint-liquidaciones-generales
- **project**: comision-asuntos-municipales
- **phase**: explore (architecture validation)
- **contract**: contract/PLAN_REFACTORIZACION.md
- **date**: 2026-08-12

---

## Status: partial

## Executive Summary

The new `GET /liquidaciones/generales` endpoint is **largely compliant** with the architecture contract. The 4-layer separation (Controller → Orchestrator → Core → Presenter) is correctly implemented, query params use the Ninja `Query(...)` pattern, and registration follows existing conventions. One **CRITICAL** risk exists: the general core service prefetches all 6 relationship chains regardless of tipo, creating unnecessary memory/IO overhead on every call. One **WARNING**: the `auth=None` differs from the JWT-protected pattern of other list endpoints. One **SUGGESTION**: the presenter accesses `proyecto.entidad` fields without `getattr` safety, risking `AttributeError` in edge cases.

---

## Layer-by-Layer Validation Table

| Capa | Regla del contrato | ¿Cumple? | Evidencia |
|------|---------------------|----------|-----------|
| **Controller** | "Solo parsea → delega → success_response. Cero ifs, cero ORM, cero error_responses manuales" | ✅ Sí | `liquidacion_general_controller.py:44-70` — puro parse + delegate |
| **Controller** | Usa `Query(...)` + response schema `ApiResponse[PaginatedData[...]]` | ✅ Sí | `controller.py:46-51` y `:41` |
| **Orchestrator** | Fachada thin — validación + delegación | ✅ Sí | `orchestrator.py:62-84` — paginación, delegate, build result |
| **Orchestrator** | Usa `@inject`, `sync_to_async` con variable intermedia | ⚠️ Parcial | Inyecta bien, pero NO usa `sync_to_async` (es sync pura) |
| **Core** | ORM puro — cero lógica condicional de negocio | ✅ Sí | `core_service.py:763-816` — filter/select/prefetch chain |
| **Core** | Filtros encadenados solo para no-None | ✅ Sí | `core_service.py:804-812` |
| **Presenter** | Solo `@staticmethod`, mapeo Result→Schema Out | ✅ Sí | `presenter.py:49-203` |
| **Presenter** | Sin acceso a ORM | ✅ Sí | Solo opera sobre `LiquidacionGeneralResult` |
| **Registro API** | Registro via `api.register_controllers(...)` | ✅ Sí | `api.py:33-34,109` |
| **Contrato público** | `LiquidacionGeneralOutput.tipo_liquidacion` presente | ✅ Sí | Mapeado en orchestrator `:200-207` y presenter `:131-136` |

---

## Hallazgos

### 🔴 CRITICAL

**1. Core prefetch ALL tipos — N+1/performance severo**
- **Archivo**: `liquidacion_general_core_service.py:779-802`
- **Por qué**: El nuevo método `list_liquidaciones_generales_paginated` hace `prefetch_related` de los 6 tipos de liquidación (`edificaciones`, `habilitacion_urbana`, `mecanica_suelos`, `inspeccion_obra`, `taludes`, `impacto_vial`) para CADA resultado, sin importar el `tipo_liquidacion` de ese resultado.
- **Impacto**: Si el modal de búsqueda retorna 20 liquidaciones de tipos mixtos (5 EDIFICACION, 5 HU, 5 MS, 5 IO), Django dispara prefetch para las 6 tablas × 20 = 120 relaciones, cuando solo se necesitan las 20 del tipo correcto.
- **Comparación**: Los 6 métodos específicos (`list_liquidaciones_by_type_paginated`, `list_liquidaciones_hu_paginated`, etc.) hacen prefetch SOLO del tipo correspondiente. Este método general no puede usar la misma estrategia porque ignora el tipo en el prefetch.
- **Contrato violado**: El core debe ser "pure ORM" pero aquí el prefetch blanket viola el principio de eficiencia que subyace al contrato.
- **Fix sugerido**: Eliminar el prefetch general y hacer un prefetch selectivo basado en tipo, O usar `prefetch_related()` vacío y dejar que Django lazy-load cuando el presenter/iterspector acceda solo a las relaciones del tipo correcto.

### 🟡 WARNING

**2. `auth=None` difiere de los otros endpoints de listado**
- **Archivo**: `liquidacion_general_controller.py:42`
- **Por qué**: `LiquidacionEdificacionesController.list_liquidaciones` (`:73`) NO tiene `auth=None` declarado, lo que implica que hereda JWT del API. En cambio, este endpoint explícitamente dice `auth=None`.
- **Si es intencional** (búsqueda pública en modal): OK, pero inconsistente con el resto del módulo.
- **Si fue por descuido**: Debería usar JWT como los demás.
- **Acción requerida**: Confirmar con el usuario si la búsqueda general debe ser pública.

### 🟡 WARNING

**3. Presenter sin `getattr` safety en acceso a entidad**
- **Archivo**: `presenter.py:78-83`
- **Por qué**: El presenter hace `general.proyecto.entidad.tipo_documento` etc. sin verificar que `entidad` no sea `None`. El orchestrator (`:193-197`) SÍ construye `EntidadResult` con defaults (`""`) cuando hay datos, pero si `proyecto.entidad` es `None` en el Result, esto crashea.
- **Evidencia**: El orchestrator (`:93-95`) accede a campos denormalizados con `hasattr` y fallback `None`, y luego construye `EntidadResult` solo si hay datos (`:193-197`). Si `proyecto.entidad` es `None` en el Result, `presenter.py:78` crashea con `AttributeError`.
- **Comparación**: El propio orchestrator usa `getattr(..., 'atributo', None)` defensivamente (`:93-95`). El presenter no sigue el mismo patrón.

### 💡 SUGGESTION

**4. Nombre del método del orquestador no sigue la convención `_*_proceso`**
- **Archivo**: `orchestrator.py:48`
- **Por qué**: Los métodos públicos del orquestador específico usan sufijo `_proceso` (e.g., `listar_liquidaciones_proceso`, `crear_primera_revision_proceso`). El método nuevo es `listar_liquidaciones_generales` sin `_proceso`.
- **Importancia**: Baja — es una convención de nomenclatura, no una regla arquitectónica del contrato.

**5. El core service no tiene método `sync_to_async` para el método general**
- **Archivo**: `orchestrator.py:70`
- **Por qué**: El orchestrator llama `self.general_core_service.list_liquidaciones_generales_paginated(...)` directamente sin `sync_to_async`. Los métodos del core son sincronicos (Django ORM). Si bien el contrato dice que el orquestador usa `sync_to_async`, los métodos de listado en este módulo no lo usan (el propio `LiquidacionEdificacionesOrchestrator.listar_liquidaciones` también llama directo al core sync).
- **Comparación**: El `delegado_orchestrator.py:145` también llama `self.core_service.list_delegados_paginated(...)` directo sin `sync_to_async`. Es el patrón existente en el módulo.

---

## Risks

1. **Performance** (CRITICAL): El prefetch blanket en el core puede causar uso excesivo de memoria y queries lentas en listados grandes.
2. **Runtime crash** (WARNING): El presenter puede crashear con `AttributeError` si `proyecto.entidad` es `None` en el Result en algún caso borde.
3. **Inconsistencia de auth** (WARNING): Si el endpoint DEBE requerir JWT (como los demás), tener `auth=None` es un riesgo de seguridad.
4. **Contrato público** (OK): `tipo_liquidacion` SÍ viene en la respuesta — el contracto público de `LiquidacionGeneralOutput` se respeta.

---

## Análisis Adicional

### ¿El nuevo orquestador general duplica lógica de los orquestadores específicos o la reutiliza bien?

El `LiquidacionGeneralOrchestrator` no reutiliza los orquestadores específicos (edificaciones, HU, etc.) — y está bien, porque su trabajo es diferente: listar TODOS los tipos sin filtrar por tipo. La lógica de paginación (`if page < 1`, `if page_size > 100`) ES consistente con `DelegadoOrchestrator.list_delegados_proceso` (`:138-143`).

### ¿El filtro por `documento` usa el campo REAL del modelo?

Sí — `proyecto__entidad_numero_documento` (core_service.py:808) es el campo correcto según el modelo `Proyecto` que tiene campos denormalizados `entidad_numero_documento`.

### ¿El controller registra `auth` coherente con los otros?

No — usa `auth=None` explícito mientras `LiquidacionEdificacionesController` no declara auth (hereda JWT). **Esto requiere confirmación del usuario.**

---

## next_recommended

`apply-fix` — Las desviaciones CRITICAL (prefetch blanket) y WARNING (auth, presenter safety) deben resolverse antes de usar este endpoint en producción.
