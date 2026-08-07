# Skill / Guía de Desarrollo: Modelado de Formularios y Liquidaciones

Esta guía define las reglas de negocio, la estructura de base de datos y las relaciones necesarias para modelar cualquier tipo de liquidación en el sistema. Debe servir como referencia obligatoria al implementar nuevos formularios de liquidación.

---

## 1. La Relación de Tablas por Liquidación (Estructura de 3 Tablas)

A excepción de Edificaciones, cada liquidación y tipo de cálculo se define estrictamente mediante **3 tablas**:

```
                  ┌──────────────────────┐
                  │  LiquidacionGeneral  │
                  └──────────┬───────────┘
                             │ (1:1 OneToOneField)
                             ▼
              ┌──────────────────────────────┐
              │ LiquidacionHabilitacionUrbana │ (Tabla de Tipo / Extensión)
              └──────────────┬───────────────┘
                             │ (1:1 OneToOneField)
                             ▼
              ┌──────────────────────────────┐
              │ LiquidacionPorMetroCuadrado  │ (Tabla de Cálculo / Valores)
              └──────────────────────────────┘
```

1. **Tabla Cabecera (`LiquidacionGeneral`):**
   * Almacena datos comunes de auditoría, estado, fecha, expediente, municipalidad, y totales del cobro (`sub_total`, `total`).
2. **Tabla de Tipo / Extensión (e.g., `LiquidacionHabilitacionUrbana`):**
   * Hereda de `BaseModel` y `AutoNumeroModel`.
   * Contiene una relación `OneToOneField` hacia `LiquidacionGeneral` (con `related_name="habilitacion_urbana"`).
   * Sirve para asignar el número secuencial (correlativo por municipalidad/tipo) y asociar datos propios del trámite.
3. **Tabla de Cálculo / Valores (e.g., `LiquidacionPorMetroCuadrado`, `LiquidacionPorCategoriaVisitas`, `LiquidacionPorcentajeObra`):**
   * Contiene una relación `OneToOneField` hacia `LiquidacionGeneral` (con `related_name="liquidacion_m2"`, `"liquidacion_visitas"`, o `"liquidacion_porcentaje_obra"`).
   * Guarda los datos específicos del cálculo (`area_m2`, `costo_por_m2`, `cantidad_visitas`, `valor_declarado`).
   * Guarda FKs hacia la tarifa aplicada (`TarifaPorMetroCuadrado` o `TarifaPorCategoriaVisitas`) y el derecho aplicado (`Derecho`, `DerechoPorcentajeObra`, etc.).

---

## 2. La Regla de las Tablas de Configuración (Tarifas y Derechos)

Tanto para metro cuadrado como para visitas o porcentual de obra, el cálculo financiero requiere:

* **Tarifa:** Define el precio unitario o el porcentaje (`costo_por_m2`, `costo_por_visita` o `porcentaje_liquidacion`). Está asociada a `TarifaLiquidacionBase` (que maneja las fechas de vigencia y el tipo de liquidación).
* **Derecho (Tope / Clamps):** Define el costo mínimo absoluto (`minimo` / `derecho_minimo`) y máximo (`maximo` / `derecho_maximo`) que restringe el cobro.

---

## 3. Ejemplo de Asociación para un Flujo de Creación

Al momento de ejecutar el guardado atómico (dentro de `@transaction.atomic` en la capa de `Flujo`):

1. **Paso 1:** Se crea `LiquidacionGeneral`.
2. **Paso 2:** Se crea `LiquidacionHabilitacionUrbana` enlazada a la general.
3. **Paso 3:** Se obtiene la `TarifaPorMetroCuadrado` vigente y el `Derecho` vigente.
4. **Paso 4:** Se calcula el monto bruto (`area * costo_m2`), se aplican los topes de `Derecho` (mínimo/máximo) y se guarda la fila en `LiquidacionPorMetroCuadrado`, asociándole las FKs de `tarifa_aplicada` y `derecho_aplicado` (o `derecho`).
