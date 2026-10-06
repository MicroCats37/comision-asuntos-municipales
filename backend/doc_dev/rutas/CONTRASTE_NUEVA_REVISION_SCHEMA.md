# Contraste: Nueva Revision Schema Reducido — Verificación Arquitectónica

**Fecha:** 2026-08-11  
**Proyecto:** aplicacion  
**Change:** `nueva-revision-schema-reducido-contraste`  
**Artifact Store:** engram

---

## 1. Hallazgo: Schemas de Entrada — ✅ CONFORMIDAD VERIFICADA

### Archivos Inspeccionados
- `backend/modules/liquidaciones/presentation/schemas/liquidacion_especifico/liquidacion_edificaciones_schemas.py:70-94`

### Schema: `LiquidacionGeneralNuevaRevisionIn`
```python
class LiquidacionGeneralNuevaRevisionIn(BaseSchema):  # ✅ hereda BaseSchema
```
- Campos: `expediente`, `observacion`, `retencion`, `contacto`
- **SIN** `municipalidad` ni `proyecto` (heredados de previa)
- Líneas 70-75

### Schema: `LiquidacionEspecificaNuevaRevisionIn`
```python
class LiquidacionEspecificaNuevaRevisionIn(BaseSchema):  # ✅ hereda BaseSchema
```
- Campo: `tarifas: List[LiquidacionPorcentajeObraTarifaIn]`
- **SIN** `datos` (heredados de previa)
- Líneas 78-83

### Schema: `LiquidacionEdificacionesNuevaRevisionInput`
```python
class LiquidacionEdificacionesNuevaRevisionInput(BaseSchema):  # ✅ hereda BaseSchema
```
- Campos: `liquidacion_previa_id: uuid.UUID`, `liquidacion_general: LiquidacionGeneralNuevaRevisionIn`, `liquidacion_especifica: LiquidacionEspecificaNuevaRevisionIn`
- Líneas 86-94

### Contraste con el Plan
| Aspecto | Plan | Implementación | Estado |
|---------|------|----------------|--------|
| Schema input hereda `BaseSchema` | Obligatorio | ✅ `BaseSchema` en los 3 schemas | PASS |
| `LiquidacionGeneralNuevaRevisionIn` sin municipalidad/proyecto | Reducido | ✅ Campos: expediente, observacion, retencion, contacto | PASS |
| `LiquidacionEspecificaNuevaRevisionIn` solo tarifas | Reducido | ✅ Campo único: `tarifas` (sin `datos`) | PASS |

---

## 2. Hallazgo: Orchestrator — ✅ HERENCIA DE `valor_declarado` CORRECTA

### Archivo Inspeccionado
- `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_especifico/liquidacion_edificaciones_orchestrator.py:499-651`

### Método: `crear_nueva_revision_proceso`

**Paso 7 (línea 566):**
```python
# Step 7: valor_declarado se HEREDA de la previa (no viene en el input de nueva revision)
valor_declarado = previa.liquidacion_porcentaje_obra.valor_declarado
if valor_declarado <= 0:
    raise HttpError(400, "valor_declarado debe ser mayor a 0")
```
✅ El `valor_declarado` se obtiene de `previa.liquidacion_porcentaje_obra.valor_declarado`, **NO** del input.

**Paso 10 (líneas 605-641):** Construcción del Domain DTO:
```python
domain_data = EdificacionesPrimeraRevisionData(
    liquidacion_general=LiquidacionGeneralData(
        municipalidad_id=str(previa.municipalidad_id),  # ✅ hereda de previa
        expediente=payload_in.liquidacion_general.expediente or previa.expediente,
        # ... proyecto completo de previa (no del input)
    ),
    liquidacion_especifica=LiquidacionPorcentajeObraData(
        datos=DatosPorcentajeObra(valor_declarado=valor_declarado),  # ✅ heredado
        tarifas=tarifas_aplicadas,
    ),
)
```

### Contraste con el Plan
| Aspecto | Plan | Implementación | Estado |
|---------|------|----------------|--------|
| Orchestrator obtiene `valor_declarado` de previa | HEREDA, no del input | ✅ `previa.liquidacion_porcentaje_obra.valor_declarado` | PASS |
| Construye Domain DTOs | Requerido | ✅ `EdificacionesPrimeraRevisionData` con `LiquidacionGeneralData` y `LiquidacionPorcentajeObraData` | PASS |
| Asignación a variable (no return gigante) | Regla D del plan | ✅ `response = await flujo_seguro(...)` → `return response` (línea 644-651) | PASS |

---

## 3. Hallazgo: Controller — ✅ THIN CONTROLLER VERIFICADO

### Archivo Inspeccionado
- `backend/modules/liquidaciones/presentation/controllers/liquidacion_especifico/liquidacion_edificaciones_controller.py:140-157`

### Endpoint: `crear_nueva_revision`

```python
@route.post(
    "/nueva-revision",
    response={200: ApiResponse[LiquidacionEdificacionesOutput]},
)
def crear_nueva_revision(self, request, payload: LiquidacionEdificacionesNuevaRevisionInput):
    """
    Crea una nueva revisión (3 o 5) para una Edificación existente.
    """
    usuario_id = self.auth_core_service.get_authenticated_user_id(request)  # ✅ auth

    domain_result = self.orchestrator.crear_nueva_revision_proceso(  # ✅ delegación pura
        usuario_id=usuario_id,
        payload_in=payload,
        liquidacion_previa_id=payload.liquidacion_previa_id,
    )

    result = self.presenter.present_primera_revision(domain_result)  # ✅ presenter
    return success_response(result)  # ✅ retorno único
```

### Verificación Anti-Patrones
| Anti-Patrón | Buscado | Encontrado |
|-------------|---------|------------|
| `if`/`for` en controller | ❌ | ✅ NO — cero lógica condicional |
| ORM directo (`Model.objects`) | ❌ | ✅ NO — solo llama orchestrator |
| `error_response` manual | ❌ | ✅ NO — excepciones delegadas al orquestador |
| Return con lógica | ❌ | ✅ NO — return único con `success_response` |

### Contraste con el Plan
| Aspecto | Plan | Implementación | Estado |
|---------|------|----------------|--------|
| Controller thin (3 acciones) | Regla A | ✅ Parseo payload → llama orchestrator → retorna success_response | PASS |
| Sin `if`/`for`/variables estado | Prohibido | ✅ Controller sin lógica | PASS |
| Sin ORM directo | Prohibido | ✅ Sin `objects.` | PASS |

---

## 4. Hallazgo: Presenter — ✅ UNCHANGED, @staticmethod

### Archivo Inspeccionado
- `backend/modules/liquidaciones/presentation/presenters/liquidacion_especifico/liquidacion_edificaciones_presenter.py:42-261`

### Clase: `LiquidacionEdificacionesPresenter`

```python
class LiquidacionEdificacionesPresenter:
    @staticmethod
    def present_primera_revision(domain_result: EdificacionesPrimeraRevisionResult) -> LiquidacionEdificacionesOutput:
        # ... mapeo Domain Result → Schema Out
        return LiquidacionEdificacionesOutput(...)

    @staticmethod
    def present_cotizacion(...) -> LiquidacionEdificacionesCotizarOutput: ...

    @staticmethod
    def present_list(...) -> PaginatedData[LiquidacionEdificacionesOutput]: ...

    @staticmethod
    def present_detalle(...) -> LiquidacionEdificacionesOutput: ...

    @staticmethod
    def present_tarifas_vigentes(tarifas) -> dict: ...
```

### Verificación de Reglas
| Regla | Verificación | Estado |
|-------|-------------|--------|
| Solo `@staticmethod` o `@classmethod` | ✅ Todos los métodos son `@staticmethod` | PASS |
| Sin acceso a base de datos | ✅ Sin `objects.` | PASS |
| Lógica mínima de formateo | ✅ Solo mapeo de campos | PASS |
| Sin lógica de negocio | ✅ Solo transformación de datos | PASS |

### Contraste con el Plan
| Aspecto | Plan | Implementación | Estado |
|---------|------|----------------|--------|
| Presenter unchanged | Homogéneo | ✅ Mismos métodos, misma estructura que `primera_revision` | PASS |
| `@staticmethod` | Regla A | ✅ Todos los métodos son `@staticmethod` | PASS |
| Sin acceso a ORM | Prohibido | ✅ Solo conoce Domain Results y Schemas | PASS |

---

## 5. Resumen de Verificación

| Componente | Regla del Plan | Estado |
|------------|---------------|--------|
| `LiquidacionGeneralNuevaRevisionIn` hereda `BaseSchema` | C. Tipado Estricto | ✅ PASS |
| `LiquidacionEspecificaNuevaRevisionIn` hereda `BaseSchema` | C. Tipado Estricto | ✅ PASS |
| `LiquidacionEdificacionesNuevaRevisionInput` hereda `BaseSchema` | C. Tipado Estricto | ✅ PASS |
| Schema reducido (sin municipalidad/proyecto/datos) | Input modificado | ✅ PASS |
| Orchestrator hereda `valor_declarado` de previa | Context | ✅ PASS |
| Orchestrator construye Domain DTOs | Flujo correcto | ✅ PASS |
| Controller thin (zero lógica) | Regla A | ✅ PASS |
| Presenter unchanged, `@staticmethod` | Regla A | ✅ PASS |

---

## 6. Artefactos SDD

| Artefacto | Modo |
|-----------|------|
| `sdd/nueva-revision-schema-reducido-contraste/explore` | engram |

---

## 7. Decisiones Detectadas

1. **Schema input reducido** — `LiquidacionEdificacionesNuevaRevisionInput` solo contiene campos editables; `municipalidad`, `proyecto`, y `valor_declarado` se heredan de la liquidación previa.
2. **Herencia de `valor_declarado`** — El orquestador extrae `valor_declarado` de `previa.liquidacion_porcentaje_obra.valor_declarado` (línea 566), no del payload de entrada.
3. **Presenter homogéneo** — `present_primera_revision` se reutiliza para nueva revisión, confirmando salida consistente.
