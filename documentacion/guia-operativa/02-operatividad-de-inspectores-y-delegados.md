# 02 — Operatividad de inspectores y delegados

> Referencia de datos: [00 §0.6 y §0.7](00-datos-operativos-de-referencia.md).
> La operatividad es el catálogo que responde **"quién puede hacer qué, en qué
> municipalidad, con qué especialidad y desde cuándo"**. Todo lo demás del
> sistema (selección de candidatos, asignaciones sobre liquidaciones y cálculo
> de RH) se apoya en ella.

## 2.1 La idea central

Hay **dos perfiles profesionales** con roles distintos:

| Perfil | Puede | Su unidad de operatividad |
|---|---|---|
| **Inspector** | Ejecutar y liquidar inspecciones de obra | Tipo de liquidación + especialidad + categoría |
| **Delegado** | Crear y revisar liquidaciones | Municipalidad + tipo de liquidación + especialidad (+ rol titular/alterno) |

Para cada uno, la operatividad se modela en **dos piezas**:

1. **La asignación**: el contexto estable (qué hace, dónde, con qué
   especialidad). Es un registro permanente.
2. **Los períodos de vigencia**: los tramos de fechas durante los cuales esa
   asignación está activa. Un inspector puede tener la misma asignación
   reabierta en tramos consecutivos, con una pequeña ventana entre medias.

La vigencia no se guarda "en la asignación", sino en una tabla aparte. Eso
permite **cerrar y reabrir** sin perder el histórico: el pasado sigue siendo
consultable.

## 2.2 Inspectores

### 2.2.1 Las tablas

| Modelo | Tabla física | Contenido |
|---|---|---|
| `Inspector` | `liquidaciones_inspector` | Persona habilitada como inspector (uno a uno con `PerfilIngeniero`) |
| `InspectorOperacion` | `liquidaciones_inspectoroperacion` | La asignación: inspector + tipo de liquidación + especialidad de revisión + categoría |
| `InspectorOperacionPeriodo` | `liquidaciones_inspectoroperacionperiodo` | Tramos de vigencia de una asignación |

`InspectorOperacion` guarda además `numero_registro`, que se compone
automáticamente como `CAM` + CIP sin ceros + categoría, y que junto con
`inspector` y `tipo_liquidacion` forma una clave única. Ese número es el
identificador con el que el inspector aparece en las listas operativas.

### 2.2.2 El ciclo de un período

`InspectorOperacionPeriodo` admite **un solo período abierto por asignación**.
La restricción está en el modelo, y el propio `save()` la verifica: si se
intenta abrir un segundo tramo sin cerrar el anterior, la operación falla con
el mensaje de que hay que cerrar el período vigente antes de abrir uno nuevo.

El helper `close_current_and_open_new(inspector_operacion, fecha_inicio)` hace
exactamente eso:

```
periodo_fin del tramo abierto = fecha_inicio − 1 día
nuevo periodo_inicio          = fecha_inicio
nuevo periodo_fin            = NULL (abierto)
```

Así, cambiar la operatividad de un inspector no borra nada: solo marca que a
partir de cierta fecha empieza (o deja de empezar) una asignación.

### 2.2.3 Cómo se eligen los candidatos

`InspectorCoreService.list_inspectores_vigentes_para_tipo(tipo, fecha, categoria, q)`
es el filtro que usa el formulario de creación de Inspección de Obra. Combina
tres condiciones:

1. `tipo_liquidacion.codigo == tipo_liquidacion` (obligatorio).
2. `especialidad_revision` presente en la asignación (siempre lo está).
3. **Período vigente a la fecha**: existe un `InspectorOperacionPeriodo` con
   `periodo_inicio <= fecha` y (`periodo_fin IS NULL` o `periodo_fin >= fecha`).

Sobre eso se aplican dos filtros opcionales de la pantalla: la **categoría**
(`io.categoria`) y una búsqueda libre (`q`) por nombres, apellidos o CIP.

El endpoint correspondiente en el backend es
`GET /inspectores/seleccionables`; el que devuelve todas las operatividades de
un inspector concreto es `GET /inspectores/seleccionables-por-cip`, que por
omisión incluye histórico y vigente y admite el parámetro `vigente` para
filtrar.

También existe `GET /inspectores/vigentes`, que devuelve inspectores con al
menos un período vigente **hoy**, filtrados por tipo de liquidación.

### 2.2.4 Volumen y composición reales

**220 inspectores**, **248 operatividades** y **283 períodos** registrados.

Tramos de período que existen en la base:

| Período | Períodos |
|---|---|
| 2026-08-01 → 2027-07-31 | 145 |
| 2025-08-01 → 2026-07-31 | 138 |

Composición por tipo, categoría y especialidad (los registros con **con
período** son operatividades que tienen al menos un tramo de vigencia
registrado):

| Tipo | Categoría | Especialidad | Operatividades | Con período |
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

*Datos de desarrollo consultados: 2026-11-08 18:01 (UTC−05:00)*

## 2.3 Delegados

### 2.3.1 Las tablas

| Modelo | Tabla física | Contenido |
|---|---|---|
| `Delegado` | `liquidaciones_delegado` | Persona habilitada como delegado (uno a uno con `PerfilIngeniero`) |
| `DelegadoOperacion` | `liquidaciones_delegadooperacion` | La asignación: delegado + municipalidad + tipo de liquidación + especialidad de revisión + rol |
| `DelegadoOperacionPeriodo` | `liquidaciones_delegadooperacionperiodo` | Tramos de vigencia de una asignación |

El rol se guarda en el campo `tipo`, con dos valores:

| Valor | Significado |
|---|---|
| `TITULAR` | Delegado titular de la operatividad |
| `ALTERNO` | Delegado alterno que cubre la misma operatividad |

La unicidad de la asignación está sobre `(delegado, municipalidad,
tipo_liquidacion)`.

### 2.3.2 El tipo de liquidación es parte de la operatividad

A diferencia del inspector, la operatividad del delegado **incluye el tipo de
liquidación** y ese campo tiene consecuencias directas:

- Es lo que determina **qué tasa se aplica** al calcular el RH mensual (ver
  [documento 03 §3.2](03-rh-mensual-y-reparto-estacional.md)). Sin tipo de
  liquidación no hay tasa aplicable.
- Es lo que define **el conjunto de liquidaciones candidatas** del delegado:
  se filtran por municipalidad, tipo y especialidad.

En la base de desarrollo, las 3 361 operatividades de delegado tienen tipo de
liquidación asignado.

### 2.3.3 El ciclo de un período

`DelegadoOperacionPeriodo` funciona igual que el del inspector: un solo
período abierto por asignación, `close_current_and_open_new()` para rotar el
tramo, y el mismo criterio de resolución (`periodo_inicio <= fecha` y
`periodo_fin IS NULL` o `>= fecha`).

### 2.3.4 Cómo se eligen los candidatos

El endpoint `GET /delegados/candidatas` devuelve las liquidaciones que un
delegado puede incorporar a su RH mensual. Tiene dos caminos de resolución:

**Camino 1 — por operatividad (SmartField).** Se manda
`delegado_operacion_id`. El sistema resuelve esa operatividad, comprueba que
pertenece al CIP indicado y que está vigente, y usa la municipalidad, el tipo
de liquidación y la especialidad de la operatividad para filtrar.

**Camino 2 — por filtros.** Se mandan `cip`, `municipalidad_id`,
`tipo_liquidacion_id` y `tipo_delegado`. El sistema exige que **exactamente
una** operatividad activa coincida con esos cuatro datos: si no encuentra
ninguna responde 404, y si encuentra varias responde 409.

Sobre el resultado se aplican filtros de búsqueda opcionales: `expediente`,
`numero`, `propietario`, `direccion`, `comprobante_serie`,
`comprobante_numero`, `documento`, y el rango `fecha_inicio` / `fecha_fin`
sobre la fecha de registro.

Otros endpoints del mismo dominio:

| Endpoint | Para qué |
|---|---|
| `GET /delegados/` | Listado de delegados |
| `GET /delegados/municipalidad/{municipalidad_id}?vigente=true` | Delegados de una municipalidad, con filtro de vigencia |
| `GET /delegados/tipos-liquidacion` | Tipos de liquidación para los desplegables |
| `GET /delegados/operatividades` | Operatividades del delegado |
| `GET /liquidaciones/delegados/vigentes` | Delegados vigentes para una liquidación |
| `GET /liquidaciones/delegados/vigentes-por-especialidad` | Delegados vigentes por especialidad |
| `GET /liquidaciones/delegados-asignaciones` | Asignaciones de delegado sobre liquidaciones |

### 2.3.5 Volumen y composición reales

**220 delegados**, **3 361 operatividades** y **1 506 períodos** registrados.

| Tipo | Rol | Operatividades | Períodos |
|---|---|---|---|
| `EDIFICACION` | `TITULAR` | 2 306 | 586 |
| `EDIFICACION` | `ALTERNO` | 545 | 548 |
| `HABILITACION_URBANA` | `TITULAR` | 335 | 188 |
| `HABILITACION_URBANA` | `ALTERNO` | 175 | 184 |

Tramos de período registrados:

| Período | Períodos |
|---|---|
| 2026-09-01 → 2027-08-31 | 753 |
| 2025-09-01 → 2026-08-31 | 753 |

Una operatividad real completa (municipalidad `L-80`):

| Tipo | Municipalidad | Rol | Especialidad | Período |
|---|---|---|---|---|
| `EDIFICACION` | L-80 | `TITULAR` | Ingeniería Civil | 2026-09-01 → 2027-08-31 |
| `EDIFICACION` | L-80 | `TITULAR` | Ingeniería Civil | 2025-09-01 → 2026-08-31 |
| `EDIFICACION` | L-80 | `TITULAR` | Ingeniería Eléctrica y Mecánica Eléctrica | 2025-09-01 → 2026-08-31 |
| `EDIFICACION` | L-80 | `ALTERNO` | Ingeniería Sanitaria | 2025-09-01 → 2026-08-31 |
| `EDIFICACION` | L-80 | `ALTERNO` | Ingeniería Eléctrica y Mecánica Eléctrica | 2025-09-01 → 2026-08-31 |
| `EDIFICACION` | L-80 | `ALTERNO` | Ingeniería Civil | 2026-09-01 → 2027-08-31 |

*Datos de desarrollo consultados: 2026-11-08 18:02 (UTC−05:00)*

## 2.4 Cómo se conecta la operatividad con el resto del sistema

```
Operatividad (InspectorOperacion / DelegadoOperacion)
      │
      │  + período vigente a la fecha
      ▼
Selección de candidatos (formularios de creación y de RH)
      │
      ▼
Asignación sobre la liquidación
   LiquidacionInspector  →  apunta a LiquidacionPorCategoriaVisitas
   LiquidacionDelegado   →  apunta a LiquidacionGeneral
      │
      ▼
RH mensual (documento 03)
   ReciboHonorarioInspectorMensual  →  inspector + escala de descuento
   ReciboHonorarioDelegadoMensual   →  delegado + operatividad + tasa
```

Los dos puntos de anclaje son explícitos en el modelo:

- `LiquidacionInspector.inspector_operacion_id` guarda **qué operatividad**
  contrató el inspector para esa liquidación. El RH mensual del inspector exige
  que todos sus ítems pertenezcan a la misma operatividad: si se mezclan
  operaciones distintas, la creación responde 409.
- `LiquidacionDelegado.delegado_operacion_id` guarda **qué operatividad** se
  usó. El RH mensual del delegado se construye sobre una operatividad
  concreta, y es esa operatividad la que fija el tipo de liquidación y, con
  él, la tasa aplicable.

## 2.5 Resumen operativo

| Pregunta | Dónde se responde |
|---|---|
| ¿Quién puede inspeccionar este tipo de liquidación? | `InspectorOperacion` + su período vigente |
| ¿En qué categorías puede operar? | `InspectorOperacion.categoria` |
| ¿Qué especialidad revisa? | `InspectorOperacion.especialidad_revision` |
| ¿Desde cuándo y hasta cuándo? | `InspectorOperacionPeriodo` |
| ¿Quién revisa liquidaciones en esta municipalidad? | `DelegadoOperacion.municipalidad` + período |
| ¿Qué tipo de liquidación cubre? | `DelegadoOperacion.tipo_liquidacion` |
| ¿Qué tasa se le aplica? | `TasaDelegado` del tipo (ver documento 03) |
| ¿Es titular o alterno? | `DelegadoOperacion.tipo` |
| ¿Cómo se rota una operatividad? | `close_current_and_open_new(…, fecha_inicio)` |
