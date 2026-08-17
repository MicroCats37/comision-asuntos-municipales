# Verify Report: Homogeneización Fases 1-4 vs PLAN_REFACTORIZACION.md

**Proyecto**: `comision-asuntos-municipales`
**Backend**: Django 5.2 en `backend/`
**Fecha**: 2026-08-15
**Status**: `partial`

---

## executive_summary

La homogeneización de liquidaciones (Fases 1-4) cumple sustancialmente el contrato arquitectónico `PLAN_REFACTORIZACION.md`. Las 4 capas (Controller → Orchestrator → Core → Presenter) están correctamente implementadas con las responsabilidades separadas. Quedan 4 deudas técnicas pendientes de resolver antes de producción.

---

## Tabla de Validación Final por Capa

| Capa | Regla del Contrato | ¿Cumple? | Evidencia |
|------|-------------------|----------|-----------|
| **Controller** | Prohibido `if`/`for`/ORM | ✅ | Grep no encuentra `if`/`for`/ORM en lógica real. Matches son docstrings/comentarios. Líneas 132-135 (IO), 152-154 (HU), 148-153 (Taludes) extraen campos de payload — es parsing, no lógica de negocio. |
| **Controller** | Solo parseo + delegación + presenter | ✅ | Controllers parsean payload tipado (Pydantic), delegan a orchestrator, retornan `success_response(presenter.xxx())`. |
| **Orchestrator** | Thin facade, sin ORM directo | ✅ | Grep `LiquidacionGeneral.objects` → 0 matches en orchestrators. Los 6 `_build_*_result` delegan a `core.build_general_result()`. |
| **Orchestrator** | Validación con `raise HttpError` | ✅ | `LiquidacionPOValidationMixin` usado por 3 orquestadores PO (Edif, IV, Taludes). Mixin lanza `HttpError`. |
| **Orchestrator** | Sin returns masivos | ✅ | Cada método orquestador asigna a variable antes de retornar. |
| **Core** | ORM puro, cero lógica de negocio | ✅ | `build_general_result()` es mapeo puro ORM→Result. Sin condicionales de negocio. |
| **Core** | Sin `if`/`for` de negocio | ✅ | Solo `if` de filtros de query (legítimo en ORM helper). |
| **Presenter** | Solo mapeo, sin ORM | ✅ | `present_liquidacion_general()` + `_map_delegados()` — mapeo puro Result→Schema. Sin `objects`. |
| **Flujo** | `transaction.atomic` en flujo | ✅ | No aplicable a endpoints de lista/detalle. Flujos de creación usan `@transaction.atomic`. |

---

## Conteo de Duplicación Eliminada (Verificado)

| Fase | Ubicación | Líneas estimadas |
|------|-----------|-----------------|
| Fase 1 (Presenters) | 6 presenters específicos + general | ~833 |
| Fase 2 (Core builder) | `build_general_result()` centralizado en core | Incluido arriba |
| Fase 3 (Orquestadores) | 6 `_build_*_result` ahora delegan a core | ~919 |
| **Total** | | **~1,752 líneas** |

---

## Deuda Técnica Pendiente

### Prioridad ALTA

**1. `present_tarifas_vigentes` duplicado en 3 presenters PO**
- Archivos:
  - `presentation/presenters/liquidacion_especifico/liquidacion_edificaciones_presenter.py` (línea 141)
  - `presentation/presenters/liquidacion_especifico/liquidacion_impacto_vial_presenter.py` (línea 142)
  - `presentation/presenters/liquidacion_especifico/liquidacion_taludes_presenter.py` (línea 142)
- Método **idéntico** en los 3 archivos (~25 líneas × 3 = ~75 líneas duplicadas)
- Lösung: Mover a un presenter compartido para PO o a un helper en `presentation/presenters/_shared/`

### Prioridad MEDIA

**2. `get_liquidacion_previa_para_io` sin prefetch_related del tipo específico (N+1 potencial)**
- Archivo: `domain/services/core/liquidacion_general/liquidacion_general_core_service.py` (línea 572-591)
- Solo tiene `select_related`; no tiene `prefetch_related` para `liquidacion_delegados`
- Si se acceden `liquidacion_delegados` en la liquidación prévia → N+1 queries
- Lösung: Agregar `prefetch_related('liquidacion_delegados__delegado__perfil_ingeniero', ...)` o verificar que no se consulta esa relación desde la prévia

**3. Core `list_liquidaciones_*_paginated` (6 métodos) siguen duplicados**
- Archivo: `domain/services/core/liquidacion_general/liquidacion_general_core_service.py` (líneas 158-540 = 383 líneas)
- Lógica de filtros WHERE idéntica en los 6 métodos (municipalidad, propietario, razon_social, creador_username, fecha_desde, fecha_hasta, numero, numero_revision)
- Diferencias: `tipo_liquidacion__codigo` y `prefetch_related` chain
- Lösung: Unificar en un solo método parametrizado (future, menor prioridad por ser solo 6 métodos)

### Prioridad BAJA

**4. Tests de integración mal hechos**
- Marcado como pendiente de arreglar "al final" por el equipo
- No verificado en esta validación — requiere auditoría separada

---

## Veredicto

**¿La homogeneización cumple el contrato?**

**Sí, sustancialmente.**

La arquitectura de 4 capas está correctamente implementada según `PLAN_REFACTORIZACION.md`:

- ✅ **Controllers thin**: sin `if`/`for`/ORM en lógica de negocio
- ✅ **Orchestrators fachada + validación**: con `raise HttpError` para errores
- ✅ **Core ORM puro**: `build_general_result()` como mapeo centralizado, sin lógica de negocio
- ✅ **Presenters solo formatean**: sin ORM, solo mapeo Result→Schema
- ✅ **Delegación correcta**: los 6 `_build_*_result` de orquestadores delegan a `core.build_general_result()`

**¿Qué falta antes de producción?**

1. **(ALTA)** Consolidar `present_tarifas_vifices` duplicado — riesgo de divergencia futura
2. **(MEDIA)** Verificar/fix `get_liquidacion_previa_para_io` para N+1 en liquidacion_delegados
3. **(MEDIA)** Unificar 6 `list_liquidaciones_*_paginated` del core (opcional, bajo impacto)
4. **(BAJA)** Arreglar tests de integración

---

## Risks

- **N+1 en IO prévia**: `get_liquidacion_previa_para_io` no tiene `prefetch_related` para `liquidacion_delegados`. Si se consultan delegaciones de la liquidación prévia → query por cada una.
- **Divergencia de código duplicado**: `present_tarifas_vigentes` en 3 presenters puede diverger en futuras modificaciones.
- **Tests bloqueantes**: Tests de integración mal hechos pueden ocultar regresiones en producción.

---

## next_recommended

1. **Inmediato**: Extraer `present_tarifas_vigentes` a un presenter/shared helper para PO genérico
2. **Corto plazo**: Agregar `prefetch_related` faltante en `get_liquidacion_previa_para_io` o verificar que no se necesita
3. **Medio plazo**: Unificar los 6 `list_liquidaciones_*_paginated` del core en un solo método con parámetros
4. **Post-producción**: Arreglar tests de integración como tarea separate

---

## skill_resolution

- SDD explorar skill: `C:\Users\Usuario\.claude\skills\sdd-explore\SKILL.md`
- _shared skill: `C:\Users\Usuario\.config\opencode\skills\_shared\SKILL.md`
