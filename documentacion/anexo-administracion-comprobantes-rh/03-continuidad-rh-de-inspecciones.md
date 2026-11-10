# 03 - Continuidad RH de inspectores

Este documento explica **cómo se controla el saldo de visitas** de una liquidación
de Inspección de Obra a lo largo de los meses, **cómo se registran visitas
históricas** y **qué consultas de diagnóstico** sirven para seguir el estado.

Cubre las tablas físicas y sus claves foráneas, la aritmética del saldo, el
mecanismo que impide superarlo, las consultas SQL de solo lectura para
diagnóstico y el procedimiento operativo para registrar visitas.

---

## 3.1 Las piezas del saldo

El saldo de visitas de una IO no está almacenado en ningún campo. Es el resultado
de restar dos cosas que sí están almacenadas:

| Pieza | Dónde vive | Qué representa |
|---|---|---|
| **Visitas programadas** | `liquidaciones_liquidacionporcategoriavisitas.cantidad_visitas` | Cuántas visitas de inspección se contrató para esa liquidación. |
| **Visitas pagadas** | `finanzas_registropagoinspector.inspecciones_pagadas` | Cuántas visitas ya se pagaron, por período. |

Y de la resta sale:

```
saldo disponible = visitas programadas − visitas pagadas acumuladas
```

### Tabla de visitas programadas

`liquidaciones_liquidacionporcategoriavisitas`, una fila por liquidación de
Inspección de Obra.

| Columna | Tipo | Nulo | Restricción |
|---|---|---|---|
| `id` | `uuid` | NO | PRIMARY KEY |
| `created_at` | `timestamptz` | NO | — |
| `updated_at` | `timestamptz` | NO | — |
| `cantidad_visitas` | `integer` | NO | `CHECK (cantidad_visitas >= 0)` |
| `porcentaje_uit` | `numeric(5,4)` | SÍ | Fracción de UIT por visita aplicada. |
| `categoria` | `varchar(20)` | SÍ | Categoría de inspección. |
| `liquidacion_general_id` | `uuid` | NO | FK → `liquidaciones_liquidaciongeneral(id)`, `DEFERRABLE INITIALLY DEFERRED` |
| `tarifa_aplicada_id` | `uuid` | SÍ | FK → `liquidaciones_tarifaporcategoriavisitas(id)`, `DEFERRABLE INITIALLY DEFERRED` |

La relación con la liquidación es por `liquidacion_general_id`, y el accessor en
el modelo es `liquidacion_visitas` sobre `LiquidacionGeneral`.

La tabla de asignaciones `liquidaciones_liquidacioninspector` es la que enlaza
cada IO con su inspector. Sus columnas `liquidacion_id` (FK →
`liquidaciones_liquidacionporcategoriavisitas(id)`), `inspector_id`,
`inspector_operacion_id` y `especialidad_revision_id` completan el vínculo, y
las restricciones que la gobiernan son:

| Restricción | Definición |
|---|---|
| `unique_liquidacion_inspector` | `UNIQUE (liquidacion_id, inspector_id)` — un inspector no se asigna dos veces a la misma IO. |
| `liquidacion_inspector_mes_valid` | `CHECK ((mes IS NULL) OR ((mes >= 1) AND (mes <= 12)))` |
| `liquidaciones_liquidacioninspector_periodo_check` | `CHECK ((periodo >= 0))` |
| `liquidaciones_liquidacioninspector_mes_check` | `CHECK ((mes >= 0))` |

### Tabla del libro de pagos

`finanzas_registropagoinspector`, una fila por evento de pago de una IO en un
período.

| Columna | Tipo | Nulo | Restricción |
|---|---|---|---|
| `id` | `uuid` | NO | PRIMARY KEY |
| `created_at` | `timestamptz` | NO | — |
| `updated_at` | `timestamptz` | NO | — |
| `periodo` | `smallint` | SÍ | `CHECK (periodo >= 0)` — año del período (1900–2100 en el modelo). |
| `mes` | `smallint` | SÍ | `CHECK (mes >= 0)` — mes 1–12 en el modelo. |
| `inspecciones_pagadas` | `integer` | NO | Número de visitas pagadas en este evento. |
| `fecha_registro` | `date` | SÍ | Fecha en que se registró el pago. |
| `liquidacion_por_categoria_visitas_id` | `uuid` | NO | FK → `liquidaciones_liquidacionporcategoriavisitas(id)`, `DEFERRABLE INITIALLY DEFERRED`; el código la declara con `on_delete=PROTECT` |
| `recibo_mensual_id` | `uuid` | SÍ | FK → `finanzas_recibohonorarioinspectormensual(id)`, `DEFERRABLE INITIALLY DEFERRED`; el código la declara con `on_delete=CASCADE` |

El `recibo_mensual_id` es el vínculo con el RH mensual que originó el pago. Es
nullable a propósito: un pago puede existir sin recibo asociado (por ejemplo,
cuando el registro es previo a la creación del recibo) y esa fila con FK nula
**no se borra** al eliminar el RH, porque el borrado en cascada solo alcanza a las
filas que lo referencian.

### Tablas del RH mensual

`finanzas_recibohonorarioinspectormensual` es la cabecera del recibo:

| Columna | Tipo | Nulo |
|---|---|---|
| `id` | `uuid` | NO |
| `numero` | `integer` | SÍ |
| `periodo` | `smallint` | SÍ (`CHECK (periodo >= 0)`) |
| `mes` | `smallint` | SÍ (`CHECK (mes >= 0)`) |
| `fecha_registro` | `timestamptz` | NO |
| `sub_total` | `numeric(12,2)` | NO |
| `descuento` | `numeric(12,2)` | NO |
| `honorarios` | `numeric(12,2)` | NO |
| `tasa_descuento` | `numeric(7,6)` | SÍ |
| `escala_descuento_id` | `uuid` | NO — FK → `finanzas_escaladescuentoinspector(id)` |
| `inspector_id` | `uuid` | NO — FK → `liquidaciones_inspector(id)` |
| `inspector_operacion_id` | `uuid` | SÍ — FK → `liquidaciones_inspectoroperacion(id)` |

`finanzas_detallehonorarioinspector` es el detalle, una fila por liquidación
dentro del recibo:

| Columna | Tipo | Nulo |
|---|---|---|
| `id` | `uuid` | NO |
| `recibo_mensual_id` | `uuid` | SÍ — FK → `finanzas_recibohonorarioinspectormensual(id)`, `ON DELETE CASCADE` |
| `liquidacion_por_categoria_visitas_id` | `uuid` | NO — FK → `liquidaciones_liquidacionporcategoriavisitas(id)`, `ON DELETE PROTECT` |
| `escala_descuento_id` | `uuid` | SÍ — FK → `finanzas_escaladescuentoinspector(id)` |
| `inspecciones_liquidadas` | `integer` | NO |
| `inspecciones_programadas` | `integer` | SÍ |
| `inspecciones_pagadas_hasta_mes_anterior` | `integer` | SÍ |
| `costo_por_inspeccion` | `numeric(12,2)` | NO |
| `monto_contribuido` | `numeric(12,2)` | NO |
| `importe_bruto` | `numeric(12,2)` | SÍ |
| `saldo_restante` | `numeric(12,2)` | SÍ |
| `sub_total`, `descuento`, `honorarios` | `numeric(12,2)` | SÍ |
| `tasa_descuento` | `numeric(7,6)` | SÍ |

El detalle es una **fotografía del cálculo**: guarda las visitas programadas, las
liquidadas, el costo por inspección y el saldo restante tal como quedaron al
crear o reeditar el recibo.

---

## 3.2 La aritmética del saldo

### Cómo se acumula el pagado

El saldo disponible de una IO en un período dado se calcula sumando las visitas
pagadas de **todos los períodos anteriores**, más las del período actual hasta
el mes que se está liquidando. El filtro es:

```sql
---periodo < :periodo
OR (periodo = :periodo AND mes <= :mes)
```

Este filtro aparece en dos lugares del backend, con el mismo criterio:

1. `FinanzasCoreService.list_liquidaciones_inspector_candidatas()` — arma la
   lista de candidatas del RH mensual con su `saldo_disponible`.
2. `RHInspectorMensualCotizarFlujo.cotizar()` — valida la cantidad que se
   quiere liquidar.

La razón de incluir el mes actual en la suma es preventiva: si ya existe un
`RegistroPagoInspector` para ese período, la visita se cuenta como pagada y no
se puede volver a liquidar.

### Las dos validaciones que impiden superar el saldo

En `rh_inspector_mensual_flujo.py`, la cotización de cada ítem comprueba:

| Validación | Error |
|---|---|
| `cantidad_visitas <= saldo_disponible` | 400 — *"La cantidad de visitas (N) excede el saldo disponible (M) para 'EXP'"* |
| `cantidad_visitas <= programas` | 400 — *"La cantidad de visitas (N) excede las inspecciones programadas (P) para 'EXP'"* |

Donde `saldo_disponible = programas − pagadas_hasta_mes_anterior`. Las dos
comprobaciones son necesarias: la primera impide consumir más de lo que queda,
la segunda impide consumir más de lo que se contrató.

El frontend replica ambas guardas en el wizard de RH, en
`RhInspectorMensualModal.tsx`: rechaza la selección si `cantidad_visitas <= 0`
o si `cantidad_visitas > saldo_disponible`, y exige `periodo` con formato `YYYY`
y `mes` entre 1 y 12.

### El marcador de período en la asignación

`liquidaciones_liquidacioninspector` (la asignación de un inspector a una IO)
tiene columnas `periodo` y `mes`, que funcionan como **marcador de última
liquidación**. Cuando el RH mensual se crea, cada asignación afectada se
actualiza con el período y mes de su ítem
(`update_liquidacion_inspector_periodo_mes()`), y al borrar un RH se recalculan
desde el libro de pagos restante
(`recalcular_marcadores_periodo_inspector()`).

---

## 3.3 Dónde se registran las visitas

### La vía principal: el wizard de RH mensual

La pantalla **RH Mensual de Inspectores** (`/liquidaciones/recibos-inspectores/mensual`)
abre el wizard `RhInspectorMensualModal`, que es el camino ordinario para
registrar visitas ya realizadas.

El flujo tiene cuatro pasos:

1. **CIF** — se selecciona el inspector.
2. **Periodo** — se indica el año y el mes del RH.
3. **Liquidaciones** — el browse lista las candidatas del inspector con su
   `saldo_disponible`, y el operador marca cuántas visitas liquidó cada una.
4. **Resumen** — se revisa el total, el descuento de la escala y los honorarios,
   y se crea el recibo.

Los endpoints que consume, todos bajo `/api/finanzas/recibos-inspectores`:

| Endpoint | Uso |
|---|---|
| `GET /candidatos?cip=…&periodo=…` | Lista las IOs candidatas con `cantidad_visitas`, `inspecciones_pagadas` y `saldo_disponible`. |
| `GET /operatividades?cip=…` | Lista las operatividades del inspector, actuales, históricas o ambas. |
| `POST /cotizar` | Calcula el RH sin persistir. |
| `POST /crear` | Crea la cabecera, los detalles y el libro de pagos, en una sola transacción. |
| `GET /finanzas/recibos-inspectores` | Lista los recibos mensuales, con filtros por inspector, período y mes. |
| `GET /finanzas/recibos-inspectores/detalle` | Detalle de un RH. |
| `PATCH /finanzas/recibos-inspectores/{rh_id}` | Sincroniza el conjunto final de detalles. |
| `POST /finanzas/recibos-inspectores/{rh_id}/cotizar` | Recotiza una edición. |
| `DELETE /finanzas/recibos-inspectores/{id}/eliminar` | Elimina el RH y revierte sus pagos. |

Cuando el wizard crea el recibo, por cada ítem seleccionado escribe **tres
filas**: el `DetalleHonorarioInspector`, el `RegistroPagoInspector` (con
`periodo`, `mes` e `inspecciones_pagadas`) y la actualización del marcador de
período en la asignación. Todo dentro de la misma transacción.

El wizard **exporta** el resumen del RH a un archivo `.xlsx` al final. La carga
masiva de liquidaciones históricas, por su parte, es una operación de backend:
los comandos `import_legacy_inspeccion_obra` e `import_legacy_edificaciones`
siembran el `DetalleHonorarioInspector` de forma idempotente.

### La vía de registro histórico: el admin de liquidaciones

Para **registrar visitas que ya se realizaron y que no forman parte de un RH
mensual** — el caso de continuidad: meses antiguos que nunca se liquidaron — la
vía es el **Django admin**.

En la pantalla de **Liquidaciones de Inspección de Obra**
(`/admin/liquidaciones/liquidacioninspeccionobraproxy/`) cada liquidación tiene
un inline **Registros de visitas** (`RegistroPagoInspectorInline`), que permite
añadir filas del libro de pagos directamente sobre la liquidación:

| Campo del inline | Tipo | Uso |
|---|---|---|
| `periodo` | Año | Período al que se asigna la visita. |
| `mes` | 1–12 | Mes del período. |
| `inspecciones_pagadas` | Entero | Número de visitas a registrar. |
| `fecha_registro` | Solo lectura | Se autocompleta con la fecha del día si se deja vacía. |
| `recibo_mensual` | Solo lectura | Se autocompleta con el RH mensual cuando el registro proviene del wizard. |

El inline tiene tres guardas propias, implementadas en
`RegistroPagoInspectorFormSet`:

1. **No se admiten períodos futuros.** El inline compara `(periodo, mes)` con
   la fecha de hoy y rechaza la fila con *"No se pueden registrar visitas en un
   período futuro."*
2. **El total no puede superar las programadas.** La suma de
   `inspecciones_pagadas` de todas las filas del formset se compara con
   `cantidad_visitas` de la liquidación y, si lo excede, se aborta con
   *"Las inspecciones pagadas (N) superan las programadas (P)."*
3. **Las filas no se pueden borrar desde el inline** (`can_delete = False`) ni
   modificarse (`has_change_permission` devuelve `False`): el inline es solo de
   alta.

El mismo modelo tiene su propio listado en
`/admin/finanzas/registropagoinspector/`, con `periodo` y `mes` como filtros y
búsqueda por el expediente de la liquidación.

---

## 3.4 Consultas SQL de diagnóstico

Todas las consultas de esta sección son `SELECT`.

### 3.4.1 Saldo de una IO concreta

```sql
-- Solo lectura: programadas, pagadas y saldo de una IO
SELECT lcv.id                          AS liquidacion_categoria_visitas_id,
       lcv.cantidad_visitas           AS programadas,
       COALESCE(SUM(r.inspecciones_pagadas), 0) AS pagadas_total,
       lcv.cantidad_visitas - COALESCE(SUM(r.inspecciones_pagadas), 0) AS saldo
FROM liquidaciones_liquidacionporcategoriavisitas lcv
LEFT JOIN finanzas_registropagoinspector r
       ON r.liquidacion_por_categoria_visitas_id = lcv.id
WHERE lcv.id = :'liquidacion_categoria_visitas_id'::uuid
GROUP BY lcv.id, lcv.cantidad_visitas;
```

### 3.4.2 Saldo acumulado hasta un período concreto

Este es el cálculo que replica el del backend: suma los pagos de períodos
anteriores y los del período actual hasta el mes indicado.

```sql
-- Solo lectura: saldo disponible en un (periodo, mes)
WITH lcv AS (
    SELECT id, cantidad_visitas
    FROM liquidaciones_liquidacionporcategoriavisitas
    WHERE id = :'liquidacion_categoria_visitas_id'::uuid
)
SELECT lcv.id AS liquidacion_categoria_visitas_id,
       lcv.cantidad_visitas AS programadas,
       COALESCE(SUM(r.inspecciones_pagadas), 0) AS pagadas_hasta_el_mes,
       lcv.cantidad_visitas - COALESCE(SUM(r.inspecciones_pagadas), 0) AS saldo_disponible
FROM lcv
LEFT JOIN finanzas_registropagoinspector r
       ON r.liquidacion_por_categoria_visitas_id = lcv.id
      AND (r.periodo < :periodo OR (r.periodo = :periodo AND r.mes <= :mes))
GROUP BY lcv.id, lcv.cantidad_visitas;
```

### 3.4.3 Libro de pagos completo de una IO

```sql
-- Solo lectura: historial de pagos de una IO
SELECT r.id, r.periodo, r.mes, r.inspecciones_pagadas, r.fecha_registro,
       r.recibo_mensual_id, rh.numero AS numero_rh
FROM finanzas_registropagoinspector r
LEFT JOIN finanzas_recibohonorarioinspectormensual rh ON rh.id = r.recibo_mensual_id
WHERE r.liquidacion_por_categoria_visitas_id = :'liquidacion_categoria_visitas_id'::uuid
ORDER BY r.periodo, r.mes;
```

### 3.4.4 IOs sin saldo, por inspector

```sql
-- Solo lectura: candidatas de un inspector con su saldo, para un periodo
SELECT li.id                       AS liquidacion_inspector_id,
       lcv.id                     AS liquidacion_categoria_visitas_id,
       lcv.cantidad_visitas       AS programadas,
       COALESCE(SUM(r.inspecciones_pagadas), 0) AS pagadas,
       lcv.cantidad_visitas - COALESCE(SUM(r.inspecciones_pagadas), 0) AS saldo_disponible
FROM liquidaciones_liquidacioninspector li
JOIN liquidaciones_liquidacionporcategoriavisitas lcv ON lcv.id = li.liquidacion_id
LEFT JOIN finanzas_registropagoinspector r
       ON r.liquidacion_por_categoria_visitas_id = lcv.id
      AND (r.periodo < :periodo OR (r.periodo = :periodo AND r.mes <= :mes))
WHERE li.inspector_id = :'inspector_id'::uuid
GROUP BY li.id, lcv.id, lcv.cantidad_visitas
HAVING lcv.cantidad_visitas - COALESCE(SUM(r.inspecciones_pagadas), 0) > 0
ORDER BY saldo_disponible DESC;
```

### 3.4.5 Asignaciones sin marcador de período

```sql
-- Solo lectura: asignaciones que nunca se han liquidado
SELECT li.id,
       li.liquidacion_id,
       lcv.cantidad_visitas,
       li.periodo,
       li.mes
FROM liquidaciones_liquidacioninspector li
JOIN liquidaciones_liquidacionporcategoriavisitas lcv ON lcv.id = li.liquidacion_id
WHERE li.periodo IS NULL OR li.mes IS NULL
ORDER BY li.id;
```

### 3.4.6 Control de integridad: pagos que exceden lo programado

```sql
-- Solo lectura: IOs donde lo pagado supera lo programado
SELECT lcv.id AS liquidacion_categoria_visitas_id,
       lcv.cantidad_visitas AS programadas,
       SUM(r.inspecciones_pagadas) AS pagadas,
       SUM(r.inspecciones_pagadas) - lcv.cantidad_visitas AS exceso
FROM liquidaciones_liquidacionporcategoriavisitas lcv
JOIN finanzas_registropagoinspector r
     ON r.liquidacion_por_categoria_visitas_id = lcv.id
GROUP BY lcv.id, lcv.cantidad_visitas
HAVING SUM(r.inspecciones_pagadas) > lcv.cantidad_visitas;
```

### 3.4.7 IOs de Inspección de Obra sin liquidar

```sql
-- Solo lectura: liquidaciones de IO sin ningún detalle de honorario
SELECT i.numero,
       lg.id AS liquidacion_general_id,
       lg.estado,
       lcv.cantidad_visitas AS programadas,
       lcv.categoria
FROM liquidaciones_liquidacioninspeccionobra i
JOIN liquidaciones_liquidaciongeneral lg ON lg.id = i.liquidacion_id
JOIN liquidaciones_liquidacionporcategoriavisitas lcv ON lcv.liquidacion_general_id = lg.id
LEFT JOIN finanzas_detallehonorarioinspector d
     ON d.liquidacion_por_categoria_visitas_id = lcv.id
WHERE d.id IS NULL
ORDER BY i.numero;
```

### 3.4.8 Detalle de honorarios de una IO

```sql
-- Solo lectura: snapshots de cálculo guardados para una IO
SELECT d.id,
       d.recibo_mensual_id,
       d.inspecciones_programadas,
       d.inspecciones_liquidadas,
       d.inspecciones_pagadas_hasta_mes_anterior,
       d.costo_por_inspeccion,
       d.monto_contribuido,
       d.sub_total,
       d.descuento,
       d.honorarios,
       d.tasa_descuento
FROM finanzas_detallehonorarioinspector d
WHERE d.liquidacion_por_categoria_visitas_id = :'liquidacion_categoria_visitas_id'::uuid
ORDER BY d.created_at;
```

---

## 3.5 Estado actual de los datos

| Métrica | Valor |
|---|---|
| IOs con visitas programadas (`liquidaciones_liquidacionporcategoriavisitas`) | 9 860 |
| Asignaciones de inspector (`liquidaciones_liquidacioninspector`) | 9 868 |
| Detalles de honorario de inspector | 9 849 |
| Registros de pago (`finanzas_registropagoinspector`) | 0 |
| Recibos de honorario mensual de inspector | 0 |
| Operatividades de inspector (`liquidaciones_inspectoroperacion`) | 248 |
| Asignaciones sin marcador de período | 9 868 |
| IOs sin detalle de honorario | 11 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

### Distribución de visitas programadas

| Métrica | Valor |
|---|---|
| Filas | 9 860 |
| Mínimo | 1 |
| Máximo | 214 |
| Promedio | 11,58 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

| `categoria` | Filas | Mínimo | Máximo |
|---|---|---|---|
| 4 | 3 096 | 1 | 214 |
| 3 | 3 066 | 1 | 174 |
| *(sin categoría)* | 1 834 | 1 | 198 |
| 2 | 1 424 | 1 | 66 |
| 1 | 416 | 1 | 200 |
| C3 | 10 | 2 | 36 |
| C4 | 8 | 6 | 40 |
| C1 | 3 | 2 | 29 |
| C2 | 3 | 6 | 9 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

Las categorías con prefijo `C` y las vacías provienen de la carga histórica; las
que usa el motor actual son las numéricas 1 a 4, que coinciden con las
`categoria_visitas` del tarifario de visitas.

### Saldo de las IOs no-legacy

Las ocho liquidaciones de Inspección de Obra no-legacy, con sus visitas
programadas y sus importes:

| `numero` | `cantidad_visitas` | `categoria` | `porcentaje_uit` | `sub_total` | `total` | `estado` |
|---|---|---|---|---|---|---|
| 1 | 3 | 3 | 0.0420 | 693.00 | 817.74 | PENDIENTE |
| 2 | 1 | 4 | 0.0880 | 484.00 | 571.12 | PENDIENTE |
| 3 | 7 | 3 | 0.0420 | 1 617.00 | 1 908.06 | PENDIENTE |
| 4 | 31 | 3 | 0.0420 | 7 161.00 | 8 449.98 | PENDIENTE |
| 5 | 23 | 3 | 0.0420 | 5 313.00 | 6 269.34 | PENDIENTE |
| 6 | 3 | 4 | 0.0880 | 1 452.00 | 1 713.36 | PENDIENTE |
| 7 | 15 | 3 | 0.0420 | 3 465.00 | 4 088.70 | PENDIENTE |
| 8 | 39 | 3 | 0.0420 | 9 009.00 | 10 630.62 | PENDIENTE |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

### Detalles de honorario: importes y cantidades

Las primeras filas de `finanzas_detallehonorarioinspector`, con las visitas
programadas de la liquidación de origen:

| Visits liquidadas | Programadas en el detalle | Costo por inspección | Monto contribuido | `sub_total` | Descuento | Honorarios | `tasa_descuento` | Programadas en la liquidación |
|---|---|---|---|---|---|---|---|---|
| 12 | 12 | 378.40 | 4 540.80 | 4 540.80 | 0.00 | 4 540.80 | 0.000000 | 12 |
| 8 | 8 | 316.00 | 2 528.00 | 2 528.00 | 252.80 | 2 275.20 | 0.100000 | 8 |
| 5 | 5 | 369.60 | 1 848.00 | 1 848.00 | 0.00 | 1 848.00 | 0.000000 | 5 |
| 4 | 4 | 404.80 | 1 619.20 | 1 619.20 | 0.00 | 1 619.20 | 0.000000 | 4 |
| 22 | 22 | 484.00 | 10 648.00 | 10 648.00 | 0.00 | 10 648.00 | 0.000000 | 22 |
| 2 | 2 | 207.90 | 415.80 | 415.80 | 0.00 | 415.80 | 0.000000 | 2 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

La segunda fila muestra el descuento de escala aplicado: un subtotal de
S/ 2 528.00 con tasa 0.100000 produce un descuento de S/ 252.80 y unos honorarios
de S/ 2 275.20.

### Integridad del saldo

De los 9 849 detalles de honorario, **ninguno** supera las visitas programadas
de su liquidación: la consulta de control 3.4.6 no devuelve filas.

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

En las filas mostradas, `inspecciones_liquidadas` coincide con
`inspecciones_programadas` y con las visitas programadas de la liquidación: el
saldo queda en cero para cada una.

### Operatividad de los inspectores

Los períodos de operatividad vigentes son:

| `periodo_inicio` | `periodo_fin` | Asignaciones |
|---|---|---|
| 2025-08-01 | 2026-07-31 | 138 |
| 2026-08-01 | 2027-07-31 | 145 |

*Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)*

Las operatividades se administran en
`/admin/liquidaciones/inspectoroperacion/`, con sus períodos de vigencia como
inline, y se consultan desde la pantalla de inspectores
(`/liquidaciones/inspectores`) y desde el endpoint
`GET /api/finanzas/recibos-inspectores/operatividades?cip=…`.

---

## 3.6 Procedimiento operativo para registrar visitas históricas

Este es el procedimiento para dejar registrado un mes de visitas ya realizadas
que nunca se liquidó, de modo que el saldo de la IO refleje la realidad y no
permita liquidar de más.

### Cuándo usar cada vía

| Situación | Vía |
|---|---|
| El mes se liquida ahora, con su RH mensual y su escala de descuento | Wizard de RH mensual (`/liquidaciones/recibos-inspectores/mensual`) |
| Meses antiguos ya realizados que nunca se liquidaron, y no se quiere emitir un RH retroactivo | Admin, inline **Registros de visitas** sobre la liquidación de IO |
| Revisar o corregir el libro de pagos | Admin, `/admin/finanzas/registropagoinspector/` |

### Procedimiento por admin

1. **Localizar la liquidación de IO.** En
   `/admin/liquidaciones/liquidacioninspeccionobraproxy/`, el buscador acepta el
   número de liquidación (coincidencia exacta sobre el `numero` de la tabla
   wrapper) además del expediente, el propietario y el documento.
2. **Comprobar el saldo antes de escribir.** Con la consulta 3.4.1 se obtiene el
   saldo actual de esa IO.
3. **Abrir la liquidación y añadir el registro.** En la pantalla de edición,
   bajar al inline **Registros de visitas** y completar:
   - `periodo`: el año del mes que se quiere liquidar.
   - `mes`: el mes (1–12).
   - `inspecciones_pagadas`: cuántas visitas se deben descontar del saldo.
4. **Guardar.** El inline valida en el servidor:
   - que `(periodo, mes)` no sea un período futuro,
   - que el total de visitas pagadas del formulario no supere las
     `cantidad_visitas` de la liquidación.
   Si alguna de las dos falla, no se guarda nada y el formulario muestra el
   motivo.
5. **Verificar.** Repetir la consulta 3.4.1: el saldo debe haber bajado en la
   cantidad registrada, y la consulta 3.4.3 debe mostrar la fila nueva en el
   libro.

### Registro de varios meses

El inline admite varias filas en una misma sesión de edición: se añaden todas
las que se necesiten y se guardan juntas. La validación del total es sobre el
conjunto del formset, de modo que un conjunto que en conjunto exceda lo
programado se rechaza entero.

### Interaction con el RH mensual

El flujo con el RH mensual es el inverso: el RH mensual calcula el saldo
descontando el libro, de modo que las visitas ya registradas por admin **se
descuentan automáticamente** de las candidatas que el wizard ofrece para los
meses posteriores.

El `recibo_mensual` es de solo lectura en el inline: el enlace entre un registro
y su RH lo establece el wizard al crear el recibo, no el admin.

### Al borrar un RH

`DELETE /api/finanzas/recibos-inspectores/{id}/eliminar` borra la cabecera y sus
detalles, y **revierte los pagos** que el RH había generado: los
`RegistroPagoInspector` con `recibo_mensual_id` igual al del RH se eliminan, y
los marcadores de período de las IOs afectadas se recalculan desde el libro
restante. Los registros con `recibo_mensual_id` nulo no se tocan.

La operación solo admite el **último** RH del inspector: sobre un RH anterior
responde 409.
