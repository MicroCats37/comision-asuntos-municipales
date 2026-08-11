# SDD Architecture Validation: Registro de Búsquedas de Ingeniero Habilitado

## Metadata

- **Change**: Registro de búsquedas de ingeniero habilitado (deduplicación diaria)
- **Project**: comision-asuntos-municipales
- **Validator**: sdd-explore phase
- **Date**: 2026-08-11

---

## Status

**`partial`** — La implementación es mayormente correcta pero tiene 1 CRITICAL y 1 WARNING que requieren decisión antes de marcar `verify`.

---

## Executive Summary

La implementación cumple la arquitectura en sus líneas generales: el controlador stayed sacred, el orquestador es fachada thin, el modelo y el core service respetan convenciones, y el binding DI es consistente. **Sin embargo, hay dos desviaciones significativas**: (1) `_registrar_busqueda_async` combina `get_or_create` de PerfilIngeniero + llamada al core service sin `@transaction.atomic`, rompiendo la atomicidad esperada cuando se registra un PerfilIngeniero nuevo; y (2) el `get_or_create` se hace directamente en el flujo en lugar de delegar al core service, violando la separación Core = ORM puro. El efecto invisible (try/except silencioso) es discutible pero coherente con la documentación del propio flujo.

---

## Validation Table

| Capa | Regla del Contrato (cita) | ¿Cumple? | Evidencia |
|------|--------------------------|----------|-----------|
| **Controller** | "El controlador solo hace 3 cosas: Parsear la entrada, llamar al Orquestador, y retornar el éxito formateado por un Presenter." (Sección 1.A) | ✅ SÍ | `ingeniero_habilitado_controller.py:46` — solo llama orchestrator + success_response, cero lógica |
| **Controller** | PROHIBIDO: if, for, estado, ORM, errores manuales (Sección 1.A) | ✅ SÍ | Controlador sin if/for/ORM |
| **Orchestrator** | "Fachada ligera — delega lógica a Flujo" (Sección 4) | ✅ SÍ | `ingeniero_habilitado_orchestrator.py:39` — retorna directamente del flujo, sin lógica propia |
| **Orchestrator** | "Usa sync_to_async y asigna a variables" (Sección 4) | ✅ SÍ | `ingeniero_habilitado_orchestrator.py:46` — usa `await` directo con variable |
| **Flujo** | "Único lugar donde existe el decorador @transaction.atomic" (Sección 4) | ❌ **NO** | `ingeniero_habilitado_flujo.py:93-128` — NO tiene `@transaction.atomic` |
| **Flujo** | "Agrupa múltiples interacciones de Core" (Sección 4) | ⚠️ PARCIAL | `get_or_create` NO va a Core, va directo al ORM |
| **Flujo** | "El Orquestador o el Flujo/Core mediante raise" (Sección 1.B) | ⚠️ PARCIAL | `_registrar_busqueda_async` hace try/except + logger.exception sin re-raise (efecto invisible) |
| **Core** | "Transaccionalidad pura del ORM de Django (get, create, filter)" (Sección 4) | ✅ SÍ | `registrar_busqueda` usa `update_or_create` — ORM puro |
| **Core** | "Cero lógica de negocio condicional" (Sección 4) | ✅ SÍ | `registrar_busqueda` no tiene lógica condicional más allá de update_or_create |
| **Modelo** | Constraint parcial: condition=fecha_busqueda__isnull=False | ✅ SÍ | `perfil_ingeniero.py:215` + `0002 migration:38` — coincide |
| **DI** | Singleton para servicios core | ✅ SÍ | `di.py:62` — binding correcto |
| **DI** | Patrón consistente con módulo | ✅ SÍ | Mismo patrón que `PerfilIngenieroCoreService` en `di.py:61` |
| **sync_to_async** | `thread_sensitive=True` en operaciones BD | ✅ SÍ | `ingeniero_habilitado_flujo.py:112,118` — ambos con thread_sensitive=True |

---

## Hallazgos

### 🔴 CRITICAL — `_registrar_busqueda_async`: Sin `@transaction.atomic`

**Archivo**: `backend/modules/usuarios/domain/services/flujos/ingeniero_habilitado_flujo.py:93-128`  
**Archivo**: `backend/modules/usuarios/domain/services/flujos/ingeniero_habilitado_flujo.py:109-123`

**Problema**: `_registrar_busqueda_async` ejecuta dos operaciones de escritura en BD:
1. `PerfilIngeniero.objects.get_or_create(cip=normalized_cip)` → línea 110-113
2. `self._habilitacion_core.registrar_busqueda(...)` → línea 116-123

Si (1) succeedea pero (2) falla (ej. error de constraint, conexión perdida), el PerfilIngeniero queda huérfano: creado sin su registro de búsqueda. El contrato dice explícitamente que Flujo es "el único lugar donde existe el decorador `@transaction.atomic`" (Sección 4, Plan de Refactorización).

**Evidencia contractual**:
```
# Plan refactorización Sección 4:
# "Flujo (domain/services/flujos/auth_flujo.py)
#  - Agrupa múltiples interacciones de Core.
#  - Único lugar donde existe el decorador @transaction.atomic."
```

**Alternativas**:
- **Opción A (recomendada)**: Agregar `@transaction.atomic` a `_registrar_busqueda_async` (el flujo puede tener múltiples métodos con atomic si cada uno es independiente)
- **Opción B**: Unificar todo en `_proceso_obtener_ingeniero_habilitado` bajo un solo atomic (más costoso en performance)

**Gravedad**: Si un PerfilIngeniero no existe y el CIP externo responde, el `get_or_create` lo crea. La operación de registro de búsqueda es el efecto secundario de esa misma acción de negocio. Sin atomicidad, pueden quedar filas "huérfanas" de PerfilIngeniero sin `IngenieroHabilitacion`.

---

### 🟡 WARNING — `get_or_create` de PerfilIngeniero en el Flujo, no en Core

**Archivo**: `backend/modules/usuarios/domain/services/flujos/ingeniero_habilitado_flujo.py:109-113`

**Problema**: El flujo hace `PerfilIngeniero.objects.get_or_create(...)` directamente, en lugar de delegar esta operación ORM a `PerfilIngenieroCoreService`.

**Evidencia contractual** (contrato, Sección 4):
```
# Core (domain/services/core/persona_core.py)
#  - Transaccionalidad pura del ORM de Django (get, create, filter).
#  - Cero lógica de negocio condicional.
```

El patrón del módulo ya tiene `_obtener_perfil_por_cip()` y `_upsert_perfil_from_cip()` en `PerfilIngenieroCoreService`. El flujo debería consumir esos métodos del core, no invocar ORM directo.

**Nota**: Esto es un desvío del patrón del módulo más que del contrato strictu sensu. El core service ya existe con la lógica necesaria.

**Gravedad**: Lower que el CRITICAL — la lógica funciona pero no es coherente con cómo se organizan las responsabilidades en el resto del módulo.

---

### 💡 SUGGESTION — `get_or_create` no es idempotente para `created`

**Archivo**: `backend/modules/usuarios/domain/services/flujos/ingeniero_habilitado_flujo.py:110`

```python
perfil, _ = await sync_to_async(
    PerfilIngeniero.objects.get_or_create,
    thread_sensitive=True,
)(cip=normalized_cip)
```

El código descarta el flag `created` (`_`). Esto es aceptable dado que `registrar_busqueda` usa `update_or_create` (sobrescribe `condicion_cip` y `ultimo_periodo_pagado_cip` siempre), pero si en el futuro se quisiera saber si fue creado vs. actualizado para lógica adicional, no hay forma de distinguirlo.

**No requiere acción inmediata** — es consistente con el diseño actual.

---

### ✅ `timezone.localdate()` vs `date.today()` — Correcto

**Archivo**: `backend/modules/usuarios/domain/services/core/ingeniero_habilitacion_core_service.py:49`

Usa `timezone.localdate()` en vez de `date.today()`. El contrato no especifica nada sobre esto, pero el módulo ya usa `timezone` en otros core services (`perfil_ingeniero_core_service.py:103` usa `timezone.now()`). **Decisión coherente con el codebase**.

---

### ✅ Efecto invisible (try/except silencioso) — Consistente con la documentación

**Archivo**: `backend/modules/usuarios/domain/services/flujos/ingeniero_habilitado_flujo.py:124-128`

El try/except con `logger.exception` y sin re-raise es **intencional** según la documentación del método (líneas 101-102: "Efecto secundario invisible: no debe romper la respuesta del endpoint"). Esto no viola el contrato porque:

1. El contrato habla de manejo de errores en el orquestador/core para casos de **validación de negocio** (raise HttpError)
2. El registro de búsqueda es un efecto secundario que no debe afectar la respuesta del endpoint
3. La documentación del propio flujo explicitó esta decisión

**Sin embargo**: si el CRITICAL de atomicidad se materializa, el efecto invisible esconderá el fallo dejando la BD en estado inconsistente. Por eso el CRITICAL tiene prioridad.

---

## Risks

| Riesgo | Probabilidad | Impacto | Mitigation |
|--------|-------------|---------|------------|
| PerfilIngeniero huérfano sin registro de búsqueda (si falla `registrar_busqueda` tras `get_or_create`) | Media (errores de BD, constraint violada) | Inconsistencia de datos | Agregar `@transaction.atomic` |
| Desconocimiento del equipo sobre la ausencia de atomicidad | Baja (el código estádocumentado) | Debt técnico | Documentar en code review |
| Violación del patrón de separación Core/ORM | Baja (funciona correctamente) | Inconsistencia arquitectural | Refactorizar `get_or_create` a core service |

---

## Next Recommended

**`apply-fix`** — Antes de `sdd-verify`, resolver el CRITICAL aplicando `@transaction.atomic` a `_registrar_busqueda_async`. Opcionalmente, mover el `get_or_create` a `PerfilIngenieroCoreService` como mejora de consistencia arquitectural (SUGGESTION).

---

## Skill Resolution

- `sdd-explore`: Loaded from `C:\Users\Usuario\.claude\skills\sdd-explore\SKILL.md`
- `_shared/sdd-phase-common.md`: Loaded from `C:\Users\Usuario\.config\opencode\skills\_shared\sdd-phase-common.md`
