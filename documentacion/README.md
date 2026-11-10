# Documentación — Comisión de Asuntos Municipales (CAM)

Esta carpeta contiene la documentación funcional del sistema CAM, dividida en
cinco versiones según su alcance y su organización.

> **El código es la fuente de verdad.** Si un documento y el código discrepan, el
> código gana y el documento es incorrecto. Ninguna afirmación de estos archivos
> debe tratarse como especificación normativa sin contrastarla contra el
> repositorio.

## Versiones

| Versión | Qué es | Enfoque |
|---|---|---|
| **[Guía operativa](guia-operativa/README.md)** | **Guía general recomendada.** Guía de alto nivel para comprender y operar CAM: liquidaciones, operatividad de inspectores y delegados, y RH mensual con reparto estacional. Los datos operativos se presentan primero, con ejemplos reales extraídos en modo solo lectura de la base de datos de desarrollo, y los flujos enlazan a esas secciones. | Operativo y didáctico: el catálogo de datos (tarifas, vigencias, derechos, UIT/IGV, especialidades, operatividad, escalas, tasas, reparto) antes que los procesos, con cifras reales como hilo conductor. |
| **[Anexo de administración, comprobantes y RH](anexo-administracion-comprobantes-rh/README.md)** | **Anexo operativo recomendado.** Complementa a la guía general con el detalle de ejecución de tres frentes concretos: la administración de vigencias y catálogos, el alta de comprobantes de liquidación por SQL y la continuidad del RH de inspectores. | Operativo y de ejecución: tablas, columnas, claves foráneas, restricciones, rutas administrativas, pantallas y consultas SQL verificadas contra el esquema real de la base de datos. |
| **[beta-3](beta-3/README.md)** | Tercera versión. Organiza la guía en el orden en que se necesita: primero una referencia de datos (modelos, tablas, campos, relaciones, nulabilidad, restricciones y vigencias) y después los workflows que la usan. | Didáctico y verificado: los datos primero, los procesos después; cada endpoint tiene un consumidor frontend comprobado y una ruta `ruta:línea` de frontend y backend. |
| **[beta-1](beta-1/README.md)** | Primera versión de la documentación funcional. Describe el dominio por módulos (usuarios, liquidaciones, operatividad, RH) leyendo el backend completo: modelos, servicios, flujos, orquestadores y controladores. | Amplio: describe el sistema, incluyendo superficie que no está conectada a una pantalla. |
| **[beta-2](beta-2/README.md)** | Segunda versión. Documenta **solo** lo que está enlazado a pantallas del frontend: cada endpoint se llega desde una pantalla real, se verifica contra el handler del backend y se traza hasta sus modelos. | Verificado: cada endpoint tiene una pantalla consumidora confirmada y una ruta `ruta:línea` de frontend y backend. |

### Cuál usar

- **Guía operativa** para comprender y operar el sistema: qué reglas de cobro y de pago
  están configuradas, qué hace cada flujo y con qué cifras reales se comporta.
  Es la versión general recomendada.
- **Anexo de administración, comprobantes y RH** para ejecutar las tareas administrativas y operativas con el detalle
  de tablas, columnas, restricciones, rutas y consultas: administración de
  vigencias y catálogos, alta de comprobantes por SQL y continuidad del RH de
  inspectores. Es el anexo operativo recomendado.
- **beta-3** para el detalle campo por campo de los modelos, las relaciones y
  las restricciones, con referencias de línea en frontend y backend.
- **beta-1** para entender el modelo de dominio completo y la arquitectura por
  capas (incluye endpoints, modelos y flujos sin consumidor de UI confirmado).
- **beta-2** para saber **qué pantalla llama a qué endpoint**, qué persiste cada
  endpoint y bajo qué condición de vigencia opera.

La diferencia entre documentos no es de redacción: es de alcance y de orden de
lectura. beta-2 y beta-3 se centran en la trazabilidad entre pantalla, endpoint
y modelo. La guía operativa se centra en la operación: parte del catálogo real
de datos y explica qué se calcula, se guarda y se paga con él. El anexo baja un
nivel más y entrega el procedimiento ejecutable de los tres frentes que un
operador necesita: catálogos, comprobantes y continuidad de inspectores.

## Anexo de administración, comprobantes y RH

| Documento | Alcance |
|---|---|
| [README — Anexo operativo](anexo-administracion-comprobantes-rh/README.md) | Orden de lectura, relación con la guía operativa, convenciones y origen de los datos del anexo. |
| [01 — Administración de vigencias y catálogos](anexo-administracion-comprobantes-rh/01-administracion-de-vigencias-y-catalogos.md) | El concepto único de vigencia y los diez catálogos que la usan: tarifas base (porcentuales, metro cuadrado y visitas), derechos mínimos, IGV, UIT, escalas de descuento del inspector, tasas de delegado y especialidades de liquidaciones, con su modelo, tabla física, campos, regla de vigencia y ruta de administración. |
| [02 — Comprobantes de liquidación por SQL](anexo-administracion-comprobantes-rh/02-comprobantes-de-liquidacion-por-sql.md) | Referencia autocontenida para localizar una liquidación por `CTA + tipo + número + legacy = false` y registrar un comprobante por SQL: catálogo de CTA y su CTA repetido, corte de numeración legacy/no-legacy, anatomía física de la tabla de comprobantes con sus FK y su índice único parcial, consultas de solo lectura, plantilla transaccional de inserción y checklists de ejecución y validación. |
| [03 — Continuidad RH de inspectores](anexo-administracion-comprobantes-rh/03-continuidad-rh-de-inspecciones.md) | Cómo se controla el saldo de visitas de una IO: tablas de visitas programadas, libro de pagos y RH mensual, la aritmética del saldo y las validaciones que impiden superarlo, consultas SQL de diagnóstico, y el procedimiento de registro de visitas históricas por admin. |

## Guía operativa

| Documento | Alcance |
|---|---|
| [00 — Datos operativos de referencia](guia-operativa/00-datos-operativos-de-referencia.md) | Catálogo operativo: tipos de liquidación, patrón de vigencia, UIT e IGV, tarifas (metro cuadrado, categoría de visitas, porcentaje de obra), derechos, especialidades y especialidades habilitadas, operatividad de inspectores y delegados, escala y rangos de descuento, tasas de delegado, capítulos, liquidaciones y sus tablas de detalle, comprobantes, relaciones y asignaciones. |
| [01 — Liquidaciones: flujo operativo](guia-operativa/01-liquidaciones-flujo-operativo.md) | Del formulario a la persistencia: cómo la fecha efectiva selecciona tarifa, vigencia, especialidad y derechos, los tres motores de cálculo (M2, categoría de visitas, porcentaje de obra), creación, revisiones, comprobantes, estado, asignación de inspectores y delegados y baja lógica. |
| [02 — Operatividad de inspectores y delegados](guia-operativa/02-operatividad-de-inspectores-y-delegados.md) | Asignaciones y períodos de vigencia de cada perfil, criterios de selección de candidatos, vínculo con las asignaciones sobre liquidaciones y con el RH mensual. |
| [03 — RH mensual y reparto estacional](guia-operativa/03-rh-mensual-y-reparto-estacional.md) | Cálculo y persistencia del RH mensual de inspector y de delegado, congelamiento de escala y tasa, libro de inspecciones pagadas, edición y borrado, y reparto del fondo común entre delegados y capítulos. |

## Documentos de beta-3

| Documento | Alcance |
|---|---|
| [00 — Modelos, tablas y campos](beta-3/00-modelos-tablas-y-campos.md) | Referencia de datos por dominio: usuarios, entidades, liquidaciones, operatividad y RH/reparto. Es el primer documento del orden de lectura. |
| [01 — Usuarios, sesión y permisos](beta-3/01-usuarios-flujo.md) | Login modular (username/DNI/email), ciclo de vida del token, cookies de sesión, guard de acceso, verificación de habilitación CIP y administración de usuarios e identidad profesional. |
| [02 — Liquidaciones](beta-3/02-liquidaciones-flujo.md) | Tipos y motores de cálculo, resolución de vigencias y tarifas, cotización, creación (primera revisión, legacy, nueva revisión, relacionada), edición, comprobantes, revisiones y relaciones, estados y baja lógica. |
| [03 — Operatividad](beta-3/03-operatividad-flujo.md) | Períodos de operatividad y vigencias, selección de inspectores y delegados, asignación a liquidaciones y vínculo confirmado con el RH. |
| [04 — RH y reparto](beta-3/04-rh-y-reparto-flujo.md) | RH mensual de inspector y de delegado, resolución de escalas y tasas vigentes, detalle y persistencia, y reparto estacional del fondo común. |

## Documentos de beta-2

| Documento | Alcance |
|---|---|
| [01 — Usuarios y sesión](beta-2/01-usuarios-y-sesion.md) | Login modular (username/DNI/email), ciclo de vida del token, cookies de sesión, persistencia de usuario e identidad profesional. |
| [02 — Liquidaciones por endpoint](beta-2/02-liquidaciones-por-endpoint.md) | Pantallas de liquidaciones por tipo: listado, detalle, tarifas, cotización, creación, revisión, relación, comprobantes, eliminados y códigos. |
| [03 — Operatividad por endpoint](beta-2/03-operatividad-por-endpoint.md) | Inspectores y delegados: catálogo, operatividad con vigencia, selección para IO y conexión con liquidaciones y RH. |
| [04 — RH y reparto por endpoint](beta-2/04-rh-y-reparto-por-endpoint.md) | RH mensual de inspector y delegado, detalle, candidatas, persistencia, y reparto estacional del fondo común. |

## Reglas de elaboración aplicadas

- No se ha utilizado `doc_app/` ni `docs/` como fuente de hechos.
- Se leyó `contract/` (contratos de arquitectura) antes de explorar.
- No se ejecutaron tests, builds, servidores ni migraciones.
- No se modificó código.
- En beta-1, beta-2 y beta-3 cada afirmación relevante incluye referencia
  exacta `ruta:línea` de frontend y backend.
- Los nombres de tabla física se declaran **solo** cuando están definidos
  explícitamente en el código; en caso contrario se marca
  `tabla física no confirmada estáticamente`. En beta-3 la marca global es
  `nombre físico de tabla no declarado en el modelo`.
- En la guía operativa los nombres físicos de tabla se han confirmado por inspección del
  esquema de la base de datos de desarrollo, y los ejemplos numéricos provienen
  de consultas de solo lectura a esa misma base.
- En el anexo operativo los nombres físicos de tabla, columnas, claves foráneas,
  restricciones e índices se han confirmado por inspección del esquema de la base
  de datos de desarrollo (PostgreSQL 16.14, base `cam_db_prueba` del contenedor
  `postgres_prueba`), consultada en modo solo lectura el 2026-11-10 entre las
  13:38 y las 13:51 (UTC). Las consultas SQL de solo lectura se presentan
  verificadas; la plantilla de inserción de comprobantes se entrega como
  script transaccional con guardas, sin formar parte de ninguna ejecución
  automatizada.
