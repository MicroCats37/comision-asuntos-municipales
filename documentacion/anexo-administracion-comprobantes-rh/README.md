# CAM — Anexo de administración, comprobantes y RH

Anexo de operación de la Comisión de Asuntos Municipales (CAM). Cubre tres frentes
concretos que la guía general ([Guía operativa](../guia-operativa/README.md)) presenta de forma
resumida y que aquí se desarrollan con el detalle de tablas, campos, rutas y
consultas que un operador necesita para ejecutarlos:

1. **Administración de vigencias y catálogos** — qué se configura, dónde vive,
   cómo se resuelve una vigencia y dónde se administra cada catálogo.
2. **Comprobantes de liquidación por SQL** — cómo localizar una liquidación por
   `CTA + tipo + número + legacy = false` y registrar un comprobante directamente
   en PostgreSQL.
3. **Continuidad RH de inspectores** — cómo se evita superar el saldo de visitas
   de una Inspección de Obra y cómo se registran visitas históricas.

## Cómo leerlo

El orden es deliberado: **primero el catálogo que se administra, después el
procedimiento que lo consume**.

| Orden | Documento | Qué responde |
|---|---|---|
| 1 | [01 - Administración de vigencias y catálogos](01-administracion-de-vigencias-y-catalogos.md) | ¿Qué catálogos existen, qué tabla física sostiene cada uno, cómo se aplica su vigencia y dónde se administra? |
| 2 | [02 - Comprobantes de liquidación por SQL](02-comprobantes-de-liquidacion-por-sql.md) | ¿Cómo se localiza una liquidación por CTA + tipo + número y cómo se da de alta un comprobante por SQL? |
| 3 | [03 - Continuidad RH de inspectores](03-continuidad-rh-de-inspecciones.md) | ¿Cómo se controla el saldo de visitas de una IO y cómo se registran visitas históricas? |

### Tres ideas que se arrastran por todo el anexo

1. **La vigencia es un par de fechas, no un flag.** `periodo_inicio` y
   `periodo_fin` con `periodo_fin IS NULL` significan "abierto". La resolución
   siempre es "el registro vigente en la fecha de referencia".
2. **El catálogo se congela al calcular.** Una liquidación guarda qué tarifa,
   derecho, UIT e IGV se aplicaron. Editar el catálogo no reescribe liquidaciones
   ya calculadas.
3. **El saldo es un libro, no un campo.** El saldo de visitas de una IO no se
   almacena: se obtiene restando el libro de pagos (`RegistroPagoInspector`) a
   las visitas programadas.

## Relación con la guía operativa

[Guía operativa](../guia-operativa/README.md) es la **guía general recomendada**: explica qué
guarda CAM, cómo se calcula una liquidación, cómo funciona la operatividad de
inspectores y delegados y cómo se arma el RH mensual, con datos reales como
hilo conductor.

Este es un **anexo operativo**, no una sustitución de la guía general. Su alcance es:

| Tema | En la guía operativa | En este anexo |
|---|---|---|
| Catálogos y vigencias | Referencia del catálogo con sus valores ([00](../guia-operativa/00-datos-operativos-de-referencia.md)) | Modelo, tabla física, campos de operación, regla de vigencia y ruta de administración de cada catálogo ([01](01-administracion-de-vigencias-y-catalogos.md)) |
| Comprobantes | Se menciona el comprobante como parte del flujo de liquidación ([01](../guia-operativa/01-liquidaciones-flujo-operativo.md)) | Procedimiento autocontenido para localizar una liquidación y registrar un comprobante por SQL ([02](02-comprobantes-de-liquidacion-por-sql.md)) |
| RH de inspectores | Se explica el cálculo y la persistencia del RH mensual ([03](../guia-operativa/03-rh-mensual-y-reparto-estacional.md)) | El mecanismo del saldo de visitas, las consultas de diagnóstico y el procedimiento de registro de visitas históricas ([03](03-continuidad-rh-de-inspecciones.md)) |

Los documentos históricos beta-3, beta-2 y beta-1 se conservan sin cambios.
La entrada del conjunto sigue siendo [`documentacion/README.md`](../README.md).

## Convenciones

- **Nombre de modelo** (`TarifaLiquidacionBase`) y **nombre físico de tabla**
  (`liquidaciones_tarifaliquidacionbase`) se indican juntos.
- **Los importes** se muestran en soles (S/), con los decimales que el sistema
  persiste. Los porcentajes de tasa se guardan como fracción decimal
  (`0.0015` = 0,15 %).
- **Los ejemplos** son registros reales de la base de desarrollo, con personas
  anonimizadas: no se muestran nombres, CIP, DNI, correos, teléfonos ni datos
  bancarios.
- Cada bloque de ejemplos va precedido de la marca
  **Datos de desarrollo consultados: 2026-11-10 13:51 (UTC)**, que indica el
  momento de la consulta a la base.
- Las rutas administrativas se indican con la URL del Django admin tal como la
  registra el backend, y las pantallas del frontend con su ruta de navegación.
- Las consultas SQL de solo lectura van marcadas como **Solo lectura**; la
  única Sentencia de inserción del anexo va marcada como **Inserción** dentro de
  una plantilla transaccional.

## Origen de los datos de este anexo

| Aspecto | Detalle |
|---|---|
| Base de datos | Contenedor Docker `postgres_prueba`, PostgreSQL 16.14, base `cam_db_prueba` |
| Modo de acceso | Solo lectura (`SELECT` e inspección de esquema vía `docker exec … psql`) |
| Ventana de consulta | 2026-11-10, 13:38 – 13:51 (UTC) |
| Backend | `backend/modules/{liquidaciones,finanzas,usuarios,entidades}`, Django + Django Ninja |
| Frontend | `frontend/src/features/{liquidaciones,finanzas,inspectores}`, Next.js |
| Contratos leídos | `contract/django-app-architecture-contract.md`, `contract/next-app-architecture-contract.md` |
