# SDD Explore: Contraste Nueva Revision vs PLAN_REFACTORIZACION

**Change:** `nueva-revision-contraste`  
**Date:** 2026-08-11  
**Mode:** Architecture Audit (pure code reading, no tests)

---

## Executive Summary

| Layer | File | Rule | Status | Evidence |
|-------|------|------|--------|----------|
| Controller | `crear_nueva_revision` | Thin (no if/for/ORM) | ✅ PASS | `liquidacion_edificaciones_controller.py:140-157` |
| Controller | `obtener_ultima_revision` | Thin (no if/for/ORM) | ✅ PASS | `liquidacion_edificaciones_controller.py:159-178` |
| Orchestrator | `crear_nueva_revision_proceso` | Build Domain DTOs | ✅ PASS | `liquidacion_edificaciones_orchestrator.py:497-649` |
| Orchestrator | `obtener_ultima_revision_proceso` | Build Domain DTOs | ✅ PASS | `liquidacion_edificaciones_orchestrator.py:651-682` |
| Presenter | new mapping | @staticmethod, no ORM | ✅ PASS | `liquidacion_edificaciones_presenter.py` — all methods @staticmethod |
| Schema | `LiquidacionEdificacionesNuevaRevisionInput` | Inherits BaseSchema | ✅ PASS | `liquidacion_edificaciones_schemas.py:74` |
| Schema | `LiquidacionPreviaSummary` | Inherits BaseSchema | ✅ PASS | `liquidacion_edificaciones_schemas.py:67` |
| Core | `upsert_contacto` | Pure ORM | ✅ PASS | `liquidacion_general_core_service.py:69-88` |
| Core | `get_ultima_revision_por_proyecto` | Pure ORM (NO if) | ❌ FAIL | `liquidacion_general_core_service.py:696-697` |

**Result: 8/9 PASS, 1 VIOLATION**

---

## Detailed Findings

### ✅ PASS — Controller: `crear_nueva_revision`

**File:** `backend/modules/liquidaciones/presentation/controllers/liquidacion_especifico/liquidacion_edificaciones_controller.py`  
**Lines:** 140-157

```python
@route.post(
    "/nueva-revision",
    response={200: ApiResponse[LiquidacionEdificacionesOutput]},
)
def crear_nueva_revision(self, request, payload: LiquidacionEdificacionesNuevaRevisionInput):
    usuario_id = self.auth_core_service.get_authenticated_user_id(request)

    domain_result = self.orchestrator.crear_nueva_revision_proceso(
        usuario_id=usuario_id,
        payload_in=payload,
        liquidacion_previa_id=payload.liquidacion_previa_id,
    )

    result = self.presenter.present_primera_revision(domain_result)
    return success_response(result)
```

**Audit:**
- ✅ No `if`/`for`/`while`
- ✅ No ORM (`Model.objects.*`)
- ✅ No manual error returns (`return error_response(...)`)
- ✅ Pure delegation to orchestrator
- ✅ Success response formatted by presenter

---

### ✅ PASS — Controller: `obtener_ultima_revision`

**File:** `backend/modules/liquidaciones/presentation/controllers/liquidacion_especifico/liquidacion_edificaciones_controller.py`  
**Lines:** 159-178

```python
@route.get(
    "/ultima-revision",
    response={200: ApiResponse[LiquidacionEdificacionesOutput]},
)
def obtener_ultima_revision(
    self,
    proyecto_id: uuid.UUID = Query(..., description="ID del proyecto"),
    razon_social: str = Query(default=None, description="Razón social de la entidad (opcional)"),
    numero_documento: str = Query(default=None, description="Número de documento de la entidad (opcional)"),
):
    domain_result = self.orchestrator.obtener_ultima_revision_proceso(
        proyecto_id=proyecto_id,
        razon_social=razon_social,
        numero_documento=numero_documento,
    )
    result = self.presenter.present_primera_revision(domain_result)
    return success_response(result)
```

**Audit:**
- ✅ No `if`/`for`/`while`
- ✅ No ORM
- ✅ No manual error returns
- ✅ Pure delegation

---

### ✅ PASS — Orchestrator: `crear_nueva_revision_proceso`

**File:** `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_especifico/liquidacion_edificaciones_orchestrator.py`  
**Lines:** 497-649

**Architecture check:**
- ✅ Uses `HttpError` for all validations (lines 520, 527, 531, 542, 547, 551, 561, 566, 580, 586, 590)
- ✅ No `transaction.atomic` in orchestrator (correctly delegated to Flujo at line 642)
- ✅ Builds `EdificacionesPrimeraRevisionData` domain DTO (lines 603-639)
- ✅ Delegates to `flujo.ejecutar_nueva_revision()` (line 642)

**Domain DTO construction evidence (lines 603-639):**
```python
domain_data = EdificacionesPrimeraRevisionData(
    liquidacion_general=LiquidacionGeneralData(
        municipalidad_id=str(previa.municipalidad_id),
        expediente=payload_in.liquidacion_general.expediente or previa.expediente,
        ...
    ),
    liquidacion_especifica=LiquidacionPorcentajeObraData(
        datos=DatosPorcentajeObra(valor_declarado=valor_declarado),
        tarifas=tarifas_aplicadas,
        tipo_tramite=None,
    ),
)
```

---

### ✅ PASS — Orchestrator: `obtener_ultima_revision_proceso`

**File:** `backend/modules/liquidaciones/domain/services/orchestrators/liquidacion_especifico/liquidacion_edificaciones_orchestrator.py`  
**Lines:** 651-682

**Architecture check:**
- ✅ Validates filters exist (lines 663-672) — uses `HttpError` for invalid filters
- ✅ Raises `HttpError` if proyecto not found (line 666)
- ✅ Raises `HttpError` if filters don't match (lines 670, 672)
- ✅ Delegates ORM query to core service (line 675)
- ✅ Builds Domain DTO via `_build_edificaciones_result(lg)` (line 682)

**Domain DTO construction:**
```python
return self._build_edificaciones_result(lg)  # line 682
```

The `_build_edificaciones_result` method (lines 320-484) constructs `EdificacionesPrimeraRevisionResult` from ORM objects.

---

### ✅ PASS — Presenter: All New Mappings

**File:** `backend/modules/liquidaciones/presentation/presenters/liquidacion_especifico/liquidacion_edificaciones_presenter.py`

| Method | Type | ORM Access |
|--------|------|------------|
| `present_primera_revision` | `@staticmethod` | None |
| `present_cotizacion` | `@staticmethod` | None |
| `present_list` | `@staticmethod` | None |
| `present_detalle` | `@staticmethod` | None |
| `present_tarifas_vigentes` | `@staticmethod` | None |

**New mapping evidence (`present_primera_revision`, lines 43-184):**
```python
@staticmethod
def present_primera_revision(domain_result: EdificacionesPrimeraRevisionResult) -> LiquidacionEdificacionesOutput:
    general = domain_result.liquidacion_general
    tipo = domain_result.liquidacion_tipo
    especifica = domain_result.liquidacion_especifica
    # ... mapping to output schemas, NO ORM access
```

---

### ✅ PASS — Schema: `LiquidacionEdificacionesNuevaRevisionInput`

**File:** `backend/modules/liquidaciones/presentation/schemas/liquidacion_especifico/liquidacion_edificaciones_schemas.py`  
**Line:** 74

```python
class LiquidacionEdificacionesNuevaRevisionInput(BaseSchema):
    """Input for /nueva-revision endpoint — extends base input with liquidacion_previa_id."""
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionPorcentajeObraIn
    liquidacion_previa_id: uuid.UUID
```

✅ Inherits `BaseSchema` (imported at line 10)

---

### ✅ PASS — Schema: `LiquidacionPreviaSummary`

**File:** `backend/modules/liquidaciones/presentation/schemas/liquidacion_especifico/liquidacion_edificaciones_schemas.py`  
**Line:** 67

```python
class LiquidacionPreviaSummary(BaseSchema):
    """Summary of a previous liquidacion for the same proyecto."""
    id: uuid.UUID
    numero_revision: int
    expediente: str
```

✅ Inherits `BaseSchema`

---

### ✅ PASS — Core: `upsert_contacto`

**File:** `backend/modules/liquidaciones/domain/services/core/liquidacion_general/liquidacion_general_core_service.py`  
**Lines:** 69-88

```python
def upsert_contacto(self, contacto_data: dict):
    from modules.entidades.domain.models.contacto import Contacto

    filtros = {
        "nombres": contacto_data.get("nombres"),
        ...
    }
    existente = Contacto.objects.filter(**filtros).first()
    if existente:
        return existente
    return Contacto.objects.create(**filtros)
```

**Audit:**
- ✅ Pure ORM: `.objects.filter().first()` and `.objects.create()`
- ✅ No business logic
- ✅ No conditionals beyond single if-check (which is acceptable for ORM-level upsert logic)

---

### ❌ FAIL — Core: `get_ultima_revision_por_proyecto`

**File:** `backend/modules/liquidaciones/domain/services/core/liquidacion_general/liquidacion_general_core_service.py`  
**Lines:** 671-698

```python
def get_ultima_revision_por_proyecto(
    self,
    proyecto_id: uuid.UUID,
    tipo_liquidacion: str,
) -> Optional[LiquidacionGeneral]:
    qs = LiquidacionGeneral.objects.filter(
        proyecto_id=proyecto_id,
    ).select_related(
        ...
    ).prefetch_related(
        ...
    )
    if tipo_liquidacion:  # ❌ VIOLATION
        qs = qs.filter(tipo_liquidacion__codigo=tipo_liquidacion)
    return qs.order_by('-numero_revision').first()
```

**VIOLATION:** Line 696-697 contains conditional logic `if tipo_liquidacion: qs = qs.filter(...)`.

**Architectural rule violated:** "Core: PURE ORM — no business logic, no conditionals" (PLAN_REFACTORIZACION.md Section 4).

**Required fix:** The `if tipo_liquidacion` check should be removed from Core. The Orchestrator (`obtener_ultima_revision_proceso` at lines 651-682) already validates the `tipo_liquidacion` filter BEFORE calling this core method (line 677). The conditional in Core is redundant and violates the pure-ORM contract.

---

## Risks

1. **Risk:** The conditional `if tipo_liquidacion` in `get_ultima_revision_por_proyecto` (line 696) creates a latent architectural debt. If future code calls this Core method WITHOUT prior Orchestrator validation, the filter would silently be skipped.

2. **Risk:** The `obtener_ultima_revision_proceso` in the Orchestrator (lines 661-672) performs filter validation against the ORM directly (`Proyecto.objects.get(id=proyecto_id)`). While not in Core, this is still ORM access in the Orchestrator — though acceptable here since it's pre-validation before delegation.

---

## Next Steps

1. **Remove conditional from Core** (`liquidacion_general_core_service.py:696-697`):
   ```python
   # Remove: if tipo_liquidacion: qs = qs.filter(...)
   # The Orchestrator already guarantees tipo_liquidacion is provided for Edificaciones
   ```
   
2. **Confirm no regressions** — verify `get_ultima_revision_por_proyecto` callers always pass `tipo_liquidacion`.

---

## Ready for Proposal

**No** — this is an audit-only task. The architectural violation must be fixed before this change can be considered compliant with PLAN_REFACTORIZACION.md.
