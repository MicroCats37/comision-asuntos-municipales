# Exploration: liquidaciones-query-filters (v3 — Rápido para Apply)

## Controllers (6 endpoints GET listado)

| Controller | Archivo | Ruta | Método | Cómo llama al orquestador |
|---|---|---|---|---|
| LiquidacionEdificacionesController | `liquidacion_especifico/liquidacion_edificaciones_controller.py` | `GET /liquidaciones/edificaciones/` | `list_liquidaciones(page=1, page_size=10)` | `self.orchestrator.listar_liquidaciones(page=page, page_size=page_size)` |
| LiquidacionTaludesController | `liquidacion_especifico/liquidacion_taludes_controller.py` | `GET /liquidaciones/taludes/` | `listar_liquidaciones(request, page=1, page_size=10)` | `self.orchestrator.listar_liquidaciones(page=page, page_size=page_size)` |
| LiquidacionHabilitacionUrbanaController | `liquidacion_especifico/liquidacion_habilitacion_urbana_controller.py` | `GET /liquidaciones/habilitacion-urbana/` | `list_liquidaciones(page=1, page_size=10)` | `self.cotizar_orchestrator.listar_liquidaciones(page=page, page_size=page_size)` |
| LiquidacionImpactoVialController | `liquidacion_especifico/liquidacion_impacto_vial_controller.py` | `GET /liquidaciones/impacto-vial/` | `listar_liquidaciones(request, page=1, page_size=10)` | `self.orchestrator.listar_liquidaciones(page=page, page_size=page_size)` |
| LiquidacionInspeccionObraController | `liquidacion_especifico/liquidacion_inspeccion_obra_controller.py` | `GET /liquidaciones/inspeccion-obra/` | `list_liquidaciones(page=1, page_size=10)` | `self.orchestrator.listar_liquidaciones(page=page, page_size=page_size)` |
| LiquidacionMecanicaSuelosController | `liquidacion_especifico/liquidacion_mecanica_suelos_controller.py` | `GET /liquidaciones/mecanica-suelos/` | `list_liquidaciones(page=1, page_size=10)` | `self.cotizar_orchestrator.listar_liquidaciones(page=page, page_size=page_size)` |

## Firmas actuales del orquestador (listado)

```python
# EdificacionesOrchestrator, TaludesOrchestrator, ImpactoVialOrchestrator, InspeccionObraOrchestrator:
def listar_liquidaciones(self, page: int, page_size: int) -> tuple[List[XxxPrimeraRevisionResult], int]

# HabilitacionUrbanaOrchestrator, MecanicaSuelosOrchestrator:
def listar_liquidaciones(self, page: int, page_size: int) -> tuple[List[XxxPrimeraRevisionResult], int]
```

## Core service (donde se aplica el filtrado — 6 métodos)

```python
# LiquidacionGeneralCoreService:
def list_liquidaciones_by_type_paginated(self, tipo_liquidacion: str, page: int, page_size: int) -> tuple
def list_liquidaciones_hu_paginated(self, page: int, page_size: int) -> tuple
def list_liquidaciones_ms_paginated(self, page: int, page_size: int) -> tuple
def list_liquidaciones_taludes_paginated(self, page: int, page_size: int) -> tuple
def list_liquidaciones_io_paginated(self, page: int, page_size: int) -> tuple
def list_liquidaciones_iv_paginated(self, page: int, page_size: int) -> tuple
```

## Campos exactos por filtro

| Filtro | Campo en modelo | Ruta Django ORM | Tipo match | Notas |
|---|---|---|---|---|
| **entidad** | `LiquidacionGeneral.municipalidad_id` | `municipalidad_id` | exact (UUID) | FK directo; join ya en `select_related('municipalidad')` |
| **propietario** | `Proyecto.nombre_propietario` | `proyecto__nombre_propietario__icontains` | icontains | Join ya en `select_related('proyecto')` |
| **fecha_desde** | `LiquidacionGeneral.fecha_registro` | `fecha_registro__date__gte` | gte | DateTimeField con auto_now_add |
| **fecha_hasta** | `LiquidacionGeneral.fecha_registro` | `fecha_registro__date__lte` | lte | |
| **numero** | `{tipo}.numero` (AutoNumeroModel) | `edificaciones__numero`, `taludes__numero`, `habilitacion_urbana__numero`, `impacto_vial__numero`, `inspeccion_obra__numero`, `mecanica_suelos__numero` | exact | JOIN ya en `prefetch_related` del tipo específico |
| **razon_social** | `Proyecto.entidad_razon_social` | `proyecto__entidad_razon_social__icontains` | icontains | Snapshot denormalizado en Proyecto; join ya en `select_related('proyecto__entidad')` |
| **creado_por / usuario** | `LiquidacionGeneral.usuario_creador` → User | `usuario_creador__id` (exact) o `usuario_creador__username__icontains` | exact/icontains | FK directo; join ya en `select_related('usuario_creador')` |
| **numero_revisiones** | `LiquidacionGeneral.numero_revision` | `numero_revision__gte`, `numero_revision__exact` | gte/exact | PositiveIntegerField; no requiere join |

## Listado general

**NO existe** endpoint `GET /liquidaciones/` general. Solo los 6 endpoints por tipo.

## Convenciones Ninja

```python
# Controller actual (Ninja Query):
page: int = Query(default=1, ge=1)
page_size: int = Query(default=10, ge=1, le=100)

# Schema de referencia (tarifas_historicas_schemas.py):
class TarifasHistoricasQueryParams(BaseSchema):
    fecha_desde: date = Field(..., description="Start date for the historical range")
    fecha_hasta: date = Field(..., description="End date for the historical range")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
```

## Aplicación del filtrado (contrato §1.A)

**Controller** → parsea query params → pasa kwargs al orquestador → formatea salida.
**Orchestrator** → recibe kwargs → los pasa al core service.
**Core service** → recibe kwargs → encadena `.filter()` al QuerySet ANTES de offset/limit.

Patrón de改动 en core service (ejemplo para `list_liquidaciones_by_type_paginated`):

```python
def list_liquidaciones_by_type_paginated(
    self, tipo_liquidacion: str, page: int, page_size: int,
    municipalidad_id=None, propietario=None, razon_social=None,
    creador_username=None, fecha_desde=None, fecha_hasta=None,
    numero=None, numero_revision=None, **kwargs
) -> tuple:
    qs = LiquidacionGeneral.objects.filter(tipo_liquidacion__codigo=tipo_liquidacion)

    if municipalidad_id:
        qs = qs.filter(municipalidad_id=municipalidad_id)
    if propietario:
        qs = qs.filter(proyecto__nombre_propietario__icontains=propietario)
    if razon_social:
        qs = qs.filter(proyecto__entidad_razon_social__icontains=razon_social)
    if creador_username:
        qs = qs.filter(usuario_creador__username__icontains=creador_username)
    if fecha_desde:
        qs = qs.filter(fecha_registro__date__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_registro__date__lte=fecha_hasta)
    if numero_revision is not None:
        qs = qs.filter(numero_revision=numero_revision)

    # ... select_related + prefetch_related + order_by + offset/limit ...
```

**Para `numero`** (tipo-específico), cada método de core service sabe su tipo → filtra sobre el JOIN correcto:
- `list_liquidaciones_by_type_paginated` → `filter(edificaciones__numero=numero)`
- `list_liquidaciones_taludes_paginated` → `filter(taludes__numero=numero)`
- `list_liquidaciones_hu_paginated` → `filter(habilitacion_urbana__numero=numero)`
- `list_liquidaciones_iv_paginated` → `filter(impacto_vial__numero=numero)`
- `list_liquidaciones_io_paginated` → `filter(inspeccion_obra__numero=numero)`
- `list_liquidaciones_ms_paginated` → `filter(mecanica_suelos__numero=numero)`

## Join existente para filtros core (no se agregan nuevos)

`select_related`: `proyecto`, `proyecto__entidad`, `municipalidad`, `usuario_creador`, `tipo_liquidacion`
`prefetch_related` por tipo: `{edificaciones|taludes|habilitacion_urbana|impacto_vial|inspeccion_obra|mecanica_suelos}`

---

*Documento: v3 — 2026-08-11 — Rápido para apply*
