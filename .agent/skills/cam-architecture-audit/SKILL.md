---
name: cam-architecture-audit
description: Auditoría y corrección del backend CAM contra el contrato contract/PLAN_REFACTORIZACION.md. Detectar violaciones de arquitectura (controladores con lógica, ORM en presenters, imports relativos, schemas sin BaseSchema, returns gigantes) y corregirlas. Trigger: revisar si el backend cumple el plan, corregir malas prácticas, auditar código reciente, verificar que delegaciones respetaron el contrato.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# CAM Architecture Audit (Contrato Backend)

> **Fuente de verdad única:** `contract/PLAN_REFACTORIZACION.md`. Este skill NO duplica el contrato — lo opera. Ante cualquier duda, relee el contrato.

## 1. Reglas del Usuario (CAM — NO negociables)

- **PROHIBIDO usar git** — ni status/stash/checkout/commit/reset/push. Trabajar solo sobre el working tree.
- **`contract/PLAN_REFACTORIZACION.md` es el contrato único** del backend. Ignorar `django-app-architecture-contract.md` (obsoleto).
- **No crear `src/shared/` global** en frontend — todo dentro de `features/`. Como mucho `features/{domain}/shared/`.
- **No propiedades en modelos** — pero sí eliminar columnas si el usuario lo pide.
- **Controllers sagrados** (cero if/ORM/error_response). `HttpError` en orchestrator/flujo. Imports absolutos `modules.liquidaciones.*`. `BaseSchema` en In/Out. `transaction.atomic` SOLO en flujos.

## 2. Cómo Auditar (Workflow)

### Paso 1 — Leer el contrato
Lee `contract/PLAN_REFACTORIZACION.md` completo ANTES de tocar cualquier archivo.

### Paso 2 — Escanear el backend
Usa Grep para buscar anti-patrones en `backend/modules/` (excluye `migrations/`, `tests/`, `admin/`, `seeds/`):

| Anti-patrón | Grep a buscar |
|-------------|---------------|
| ORM en controllers/presenters | `\.objects\.(all|get|filter|create)` en `presentation/controllers` y `presentation/presenters` |
| `if`/`for` en controllers | `\b(if|for|while)\b` en `presentation/controllers` |
| Retorno manual de errores | `error_response` en `presentation/controllers` |
| Imports relativos | `^from \.\.|^from \.|^import \.` en `modules/*/domain` y `presentation` |
| Schemas sin BaseSchema | `class \w+(In|Out)` que no heredan de `BaseSchema` |
| `transaction.atomic` fuera de flujos | `@transaction.atomic` o `transaction.atomic` en archivos que NO sean `flujos/*` |
| `sync_to_async` incorrecto | `sync_to_async` en controllers (debe estar en orchestrator o capa async) |
| Returns masivos | `return await` con objetos enormes en orchestrators sin asignar a variable |
| Presenter con lógica pesada | métodos no-static en presenters |

### Paso 3 — Clasificar hallazgos
- **Violación grave (V)**: ORM en controller, `if` en controller, `error_response` manual, `transaction.atomic` en core/orchestrator, imports relativos.
- **Violación menor (M)**: presenter con método de instancia, schema sin BaseSchema, return no asignado a variable en orchestrator.
- **OK**: cumplimiento.

### Paso 4 — Corregir (si se pide)
1. Mover lógica del controller → orchestrator (validaciones) o flujo (transacciones).
2. Lanzar `HttpError(400/404, msg)` en orchestrator/core, NO retornar errores.
3. Convertir imports relativos a absolutos (`modules.{app}.{capa}.{subcapa}.{archivo}`).
4. Cambiar schemas a `from core.types import BaseSchema` (In/Out).
5. Mover `@transaction.atomic` solo a flujos.
6. Asignar el resultado de `sync_to_async(...)` a una variable en el orchestrator.
7. Presenters: solo `@staticmethod`/`@classmethod`, cero ORM.

## 3. Verificación Final (Siempre)

Después de corregir, verifica:
- [ ] `npx tsc --noEmit` en `frontend/` (si tocaste frontend)
- [ ] `python -m manage.py check` en `backend/` (si tocaste backend)
- [ ] Tests: `python -m manage.py test modules/liquidaciones modules/finanzas --settings=config.settings.test`
- [ ] Ningún archivo queda con anti-patrón de la tabla del Paso 2
- [ ] NO usar git en ningún momento

## 4. Reporte de Salida (Obligatorio)

Al terminar, devuelve:
```
## Hallazgos
- [Archivo:línea] V/M — descripción (antes → después)

## Corregido
- lista de archivos cambiados con qué se movió a dónde

## Verificación
- checks corridos + resultado

## Pendiente (si existe)
- lo que requiere decisión del usuario
```