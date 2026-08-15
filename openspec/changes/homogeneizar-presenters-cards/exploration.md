# SDD Exploration: Homogeneidad de presenters + cards/modal delegados

## Status
**success**

## Executive Summary
La exploración confirma los problemas estructurales descritos por el usuario:
1. **Backend**: `LiquidacionGeneralPresenter` NO mapea el campo `delegados` en `present_list()`, pero el schema `LiquidacionGeneralOutput` SÍ lo tiene definido (línea 155 de `general_schemas.py`). Los 6 presenters específicos duplican manualmente el mapeo de `delegados` en cada `present_primera_revision()` — exactamente ~22 líneas idénticas por archivo × 6 = **132 líneas duplicadas**.
2. **Frontend**: Las 6 cards repiten el patrón completo de `<GestionarDelegadosModal>` con estado local `delegadosModalOpen`/`setDelegadosModalOpen` y el botón "Delegados" en `rightSlotActions`. `InspeccionObraCard` NO incluye modal de delegados (usa inspectores, no delegados). `LiquidacionDetalleCard` también incluye su propio `<GestionarDelegadosModal>`.
3. **Tests**: Los tests de presenters son de integración (HTTP), no prueban presenters unitariamente. Los fixtures se duplican casi idénticos entre `test_edificaciones_list.py` y `test_taludes_list.py` (~90% igual).
4. **Contrato**: `contract/PLAN_REFACTORIZACION.md` NO existe en este proyecto (`CAM/aplicacion`). El archivo referenciado existe en `C:\Users\Usuario\Desktop\Aplicaciones\CIP\centro-de-esparcimiento\PLAN_REFACTORIZACION.md`, que pertenece a OTRO proyecto. **No se puede validar contra el contrato.**

---

## Mapa de Presenters

| Presenter | Métodos | ¿Mapea `delegados`? | Líneas duplicadas del general | Observaciones |
|---|---|---|---|---|
| `LiquidacionGeneralPresenter` | `present_list`, `present_detail` | **NO** (falta) | N/A | El schema tiene `delegados` pero el presenter no lo mapea |
| `LiquidacionEdificacionesPresenter` | `present_primera_revision`, `present_list`, `present_detalle`, `present_cotizacion`, `present_tarifas_vigentes` | **SÍ** (manual) | Líneas 153-174: 22 líneas del mapeo `delegados` | Duplica el mapeo de LiquidacionGeneralOutput completo |
| `LiquidacionTaludesPresenter` | `present_primera_revision`, `present_list`, `present_detalle`, `present_cotizacion`, `present_tarifas_vigentes` | **SÍ** (manual) | Líneas 138-159: 22 líneas idênticas a Edificaciones | Duplica |
| `LiquidacionHabilitacionUrbanaPresenter` | `present_primera_revision`, `present_list`, `present_detalle` | **SÍ** (manual) | Líneas 149-170: 22 líneas idênticas | Duplica |
| `LiquidacionImpactoVialPresenter` | `present_primera_revision`, `present_list`, `present_detalle`, `present_cotizacion`, `present_tarifas_vigentes` | **SÍ** (manual) | Líneas 138-159: 22 líneas idênticas | Duplica |
| `LiquidacionInspeccionObraPresenter` | `present_primera_revision`, `present_list`, `present_detalle` | **SÍ** (manual) | Líneas 139-160: 22 líneas idênticas | Duplica |
| `LiquidacionMecanicaSuelosPresenter` | `present_primera_revision`, `present_list`, `present_detalle` | **SÍ** (manual) | Líneas 153-174: 22 líneas idênticas | Duplica |

### Fragmento Duplicado (ejemplo de Edificaciones, líneas 153-174)
```python
delegados=[
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
],
```
Este bloque aparece **IDÊNTICO** (mismo código, mismas variables, mismo patrón) en los 6 presenters específicos.

### Construcción Completa de LiquidacionGeneralOutput Duplicada
Además del bloque `delegados`, los 6 presenters específicos también duplican la construcción completa del objeto `LiquidacionGeneralOutput` (~65 líneas por presenter) en sus métodos `present_primera_revision()`. Esto incluye:
- `municipalidad`, `usuario_creador`, `fecha_registro`, `expediente`, `observacion`, `numero_revision`, `sub_total`, `total`, `retencion`
- `igv`, `uit` (con sus null checks)
- `proyecto` completo (con `distrito` → `provincia` → `departamento`, `entidad`)
- `tipo_liquidacion`

---

## Tests de Presenters

### Archivos encontrados
```
backend/modules/liquidaciones/tests/
├── integration/
│   ├── test_edificaciones_list.py      (292 líneas)
│   ├── test_taludes_list.py             (332 líneas)
│   ├── test_hu_list.py
│   ├── test_iv_list.py
│   ├── test_io_list.py
│   ├── test_ms_list.py
│   ├── test_edificaciones_detail.py
│   ├── test_taludes_detail.py
│   └── ... (otros)
├── e2e/
│   ├── test_e2e_edificaciones.py
│   ├── test_e2e_taludes.py
│   └── ...
```

### Análisis de Cobertura

| Aspecto | Edificaciones | Taludes | Otros 5 |
|---|---|---|---|
| ¿Prueba el presenter directamente? | **NO** | **NO** | **NO** |
| ¿Prueba el endpoint HTTP? | SÍ | SÍ | SÍ |
| ¿Verifica campo `delegados` en respuesta? | **NO** | **NO** | **NO** |
| ¿Verifica estructura `liquidacion_general` completa? | Parcial (campos básicos) | Parcial (campos básicos) | No |

### Incoherencias Detectadas

1. **Fixtures duplicados**: `liquidacion_edificacion_created` (líneas 31-100 de `test_edificaciones_list.py`) y `liquidacion_taludes_created` (líneas 71-140 de `test_taludes_list.py`) son ~90% idénticos. La única diferencia es el tipo de liquidación y el número de expediente.

2. **No hay tests para `present_primera_revision` con delegados**: Ningún test verifica que la respuesta incluya el campo `delegados` poblado. Los tests de detalle solo verifican campos básicos.

3. **Tests NO son homogéneos**: Edificaciones tiene 9 tests de listado, Taludes tiene 9 tests (estructuralmente idénticos), pero los otros tipos tienen cantidades diferentes o no tienen tests de listado.

---

## Duplicación Frontend

### Cards con `<GestionarDelegadosModal>`

| Card | Archivo | Estado `delegadosModalOpen` | Botón "Delegados"? | Modal props |
|---|---|---|---|---|
| `LiquidacionEdificacionesCard` | `LiquidacionEdificacionesCard.tsx:57` | `useState(false)` | SÍ (líneas 88-97) | `liquidacionId`, `municipalidadId`, `tipoLiquidacion="edificacion"`, `delegadosActuales` |
| `LiquidacionTaludesCard` | `LiquidacionTaludesCard.tsx:41` | `useState(false)` | SÍ (líneas 79-96) | `liquidacionId`, `municipalidadId`, `tipoLiquidacion="taludes"`, `delegadosActuales` |
| `LiquidacionHabilitacionUrbanaCard` | `LiquidacionHabilitacionUrbanaCard.tsx:37` | `useState(false)` | SÍ (líneas 66-75) | `liquidacionId`, `municipalidadId`, `tipoLiquidacion="habilitacion_urbana"`, `delegadosActuales` |
| `LiquidacionImpactoVialCard` | `LiquidacionImpactoVialCard.tsx:45` | `useState(false)` | SÍ (líneas 83-100) | `liquidacionId`, `municipalidadId`, `tipoLiquidacion="impacto_vial"`, `delegadosActuales` |
| `LiquidacionInspeccionObraCard` | `LiquidacionInspeccionObraCard.tsx` | **NO TIENE** | **NO** | N/A — usa inspectores |
| `LiquidacionMecanicaSuelosCard` | `LiquidacionMecanicaSuelosCard.tsx:42` | `useState(false)` | SÍ (líneas 80-97) | `liquidacionId`, `municipalidadId`, `tipoLiquidacion="mecanica_suelos"`, `delegadosActuales` |
| `LiquidacionDetalleCard` | `LiquidacionDetalleCard.tsx:99,421` | `useState(false)` | SÍ (líneas 129-137) + botón interno (líneas 365-372) | Props diferentes: `delegados` del item directamente |

### Patrón Repetido en Cada Card (~25 líneas por archivo)
```tsx
// Estado
const [delegadosModalOpen, setDelegadosModalOpen] = useState(false);

// Botón en rightSlotActions
<span
  role="button"
  tabIndex={0}
  onClick={(e) => { e.stopPropagation(); setDelegadosModalOpen(true); }}
  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.stopPropagation(); setDelegadosModalOpen(true); } }}
  className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border text-xs font-semibold border-border/60 hover:border-primary/40 hover:bg-primary/5 hover:text-primary cursor-pointer select-none transition-colors"
>
  <Users className="h-3 w-3" />
  Delegados
</span>

// Modal al final del JSX
<GestionarDelegadosModal
  open={delegadosModalOpen}
  onOpenChange={setDelegadosModalOpen}
  liquidacionId={lg.id}
  municipalidadId={lg.municipalidad?.id ?? ""}
  tipoLiquidacion="edificacion"
  delegadoActuales={(lg.delegados ?? []).map((d) => ({ id: d.delegado_id }))}
/>
```

### Existencia de `LiquidacionBaseCard`
`LiquidacionBaseCard.tsx` existe y provee el shell del collapsible con `LiquidacionCardHeader`. **Sin embargo**, no incluye el modal de delegados ni el estado asociado — eso se repite en cada card hija.

---

## Controllers Backend — Cadena Controller → Presenter

| Controller | Archivo | Presenter usado | ¿Usa presenter específico? |
|---|---|---|---|
| `LiquidacionGeneralController` | `liquidacion_general_controller.py` | `LiquidacionGeneralPresenter` | SÍ (general) |
| `LiquidacionEdificacionesController` | `liquidacion_especifico/liquidacion_edificaciones_controller.py` | `LiquidacionEdificacionesPresenter` | SÍ (específico) |
| `LiquidacionTaludesController` | `liquidacion_especifico/liquidacion_taludes_controller.py` | `LiquidacionTaludesPresenter` | SÍ (específico) |
| `LiquidacionHabilitacionUrbanaController` | `liquidacion_especifico/liquidacion_habilitacion_urbana_controller.py` | `LiquidacionHabilitacionUrbanaPresenter` | SÍ (específico) |
| `LiquidacionImpactoVialController` | `liquidacion_especifico/liquidacion_impacto_vial_controller.py` | `LiquidacionImpactoVialPresenter` | SÍ (específico) |
| `LiquidacionInspeccionObraController` | `liquidacion_especifico/liquidacion_inspeccion_obra_controller.py` | `LiquidacionInspeccionObraPresenter` | SÍ (específico) |
| `LiquidacionMecanicaSuelosController` | `liquidacion_especifico/liquidacion_mecanica_suelos_controller.py` | `LiquidacionMecanicaSuelosPresenter` | SÍ (específico) |

**Cadena típica**: Controller → Orchestrator → Domain Result → Presenter → Schema Output

Cada controller tiene su propio presenter específico. NO hay reutilización del presenter general para la parte `liquidacion_general` del output.

---

## Análisis de Duplicación — Tabla Consolidada

| Fragmento | Aparece en | Líneas × N | Propuesta de Extracción |
|---|---|---|---|
| Mapeo `delegados` en LiquidacionGeneralOutput | 6 presenters específicos | 22 × 6 = 132 | Extraer a `LiquidacionGeneralPresenter._map_delegados()` y llamar desde `present_primera_revision()` de cada uno, O mejor: que `LiquidacionGeneralPresenter.present_detail()` maneje esto |
| Construcción completa `LiquidacionGeneralOutput` | 6 presenters específicos | ~65 × 6 = 390 | Extraer a `LiquidacionGeneralPresenter._map_general_output()` estático y reutilizar |
| Estado `delegadosModalOpen` + `setDelegadosModalOpen` | 5 cards + LiquidacionDetalleCard | 1 × 6 = 6 | Mover a `LiquidacionBaseCard` o crear hook `useDelegadosModal(liquidacionId, municipalidadId, tipoLiquidacion)` |
| Botón "Delegados" en `rightSlotActions` | 5 cards + LiquidacionDetalleCard | ~10 × 6 = 60 | Componente `<DelegadosButton>` o integrar en `LiquidacionCardHeader` |
| `<GestionarDelegadosModal>` con props | 5 cards + LiquidacionDetalleCard | ~8 × 6 = 48 | Componente `<LiquidacionDelegadosSection>` que incluya estado + botón + modal |
| Fixture `liquidacion_*_created` | `test_edificaciones_list.py`, `test_taludes_list.py` | ~70 × 2 | Crear fixture base en `conftest.py` y especializar por tipo |

---

## Recomendación de Homogeneización

### Backend

**Qué debería ser compartido (base/helper)**:
1. `_map_general_output(general_result)` — método estático en `LiquidacionGeneralPresenter` que construye el `LiquidacionGeneralOutput` completo (sin `delegados` aún)
2. `_map_delegados(general_result)` — método estático en `LiquidacionGeneralPresenter` que mapea la lista de delegados
3. `present_detail()` en `LiquidacionGeneralPresenter` — debería populate `delegados` también (actualmente no lo hace)

**Qué debería mantenerse específico**:
- El tipo específico de `liquidacion_especifica` y `liquidacion_tipo` (varía por tipo de liquidación)
- Los métodos `present_cotizacion()`, `present_tarifas_vigentes()` que son específicos del tipo

**Cambio mínimo viable**: Modificar `LiquidacionGeneralPresenter.present_detail()` para que llame a `_map_general_output()` Y agregue el mapeo de `delegados`. Luego, los presenters específicos solo construyen el `LiquidacionGeneralOutput` usando el presenter general, y añaden solo su parte específica.

### Frontend

**Qué debería ser compartido**:
1. **Nuevo componente `LiquidacionDelegadosSection.tsx`**: Incluye estado `delegadosModalOpen`, botón "Delegados", y `<GestionarDelegadosModal>` — todo en uno.
2. **Hook `useDelegadosModal(liquidacionId, municipalidadId, tipoLiquidacion, delegadosActuales)`**: Abstrae el estado y las props.
3. **Refactorizar `LiquidacionBaseCard`**: Agregar un slot o prop `rightFooterActions` para evitar duplicar `rightSlotActions` en cada card.

**Qué debería mantenerse específico**:
- El contenido de `rightSlotActions` (los otros botones: PDF, Ver detalle)
- La estructura de cada card (cada tipo tiene fields diferentes)
- `InspeccionObraCard` — no tiene modal de delegados (usa inspectores)

---

## Validación vs Contrato

### HALLAZGO CRÍTICO: El archivo `contract/PLAN_REFACTORIZACION.md` NO existe en este proyecto.

**Búsqueda realizada**:
- `C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\contract\PLAN_REFACTORIZACION.md` → NO EXISTE
- El archivo EXISTE en `C:\Users\Usuario\Desktop\Aplicaciones\CIP\centro-de-esparcimiento\PLAN_REFACTORIZACION.md` (OTRO proyecto)

### Impacto
- No se puede realizar la validación "sección → cumple/desvía → evidencia" solicitada por el usuario.
- Se requeriría que el usuario proporcione la ruta correcta al archivo de contrato, o que este sea creado/copiado al proyecto `CAM/aplicacion`.

### Hallazgos Arquitecturales Independientes del Contrato

Even without the contract file, the code shows clear DRY violations:

1. **DRY violado**: Mismo bloque de mapeo `delegados` copiado 6 veces
2. **Single Responsibility violado**: Cada presenter específico reconstruye `LiquidacionGeneralOutput` desde cero en lugar de delegar al presenter general
3. **Código incompleto**: `LiquidacionGeneralPresenter.present_detail()` no populates `delegados` though the schema supports it

---

## Estimación

| Área | Archivos a tocar | Complejidad | Riesgo |
|---|---|---|---|
| Backend: `LiquidacionGeneralPresenter._map_delegados()` | 1 | Baja | Bajo — solo extraer código existente |
| Backend: Llamar `_map_delegados` desde presenters específicos | 6 | Baja | Bajo — cambiar llamada, no lógica |
| Backend: Tests de presenters (si se agregan) | 6+ | Media | Medio — requiere fixtures con delegados |
| Frontend: Hook `useDelegadosModal` | 1 | Baja | Bajo |
| Frontend: Componente `LiquidacionDelegadosSection` | 1 | Media | Bajo |
| Frontend: Refactorizar 5 cards para usar el hook/componente | 5 | Media | Bajo — cambio mecánico |
| Frontend: `LiquidacionBaseCard` con slot de delegados | 1 | Media | Medio — podría afectar otras cards |

**Total estimado**: 17-22 archivos, esfuerzo ~2-3 días, riesgo bajo.

---

## Risks

1. **Contrato faltante**: No se puede validar contra `PLAN_REFACTORIZACION.md` porque el archivo no existe en este proyecto. Se necesita confirmación del usuario sobre la ubicación correcta o copy del contrato.
2. **Pruebas inexistentes para delegados**: No hay tests que verifiquen el campo `delegados` en las respuestas. Si se modifica el mapeo, no hay regression suite.
3. **InspeccionObra tiene patrón diferente**: Esta card/presenter usa "inspectores" en lugar de "delegados" — cualquier extracción de patrón de delegados debe ser condicional o esta clase debe ser excluida.
4. **Acoplamiento implícito**: Los presenters específicos asumen que `general.delegados` existe con cierta estructura de campos (`d.delegado_cip`, `d.delegado_dni`, etc.). Si el domain result cambia, todos los presenters se rompen simultáneamente.

---

## Next Recommended
`sdd-propose`

La exploración confirma que la refactorización es viable y tiene bajo riesgo. Se recomienda proceder a `sdd-propose` para definir el alcance exacto del cambio, priorizando:
1. Backend: extracción del mapeo `delegados` a `LiquidacionGeneralPresenter`
2. Frontend: hook + componente para eliminar duplicación del modal en cards

---

## Skill Resolution
`paths-injected` — Recibí las rutas exactas de skills del orchestrator (`sdd-explore\SKILL.md` y `_shared\SKILL.md`).
