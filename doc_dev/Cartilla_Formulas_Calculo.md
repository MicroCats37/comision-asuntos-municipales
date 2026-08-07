# Mapeo de Fórmulas Financieras y de Cálculo por Tipo de Liquidación

Este documento sirve como referencia oficial para implementar el motor de cálculo de liquidaciones en la capa de dominio (`Flujo` y `Core`), mapeando la cartilla de requisitos y sus variables financieras.

---

## 1. Fórmulas de Cálculo por Tipo

| Tipo de Liquidación | Base de Cálculo | Fórmula de Liquidación | Derecho Mínimo (Tope) | Derecho Máximo (Tope) | ¿Aplica IGV? | ¿Aplica UIT? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Edificación** | Valor de Obra declarado | `0.15% * Valor_Obra` | `2% * UIT` | *Sin tope* | Sí | Sí |
| **Habilitación Urbana** | Área bruta de Terreno | `S/. 0.20 * Area_Terreno` | `S/. 1,000.00` (Inc. IGV) | `S/. 10,000.00` (Inc. IGV) | No (Tarifa Plana Inc. IGV) | No |
| **Mecánica de Suelos** | Área bruta de Terreno | `S/. 0.20 * Area_Terreno` | `S/. 1,000.00` (Inc. IGV) | `S/. 10,000.00` (Inc. IGV) | No (Tarifa Plana Inc. IGV) | No |
| **Impacto Vial** | Valor de Obra declarado | `0.15% * Valor_Obra` | `2% * UIT` | *Sin tope* | Sí | Sí |
| **Taludes** | Valor de Obra declarado | `0.15% * Valor_Obra` | `2% * UIT` | *Sin tope* | Sí | Sí |
| **Inspección de Obra** | Visitas por Categoría | `Costo_Por_Visita * Nro_Visitas` | *Depende de la Categoría* | *Sin tope* | Sí | Sí |

---

## 2. Detalle del Cálculo de Inspección Municipal de Obra

La tarifa por cada visita de inspección se calcula de forma dinámica en base al valor de la **UIT vigente** a la fecha de cotización/liquidación:

* **Categoría 1:** `0.032 * UIT` + IGV
* **Categoría 2:** `0.037 * UIT` + IGV
* **Categoría 3:** `0.042 * UIT` + IGV
* **Categoría 4:** `0.088 * UIT` + IGV

---

## 3. Reglas Especiales de Negocio

### A. Regla de Detracción
* **Condición:** Si el monto total calculado supera los **S/. 700.00** y el administrado solicita Factura.
* **Aplicación:** El sistema debe registrar un aviso indicando que el pago está sujeto a detracción (10% depositado en el Banco de la Nación, saldo restante en el Banco de Crédito) y otorgar 5 días hábiles para el canje de vouchers.

### B. IGV e Impuestos en Habilitación Urbana y Mecánica de Suelos
* Las tarifas de `S/. 0.20` por m2 y los topes de derecho mínimo (`S/. 1,000.00`) y derecho máximo (`S/. 10,000.00`) ya incluyen IGV en su cálculo plano. Por lo tanto, no se suma una tasa extra de impuesto en estas cotizaciones.
