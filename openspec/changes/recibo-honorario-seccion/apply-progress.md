# SDD Apply Progress: recibo-honorario-seccion

## Status
**Change**: `recibo-honorario-seccion`
**Mode**: Standard (no strict TDD)
**Applied at**: 2026-08-14

---

## Implemented Tasks

### 1. Sidebar — `ProtectedSidebar.tsx`
- Added `Receipt` icon import from lucide-react
- Created `recibosGroup` with title "Recibos por Honorario" and child item "Recibos de Honorario" pointing to `/liquidaciones/recibos-honorario`
- Added `recibosOpen` state and `isRecibosChildActive` check
- Added Recibos accordion group rendering following exact pattern of `finanzasGroup`

### 2. Zod Schemas

**`frontend/src/features/finanzas/schemas/recibo-honorario.schema.ts`**:
```typescript
// ReciboHonorarioDelegadoOut — mirrors backend schema exactly
{
  id: string,
  liquidacion_delegado_id: string,
  liquidacion_general: {
    id: string,
    expediente: string | null,
    numero_revision: number,
    sub_total: number,
    total: number,
    fecha_registro: string,
    tipo_liquidacion: { codigo: string, nombre: string } | null,
    municipalidad_nombre: string | null,
    proyecto_denominacion: string | null,
  },
  delegado: { id: string, cip: string, dni: string, nombre_completo: string },
  especialidad: { id: string, codigo: string, nombre: string },
  sub_total: number,
  imp_bruto: number,
  renta_cip: number,
  aporte_codemu: number,
  fondo_comun: number,
  neto_honorario: number,
  honorario: number,
  created_at: string,
}
```

**`frontend/src/features/finanzas/schemas/delegado-asignacion.schema.ts`**:
```typescript
// LiquidacionDelegadoOut — mirrors backend schema exactly
{
  id: string,
  liquidacion_id: string,
  delegado_id: string,
  especialidad_revision: { id: string, nombre: string },
  liquidacion: { id, expediente, numero_revision, sub_total, total, municipalidad_nombre, proyecto_denominacion, tipo_liquidacion } | null,
  delegado: { id: string, cip: string, dni: string, nombre_completo: string } | null,
  periodo: string | null,
  dictamen_revision: string | null,
  fecha_presentacion: string | null,
  fecha_revision: string | null,
}
```

### 3. Hooks
| File | Purpose |
|------|---------|
| `useRecibosHonorarios.ts` | Lists paginated receipts from `GET /finanzas/recibos-honorarios` with filters `delegado_id`, `liquidacion_id` |
| `useCrearReciboHonorario.ts` | Creates receipt via `POST /finanzas/recibos-honorarios` with `{ liquidacion_delegado_id }`, invalidates list on success |
| `useDelegadosAsignaciones.ts` | Searches assignments via `GET /liquidaciones/delegados-asignaciones` with `cip` filter |

### 4. Components
| File | Description |
|------|-------------|
| `ReciboHonorarioCard.tsx` | Displays receipt card with sections: Delegado (nombre_completo, CIP), Especialidad (nombre, código), Liquidación (expediente, revisión, tipo, municipalidad, proyecto), Montos (imp_bruto, renta_cip −25%, aporte_codemu −5%, fondo_comun −10%, neto_honorario bold/primary) |
| `DelegadoAsignacionBuscarModal.tsx` | Modal to search/select LiquidacionDelegado by CIP — follows pattern of SeleccionarPreviaModal with input validation (min 3 chars), pagination, clickable result cards |
| `ReciboHonorarioFormModal.tsx` | Modal that uses DelegadoAsignacionBuscarModal to select assignment, shows selected details, confirms creation with "Crear Recibo" button |

### 5. View + Page
| File | Description |
|------|-------------|
| `ReciboHonorariosView.tsx` | Main view with PageHeader, "Nuevo Recibo" button, cards grid (empty state if no items), Pagination |
| `page.tsx` | Route file at `frontend/src/app/(protected)/liquidaciones/recibos-honorario/page.tsx` — auth-protected, renders ReciboHonorariosView |

---

## Card Display (ReciboHonorarioCard)
```
┌─────────────────────────────────────────────────────────┐
│ Recibo de Honorario                        14 ago 2026  │
├─────────────────────────────────────────────────────────┤
│ ┌──────────────┐  ┌──────────────┐                      │
│ │ 👤 Delegado  │  │ ⚖️ Especialidad│                     │
│ │ Juan Pérez   │  │ Edificaciones │                     │
│ │ CIP: 12345  │  │ Código: EDIF  │                     │
│ └──────────────┘  └──────────────┘                      │
│                                                         │
│ ┌───────────────────────────────────────────────────┐   │
│ │ 📄 Liquidación                                    │   │
│ │ Expediente | Revisión N° | Tipo | Municipalidad   │   │
│ │ Exp-2026-001 | N° 1 | Edificación | Lima        │   │
│ └───────────────────────────────────────────────────┘   │
│                                                         │
│ ┌───────────────────────────────────────────────────┐   │
│ │ 💰 Detalle de Montos                              │   │
│ │ Importe Bruto   | S/ 1,000.00                     │   │
│ │ Renta CIP (25%) | -S/ 250.00                     │   │
│ │ Aporte CODEMU  | -S/ 50.00                      │   │
│ │ Fondo Común    | -S/ 100.00                      │   │
│ │ ─────────────────────────────────────           │   │
│ │ Neto Honorario  | S/ 600.00 (bold, primary)      │   │
│ └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Modal + Buscador Flow
1. User clicks "Nuevo Recibo" → `ReciboHonorarioFormModal` opens
2. Clicks "Buscar Asignación" → `DelegadoAsignacionBuscarModal` opens
3. Enters CIP (min 3 digits), clicks "Buscar" → results shown as clickable cards
4. Selects assignment → modal closes, selection shown in form modal with details
5. Clicks "Crear Recibo" → `POST /finanzas/recibos-honorarios` with `{ liquidacion_delegado_id }`
6. On success: toast notification, modal closes, list refetches

---

## Verification Results
- `npx tsc --noEmit`: ✅ No errors in new files (only pre-existing test file errors unrelated to this work)
- `npx biome check`: ✅ No errors in new files

---

## Files Created/Modified
| File | Action | Description |
|------|--------|-------------|
| `frontend/src/components-app/sidebar/ProtectedSidebar.tsx` | Modified | Added Recibos group to sidebar |
| `frontend/src/features/finanzas/schemas/recibo-honorario.schema.ts` | Created | Zod schema for ReciboHonorarioDelegadoOut |
| `frontend/src/features/finanzas/schemas/delegado-asignacion.schema.ts` | Created | Zod schema for LiquidacionDelegadoOut |
| `frontend/src/features/finanzas/hooks/useRecibosHonorarios.ts` | Created | Hook for listing receipts |
| `frontend/src/features/finanzas/hooks/useCrearReciboHonorario.ts` | Created | Hook for creating receipt |
| `frontend/src/features/finanzas/hooks/useDelegadosAsignaciones.ts` | Created | Hook for searching assignments |
| `frontend/src/features/finanzas/components/cards/ReciboHonorarioCard.tsx` | Created | Card component for receipt display |
| `frontend/src/features/finanzas/components/modals/DelegadoAsignacionBuscarModal.tsx` | Created | Modal for searching delegacion assignments |
| `frontend/src/features/finanzas/components/modals/ReciboHonorarioFormModal.tsx` | Created | Modal for creating receipts |
| `frontend/src/features/finanzas/views/ReciboHonorariosView.tsx` | Created | Main view component |
| `frontend/src/app/(protected)/liquidaciones/recibos-honorario/page.tsx` | Created | Route page |

---

## Risks
1. Backend endpoint `/liquidaciones/delegados-asignaciones` uses `auth=None` (AllowAny) — verified from exploration
2. POST `/finanzas/recibos-honorarios` is idempotent (get_or_create) — if receipt exists for liquidacion_delegado, updates instead of erroring — user may not be aware existing receipt would be updated

---

## Next Steps
- Ready for `sdd-verify` phase
