# Liquidaciones Edificaciones: guia de refactor UI/UX, cotizacion e impresion

Este documento describe en detalle los cambios realizados en el flujo de **Liquidaciones de Edificaciones / Primera Revision**. La intencion es usarlo como referencia para aplicar el mismo criterio de UI, UX, cotizacion e impresion en otros tipos de liquidacion, sin copiar ciegamente reglas que son especificas de Edificaciones.

## Resumen Ejecutivo

Edificaciones paso de un flujo pesado y fragmentado a un formulario empresarial compacto, directo y orientado a crear una liquidacion de primera revision con menos friccion.

Los cambios principales fueron:

- Se consolido el formulario en dos secciones principales: `Datos del Tramite` y `Datos del Proyecto`.
- La cotizacion quedo dentro de `Datos del Tramite`, porque es parte del resultado economico del tramite.
- La cotizacion dejo de recalcularse por cada tecla; ahora se calcula al presionar `Enter` en `Valor del Proyecto`.
- Se oculto el boton manual de calcular dentro de este modal.
- Se agrego indicador cuando el valor actual ya no coincide con el valor usado para cotizar.
- Se simplifico la seleccion de revision/tarifa.
- Si solo hay una tarifa habilitada, se auto-selecciona y la seccion se oculta.
- Se quito la UI de proyectistas/supervisores en formulario, listas y detalles.
- Se mantuvo `proyectistas: []` en el payload para respetar contratos existentes.
- Despues de crear la liquidacion, se abre impresion directa del documento.
- El documento PDF/impresion cambio a un formato horizontal, compacto, monocromo y tipo recibo institucional.
- Backend ahora propaga `municipalidad.codigo` para que el documento pueda mostrar el `Codigo de Pago`, por ejemplo `L17`.

## Objetivo Del Cambio

El objetivo no fue solo embellecer la pantalla. Fue ordenar el flujo segun como trabaja realmente el usuario.

Antes, el usuario veia demasiadas secciones, informacion que no correspondia al flujo y un PDF tipo reporte que no se parecia a la liquidacion institucional esperada.

Despues, el flujo queda asi:

```text
Abrir Nueva Liquidacion
-> completar Datos del Tramite
-> elegir o auto-seleccionar tarifa
-> ingresar Valor del Proyecto
-> presionar Enter para cotizar
-> completar Datos del Proyecto
-> crear liquidacion
-> imprimir directamente el documento oficial
```

## Alcance Funcional

Este documento cubre:

- UI del formulario de Edificaciones.
- UX de cotizacion.
- Manejo de revision/tarifa.
- Campos visibles y campos eliminados.
- Flujo de contactos/personas.
- Flujo post-creacion.
- Impresion directa.
- Rediseño del documento PDF.
- Ajustes backend necesarios para datos institucionales.
- Reglas reutilizables para otros modulos.

## Archivos Principales

| Archivo | Responsabilidad |
|---------|-----------------|
| `frontend/src/features/liquidaciones/components/LiquidacionEdificacionesSingleFormModal.tsx` | Formulario principal de Edificaciones. |
| `frontend/src/features/liquidaciones/components/CotizacionSection.tsx` | UI de cotizacion, totales, contexto y estado pendiente. |
| `frontend/src/features/liquidaciones/components/RevisionesVigentesTable.tsx` | Selector compacto de revision/tarifa. |
| `frontend/src/features/liquidaciones/components/VariablesFinancierasCard.tsx` | Muestra IGV/UIT como metricas compactas. |
| `frontend/src/features/liquidaciones/components/ContactosSection.tsx` | Contactos compactos como chips. |
| `frontend/src/features/liquidaciones/components/EntidadLookupField.tsx` | Lookup y captura inline de entidad/propietario. |
| `frontend/src/components/genericForm/inputs/MoneyInput.tsx` | Input monetario inteligente con `onEnter`. |
| `frontend/src/features/liquidaciones/views/LiquidacionesEdificacionesView.tsx` | Vista principal, boton de nueva liquidacion y flujo post-creacion. |
| `frontend/src/features/liquidaciones/components/LiquidacionPDFModal.tsx` | Impresion directa y generacion PDF. |
| `backend/modules/liquidaciones/domain/schemas.py` | DTO de resultado con `municipalidad_codigo`. |
| `backend/modules/liquidaciones/domain/services/builders/liquidacion_edificaciones_result_builder.py` | Propaga `liquidacion.municipalidad.codigo`. |
| `backend/modules/liquidaciones/presentation/presenters/liquidacion_edificaciones_presenter.py` | Expone `MunicipalidadOut.codigo`. |

## Nueva Estructura Del Formulario

El formulario quedo con dos bloques grandes.

### 1. Datos Del Tramite

Este bloque contiene la parte administrativa y economica.

Distribucion conceptual:

```text
Datos del Tramite

Columna izquierda:
  Municipalidad
  Expediente
  Observacion

Columna derecha:
  Tipo de Tramite
  Valor del Proyecto
  Valor Declarado, si aplica

Fila completa:
  Revision / Tarifa, solo si hay mas de una opcion habilitada

Fila completa:
  Cotizacion
```

Decision importante:

La cotizacion esta dentro de `Datos del Tramite` porque representa el resultado economico del tramite. No debe sentirse como un paso separado ni como una tarjeta aislada.

### 2. Datos Del Proyecto

Este bloque contiene la informacion del proyecto, entidad y contactos.

Distribucion conceptual:

```text
Datos del Proyecto

Proyecto:
  Denominacion
  Direccion

Entidad:
  Tipo Documento
  Numero Documento / Buscar
  Nombre Completo
  Nombre del Propietario

Contactos:
  Agregar contacto
  Chips de contactos existentes
```

Decision importante:

El proyecto se crea inline. No hay busqueda por ID ni seleccion de proyecto existente en este flujo.

## UI/UX Aplicada

### Jerarquia Visual

Se redujo el ruido visual.

Cambios:

- Menos tarjetas grandes.
- Menos headers pesados.
- Bordes mas sutiles.
- Separacion compacta entre bloques.
- `gap-4` entre secciones principales.
- Cotizacion visible pero integrada.

Regla reusable:

```text
La pantalla debe guiar al usuario por prioridad funcional:
1. Tramite
2. Cotizacion
3. Proyecto
4. Contactos
```

### Campos En Mini-Grids

En componentes como `GenericInput`, cuando se usan en grillas compactas, se requiere:

```text
containerClassName: "min-w-0 w-full"
```

Motivo:

Sin esto, ciertos inputs pueden romper columnas, crecer de mas o desbordar el layout.

## Cotizacion

### Comportamiento Anterior

La cotizacion podia sentirse reactiva o demasiado acoplada al cambio de inputs.

Problemas:

- Calcular por cada tecla mete ruido.
- Puede disparar estados intermedios inutiles.
- Puede generar confusion si el usuario todavia esta escribiendo.
- El boton de calcular agregaba peso visual en un formulario que necesitaba ser mas directo.

### Comportamiento Nuevo

La cotizacion se calcula bajo demanda.

Reglas:

- El usuario escribe `Valor del Proyecto`.
- Presiona `Enter` en el `MoneyInput`.
- Se ejecuta `handleCotizar`.
- Se muestra el resultado de cotizacion.
- El boton calcular esta oculto en este modal.

### Estado Pendiente

Si el usuario cotiza con un valor y luego cambia el campo `Valor del Proyecto`, la cotizacion mostrada ya no representa el valor actual.

Por eso se agrego una comparacion entre:

```text
valorBaseActual
quote._metadata.valor_base_calculo
```

Si difieren, la UI muestra que la cotizacion esta pendiente de actualizar.

Regla reusable:

```text
Si la cotizacion es manual/on-demand,
la UI debe mostrar cuando el resultado mostrado esta desactualizado.
```

### Informacion Visible En Cotizacion

La cotizacion compacta muestra:

- Numero de revision.
- Valor usado para cotizar.
- Porcentaje de liquidacion.
- Especialidades asociadas.
- IGV.
- UIT.
- Subtotal.
- IGV calculado.
- Total.
- Total a pagar.

### Diferencias Con Otros Modulos

Edificaciones cotiza principalmente por porcentaje del valor de obra/proyecto.

Otros modulos pueden no funcionar igual.

Ejemplos:

| Modulo | Base posible de cotizacion |
|--------|-----------------------------|
| Edificaciones | Valor de obra/proyecto y porcentaje. |
| Habilitacion Urbana | Area, m2 o reglas por tipo de habilitacion. |
| Mecanica de Suelos | Area, m2, categoria o regla tecnica. |
| Impacto Vial | Area, nivel de impacto u otra base. |
| Taludes | m2, volumen, complejidad o regla especifica. |
| Inspeccion de Obra | Visitas, categoria, etapa o frecuencia. |

Regla:

No asumir que todos los modulos usan `valor_proyecto` como base unica. Primero identificar el dato que realmente dispara la cotizacion.

## Revision Y Tarifa

### Seleccion De Tarifa

La seccion `Revision / Tarifa` se rediseño para ser compacta y legible.

Cambios:

- Cards en fila en desktop.
- Wrapping natural cuando no entran.
- Badges de especialidades.
- Metricas resumidas.
- Menos altura vertical.

### Auto-Seleccion

Si solo hay una tarifa habilitada, se auto-selecciona.

Ademas, la seccion se oculta porque no hay decision que tomar.

Regla:

```text
Una UI no debe pedirle al usuario confirmar una unica opcion posible.
```

### Bug Corregido Al Reabrir Modal

Problema encontrado:

El modal no siempre se desmonta al cerrar. Entonces se limpiaba el valor seleccionado, pero quedaban flags internos como si la inicializacion ya hubiese ocurrido.

Resultado:

- Al reabrir, las revisiones ya estaban cacheadas.
- El auto-select no corria otra vez.
- El radio aparecia sin marcar.

Correccion:

- Auto-select corre solo cuando `open=true`.
- Al cerrar se resetea `hasInitializedRevisiones`.
- Al cerrar se resetea `lockedTarifaId`.

Regla reusable:

```text
Cuando un modal conserva estado entre aperturas,
hay que resetear valores visibles y tambien flags de inicializacion.
```

## Tipo De Tramite

Para primera liquidacion/revision de Edificaciones se limitaron las opciones visibles.

Opciones visibles:

- `OBRA_NUEVA`
- `DEMOLICION`
- `AMPLIACION`
- `REMODELACION`
- `REINTEGRO`

Opciones ocultas en este flujo:

- Modificacion de licencia.
- Proyecto con plantas tipicas.

Decision:

La restriccion se hizo a nivel UI del flujo, no cambiando enums globales.

Motivo:

Esas opciones pueden seguir existiendo para otros flujos o para datos historicos. Cambiar enums globales sin necesidad puede romper compatibilidad.

## Proyecto Inline

El flujo de Edificaciones no usa proyecto existente.

Reglas actuales:

- No hay busqueda de proyecto por ID.
- No hay selector de proyecto existente.
- No hay boton externo `Crear Proyecto`.
- Los datos del proyecto se capturan dentro del mismo formulario.
- El submit arma el payload con esos datos inline.

Motivo:

El usuario necesita liquidar rapido. Cambiar de contexto para buscar/crear proyecto agregaba friccion innecesaria.

## Entidad Y Propietario

`EntidadLookupField` quedo en dos columnas.

Layout:

```text
Columna izquierda:
  Tipo de Documento
  Numero de Documento + Buscar

Columna derecha:
  Nombre Completo
  Nombre del Propietario
```

Reglas:

- `Tipo de Documento` controla si se usa DNI/RUC.
- `Numero de Documento` mantiene busqueda.
- `Nombre Completo` se completa o edita segun corresponda.
- `Nombre del Propietario` queda visible junto a la entidad.

Motivo:

Entidad y propietario estan muy relacionados en este flujo. Separarlos demasiado hacia dificil entender que datos pertenecen a la misma persona/proyecto.

## Contactos

La seccion de contactos fue compactada.

Antes:

- Caja grande.
- Estado vacio demasiado prominente.
- Mucha altura para informacion auxiliar.

Ahora:

- Boton `Agregar contacto` compacto.
- Helper pequeño cuando no hay contactos.
- Contactos existentes como chips en `flex-wrap`.
- Acciones de editar/remover preservadas.

Motivo:

Contactos es informacion auxiliar. No debe competir visualmente con cotizacion ni datos del tramite.

## Proyectistas / Supervisores

Se quito la exposicion visual de proyectistas/supervisores en este flujo.

Cambios:

- No aparece seccion de proyectistas en el formulario de Edificaciones.
- No aparece contador/seccion de proyectistas en cards.
- No aparece bloque de proyectistas en detalles.
- No se agrego una UI nueva para proyectistas.
- El payload mantiene `proyectistas: []` para cumplir contratos.

Archivos afectados:

- `LiquidacionEdificacionesSingleFormModal.tsx`
- `LiquidacionGeneralCard.tsx`
- `LiquidacionDetalleCard.tsx`
- `LiquidacionListCard.tsx`
- `LiquidacionEdificacionCard.tsx`
- `LiquidacionDetalleCompleta.tsx`

Decision importante:

Quitar la UI no significa borrar el campo del dominio. Solo significa que este flujo no lo solicita al usuario.

Regla reusable:

```text
Si un campo existe por contrato pero no pertenece a la experiencia actual,
mantenerlo en el shape tecnico con valor seguro,
pero no mostrarlo en la UI.
```

Advertencia para otros modulos:

No quitar proyectistas/supervisores automaticamente en todos los modulos. Algunos flujos pueden necesitarlos funcionalmente.

## MoneyInput

El input de dinero se corrigio y mejoro.

Capacidades actuales:

- Mantiene string visual local.
- Envia numero al formulario.
- Acepta coma decimal.
- Formatea miles.
- Preserva cursor.
- Soporta `onEnter`.
- Si el usuario borra todo, vuelve a `S/ 0` y envia `0`.
- No permite valores negativos si el minimo es `0`.

Uso clave en Edificaciones:

```text
Valor del Proyecto
-> MoneyInput
-> onEnter={handleCotizar}
```

Motivo:

Los inputs monetarios no pueden tratarse como textos simples. Deben separar claramente valor visual y valor numerico del formulario.

## Zod, Defaults Y Payload

Se corrigieron problemas de validacion donde campos no visibles igual eran requeridos por el schema.

Reglas aplicadas:

- `GenericForm<FormData>` usa `formMethods={formMethods}`.
- `defaultValues` incluye `proyectistas: []`.
- `initialData` incluye `proyectistas: []`.
- Al abrir modal se asegura que `proyectistas` sea array.
- El payload final envia `proyectistas: []`.

Motivo:

El usuario no debe llenar campos invisibles, pero el contrato tecnico debe seguir recibiendo un shape valido.

## Flujo Post-Creacion

El flujo post-creacion cambio para imprimir inmediatamente.

Antes:

```text
Crear liquidacion
-> cerrar modal
-> refrescar lista
```

Ahora:

```text
Crear liquidacion
-> cerrar modal
-> refrescar lista
-> imprimir documento directamente
```

Implementacion:

- `LiquidacionEdificacionesSingleFormModal` recibe `onCreated`.
- Al crear, devuelve la liquidacion creada al padre.
- `LiquidacionesEdificacionesView` adapta la respuesta a formato compatible con PDF.
- Se llama `printLiquidacionDocument(...)`.

Decision:

No se abre un modal intermedio de preview. Se imprime directo.

Motivo:

El usuario espera generar la liquidacion y entregar/imprimir el documento inmediatamente.

## PDF E Impresion

### Cambio Principal

El documento dejo de verse como reporte moderno y paso a parecer un recibo/liquidacion institucional antigua.

Caracteristicas:

- Horizontal.
- Compacto.
- Monocromo.
- Tipo media hoja / recibo administrativo.
- Encabezado CIP/CAM.
- Bloque `IMPORTANTE`.
- `CTA 46201`.
- `Codigo de Pago` basado en `municipalidad.codigo`.
- Datos del contribuyente/proyecto en formato administrativo.
- Totales claros.
- `TOTAL A PAGAR` destacado.
- Mensaje `ESTE DOCUMENTO NO ES COMPROBANTE DE PAGO`.

### Impresion Directa

Funcion exportada:

```text
printLiquidacionDocument(item)
```

Flujo:

```text
Crear iframe oculto
-> escribir documento HTML aislado
-> esperar carga de imagenes
-> ejecutar window.print()
-> limpiar iframe
```

### Descargar PDF

La descarga usa:

```text
jsPDF("l", "mm", "a4")
```

Esto mantiene orientacion horizontal.

### Boton PDF En Cards

El boton `PDF` ya no abre un modal pesado.

Ahora llama directo:

```text
printLiquidacionDocument(item)
```

## Codigo De Pago / Municipalidad

Se corrigio la propagacion del codigo de municipalidad.

Problema:

El PDF necesitaba mostrar `Codigo de Pago`, pero `municipalidad.codigo` llegaba como `null` porque backend no lo estaba propagando.

Correccion backend:

- `LiquidacionEdificacionesResult` agrego `municipalidad_codigo`.
- El builder asigna `liquidacion.municipalidad.codigo`.
- El presenter usa ese valor al construir `MunicipalidadOut`.

Resultado esperado:

```text
Codigo de Pago L17
```

Si no hay codigo:

```text
Codigo de Pago —
```

## Que Se Puede Reutilizar En Otros Modulos

Patrones reutilizables:

- Formularios con pocas secciones reales.
- Cotizacion dentro de Datos del Tramite.
- Auto-seleccion si solo hay una tarifa habilitada.
- Ocultar selector si no hay decision.
- Indicador de cotizacion pendiente.
- `MoneyInput` con `onEnter`.
- Contactos compactos.
- Post-creacion con impresion directa.
- Documento de impresion institucional.
- Mantener campos tecnicos en payload aunque no se muestren.

## Que No Se Debe Copiar Ciegamente

No copiar sin validar:

- Base de calculo de cotizacion.
- Campos visibles del formulario.
- Eliminacion de proyectistas/supervisores.
- Texto exacto del PDF.
- Campos institucionales del documento.
- Opciones visibles de tipo de tramite.
- Reglas de tarifa unica.

Cada modulo puede tener reglas propias.

## Guia Para Migrar Otra Liquidacion

Antes de tocar otro modulo, responder estas preguntas:

- Que dato dispara la cotizacion?
- La cotizacion debe ser por Enter, por boton o reactiva?
- La tarifa depende de revision, m2, visitas, area, categoria u otro factor?
- Hay una sola tarifa posible o varias?
- Que personas son realmente necesarias: propietario, contactos, proyectistas, supervisores, delegados?
- Que campos son obligatorios por schema aunque no aparezcan en UI?
- El PDF debe usar el mismo formato de Edificaciones o uno adaptado?
- El backend ya devuelve todos los datos necesarios para imprimir?

## Checklist De Replica

- [ ] Identificar el flujo real del usuario.
- [ ] Reducir secciones principales a las necesarias.
- [ ] Colocar cotizacion donde corresponda funcionalmente.
- [ ] Definir el evento de cotizacion.
- [ ] Mostrar estado pendiente si la cotizacion no esta actualizada.
- [ ] Auto-seleccionar tarifa unica habilitada.
- [ ] Ocultar selectores sin decision real.
- [ ] Mantener payload compatible con backend.
- [ ] Quitar campos visuales que no pertenecen al flujo.
- [ ] No borrar campos de dominio sin revisar compatibilidad.
- [ ] Normalizar datos antes de imprimir.
- [ ] Imprimir directamente despues de crear si ese es el flujo esperado.
- [ ] Validar que el PDF tenga datos institucionales completos.
- [ ] Probar creacion, cotizacion, impresion y listado.

## Verificaciones Realizadas

Backend:

```bash
python -m py_compile backend/modules/liquidaciones/domain/schemas.py backend/modules/liquidaciones/domain/services/builders/liquidacion_edificaciones_result_builder.py backend/modules/liquidaciones/presentation/presenters/liquidacion_edificaciones_presenter.py
```

Resultado:

```text
OK
```

Frontend:

```bash
npx tsc --noEmit
```

Resultado conocido:

```text
Falla por errores preexistentes en deprecadedForm.tsx:
- TS2694: tipoTramiteEdificacionesSchema
- TS2304: hasProject
```

Nota:

`deprecadedForm.tsx` no debe usarse como fuente funcional de este refactor ni modificarse salvo pedido explicito.
