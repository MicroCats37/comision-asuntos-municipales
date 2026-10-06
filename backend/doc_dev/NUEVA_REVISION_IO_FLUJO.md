# Flujo de Nueva Revisión y Liquidaciones Previas — Documentación Exhaustiva

## 1. Conceptos Clave

### 1.1 Proyecto → Liquidaciones → Revisiones
```
Proyecto
  ├── Liquidación A
  │     ├── Revisión 1 (numero_revision=1)
  │     └── Revisión 3 (numero_revision=3)
  └── Liquidación B
        └── Revisión 1 (numero_revision=1)
```

- Un **proyecto** puede tener **varias liquidaciones**.
- Cada **liquidación** puede tener **varias revisiones**.
- La relación se rastrea por `proyecto_id` y `numero_revision`.

### 1.2 Nueva Liquidación vs Nueva Revisión

| Aspecto | Nueva Liquidación (Primera Revisión) | Nueva Revisión |
|---------|--------------------------------------|----------------|
| **Qué crea** | Nueva `LiquidacionGeneral` con `numero_revision=1` | Nueva `LiquidacionGeneral` con `numero_revision` incrementado |
| **Datos requeridos** | Proyecto completo (o inline) | `liquidacion_previa_id` — hereda proyecto/municipalidad |
| **Uso** | Cuando NO existe liquidación previa del proyecto | Cuando YA existe una liquidación y se agrega revisión |

## 2. Inspección de Obra (IO)

### 2.1 Flujo Actual (Alpha)

1. Usuario busca liquidaciones previas: `GET /buscar-previas?numero_documento=`
2. Usuario selecciona una liquidación previa (EDIFICACION o HABILITACION_URBANA)
3. Usuario crea IO: `POST /primera-revision` con `liquidacion_previa_id`
4. Backend deriva proyecto y municipalidad de la liquidación previa
5. Crea nueva IO con `numero_revision=1`

### 2.2 Lo que el usuario quiere

**Endpoint de "Última Revisión"**: Dado un proyecto (o liquidación previa), devolver la liquidación con el **mayor `numero_revision`**, porque esa es la que tiene la **categoría más alta** (más visitas/peso).

- **Input**: ID de la liquidación previa (o proyecto)
- **Output**: La liquidación más reciente, presentada con el **mismo presenter** de listado/creación (homogeneidad)

**Propósito**: Al crear una nueva IO, el formulario se llena con los datos de la última revisión (proyecto, municipalidad, categoría, etc.) sin reescribirlos.

## 3. Edificaciones — Numeración de Revisiones (1, 3, 5)

### 3.1 Regla de negocio

Las revisiones de Edificaciones **solo toman números impares**: `1 → 3 → 5`.

- `1` = Primera revisión
- `3` = Segunda revisión cobrada
- `5` = Tercera revisión cobrada (máximo)
- No existe revisión 2, 4, 6...

### 3.2 Constante configurable

```python
# En el flujo de Edificaciones
REVISIONES_COBRAN = {1, 3, 5}   # Revisiones que cobran
MAX_REVISIONES = 5               # Máximo de revisiones permitido
```

**Importante**: Esta constante debe vivir en un lugar **configurable** (no hardcodeado disperso), porque en el futuro puede cambiar (ej. agregar revisión 7, o reducir a 3). Se recomienda:
- Una constante central en `domain/constants.py`
- O un registro en la BD (configuración del sistema)

### 3.3 Cálculo de la siguiente revisión

```python
nuevo_numero = previa.numero_revision + 2   # 1→3, 3→5
if nuevo_numero > MAX_REVISIONES:
    raise MaximoRevisionAlcanzadoError(...)  # No se puede superar 5
```

## 4. Endpoints a Diseñar

### 4.1 `GET /ultima-revision` (para IO y Edificaciones)

Devuelve la última revisión de una liquidación/proyecto.

**Input**:
```json
{
  "liquidacion_previa_id": "uuid"  // O proyecto_id
}
```

**Output**: La liquidación más reciente, usando el **mismo presenter** de listado/creación:
```json
{
  "liquidacion_general": {
    "id": "uuid",
    "numero_revision": 5,
    "proyecto": { "...": "..." },
    "municipalidad": { "...": "..." },
    "...": "..."
  },
  "liquidacion_especifica": { "...": "..." },
  "liquidacion_tipo": { "...": "..." }
}
```

### 4.2 `POST /nueva-revision` (para Edificaciones)

Crea una nueva revisión de una liquidación existente.

**Input**: `liquidacion_previa_id` + datos específicos de la nueva revisión

**Regla**: `numero_revision = previa.numero_revision + 2`, validando `<= MAX_REVISIONES` y sin duplicados.

## 5. Decisiones Pendientes

1. **¿IO sigue el patrón 1, 3, 5?** Actualmente IO siempre crea `numero_revision=1`. ¿Debe seguir el mismo patrón de Edificaciones o mantener su propia lógica?
2. **¿Qué datos se heredan de la liquidación previa?** Solo proyecto/municipalidad, o también tarifas/categoría?
3. **¿La "última revisión" se busca por proyecto o por liquidación?** El usuario menciona ambas cosas.

## 6. Reglas de Implementación (para el rebuild)

1. **NO copiar código alpha** — solo guiarse de la intención y el flujo.
2. **Homogeneidad del presenter**: Reutilizar el mismo presenter de salida para listado, creación y última-revisión.
3. **Constante de revisiones configurable**: `REVISIONES_COBRAN` y `MAX_REVISIONES` en un lugar central.
4. **Entrada mínima**: El formulario solo necesita el ID de la liquidación previa; el resto se deriva.
