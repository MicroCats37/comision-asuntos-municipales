# 00 — Datos operativos de referencia

> Este documento es la base de la guía. Describe **qué datos guarda CAM**, con
> qué forma, cómo se relacionan entre sí y qué valores reales tienen hoy en la
> base de desarrollo. Los documentos [01](01-liquidaciones-flujo-operativo.md),
> [02](02-operatividad-de-inspectores-y-delegados.md) y
> [03](03-rh-mensual-y-reparto-estacional.md) consumen esta referencia.

## 0.1 Cómo se organiza el catálogo

CAM separa dos cosas que a menudo se confunden:

- **La cabecera de la liquidación**: quién Daw es, cuánto se cobra, en qué
  estado está, qué expediente tiene. Es la misma para todos los tipos.
- **El detalle por tipo de liquidación**: cómo se calculates ese monto. Cada
  tipo tiene su propio motor de cálculo y su propia tabla de detalle.

Los seis tipos registrados son:

| Modelo | Tabla física | Campo clave | Registros |
|---|---|---|---|
| `TipoLiquidacion` | `liquidaciones_tipoliquidacion` | `codigo`, `nombre` | 6 |

Códigos y nombres reales:

| Código | Nombre | Motor de cálculo |
|---|---|---|
| `EDIFICACION` | Edificacion | Porcentaje de obra |
| `HABILITACION_URBANA` | Habilitacion Urbana | Por metro cuadrado |
| `MECANICA_SUELOS` | Mecanica Suelos | Por metro cuadrado |
| `TALUDES` | Taludes | Porcentaje de obra |
| `IMPACTO_VIAL` | Impacto Vial | Porcentaje de obra |
| `INSPECCION_OBRA` | Inspeccion Obra | Por categoría de visitas |

*Datos de desarrollo consultados: 2026-11-08 17:59 (UTC−05:00)*

## 0.2 El patrón de vigencia

Casi todo el catálogo parametrizado usa el mismo par de campos:

- `periodo_inicio` — fecha desde la que el registro aplica.
- `periodo_fin` — fecha hasta la que aplica. Si es `NULL`, el registro está
  **abierto** (vigente hacia adelante).

La resolución de vigencia vive en la clase base `VigenciaModel`
(`backend/core_application/models.py`), con dos operaciones:

| Operación | Qué hace |
|---|---|
| `vigentes(fecha)` | Devuelve todos los registros donde `periodo_inicio <= fecha` y (`periodo_fin IS NULL` o `periodo_fin >= fecha`). |
| `vigente(fecha)` | Devuelve **el más reciente** de esos, ordenado por `periodo_inicio` descendente. Es la operación que usa el sistema para "la tarifa que corresponde a esta fecha". |

Consecuencia práctica: **una fecha nunca crea ni modifica catálogo**. Cambiar
de fecha cambia qué registro se resuelve, no el catálogo. Para que un cambio de
tarifa entre en vigor hay que cerrar el tramo anterior (`periodo_fin`) y abrir
uno nuevo (`periodo_inicio`).

## 0.3 Valores monetarios de referencia: UIT e IGV

| Modelo | Tabla física | Campos | Notas |
|---|---|---|---|
| `UIT` | `finanzas_uit` | `periodo_inicio`, `periodo_fin`, `valor` (entero) | Un valor por año |
| `IGV` | `finanzas_igv` | `periodo_inicio`, `periodo_fin`, `valor` (numérico, fracción) | Fracción: `0.18` = 18 % |

La UIT es el valor de referencia que multiplica porcentajes; el IGV es la
fracción que se aplica al subtotal para obtener el total.

**UIT — serie completa registrada:**

| Año | Valor | Año | Valor | Año | Valor |
|---|---|---|---|---|---|
| 2000 | 2900 | 2009 | 3550 | 2018 | 4150 |
| 2001 | 3000 | 2010 | 3600 | 2019 | 4200 |
| 2002 | 3100 | 2011 | 3600 | 2020 | 4300 |
| 2003 | 3100 | 2012 | 3650 | 2021 | 4400 |
| 2004 | 3200 | 2013 | 3700 | 2022 | 4600 |
| 2005 | 3300 | 2014 | 3800 | 2023 | 4950 |
| 2006 | 3400 | 2015 | 3850 | 2024 | 5150 |
| 2007 | 3450 | 2016 | 3950 | 2025 | 5350 |
| 2008 | 3500 | 2017 | 4050 | 2026 | 5500 |

Cada año tiene su propio tramo (`2000-01-01` a `2000-12-31`, etc.). El tramo de
2026 es `2026-01-01` con `periodo_fin` abierto.

**IGV:** un único tramo `2000-01-01` → abierto, valor `0.18`.

*Datos de desarrollo consultados: 2026-11-08 17:59 (UTC−05:00)*

## 0.4 Tarifas

### 0.4.1 Tarifa base

| Modelo | Tabla física | Campos |
|---|---|---|
| `TarifaLiquidacionBase` | `liquidaciones_tarifaliquidacionbase` | `periodo_inicio`, `periodo_fin`, `tipo_liquidacion_id` |

La tarifa base es el **ancla de vigencia**. Cada tipo de liquidación que
necesita reglas de cobro tiene uno o más tramos de tarifa base; las reglas
concretas cuelgan de esa base.

Tramos reales registrados (11 en total):

| Tipo | Tramo 1 | Tramo 2 |
|---|---|---|
| `EDIFICACION` | 2000-01-01 → 2026-04-30 | 2026-05-01 → abierto |
| `HABILITACION_URBANA` | 2000-01-01 → 2026-04-30 | 2026-05-01 → abierto |
| `MECANICA_SUELOS` | 2000-01-01 → 2026-04-30 | 2026-05-01 → abierto |
| `TALUDES` | 2000-01-01 → 2026-04-30 | 2026-05-01 → abierto |
| `IMPACTO_VIAL` | 2000-01-01 → 2026-04-30 | 2026-05-01 → abierto |
| `INSPECCION_OBRA` | 2000-01-01 → abierto | — |

*Datos de desarrollo consultados: 2026-11-08 17:59 (UTC−05:00)*

### 0.4.2 Tarifa por metro cuadrado (Habilitación Urbana y Mecánica de Suelos)

| Modelo | Tabla física | Campos |
|---|---|---|
| `TarifaPorMetroCuadrado` | `liquidaciones_tarifapormetrocuadrado` | `costo_por_m2`, `tarifa_base_id` |

| Tipo | Tramo de la base | `costo_por_m2` |
|---|---|---|
| `HABILITACION_URBANA` | 2000-01-01 → 2026-04-30 | 0.1500 |
| `HABILITACION_URBANA` | 2026-05-01 → abierto | 0.2000 |
| `MECANICA_SUELOS` | 2000-01-01 → 2026-04-30 | 0.1500 |
| `MECANICA_SUELOS` | 2026-05-01 → abierto | 0.2000 |

*Datos de desarrollo consultados: 2026-11-08 17:59 (UTC−05:00)*

### 0.4.3 Tarifa por categoría de visitas (Inspección de Obra)

| Modelo | Tabla física | Campos |
|---|---|---|
| `TarifaPorCategoriaVisitas` | `liquidaciones_tarifaporcategoriavisitas` | `categoria_visitas`, `porcentaje_uit`, `tarifa_base_id` |

Cada categoría tiene su propio porcentaje de UIT por visita. Las cuatro
categorías del tipo `INSPECCION_OBRA` cuelgan de la base abierta desde 2000:

| Categoría | `porcentaje_uit` por visita |
|---|---|
| `1` | 0.0320 |
| `2` | 0.0370 |
| `3` | 0.0420 |
| `4` | 0.0880 |

*Datos de desarrollo consultados: 2026-11-08 17:59 (UTC−05:00)*

### 0.4.4 Tarifa por porcentaje de obra (Edificación, Taludes, Impacto Vial)

| Modelo | Tabla física | Campos |
|---|---|---|
| `TarifaPorcentajeObra` | `liquidaciones_tarifaporcentajeobra` | `porcentaje_liquidacion`, `tarifa_base_id` |

El porcentaje es **unitario**: se aplica al valor declarado de la obra y se
reparte entre las especialidades participantes.

| Tipo | Tramo 2000-01-01 → 2026-04-30 | Tramo 2026-05-01 → abierto |
|---|---|---|
| `EDIFICACION` | 0.0002 | 0.0005 |
| `TALUDES` | 0.0004 | 0.0015 |
| `IMPACTO_VIAL` | 0.0004 | 0.0015 |

*Datos de desarrollo consultados: 2026-11-08 17:59 (UTC−05:00)*

## 0.5 Derechos

Los derechos son las cotas que se aplican al monto calculado. Viven en dos
modelos distintos porque cada motor de cálculo tiene su propia forma de tope.

| Modelo | Tabla física | Campos |
|---|---|---|
| `DerechoPorMetroCuadrado` | `liquidaciones_derechopormetrocuadrado` | `periodo_inicio`, `periodo_fin`, `derecho_minimo`, `derecho_maximo` |
| `DerechoPorcentajeObra` | `liquidaciones_derechoporcentajeobra` | `periodo_inicio`, `periodo_fin`, `derecho_minimo`, `derecho_maximo`, `porcentaje_minimo_uit` |

Tramos reales:

| Derecho | Tramo | Mínimo | Máximo | Nota |
|---|---|---|---|---|
| `DerechoPorMetroCuadrado` | 2000-01-01 → 2026-04-30 | 750.00 | 7500.00 | |
| `DerechoPorMetroCuadrado` | 2026-05-01 → abierto | 1000.00 | 10000.00 | Vigente |
| `DerechoPorcentajeObra` | 2000-01-01 → abierto | — | — | `porcentaje_minimo_uit` = 0.0200 |

El derecho de porcentaje de obra **no trae monto absoluto**: el mínimo se
calcula en el momento de cotizar como

```
derecho_minimo = UIT_vigente × porcentaje_minimo_uit × (1 + IGV_vigente)
```

Con la UIT 2026 (5500) y el IGV 0.18, eso da
`5500 × 0.0200 × 1.18 = 129.80`. Ese valor es el que queda congelado en cada
liquidación de Edificación (campo `derecho_minimo` de
`liquidaciones_liquidacionporcentajeobra`).

*Datos de desarrollo consultados: 2026-11-08 17:59 (UTC−05:00)*

## 0.6 Especialidades

### 0.6.1 Especialidades de revisión

| Modelo | Tabla física | Campos |
|---|---|---|
| `EspecialidadRevision` | `usuarios_especialidadrevision` | `slug`, `nombre` |

Catálogo completo (5):

| Slug | Nombre |
|---|---|
| `civil` | Ingeniería Civil |
| `ingenier-a-electr-nica` | Ingeniería Electrónica |
| `ingenier-a-el-ctrica-y-mec-nica-el-ctrica` | Ingeniería Eléctrica y Mecánica Eléctrica |
| `sanitaria` | Ingeniería Sanitaria |
| `inspeccion-obra` | Inspección de Obra |

### 0.6.2 Especialidades habilitadas por tipo de liquidación

| Modelo | Tabla física | Campos |
|---|---|---|
| `LiquidacionEspecialidadDisponibles` | `liquidaciones_liquidacionespecialidaddisponibles` | `periodo_inicio`, `periodo_fin`, `activo`, `especialidad_id`, `tipo_liquidacion_id` |

Este catálogo responde a la pregunta **"para este tipo de liquidación y en esta
fecha, qué especialidades pueden participate"**. En el motor de porcentaje de
obra, la cantidad de especialidades habilitadas es el **universo de cobro (H)**:
de él depende el reparto cuando el total declarado se distribute entre
especialidades.

Tramos registrados (8 filas):

| Tipo | Especialidad | Vigencia |
|---|---|---|
| `EDIFICACION` | Ingeniería Civil | 2000-01-01 → abierto |
| `EDIFICACION` | Ingeniería Eléctrica y Mecánica Eléctrica | 2000-01-01 → abierto |
| `EDIFICACION` | Ingeniería Sanitaria | 2000-01-01 → abierto |
| `EDIFICACION` | Ingeniería Electrónica | 2000-01-01 → 2026-05-01 |
| `HABILITACION_URBANA` | Ingeniería Civil | 2000-01-01 → abierto |
| `IMPACTO_VIAL` | Ingeniería Civil | 2000-01-01 → abierto |
| `MECANICA_SUELOS` | Ingeniería Civil | 2000-01-01 → abierto |
| `TALUDES` | Ingeniería Civil | 2000-01-01 → abierto |

Especialidades habilitadas vigentes a **2026-11-08**:

| Tipo | H (habilitadas vigentes) |
|---|---|
| `EDIFICACION` | 3 |
| `HABILITACION_URBANA` | 1 |
| `IMPACTO_VIAL` | 1 |
| `MECANICA_SUELOS` | 1 |
| `TALUDES` | 1 |

*Datos de desarrollo consultados: 2026-11-08 17:59 (UTC−05:00)*

## 0.7 Operatividad

La operatividad responde a **"quién puede hacer qué, dónde y desde cuándo"**.
Hay dos figuras y cada una tiene su propio par de modelos: una asignación
(contexto: tipo, municipalidad, especialidad, categoría) y sus **períodos de
vigencia**.

### 0.7.1 Inspectores

| Modelo | Tabla física | Campos |
|---|---|---|
| `Inspector` | `liquidaciones_inspector` | `perfil_ingeniero_id` (uno a uno con `PerfilIngeniero`) |
| `InspectorOperacion` | `liquidaciones_inspectoroperacion` | `inspector_id`, `tipo_liquidacion_id`, `especialidad_revision_id`, `categoria`, `numero_registro` |
| `InspectorOperacionPeriodo` | `liquidaciones_inspectoroperacionperiodo` | `inspector_tipo_liquidacion_id`, `periodo_inicio`, `periodo_fin` |

`InspectorOperacion` es la asignación: un inspector opera un tipo de liquidación,
para una especialidad de revisión, en una categoría. `numero_registro` se
compone automáticamente como `CAM` + CIP sin ceros + categoría, y la unicidad
está garantizada sobre `(inspector, tipo_liquidacion, numero_registro)`.

Un modelo `InspectorOperacionPeriodo` solo puede tener **un período abierto** a
la vez (restricción parcial sobre `periodo_fin IS NULL`). El helper
`close_current_and_open_new` cierra el tramo anterior con
`periodo_fin = nueva_fecha − 1 día` y abre el siguiente.

Volumen real: **220 inspectores**, **248 `InspectorOperacion`**, **283
períodos**.

Composición de la operatividad de inspectores por tipo, categoría y especialidad:

| Tipo | Categoría | Especialidad | Operaciones | Con período |
|---|---|---|---|---|
| `EDIFICACION` | 1 | Ingeniería Civil | 14 | 14 |
| `EDIFICACION` | 2 | Ingeniería Civil | 28 | 28 |
| `EDIFICACION` | 2 | Ingeniería Eléctrica y Mecánica Eléctrica | 1 | 1 |
| `EDIFICACION` | 2 | Ingeniería Electrónica | 1 | 1 |
| `EDIFICACION` | 3 | Ingeniería Civil | 85 | 85 |
| `EDIFICACION` | 3 | Ingeniería Electrónica | 1 | 1 |
| `EDIFICACION` | 3 | Ingeniería Eléctrica y Mecánica Eléctrica | 2 | 2 |
| `EDIFICACION` | 4 | Ingeniería Electrónica | 2 | 2 |
| `EDIFICACION` | 4 | Ingeniería Eléctrica y Mecánica Eléctrica | 14 | 14 |
| `EDIFICACION` | 4 | Ingeniería Sanitaria | 3 | 3 |
| `EDIFICACION` | 4 | Ingeniería Civil | 103 | 103 |
| `HABILITACION_URBANA` | 2 | Ingeniería Civil | 1 | 1 |
| `HABILITACION_URBANA` | 3 | Ingeniería Civil | 6 | 6 |
| `HABILITACION_URBANA` | 4 | Ingeniería Civil | 22 | 22 |
| `INSPECCION_OBRA` | 1 | Ingeniería Civil | 49 | 0 |
| `INSPECCION_OBRA` | 1 | Ingeniería Sanitaria | 2 | 0 |
| `INSPECCION_OBRA` | 1 | Ingeniería Electrónica | 1 | 0 |
| `INSPECCION_OBRA` | 1 | Inspección de Obra | 15 | 0 |
| `INSPECCION_OBRA` | 1 | Ingeniería Eléctrica y Mecánica Eléctrica | 4 | 0 |
| `INSPECCION_OBRA` | 3 | Inspección de Obra | 2 | 0 |

Períodos registrados (dos tramos anuales):

| Tramo | Períodos |
|---|---|
| 2026-08-01 → 2027-07-31 | 145 |
| 2025-08-01 → 2026-07-31 | 138 |

*Datos de desarrollo consultados: 2026-11-08 18:01 (UTC−05:00)*

### 0.7.2 Delegados

| Modelo | Tabla física | Campos |
|---|---|---|
| `Delegado` | `liquidaciones_delegado` | `perfil_ingeniero_id` (uno a uno) |
| `DelegadoOperacion` | `liquidaciones_delegadooperacion` | `delegado_id`, `municipalidad_id`, `tipo_liquidacion_id`, `especialidad_revision_id`, `tipo` |
| `DelegadoOperacionPeriodo` | `liquidaciones_delegadooperacionperiodo` | `delegado_municipalidad_id`, `periodo_inicio`, `periodo_fin` |

`DelegadoOperacion` vincula al delegado con **una municipalidad**, **un tipo de
liquidación** y **una especialidad de revisión**. El campo `tipo` distingue dos
roles: `TITULAR` y `ALTERNO`. La unicidad está sobre
`(delegado, municipalidad, tipo_liquidacion)`.

El tipo de liquidación de la operatividad es obligatorio en la práctica: sin él
no hay tasa aplicable y el cálculo de RH no puede resolverse.

Volumen real: **220 delegados**, **3 361 `DelegadoOperacion`** (las 3 361 con
tipo de liquidación asignado), **1 506 períodos**.

| Tipo | Rol | Operaciones | Períodos |
|---|---|---|---|
| `EDIFICACION` | `TITULAR` | 2 306 | 586 |
| `EDIFICACION` | `ALTERNO` | 545 | 548 |
| `HABILITACION_URBANA` | `TITULAR` | 335 | 188 |
| `HABILITACION_URBANA` | `ALTERNO` | 175 | 184 |

Períodos registrados (dos tramos anuales):

| Tramo | Períodos |
|---|---|
| 2026-09-01 → 2027-08-31 | 753 |
| 2025-09-01 → 2026-08-31 | 753 |

Una operatividad real (municipalidad `L-80`, rol `TITULAR`):

| Tipo | Municipalidad | Rol | Especialidad | Período |
|---|---|---|---|---|
| `EDIFICACION` | L-80 | `TITULAR` | Ingeniería Civil | 2026-09-01 → 2027-08-31 |
| `EDIFICACION` | L-80 | `TITULAR` | Ingeniería Civil | 2025-09-01 → 2026-08-31 |
| `EDIFICACION` | L-80 | `TITULAR` | Ingeniería Eléctrica y Mecánica Eléctrica | 2025-09-01 → 2026-08-31 |
| `EDIFICACION` | L-80 | `ALTERNO` | Ingeniería Sanitaria | 2025-09-01 → 2026-08-31 |

*Datos de desarrollo consultados: 2026-11-08 18:02 (UTC−05:00)*

### 0.7.3 Especialidades de revisión y capítulos

| Modelo | Tabla física | Campos |
|---|---|---|
| `Capitulo` | `usuarios_capitulo` | `registro_id`, `abreviacion`, `nombre`, `grupo_envio_intitucional` |
| `EspecialidadRevisionCapitulo` | `usuarios_especialidadrevisioncapitulo` | `especialidad_revision_id`, `capitulo_id` |

El vínculo especialidad → capítulo es lo que permite repartir el fondo común
entre los capítulos profesionales (ver documento 03).

Capítulos registrados (10):

| `registro_id` | Abreviatura | Nombre |
|---|---|---|
| 00 | NO ESPECIFICADO | NO ESPECIFICADO |
| 01 | AGRONOMICA | INGENIERIA AGRONOMICA Y ZOOTECNIA |
| 02 | CIVIL | INGENIERIA CIVIL |
| 03 | GEOLOGICA | INGENIERIA GEOLOGICA |
| 04 | INDUSTRIAL-SIST | INGENIERÍA INDUSTRIAL, DE SISTEMAS Y TRANSPORTE |
| 05 | MECANICA | INGENIERIA MECÁNICA Y MECÁNICA ELÉCTRICA |
| 09 | SANITARIA | INGENIERIA SANITARIA E HIGIENE Y SEGURIDAD INDUSTRIAL |
| 15 | ELECTRICA | INGENIERIA ELECTRICA |
| 16 | ELECTRONICA | INGENIERIA ELECTRONICA |
| 25 | AMBIENTAL | INGENIERIA AMBIENTAL |

Capítulos por especialidad de revisión:

| Especialidad de revisión | Capítulos vinculados |
|---|---|
| Ingeniería Civil | 1 |
| Ingeniería Electrónica | 1 |
| Ingeniería Eléctrica y Mecánica Eléctrica | 2 |
| Ingeniería Sanitaria | 1 |

*Datos de desarrollo consultados: 2026-11-08 18:03 (UTC−05:00)*

## 0.8 RH: escalas, rangos y tasas

### 0.8.1 Escala de descuento del inspector

| Modelo | Tabla física | Campos |
|---|---|---|
| `EscalaDescuentoInspector` | `finanzas_escaladescuentoinspector` | `nombre`, `periodo_inicio`, `periodo_fin` |
| `RangoDescuentoInspector` | `finanzas_rangodescuentoinspector` | `escala_id`, `monto_minimo`, `monto_maximo`, `porcentaje_descuento` |

Escala vigente:

| Escala | Vigencia |
|---|---|
| Escala 2026 | 2026-01-01 → abierto |

Rangos de esa escala:

| `monto_minimo` | `monto_maximo` | `porcentaje_descuento` |
|---|---|---|
| 0.00 | 8000.00 | 0.1500 |
| 8000.00 | 15000.00 | 0.2000 |
| 15000.00 | 30000.00 | 0.3000 |
| 30000.00 | — | 0.4000 |

El rango se elige **por el subtotal acumulado del mes**: el primer rango cuyo
`monto_minimo` es menor o igual al subtotal, y cuyo `monto_maximo` es `NULL` o
mayor o igual. El último rango (sin `monto_maximo`) cubre los montos altos.

### 0.8.2 Tasa del delegado

| Modelo | Tabla física | Campos |
|---|---|---|
| `TasaDelegado` | `finanzas_tasadelegado` | `nombre`, `renta_cip`, `aporte_codemu`, `fondo_comun`, `tipo_liquidacion_id`, `periodo_inicio`, `periodo_fin` |

Las tres tasas son fracciones del importe bruto de la liquidación. El tipo de
liquidación de la operatividad del delegado determina qué tasa se usa.

| Tipo | `renta_cip` | `aporte_codemu` | `fondo_comun` | Vigencia |
|---|---|---|---|---|
| `EDIFICACION` | 0.2500 | 0.0500 | 0.1000 | 1900-01-01 → abierto |
| `HABILITACION_URBANA` | 0.2500 | 0.0500 | 0.0000 | 1900-01-01 → abierto |
| `MECANICA_SUELOS` | 0.1000 | 0.0500 | 0.0000 | 1900-01-01 → abierto |
| `IMPACTO_VIAL` | 0.0000 | 0.0000 | 0.0000 | 1900-01-01 → abierto |
| `INSPECCION_OBRA` | 0.0000 | 0.0000 | 0.0000 | 1900-01-01 → abierto |
| `TALUDES` | 0.0000 | 0.0000 | 0.0000 | 1900-01-01 → abierto |

Con estas tasas, el neto a pagar de un delegado es
`importe × (1 − renta_cip − aporte_codemu − fondo_comun)`. En Edificación eso
es 0.60 del bruto; en Habilitación Urbana, 0.70; en Mecánica de Suelos, 0.85.

*Datos de desarrollo consultados: 2026-11-08 18:03 (UTC−05:00)*

## 0.9 Liquidaciones y sus tablas de detalle

### 0.9.1 Cabecera

| Modelo | Tabla física | Campos clave |
|---|---|---|
| `LiquidacionGeneral` | `liquidaciones_liquidaciongeneral` | `fecha_registro`, `estado`, `sub_total`, `total`, `igv_snapshot`, `uit_snapshot`, `expediente`, `numero_revision`, `modo_calculo`, `legacy`, `eliminado`, `fecha_eliminacion`, `motivo_eliminacion`, `tipo_liquidacion_id`, `municipalidad_id`, `proyecto_id`, `igv_id_id`, `uit_id_id`, `usuario_creador_id` |

Puntos a tener presentes:

- `estado` tiene dos valores: `PENDIENTE` y `PAGADA`.
- `modo_calculo` distingue `TARIFA` (calculado con el catálogo) de `MANUAL`
  (el modo "edge", con subtotal cargado a mano y sin tarifa aplicada).
- `eliminado` es la marca de baja lógica; la baja conserva el registro y
  guarda `fecha_eliminacion` y `motivo_eliminacion`.
- `igv_snapshot` / `uit_snapshot` congelan los valores financieros usados.
- `igv_id_id` / `uit_id_id` apuntan a las filas exactas del catálogo que se
  aplicaron.

### 0.9.2 Tablas de detalle por tipo

| Modelo | Tabla física | Campos clave |
|---|---|---|
| `LiquidacionPorMetroCuadrado` | `liquidaciones_liquidacionpormetrocuadrado` | `area_m2`, `costo_por_m2`, `derecho_minimo`, `derecho_maximo`, `tarifa_aplicada_id`, `derecho_id` |
| `LiquidacionPorcentajeObra` | `liquidaciones_liquidacionporcentajeobra` | `tipo_tramite`, `valor_declarado`, `porcentaje_liquidacion`, `porcentaje_tarifa`, `estrategia_cotizacion`, `cantidad_especialidades_habilitadas`, `total_explicito`, `derecho_minimo`, `derecho_maximo`, `porcentaje_minimo_uit`, `derecho_aplicado_id`, `tarifa_aplicada_id` |
| `LiquidacionPorcentajeObraDetalle` | `liquidaciones_liquidacionporcentajeobradetalle` | `porcentaje_aplicado`, `subtotal`, `importe_parcial`, `ajuste_redondeo`, `especialidad_id`, `tarifa_aplicada_id` |
| `LiquidacionPorCategoriaVisitas` | `liquidaciones_liquidacionporcategoriavisitas` | `cantidad_visitas`, `porcentaje_uit`, `categoria`, `tarifa_aplicada_id` |
| `LiquidacionPorcentajeObraAcumulacion` | `liquidaciones_liquidacionporcentajeobraacumulacion` | — (proyección de acumulación) |

Además, cada tipo tiene su tabla envoltorio de un uno a uno con
`LiquidacionGeneral` (`liquidaciones_liquidacionedificacion`,
`...habilitacionurbana`, `...mecanicasuelos`, `...taludes`, `...impactovial`,
`...inspeccionobra`), que es donde vive el **número** correlativo de la
liquidación específica.

### 0.9.3 Comprobantes

| Modelo | Tabla física | Campos clave |
|---|---|---|
| `LiquidacionComprobante` | `liquidaciones_liquidacioncomprobante` | `tipo_comprobante`, `serie`, `numero`, `fecha_emision`, `monto`, `activo`, `motivo_reemplazo` |

Una liquidación puede tener varios comprobantes, pero **solo uno activo** a la
vez: cuando se emite uno nuevo, el anterior pasa a `activo = false` y guarda el
`motivo_reemplazo`. El comprobante activo es el que aparece en el detalle de la
liquidación y en los reportes de RH.

### 0.9.4 Relaciones entre liquidaciones (revisiones)

| Modelo | Tabla física | Campos clave |
|---|---|---|
| `LiquidacionRelacionGrupo` | `liquidaciones_liquidacionrelaciongrupo` | `codigo` |
| `LiquidacionRelacionMiembro` | `liquidaciones_liquidacionrelacionmiembro` | `relacion_key`, `numero_revision` |

La `relacion_key` es una etiqueta del tipo `TIPO-TRÁMITE` (por ejemplo
`EDIFICACION-AMPLIACION`). Una primera revisión abre un grupo; una nueva
revisión o una liquidación relacionada se suma como miembro del mismo grupo.

### 0.9.5 Asignaciones sobre liquidaciones

| Modelo | Tabla física | Campos clave |
|---|---|---|
| `LiquidacionInspector` | `liquidaciones_liquidacioninspector` | `liquidacion_id` (→ `LiquidacionPorCategoriaVisitas`), `inspector_id`, `inspector_operacion_id`, `especialidad_revision_id`, `periodo`, `mes`, `dictamen_revision`, `fecha_presentacion`, `fecha_revision` |
| `LiquidacionDelegado` | `liquidaciones_liquidaciondelegado` | `liquidacion_id` (→ `LiquidacionGeneral`), `delegado_id`, `delegado_operacion_id`, `especialidad_revision_id`, `periodo`, `mes`, `dictamen_revision`, `fecha_presentacion`, `fecha_revision`, `numero_rh`, `creado_por_rh` |

`creado_por_rh` marca las asignaciones que nacieron dentro del flujo de RH
mensual: al eliminar un RH, esas asignaciones se limpian; las históricas o
compartidas se conservan.

### 0.9.6 Datos de contexto

| Modelo | Tabla física | Registros |
|---|---|---|
| `Proyecto` | `liquidaciones_proyecto` | 71 656 |
| `Municipalidad` | `entidades_municipalidad` | 94 |
| `PerfilIngeniero` | `usuarios_perfilingeniero` | 396 |

## 0.10 Volumen de datos registrado

| Dato | Cantidad |
|---|---|
| Liquidaciones (`LiquidacionGeneral`) | 62 019 |
| Liquidaciones `EDIFICACION` | 50 759 |
| Liquidaciones `INSPECCION_OBRA` | 9 852 |
| Liquidaciones `HABILITACION_URBANA` | 1 408 |
| Comprobantes (todos activos) | 54 913 |
| Asignaciones de inspector (`LiquidacionInspector`) | 9 860 sobre 9 850 liquidaciones |
| Asignaciones de delegado (`LiquidacionDelegado`) | 139 154 sobre 49 485 liquidaciones |
| Grupos de relación | 1 402 |
| Miembros de relación | 1 (`EDIFICACION-AMPLIACION`) |
| Inspectores / delegados | 220 / 220 |
| Perfiles de ingeniero | 396 |

Rango de fechas de registro de las liquidaciones:

| Tipo | Desde | Hasta |
|---|---|---|
| `EDIFICACION` | 2003-01-29 | 2026-10-30 |
| `INSPECCION_OBRA` | 2003-12-21 | 2026-10-30 |
| `HABILITACION_URBANA` | 2010-02-09 | 2026-10-27 |

Estado actual de las 62 019 liquidaciones: 62 019 en `PENDIENTE`, 0 en
`PAGADA`, 0 con baja lógica (`eliminado = true`).

*Datos de desarrollo consultados: 2026-11-08 18:05 (UTC−05:00)*

## 0.11 Cómo leer el resto de la guía

| Documento | Datos de este documento que consume |
|---|---|
| [01 — Liquidaciones](01-liquidaciones-flujo-operativo.md) | Secciones 0.3 a 0.6 y 0.9 |
| [02 — Operatividad](02-operatividad-de-inspectores-y-delegados.md) | Secciones 0.6, 0.7 y 0.7.3 |
| [03 — RH y reparto](03-rh-mensual-y-reparto-estacional.md) | Secciones 0.7.3, 0.8 y 0.9.5 |
