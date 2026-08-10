# Exploración: Variables Financieras y Vigencia

## 1. Análisis de Herencia de Vigencia (Database)
El usuario sospechaba que faltaba aplicar el componente abstracto de vigencia. 

**Resultado de la Auditoría:** FALSO. La herencia está correctamente aplicada.
- `backend/modules/finanzas/domain/models/igv.py`: `class IGV(VigenciaModel)` ✅
- `backend/modules/finanzas/domain/models/uit.py`: `class UIT(VigenciaModel)` ✅
- `backend/modules/liquidaciones/domain/models/tarifas/tarifa_liquidacion_base.py`: `class TarifaLiquidacionBase(VigenciaModel)` ✅
- `backend/modules/liquidaciones/domain/models/derechos/...`: `class DerechoPorMetroCuadrado(VigenciaModel)` ✅

Todo el sistema soporta historial de fechas (`periodo_inicio` y `periodo_fin`).

## 2. Diagnóstico del Controlador de Finanzas
Endpoint: `GET /api/finanzas/variables/vigentes`

**Problema Actual:**
El orquestador (`FinanzasOrchestrator`) está puenteado/roto:
```python
def obtener_variables_vigentes(self):
    # TODO: rebuild FinanzasOrchestrator
    return {"igv": None, "uit": None, "message": "FinanzasOrchestrator pendiente de reconstruir"}
```

**Conflicto de Contrato:**
El schema de salida en el frontend y backend exige datos reales, por lo que devolver `None` rompe las expectativas de la UI (causando crashes en el formulario de cotización cuando intenta calcular impuestos).

## 3. Propuesta de Solución (Contrato y Presentador)

1. **Reactivar Orquestador:** Usar el ORM para traer los valores vigentes (los mismos que usa `LiquidacionGeneralCoreService` actualmente: `IGV.objects.filter(periodo_fin__isnull=True).last()`).
2. **Presentador Recomendado:** Crear `FinanzasPresenter.present_variables_vigentes(igv, uit)`. Debe mapear los modelos del ORM hacia la clase `VariablesFinancierasOut`.
3. **Contrato de Salida:**
```python
class VariableFinancieraData(BaseSchema):
    id: uuid.UUID
    valor: float
    periodo_inicio: date
    # ... metadata adicional

class VariablesFinancierasOut(BaseSchema):
    igv: VariableFinancieraData
    uit: VariableFinancieraData
```