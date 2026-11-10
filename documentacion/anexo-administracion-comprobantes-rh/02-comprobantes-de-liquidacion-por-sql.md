# 02 - Comprobantes de liquidación por SQL

Documento autocontenido de referencia para **localizar una liquidación** en la
base de datos y **registrar directamente un comprobante de pago** mediante
PostgreSQL, sin pasar por la aplicación.

Cubre el proceso de resolución del objetivo (`CTA + tipo + número + legacy =
false`), el catálogo de CTA, la anatomía física de la tabla de comprobantes con
sus claves foráneas y restricciones, las consultas de solo lectura para resolver
y verificar el objetivo, la plantilla transaccional de inserción y los
 checklists de ejecución y validación.

---

## 2.1 El proceso, confirmado y corregido

El proceso de referencia es:

```
CTA + tipo + número + legacy = false
   → tabla wrapper del tipo (liquidaciones_liquidacion<tipo>)
   → liquidaciones_liquidaciongeneral.id
   → INSERT en liquidaciones_liquidacioncomprobante
```

Los cuatro componentes son necesarios y cada uno hace un trabajo distinto:

| Componente | Para qué sirve | Por qué no basta sin los otros |
|---|---|---|
| **CTA** (`codigo_cta`) | Es el código de cuenta que el operador tiene a la mano. Está en `liquidaciones_liquidacioncodigo`, ligado a un tipo de liquidación. | No es único: el mismo CTA sirve a dos tipos (ver 2.2). |
| **Tipo** (`TipoLiquidacion.codigo`) | Determina **qué tabla wrapper** hay que leer para obtener el número. | Sin él, el número no es interpretable: cada tipo tiene su propio espacio de numeración. |
| **Número** (`numero` de la tabla wrapper) | Es el correlativo de la liquidación dentro de su tipo. | El mismo número existe en los dos universes de origen (ver 2.3). |
| **`legacy = false`** | Descarta las liquidaciones migradas del sistema anterior. | Sin este filtro, el número resuelve a dos filas distintas (ver 2.3). |

### Las tres reglas que hacen que la clave sea única

1. **El número vive en la tabla wrapper del tipo**, no en
   `liquidaciones_liquidaciongeneral`. Cada tipo tiene la suya:
   `liquidaciones_liquidacionedificacion`,
   `liquidaciones_liquidacionhabilitacionurbana`,
   `liquidaciones_liquidacionmecanicasuelos`,
   `liquidaciones_liquidaciontaludes`,
   `liquidaciones_liquidacionimpactovial` y
   `liquidaciones_liquidacioninspeccionobra`. Todas comparten la misma forma:
   `id`, `created_at`, `updated_at`, `numero`, `liquidacion_id`.

2. **`legacy` es un discriminante real dentro del número.** El campo
   `liquidaciones_liquidaciongeneral.legacy` (boolean, NOT NULL, por defecto
   `false`) marca las liquidaciones migradas del sistema anterior. La numeración
   automática, al crear una liquidación nueva, toma el último número **excluyendo**
   las legacy: es el comportamiento de `AutoNumeroModel.get_autonumero_queryset()`
   en `backend/core_application/models.py`, que filtra por
   `autonumero_legacy_lookup = "liquidacion__legacy"` con valor `False`.

3. **La columna `numero` no tiene restricción de unicidad.** En la tabla de
   liquidaciones de Edificación hay 50 765 filas con 50 759 números distintos: los
   6 números del rango 1–6 existen dos veces, una en el universo legacy y otra en
   el no-legacy. El índice sobre `numero` es unbtree **no único**, y la
   restricción `UNIQUE` de cada tabla wrapper está sobre `liquidacion_id`, no
   sobre `numero`.

Por eso la clave de resolución debe llevar los cuatro componentes y debe
validarse con un conteo: **el objetivo tiene que resolver exactamente una fila**.

---

## 2.2 El catálogo de CTA

El CTA se guarda en `liquidaciones_liquidacioncodigo`, con una fila por tipo de
liquidación.

| Columna | Tipo | Restricción |
|---|---|---|
| `id` | `uuid` | PRIMARY KEY |
| `created_at` | `timestamptz` | NOT NULL |
| `updated_at` | `timestamptz` | NOT NULL |
| `codigo_cta` | `varchar(20)` | NOT NULL, **sin unicidad** |
| `tipo_liquidacion_id` | `uuid` | NOT NULL, FK → `liquidaciones_tipoliquidacion(id)`, `DEFERRABLE INITIALLY DEFERRED` (el código la declara con `on_delete=PROTECT`) |

El backend lo resuelve con `get_codigo_cta_map()`, un mapa indexado por
`tipo_liquidacion.codigo`, y lo expone como `codigo_cta` en el payload de la
liquidación. El frontend lo consume como dato de solo lectura y lo renderiza en
el recibo PDF (`CTA: <codigo_cta>`).

### Catálogo actual CTA ↔ tipo

| Tipo (`codigo`) | Nombre | `codigo_cta` |
|---|---|---|
| `EDIFICACION` | Edificacion | 46201 |
| `HABILITACION_URBANA` | Habilitacion Urbana | 70317999 |
| `IMPACTO_VIAL` | Impacto Vial | 7032033 |
| `INSPECCION_OBRA` | Inspeccion Obra | 462021 |
| `MECANICA_SUELOS` | Mecanica Suelos | 70317999 |
| `TALUDES` | Taludes | 7032018 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

### Tratamiento explícito del CTA repetido

`70317999` está asignado a **dos** tipos a la vez: `HABILITACION_URBANA` y
`MECANICA_SUELOS`.

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

Es un caso real y con consecuencias operativas:

- **El CTA por sí solo no es una clave de liquidación.** Es un atributo del
  *tipo*, y el modelo lo refleja en que `codigo_cta` **no** tiene restricción
  `UNIQUE` en la base, a diferencia de `TipoLiquidacion.codigo` y `.nombre`, que
  sí la tienen.
- **Hoy ese CTA solo resuelve números de un tipo.** En los datos actuales de
  desarrollo la tabla wrapper de `MECANICA_SUELOS` está vacía, de modo que las
  1 408 liquidaciones de `HABILITACION_URBANA` (números 2–1535) son la única
  numeración viva de `70317999`. Eso es una característica del conjunto de
  datos, no una garantía del catálogo.
- **Por eso el tipo es un componente obligatorio de la clave.** La clave
  `CTA + tipo` sí es única: cada tipo tiene exactamente un CTA, y cada CTA
  identifica a lo sumo dos tipos.
- **El backend resuelve el CTA desde el tipo, no al revés.** El servicio
  `get_codigo_cta_map()` de
  `modules/liquidaciones/domain/services/core/liquidacion_general/liquidacion_general_core_service.py`
  construye el mapa indexado por `tipo_liquidacion.codigo`, de modo que un CTA
  repetido no genera ambigüedad en la aplicación.

**Consecuencia práctica para el operador:** si se conoce el CTA pero no el tipo,
hay que probar ambos tipos posibles y descartar el que no resuelva a una
liquidación existente. Si se conoce el tipo, el CTA se deduce y no hace falta
aportar.

---

## 2.3 El corte de numeración legacy / no-legacy

### Qué separa a los dos universos

| | Legacy | No legacy |
|---|---|---|
| Campo | `liquidaciones_liquidaciongeneral.legacy = true` | `liquidaciones_liquidaciongeneral.legacy = false` |
| Origen | Migración desde el sistema anterior | Creación en CAM |
| Numeración | Conserva el correlativo histórico del sistema anterior | Numeración automática propia |
| Rango observado en Edificación | 1 … 55200 | 1 … 6 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

El corte está confirmado por el código y por la base de datos:

- **Código.** `AutoNumeroModel.get_autonumero_queryset()` aplica
  `queryset.filter(**{legacy_lookup: False})` cuando el modelo declara
  `autonumero_legacy_lookup`. Los seis modelos wrapper de liquidación
  declaran `autonumero_legacy_lookup = "liquidacion__legacy"`. El efecto es que
  la numeración automática corre en una secuencia separada de la legacy.
- **Base de datos.** La tabla wrapper de Edificación tiene 50 765 filas con
  50 759 números distintos. Los 6 números duplicados son exactamente el rango
  1–6, presente una vez en cada universo.

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

Rangos numéricos por tipo, con el desglose legacy:

| Tipo | Filas legacy | `numero` mínimo | `numero` máximo | Números distintos |
|---|---|---|---|---|
| `EDIFICACION` | 50 759 | 1 | 55200 | 50 759 |
| `HABILITACION_URBANA` | 1 408 | 2 | 1535 | 1 408 |
| `INSPECCION_OBRA` | 9 852 | 2 | 10796 | 9 852 |

Las tres tablas wrapper restantes —`liquidaciones_liquidacionmecanicasuelos`,
`liquidaciones_liquidaciontaludes` y `liquidaciones_liquidacionimpactovial`—
existen con la misma forma y están vacías: no hay ninguna liquidación de esos
tipos en la base de desarrollo.

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

Distribución del universo no-legacy:

| Tipo | Liquidaciones legacy | Liquidaciones no legacy |
|---|---|---|
| `EDIFICACION` | 50 759 | 6 |
| `HABILITACION_URBANA` | 1 408 | 0 |
| `INSPECCION_OBRA` | 9 852 | 8 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

### Por qué el filtro es obligatorio

Un número de liquidación no-legacy puede coincidir con uno legacy **del mismo
tipo**. Por eso una resolución sin el filtro `legacy = false` devuelve dos filas,
y con el filtro devuelve exactamente una.

---

## 2.4 Anatomía física de la tabla de comprobantes

### Tabla y columnas

`liquidaciones_liquidacioncomprobante`, confirmada en `information_schema`:

| Columna | Tipo | Nulo | Notas |
|---|---|---|---|
| `id` | `uuid` | NO | PRIMARY KEY. El modelo lo genera con `uuid.uuid4`. |
| `created_at` | `timestamptz` | NO | `auto_now_add` en el modelo. |
| `updated_at` | `timestamptz` | NO | `auto_now` en el modelo. |
| `tipo_comprobante` | `varchar(20)` | SÍ | `FACTURA`, `BOLETA`, `NOTA_CREDITO` o `NOTA_DEBITO`. Sin `CHECK` en la base: la lista la impone la aplicación. |
| `serie` | `varchar(20)` | SÍ | Serie del comprobante. |
| `numero` | `varchar(50)` | SÍ | Número del comprobante. Es `varchar`, no numérico. |
| `fecha_emision` | `date` | SÍ | Fecha de emisión del comprobante. |
| `monto` | `numeric(12,2)` | SÍ | Importe del comprobante. |
| `activo` | `boolean` | NO | Marca el comprobante vigente de la liquidación. |
| `motivo_reemplazo` | `varchar(500)` | SÍ | Motivo por el que este comprobante reemplazó a otro. |
| `liquidacion_general_id` | `uuid` | NO | FK a la liquidación cabecera. |
| `motivo_actualizacion` | `varchar(500)` | SÍ | Columna nullable adicional del esquema. |

La tabla **no** tiene columna `periodo_inicio` / `periodo_fin`: un comprobante no
tiene vigencia, tiene un flag `activo`.

### Clave foránea

| Constraint | Definición |
|---|---|
| `liquidaciones_liquid_liquidacion_general__3672a219_fk_liquidaci` | `FOREIGN KEY (liquidacion_general_id) REFERENCES liquidaciones_liquidaciongeneral(id) DEFERRABLE INITIALLY DEFERRED` |

La FK es `DEFERRABLE INITIALLY DEFERRED`, de modo que dentro de una transacción
la comprobación se hace al confirmar.

### Restricción de comprobante activo

| Índice | Definición |
|---|---|
| `unique_liquidacion_comprobante_activo` | `CREATE UNIQUE INDEX … ON liquidaciones_liquidacioncomprobante USING btree (liquidacion_general_id) WHERE activo` |

Es un **índice único parcial sobre `activo`**. Su efecto es la regla de
negocio central de esta tabla:

> Una liquidación tiene **muchos** comprobantes en su historial, pero **como
> máximo uno activo**.

Consecuencias:

- Un segundo comprobante con `activo = true` para la misma liquidación es
  **rechazado por la base**. La aplicación lo evita de otra forma: el servicio
  `crear_comprobante()` desactiva primero los activos
  (`liquidacion_general.comprobantes.filter(activo=True).update(activo=False)`)
  y luego crea el nuevo, todo dentro de la misma transacción.
- Un comprobante con `activo = false` es historial y puede haber muchos.

### Restricciones e índices adicionales

| Constraint / índice | Definición |
|---|---|
| `liquidaciones_liquidacioncomprobante_pkey` | `PRIMARY KEY (id)` |
| `liquidaciones_liquidacionc_liquidacion_general_id_3672a219` | `CREATE INDEX … USING btree (liquidacion_general_id)` |

La nulabilidad por columna es la que impone el modelo y la que el motor aplica
como `NOT NULL` nativo: `id`, `created_at`, `updated_at`, `activo` y
`liquidacion_general_id` son obligatorias; el resto admiten `NULL`.

### Estado actual de la tabla

| Métrica | Valor |
|---|---|
| Comprobantes totales | 55 010 |
| Activos | 55 009 |
| Inactivos (historial) | 1 |
| Sin `tipo_comprobante` | 10 111 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

| Tipo de liquidación | Activos | Inactivos |
|---|---|---|
| `EDIFICACION` | 44 598 | 1 |
| `HABILITACION_URBANA` | 1 196 | 0 |
| `INSPECCION_OBRA` | 9 215 | 0 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

El único comprobante no-legacy de la base pertenece a una liquidación de
`EDIFICACION`:

| Tipo | `tipo_comprobante` | `serie` | `numero` | `fecha_emision` | `activo` |
|---|---|---|---|---|---|
| `EDIFICACION` | FACTURA | F01 | C-10211 | 2026-11-04 | sí |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

---

## 2.5 Consultas de solo lectura

Todas las consultas de esta sección son `SELECT` y no modifican datos.

### 2.5.1 Catálogo CTA ↔ tipo

```sql
-- Solo lectura
SELECT t.codigo AS tipo,
       t.nombre,
       c.codigo_cta
FROM liquidaciones_tipoliquidacion t
LEFT JOIN liquidaciones_liquidacioncodigo c
       ON c.tipo_liquidacion_id = t.id
ORDER BY t.codigo;
```

Para localizar los CTA que sirven a más de un tipo:

```sql
-- Solo lectura
SELECT c.codigo_cta,
       count(*) AS veces,
       string_agg(t.codigo, ', ' ORDER BY t.codigo) AS tipos
FROM liquidaciones_liquidacioncodigo c
JOIN liquidaciones_tipoliquidacion t ON t.id = c.tipo_liquidacion_id
GROUP BY c.codigo_cta
HAVING count(*) > 1;
```

### 2.5.2 Resolver el objetivo

Esta es la consulta central. Devuelve **una fila por liquidación que coincide**
con los cuatro componentes, de modo que el conteo es la validación:

```sql
-- Solo lectura
WITH wrappers AS (
    SELECT 'EDIFICACION'::text      AS tipo, numero, liquidacion_id FROM liquidaciones_liquidacionedificacion
    UNION ALL SELECT 'HABILITACION_URBANA', numero, liquidacion_id FROM liquidaciones_liquidacionhabilitacionurbana
    UNION ALL SELECT 'MECANICA_SUELOS',     numero, liquidacion_id FROM liquidaciones_liquidacionmecanicasuelos
    UNION ALL SELECT 'TALUDES',             numero, liquidacion_id FROM liquidaciones_liquidaciontaludes
    UNION ALL SELECT 'IMPACTO_VIAL',        numero, liquidacion_id FROM liquidaciones_liquidacionimpactovial
    UNION ALL SELECT 'INSPECCION_OBRA',     numero, liquidacion_id FROM liquidaciones_liquidacioninspeccionobra
), target AS (
    SELECT w.tipo,
           w.numero,
           lg.id AS liquidacion_general_id,
           lg.legacy,
           lg.estado,
           lg.expediente,
           lg.sub_total,
           lg.total,
           lg.fecha_registro
    FROM wrappers w
    JOIN liquidaciones_liquidaciongeneral lg ON lg.id = w.liquidacion_id
    JOIN liquidaciones_tipoliquidacion tl   ON tl.id = lg.tipo_liquidacion_id
    JOIN liquidaciones_liquidacioncodigo lc ON lc.tipo_liquidacion_id = tl.id
    WHERE w.tipo = :'tipo'
      AND w.numero = :numero
      AND lc.codigo_cta = :'codigo_cta'
      AND lg.legacy = false
)
SELECT * FROM target;
```

**Interpretación del resultado:**

| Filas devueltas | Significado | Acción |
|---|---|---|
| 1 | Objetivo único y correcto | Continuar. |
| 0 | No existe, o el CTA no corresponde a ese tipo, o el número no es no-legacy | Revisar los componentes por separado con 2.5.3 y 2.5.4. |
| > 1 | La clave no discrimina | Descartar: con el filtro `legacy = false` y el CTA por tipo, no debería ocurrir. Revisar si hay dos liquidaciones no-legacy con el mismo número en el mismo tipo. |

### 2.5.3 Consultas de apoyo para resolver

Cuando la resolución devuelve 0 filas, estas consultas acotan el problema:

```sql
-- Solo lectura: el número existe en ese tipo, pero en el universo legacy
SELECT lg.legacy, lg.id AS liquidacion_general_id, lg.estado
FROM liquidaciones_liquidacioninspeccionobra w
JOIN liquidaciones_liquidaciongeneral lg ON lg.id = w.liquidacion_id
WHERE w.numero = :numero
ORDER BY lg.legacy, lg.created_at DESC;
```

```sql
-- Solo lectura: qué CTA(s) tiene asignados el tipo
SELECT t.codigo, c.codigo_cta
FROM liquidaciones_tipoliquidacion t
LEFT JOIN liquidaciones_liquidacioncodigo c ON c.tipo_liquidacion_id = t.id
WHERE t.codigo = :'tipo';
```

```sql
-- Solo lectura: qué números no-legacy existen para ese tipo
SELECT w.numero
FROM liquidaciones_liquidacioninspeccionobra w
JOIN liquidaciones_liquidaciongeneral lg ON lg.id = w.liquidacion_id
WHERE lg.legacy = false
ORDER BY w.numero;
```

### 2.5.4 Verificar el estado de la liquidación objetivo

```sql
-- Solo lectura: la liquidación y su estado
SELECT lg.id, lg.expediente, lg.estado, lg.sub_total, lg.total,
       lg.numero_revision, lg.fecha_registro, lg.eliminado
FROM liquidaciones_liquidaciongeneral lg
WHERE lg.id = :'liquidacion_general_id'::uuid;
```

Los valores admitidos de `estado` son `PENDIENTE` y `PAGADA`
(`EstadoLiquidacion`).

```sql
-- Solo lectura: la liquidación y su detalle por tipo
SELECT 'IO' AS detalle, w.numero, lcv.cantidad_visitas, lcv.categoria, lcv.porcentaje_uit
FROM liquidaciones_liquidacioninspeccionobra w
JOIN liquidaciones_liquidaciongeneral lg ON lg.id = w.liquidacion_id
JOIN liquidaciones_liquidacionporcategoriavisitas lcv ON lcv.liquidacion_general_id = lg.id
WHERE lg.id = :'liquidacion_general_id'::uuid;
```

### 2.5.5 Verificar los comprobantes de la liquidación

```sql
-- Solo lectura: historial completo de comprobantes de la liquidación
SELECT c.id,
       c.tipo_comprobante,
       c.serie,
       c.numero,
       c.fecha_emision,
       c.monto,
       c.activo,
       c.motivo_reemplazo,
       c.created_at
FROM liquidaciones_liquidacioncomprobante c
WHERE c.liquidacion_general_id = :'liquidacion_general_id'::uuid
ORDER BY c.activo DESC, c.created_at DESC;
```

```sql
-- Solo lectura: ¿existe ya un comprobante activo? (debe devolver 0 filas)
SELECT c.id, c.tipo_comprobante, c.serie, c.numero, c.fecha_emision, c.monto
FROM liquidaciones_liquidacioncomprobante c
WHERE c.liquidacion_general_id = :'liquidacion_general_id'::uuid
  AND c.activo;
```

### 2.5.6 Comprobar la restricción de unicidad del activo

```sql
-- Solo lectura: inventario de comprobantes activos por liquidación
-- debe devolver una sola fila por liquidacion_general_id
SELECT liquidacion_general_id, count(*) AS activos
FROM liquidaciones_liquidacioncomprobante
WHERE activo
GROUP BY liquidacion_general_id
HAVING count(*) > 1;
```

Esta consulta devuelve **0 filas** mientras el índice único parcial esté
satisfecho. Es el control previo que replica la condición de la base.

---

## 2.6 Plantilla SQL de alta de comprobante

> **Inserción.** Los dos bloques de esta sección son los únicos del documento que
> escriben datos. Están pensados para ejecutarse con `psql` y variables `-v`, de
> forma que los valores concretos no quedan escritos en el script.

### Parámetros

| Parámetro | Tipo | Significado |
|---|---|---|
| `:codigo_cta` | texto | CTA del tipo objetivo. |
| `:tipo` | texto | Código del tipo (`EDIFICACION`, `HABILITACION_URBANA`, `MECANICA_SUELOS`, `TALUDES`, `IMPACTO_VIAL`, `INSPECCION_OBRA`). |
| `:numero` | entero | Número de la liquidación dentro de su tipo. |
| `:tipo_comprobante` | texto | `FACTURA`, `BOLETA`, `NOTA_CREDITO` o `NOTA_DEBITO`. |
| `:serie` | texto | Serie del comprobante. |
| `:numero_comprobante` | texto | Número del comprobante. |
| `:fecha_emision` | `YYYY-MM-DD` | Fecha de emisión. |
| `:monto` | numérico | Importe, con 2 decimales. |

### Script

```sql
-- Variables de entrada (psql -v)
--   psql -X -v ON_ERROR_STOP=1 \
--        -v codigo_cta=462021 -v tipo=INSPECCION_OBRA -v numero=3 \
--        -v tipo_comprobante=FACTURA -v serie=F001 -v numero_comprobante=000123 \
--        -v fecha_emision=2026-11-09 -v monto=1908.06 \
--        -f alta_comprobante.sql

\set codigo_cta '462021'
\set tipo 'INSPECCION_OBRA'
\set numero '3'
\set tipo_comprobante 'FACTURA'
\set serie 'F001'
\set numero_comprobante '000123'
\set fecha_emision '2026-11-09'
\set monto '1908.06'

\echo '=== PASO 1: RESOLUCION DEL TARGET (solo lectura) ==='
WITH wrappers AS (
    SELECT 'EDIFICACION'::text      AS tipo, numero, liquidacion_id FROM liquidaciones_liquidacionedificacion
    UNION ALL SELECT 'HABILITACION_URBANA', numero, liquidacion_id FROM liquidaciones_liquidacionhabilitacionurbana
    UNION ALL SELECT 'MECANICA_SUELOS',     numero, liquidacion_id FROM liquidaciones_liquidacionmecanicasuelos
    UNION ALL SELECT 'TALUDES',             numero, liquidacion_id FROM liquidaciones_liquidaciontaludes
    UNION ALL SELECT 'IMPACTO_VIAL',        numero, liquidacion_id FROM liquidaciones_liquidacionimpactovial
    UNION ALL SELECT 'INSPECCION_OBRA',     numero, liquidacion_id FROM liquidaciones_liquidacioninspeccionobra
), target AS (
    SELECT w.tipo, w.numero, lg.id AS liquidacion_general_id, lg.legacy, lg.estado, lg.total
    FROM wrappers w
    JOIN liquidaciones_liquidaciongeneral lg ON lg.id = w.liquidacion_id
    JOIN liquidaciones_tipoliquidacion tl   ON tl.id = lg.tipo_liquidacion_id
    JOIN liquidaciones_liquidacioncodigo lc ON lc.tipo_liquidacion_id = tl.id
    WHERE w.tipo = :'tipo'
      AND w.numero = :numero
      AND lc.codigo_cta = :'codigo_cta'
      AND lg.legacy = false
)
SELECT (SELECT count(*) FROM target)                            AS filas_encontradas,
       (SELECT count(*) FROM target WHERE legacy)               AS legacy_encontradas,
       (SELECT liquidacion_general_id::text FROM target LIMIT 1) AS liquidacion_general_id,
       (SELECT estado FROM target LIMIT 1)                      AS estado,
       (SELECT total FROM target LIMIT 1)                      AS total
\gset

SELECT (:filas_encontradas = 1) AS ok_unico,
       (:legacy_encontradas = 0) AS ok_no_legacy
\gset

\if :ok_unico
\else
  \echo 'ABORT: el objetivo (CTA + tipo + numero + legacy=false) no es unico o no existe.'
  \quit
\endif
\if :ok_no_legacy
\else
  \echo 'ABORT: el objetivo resuelve a una liquidacion legacy.'
  \quit
\endif

\echo '=== PASO 2: GUARDA DE COMPROBANTE ACTIVO (solo lectura) ==='
SELECT count(*) AS comprobantes_activos
FROM liquidaciones_liquidacioncomprobante c
WHERE c.liquidacion_general_id = :'liquidacion_general_id'::uuid
  AND c.activo
\gset

SELECT (:comprobantes_activos = 0) AS ok_sin_activo
\gset

\if :ok_sin_activo
\else
  \echo 'ABORT: ya existe un comprobante activo para esta liquidacion.'
  \quit
\endif

\echo '=== PASO 3: ALTA TRANSACCIONAL ==='
BEGIN;
INSERT INTO liquidaciones_liquidacioncomprobante (
    id, created_at, updated_at,
    tipo_comprobante, serie, numero, fecha_emision, monto,
    activo, motivo_reemplazo, liquidacion_general_id
)
SELECT gen_random_uuid(),
       now(),
       now(),
       :'tipo_comprobante',
       :'serie',
       :'numero_comprobante',
       :'fecha_emision'::date,
       :'monto'::numeric(12,2),
       true,
       NULL,
       :'liquidacion_general_id'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM liquidaciones_liquidacioncomprobante c
    WHERE c.liquidacion_general_id = :'liquidacion_general_id'::uuid AND c.activo
);
COMMIT;
```

### Qué garantiza cada paso

| Paso | Guarda |
|---|---|
| 1 | El objetivo resuelve a **exactamente una** liquidación no-legacy. Si no, el script aborta con `\quit` antes de escribir. |
| 2 | **No hay ya un comprobante activo** para esa liquidación. Si lo hay, el script aborta. |
| 3 | La inserción se hace dentro de `BEGIN` … `COMMIT`. El `WHERE NOT EXISTS` repite la guarda del paso 2 en el propio `INSERT`, de modo que la condición se evalúa con el estado de la base en el momento de la escritura y no solo con el de la lectura anterior. |

El índice único parcial `unique_liquidacion_comprobante_activo` es la última
línea de defensa: si dos ejecuciones concurrentes intentaran insertar un
comprobante activo para la misma liquidación, la segunda fallaría por
violación de unicidad y su transacción se revertiría.

### Variante de reemplazo

Cuando la liquidación ya tiene un comprobante activo y lo que se quiere es
**sustituirlo**, el orden que usa la aplicación es: desactivar el anterior y
luego insertar el nuevo. La variante equivalente por SQL, con la misma semántica,
es:

```sql
-- Inserción (reemplazo): desactiva el activo previo y da de alta el nuevo.
BEGIN;

UPDATE liquidaciones_liquidacioncomprobante
   SET activo = false,
       updated_at = now(),
       motivo_reemplazo = :'motivo_reemplazo'
 WHERE liquidacion_general_id = :'liquidacion_general_id'::uuid
   AND activo;

INSERT INTO liquidaciones_liquidacioncomprobante (
    id, created_at, updated_at,
    tipo_comprobante, serie, numero, fecha_emision, monto,
    activo, motivo_reemplazo, liquidacion_general_id
)
SELECT gen_random_uuid(),
       now(),
       now(),
       :'tipo_comprobante',
       :'serie',
       :'numero_comprobante',
       :'fecha_emision'::date,
       :'monto'::numeric(12,2),
       true,
       :'motivo_reemplazo',
       :'liquidacion_general_id'::uuid
WHERE NOT EXISTS (
    SELECT 1 FROM liquidaciones_liquidacioncomprobante c
    WHERE c.liquidacion_general_id = :'liquidacion_general_id'::uuid AND c.activo
);

COMMIT;
```

El comprobante anterior permanece en la tabla con `activo = false` y su
`motivo_reemplazo` original intacto; el nuevo queda como el único activo.

---

## 2.7 Checklist de ejecución previa

Antes de ejecutar la plantilla:

1. **El CTA está confirmado contra el tipo.** Consultar 2.5.1 y verificar que
   `codigo_cta` corresponde al tipo que se está usando. Recordar que `70317999`
   sirve a dos tipos.
2. **El número está confirmado en el universo no-legacy.** Consultar 2.5.2 y
   confirmar que devuelve **exactamente una fila**.
3. **El estado de la liquidación es el esperado.** Consultar 2.5.4. Una
   liquidación en `PAGADA` o con `eliminado = true` no debe recibir un
   comprobante nuevo por esta vía.
4. **No hay ya un comprobante activo.** Consultar 2.5.5: la consulta de activos
   debe devolver 0 filas.
5. **La base no tiene comprobantes activos duplicados.** Consultar 2.5.6: debe
   devolver 0 filas.
6. **Los parámetros están completos y con el formato esperado**: `fecha_emision`
   en `YYYY-MM-DD`, `monto` con 2 decimales, `tipo_comprobante` con uno de los
   cuatro valores admitidos, `numero_comprobante` como texto.
7. **La conexión apunta a la base correcta**, verificada con `SELECT
   current_database();`.

## 2.8 Checklist de validación posterior

Después de ejecutar la plantilla:

1. **El comprobante existe y está activo.** Consultar 2.5.5: debe aparecer la
   fila con `activo = true` y los valores esperados.
2. **Sigue habiendo un solo comprobante activo.** Consultar 2.5.6: debe
   devolver 0 filas.
3. **El detalle de la liquidación es el esperado.** Consultar 2.5.4 para
   confirmar que el `total` de la liquidación no se vio alterado por el alta.
4. **El conteo total de comprobantes aumentó en uno**, y el de activos también
   en uno.
5. **Si se usó la variante de reemplazo**, el comprobante anterior debe seguir
   presente con `activo = false` y el motivo de reemplazo informado.

---

## 2.9 Vías de la aplicación, para contraste

La aplicación registra comprobantes por API, no por SQL directo. La diferencia
relevante para un operador es que **la API desactiva el comprobante activo
anterior** de forma automática, mientras que la plantilla de alta simple exige
que no exista uno.

| Vía | Endpoint | Comportamiento |
|---|---|---|
| Alta o reemplazo | `POST /api/liquidaciones/generales/{liquidacion_id}/comprobante` | Desactiva el activo previo y crea el nuevo activo. Acepta `tipo_comprobante`, `serie`, `numero`, `fecha_emision`, `monto` y `motivo_reemplazo`. |
| Edición en sitio | `PATCH /api/liquidaciones/generales/{liquidacion_id}/comprobante/{comprobante_id}` | Actualiza el comprobante **activo** en la misma fila: no desactiva, no crea, no incrementa el historial y no admite `monto`. |
| Marcar pagada | `POST /api/liquidaciones/generales/{liquidacion_id}/marcar-pagada` | Transiciona `PENDIENTE` → `PAGADA`. Es idempotente. |

En el frontend, el alta, el reemplazo y la edición se hacen desde un único modal,
`ComprobanteFormModal`, que decide internamente qué operación ofrece según el
estado del comprobante activo. El botón que lo abre es *Gestionar comprobante*,
presente en la tarjeta de cada liquidación y en las vistas de listado por tipo.
La tarjeta muestra el comprobante activo con su tipo, serie, número, monto y
fecha de emisión; el modal no pide `monto` en ningún modo, porque el backend lo
preserva.
