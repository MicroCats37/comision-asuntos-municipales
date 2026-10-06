# Resumen de problemas con la seed de Municipalidades

> Documento de referencia para entrega/auditoría de la seed de `Municipalidad`.
> Ubicación: `backend/modules/entidades/seeds/RESUMEN_PROBLEMAS_SEED_MUNICIPALIDADES.md`.

## Contexto

El sistema CAM tiene una seed de municipalidades en `backend/modules/entidades/seeds/municipalidades.json` con **78 entradas** (`codigo` + `nombre`) que actualmente se cargan **sin asignar el distrito ni la provincia** (las FK quedan en `NULL`). El comentario en el comando de seed dice literalmente:

> *"provincia/distrito quedan null (se asignan en una fase posterior si aplica)"*

Esa fase se está ejecutando ahora. Este documento lista los hallazgos y el formato esperado para la entrega de seeds corregidas.

## Datos disponibles

- ✅ `UbigeoDepartamento`, `UbigeoProvincia`, `UbigeoDistrito` ya están cargados en la DB desde `backend/utils/ubigeo.json` (vía `python manage.py load_ubigeo`).
- ✅ Las **78 entradas** de `municipalidades.json` corresponden al **departamento LIMA** (provincias: BARRANCA, CAJATAMBO, CAÑETE, CANTA, HUARAL, HUAROCHIRI, HUAURA, LIMA, OYON, YAUYOS).
- ✅ El modelo `Municipalidad` (`backend/modules/entidades/domain/models/municipalidad.py`) tiene FK `provincia` y `distrito` apuntando a `UbigeoProvincia` y `UbigeoDistrito`.
- ⚠️ `Municipalidad.clean()` impide asignar `provincia` y `distrito` simultáneamente — son mutuamente excluyentes. La asignación es a nivel **distrito** para todas las entradas, ya que cada una representa una municipalidad distrital (no provincial-capital).

## Hallazgos

### 1. Duplicado confirmado (1 caso)

El distrito **LIMA / LIMA** (provincia LIMA) tiene **2 entradas** en el seed:

| codigo | nombre legacy |
|---|---|
| L1 | CERCADO DE LIMA |
| L1-2 | CENTRO HISTÓRICO DE LIMA |

Es el único distrito con más de una municipalidad. El modelo lo permite, así que la pregunta de negocio es si se quieren mantener ambas (caso de uso: dos admins distintos para el mismo distrito) o consolidar (caso Centro Histórico = alias del Cercado). **Hace falta una decisión.**

### 2. Entrada no resoluble (1 caso)

| codigo | nombre | observación |
|---|---|---|
| L1-1 | COMISION AD HOC SEGUNDA INSTANCIA ADMINISTRATIVA | No es una municipalidad real, es una entidad administrativa. No tiene distrito en el ubigeo. Queda con `distrito = NULL` y `provincia = NULL`. |

### 3. Mismatches de nombre legacy vs. ubigeo canónico (5 casos)

El `nombre` en la seed es **legacy** (proviene del sistema DEVCOMU). El nombre canónico en `UbigeoDistrito.nombre` difiere en 5 casos. La regla es: **NO tocar el `nombre` legacy** (es para display), pero internamente la FK debe apuntar al nombre canónico. Mapeos:

| codigo | nombre legacy (display) | distrito canónico (FK) |
|---|---|---|
| L3 | ATE VITARTE | ATE |
| L15 | LURIGANCHO - CHOSICA | LURIGANCHO |
| SINCODE3 | 27 DE NOVIEMBRE | VEINTISIETE DE NOVIEMBRE |
| L70-2 | SUPE - PUERTO | SUPE PUERTO |
| L80-1 | SAN ANTONIO DE HUAROCHIRI | SAN ANTONIO |

### 4. Gaps en la numeración legacy

Los códigos legacy tienen gaps (L17 → L18, L19 → L20, L31 → L32, etc. no son estrictamente consecutivos). Hay códigos `SINCODE1` a `SINCODE5` que rellenan huecos. **No es funcional**, solo observación.

### 5. Decisiones pendientes

| Tema | Opciones | Recomendación |
|---|---|---|
| Duplicado L1 + L1-2 sobre `LIMA/LIMA` | (a) Consolidar: borrar L1-2. (b) Mantener ambas con la misma FK. | **(a)** consolidar, salvo que haya razón administrativa real para mantener la Comisión Ad Hoc como "municipalidad" separada. |
| L1-1 (no resoluble) | Dejar con FKs en NULL | Mantener (no es un bug, es una entrada administrativa sin ubigeo). |
| ¿Normalizar `nombre` al canónico? | (a) Sí — alinear a `ATE`, `LURIGANCHO`, etc. (b) No — mantener legacy para display. | **(b)** mantener legacy; la FK se linkea al canónico, pero el `display` no cambia. |

## Formato esperado de la seed

Cada entrada debe tener **4 campos**:

```json
{
  "codigo": "L1",
  "nombre": "CERCADO DE LIMA",
  "provincia_nombre": "LIMA",
  "distrito_nombre": "LIMA"
}
```

| Campo | Criterio |
|---|---|
| `codigo` | Se mantiene como está (legacy). |
| `nombre` | Se mantiene el legacy para display. NO normalizar. |
| `provincia_nombre` | Nombre canónico según `UbigeoProvincia.nombre` (depto LIMA). |
| `distrito_nombre` | Nombre canónico según `UbigeoDistrito.nombre`. |

Las **76 entradas resolubles** deben traer estos 4 campos. Solo `L1-1 COMISION AD HOC SEGUNDA INSTANCIA ADMINISTRATIVA` queda sin `provincia_nombre` / `distrito_nombre` (es la única no resoluble).

## Tabla de mapeo esperada (76 entradas)

### Lima provincia (43 L1-L43 + 1 duplicado L1-2 + 1 L15-1)

| codigo | nombre (legacy, display) | provincia_nombre | distrito_nombre |
|---|---|---|---|
| L1 | CERCADO DE LIMA | LIMA | LIMA |
| L2 | ANCON | LIMA | ANCON |
| L3 | ATE VITARTE | LIMA | ATE |
| L4 | BARRANCO | LIMA | BARRANCO |
| L5 | BREÑA | LIMA | BREÑA |
| L6 | CARABAYLLO | LIMA | CARABAYLLO |
| L7 | COMAS | LIMA | COMAS |
| L8 | CHACLACAYO | LIMA | CHACLACAYO |
| L9 | CHORRILLOS | LIMA | CHORRILLOS |
| L10 | EL AGUSTINO | LIMA | EL AGUSTINO |
| L11 | JESUS MARIA | LIMA | JESUS MARIA |
| L12 | LA MOLINA | LIMA | LA MOLINA |
| L13 | LA VICTORIA | LIMA | LA VICTORIA |
| L14 | LINCE | LIMA | LINCE |
| L15 | LURIGANCHO - CHOSICA | LIMA | LURIGANCHO |
| L16 | LURIN | LIMA | LURIN |
| L17 | MAGDALENA DEL MAR | LIMA | MAGDALENA DEL MAR |
| L18 | MIRAFLORES | LIMA | MIRAFLORES |
| L19 | PACHACAMAC | LIMA | PACHACAMAC |
| L20 | PUCUSANA | LIMA | PUCUSANA |
| L21 | PUEBLO LIBRE | LIMA | PUEBLO LIBRE |
| L22 | PUENTE PIEDRA | LIMA | PUENTE PIEDRA |
| L23 | PUNTA NEGRA | LIMA | PUNTA NEGRA |
| L24 | PUNTA HERMOSA | LIMA | PUNTA HERMOSA |
| L25 | RIMAC | LIMA | RIMAC |
| L26 | SAN BARTOLO | LIMA | SAN BARTOLO |
| L27 | SAN ISIDRO | LIMA | SAN ISIDRO |
| L28 | INDEPENDENCIA | LIMA | INDEPENDENCIA |
| L29 | SAN JUAN DE MIRAFLORES | LIMA | SAN JUAN DE MIRAFLORES |
| L30 | SAN LUIS | LIMA | SAN LUIS |
| L31 | SAN MARTIN DE PORRES | LIMA | SAN MARTIN DE PORRES |
| L32 | SAN MIGUEL | LIMA | SAN MIGUEL |
| L33 | SANTIAGO DE SURCO | LIMA | SANTIAGO DE SURCO |
| L34 | SURQUILLO | LIMA | SURQUILLO |
| L35 | VILLA MARIA DEL TRIUNFO | LIMA | VILLA MARIA DEL TRIUNFO |
| L36 | SAN JUAN DE LURIGANCHO | LIMA | SAN JUAN DE LURIGANCHO |
| L37 | SANTA MARIA DEL MAR | LIMA | SANTA MARIA DEL MAR |
| L38 | SANTA ROSA | LIMA | SANTA ROSA |
| L39 | LOS OLIVOS | LIMA | LOS OLIVOS |
| L40 | CIENEGUILLA | LIMA | CIENEGUILLA |
| L41 | SAN BORJA | LIMA | SAN BORJA |
| L42 | VILLA EL SALVADOR | LIMA | VILLA EL SALVADOR |
| L43 | SANTA ANITA | LIMA | SANTA ANITA |
| L1-2 | CENTRO HISTÓRICO DE LIMA | LIMA | LIMA (duplicado de L1) |
| L15-1 | SANTA MARIA DE HUACHIPA | LIMA | SANTA MARIA DE HUACHIPA |

### Cañete provincia (L44 + L44-1..L44-15)

| codigo | nombre (legacy, display) | provincia_nombre | distrito_nombre |
|---|---|---|---|
| L44 | SAN VICENTE DE CAÑETE | CAÑETE | SAN VICENTE DE CAÑETE |
| L44-1 | SAN ANTONIO - CAÑETE | CAÑETE | SAN ANTONIO |
| L44-2 | SAN VICENTE DE CAÑETE/ASIA | CAÑETE | SAN VICENTE DE CAÑETE |
| L44-3 | CERRO AZUL | CAÑETE | CERRO AZUL |
| L44-4 | LUNAHUANA | CAÑETE | LUNAHUANA |
| L44-5 | MALA | CAÑETE | MALA |
| L44-6 | CHILCA | CAÑETE | CHILCA |
| L44-7 | IMPERIAL | CAÑETE | IMPERIAL |
| L44-8 | NUEVO IMPERIAL | CAÑETE | NUEVO IMPERIAL |
| L44-9 | SAN LUIS - CAÑETE | CAÑETE | SAN LUIS |
| L44-10 | CALANGO | CAÑETE | CALANGO |
| L44-11 | COAYLLO | CAÑETE | COAYLLO |
| L44-12 | PACARAN | CAÑETE | PACARAN |
| L44-13 | QUILMANA | CAÑETE | QUILMANA |
| L44-14 | SANTA CRUZ DE FLORES | CAÑETE | SANTA CRUZ DE FLORES |
| L44-15 | ZUÑIGA | CAÑETE | ZUÑIGA |

### Huaral provincia (L50 + L50-1..L50-12 + SINCODE1..SINCODE3)

| codigo | nombre (legacy, display) | provincia_nombre | distrito_nombre |
|---|---|---|---|
| L50 | HUARAL | HUARAL | HUARAL |
| L50-1 | CHANCAY | HUARAL | CHANCAY |
| L50-3 | IHUARI | HUARAL | IHUARI |
| L50-4 | SUMBILCA | HUARAL | SUMBILCA |
| L50-5 | PACARAOS | HUARAL | PACARAOS |
| L50-6 | LAMPIAN | HUARAL | LAMPIAN |
| L50-10 | SAN MIGUEL DE ACOS | HUARAL | SAN MIGUEL DE ACOS |
| L50-11 | SANTA CRUZ DE ANDAMARCA | HUARAL | SANTA CRUZ DE ANDAMARCA |
| L50-12 | AUCALLAMA | HUARAL | AUCALLAMA |
| SINCODE1 | ATAVILLOS ALTO | HUARAL | ATAVILLOS ALTO |
| SINCODE2 | ATAVILLOS BAJO | HUARAL | ATAVILLOS BAJO |
| SINCODE3 | 27 DE NOVIEMBRE | HUARAL | VEINTISIETE DE NOVIEMBRE |

### Huaura provincia (L60 + L60-1..L60-11 + SINCODE4)

| codigo | nombre (legacy, display) | provincia_nombre | distrito_nombre |
|---|---|---|---|
| L60 | HUAURA | HUAURA | HUAURA |
| L60-1 | CALETA DE CARQUIN | HUAURA | CALETA DE CARQUIN |
| L60-2 | HUACHO | HUAURA | HUACHO |
| L60-3 | SAYAN | HUAURA | SAYAN |
| L60-4 | VEGUETA | HUAURA | VEGUETA |
| L60-6 | CHECRAS | HUAURA | CHECRAS |
| L60-7 | LEONCIO PRADO | HUAURA | LEONCIO PRADO |
| L60-8 | SANTA LEONOR | HUAURA | SANTA LEONOR |
| L60-9 | PACCHO | HUAURA | PACCHO |
| L60-10 | HUALMAY | HUAURA | HUALMAY |
| L60-11 | SANTA MARIA | HUAURA | SANTA MARIA |
| SINCODE4 | AMBAR | HUAURA | AMBAR |

### Barranca provincia (L70 + L70-1..L70-4)

| codigo | nombre (legacy, display) | provincia_nombre | distrito_nombre |
|---|---|---|---|
| L70 | BARRANCA - NORTE | BARRANCA | BARRANCA |
| L70-1 | SUPE | BARRANCA | SUPE |
| L70-2 | SUPE - PUERTO | BARRANCA | SUPE PUERTO |
| L70-3 | PARAMONGA | BARRANCA | PARAMONGA |
| L70-4 | PATIVILCA | BARRANCA | PATIVILCA |

### Huarochirí provincia (L-80 + L80-1)

| codigo | nombre (legacy, display) | provincia_nombre | distrito_nombre |
|---|---|---|---|
| L-80 | HUAROCHIRI | HUAROCHIRI | HUAROCHIRI |
| L80-1 | SAN ANTONIO DE HUAROCHIRI | HUAROCHIRI | SAN ANTONIO |

### Canta provincia (SINCODE5)

| codigo | nombre (legacy, display) | provincia_nombre | distrito_nombre |
|---|---|---|---|
| SINCODE5 | PROVINCIA CANTA | CANTA | CANTA |

### Entrada administrativa sin resolución

| codigo | nombre | provincia_nombre | distrito_nombre |
|---|---|---|---|
| L1-1 | COMISION AD HOC SEGUNDA INSTANCIA ADMINISTRATIVA | *(omitidos)* | *(omitidos)* |

## Validación esperada

Una vez entregada la seed:

```bash
python manage.py seed_municipalidades --dry-run --settings=config.settings.development
```

Salida esperada por entrada:

```
[OK]    L1 → provincia=LIMA, distrito=LIMA (CERCADO DE LIMA)
[OK]    L3 → provincia=LIMA, distrito=ATE (ATE VITARTE)
[SKIP]  L1-1 COMISION AD HOC SEGUNDA INSTANCIA ADMINISTRATIVA (sin FK — entrada administrativa)
```

Y al correr **sin** `--dry-run`, la tabla `entidades_municipalidad` debería tener `distrito_id` no-NULL en **76 de 78** filas. Las 2 sin distrito son: `L1-1` (administrativa) y la decisión pendiente sobre `L1-2` (si se consolida con `L1`).

## Archivos clave para referencia

| Archivo | Rol |
|---|---|
| `backend/modules/entidades/seeds/municipalidades.json` | Seed actual a actualizar. |
| `backend/modules/entidades/management/commands/seed_municipalidades.py` | Comando que la carga (ya extendido en el paso previo para resolver FK). |
| `backend/modules/entidades/domain/models/municipalidad.py` | Modelo `Municipalidad` (FKs provincia + distrito, `clean()` exclusivo). |
| `backend/modules/entidades/domain/models/ubigeo.py` | Modelo `UbigeoDistrito`. |
| `backend/utils/ubigeo.json` | Fuente de verdad del ubigeo (sección `"LIMA": {...}`). |

## Estado de resolución

- ✅ Análisis completo del estado actual (este documento).
- ✅ Comando `seed_municipalidades.py` extendido para resolver `provincia_nombre + distrito_nombre` → FK al ubigeo.
- ✅ Tabla de mapeo de las 78 entradas (arriba).
- ⏳ Pendiente: entrega formal del JSON actualizado y decisión sobre `L1-2` (consolidar o mantener).
