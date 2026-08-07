# Guía de Arquitectura de Wrappers y Abstracción de Liquidaciones

Esta guía define la estructura genérica y específica para el desarrollo del módulo de liquidaciones. Su objetivo es garantizar el desacoplamiento entre las cabeceras genéricas y las especialidades específicas, estructuradas de forma limpia en un único archivo controlador por especialidad.

---

## 1. Estructura de Abstracciones Físicas (Carpetas)

El código se organiza dividiendo lo genérico de lo específico:

```
aplicacion/backend/modules/liquidaciones/
│
├── domain/
│   ├── results/
│   │   ├── calculo.py             <-- DTOs genéricos de cálculo (M2, Visitas, Obra)
│   │   └── liquidacion.py         <-- DTOs genéricos de cabecera (LiquidacionGeneral)
│   │
│   └── services/
│       ├── core/
│       │   ├── liquidacion_core_service.py   <-- Core Genérico (crea LiquidacionGeneral)
│       │   └── tarifa_core_service.py        <-- Core Genérico (busca tarifas vigentes)
│       │
│       └── flujos/
│           └── liquidacion_flujo.py          <-- Flujo Genérico (creación atómica base)
│
├── presentation/
│   ├── controllers/
│   │   └── liquidacion_hu_controller.py      <-- ÚNICO controlador para HU (reúne sus 3 endpoints)
│   │
│   ├── presenters/
│   │   └── liquidacion_hu_presenter.py       <-- ÚNICO presentador para HU
│   │
│   └── schemas/
│       ├── shared.py                         <-- Schemas/Wrappers Ninja compartidos
│       └── liquidacion_hu_schemas.py         <-- Schemas Ninja de entrada/salida para HU
```

---

## 2. Abstracciones en Capas Genéricas

### Core Genérico (`domain/services/core/`)
Las clases Core a nivel base no contienen lógica de especialidades (como Habilitación Urbana). Solo implementan la creación de la cabecera genérica y los 3 cálculos base:
* `create_liquidacion_general()`
* `create_liquidacion_por_metro_cuadrado()`
* `create_liquidacion_por_categoria_visitas()`
* `create_liquidacion_porcentaje_obra()`

### Flujo Genérico (`domain/services/flujos/`)
Implementa las transacciones atómicas reutilizando el core genérico. Recibe un parámetro identificador de la especialidad (por ejemplo, `TipoLiquidacion.HABILITACION_URBANA`).

---

## 3. Capas Específicas Unificadas (Habilitación Urbana)

Para evitar una proliferación innecesaria de archivos en la capa de presentación, todos los endpoints, esquemas y presenters correspondientes a **Habilitación Urbana** se consolidan en archivos únicos por rol:

### A. Único Controlador HTTP (`presentation/controllers/liquidacion_hu_controller.py`)
Agrupa los 3 endpoints relacionados de Habilitación Urbana de forma limpia y ordenada:

```python
@api_controller("/liquidaciones/habilitacion-urbana", tags=["Habilitación Urbana"], permissions=[AllowAny])
class LiquidacionHabilitacionUrbanaController:
    
    @route.get("/tarifas/vigentes", response={200: ApiResponse[TarifasVigentesOutputSchema]})
    def get_tarifas_vigentes(self):
        # 1. Obtiene tarifas vigentes
        ...
        
    @route.post("/cotizar", response={200: ApiResponse[CotizarOutputSchema]})
    async def cotizar(self, payload: CotizarInputSchema):
        # 2. Cotiza cálculo M2
        ...
        
    @route.post("/primera-revision", response={200: ApiResponse[PrimeraRevisionOutputSchema]})
    async def crear_primera_revision(self, payload: PrimeraRevisionInputSchema):
        # 3. Crea la liquidación completa
        ...
```

### B. Único Presenter (`presentation/presenters/liquidacion_hu_presenter.py`)
Agrupa los métodos estáticos de mapeo para las 3 respuestas Ninja:
* `@staticmethod present_tarifas_vigentes(...)`
* `@staticmethod present_cotizacion(...)`
* `@staticmethod present_primera_revision(...)`
