# Wrappers Semánticos — Estado Actual (Buggy/Swapped)

> **Fecha de generación:** Agosto 2026
> **Propósito:** Documentar la semántica ACTUAL de los wrappers `liquidacion_tipo` y `liquidacion_especifica` en los schemas de salida, reflejando el bug de nombres intercambiados.

---

## 1. Habilitación Urbana (HU)

### 1.1 Input Payload

```json
{
  "liquidacion_general": {
    "municipalidad_id": "uuid-municipalidad",
    "expediente": "EXP-2026-00123",
    "observacion": "Primera revisión HU",
    "proyecto": {
      "denominacion": "Urbanización Las Margaritas",
      "nombre_propietario": "Carlos Mendoza",
      "direccion": "Av. Brasil 1234, Lima",
      "distrito_id": "uuid-distrito",
      "entidad": {
        "tipo_documento": "RUC",
        "numero_documento": "20123456789",
        "razon_social": "Mendoza Constructora S.A.C."
      }
    }
  },
  "liquidacion_especifica": {
    "datos": {
      "area_solicitada": 450.5
    },
    "tarifa": {
      "tarifa_m2_id": "uuid-tarifa-m2"
    }
  }
}
```

**Nota:** En el input, `liquidacion_especifica` contiene el cálculo M2 (área solicitada). Este es correcto en el input.

### 1.2 Output Payload (ACTUAL — Buggy)

```json
{
  "liquidacion_general": {
    "id": "uuid-liquidacion-general",
    "municipalidad_id": "uuid-municipalidad",
    "usuario_creador": {
      "id": "uuid-usuario"
    },
    "fecha_registro": "2026-08-08T10:30:00Z",
    "expediente": "EXP-2026-00123",
    "observacion": "Primera revisión HU",
    "numero_revision": 1,
    "sub_total": 2252.50,
    "total": 2657.95,
    "igv_id": "uuid-igv",
    "uit_id": "uuid-uit",
    "proyecto": {
      "id": "uuid-proyecto",
      "denominacion": "Urbanización Las Margaritas",
      "nombre_propietario": "Carlos Mendoza",
      "direccion": "Av. Brasil 1234, Lima",
      "distrito_id": "uuid-distrito",
      "entidad": {
        "tipo_documento": "RUC",
        "numero_documento": "20123456789",
        "razon_social": "Mendoza Constructora S.A.C."
      }
    }
  },
  "liquidacion_tipo": {
    "id": "uuid-liquidacion-tipo",
    "numero": 42
  },
  "liquidacion_especifica": {
    "id": "uuid-liquidacion-m2",
    "area_m2": 450.5,
    "costo_por_m2": 5.0,
    "derecho_minimo": 500.0,
    "derecho_maximo": 10000.0,
    "tarifa_aplicada_id": "uuid-tarifa-m2",
    "derecho_aplicado_id": "uuid-derecho-m2"
  }
}
```

### 1.3 Análisis del Bug en HU

| Wrapper | Campos actuales | Problema semántico |
|---------|------------------|---------------------|
| `liquidacion_tipo` | `id`, `numero` | Debería devolver `area_m2`, `costo_por_m2`, etc. (campos de cálculo M2) |
| `liquidacion_especifica` | `area_m2`, `costo_por_m2`, ... | Debería devolver `id` de la liquidación específica y datos propios de HU |

**Raíz del bug:** En `LiquidacionHabilitacionUrbanaOutput`, se asignó `LiquidacionTipoOutput` (que solo tiene `id` y `numero`) a `liquidacion_tipo`, cuando debería usar `LiquidacionPorMetroCuadradoDatosOut`.

---

## 2. Inspección de Obra (IO)

### 2.1 Input Payload

```json
{
  "liquidacion_general": {
    "municipalidad_id": "uuid-municipalidad",
    "expediente": "EXP-2026-00456",
    "observacion": "Inspección inicial",
    "proyecto": {
      "denominacion": "Edificio Torre Azul",
      "nombre_propietario": "María Elena Torres",
      "direccion": "Calle Las Flores 789, Lima",
      "distrito_id": "uuid-distrito",
      "entidad": {
        "tipo_documento": "DNI",
        "numero_documento": "87654321",
        "razon_social": "María Elena Torres"
      }
    }
  },
  "liquidacion_especifica": {
    "datos": {
      "cantidad_visitas": 3,
      "categoria": "B"
    },
    "tarifa": {
      "tarifa_visitas_id": "uuid-tarifa-visitas"
    }
  }
}
```

**Nota:** En el input, `liquidacion_especifica` contiene el cálculo por visitas (cantidad y categoría). Este es correcto en el input.

### 2.2 Output Payload (ACTUAL — Buggy)

```json
{
  "liquidacion_general": {
    "id": "uuid-liquidacion-general",
    "municipalidad_id": "uuid-municipalidad",
    "usuario_creador": {
      "id": "uuid-usuario"
    },
    "fecha_registro": "2026-08-08T11:00:00Z",
    "expediente": "EXP-2026-00456",
    "observacion": "Inspección inicial",
    "numero_revision": 1,
    "sub_total": 1200.00,
    "total": 1416.00,
    "igv_id": "uuid-igv",
    "uit_id": "uuid-uit",
    "proyecto": {
      "id": "uuid-proyecto",
      "denominacion": "Edificio Torre Azul",
      "nombre_propietario": "María Elena Torres",
      "direccion": "Calle Las Flores 789, Lima",
      "distrito_id": "uuid-distrito",
      "entidad": {
        "tipo_documento": "DNI",
        "numero_documento": "87654321",
        "razon_social": "María Elena Torres"
      }
    }
  },
  "liquidacion_tipo": {
    "id": "uuid-liquidacion-tipo",
    "numero": 17
  },
  "liquidacion_especifica": {
    "id": "uuid-liquidacion-visitas",
    "cantidad_visitas": 3,
    "porcentaje_uit": 0.15,
    "categoria": "B",
    "tarifa_aplicada_id": "uuid-tarifa-visitas"
  }
}
```

### 2.3 Análisis del Bug en IO

| Wrapper | Campos actuales | Problema semántico |
|---------|------------------|---------------------|
| `liquidacion_tipo` | `id`, `numero` | Debería devolver `cantidad_visitas`, `porcentaje_uit`, `categoria` (campos de cálculo Visitas) |
| `liquidacion_especifica` | `cantidad_visitas`, `porcentaje_uit`, `categoria`, ... | Debería devolver `id` de la liquidación específica y datos propios de IO |

**Raíz del bug:** En `LiquidacionInspeccionObraOutput`, se asignó `LiquidacionTipoOutput` (que solo tiene `id` y `numero`) a `liquidacion_tipo`, cuando debería usar `LiquidacionPorCategoriaVisitasDatosOut`.

---

## 3. Resumen del Bug (Semantic Swap)

### Estado Actual (Buggy)

```
liquidacion_tipo       → { id, numero }                        ❌ Solo identidad
liquidacion_especifica → { area_m2, costo_por_m2, ... }        ❌ Datos de cálculo
```

### Estado Esperado (Correcto)

```
liquidacion_tipo       → { area_m2, costo_por_m2, ... }        ✅ Datos de cálculo
liquidacion_especifica → { id, numero }                        ✅ Solo identidad
```

### Archivos Afectados

| Archivo | Rol |
|---------|-----|
| `liquidacion_especifico/liquidacion_habilitacion_urbana_schemas.py` | Define `LiquidacionHabilitacionUrbanaOutput` con wrappers intercambiados |
| `liquidacion_especifico/liquidacion_inspeccion_obra_schemas.py` | Define `LiquidacionInspeccionObraOutput` con wrappers intercambiados |
| `liquidacion_tipo/tipo_schemas.py` | Define `LiquidacionTipoOutput` (correcto como identidad) y `LiquidacionPorMetroCuadradoDatosOut` (cálculo M2) |
| `liquidacion_tipo/visitas_schemas.py` | Define `LiquidacionPorCategoriaVisitasDatosOut` (cálculo Visitas) |

---

## 4. Fix Requerido

En los schemas de output (`LiquidacionHabilitacionUrbanaOutput` y `LiquidacionInspeccionObraOutput`):

1. **Cambiar `liquidacion_tipo`** de `LiquidacionTipoOutput` → al schema de cálculo correspondiente (`LiquidacionPorMetroCuadradoDatosOut` o `LiquidacionPorCategoriaVisitasDatosOut`)

2. **Cambiar `liquidacion_especifica`** del schema de cálculo → a `LiquidacionTipoOutput`

**Nota:** Los schemas de INPUT (`LiquidacionHabilitacionUrbanaInput` y `LiquidacionInspeccionObraInput`) NO necesitan cambios, ya que la dirección del flujo de datos es correcta en la entrada.
