# CAM — Guía funcional de operación

Guía de alto nivel para **comprender y operar la Comisión de Asuntos Municipales
(CAM)**: liquidaciones, operatividad de inspectores y delegados, y Recursos
Humanos (RH mensual y reparto estacional).

La guía está escrita a partir del código real del backend (Django + Django
Ninja), del frontend (Next.js) y de la base de datos PostgreSQL de desarrollo.
Todos los importes, tarifas, vigencias, códigos, conteos y fechas que aparecen
como ejemplo provienen de consultas de solo lectura a esa base.

## Cómo leerla

El orden es deliberado: **primero los datos, después los procesos**. Los datos
que un flujo necesita están descritos en el documento 00; los documentos 01 a 03
explican qué hace el sistema con ellos y remiten a la sección del documento 00
que corresponde.

| Orden | Documento | Qué responde |
|---|---|---|
| 1 | [00 — Datos operativos de referencia](00-datos-operativos-de-referencia.md) | ¿Qué se guarda, dónde vive y qué valores tiene? Tarifas, vigencias, derechos, UIT/IGV, especialidades, operatividad, escalas, tasas y reparto. |
| 2 | [01 — Liquidaciones: flujo operativo](01-liquidaciones-flujo-operativo.md) | ¿Cómo se crea, revisa, comprueba y da de baja una liquidación, y cómo una fecha determina la tarifa que se aplica? |
| 3 | [02 — Operatividad de inspectores y delegados](02-operatividad-de-inspectores-y-delegados.md) | ¿Quién puede operar, en qué tipo de liquidación, municipalidad, especialidad y rango de fechas? |
| 4 | [03 — RH mensual y reparto estacional](03-rh-mensual-y-reparto-estacional.md) | ¿Cómo se calcula el honorario de un inspector o delegado en un mes, cómo se persiste y cómo se reparte el fondo común? |

### Tres ideas para carry por toda la guía

1. **La fecha manda.** almost todo lo que el sistema cobra o paga depende de un
   rango de vigencia (`periodo_inicio` / `periodo_fin`) resuelto con una fecha
   efectiva. La fecha efectiva es la fecha de registro de la liquidación, y en
   las cotizaciones es la que envía la pantalla.
2. **El catálogo se congela en el momento del cálculo.** La liquidación guarda
   qué tarifa, qué derecho, qué UIT y qué IGV se aplicaron. Editar o recotizar
   no reescribe ese pasado: usa los valores vigentes a la fecha de registro.
3. **Los importes se reparten, no se inventan.** Cuando varios participantes
   (especialidades, delegados, capítulos) intervienen, el sistema reparte el
   total con aritmética de céntimos y deja el residuo absorbedido, de modo que
   la suma de las partes siempre cuadra con el total.

## Convenciones

- **Nombre de modelo** (`TarifaLiquidacionBase`) y **nombre físico de tabla**
  (`liquidaciones_tarifaliquidacionbase`) se indican juntos. Los nombres de
  tabla que aparecen aquí se han comprobado por inspección del esquema de la
  base de datos de desarrollo.
- **Los importes** se muestran en soles (S/), con los decimales que el sistema
  persiste.
- **Los ejemplos** son registros reales, con personas anonimizadas: no se
  muestran nombres, CIP, DNI, correos ni números de expediente.
- Cada bloque de ejemplos va precedido de la marca
  **«Datos de desarrollo consultados: &lt;timestamp&gt;»**, que indica el
  momento de la consulta a la base.
- Las referencias a pantallas y endpoints se dan solo cuando ayudan a
  entender el flujo.

## Origen de los datos de esta versión

| Aspecto | Detalle |
|---|---|
| Base de datos | Contenedor Docker `cam_db`, imagen `postgres:16-alpine`, base `cam_db`, usuario `cam_user` |
| Modo de acceso | Solo lectura (`SELECT` e inspección de esquema vía `docker exec … psql`) |
| Ventana de consulta | 2026-11-08, 17:59 – 18:07 (UTC−05:00) |
| Backend | `backend/modules/{liquidaciones,finanzas,usuarios,entidades}`, Django + Django Ninja |
| Frontend | `frontend/src/features/{liquidaciones,finanzas,inspectores,delegados}`, Next.js |

## Versiones anteriores

Las entregas beta-1, beta-2 y beta-3 se conservan en esta carpeta y cubren el
sistema con otro corte y otro nivel de detalle. La referencia de entrada del
conjunto está en [`documentacion/README.md`](../README.md).
