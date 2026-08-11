# Architecture Validation: liquidaciones-query-filters

**Status**: partial
**Date**: 2026-08-11
**Project**: comision-asuntos-municipales
**Scope**: 13 files (1 core service, 6 orchestrators, 6 controllers) — query filters on 6 GET `/liquidaciones/{tipo}/` list endpoints

---

## Executive Summary

La implementación respeta el contrato `contract/PLAN_REFACTORIZACION.md` a nivel de arquitectura: los controllers son "sagrados" (solo parsean query params con `Query(...)`, renombran params y delegan; cero `if`/`for`/ORM/`error_response`), los orquestadores son pasamanos finos (reciben 8 kwargs de filtro y los reenvían al core), y el filtrado vive exclusivamente en el Core service (`LiquidacionGeneralCoreService`) como `.filter()` encadenados solo para params no-None, antes de `count()`/offset — exactamente el patrón del spec `openspec/changes/liquidaciones-query-filters/exploration.md` v3. No se encontró ninguna violación CRITICAL del contrato. Los hallazgos son de menor severidad: (1) los 51 tests de listado NO ejercitan ningún filtro (son estructurales pre-existentes; ningún archivo de tests fue modificado) y los conteos reportados (60 / 9-9-8-7-7-9) no coinciden con la realidad (51 / 9-9-8-8-8-9); (2) divergencia menor de firma entre los 6 controllers (2 de 6 incluyen un `request` sin usar); (3) inconsistencia pre-existente de `auth=None` en el listado (solo edificaciones). El contrato no menciona filtros/query params explícitamente — la guía operativa es el spec de openspec, que la implementación sigue fielmente.

## Validation by Layer

| Layer | Contract Rule (quote) | Complies? | Evidence (file:line) |
|---|---|---|---|
| Controller | §1.A "El controlador solo hace 3 cosas: Parsear la entrada, llamar al Orquestador, y retornar el éxito formateado por un Presenter" | ✅ Yes | `liquidacion_edificaciones_controller.py:73-107` (Query parse + delegación + `success_response(presenter.present_list(...))`); sin `if`/`for`/ORM/`error_response` en los 6 controllers |
| Controller | §2 "La firma de un controlador solo puede aceptar self, request, el payload..., y parámetros de ruta/query" | ✅ Yes (with divergence) | Todos los params son `Query(...)`; pero `liquidacion_taludes_controller.py:61` y `liquidacion_impacto_vial_controller.py:62` incluyen `request` sin usar en el listado, los otros 4 no → divergencia entre los 6 |
| Controller | §2 Patrón de query params (Ninja) — spec exploration "Convenciones Ninja: `page: int = Query(default=1, ge=1)`" | ✅ Yes | `liquidacion_edificaciones_controller.py:75-76`; inline `Query(...)` coincide con la convención actual del repo |
| Orchestrator | §4 "Orchestrator: Contiene validaciones complejas... Lanza HttpError" | ✅ Yes | `liquidacion_edificaciones_orchestrator.py:275-311` — paginación validada (boundaries) y passthrough puro de los 8 filtros |
| Orchestrator | Spec exploration: "Orchestrator → recibe kwargs → los pasa al core service" | ✅ Yes | `liquidacion_edificaciones_orchestrator.py:279-311`; firma idéntica en los 6 (`mecanica_suelos_orchestrator.py:164-174`) |
| Core | §4 "Core: Transaccionalidad pura del ORM de Django (get, create, filter). Cero lógica de negocio condicional" | ✅ Yes | `liquidacion_general_core_service.py:159-175` — `if` solo como guard de params opcionales, `.filter()` ORM puro |
| Core | Spec exploration: "Core service → recibe kwargs → encadena .filter() al QuerySet ANTES de offset/limit" | ✅ Yes | `liquidacion_general_core_service.py:142-179` (filters 160-175; `count()` 177; offset/limit 178-179) |
| Core | Spec exploration: "Para `numero`, cada método sabe su tipo → filtra sobre el JOIN correcto" | ✅ Yes | `edificaciones__numero` (173), `taludes__numero` (351), `habilitacion_urbana__numero` (231), `impacto_vial__numero` (473), `inspeccion_obra__numero` (411), `mecanica_suelos__numero` (289) |
| Consistency (6 tipos) | Patrón uniforme entre los 6 endpoints | ⚠️ Partial | Firmas de orquestadores y kwargs idénticas; divergencia `request` en 2/6 controllers; anotación de retorno `-> tuple` sin tipo en MS (`mecanica_suelos_orchestrator.py:174`) e IO (`inspeccion_obra_orchestrator.py:203`) |
| Tests | Claim de verificación "60 list tests pass" (apply-progress) | ❌ No | Conteo real: 51 tests (9+9+8+8+8+9); ningún test ejercita filtros; `git diff` de `backend/modules/liquidaciones/tests/` está vacío |

## Findings

### CRITICAL
Ninguno. No se detectó violación del contrato a nivel de arquitectura: el filtrado vive en el Core (capa ORM), el controller no introduce lógica, y el orquestador es pasamanos fino.

### WARNING

1. **Cobertura de tests: los filtros no están verificados funcionalmente**
   - Evidencia: `apply-progress.md:57-65` (afirma "All 60 list tests pass" con conteos 9/9/8/7/7/9=49, que no coinciden con la realidad 9/9/8/8/8/9=51); los 6 archivos `test_*_list.py` no contienen ningún test que envíe `entidad_id`/`propietario`/`razon_social`/`fecha_desde`/`fecha_hasta`/`numero`/`creado_por`/`numero_revisiones`; `git diff HEAD --stat -- backend/modules/liquidaciones/tests/` no devuelve nada (ningún test modificado/agregado).
   - Por qué importa: un bug en la lógica de filtrado (p.ej. un param ignorado o un nombre mal mapeado) pasaría los 51 tests verdes. La afirmación de verificación está sobrestimada y el comportamiento central del cambio está sin protección de regresión.

2. **Divergencia de firma entre los 6 controllers (request sin usar en 2/6)**
   - Evidencia: `liquidacion_taludes_controller.py:61` y `liquidacion_impacto_vial_controller.py:62` incluyen `request` en el método de listado; los otros 4 (`liquidacion_edificaciones_controller.py:73-75`, `liquidacion_habilitacion_urbana_controller.py:76-78`, `liquidacion_inspeccion_obra_controller.py:73-75`, `liquidacion_mecanica_suelos_controller.py:76-78`) no.
   - Por qué importa: rompe la uniformidad del patrón entre los 6 tipos (el spec de exploración documenta los 6 como el mismo patrón) y sugiere copy-paste incompleto.

3. **Inconsistencia pre-existente de `auth=None` en el listado (no introducida por este cambio)**
   - Evidencia: `liquidacion_edificaciones_controller.py:71` tiene `auth=None` en GET list; los otros 5 listados (`taludes:56`, `habilitacion_urbana:71`, `impacto_vial:56`, `inspeccion_obra:68`, `mecanica_suelos:71`) no lo tienen.
   - Por qué importa: la misma operación (listado con filtros) tiene semántica de autenticación distinta según el tipo de liquidación; afecta al consumidor de los filtros.

### SUGGESTION

1. **Anotación de retorno inconsistente en orquestadores**: MS (`liquidacion_mecanica_suelos_orchestrator.py:174`) e IO (`liquidacion_inspeccion_obra_orchestrator.py:203`) usan `-> tuple` sin tipo; los otros 4 tipan `tuple[List[XxxPrimeraRevisionResult], int]`. Alinear.
2. **`**kwargs` en los 6 métodos del core traga typos silenciosamente** (`liquidacion_general_core_service.py:134`, `193`, `251`, `309`, `371`, `431`): un param mal escrito (p.ej. `numero_revisiones` vs `numero_revision`) no fallaría. Considerar quitarlo o validarlo.
3. **Semántica de `numero_revisiones`**: el spec de exploración (`exploration.md:47`) documenta "`numero_revision__gte`, `numero_revision__exact` | gte/exact"; la implementación solo hace `exact` (`liquidacion_general_core_service.py:174-175`). Si el producto quiere "revisiones >= N", falta `__gte`. Confirmar intención.
4. **Nombres de params vs spec**: el spec (`exploration.md:40`) usa `entidad` y la implementación expone `entidad_id`; `creado_por`/`numero_revisiones` sí coinciden. Los nombres de la API quedan como contrato público — documentar para el frontend (hoy `useLiquidacionList.ts:44` solo envía `page`/`page_size`; los filtros no tienen consumidor aún).
5. **Duplicación del bloque de filtros** (8 `if` idénticos × 6 métodos, `liquidacion_general_core_service.py:160-175` y repetidos): un helper `_apply_filtros_comunes(qs, **kwargs)` reduciría el riesgo de drift futuro, aunque el patrón actual es explícito y el spec lo sanciona.

## Contract mentions of filters/query params (verificación punto 5)

`contract/PLAN_REFACTORIZACION.md` NO menciona filtros, query params, schemas de entrada ni capas de presentación/dominio específicamente para listados. Las reglas aplicables son genéricas: §1.A (controller sagrado: "Parsear la entrada"), §2 (firmas: "parámetros de ruta/query" permitidos), §4 (Core: "filter" ORM puro). La guía operativa específica es el spec `openspec/changes/liquidaciones-query-filters/exploration.md` v3, que la implementación sigue fielmente (kwargs → passthrough → `.filter()` en core antes de offset/limit). No hay regla del contrato que la implementación viole.

## Risks

- **Riesgo de regresión no detectado**: los filtros no tienen tests de comportamiento; un cambio futuro (o un bug actual silencioso) no sería capturado por la suite.
- **Riesgo de drift de API**: los nombres de query params (`entidad_id`, `creado_por`, `numero_revisiones`) se eligieron en el controller, no en un schema `BaseSchema` central como `TarifasHistoricasQueryParams`; si el frontend adopta otros nombres, el mapeo se rompe en silencio.
- **Riesgo bajo de duplicados**: descartado — los 6 `{tipo}__numero` filtran sobre `OneToOneField` (verificado en `liquidacion_edificaciones.py:28-33` y los 5 análogos), por lo que el JOIN no multiplica filas; no se requiere `.distinct()`.
- **N+1**: los filtros `{tipo}__numero` y `proyecto__*` usan joins ya cubiertos por `select_related`/`prefetch_related` existentes; sin joins nuevos (spec `exploration.md:111-114`).

## Next Recommended

`apply-fix` (scope acotado, sin tocar la arquitectura que ya cumple):
1. Agregar tests de comportamiento por filtro (mínimo 1 test por param, 6 archivos) y corregir los conteos en `apply-progress.md` (51 reales).
2. Alinear los 2 controllers divergentes (eliminar `request` sin usar en taludes/impacto_vial).
3. Confirmar semántica de `numero_revisiones` (exact vs gte) y documentar los nombres de params para el frontend.
4. (Opcional) Resolver la inconsistencia pre-existente de `auth=None` en el listado de edificaciones.

## Persistence Notes

- `mem_save` (title: `sdd/liquidaciones-query-filters/architecture-validation`, type: `architecture`, topic_key: `sdd/liquidaciones-query-filters/architecture-validation`, project: `comision-asuntos-municipales`, capture_prompt: `false`): **NO ejecutado** — esta sesión no expone el servidor MCP de Engram (`list_mcp_resources` → vacío). Pendiente de registrar manualmente.
- Este archivo cumple el requisito de artifact store (`openspec/changes/liquidaciones-query-filters/architecture-validation.md`).
