# SDD Tasks: Homogeneizar presenters + cards/modal delegados

## Status
**success**

## Executive Summary
Plan de tareas modular, verificable y en orden de dependencias para:
1. Extraer `_map_delegados()` en `LiquidacionGeneralPresenter` y reutilizarlo en los 6 presenters específicos
2. Crear hook `useDelegadosModal` + componente `DelegadosButtonModal` en frontend para eliminar la duplicación de estado + modal en las 5 cards activas

---

## Task Breakdown

### Backend Tasks

#### T-1 · Extraer `_map_delegados()` en `LiquidacionGeneralPresenter`
| Campo | Detalle |
|-------|---------|
| **Archivos** | `backend/modules/liquidaciones/presentation/presenters/liquidacion_general/liquidacion_general_presenter.py` |
| **Depende de** | Ninguno |
| **Qué hace** | Agrega el método estático `_map_delegados(general: LiquidacionGeneralResult) -> list[LiquidacionDelegadoOut]` que extrae el bloque de mapeo de delegados (las 22 líneas que se repiten en cada presenter específico). También agrega `_map_general_output(general: LiquidacionGeneralResult) -> LiquidacionGeneralOutput` que construye el output general completo (sin `delegados`). |
| **Cambio exacto** | En `liquidacion_general_presenter.py`, después del método `_map_result_to_output()` existente: agregar `_map_delegados(general) → list[LiquidacionDelegadoOut]` y `_map_general_output(general) → LiquidacionGeneralOutput` (ambos `@staticmethod`). |
| **Verificación** | `python -m pytest backend/modules/liquidaciones/tests/integration/test_edificaciones_list.py -v` — verificar que la respuesta HTTP incluya `delegados` populated en items de list |

#### T-2 · Modificar `LiquidacionGeneralPresenter.present_list()` para usar `_map_delegados`
| Campo | Detalle |
|-------|---------|
| **Archivos** | `backend/modules/liquidaciones/presentation/presenters/liquidacion_general/liquidacion_general_presenter.py` |
| **Depende de** | T-1 |
| **Qué hace** | Modificar `present_list()` para que `_map_result_to_output()` también setee el campo `delegados` usando `_map_delegados(general)`. Consecuencia: el endpoint `GET /liquidaciones/generales` começará a retornar `delegados` populated. |
| **Verificación** | Test HTTP ya existente para `LiquidacionGeneralController.list_liquidaciones` deve verificar que la respuesta incluya `delegados` (si la liquidacion los tiene en el result). |

#### T-3 · Modificar `LiquidacionEdificacionesPresenter.present_primera_revision()` para reutilizar `_map_delegados`
| Campo | Detalle |
|-------|---------|
| **Archivos** | `backend/modules/liquidaciones/presentation/presenters/liquidacion_especifico/liquidacion_edificaciones_presenter.py` |
| **Depende de** | T-1 |
| **Qué hace** | Reemplazar el bloque `delegados=[...]` en `present_primera_revision()` (líneas 153-174 actuales) por una llamada a `LiquidacionGeneralPresenter._map_delegados(general)`. Elimina ~22 líneas duplicadas. |
| **Verificación** | `python -m pytest backend/modules/liquidaciones/tests/integration/test_edificaciones_list.py -v` y `test_edificaciones_detail.py -v` — respuesta HTTP sigue incluyendo `delegados` populated |

#### T-4 · Modificar `LiquidacionTaludesPresenter.present_primera_revision()`
| Campo | Detalle |
|-------|---------|
| **Archivos** | `backend/modules/liquidaciones/presentation/presenters/liquidacion_especifico/liquidacion_taludes_presenter.py` |
| **Depende de** | T-1 |
| **Qué hace** | Mismo reemplazo: bloque `delegados=[...]` (líneas 138-159) → `LiquidacionGeneralPresenter._map_delegados(general)`. |
| **Verificación** | `python -m pytest backend/modules/liquidaciones/tests/integration/test_taludes_list.py -v` y `test_taludes_detail.py -v` |

#### T-5 · Modificar `LiquidacionHabilitacionUrbanaPresenter.present_primera_revision()`
| Campo | Detalle |
|-------|---------|
| **Archivos** | `backend/modules/liquidaciones/presentation/presenters/liquidacion_especifico/liquidacion_habilitacion_urbana_presenter.py` |
| **Depende de** | T-1 |
| **Qué hace** | Reemplazar bloque `delegados=[...]` (líneas ~149-170) por `LiquidacionGeneralPresenter._map_delegados(general)`. |
| **Verificación** | `python -m pytest backend/modules/liquidaciones/tests/integration/test_hu_list.py -v` |

#### T-6 · Modificar `LiquidacionImpactoVialPresenter.present_primera_revision()`
| Campo | Detalle |
|-------|---------|
| **Archivos** | `backend/modules/liquidaciones/presentation/presenters/liquidacion_especifico/liquidacion_impacto_vial_presenter.py` |
| **Depende de** | T-1 |
| **Qué hace** | Reemplazar bloque `delegados=[...]` (líneas ~138-159) por `LiquidacionGeneralPresenter._map_delegados(general)`. |
| **Verificación** | `python -m pytest backend/modules/liquidaciones/tests/integration/test_iv_list.py -v` |

#### T-7 · Modificar `LiquidacionInspeccionObraPresenter.present_primera_revision()`
| Campo | Detalle |
|-------|---------|
| **Archivos** | `backend/modules/liquidaciones/presentation/presenters/liquidacion_especifico/liquidacion_inspeccion_obra_presenter.py` |
| **Depende de** | T-1 |
| **Qué hace** | Reemplazar bloque `delegados=[...]` (líneas ~139-160) por `LiquidacionGeneralPresenter._map_delegados(general)`. |
| **Verificación** | `python -m pytest backend/modules/liquidaciones/tests/integration/test_io_list.py -v` |

#### T-8 · Modificar `LiquidacionMecanicaSuelosPresenter.present_primera_revision()`
| Campo | Detalle |
|-------|---------|
| **Archivos** | `backend/modules/liquidaciones/presentation/presenters/liquidacion_especifico/liquidacion_mecanica_suelos_presenter.py` |
| **Depende de** | T-1 |
| **Qué hace** | Reemplazar bloque `delegados=[...]` (líneas ~153-174) por `LiquidacionGeneralPresenter._map_delegados(general)`. |
| **Verificación** | `python -m pytest backend/modules/liquidaciones/tests/integration/test_ms_list.py -v` |

#### T-9 · Tests de regresión: verificar campo `delegados` en respuestas de los 6 tipos
| Campo | Detalle |
|-------|---------|
| **Archivos** | `backend/modules/liquidaciones/tests/integration/test_edificaciones_list.py`, `test_taludes_list.py`, `test_hu_list.py`, `test_iv_list.py`, `test_io_list.py`, `test_ms_list.py` |
| **Depende de** | T-2 a T-8 |
| **Qué hace** | Agregar assertion en cada test de list que verifica `item["liquidacion_general"]["delegados"]` — que sea `list` y que los elementos tengan `delegado_id`, `especialidad_revision.nombre`, `delegado.nombre_completo`. |
| **Verificación** | `python -m pytest backend/modules/liquidaciones/tests/integration/ -v -k "list" --tb=short` — todos pasan |

---

### Frontend Tasks

#### T-10 · Crear hook `useDelegadosModal`
| Campo | Detalle |
|-------|---------|
| **Archivos** | `frontend/src/features/liquidaciones/hooks/useDelegadosModal.ts` (nuevo) |
| **Depende de** | Ninguno |
| **Qué hace** | Crea hook que recibe `liquidacionId`, `municipalidadId`, `tipoLiquidacion`, `delegadosActuales` y retorna `{ isOpen, setIsOpen, triggerButton, modal }` — o simplemente `{ isOpen, setIsOpen }` para ser usado dentro del card. El hook gestiona el estado `useState(false)`. |
| **Verificación** | TypeScript compila sin errores: `cd frontend && npx tsc --noEmit` |

#### T-11 · Refactorizar `LiquidacionEdificacionesCard` para usar hook
| Campo | Detalle |
|-------|---------|
| **Archivos** | `frontend/src/features/liquidaciones/components/cards/LiquidacionEdificacionesCard.tsx` |
| **Depende de** | T-10 |
| **Qué hace** | Reemplazar `useState(false)` + botón + modal por `useDelegadosModal(...)`. Eliminando `useState` de `delegadosModalOpen`, botón "Delegados" inline, y `<GestionarDelegadosModal>` al final del JSX. |
| **Verificación** | Card sigue funcionando igual en UI — verificar que al hacer click en "Delegados" se abre el modal y guarda correctamente. |

#### T-12 · Refactorizar `LiquidacionTaludesCard`
| Campo | Detalle |
|-------|---------|
| **Archivos** | `frontend/src/features/liquidaciones/components/cards/LiquidacionTaludesCard.tsx` |
| **Depende de** | T-10 |
| **Qué hace** | Mismo reemplazo que T-11. |
| **Verificación** | Card funciona igual. |

#### T-13 · Refactorizar `LiquidacionHabilitacionUrbanaCard`
| Campo | Detalle |
|-------|---------|
| **Archivos** | `frontend/src/features/liquidaciones/components/cards/LiquidacionHabilitacionUrbanaCard.tsx` |
| **Depende de** | T-10 |
| **Qué hace** | Mismo reemplazo. |
| **Verificación** | Card funciona igual. |

#### T-14 · Refactorizar `LiquidacionImpactoVialCard`
| Campo | Detalle |
|-------|---------|
| **Archivos** | `frontend/src/features/liquidaciones/components/cards/LiquidacionImpactoVialCard.tsx` |
| **Depende de** | T-10 |
| **Qué hace** | Mismo reemplazo. |
| **Verificación** | Card funciona igual. |

#### T-15 · Refactorizar `LiquidacionMecanicaSuelosCard`
| Campo | Detalle |
|-------|---------|
| **Archivos** | `frontend/src/features/liquidaciones/components/cards/LiquidacionMecanicaSuelosCard.tsx` |
| **Depende de** | T-10 |
| **Qué hace** | Mismo reemplazo. |
| **Verificación** | Card funciona igual. |

---

## Detalle de Extracción Backend

### Firma propuesta para `_map_delegados`

```python
@staticmethod
def _map_delegados(general: LiquidacionGeneralResult) -> list[LiquidacionDelegadoOut]:
    """
    Maps the 'delegados' flat-join fields from LiquidacionGeneralResult
    into a list of LiquidacionDelegadoOut schema objects.
    Returns [] if general.delegados is empty or None.
    """
    from modules.liquidaciones.presentation.schemas.delegado.delegado_batch_schemas import (
        LiquidacionDelegadoOut,
        EspecialidadRevisionOut,
        LiquidacionDelegadoDelegadoOut,
    )
    return [
        LiquidacionDelegadoOut(
            id=uuid.UUID(d.id),
            liquidacion_id=uuid.UUID(d.liquidacion_id),
            delegado_id=uuid.UUID(d.delegado_id),
            especialidad_revision=EspecialidadRevisionOut(
                id=uuid.UUID(d.especialidad_revision_id),
                nombre=d.especialidad_revision_nombre,
            ),
            delegado=LiquidacionDelegadoDelegadoOut(
                id=uuid.UUID(d.delegado_id),
                cip=d.delegado_cip,
                dni=d.delegado_dni,
                nombre_completo=d.delegado_nombre_completo,
            ),
            periodo=d.periodo,
            dictamen_revision=d.dictamen_revision,
            fecha_presentacion=d.fecha_presentacion,
            fecha_revision=d.fecha_revision,
        )
        for d in (general.delegados or [])
    ]
```

### Cómo reutilizan los 6 presenters específicos

Los presenters usan Ninja Extra DI ( `@inject` en `__init__`). Cada controller inyecta su presenter específico:

```python
# En LiquidacionEdificacionesController
@inject
def __init__(self, ..., presenter: LiquidacionEdificacionesPresenter, ...):
    self.presenter = presenter
```

Los presenters específicos no se injectan entre sí. Para reutilizar `_map_delegados`,有两种方法:

**Opción A (recomendada — sin cambiar DI):** Import directo estático
```python
# En liquidacion_edificaciones_presenter.py
from modules.liquidaciones.presentation.presenters.liquidacion_general.liquidacion_general_presenter import (
    LiquidacionGeneralPresenter,
)

# En present_primera_revision():
delegados=LiquidacionGeneralPresenter._map_delegados(general),
```

**Opción B (cambia DI):** Injectar `LiquidacionGeneralPresenter` en cada controller y cada presenter.
- **Riesgo:** Requiere cambiar 6+ archivos de controller + 6 archivos de presenter + módulo DI.
- **No recomendado** para este cambio.

Se selecciona **Opción A** — importación directa de clase estática, sin cambiar el sistema de DI existente.

### Nota sobre `present_primera_revision` vs `present_detail`
Los 6 presenters específicos usan `present_primera_revision` tanto para `list` como para `detail`. No existe un `present_detail` separado. El `LiquidacionGeneralPresenter.present_list()` del general NO llama a `present_primera_revision` — usa `_map_result_to_output()` internamente. Esto significa que el general list endpoint (`/liquidaciones/generales/`) hasta T-2 no retorna `delegados` populated.

---

## Detalle de Extracción Frontend

### Hook propuesto: `useDelegadosModal`

```typescript
// frontend/src/features/liquidaciones/hooks/useDelegadosModal.ts
"use client";
import { useState, useCallback } from "react";
import { GestionarDelegadosModal } from "../components/GestionarDelegadosModal";
import { Users } from "lucide-react";
import type { HasId } from "../components/GestionarDelegadosModal";

interface UseDelegadosModalOptions {
  liquidacionId: string;
  municipalidadId: string;
  tipoLiquidacion: string;
  delegadosActuales: HasId[];
}

export function useDelegadosModal({
  liquidacionId,
  municipalidadId,
  tipoLiquidacion,
  delegadosActuales,
}: UseDelegadosModalOptions) {
  const [isOpen, setIsOpen] = useState(false);

  const openModal = useCallback(() => setIsOpen(true), []);
  const closeModal = useCallback(() => setIsOpen(false), []);
  const toggleModal = useCallback((e?: React.MouseEvent) => {
    e?.stopPropagation();
    setIsOpen((prev) => !prev);
  }, []);

  const DelegadosButton = (
    <span
      role="button"
      tabIndex={0}
      onClick={toggleModal}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.stopPropagation(); setIsOpen((v) => !v); } }}
      className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border text-xs font-semibold border-border/60 hover:border-primary/40 hover:bg-primary/5 hover:text-primary cursor-pointer select-none transition-colors"
    >
      <Users className="h-3 w-3" />
      Delegados
    </span>
  );

  const DelegadosModal = (
    <GestionarDelegadosModal
      open={isOpen}
      onOpenChange={setIsOpen}
      liquidacionId={liquidacionId}
      municipalidadId={municipalidadId}
      tipoLiquidacion={tipoLiquidacion}
      delegadosActuales={delegadosActuales}
    />
  );

  return {
    isOpen,
    setIsOpen,
    openModal,
    closeModal,
    toggleModal,
    DelegadosButton,
    DelegadosModal,
  };
}
```

### Refactorización tipo en cada card

**Antes (Ejemplo Edificaciones):**
```tsx
const [delegadosModalOpen, setDelegadosModalOpen] = useState(false);
// ...
<span onClick={(e) => { e.stopPropagation(); setDelegadosModalOpen(true); }}>Delegados</span>
// ...
<GestionarDelegadosModal open={delegadosModalOpen} onOpenChange={setDelegadosModalOpen} ... />
```

**Después:**
```tsx
const { DelegadosButton, DelegadosModal } = useDelegadosModal({
  liquidacionId: lg.id,
  municipalidadId: lg.municipalidad?.id ?? "",
  tipoLiquidacion: "edificacion",
  delegadosActuales: (lg.delegados ?? []).map((d) => ({ id: d.delegado_id })),
});

// En rightSlotActions: agregar DelegadosButton al div
// Al final del return: {DelegadosModal}
```

### Nota sobre `LiquidacionBaseCard`
No se modifica `LiquidacionBaseCard` — la duplicación de estado `delegadosModalOpen` es simple (`useState(false)`) y el hook la abstrae completamente. Modificar `LiquidacionBaseCard` para aceptar un slot de delegados añadiría acoplamiento innecesario a un componente base.

---

## Orden de Ejecución Secuencial

```
Backend:
  T-1 (Tarea 1: extraer _map_delegados + _map_general_output)
    → T-2 (usar _map_delegados en present_list del general)
    → T-3..T-8 (reutilizar en 6 presenters específicos)
    → T-9 (tests de regresión para verificar delegados en respuestas)

Frontend:
  T-10 (crear useDelegadosModal hook)
    → T-11..T-15 (refactorizar 5 cards activas)
```

**Orden de commits recomendado** (work-unit-commits):
1. `feat(backend): extract _map_delegados in LiquidacionGeneralPresenter`
2. `feat(backend): wire _map_delegados into all 6 specific presenters`
3. `feat(backend): add integration tests verifying delegados field`
4. `feat(frontend): add useDelegadosModal hook`
5. `feat(frontend): refactor 5 liquidacion cards to use useDelegadosModal`

---

## Estimación

| Área | Archivos | Líneas aproximadas | Riesgo |
|------|---------|-------------------|--------|
| Backend: extraer métodos | 1 presenter + 6 presenters específicos | ~30 líneas nuevas, ~130 eliminadas | Bajo |
| Backend: tests | 6 archivos de test | ~60 líneas añadidas | Bajo |
| Frontend: hook | 1 archivo nuevo | ~60 líneas | Bajo |
| Frontend: refactorizar 5 cards | 5 archivos | ~5 líneas por archivo netas (se elimina ~25, se añade ~20) | Bajo |
| **Total** | **~14 archivos** | **~180 netas** | **Bajo** |

**Líneas netas del cambio completo:** ~180 (30 adds + 60 test adds + 60 hook + 30 card refactors - 130 de duplicación eliminada)

**Esfuerzo estimado:** ~4-6 horas para quien conoce el codebase.

---

## Decisiones Pendientes

1. **Opción de reutilización backend (A vs B):** Se selecciona Opción A (import directo estático). Confirmar con el equipo si se quiere cambiar el DI para inyectar el presenter general en los específicos (Opción B — más limpio pero más invasivo).
2. **`LiquidacionDetalleCard` en deprecated:** Este card también tiene el modal pero está en `features_deprecated/`. ¿Se refactoriza también o se deja como está? El plan no incluye esta card porque está en la carpeta deprecated.
3. **`InspeccionObraCard`:** Confirmar que NO se le añade el modal de delegados — usa inspectores. El hook `useDelegadosModal` NO debe usarse ahí.

---

## Mapeo a Secciones del Contrato `contract/PLAN_REFACTORIZACION.md`

| Tarea | Sección del contrato | Cómo aplica |
|-------|---------------------|-------------|
| T-1 a T-8 | **3.A Regla del Presenter**: "El Presenter tiene una sola responsabilidad: mapear datos crudos hacia Schemas Out" + "Solo @staticmethod" | Extraer `_map_delegados` como `@staticmethod` cumple la regla: mapeo puro, sin lógica de negocio. |
| T-1 a T-8 | **3.A**: "PROHIBIDO: Llamar a la base de datos" | Los presenters son @staticmethod puros — ningún acceso a ORM. |
| T-1 | **3.B Regla de Helpers**: "Deben nombrarse con _" | `_map_delegados` y `_map_general_output` son helpers internos del presenter, nombrados con guien bajo. |
| T-3..T-8 | **3.C Schemas API vs Results Internos**: "El Presenter toma estos Results y los convierte en Schemas Out" | Los presenters reciben `EdificacionesPrimeraRevisionResult` (domain result) y producen `LiquidacionEdificacionesOutput` (schema) — exactamente el flujo prescribed. |
| T-1..T-8 | **1.A Los Controladores son Sagrados**: "El controlador solo hace 3 cosas" | Los controllers ya son thin — las tareas T-1..T-8 solo tocan presenters, no controllers. |
| T-9 | **1.D Testing**: Los tests de integración existentes verifican endpoints HTTP — se añade verificación de campo `delegados` para cerrar el gap. |

---

## Risks

1. **Sin tests unitarios para presenters**: Los tests actuales son HTTP integration. Si `_map_delegados` se rompe, no hay test unitario que lo capture directamente — solo el test de integración lo detecta indirectamente.
2. **`InspeccionObra` usa inspectores, no delegados**: El hook `useDelegadosModal` no aplica a esta card. Si alguien copia el patrón hacia essa card, será un error sutil.
3. **`LiquidacionDetalleCard` en deprecated**: No se refactoriza en este plan — la duplicación ahí permanece.
4. **Campos de `LiquidacionDelegadoEnGeneralResult` asumen flat-join**: Los presenters específicos asumen que `general.delegados` es una lista de `LiquidacionDelegadoEnGeneralResult` con campos `delegado_cip`, `delegado_dni`, `delegado_nombre_completo`. Si el domain result cambia, todos los presenters se rompen simultáneamente.
5. **Deprecation de `features_deprecated/`**: Los cambios en backend no afectan la carpeta deprecated del frontend.

---

## Next Recommended
`sdd-apply`

---

## Skill Resolution
`paths-injected` — Recibí las rutas exactas del orchestrator (`sdd-explore\SKILL.md` y `_shared\SKILL.md`).
