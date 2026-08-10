# Tarifas y Derechos Históricos — Contrato y Endpoints

## Relación de Modelos

```
TarifaLiquidacionBase (VigenciaModel: periodo_inicio, periodo_fin)
  ├── TarifaPorMetroCuadrado (OneToOne) → costo_por_m2
  ├── TarifaPorCategoriaVisitas (OneToOne) → porcentaje_uit, categoria
  └── TarifaPorcentajeObra (FK) → especialidad, porcentaje_liquidacion

DerechoPorcentajeObra (VigenciaModel) → derecho_minimo, derecho_maximo, porcentaje_minimo_uit
DerechoPorMetroCuadrado (VigenciaModel) → derecho_minimo, derecho_maximo
```

## Endpoints a Construir

### 1. GET /liquidaciones/{tipo}/tarifas/historicas
**Query params:** `fecha_desde`, `fecha_hasta`, `page`, `page_size`
**Response:** Lista de períodos con tarifas agrupadas por especialidad

### 2. GET /liquidaciones/derechos/historicos
**Query params:** `tipo` (PORCENTAJE|METRO_CUADRADO), `fecha_desde`, `fecha_hasta`
**Response:** Lista de derechos con sus períodos de vigencia

### 3. GET /liquidaciones/{tipo}/tarifas/vigentes (ya existe, no modificar)

## Arquitectura (según PLAN_REFACTORIZACION.md)
- Controller: solo delega, cero if/for
- Orchestrator: construye Domain DTOs
- Presenter: @staticmethod, mapea Result→Schema, sin ORM
- Schemas: heredan BaseSchema
