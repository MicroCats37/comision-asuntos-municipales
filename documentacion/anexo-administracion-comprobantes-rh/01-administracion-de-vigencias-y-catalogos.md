# 01 - Administración de vigencias y catálogos

Este documento describe **la zona de administración** del sistema: el conjunto de
catálogos parametrizados que un operador mantiene para que CAM sepa qué cobrar,
con qué topes y qué escalas aplicar. Cada catálogo se explica con su propósito,
su modelo y tabla física, sus campos de operación, su relación con el resto del
modelo, la regla de vigencia que aplica, dónde se administra y ejemplos reales
de la base de desarrollo.

El documento primero explica el **concepto único de vigencia** —una sola idea que
todos los catálogos comparten— y después muestra **cómo cada catálogo lo usa**.

---

## 1.1 El concepto único de vigencia

### Los dos campos

Todos los catálogos parametrizados que tienen vigencia usan la misma pareja de
campos, declarada una sola vez en la clase base `VigenciaModel`
(`backend/core_application/models.py`):

| Campo | Tipo | Significado |
|---|---|---|
| `periodo_inicio` | `date`, NOT NULL | Fecha desde la que el registro aplica. |
| `periodo_fin` | `date`, nullable | Fecha hasta la que el registro aplica. `NULL` = **período abierto**, es decir, vigente hacia adelante. |

El rango es **inclusivo en ambos extremos**: un registro con
`periodo_inicio = 2026-01-01` y `periodo_fin = 2026-12-31` aplica durante todo el
año 2026, incluidos el 1 y el 31 de diciembre.

### Cómo se resuelve

La clase base declara dos operaciones de consulta sobre un `QuerySet`
(`VigenciaQuerySet`), que son la forma en que todo el sistema pregunta "¿qué
vale hoy?":

| Operación | Qué hace |
|---|---|
| `vigentes(fecha)` | Devuelve todos los registros con `periodo_inicio <= fecha` **y** (`periodo_fin IS NULL` **o** `periodo_fin >= fecha`). Con `fecha` omitida, usa la fecha de hoy. |
| `vigente(fecha)` | Devuelve **el más reciente** de esos, ordenando por `periodo_inicio` descendente. Es la operación que usa el sistema para "la tarifa que corresponde a esta fecha". |

Consecuencia práctica: **una fecha nunca crea ni modifica catálogo**. Cambiar la
fecha de referencia cambia qué registro se resuelve, no el catálogo. Para que un
cambio entre en vigor hay que **cerrar el tramo anterior** (`periodo_fin`) y
**abrir uno nuevo** (`periodo_inicio`).

### La regla del ámbito (*scope*)

Cada catálogo declara su **ámbito de independencia** mediante
`vigencia_scope_fields`:

- **Ámbito global** (`vigencia_scope_fields = SCOPE_GLOBAL`, la tupla vacía): toda
  la tabla es un solo ámbito. No puede haber dos registros vigentes que se
  solapen, pero sí puede haber varios tipos de cálculo conviviendo porque no
  comparten tabla.
- **Ámbito por tipo de liquidación** (`SCOPE_TIPO_LIQUIDACION`): las filas se
  particionan por `tipo_liquidacion_id`. Un registro de Edificación y uno de
  Habilitación Urbana pueden estar vigentes a la vez sin colisionar.
- **Ámbito por tipo y especialidad** (`SCOPE_TIPO_LIQUIDACION_ESPECIALIDAD`): las
  filas se particionan por `tipo_liquidacion_id` **y** `especialidad_id`.

El ámbito se declara **una sola vez por modelo** y se consume en dos lugares que
no pueden discrepar:

1. La **validación en Python**
   (`core_application/vigencia/services.py`), que rechaza un solapamiento con el
   mensaje *"El período de vigencia se superpone con otro período vigente…"*
   (o su variante por tipo / por tipo y especialidad).
2. La **restricción de exclusión en PostgreSQL**, que se materializa como un
   índice GIST sobre el rango de fechas:

   ```sql
   EXCLUDE USING gist (
       <campos_de_ambito> WITH =,
       daterange(periodo_inicio, periodo_fin, '[]') WITH &&
   )
   ```

   Confirmada en la base de desarrollo para los diez catálogos de este documento.

Las claves foráneas de los catálogos están declaradas en el código con
`on_delete=models.PROTECT`, y en la base se materializan como FK simples
`DEFERRABLE INITIALLY DEFERRED`, **sin** cláusula `ON DELETE`: la prohibición de
borrar un tipo de liquidación, una especialidad o una escala con catálogo
vigente la aplica Django, no PostgreSQL.

Además, cada catálogo con vigencia declara un *check constraint* que impide
rangos invertidos:

```sql
CHECK ((periodo_fin IS NULL) OR (periodo_inicio <= periodo_fin))
```

### El rollover en la administración

La administración de un catálogo con vigencia usa el mixin compartido
`VigenciaAdminMixin` (`backend/core_application/vigencia/admin.py`), que aporta
un comportamiento uniforme:

- **Listado ordenado** por `-periodo_inicio`, con `date_hierarchy` sobre
  `periodo_inicio` para navegar por fecha.
- **Filtro "Vigencia"** con cuatro opciones: *Vigente hoy*, *Vigente en fecha X*,
  *No vigente hoy* y *Sin fecha de cierre*.
- **Columnas de estado**: *Vigente hoy* (la ventana de vigencia contiene la
  fecha actual) y *Abierto* (no tiene `periodo_fin`). Son cosas distintas: un
  período puede estar vigente y a la vez cerrado.
- **Cierre automático**: el formulario de alta incluye la casilla *"Cerrar la
  vigencia vigente anterior"*, marcada por defecto (la casilla solo aparece al
  añadir un período; al editar uno existente se retira del formulario). Al
  guardar un período nuevo, el período abierto del mismo ámbito se cierra el
  día anterior al inicio del nuevo, y todo ocurre dentro de una transacción: si
  la creación falla, el ámbito no queda a medio cerrar.

Esa casilla es la forma operativa de **encadenar vigencias**: para cambiar una
tarifa, se añade un período nuevo con la fecha de entrada correspondiente y se
acepta el cierre automático del anterior.

### Cómo se ve esto en cada catálogo

| Catálogo | Ámbito | Filas que pueden coexistir vigentes |
|---|---|---|
| Tarifas Base Porcentuales | Por tipo de liquidación | Una por cada tipo de cálculo por porcentaje |
| Tarifas Base por Metro Cuadrado | Por tipo de liquidación | Una por cada tipo de cálculo por m² |
| Tarifas Base por Visitas | Por tipo de liquidación | Una por cada tipo de cálculo por visitas |
| Derechos Mínimos Porcentuales de Obra | Global | Una |
| Derechos Mínimos por Metro Cuadrado | Global | Una |
| IGV | Global | Una |
| UIT | Global | Una |
| Escalas de Descuento del Inspector | Global | Una |
| Tasas de Delegado | Por tipo de liquidación | Una por tipo |
| Especialidades de Liquidaciones | Por tipo y especialidad | Una por par tipo/especialidad |

---

## 1.2 Los diez catálogos

### 1.2.1 Tarifas Base Porcentuales

**Propósito.** Es el catálogo cabecera de las tarifas que se calculan como
porcentaje del valor de la obra. Cada fila es un "tramo de tarifario" de un tipo
de liquidación, y su detalle (el porcentaje concreto) cuelga de él.

| Aspecto | Detalle |
|---|---|
| Modelo | `TarifaLiquidacionBase` (tabla física `liquidaciones_tarifaliquidacionbase`) |
| Entrada de administración | Proxy `TarifaBasePorcentajeObraProxy` → `/admin/liquidaciones/tarifabaseporcentajeobraproxy/` |
| Tipos que admite | `EDIFICACION`, `IMPACTO_VIAL`, `TALUDES` (filtro `tipo_codigos` del admin) |
| Ámbito de vigencia | `SCOPE_TIPO_LIQUIDACION` |
| Restricción | `exclude_tarifa_liquidacion_base_overlap` + `vigencia_rango_valido_tarifa_liquidacion_base` |

**Campos de operación.**

| Campo | Tipo | Función |
|---|---|---|
| `periodo_inicio` | `date` | Inicio de la vigencia del tramo tarifario. |
| `periodo_fin` | `date`, nullable | Fin de la vigencia. `NULL` = tramo abierto. |
| `tipo_liquidacion_id` | `uuid` → `liquidaciones_tipoliquidacion(id)` | Tipo al que aplica el tramo. Borrado protegido por Django (`on_delete=PROTECT`). |
| `id`, `created_at`, `updated_at` | `uuid`, `timestamptz` | Identidad y auditoría. |

**Detalle inline: `TarifaPorcentajeObra`** (tabla
`liquidaciones_tarifaporcentajeobra`), en relación `detalle_porcentual` con el
catálogo:

| Campo | Tipo | Función |
|---|---|---|
| `porcentaje_liquidacion` | `numeric(7,4)` | Fracción decimal del derecho a liquidar (ej. `0.0015` = 0,15 %). |
| `tarifa_base_id` | `uuid`, nullable | Cabecera tarifaria a la que pertenece. |

La relación es de uno a muchos por `detalle_porcentual`, y la cabecera es
obligatoria en el modelo `TarifaPorcentajeObra` pero la columna admite `NULL`
para trazabilidad de datos heredados.

**Dónde se administra.** En `/admin/liquidaciones/tarifabaseporcentajeobraproxy/`,
con el inline `TarifaPorcentajeObraInline` (tabular, `extra = 0`): la pantalla
del tramo tarifario muestra y permite **editar** el detalle porcentual ya
existente, y el alta de un detalle nuevo se hace desde su listado propio
`/admin/liquidaciones/tarifaporcentajeobra/`. El listado del proxy permite
filtrar por tipo de liquidación y por estado de vigencia.

**Ejemplos reales.**

| Tipo | `periodo_inicio` | `periodo_fin` | `porcentaje_liquidacion` |
|---|---|---|---|
| `EDIFICACION` | 2000-01-01 | 2026-04-30 | 0.0002 |
| `EDIFICACION` | 2026-05-01 | *(abierto)* | 0.0005 |
| `IMPACTO_VIAL` | 2000-01-01 | 2026-04-30 | 0.0004 |
| `IMPACTO_VIAL` | 2026-05-01 | *(abierto)* | 0.0015 |
| `TALUDES` | 2000-01-01 | 2026-04-30 | 0.0004 |
| `TALUDES` | 2026-05-01 | *(abierto)* | 0.0015 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

Los tramos `HABILITACION_URBANA` y `MECANICA_SUELOS` también existen en
`liquidaciones_tarifaliquidacionbase` con `periodo_inicio` 2000-01-01 y
`periodo_fin` 2026-04-30, y desde 2026-05-01 abierto, pero sin fila de detalle
porcentual: esos tipos no se calculan por porcentaje.

---

### 1.2.2 Tarifas Base por Metro Cuadrado

**Propósito.** Es el catálogo cabecera del tarifario por superficie: cada tramo
vigente de un tipo calculado en metros cuadrados, con su costo por m².

| Aspecto | Detalle |
|---|---|
| Modelo | `TarifaLiquidacionBase` (tabla `liquidaciones_tarifaliquidacionbase`) |
| Entrada de administración | Proxy `TarifaBaseMetroCuadradoProxy` → `/admin/liquidaciones/tarifabasemetrocuadradoproxy/` |
| Tipos que admite | `HABILITACION_URBANA`, `MECANICA_SUELOS` |
| Ámbito de vigencia | `SCOPE_TIPO_LIQUIDACION` |
| Restricción | `exclude_tarifa_liquidacion_base_overlap` + `vigencia_rango_valido_tarifa_liquidacion_base` |

**Detalle inline: `TarifaPorMetroCuadrado`** (tabla
`liquidaciones_tarifapormetrocuadrado`).

| Campo | Tipo | Función |
|---|---|---|
| `costo_por_m2` | `numeric(10,4)` | Costo por metro cuadrado en soles. |
| `tarifa_base_id` | `uuid`, UNIQUE | Cabecera tarifaria. La unicidad garantiza un único detalle m² por tramo. |

A diferencia del detalle porcentual, aquí la relación es de **uno a uno**
(`OneToOneField`): un tramo tarifario m² tiene exactamente un costo por m². La
base física lo refuerza con el índice único
`liquidaciones_tarifapormetrocuadrado_tarifa_base_id_key`.

**Dónde se administra.** En
`/admin/liquidaciones/tarifabasemetrocuadradoproxy/`, con el inline
`TarifaPorMetroCuadradoInline` (apilado, `extra = 0`): la pantalla del tramo
tarifario muestra y permite **editar** el costo por m² ya existente, y el alta
de un detalle nuevo se hace desde su listado propio
`/admin/liquidaciones/tarifapormetrocuadrado/`.

**Ejemplos reales.**

| Tipo | `periodo_inicio` | `periodo_fin` | `costo_por_m2` |
|---|---|---|---|
| `HABILITACION_URBANA` | 2000-01-01 | 2026-04-30 | 0.1500 |
| `HABILITACION_URBANA` | 2026-05-01 | *(abierto)* | 0.2000 |
| `MECANICA_SUELOS` | 2000-01-01 | 2026-04-30 | 0.1500 |
| `MECANICA_SUELOS` | 2026-05-01 | *(abierto)* | 0.2000 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

---

### 1.2.3 Tarifas Base por Visitas

**Propósito.** Es el catálogo cabecera del tarifario de Inspección de Obra: el
tramo vigente que define el porcentaje de UIT aplicable a cada categoría de
visita.

| Aspecto | Detalle |
|---|---|
| Modelo | `TarifaLiquidacionBase` (tabla `liquidaciones_tarifaliquidacionbase`) |
| Entrada de administración | Proxy `TarifaBaseVisitasProxy` → `/admin/liquidaciones/tarifabasevisitasproxy/` |
| Tipos que admite | `INSPECCION_OBRA` |
| Ámbito de vigencia | `SCOPE_TIPO_LIQUIDACION` |
| Restricción | `exclude_tarifa_liquidacion_base_overlap` + `vigencia_rango_valido_tarifa_liquidacion_base` |

**Detalle inline: `TarifaPorCategoriaVisitas`** (tabla
`liquidaciones_tarifaporcategoriavisitas`).

| Campo | Tipo | Función |
|---|---|---|
| `categoria_visitas` | `varchar(50)` | Categoría de la visita. Los valores admitidos por el modelo son `1`, `2`, `3` y `4` (`CategoriaIO`). |
| `porcentaje_uit` | `numeric(10,4)` | Porcentaje de la UIT aplicable por visita de esa categoría. |
| `tarifa_base_id` | `uuid` | Cabecera tarifaria. Relación de uno a muchos por `detalle_visitas`. |

La relación es de **uno a muchos**: un tramo tarifario de visitas sostiene una
fila por categoría.

**Dónde se administra.** En `/admin/liquidaciones/tarifabasevisitasproxy/`, con
el inline `TarifaPorCategoriaVisitasInline` (tabular, `extra = 1`) que permite
añadir una fila por categoría directamente en la pantalla del tramo tarifario.

**Ejemplos reales.** Un único tramo vigente desde 2000-01-01, abierto, con las
cuatro categorías:

| `categoria_visitas` | `porcentaje_uit` |
|---|---|
| 1 | 0.0320 |
| 2 | 0.0370 |
| 3 | 0.0420 |
| 4 | 0.0880 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

El costo por visita se obtiene multiplicando `porcentaje_uit` por el valor de UIT
vigente en la fecha de la liquidación. En las ocho liquidaciones de Inspección de
Obra no legacy de la base se observa el uso de las categorías 3 y 4, con
porcentajes 0.0420 y 0.0880 respectivamente.

---

### 1.2.4 Derechos Mínimos Porcentuales de Obra

**Propósito.** Es el catálogo de topes y suelo del cálculo por porcentaje: define
el derecho mínimo absoluto, el derecho máximo y el porcentaje de UIT que actúa
como mínimo cuando el derecho calculado por porcentaje queda por debajo del suelo.

| Aspecto | Detalle |
|---|---|
| Modelo | `DerechoPorcentajeObra` (tabla `liquidaciones_derechoporcentajeobra`) |
| Entrada de administración | `/admin/liquidaciones/derechoporcentajeobra/` |
| Ámbito de vigencia | `SCOPE_GLOBAL` |
| Restricción | `exclude_derecho_porcentaje_obra_overlap` + `vigencia_rango_valido_derecho_porcentaje_obra` |

**Campos de operación.**

| Campo | Tipo | Función |
|---|---|---|
| `derecho_minimo` | `numeric(10,4)`, nullable | Suelo absoluto del derecho en soles. `NULL` = sin suelo. |
| `derecho_maximo` | `numeric(10,4)`, nullable | Techo absoluto del derecho en soles. `NULL` = sin tope. |
| `porcentaje_minimo_uit` | `numeric(7,4)` | Fracción de UIT que actúa como derecho mínimo. |
| `periodo_inicio`, `periodo_fin` | `date` | Vigencia del catálogo. |

**Relación.** No tiene FK a tipo de liquidación: al ser de ámbito global,
aplica a todos los tipos calculados por porcentaje. El motor de cálculo lo
resuelve con `vigentes()` sobre la fecha de referencia.

**Dónde se administra.** En `/admin/liquidaciones/derechoporcentajeobra/`, con
listado por `derecho_minimo`, `derecho_maximo`, `porcentaje_minimo_uit` y las dos
fechas de vigencia, y el filtro de vigencia heredado.

**Ejemplos reales.**

| `periodo_inicio` | `periodo_fin` | `derecho_minimo` | `derecho_maximo` | `porcentaje_minimo_uit` |
|---|---|---|---|---|
| 2000-01-01 | *(abierto)* | *(NULL)* | *(NULL)* | 0.0300 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

---

### 1.2.5 Derechos Mínimos por Metro Cuadrado

**Propósito.** Es el catálogo de topes y suelo del cálculo por superficie: el
derecho mínimo y el máximo absolutos que se aplican a una liquidación por m².

| Aspecto | Detalle |
|---|---|
| Modelo | `DerechoPorMetroCuadrado` (tabla `liquidaciones_derechopormetrocuadrado`) |
| Entrada de administración | `/admin/liquidaciones/derechopormetrocuadrado/` |
| Ámbito de vigencia | `SCOPE_GLOBAL` |
| Restricción | `exclude_derecho_por_metro_cuadrado_overlap` + `vigencia_rango_valido_derecho_por_metro_cuadrado` |

**Campos de operación.**

| Campo | Tipo | Función |
|---|---|---|
| `derecho_minimo` | `numeric(10,2)` | Suelo absoluto del derecho en soles. |
| `derecho_maximo` | `numeric(10,2)` | Techo absoluto del derecho en soles. |
| `periodo_inicio`, `periodo_fin` | `date` | Vigencia del catálogo. |

**Relación.** Las liquidaciones por m² lo referencian desde
`liquidaciones_liquidacionpormetrocuadrado.derecho` (columna `derecho_id`, FK con
`on_delete=PROTECT` en el código), de modo que el catálogo es histórico: una
liquidación conserva el derecho que se le aplicó.

**Dónde se administra.** En `/admin/liquidaciones/derechopormetrocuadrado/`.

**Ejemplos reales.**

| `periodo_inicio` | `periodo_fin` | `derecho_minimo` | `derecho_maximo` |
|---|---|---|---|
| 2000-01-01 | 2026-04-30 | 750.00 | 7500.00 |
| 2026-05-01 | *(abierto)* | 1000.00 | 10000.00 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

---

### 1.2.6 IGV

**Propósito.** Es la tasa del Impuesto General a las Ventas aplicable a las
liquidaciones. Se guarda como **fracción decimal**, no como porcentaje: `0.18`
es 18 %.

| Aspecto | Detalle |
|---|---|
| Modelo | `IGV` (tabla `finanzas_igv`) |
| Entrada de administración | `/admin/finanzas/igv/` |
| Ámbito de vigencia | `SCOPE_GLOBAL` |
| Restricción | `exclude_igv_overlap` + `vigencia_rango_valido_igv` |

**Campos de operación.**

| Campo | Tipo | Función |
|---|---|---|
| `valor` | `numeric(3,2)` | Tasa como fracción decimal. El modelo valida `0 <= valor <= 1` con `MinValueValidator` / `MaxValueValidator`. |
| `periodo_inicio`, `periodo_fin` | `date` | Vigencia del catálogo. |

**Relación.** `liquidaciones_liquidaciongeneral.igv_id_id` (columna física de la
FK `igv_id`) referencia el registro de IGV aplicado
(`FOREIGN KEY (igv_id_id) REFERENCES finanzas_igv(id) DEFERRABLE INITIALLY
DEFERRED`), y `liquidaciones_liquidaciongeneral.igv_snapshot` congela el valor
aplicado. Los cálculos de liquidación toman el IGV vigente con
`IGV.objects.vigente()`.

**Dónde se administra.** En `/admin/finanzas/igv/`, listado por `valor` y las dos
fechas.

**Ejemplos reales.**

| `periodo_inicio` | `periodo_fin` | `valor` |
|---|---|---|
| 2000-01-01 | 2026-11-07 | 0.18 |
| 2026-11-08 | *(abierto)* | 0.18 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

---

### 1.2.7 UIT

**Propósito.** Es el valor de la Unidad Impositiva Tributaria en soles. Es el
referencial monetario de todo el sistema: define el costo por visita de la
Inspección de Obra, el derecho mínimo porcentual y el mínimo por m².

| Aspecto | Detalle |
|---|---|
| Modelo | `UIT` (tabla `finanzas_uit`) |
| Entrada de administración | `/admin/finanzas/uit/` |
| Ámbito de vigencia | `SCOPE_GLOBAL` |
| Restricción | `exclude_uit_overlap` + `vigencia_rango_valido_uit` |

**Campos de operación.**

| Campo | Tipo | Función |
|---|---|---|
| `valor` | `integer` | Valor de la UIT en soles. |
| `periodo_inicio`, `periodo_fin` | `date` | Vigencia del catálogo. |

**Relación.** `liquidaciones_liquidaciongeneral.uit_id_id` (columna física de la
FK `uit_id`) referencia el registro de UIT aplicado
(`FOREIGN KEY (uit_id_id) REFERENCES finanzas_uit(id) DEFERRABLE INITIALLY
DEFERRED`) y `uit_snapshot` congela el valor. El motor de Inspección de Obra
calcula `costo_por_visita = porcentaje_uit × UIT vigente`.

**Dónde se administra.** En `/admin/finanzas/uit/`.

**Ejemplos reales.** El catálogo tiene 28 filas, una por tramo anual desde 2000.

| `periodo_inicio` | `periodo_fin` | `valor` |
|---|---|---|
| 2023-01-01 | 2023-12-31 | 4950 |
| 2024-01-01 | 2024-12-31 | 5150 |
| 2025-01-01 | 2025-12-31 | 5350 |
| 2026-01-01 | 2026-11-07 | 1000 |
| 2026-11-08 | *(abierto)* | 7777 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

---

### 1.2.8 Escalas de Descuento del Inspector

**Propósito.** Es el catálogo de descuento sobre los honorarios del inspector.
Una escala es una lista de **rangos de monto** y el porcentaje de descuento que
corresponde a cada rango. El motor del RH mensual toma el sub_total del mes,
localiza el rango que lo contiene y aplica ese porcentaje.

| Aspecto | Detalle |
|---|---|
| Modelo | `EscalaDescuentoInspector` (tabla `finanzas_escaladescuentoinspector`) |
| Entrada de administración | `/admin/finanzas/escaladescuentoinspector/` |
| Ámbito de vigencia | `SCOPE_GLOBAL` |
| Restricción | `exclude_escala_descuento_inspector_overlap` + `vigencia_rango_valido_escala_descuento_inspector` |

**Campos de operación de la cabecera.**

| Campo | Tipo | Función |
|---|---|---|
| `nombre` | `varchar(100)` | Nombre de la escala. |
| `periodo_inicio`, `periodo_fin` | `date` | Vigencia de la escala. |

**Detalle inline: `RangoDescuentoInspector`** (tabla
`finanzas_rangodescuentoinspector`).

| Campo | Tipo | Función |
|---|---|---|
| `monto_minimo` | `numeric(12,2)` | Límite inferior **inclusive** del rango. |
| `monto_maximo` | `numeric(12,2)`, nullable | Límite superior **exclusivo** del rango. `NULL` = sin tope. |
| `porcentaje_descuento` | `numeric(5,4)` | Tasa de descuento como fracción decimal. |
| `escala_id` | `uuid` | Escala a la que pertenece el rango. |

La relación es de **uno a muchos** por `rangos`. El modelo define además un
`UniqueConstraint` sobre `(escala_id, monto_minimo)`
(`unique_rango_descuento_inspector`), que impide dos rangos con el mismo mínimo
dentro de la misma escala.

La regla de aplicación del rango es: un monto pertenece al rango cuando
`monto_minimo <= monto < monto_maximo`; si `monto_maximo` es `NULL`, el rango
aplica a todo monto `>= monto_minimo`.

**Dónde se administra.** En `/admin/finanzas/escaladescuentoinspector/`, con el
inline `RangoDescuentoInspectorInline` (tabular, `extra = 0`): la pantalla de la
escala muestra y permite **editar** los rangos existentes, y el alta de un rango
nuevo se hace desde su listado propio
`/admin/finanzas/rangodescuentoinspector/`.

**Ejemplos reales.** Una escala vigente desde 2026-01-01, abierta, con cuatro
rangos:

| `monto_minimo` | `monto_maximo` | `porcentaje_descuento` |
|---|---|---|
| 0.00 | 8000.00 | 0.1500 |
| 8000.00 | 15000.00 | 0.2000 |
| 15000.00 | 30000.00 | 0.3000 |
| 30000.00 | *(NULL, sin tope)* | 0.4000 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

El descuento se aplica sobre el **subtotal del mes completo**, no sobre cada
línea: en los detalles de honorario persistidos se observa un sub_total de
S/ 2528.00 con tasa 0.100000 y un descuento de S/ 252.80, es decir exactamente
el 10 % de ese subtotal.

---

### 1.2.9 Tasas de Delegado

**Propósito.** Es el catálogo de retenciones que se aplican al honorario del
delegado: renta del CIP, aporte al CODEMU y fondo común. Sustituye a las
constantes que antes vivían en el código.

| Aspecto | Detalle |
|---|---|
| Modelo | `TasaDelegado` (tabla `finanzas_tasadelegado`) |
| Entrada de administración | `/admin/finanzas/tasadelegado/` |
| Ámbito de vigencia | `SCOPE_TIPO_LIQUIDACION` |
| Restricción | `exclude_tasa_delegado_overlap` + `vigencia_rango_valido_tasa_delegado` + índice único parcial `unique_tasa_delegado_vigente_por_tipo` |

**Campos de operación.**

| Campo | Tipo | Función |
|---|---|---|
| `tipo_liquidacion_id` | `uuid` → `liquidaciones_tipoliquidacion(id)` | Tipo al que aplican las tasas. Borrado protegido por Django (`on_delete=PROTECT`). |
| `nombre` | `varchar(100)` | Nombre descriptivo de la tasa. |
| `renta_cip` | `numeric(5,4)` | Fracción decimal de la renta del CIP. |
| `aporte_codemu` | `numeric(5,4)` | Fracción decimal del aporte al CODEMU. |
| `fondo_comun` | `numeric(5,4)` | Fracción decimal del fondo común. |
| `periodo_inicio`, `periodo_fin` | `date` | Vigencia. |

Las tres tasas se validan en el modelo entre 0 y 1.

**Relación.** Es el único catálogo de esta lista con ámbito **por tipo de
liquidación**: cada tipo de liquidación tiene su propio conjunto de tasas, y el
motor del RH mensual del delegado resuelve el vigente por el tipo de la
liquidación y la fecha de referencia.

**Dónde se administra.** En `/admin/finanzas/tasadelegado/`, con listado por tipo,
nombre y las tres tasas.

**Ejemplos reales.**

| Tipo | `periodo_inicio` | `periodo_fin` | `renta_cip` | `aporte_codemu` | `fondo_comun` |
|---|---|---|---|---|---|
| `EDIFICACION` | 1900-01-01 | 2026-11-07 | 0.2500 | 0.0500 | 0.1000 |
| `EDIFICACION` | 2026-11-08 | *(abierto)* | 0.0000 | 0.0000 | 0.0000 |
| `HABILITACION_URBANA` | 1900-01-01 | *(abierto)* | 0.2500 | 0.0500 | 0.0000 |
| `IMPACTO_VIAL` | 1900-01-01 | *(abierto)* | 0.0000 | 0.0000 | 0.0000 |
| `INSPECCION_OBRA` | 1900-01-01 | *(abierto)* | 0.0000 | 0.0000 | 0.0000 |
| `MECANICA_SUELOS` | 1900-01-01 | *(abierto)* | 0.1000 | 0.0500 | 0.0000 |
| `TALUDES` | 1900-01-01 | *(abierto)* | 0.0000 | 0.0000 | 0.0000 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

El tipo `EDIFICACION` es el único con dos tramos encadenados: el histórico
1900-01-01 → 2026-11-07 y uno nuevo abierto desde 2026-11-08.

---

### 1.2.10 Especialidades de Liquidaciones

**Propósito.** Es el catálogo que declara **qué especialidades de revisión
están habilitadas para cada tipo de liquidación**, y desde cuándo. Es el
catálogo que gobierna el motor de cálculo por porcentaje: las especialidades
habilitadas determinan cuántas participate en el reparto del subtotal.

| Aspecto | Detalle |
|---|---|
| Modelo | `LiquidacionEspecialidadDisponibles` (tabla `liquidaciones_liquidacionespecialidaddisponibles`) |
| Entrada de administración | `/admin/liquidaciones/liquidacionespecialidaddisponibles/` |
| Ámbito de vigencia | `SCOPE_TIPO_LIQUIDACION_ESPECIALIDAD` |
| Restricción | `exclude_liquidacion_especialidad_disponible_overlap` + `vigencia_rango_valido_liquidacion_especialidad_disponible` |

**Campos de operación.**

| Campo | Tipo | Función |
|---|---|---|
| `tipo_liquidacion_id` | `uuid` → `liquidaciones_tipoliquidacion(id)` | Tipo de liquidación. Borrado protegido por Django (`on_delete=PROTECT`). |
| `especialidad_id` | `uuid` → `usuarios_especialidadrevision(id)` | Especialidad de revisión habilitada. Borrado protegido por Django (`on_delete=PROTECT`). |
| `activo` | `boolean` | Indica si la especialidad está disponible para liquidaciones. |
| `periodo_inicio`, `periodo_fin` | `date` | Vigencia. |

**Relación.** Es el catálogo de **ámbito más fino**: la combinación
`(tipo_liquidacion_id, especialidad_id)` forma su propio ámbito, de modo que
habilitar y deshabilitar una especialidad no interfiere con otro tipo.

**Dónde se administra.** En
`/admin/liquidaciones/liquidacionespecialidaddisponibles/`, con filtrado por
tipo, especialidad y estado activo.

**Ejemplos reales.** Ocho filas habilitadas:

| Tipo | Especialidad | `activo` | `periodo_inicio` | `periodo_fin` |
|---|---|---|---|---|
| `EDIFICACION` | Ingeniería Civil | sí | 2000-01-01 | *(abierto)* |
| `EDIFICACION` | Ingeniería Electrónica | sí | 2000-01-01 | 2026-05-01 |
| `EDIFICACION` | Ingeniería Eléctrica y Mecánica Eléctrica | sí | 2000-01-01 | *(abierto)* |
| `EDIFICACION` | Ingeniería Sanitaria | sí | 2000-01-01 | *(abierto)* |
| `HABILITACION_URBANA` | Ingeniería Civil | sí | 2000-01-01 | *(abierto)* |
| `IMPACTO_VIAL` | Ingeniería Civil | sí | 2000-01-01 | *(abierto)* |
| `MECANICA_SUELOS` | Ingeniería Civil | sí | 2000-01-01 | *(abierto)* |
| `TALUDES` | Ingeniería Civil | sí | 2000-01-01 | *(abierto)* |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

`EDIFICACION` es el único tipo con varias especialidades habilitadas, y
Ingeniería Electrónica es la única con el tramo cerrado: su vigencia termina el
2026-05-01 y no tiene continuidad abierta.

---

## 1.3 Cómo se administran en conjunto

Los diez catálogos se administran desde el **Django admin** de CAM, en la URL
`/admin/`, y el acceso se hace a través del proxy que sirve tanto el admin como
la aplicación.

### El grupo "Vigencias"

El backend reagrupa los catálogos con vigencia en una sección propia del menú
lateral del admin, definida en `backend/core/admin.py`. La sección agrupa, en
este orden, los diez catálogos de este documento:

1. Tarifas Base Porcentuales
2. Tarifas Base por Metro Cuadrado
3. Tarifas Base por Visitas
4. Derechos Mínimos Porcentuales de Obra
5. Derechos Mínimos por Metro Cuadrado
6. IGV
7. UIT
8. Escalas de Descuento del Inspector
9. Tasas de Delegado
10. Especialidades de Liquidaciones

Los modelos con vigencia quedan fuera de sus secciones de módulo originales
para no aparecer duplicados: cada catálogo aparece una sola vez, en "Vigencias".

### El resto de secciones del admin

| Sección | Modelos |
|---|---|
| Liquidación | Liquidaciones, Liquidaciones de Delegado |
| Liquidaciones por Tipo | Un proxy por cada tipo, filtrado por `tipo_liquidacion__codigo` |
| Tarifas y Reglas | Tablas de detalle de tarifas: Tarifas por Categoría de Visitas, Tarifas por Metro Cuadrado, Tarifas Porcentuales de Obra |
| Profesionales | Delegados, Delegados de Operaciones, Inspectores, Inspectores de Operaciones, Proyectistas |
| Catálogos | Tipos de Liquidación, Códigos de Liquidaciones |
| Proyectos | Proyectos |
| RH Inspector | Recibos de Honorarios Mensuales del Inspector, Registros de Pago del Inspector |
| RH Delegado | Recibos de Honorarios del Delegado, Recibos de Honorarios Mensuales del Delegado |
| Repartición Estacional | Reparticiones Estacionales |
| Impuestos y Tasas | IGV, UIT, Tasas de Delegado |
| Descuentos Inspector | Escalas de Descuento del Inspector, Rangos de Descuento del Inspector, Recibos de Honorarios del Inspector |

### Del admin a la pantalla

El frontend **no administra** estos catálogos: los consulta. La pantalla
**Tarifario** (`/liquidaciones/finanzas`) llama a `GET /liquidaciones/tarifas` y
presenta las tarifas agrupadas por tipo de liquidación y por período de
vigencia, distinguiendo visualmente los tramos vigentes de los históricos. El
detalle de cada período muestra el porcentaje de liquidación por especialidad,
el porcentaje de UIT por categoría de visitas y el costo por m².

Esa lectura de solo consulta es la contraparte del admin: el operador configura
en `/admin/`, y el resto del sistema lee el resultado a través de la API y de las
resoluciones de vigencia.

---

## 1.4 Referencia rápida de tablas

| Catálogo | Tabla física | Ámbito | Restricción de no solapamiento |
|---|---|---|---|
| Tarifas Base (3 familias) | `liquidaciones_tarifaliquidacionbase` | Por tipo | `exclude_tarifa_liquidacion_base_overlap` |
| Detalle porcentaje | `liquidaciones_tarifaporcentajeobra` | — | FK `tarifa_base_id` → `liquidaciones_tarifaliquidacionbase(id)`, `on_delete=CASCADE` |
| Detalle m² | `liquidaciones_tarifapormetrocuadrado` | — | UNIQUE `tarifa_base_id` |
| Detalle visitas | `liquidaciones_tarifaporcategoriavisitas` | — | FK `tarifa_base_id` → `liquidaciones_tarifaliquidacionbase(id)` |
| Derechos % Obra | `liquidaciones_derechoporcentajeobra` | Global | `exclude_derecho_porcentaje_obra_overlap` |
| Derechos M² | `liquidaciones_derechopormetrocuadrado` | Global | `exclude_derecho_por_metro_cuadrado_overlap` |
| IGV | `finanzas_igv` | Global | `exclude_igv_overlap` |
| UIT | `finanzas_uit` | Global | `exclude_uit_overlap` |
| Escala de descuento | `finanzas_escaladescuentoinspector` | Global | `exclude_escala_descuento_inspector_overlap` |
| Rangos de la escala | `finanzas_rangodescuentoinspector` | — | `unique_rango_descuento_inspector` |
| Tasa de delegado | `finanzas_tasadelegado` | Por tipo | `exclude_tasa_delegado_overlap` + índice único parcial `unique_tasa_delegado_vigente_por_tipo` |
| Especialidades | `liquidaciones_liquidacionespecialidaddisponibles` | Por tipo y especialidad | `exclude_liquidacion_especialidad_disponible_overlap` |

Además, cada uno de los diez catálogos con vigencia declara en la base el *check
constraint* `vigencia_rango_valido_<catálogo>`
(`CHECK ((periodo_fin IS NULL) OR (periodo_inicio <= periodo_fin))`).

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*
