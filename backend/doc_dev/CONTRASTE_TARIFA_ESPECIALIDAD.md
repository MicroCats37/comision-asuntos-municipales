# Contraste: Tarifas ↔ Especialidades (Alpha con Reglas vs Actual con FK)

## Propósito

Documenta cómo la **versión alpha** relacionaba las tarifas con las especialidades mediante **reglas**, en contraste con la versión actual que usa un **FK directo**. Sirve como base para la decisión de separar `Especialidad` en `EspecialidadIngeniero` (perfil del ingeniero) vs `Especialidad` (catálogo de cálculo).

## 1. Enfoque ALPHA (basado en REGLAS + M2M)

Ubicación: `C:\Users\Usuario\AppData\Local\Temp\opencode\cam-alpha\`

### 1.1 `TarifaLiquidacionBase` → ManyToMany a Especialidad

Cada tarifa base puede aplicar a **varias especialidades** del catálogo:

```python
# alpha/backend/modules/liquidaciones/domain/models/liquidacion/liquidacion.py (líneas 331-336)
class TarifaLiquidacionBase(models.Model):
    ...
    especialidades = models.ManyToManyField("Especialidad", ...)
```

**Consecuencia**: si varias especialidades comparten el mismo porcentaje, se usa UNA sola `TarifaLiquidacionBase` con su M2M — no se duplica el registro.

### 1.2 Tres modelos de Regla para resolver qué tarifa aplica

| Regla | Tipo de liquidación | Clave de resolución | Resultado |
|-------|--------------------|--------------------|-----------|
| `ReglaTarifaEdificacion` | Edificación | `tipo_tramite + tramite_accion` | `tarifa_base` |
| `ReglaTarifaLiquidacion` | HU, MS, IV, Taludes | `tramite_accion` | `tarifa_base` |
| `ReglaTarifaInspeccionObra` | Inspección de Obra | `categoria + tramite_accion` | `tarifa_base` |

Las reglas viven en modelos dedicados (`alpha/.../tarifas_reglas.py`), no en la FK.

### 1.3 `EspecialidadesLiquidacion` — validación por período

Modelo separado que define **qué especialidades del catálogo están habilitadas por tipo de liquidación y período**. Es validación, no el vínculo tarifa→especialidad.

## 2. Enfoque ACTUAL (FK directo)

Ubicación: `C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\`

### 2.1 `TarifaPorcentajeObra` → FK directo a Especialidad

Cada tarifa queda ligada a **UNA sola especialidad**:

```python
# aplicacion/backend/modules/liquidaciones/domain/models/liquidacion/liquidacion_tipo/tarifas_reglas.py (líneas 149-155)
class TarifaPorcentajeObra(models.Model):
    ...
    especialidad = models.ForeignKey("usuarios.Especialidad", ...)
```

**Consecuencia**: si varias especialidades comparten el mismo %, se necesitan N registros `TarifaPorcentajeObra` (uno por especialidad).

### 2.2 `LiquidacionEspecialidadDisponibles` — puente tipo ↔ especialidad

Modelo que relaciona `TipoLiquidacion ↔ Especialidad` (qué especialidades están disponibles por tipo de liquidación). Cumple un rol similar a `EspecialidadesLiquidacion` de alpha.

## 3. Comparación directa

| Aspecto | Alpha (Reglas + M2M) | Actual (FK directo) |
|---------|---------------------|---------------------|
| Tarifa → Especialidad | M2M en `TarifaLiquidacionBase` | FK en `TarifaPorcentajeObra` |
| Resolución de tarifa | Modelos `ReglaTarifa*` | FK implícito |
| Mismo % para varias especialidades | 1 TarifaBase + M2M | N registros TarifaPorcentajeObra |
| Reglas de negocio | En modelos dedicados | Implícitas en la FK |
| Validación por período | `EspecialidadesLiquidacion` | `LiquidacionEspecialidadDisponibles` |

## 4. Por qué importa para el split de Especialidad

El usuario quiere separar `Especialidad` en dos conceptos:
- `EspecialidadIngeniero` — la especialidad profesional del ingeniero (del CIP)
- `Especialidad` — el catálogo de especialidades para cálculo/tarifas

**Con el enfoque de alpha (M2M + Reglas):**
- La tarifa referencia el **catálogo `Especialidad`**, no la relación con el ingeniero
- `EspecialidadIngeniero` queda completamente **separada** del cálculo
- Las reglas de negocio viven en modelos dedicados, no en la FK
- El split NO afecta la resolución de tarifas

**Con el enfoque actual (FK directo):**
- El FK de `TarifaPorcentajeObra` apunta a `usuarios.Especialidad` (modelo a dividir)
- El split obligaría a repuntar el FK hacia el catálogo `Especialidad`
- Mayor acoplamiento entre tarifa y catálogo

## 5. Recomendación

Adoptar el enfoque de **alpha: M2M + modelos de Regla**. Ventajas para el split:
1. Las tarifas referencian solo el catálogo `Especialidad`
2. `EspecialidadIngeniero` se llena desde el CIP (código + capítulo) sin tocar el cálculo
3. Las reglas de negocio quedan centralizadas y testables

## 6. Archivos afectados

| Versión | Archivo | Cambio |
|---------|---------|--------|
| Alpha | `backend/modules/liquidaciones/domain/models/liquidacion/liquidacion.py` | `TarifaLiquidacionBase.especialidades` (M2M), `EspecialidadesLiquidacion` |
| Alpha | `backend/modules/liquidaciones/domain/models/liquidacion/tarifas_reglas.py` | Modelos `ReglaTarifa*` |
| Alpha | `backend/modules/liquidaciones/domain/models/especialidades.py` | Catálogo `Especialidad` |
| Actual | `backend/modules/liquidaciones/domain/models/liquidacion/liquidacion_tipo/tarifas_reglas.py` | `TarifaPorcentajeObra.especialidad` (FK a cambiar) |
| Actual | `backend/modules/liquidaciones/domain/models/liquidacion/liquidacion_general/liquidacion.py` | `LiquidacionEspecialidadDisponibles` |
| Actual | `backend/modules/usuarios/domain/models/perfil_ingeniero.py` | `Especialidad` (modelo a dividir) |
