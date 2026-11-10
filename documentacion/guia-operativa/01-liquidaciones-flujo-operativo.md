# 01 — Liquidaciones: flujo operativo

> Referencia de datos: [00 — Datos operativos de referencia](00-datos-operativos-de-referencia.md).
> Este documento explica el recorrido completo de una liquidación: desde la
> pantalla hasta la persistencia, y qué efecto tiene la fecha sobre lo que se
> cobra.

## 1.1 Panorama

Una liquidación en CAM son **dos cosas unidas por un identificador**:

1. Una **cabecera** (`LiquidacionGeneral`, tabla
   `liquidaciones_liquidaciongeneral`): municipalidad, expediente, fecha de
   registro, estado, subtotal, total, IGV y UIT aplicados.
2. Un **detalle por tipo** (`LiquidacionPorMetroCuadrado`,
   `LiquidacionPorcentajeObra` o `LiquidacionPorCategoriaVisitas`), que es
   donde vive el cálculo y la fotografía del catálogo que se usó.

Sobre la cabecera se apoyan, además:

- el **wrapper del tipo** (tabla envoltura uno a uno), que aporta el número
  correlativo de la liquidación específica;
- los **grupos de relación** (`LiquidacionRelacionGrupo` /
  `LiquidacionRelacionMiembro`), que encadenan revisiones;
- los **comprobantes** (`LiquidacionComprobante`), de los que solo uno está
  activo;
- las **asignaciones** de inspectores (`LiquidacionInspector`) y de delegados
  (`LiquidacionDelegado`).

Todo el proceso se apoya en un mismo patrón: **la fecha efectiva selecciona el
catálogo y el catálogo queda congelado en la liquidación**.

## 1.2 Las pantallas y sus endpoints

En el frontend, cada tipo de liquidación tiene su propia vista bajo
`/liquidaciones/<tipo>` (`habilitacion-urbana`, `edificaciones`,
`mecanica-suelos`, `taludes`, `impacto-vial`, `inspeccion-obra`), más las
pantallas transversales `/liquidaciones/finanzas`, `/liquidaciones/inspectores`,
`/liquidaciones/delegados`, `/liquidaciones/recibos-inspectores`,
`/liquidaciones/recibos-delegados` y `/liquidaciones/reparticiones-estacionales`.

En el backend, cada tipo expone el mismo conjunto de operaciones:

| Operación | Endpoint (plantilla) |
|---|---|
| Tarifas vigentes del tipo | `GET /liquidaciones/{tipo}/tarifas/vigentes` |
| Listado | `GET /liquidaciones/{tipo}/` |
| Detalle | `GET /liquidaciones/{tipo}/{id}` |
| Cotización (preview) | `POST /liquidaciones/{tipo}/cotizar?fecha=YYYY-MM-DD` |
| Cotización en edición | `POST /liquidaciones/{tipo}/{id}/cotizar-edicion` |
| Primera revisión | `POST /liquidaciones/{tipo}/nueva-liquidacion/primera-revision` |
| Registro histórico | `POST /liquidaciones/{tipo}/nueva-liquidacion/legacy` |
| Nueva revisión | `POST /liquidaciones/{tipo}/nueva-revision` |
| Relacionada | `POST /liquidaciones/{tipo}/relacionada` |
| Modo manual | `POST /liquidaciones/{tipo}/edge` |

Y las operaciones transversales:

| Operación | Endpoint |
|---|---|
| Comprobante (alta o reemplazo) | `POST /liquidaciones/generales/{id}/comprobante` |
| Comprobante (edición en sitio) | `PATCH /liquidaciones/generales/{id}/comprobante/{comprobante_id}` |
| Marcar pagada | `POST /liquidaciones/generales/{id}/marcar-pagada` |
| Baja lógica | `PATCH /liquidaciones/generales/{id}/eliminar` |
| Historial de tarifas | `GET /liquidaciones/{tipo}/tarifas/historicas` |
| Historial de derechos | `GET /liquidaciones/derechos/historicos` |
| Asignar inspectores | `PATCH /inspectores/{liquidacion_id}/inspectores` |
| Asignar delegados | `PATCH /liquidaciones/{liquidacion_id}/delegados` |

## 1.3 Paso 1 — La fecha decide el catálogo

El frontend pide la cotización con la fecha efectiva. En la práctica, el
formulario de creación manda `fecha_registro` como parámetro `?fecha=` a
`POST /liquidaciones/{tipo}/cotizar`, y el backend resuelve con ella:

- el **IGV** y la **UIT** vigentes a esa fecha;
- el **derecho** vigente a esa fecha (`DerechoPorMetroCuadrado` para los tipos
  por metro cuadrado, `DerechoPorcentajeObra` para los de porcentaje de obra);
- la **tarifa base** del tipo vigente a esa fecha, y de ella la tarifa concreta
  (metro cuadrado, porcentaje de obra o categoría de visitas);
- el **catálogo de especialidades habilitadas** vigente a esa fecha, que define
  cuántas especialidades pueden participar.

Si la pantalla no manda fecha, la fecha efectiva es hoy y se resuelve el
catálogo abierto.

La pantalla de tarifas vigentes (`GET /liquidaciones/{tipo}/tarifas/vigentes`)
acepta la misma fecha, de modo que el selector de tarifas que ve el usuario y
el cálculo del backend usan exactamente la misma fuente.

### Ejemplo real: qué tarifa aplica a cada fecha

| Fecha efectiva | Tipo | Tarifa base vigente | Tarifa concreta | Derecho vigente |
|---|---|---|---|---|
| 2026-04-15 | `HABILITACION_URBANA` | 2000-01-01 → 2026-04-30 | `costo_por_m2` = 0.1500 | 750.00 – 7500.00 |
| 2026-05-02 | `HABILITACION_URBANA` | 2026-05-01 → abierto | `costo_por_m2` = 0.2000 | 1000.00 – 10000.00 |
| 2026-05-02 | `EDIFICACION` | 2026-05-01 → abierto | `porcentaje_liquidacion` = 0.0005 | 129.80 (2 % de UIT con IGV) |

Los mismos tres datos del catálogo que aparecen en
[00 §0.4 y §0.5](00-datos-operativos-de-referencia.md) resuelven a valores
distintos según el día. Las 4 liquidaciones de Habilitación Urbana
registradas en octubre de 2026 ya usan `costo_por_m2` = 0.2000 y el derecho
1000.00 – 10 000.00, porque todas son posteriores al cambio de vigencia del
2026-05-01.

*Datos de desarrollo consultados: 2026-11-08 18:06 (UTC−05:00)*

## 1.4 Paso 2 — Los tres motores de cálculo

### 1.4.1 Por metro cuadrado (Habilitación Urbana, Mecánica de Suelos)

```
total    = área_solicitada × costo_por_m2        (el costo por m² ya incluye IGV)
subtotal = total / (1 + IGV_vigente)
```

En el camino de registro histórico, el total se acota antes de derivar el
subtotal:

```
si total <  derecho_minimo  →  total = derecho_minimo
si total >  derecho_maximo  →  total = derecho_maximo
```

**Ejemplo real 1 — área dentro del rango.** Liquidación de Habilitación Urbana
registrada el 2026-10-27:

| Dato | Valor |
|---|---|
| `area_m2` | 11 840.00 |
| `costo_por_m2` | 0.2000 |
| `derecho_minimo` / `derecho_maximo` | 1000.00 / 10 000.00 |
| `sub_total` | 2 006.78 |
| `total` | 2 368.00 |

Comprobación: `11 840.00 × 0.2000 = 2 368.00` (total, con IGV incluido) y
`2 368.00 / 1.18 = 2 006.78` (subtotal).

**Ejemplo real 2 — área que supera el tope.** Liquidación de Habilitación Urbana
registrada el 2026-10-22:

| Dato | Valor |
|---|---|
| `area_m2` | 69 680.00 |
| `costo_por_m2` | 0.2000 |
| `sub_total` | 8 474.58 |
| `total` | 10 000.00 |

Comprobación: `69 680.00 × 0.2000 = 13 936.00`, que se acota al
`derecho_maximo` de 10 000.00; y `10 000.00 / 1.18 = 8 474.58`.

**Ejemplo real 3 — área por debajo del mínimo.** Liquidación de Habilitación
Urbana registrada el 2026-10-19:

| Dato | Valor |
|---|---|
| `area_m2` | 4 745.39 |
| `costo_por_m2` | 0.2000 |
| `sub_total` | 847.46 |
| `total` | 1 000.00 |

Comprobación: `4 745.39 × 0.2000 = 949.08`, que se eleva al
`derecho_minimo` de 1 000.00; y `1 000.00 / 1.18 = 847.46`.

*Datos de desarrollo consultados: 2026-11-08 18:06 (UTC−05:00)*

### 1.4.2 Por categoría de visitas (Inspección de Obra)

```
subtotal = cantidad_visitas × (porcentaje_uit × UIT_vigente)
total    = subtotal × (1 + IGV_vigente)
```

Aquí la fecha pesa por partida doble: la **categoría** determina el
`porcentaje_uit` de la tarifa, y el **año** de la fecha determina la **UIT**.

**Ejemplo real 4 — categoría 4.** Liquidación de Inspección de Obra registrada
el 2026-10-30:

| Dato | Valor |
|---|---|
| `categoria` | `4` |
| `cantidad_visitas` | 5 |
| `porcentaje_uit` | 0.0880 |
| `sub_total` | 2 420.00 |
| `total` | 2 855.60 |

Comprobación: `5 × (0.0880 × 5500) = 2 420.00` (UIT 2026 = 5500) y
`2 420.00 × 1.18 = 2 855.60`.

**Ejemplo real 5 — categoría 3.** Liquidación de Inspección de Obra registrada
el 2026-10-30:

| Dato | Valor |
|---|---|
| `categoria` | `3` |
| `cantidad_visitas` | 2 |
| `porcentaje_uit` | 0.0420 |
| `sub_total` | 462.00 |
| `total` | 545.16 |

Comprobación: `2 × (0.0420 × 5500) = 462.00` y `462.00 × 1.18 = 545.16`.

*Datos de desarrollo consultados: 2026-11-08 18:06 (UTC−05:00)*

### 1.4.3 Por porcentaje de obra (Edificación, Taludes, Impacto Vial)

Este es el motor más rico, porque reparte el monto entre **especialidades**.
El flujo resuelve, en este orden:

1. La **estrategia de cotización** elegida:
   - `NORMAL_SELECCIONADAS` — cobra solo las especialidades seleccionadas.
   - `TARIFA_HABILITADAS_PARTICIPANTES` — cobra el universo de specialties
     habilitadas.
   - `TOTAL_EXPLICITO` — el total con IGV manda; el valor declarado queda como
     referencia.
2. El **valor declarado** de la obra.
3. La **tarifa vigente** del tipo (porcentaje unitario `f`).
4. El **universo de specialties habilitadas** (H) vigente a la fecha efectiva,
   tomado de `LiquidacionEspecialidadDisponibles`.
5. El **derecho** vigente, cuyo mínimo se calcula como
   `UIT × porcentaje_minimo_uit × (1 + IGV)`.

El reparto produce una fila por especialidad en
`LiquidacionPorcentajeObraDetalle` con `porcentaje_aplicado`, `subtotal`,
`importe_parcial` y `ajuste_redondeo`. El `ajuste_redondeo` de ±0.01 es lo que
hace que la suma de los detalles cuadre exactamente con el subtotal de la
cabecera.

**Ejemplo real 6 — Edificación con tres especialidades.** Liquidación de
Edificación registrada el 2026-10-30:

| Dato | Valor |
|---|---|
| `valor_declarado` | 335 995.68 |
| `porcentaje_tarifa` | 0.0005 |
| `cantidad_especialidades_habilitadas` (H) | 3 |
| `estrategia_cotizacion` | `NORMAL_SELECCIONADAS` |
| `derecho_minimo` | 129.80 |
| `porcentaje_minimo_uit` | 0.0200 |
| `sub_total` | 503.99 |
| `total` | 594.71 |

Detalle por especialidad:

| Especialidad | `porcentaje_aplicado` | `subtotal` | `importe_parcial` | `ajuste_redondeo` |
|---|---|---|---|---|
| Ingeniería Civil | 0.0005 | 168.00 | 168.00 | 0.00 |
| Ingeniería Eléctrica y Mecánica Eléctrica | 0.0005 | 167.99 | 168.00 | −0.01 |
| Ingeniería Sanitaria | 0.0005 | 168.00 | 168.00 | 0.00 |
| **Suma** | | **503.99** | **504.00** | **0.00** |

Comprobaciones: `335 995.68 × 0.0005 = 167.9978` por especialidad, tres
especialidades → `503.99`; y `503.99 × 1.18 = 594.71`. El derecho mínimo
`129.80` sale de `5500 × 0.0200 × 1.18`.

*Datos de desarrollo consultados: 2026-11-08 18:06 (UTC−05:00)*

## 1.5 Paso 3 — Creación: qué se persiste

La creación comparte el mismo esqueleto para todos los tipos, dentro de una
única transacción:

1. **Entidad** (`Entidad`): alta o reutilización a partir del tipo y número de
   documento del titular.
2. **Proyecto** (`Proyecto`): nombre del propietario, dirección, distrito,
   urbanización y razón social.
3. **Cabecera** (`LiquidacionGeneral`): municipalidad, expediente, observación,
   `numero_revision`, `sub_total` y `total` que entrega la cotización,
   `igv_id_id` y `uit_id_id` (las filas exactas del catálogo aplicadas),
   `usuario_creador_id`, `fecha_registro`, y `modo_calculo` = `TARIFA`.
4. **Detalle por tipo**: se escribe la fila de detalle con el área, el costo por
   m² y el derecho (M2), o el valor declarado, el porcentaje y el derecho (PO),
   o la cantidad de visitas y el porcentaje de UIT (IO). En PO se escribe
   además una fila por especialidad en `LiquidacionPorcentajeObraDetalle`.
5. **Wrapper del tipo**: la tabla envoltura que asigna el número correlativo.
6. **Grupo de relación**: se abre un grupo con la `relacion_key` del tipo (más
   el tipo de trámite en los tipos que lo tienen) y la liquidación queda como
   primer miembro.

El `numero_revision` lo elige el cliente y se persiste **tal cual**, tanto en
la cabecera como en el miembro del grupo. El sistema no lo deriva ni lo
fuerza a 1.

### Modos alternativos

- **Registro histórico** (`/nueva-liquidacion/legacy`): el cliente manda la
  fecha efectiva y los importes; el backend resuelve IGV, UIT, tarifa y
  derecho **a esa fecha** y valida que la tarifa del payload sea la vigente en
  ella.
- **Modo manual / edge** (`/edge`): el subtotal se carga a mano, el total se
  calcula como `subtotal × (1 + IGV)`, `modo_calculo` queda en `MANUAL` y el
  detalle se crea sin tarifa aplicada ni derecho. Esta liquidación **no** abre
  grupo de relación: es un registro autónomo.

## 1.6 Paso 4 — Revisión y relacionada

- **Nueva revisión** (`POST /liquidaciones/{tipo}/nueva-revision`): crea una
  liquidación nueva y la suma como miembro del grupo de la liquidación previa.
- **Relacionada** (`POST /liquidaciones/{tipo}/relacionada`): mismo mecanismo,
  con la diferencia de que la liquidación previa es solo el punto de anclaje:
  no se persiste una línea de ascendencia, solo la pertenencia al grupo.

En ambos casos la liquidación previa se usa **de forma transitoria** para
encontrar (o crear, si no tenía) el grupo. El número de revisión del nuevo
miembro es el mismo que el de la cabecera nueva.

## 1.7 Paso 5 — Comprobantes y estado

El estado de la liquidación tiene dos valores, `PENDIENTE` y `PAGADA`.

- `POST /liquidaciones/generales/{id}/comprobante` **agrega o reemplaza**: si
  ya había un comprobante activo, se desactiva y se crea uno nuevo con
  `activo = true`. El comprobante anterior queda en el historial con su
  `motivo_reemplazo`.
- `PATCH /liquidaciones/generales/{id}/comprobante/{comprobante_id}` edita el
  comprobante **activo en sitio**: no crea filas nuevas, no desactiva nada y no
  toca el `monto` ya registrado.
- `POST /liquidaciones/generales/{id}/marcar-pagada` mueve el estado a `PAGADA`.
  Es idempotente: si ya estaba pagada, responde con éxito sin cambiar nada.

El comprobante activo es el que aparece en el detalle de la liquidación y en
los reportes de RH.

**Ejemplo real 7 — comprobantes registrados.** Comprobantes de tipo `FACTURA`
y `BOLETA` con `monto` y `fecha_emision`:

| Tipo | Serie | Número | Fecha de emisión | Monto |
|---|---|---|---|---|
| `FACTURA` | F01 | 00035920 | 2025-07-24 | 3 977.19 |
| `FACTURA` | F02 | 00031753 | 2021-06-25 | 2 497.35 |
| `BOLETA` | B11 | 00000061 | 2020-02-19 | 487.10 |
| `BOLETA` | B02 | 00081352 | — | 108.87 |

*Datos de desarrollo consultados: 2026-11-08 18:06 (UTC−05:00)*

## 1.8 Paso 6 — Inspección: asignar inspectores

La Inspección de Obra es un caso particular: **el inspector se asigna a la
liquidación por categoría de visitas**, no a la cabecera. La tabla
`LiquidacionInspector` cuelga de `LiquidacionPorCategoriaVisitas`.

Al asignar se guardan:

| Campo | Para qué sirve |
|---|---|
| `inspector_id` | Quién |
| `inspector_operacion_id` | Con qué operatividad (tipo + categoría + especialidad) se contrató |
| `especialidad_revision_id` | La especialidad con la que revisa |
| `periodo`, `mes` | En qué mes se imputa la inspección (se actualizan con el RH) |
| `dictamen_revision` | `CONFORME`, `NO_CONFORME`, `PENDIENTE` o `AP_OB` |
| `fecha_presentacion`, `fecha_revision` | Las dos fechas del ciclo de revisión |

La selection de candidatos la hace
`InspectorCoreService.list_inspectores_vigentes_para_tipo`, que filtra por tipo
de liquidación, especialidad y **período de operatividad vigente a la fecha**
(ver [documento 02](02-operatividad-de-inspectores-y-delegados.md)).

## 1.9 Paso 7 — Delegados: asignar revisores

La asignación de delegados cuelga de la cabecera: `LiquidacionDelegado` apunta
a `LiquidacionGeneral` y guarda el `delegado_operacion_id`, la especialidad de
revisión, el período, el mes, el dictamen, las fechas y el `numero_rh`.

Es la tabla que consume el flujo de RH mensual: el sistema la crea (o la
reutiliza) al pagar a un delegado, y marca con `creado_por_rh = true` las que
nacen dentro de ese flujo, para poder limpiarlas si el RH se elimina.

Volumen real: 139 154 asignaciones sobre 49 485 liquidaciones distintas.

## 1.10 Paso 8 — Baja lógica

`PATCH /liquidaciones/generales/{id}/eliminar` no borra la fila:

- pone `eliminado = true`;
- graba `fecha_eliminacion`, `eliminado_por_id` y `motivo_eliminacion`;
- limpia el `numero` de la tabla envoltura del tipo, de modo que ese número
  queda libre para la siguiente liquidación de ese tipo.

La operación es idempotente: si la liquidación ya estaba dada de baja,
responde con éxito sin volver a aplicar cambios.

En la base de desarrollo hay 62 019 liquidaciones y **ninguna** con baja
lógica, todas en estado `PENDIENTE`.

## 1.11 Resumen: qué queda escrito tras cada operación

| Operación | Cabecera | Detalle por tipo | Wrapper | Grupo | Comprobante | Asignaciones |
|---|---|---|---|---|---|---|
| Cotizar | — | — | — | — | — | — |
| Primera revisión | Sí | Sí | Sí | Sí (abre) | — | — |
| Registro histórico | Sí | Sí | Sí | No | — | — |
| Modo manual | Sí | Sí (sin tarifa) | Sí | No | — | — |
| Nueva revisión | Sí | Sí | Sí | Sí (suma) | — | — |
| Relacionada | Sí | Sí | Sí | Sí (suma) | — | — |
| Asignar inspector | — | — | — | — | — | `LiquidacionInspector` |
| Asignar delegado | — | — | — | — | — | `LiquidacionDelegado` |
| Emitir comprobante | — | — | — | — | Sí | — |
| Marcar pagada | `estado` | — | — | — | — | — |
| Baja | `eliminado` | — | `numero` liberado | — | — | — |
