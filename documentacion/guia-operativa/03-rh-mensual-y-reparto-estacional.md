# 03 — RH mensual y reparto estacional

> Referencia de datos: [00 §0.7.3, §0.8 y §0.9.5](00-datos-operativos-de-referencia.md).
> El RH (Recargo de Honorarios) mensual es el documento que paga a inspectores
> y delegados por el trabajo de un mes concreto. El reparto estacional es el
> mecanismo que reparte el fondo común acumulado entre delegados y capítulos.

## 3.1 Las tablas del RH

| Modelo | Tabla física | Rol |
|---|---|---|
| `ReciboHonorarioInspectorMensual` | `finanzas_recibohonorarioinspectormensual` | Cabecera mensual del inspector: período, mes, totales, escala aplicada |
| `DetalleHonorarioInspector` | `finanzas_detallehonorarioinspector` | Una fila por liquidación de inspección liquidada en el mes |
| `ReciboHonorarioDelegadoMensual` | `finanzas_recibohonorariodelegadomensual` | Cabecera mensual del delegado: período, mes, totales, tasa aplicada |
| `DetalleHonorarioDelegado` | `finanzas_detallehonorariodelegado` | Una fila por liquidación atendida en el mes |
| `RegistroPagoInspector` | `finanzas_registropagoinspector` | Libro de inspecciones pagadas por liquidación |
| `ReciboHonorarioInspector` | `finanzas_recibohonorarioinspector` | Recibo por liquidación de inspección (no mensual) |
| `ReciboHonorarioDelegado` | `finanzas_recibohonorariodelegado` | Recibo por liquidación de delegado (no mensual) |

Los dos "mensuales" son la vista acumulada por mes; los otros dos son el
recibo individual de una liquidación.

Cada cabecera mensual **congela** los parámetros con los que se calculó:

| Campo congelado | En la cabecera de inspector | En la cabecera de delegado |
|---|---|---|
| Escala / tasa | `escala_descuento_id` y `tasa_descuento` | `tasa_delegado_id` |
| Operatividad | `inspector_operacion_id` | `delegado_operacion_id` |
| Periodo y mes | `periodo`, `mes` | `periodo`, `mes` |

Congelar es lo que permite **editar un RH meses después** sin que el resultado
cambie: la reconciliación vuelve a cotizar con la escala o la tasa original,
no con la vigente del día.

## 3.2 RH mensual del inspector

### 3.2.1 La cotización

`POST /finanzas/recibos-inspectores/cotizar` calcula el RH **sin escribir
nada**. La pantalla `rh-inspector-mensual` lo llama para mostrar el preview.

El cálculo, paso a paso:

**1. Resolver el inspector** por CIP. Si no existe, la operación responde 404.

**2. Resolver la escala de descuento** vigente. Si se edita un RH existente, en
lugar de la vigente se usa la escala **congelada** en ese recibo.

**3. Por cada liquidación seleccionada:**

| Paso | Qué ocurre |
|---|---|
| Identificación | Por `liquidacion_categoria_visitas_id` (flujo de candidatas) o por `exp_liqui` (flujo manual). |
| Validación | La liquidación debe ser de inspección de obra y estar **asociada al inspector**. |
| Importe bruto | `LiquidacionGeneral.sub_total` de la liquidación. |
| Inspecciones programadas | `cantidad_visitas` de la liquidación por categoría de visitas. |
| Saldo disponible | `programadas − inspecciones ya pagadas` (ver el libro de pagos). |
| Costo por inspección | `importe_bruto / programadas`, redondeado a dos decimales. |
| Monto contribuido | `costo_por_inspeccion × cantidad_visitas del mes`. |
| Saldo restante | `saldo_disponible − cantidad_visitas del mes`. |

**4. Descuento sobre el total del mes.** Con el subtotal acumulado, se busca el
rango de la escala que lo contiene y se aplica su porcentaje:

```
total_descuento = subtotal × tasa_del_rango
total_honorarios = subtotal − total_descuento
```

**5. Reparto por liquidación.** El descuento total se prorratea entre los
ítems en proporción a su subtotal, y **el último ítem absorbe el residuo** por
resta, de modo que la suma de los descuentos por ítem sea exactamente igual al
descuento total.

### 3.2.2 El libro de pagos

`RegistroPagoInspector` es lo que impide pagar dos veces la misma inspección.
Guarda, por liquidación: período, mes, inspecciones pagadas, fecha de
registro y el recibo mensual al que pertenece.

El saldo disponible de una liquidación se calcula sumando las inspecciones
pagadas en **períodos anteriores** y, dentro del mismo período, **hasta el mes
inclusivo** del RH que se está cotizando:

```
pagadas_hasta_mes_anterior = Σ inspecciones_pagadas
                             de los registros con
                             (periodo < periodo_del_rh)
                             o (periodo = periodo_del_rh y mes <= mes_del_rh)

saldo_disponible = cantidad_visitas_programadas − pagadas_hasta_mes_anterior
```

Cuando se edita un RH, el propio recibo se excluye del cálculo: el RH no se
descuenta de su propio balance.

### 3.2.3 La creación

`POST /finanzas/recibos-inspectores/crear` ejecuta todo dentro de **una sola
transacción**:

1. Cotiza (reutilizando el flujo de cotización, con todas sus validaciones).
2. Verifica que **todos los ítems pertenezcan a la misma operatividad de
   inspector**. Si se mezclan operaciones distintas, responde 409: un RH es por
   operación.
3. Crea la cabecera mensual con los totales ya calculados y la escala
   congelada.
4. Por cada ítem, crea el detalle (`DetalleHonorarioInspector`) y actualiza el
   libro de pagos (`RegistroPagoInspector`).
5. Actualiza los marcadores de período y mes en `LiquidacionInspector`.
6. Aplica el `expediente` que venga en el payload sobre la liquidación. Si el
   valor enviado difiere del persistido, se escribe; si falta el campo, no se
   toca nada. Si la liquidación está `PAGADA` y el expediente cambia, la
   operación se aborta entera y no queda ni RH ni expediente.

### 3.2.4 La edición y el borrado

`PATCH /finanzas/recibos-inspectores/{rh_id}` **sincroniza** el recibo: el
conjunto de ítems del payload es el conjunto **final** de detalles. Los
detalles que no aparecen en el payload se retiran; los que aparecen con su
`detalle_id` se conservan y se recalculan; los que aparecen sin `detalle_id`
se agregan. El libro de pagos se reemplaza **solo** por las filas de este
recibo, y los marcadores de período se recalculan desde el libro resultante.

`DELETE /finanzas/recibos-inspectores/{id}/eliminar` elimina el recibo y sus
detalles en cascada.

### 3.2.5 Escala de descuento: datos reales

Escala vigente y sus rangos (de [00 §0.8.1](00-datos-operativos-de-referencia.md)):

| Escala | Vigencia | `monto_minimo` | `monto_maximo` | `porcentaje_descuento` |
|---|---|---|---|---|
| Escala 2026 | 2026-01-01 → abierto | 0.00 | 8000.00 | 0.1500 |
| Escala 2026 | 2026-01-01 → abierto | 8000.00 | 15000.00 | 0.2000 |
| Escala 2026 | 2026-01-01 → abierto | 15000.00 | 30000.00 | 0.3000 |
| Escala 2026 | 2026-01-01 → abierto | 30000.00 | — | 0.4000 |

El rango se elige por el **subtotal del mes**, no por el honorario final. Un
mes cuyo subtotal acumulado cae en 8 000.00 – 15 000.00 recibe 20 % de
descuento sobre ese subtotal.

## 3.3 RH mensual del delegado

### 3.3.1 La cotización

`POST /finanzas/recibos-delegados/cotizar`. El flujo es paralelo al del
inspector, pero con tres diferencias que cambian el resultado.

**1. Se resuelve una operatividad concreta.** El payload trae
`delegado_operacion_id`. El sistema exige que exista, que pertenezca al
delegado identificado por el CIP y que tenga **tipo de liquidación asignado**:
sin tipo no hay tasa aplicable.

**2. La tasa sale del tipo de liquidación de la operatividad.** Se resuelve la
`TasaDelegado` vigente de ese tipo. Si se edita un RH existente, se usa la
tasa **congelada** en ese recibo.

**3. La base imponible depende de la estrategia del tipo.** El sistema
clasifica el tipo de liquidación en dos estrategias:

| Estrategia | Tipos | Base imponible |
|---|---|---|
| `detail` | `EDIFICACION`, `IMPACTO_VIAL`, `TALUDES` | `LiquidacionPorcentajeObraDetalle.subtotal` de la especialidad del delegado, con su ajuste de redondeo |
| `direct` | `HABILITACION_URBANA`, `MECANICA_SUELOS` | `LiquidacionGeneral.sub_total` completo, sin distribución por especialidad |

### 3.3.2 El cálculo de las deducciones

Sobre la base imponible se aplican las tres tasas:

```
tasa_neto        = 1 − renta_cip − aporte_codemu − fondo_comun
neto_honorario   = base_imponible × tasa_neto
aporte_codemu    = base_imponible × aporte_codemu
fondo_comun      = base_imponible × fondo_comun
renta_cip        = base_imponible_total − neto_honorario − aporte_codemu − fondo_comun
```

La **renta CIP se calcula por resta**, no por porcentaje: así absorbe el
ajuste de redondeo y cualquier diferencia entre la base exacta y la base
redondeada, de modo que las cuatro cifras siempre cuadran.

### 3.3.3 La creación

`POST /finanzas/recibos-delegados/crear`, en una sola transacción:

1. Cotiza.
2. Crea la cabecera `ReciboHonorarioDelegadoMensual` con los totales y la tasa
   congelada.
3. Por cada ítem, crea o reutiliza la asignación `LiquidacionDelegado` (con su
   `delegado_operacion_id`, período, mes, dictamen, fechas y `numero_rh`), y
   a continuación el detalle `DetalleHonorarioDelegado` que apunta a ella.
4. Aplica el `expediente` recibido, con la misma semántica que en el RH de
   inspector.

Las asignaciones creadas dentro de este flujo quedan marcadas con
`creado_por_rh = true`.

### 3.3.4 La edición y el borrado

`PATCH /finanzas/recibos-delegados/{rh_id}` sincroniza el conjunto final de
detalles, igual que en el inspector, con dos añadidos:

- los detalles retenidos se recalculan con la **tasa congelada** del recibo;
- la metadata de la asignación (número de RH, período, mes, dictamen y fechas)
  nunca se modifica sobre un detalle retenido: si el payload intenta cambiarla,
  la operación responde 409 y no se altera ningún recibo.

`DELETE /finanzas/recibos-delegados/{id}/eliminar` elimina el recibo y sus
detalles en cascada, y **solo** limpia las asignaciones que creó el propio
RH y que no están referenciadas por ningún otro recibo. Las asignaciones
compartidas o históricas se conservan.

### 3.3.5 Tasas reales

De [00 §0.8.2](00-datos-operativos-de-referencia.md):

| Tipo | `renta_cip` | `aporte_codemu` | `fondo_comun` | Neto sobre el bruto |
|---|---|---|---|---|
| `EDIFICACION` | 0.2500 | 0.0500 | 0.1000 | 0.60 |
| `HABILITACION_URBANA` | 0.2500 | 0.0500 | 0.0000 | 0.70 |
| `MECANICA_SUELOS` | 0.1000 | 0.0500 | 0.0000 | 0.85 |
| `IMPACTO_VIAL` | 0.0000 | 0.0000 | 0.0000 | 1.00 |
| `INSPECCION_OBRA` | 0.0000 | 0.0000 | 0.0000 | 1.00 |
| `TALUDES` | 0.0000 | 0.0000 | 0.0000 | 1.00 |

**Ejemplo real de una liquidación de Edificación.** Con la tasa vigente de
`EDIFICACION` y una base imponible de 3 000.00:

| Concepto | Cálculo | Valor |
|---|---|---|
| Renta CIP | `3000.00 × 0.2500` | 750.00 |
| Aporte CODEMU | `3000.00 × 0.0500` | 150.00 |
| Fondo común | `3000.00 × 0.1000` | 300.00 |
| Neto honorario | `3000.00 × 0.60` | 1 800.00 |

Los 300.00 de fondo común son exactamente la suma que el reparto estacional
busca repartir después.

*Datos de desarrollo consultados: 2026-11-08 18:03 (UTC−05:00)*

## 3.4 El reparto estacional del fondo común

El fondo común es la porción de la renta CIP que no se paga al delegado
directamente: se acumula y se reparte, al final de un tramo de meses, entre
los delegados participantes y los capítulos profesionales.

### 3.4.1 Las tablas

| Modelo | Tabla física | Contenido |
|---|---|---|
| `RHReparticionEstacional` | `finanzas_rhreparticionestacional` | Cabecera: período, rango de meses, fondo común total, número de capítulos, número de delegados, monto por participación, residual |
| `RHReparticionEstacionalDelegado` | `finanzas_rhreparticionestacionaldelegado` | Monto asignado a cada delegado |
| `RHReparticionEstacionalCapitulo` | `finanzas_rhreparticionestacionalcapitulo` | Monto asignado a cada capítulo |

La cabecera también guarda `especialidad_revision_id`, `is_deleted` y
`deleted_at`: el reparto es **por especialidad de revisión**.

### 3.4.2 De dónde sale el fondo común

`get_fondo_comun_total(especialidad_revision_id, periodo, mes_desde, mes_hasta)`
suma el `fondo_comun` de todos los `DetalleHonorarioDelegado` que:

- pertenecen a una asignación con esa `especialidad_revision_id`;
- tienen `periodo` igual al año pedido;
- tienen `mes` entre `mes_desde` y `mes_hasta` (ambos inclusive).

Si el total es cero o negativo, la operación responde 400.

### 3.4.3 Quiénes participan

- **Delegados**: los que el usuario selecciona en la pantalla. El sistema no
  los deduce: son una entrada explícita.
- **Capítulos**: se deducen del catálogo. Los capítulos de una especialidad
  son los vinculados en `EspecialidadRevisionCapitulo`.

Datos reales de capítulos por especialidad:

| Especialidad de revisión | Capítulos vinculados |
|---|---|
| Ingeniería Civil | 1 |
| Ingeniería Electrónica | 1 |
| Ingeniería Eléctrica y Mecánica Eléctrica | 2 |
| Ingeniería Sanitaria | 1 |

### 3.4.4 La fórmula

```
divisor_total = número_de_delegados + número_de_capítulos
monto_por_participacion = fondo_comun_total / divisor_total
```

El reparto se hace **en céntimos enteros**, no con decimales, para que la
suma cuadre exactamente:

```
total_cents     = fondo_comun × 100
base_cents      = total_cents // divisor_total
leftover_cents  = total_cents % divisor_total
```

Los céntimos sobrantes van **a los capítulos**, en orden ascendente de
identificador: primero se reparte entre los capítulos de forma entera, y el
resto final se reparte uno a uno entre los primeros capítulos. Los delegados
reciben siempre la parte exacta, sin céntimos residuales.

El ejemplo del propio código, con un fondo común de 4.03, 2 capítulos y 2
delegados:

| Participante | Céntimos | Monto |
|---|---|---|
| Capítulo 1 | 102 | 1.02 |
| Capítulo 2 | 101 | 1.01 |
| Delegado 10 | 100 | 1.00 |
| Delegado 11 | 100 | 1.00 |
| **Suma** | **403** | **4.03** |

El `residual` guardado en la cabecera es siempre 0.00: el total se distribuye
completo.

### 3.4.5 Cotización, creación, edición y borrado

| Operación | Endpoint | Qué hace |
|---|---|---|
| Cotizar | `POST /finanzas/reparticiones-estacionales/cotizar` | Calcula el reparto **sin persistir**. Es el preview de la pantalla. |
| Crear | `POST /finanzas/reparticiones-estacionales` | Valida, calcula y persiste cabecera + detalles en una transacción. |
| Listar | `GET /finanzas/reparticiones-estacionales` | Reparticiones registradas. |
| Editar | `PATCH /finanzas/reparticiones-estacionales/{id}` | Recalcula con la misma lógica de cotización y **reemplaza** el conjunto de detalles. |
| Borrar | `DELETE /finanzas/reparticiones-estacionales/{id}` | Baja lógica (`is_deleted`, `deleted_at`). |

Reglas de validación:

- `mes_desde` no puede ser mayor que `mes_hasta`.
- No puede existir otra reparto **activa** para la misma especialidad y
  período con un rango de meses que se solape.
- Debe seleccionarse al menos un delegado.
- La especialidad debe tener al menos un capítulo vinculado.
- Un reparto eliminado (baja lógica) **no se revive** al editarlo: la
  operación responde 409.

Al editar, el registro conserva su identidad y su fecha de creación; solo se
reescriben los campos del snapshot y el conjunto **final** de detalles, que se
borra por completo antes de escribirse el nuevo, para que no sobreviva ninguna
fila obsoleta.

### 3.4.6 Un caso real de configuración

Con la tasa de `EDIFICACION` vigente, cada liquidación atendida por un delegado
aporta un 10 % de su base imponible al fondo común. Supongamos que en el
trimestre 2026-01 a 2026-03 la especialidad **Ingeniería Civil** acumula
`fondo_comun` de 1 200.00 en los detalles de delegado, y que se reparten con
2 delegados y 1 capítulo (Ingeniería Civil tiene 1 capítulo):

```
divisor_total           = 2 delegados + 1 capítulo = 3
monto_por_participación = 1200.00 / 3 = 400.00
residual                = 0.00
```

| Participante | Monto |
|---|---|
| Delegado 1 | 400.00 |
| Delegado 2 | 400.00 |
| Capítulo Ingeniería Civil (registro 02) | 400.00 |
| **Suma** | **1 200.00** |

Con **Ingeniería Eléctrica y Mecánica Eléctrica**, que tiene 2 capítulos, el
mismo fondo de 1 200.00 con 2 delegados se repartiría entre 4 participantes:
400.00 para cada delegado y 400.00 para cada capítulo.

*Datos de desarrollo consultados: 2026-11-08 18:03 (UTC−05:00)*

## 3.5 Resumen: del liquidado al pagado

```
Liquidación (con subtotal y total)
   │
   ├─ se asigna inspector ─→ LiquidacionInspector
   │                            │
   │                            └─ mes: RH Inspector Mensual
   │                                 escala de descuento vigente
   │                                 costo por inspección = sub_total / visitas
   │                                 saldo de visitas contra libro de pagos
   │
   └─ se asigna delegado ──→ LiquidacionDelegado
                                │
                                └─ mes: RH Delegado Mensual
                                     tasa vigente del tipo de la operatividad
                                     neto = base × (1 − renta − codemu − fondo)
                                     │
                                     └─ tramo de meses: Reparto Estacional
                                          fondo común acumulado ÷ (delegados + capítulos)
```

| Dato | Dónde se congela |
|---|---|
| Escala de descuento | `ReciboHonorarioInspectorMensual.escala_descuento_id` y `tasa_descuento` |
| Tasa de delegado | `ReciboHonorarioDelegadoMensual.tasa_delegado_id` |
| Operatividad | `inspector_operacion_id` / `delegado_operacion_id` |
| Reparto estacional | Cabecera `RHReparticionEstacional` + detalles por delegado y por capítulo |
