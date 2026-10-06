# Wrappers Semantics — Corrected JSON Payloads

> **Date**: 2026-08-08  
> **Status**: DRAFT — For user review before code changes  
> **Change**: Swap the semantic meaning of `liquidacion_especifica` and `liquidacion_tipo`

---

## Semantic Correction Summary

### Current (Incorrect) Naming

| Wrapper | Holds | Discriminator |
|---------|-------|---------------|
| `liquidacion_especifica` | Calculation engine data (`area_m2`, `cantidad_visitas`, etc.) | No |
| `liquidacion_tipo` | Only `id` and `numero` from AutoNumeroModel | No |

### Corrected (After Fix) Naming

| Wrapper | Holds | Discriminator |
|---------|-------|---------------|
| `liquidacion_tipo` | Calculation engine data (`area_m2`, `cantidad_visitas`, etc.) + `tipo_calculo` | **Yes** — polymorphic discriminator |
| `liquidacion_especifica` | Only `id` and `numero` from AutoNumeroModel | No |

---

## Domain Model Layer (Backend Python)

### Semantic Rule

- **`liquidacion_tipo`** = The calculation engine table. Contains the computation fields and a `tipo_calculo` discriminator that tells the system *which* calculation formula to apply.
- **`liquidacion_especifica`** = The AutoNumeroModel table. Contains only `id` (UUID) and `numero` (sequential integer assigned by the database).

---

## 1. Habilitación Urbana — `POST /api/liquidaciones/habilitacion-urbana/primera-revision`

### Input JSON (Request Body)

```json
{
  "liquidacion_general": {
    "municipalidad_id": "550e8400-e29b-41d4-a716-446655440001",
    "expediente": "EXP-2026-00123",
    "observacion": "Primera revisión de habilitación urbana",
    "proyecto": {
      "denominacion": "Urbanización Las Palmeras",
      "nombre_propietario": "Constructora ABC S.A.C.",
      "direccion": "Av. Principal 123",
      "distrito_id": "550e8400-e29b-41d4-a716-446655440099",
      "entidad": {
        "tipo_documento": "RUC",
        "numero_documento": "20456789012",
        "razon_social": "Constructora ABC S.A.C."
      }
    }
  },
  "liquidacion_tipo": {
    "datos": {
      "area_solicitada": 2500.50
    },
    "tarifa": {
      "tarifa_m2_id": "550e8400-e29b-41d4-a716-446655440010"
    }
  }
}
```

**Field Semantics:**

| Field | Type | Description |
|-------|------|-------------|
| `liquidacion_general` | Object | Common header: municipalidad, expediente, proyecto |
| `liquidacion_tipo` | Object | **Calculation engine** — contains `area_solicitada` and `tarifa_m2_id`. This tells the system to apply the M2 formula. No `tipo_calculo` needed here because the *shape* of the `datos` object already implies M2 calculation. |
| `liquidacion_tipo.datos.area_solicitada` | float | Area in square meters for the HU project |
| `liquidacion_tipo.tarifa.tarifa_m2_id` | UUID | Reference to the M2 tariff table |

---

### Output JSON (Response Body)

```json
{
  "liquidacion_general": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "municipalidad_id": "550e8400-e29b-41d4-a716-446655440001",
    "usuario_creador": {
      "id": "550e8400-e29b-41d4-a716-446655440100"
    },
    "fecha_registro": "2026-08-08T10:30:00Z",
    "expediente": "EXP-2026-00123",
    "observacion": "Primera revisión de habilitación urbana",
    "numero_revision": 1,
    "sub_total": 18753.75,
    "total": 22170.43,
    "igv_id": "550e8400-e29b-41d4-a716-446655440200",
    "uit_id": "550e8400-e29b-41d4-a716-446655440201",
    "proyecto": {
      "id": "550e8400-e29b-41d4-a716-446655440300",
      "denominacion": "Urbanización Las Palmeras",
      "nombre_propietario": "Constructora ABC S.A.C.",
      "direccion": "Av. Principal 123",
      "distrito_id": "550e8400-e29b-41d4-a716-446655440099",
      "entidad": {
        "tipo_documento": "RUC",
        "numero_documento": "20456789012",
        "razon_social": "Constructora ABC S.A.C."
      }
    }
  },
  "liquidacion_tipo": {
    "id": "550e8400-e29b-41d4-a716-446655440400",
    "area_m2": 2500.50,
    "costo_por_m2": 7.50,
    "derecho_minimo": 500.00,
    "derecho_maximo": 25000.00,
    "tarifa_aplicada_id": "550e8400-e29b-41d4-a716-446655440010",
    "derecho_aplicado_id": "550e8400-e29b-41d4-a716-446655440011"
  },
  "liquidacion_especifica": {
    "id": "550e8400-e29b-41d4-a716-446655440500",
    "numero": 42
  }
}
```

**Field Semantics (Output):**

| Field | Type | Description |
|-------|------|-------------|
| `liquidacion_general` | Object | Common header with all project and financial metadata |
| `liquidacion_tipo` | Object | **Calculation engine result** — the persisted M2 calculation with all computed values |
| `liquidacion_especifica` | Object | **AutoNumeroModel snapshot** — `id` (primary key of the specific HU table) and `numero` (sequential number assigned at creation time) |

---

## 2. Inspección de Obra — `POST /api/liquidaciones/inspeccion-obra/crear-primera-revision`

### Input JSON (Request Body)

```json
{
  "liquidacion_general": {
    "municipalidad_id": "550e8400-e29b-41d4-a716-446655440001",
    "expediente": "EXP-2026-00456",
    "observacion": "Inspección de obra nueva",
    "proyecto": {
      "denominacion": "Edificio Miraflores Tower",
      "nombre_propietario": "Inmobiliaria XYZ S.A.",
      "direccion": "Av. Larco 890",
      "distrito_id": "550e8400-e29b-41d4-a716-446655440099",
      "entidad": {
        "tipo_documento": "RUC",
        "numero_documento": "20512345678",
        "razon_social": "Inmobiliaria XYZ S.A."
      }
    }
  },
  "liquidacion_tipo": {
    "datos": {
      "cantidad_visitas": 3,
      "categoria": "C2"
    },
    "tarifa": {
      "tarifa_visitas_id": "550e8400-e29b-41d4-a716-446655440020"
    }
  }
}
```

**Field Semantics:**

| Field | Type | Description |
|-------|------|-------------|
| `liquidacion_general` | Object | Common header: municipalidad, expediente, proyecto |
| `liquidacion_tipo` | Object | **Calculation engine** — contains `cantidad_visitas` and `categoria`. The shape of `datos` implies the Visitas calculation. |
| `liquidacion_tipo.datos.cantidad_visitas` | int | Number of inspection visits required |
| `liquidacion_tipo.datos.categoria` | string | Category classification (C1, C2, C3, C4) |
| `liquidacion_tipo.tarifa.tarifa_visitas_id` | UUID | Reference to the Visitas tariff table |

---

### Output JSON (Response Body)

```json
{
  "liquidacion_general": {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "municipalidad_id": "550e8400-e29b-41d4-a716-446655440001",
    "usuario_creador": {
      "id": "550e8400-e29b-41d4-a716-446655440100"
    },
    "fecha_registro": "2026-08-08T11:00:00Z",
    "expediente": "EXP-2026-00456",
    "observacion": "Inspección de obra nueva",
    "numero_revision": 1,
    "sub_total": 4500.00,
    "total": 5310.00,
    "igv_id": "550e8400-e29b-41d4-a716-446655440200",
    "uit_id": "550e8400-e29b-41d4-a716-446655440201",
    "proyecto": {
      "id": "550e8400-e29b-41d4-a716-446655440301",
      "denominacion": "Edificio Miraflores Tower",
      "nombre_propietario": "Inmobiliaria XYZ S.A.",
      "direccion": "Av. Larco 890",
      "distrito_id": "550e8400-e29b-41d4-a716-446655440099",
      "entidad": {
        "tipo_documento": "RUC",
        "numero_documento": "20512345678",
        "razon_social": "Inmobiliaria XYZ S.A."
      }
    }
  },
  "liquidacion_tipo": {
    "id": "550e8400-e29b-41d4-a716-446655440401",
    "cantidad_visitas": 3,
    "porcentaje_uit": 0.15,
    "categoria": "C2",
    "tarifa_aplicada_id": "550e8400-e29b-41d4-a716-446655440020"
  },
  "liquidacion_especifica": {
    "id": "550e8400-e29b-41d4-a716-446655440501",
    "numero": 17
  }
}
```

**Field Semantics (Output):**

| Field | Type | Description |
|-------|------|-------------|
| `liquidacion_general` | Object | Common header with all project and financial metadata |
| `liquidacion_tipo` | Object | **Calculation engine result** — the persisted Visitas calculation with `cantidad_visitas`, `porcentaje_uit`, `categoria` |
| `liquidacion_especifica` | Object | **AutoNumeroModel snapshot** — `id` (primary key of the specific IO table) and `numero` (sequential number) |

---

## Files Affected by the Semantic Swap

### Schemas (Input/Output API Contracts)

| File | Change |
|------|--------|
| `backend/modules/liquidaciones/presentation/schemas/liquidacion_especifico/liquidacion_habilitacion_urbana_schemas.py` | Rename `liquidacion_especifica` → `liquidacion_tipo` in `LiquidacionHabilitacionUrbanaInput` and `LiquidacionHabilitacionUrbanaOutput` |
| `backend/modules/liquidaciones/presentation/schemas/liquidacion_especifico/liquidacion_inspeccion_obra_schemas.py` | Rename `liquidacion_especifica` → `liquidacion_tipo` in `LiquidacionInspeccionObraInput` and `LiquidacionInspeccionObraOutput` |
| `backend/modules/liquidaciones/presentation/schemas/liquidacion_tipo/tipo_schemas.py` | Rename `LiquidacionTipoOutput` fields (add calculation fields) — verify `CotizarPorMetroCuadradoInputSchema.liquidacion_especifica` → `liquidacion_tipo` |
| `backend/modules/liquidaciones/presentation/schemas/liquidacion_tipo/visitas_schemas.py` | Verify `CotizarPorCategoriaVisitasInputSchema.liquidacion_especifica` → `liquidacion_tipo` |

### Domain Results (Internal DTOs)

| File | Change |
|------|--------|
| `backend/modules/liquidaciones/domain/results/liquidacion_especifico/habilitacion_urbana_primera_revision_result.py` | Swap `liquidacion_tipo` (LiquidacionM2Result) ↔ `liquidacion_especifica` (LiquidacionEspecificaHabilitacionUrbanaResult) |
| `backend/modules/liquidaciones/domain/results/liquidacion_especifico/inspeccion_obra_primera_revision_result.py` | Swap `liquidacion_tipo` (LiquidacionVisitasResult) ↔ `liquidacion_especifica` (LiquidacionEspecificaInspeccionObraResult) |

### Presenters (Domain → Presentation Mapper)

| File | Change |
|------|--------|
| `backend/modules/liquidaciones/presentation/presenters/liquidacion_especifico/liquidacion_habilitacion_urbana_presenter.py` | Update field mapping: `tipo_out` should receive calculation data, `especifica_out` should receive `id` + `numero` |
| `backend/modules/liquidaciones/presentation/presenters/liquidacion_especifico/liquidacion_inspeccion_obra_presenter.py` | Same as above for IO |

### Frontend TypeScript Types

| File | Change |
|------|--------|
| `frontend/src/features/liquidaciones/types/liquidacion-habilitacion-urbana.types.ts` | Rename `liquidacion_especifica` → `liquidacion_tipo` for input/output types |
| `frontend/src/features/liquidaciones/types/liquidacion-inspeccion-obra.types.ts` | Same for IO types |

---

## Validation Checklist

- [ ] `liquidacion_tipo` in Input contains calculation data (`area_solicitada` for HU, `cantidad_visitas` for IO)
- [ ] `liquidacion_tipo` in Output contains calculation result fields (`area_m2`, `costo_por_m2` for HU; `cantidad_visitas`, `porcentaje_uit` for IO)
- [ ] `liquidacion_especifica` in Output contains ONLY `id` (UUID) and `numero` (int)
- [ ] All presenters updated to map fields to correct semantic positions
- [ ] All API schemas updated
- [ ] All TypeScript types updated
- [ ] All imports and references to renamed fields updated across the codebase
