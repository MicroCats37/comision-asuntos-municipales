# Explore: New Liquidacion Form

## Goal
The "Nueva Liquidación" form is a shared modal shell used by all 6 liquidacion tipos (Edificaciones, Habilitación Urbana, Mecánica de Suelos, Impacto Vial, Taludes, Inspección de Obra). Each tipo has its own FormModal that composes: (1) `LiquidacionFormBodyBase` (2-column layout with shared fields: municipalidad, expediente, retención, observación, entidad lookup, denominacion, distrito, dirección, contacto), plus (2) tipo-specific Smart Fields (tramiteField for the motor input value, motorSection for tarifas + cotización). The form follows a base+specific pattern: shared base card + per-tipo engine section.

## Estado actual (evidence)

### Files involved

| File | Role |
|------|------|
| `LiquidacionFormBodyBase.tsx` | Shared 2-column base layout (DATOS DEL TRÁMITE left, DATOS DEL PROYECTO right) |
| `EdificacionesFormModal.tsx` | Edificaciones PO create form |
| `HabilitacionUrbanaFormModal.tsx` | HU M2 create form |
| `InspeccionObraEditFormModal.tsx` | IO edit form (create form NOT FOUND at `InspeccionObraFormModal.tsx`) |
| `TipoTramiteSmartField.tsx` | tipo_tramite dropdown (Edificaciones only) |
| `TarifasYEspecialidadesSmartField.tsx` | Specialty chips + auto-select for PO tipos |
| `TarifasM2SmartField.tsx` | HU/MS tariff selector |
| `CotizacionPorcentajeSmartField.tsx` | PO live quote preview |
| `CotizacionM2SmartField.tsx` | M2 live quote preview |
| `CotizacionVisitasSmartField.tsx` | IO manual-calculate quote preview |
| `EntidadLookupSmartField.tsx` | RUC/DNI lookup via SUNAT/RENIEC |
| `ContactoFormModal.tsx` | Contact sub-modal (singular) |
| `ComprobanteFormModal.tsx` | Comprobante sub-modal (out of scope for this exploration) |
| `useCrearEdificaciones.ts` | Mutation hook with `buildApiPayload` (payload construction) |
| `useCrearHabilitacionUrbana.ts` | Same pattern for HU |
| `liquidacion-form-base.schema.ts` | Shared Zod schemas (ContactoInline, proyectoForm, generalForm) |
| `liquidacion-edificaciones-form.schema.ts` | Edificaciones-specific schema |
| `AppFormModal.tsx` | Modal shell wrapping GenericForm + footer with primary/secondary buttons |

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  HEADER: title "Nueva Liquidación — {Tipo}", eyebrow, icon     │
├──────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────┐  ┌──────────────────────────────┐  │
│  │ DATOS DEL TRÁMITE       │  │ DATOS DEL PROYECTO           │  │
│  │ ─────────────────────── │  │ ────────────────────────────  │  │
│  │ municipalidad (required) │  │ [EntidadLookup Smart Field]  │  │
│  │ expediente              │  │   RUC/DNI RadioGroup          │  │
│  │ [tramiteField: valor_   │  │   Número + Buscar button      │  │
│  │  declarado OR area_m2]  │  │   Razón Social (auto-fill)   │  │
│  │ retencion checkbox      │  │   Propietario inline field    │  │
│  │ observacion textarea    │  │ denominacion (optional)       │  │
│  ├─────────────────────────┤  │ urbanizacion (HU/MS only)    │  │
│  │ [motorSection]          │  │ distrito (required)           │  │
│  │ ┌─────────────────────┐ │  │ dirección (required)          │  │
│  │ │ TarifasYEspecialidad │ │  │ ────────────────────────────  │  │
│  │ │ (PO) OR TarifasM2   │ │  │ CONTACTO PRINCIPAL            │  │
│  │ │ esSmartField (M2)    │ │  │ [Agregado badge] Edit Trash  │  │
│  │ └─────────────────────┘ │  │ OR "+ Agregar" button        │  │
│  │ ┌─────────────────────┐ │  └──────────────────────────────┘  │
│  │ │ CotizacionSmart     │ │                                    │
│  │ │ Field (live preview)│ │                                    │
│  │ └─────────────────────┘ │                                    │
│  └─────────────────────────┘                                    │
├──────────────────────────────────────────────────────────────────┤
│  FOOTER: [outline Cancelar] [primary Crear Liquidación + spinner]│
└──────────────────────────────────────────────────────────────────┘
```

- 2-column grid (`grid-cols-1 lg:grid-cols-2` at `LiquidacionFormBodyBase.tsx:318`)
- Left column: DATOS DEL TRÁMITE + motorSection (tarifas + cotización) stacked
- Right column: DATOS DEL PROYECTO + Contacto
- `tramiteField` slot per tipo: `valor_declarado` (PO) or `area_solicitada` (M2)

### GenericForm pattern

All 6 create forms use **Mode 1 (manual children)** — `GenericForm` wraps the body via `children` render prop. This is correct per architecture contract. The `onSubmit` prop on `GenericForm` triggers `handleFormSubmit` which calls the parent's `handleSubmit` callback.

`AppFormModal.tsx:171` — `GenericForm` receives `handleFormSubmit as onSubmit`. `handleFormSubmit` calls `await onSubmit(data)` then `onOpenChange(false)` to close.

### buildApiPayload location

**Correct** — payload construction is in each mutation hook:
- `useCrearEdificaciones.ts:25-108` — wrapper destructures form fields, builds `{ liquidacion_general, liquidacion_especifica }` payload
- `useCrearHabilitacionUrbana.ts:26-93` — same pattern for HU

No `buildApiPayload` found inside form components. This follows the architecture contract.

### Validación flow

Zod schemas per tipo (`liquidacion-edificaciones-form.schema.ts`, etc.) composed by spreading `proyectoFormSchema`, `generalFormSchema`, and adding tipo-specific fields. `AppFormModal` passes schema to `GenericForm`. Errors surface via:
1. **Inline field errors**: `fieldState.error.message` shown below each field in small destructive text
2. **Mutation errors**: `notify.error()` via the mutation hook's `onError`
3. **Smart field errors**: local `error` state + destructive text display inside the smart field

### Specialty selection

`TarifasYEspecialidadesSmartField.tsx` is used ONLY by PO tipos (Edificaciones, Impacto Vial, Taludes). It receives `tipo` prop which is passed to `useTarifasVigentesPorcentaje(tipo, ...)`. HU/MS use `TarifasM2SmartField` instead — completely separate component and hook. **HU does not see Edificaciones specialties. Each tipo is isolated.**

Auto-select behavior (`TarifasYEspecialidadesSmartField.tsx:114-128`):
- Group A (OBRA_NUEVA, DEMOLICION, AMPLIACION, REMODELACION, REINTEGRO, PROYECTO_CON_PLANTAS_TIPICAS) or `tipo_tramite === undefined`: auto-selects ALL specialties when no selection exists
- Group B (MODIFICACION_LICENCIA, VARIACION_PROYECTO_APROBADO): no auto-select, user must pick explicitly
- `variant="auto"` (create mode default): compact view with chips + "Editar selección" button; `variant="manual"`: always expanded

### Cotización variants

| Tipo | Component | Auto-calculate | Manual calculate |
|------|-----------|-----------------|-----------------|
| PO (Edif/IV/Taludes) | `CotizacionPorcentajeSmartField` | ✅ debounced 500ms | ❌ |
| M2 (HU/MS) | `CotizacionM2SmartField` | ✅ debounced 500ms | ❌ |
| IO (Inspección Obra) | `CotizacionVisitasSmartField` | ❌ | ✅ button "Calcular Cotización" |

---

## Issues found (UI/UX)

### Issue 1: IO Create Form Missing
- **Description**: `InspeccionObraFormModal.tsx` does not exist at the expected path. Only `InspeccionObraEditFormModal.tsx` exists. The 6 liquidacion tipos listed include "Inspección de Obra" but there is no create modal for it.
- **Severity**: critical
- **Evidence**: `glob` found no `InspeccionObraFormModal.tsx`; only `NuevaRevisionInspeccionObraFormModal.tsx` and `InspeccionObraEditFormModal.tsx`
- **Suggested fix**: Determine if IO creation is handled elsewhere (e.g., from a listing action button) or if the create modal needs to be created

### Issue 2: Cotización Header Lacks Tipo Context
- **Description**: All 3 Cotización smart fields render the same header `"Cotización"` with a Calculator icon. There is no per-tipo context label (e.g., "% Liquidación" for PO, "Costo/m²" for M2, "Visitas" for IO). The sub-labels inside the quote preview are different but the section header is identical across all tipos.
- **Severity**: medium
- **Evidence**: `CotizacionPorcentajeSmartField.tsx:158`, `CotizacionM2SmartField.tsx:141` — both say `<h3>Cotización</h3>`
- **Suggested fix**: Add a tipo descriptor to the header, e.g., `<h3>Cotización — Porcentaje de Obra</h3>`

### Issue 3: Form Not Resetting After Successful Submit
- **Description**: After a successful submit, `handleSubmit` clears `contacto` state and calls `onSuccess()` but does NOT reset the GenericForm's internal RHF state. The form fields (expediente, valor_declarado, municipalidad, etc.) remain filled. The user sees the modal close but if they reopen it, the fields are pre-populated with previous data.
- **Severity**: high
- **Evidence**: `EdificacionesFormModal.tsx:53-54` — only `setContacto(null)` and `onSuccess?.()` are called; no form reset
- **Suggested fix**: Call `methods.reset()` after success, or restructure `onSuccess` to reset the form. However, this may be intentional if re-opening is meant to allow duplication — confirm with user.

### Issue 4: EntidadLookupField — Document Type Change Doesn't Clear RHF Numero
- **Description**: When user switches from RUC to DNI (or vice versa) in the RadioGroup, `onValueChange` resets `lookupState.numero_documento` to empty (`EntidadLookupSmartField.tsx:232-235`). But `numDocCtrl.field.value` (the RHF field) is NOT cleared — it still holds the old document number. If the user then types a new number, both old and new coexist confusingly. The lookup will use the old RHF value on the next search.
- **Severity**: high
- **Evidence**: `EntidadLookupSmartField.tsx:232-235` — only `setLookupState` is updated; no `numDocCtrl.field.onChange("")`
- **Suggested fix**: Clear `numDocCtrl.field.onChange("")` when `tipo_documento` changes

### Issue 5: EntidadLookupField — Propietario Auto-fills from Lookup But Can Be Edited
- **Description**: The `nombre_propietario` field (shown as `razonSocialSideSlot` in `EntidadLookupField`) is auto-filled with the lookup result but is a free text input. A user could search RUC, get empresa name filled in propietario, then manually change propietario to a different person's name — and this is not validated against the entity. No warning or lock after lookup.
- **Severity**: medium
- **Evidence**: `EntidadLookupSmartField.tsx:162-165` — `nombrePropietarioCtrl.field.onChange(razonSocial)` sets the value
- **Suggested fix**: After lookup succeeds, disable the propietario field (show as read-only chip with edit option). Or add a visual indicator that it's auto-filled.

### Issue 6: Schema-UI Mismatch on `denominacion`
- **Description**: `proyectoFormSchema.denominacion` is `z.string().optional()` (`liquidacion-form-base.schema.ts:19`) but the UI renders it as a non-required field with no visual indicator of optionality. The label says "Denominación" with no asterisk. However, `nombre_propietario` and `direccion` correctly show `<span className="text-destructive">*</span>` for required fields.
- **Severity**: low
- **Evidence**: `LiquidacionFormBodyBase.tsx:141` — no `required` indicator on `DenominacionField`; schema at `liquidacion-form-base.schema.ts:19`
- **Suggested fix**: Add visual "(opcional)" label to denominacion, or make it consistent with other optional fields

### Issue 7: "TODAS LAS ESPECIALIDADES" Button Label Misleading
- **Description**: The specialty selector header dynamically shows "Todas las Especialidades" when all specialties are selected (`TarifasYEspecialidadesSmartField.tsx:167-172`). But this label also appears in `TipoTramiteSmartField.tsx:109` as the `DropdownMenuLabel` for the Group A options. Users may confuse "Todas las Especialidades" in the dropdown (which is a category of tipo_tramite) with the button in the specialty selector (which means "all specialties are selected"). These are two different concepts with the same label.
- **Severity**: medium
- **Evidence**: `TarifasYEspecialidadesSmartField.tsx:169` labelText and `TipoTramiteSmartField.tsx:109` DropdownMenuLabel both say "Todas las Especialidades"
- **Suggested fix**: Rename the specialty selector's "Todas las Especialidades" to something like "Todas las especialidades aplicadas" or "X de Y especialidades"

### Issue 8: Smart Field Debounce Fires on Every Keystroke Before Debounce Kicks In
- **Description**: The debounced recalculation in `CotizacionPorcentajeSmartField` (500ms) uses `useDebounce`. However, the effect fires `cotizacionMutation.mutate` directly — the debounce is on the VALUE change, but each mutation call still fires even if suppressed by the debounce. Looking at the implementation, `cotizacionMutation.mutate` is called inside `useEffect` which is triggered by the debounced value. If the effect fires rapidly, multiple mutation calls queue up.
- **Severity**: low
- **Evidence**: `CotizacionPorcentajeSmartField.tsx:135-140` — `cotizacionMutation.mutate` called inside effect dependent on `debouncedValor`; effect also depends on `cotizacionMutation.mutate` in deps (`CotizacionPorcentajeSmartField.tsx:142-150`)
- **Suggested fix**: This is a common pattern and generally acceptable. Consider skipping if backend handles concurrent requests gracefully. The `cotizacionMutation` itself uses TanStack Query which deduplicates identical requests.

### Issue 9: IO Create Flow — InspeccionObraCreateFormModal Doesn't Exist
- **Description**: Only `InspeccionObraEditFormModal` was found. For a complete exploration of all 6 tipos' create flows, the IO create form is missing or named differently.
- **Severity**: high
- **Evidence**: File search returned only edit and nueva-revision variants for IO
- **Suggested fix**: Confirm if IO create is handled via a different mechanism or if the file needs to be created

### Issue 10: Contacto Modal — No Deduplication Check
- **Description**: `ContactoFormModal` can be opened multiple times. If a user opens it, saves a contact, closes it, opens it again and saves a different contact — the second contact silently replaces the first without confirmation. There's no "are you sure?" or deduplication warning.
- **Severity**: low
- **Evidence**: `ContactoFormModal.tsx` — `onSaved` callback just calls `setContacto(saved)` without any guard
- **Suggested fix**: Add a check if `contacto` already exists and show a confirmation dialog

### Issue 11: Loading State on Entidad Lookup — No Error State for Network Failure
- **Description**: The "Buscar" button shows a spinner while `isConsulting` is true. But if the lookup API returns an HTTP error (not just "not found"), the error is handled by `handleApiError` at the mutation level. The UI doesn't show a specific error under the document input for network failures vs. "not found" results.
- **Severity**: low
- **Evidence**: `EntidadLookupSmartField.tsx:175-208` — `handleLookup` calls `documentoLookup.mutateAsync`; on error, mutation's `onError` handles it via `handleApiError` globally, not locally
- **Suggested fix**: Show inline error message from `handleApiError` specifically under the document input

### Issue 12: Responsive — 2-Column Grid May Be Too Cramped on Tablet
- **Description**: The grid uses `grid-cols-1 lg:grid-cols-2` meaning on tablet (768px-1024px) the layout is single column, on mobile it's single column. This is acceptable but the left column with tramiteField + motorSection stacked can get very tall.
- **Severity**: low
- **Evidence**: `LiquidacionFormBodyBase.tsx:318` — `lg:grid-cols-2` breakpoint
- **Suggested fix**: Consider `md:grid-cols-2` for tablet support or ensure the motorSection is scrollable on mobile

### Issue 13: Accessibility — No aria-live on Cotización Preview
- **Description**: The Cotización result (`CotizacionPorcentajeSmartField.tsx:174-190`) updates with `setQuote` but there is no `aria-live` region. Screen readers won't announce the quote result.
- **Severity**: medium
- **Evidence**: `CotizacionPorcentajeSmartField.tsx:175` — `<div className="space-y-2 rounded-lg border...">` without aria-live
- **Suggested fix**: Add `aria-live="polite"` to the quote result container

### Issue 14: Accessibility — DropdownMenu Trigger Missing aria-expanded
- **Description**: `TipoTramiteSmartField` uses `DropdownMenuTrigger asChild` on a `Button`. The Button has no `aria-expanded` attribute. The Radix DropdownMenu should handle this automatically but it's worth verifying.
- **Severity**: low
- **Evidence**: `TipoTramiteSmartField.tsx:91-106`
- **Suggested fix**: Add `aria-expanded` tracking if Radix doesn't handle it automatically

### Issue 15: Submit Button — `primaryLoadingLabel` But Loading Label Is Truncated on Mobile
- **Description**: The footer uses `primaryLoadingLabel="Creando..."` but on mobile the primary button shows only the spinner icon (`sm:hidden` on the CheckCircle icon, text is `hidden sm:inline`). So "Creando..." is never visible on mobile — the user only sees a spinner with no context about what's happening.
- **Severity**: medium
- **Evidence**: `AppFormModal.tsx:205-213` — `<span className="hidden sm:inline">` for the loading label; mobile shows only the spinner
- **Suggested fix**: Show a brief text label even on mobile, or ensure the modal title gives enough context

---

## Architecture observations

1. **GenericForm Mode 1 (manual children)**: All 6 create forms use manual children pattern. ✅ Correct per architecture contract.
2. **buildApiPayload in mutation hooks**: Payload construction is correctly placed in `useCrearEdificaciones`, `useCrearHabilitacionUrbana`, etc. ✅ Follows architecture contract.
3. **Error handling via handleApiError**: Mutations propagate errors to `handleApiError` (via TanStack Query's `onError`). The `catch` block in `handleSubmit` is intentionally empty (`EdificacionesFormModal.tsx:63`). ✅
4. **Smart Field isolation**: PO tipos use `TarifasYEspecialidadesSmartField` (PO specialties); M2 tipos use `TarifasM2SmartField` (M2 tarifas); IO uses `CotizacionVisitasSmartField` + `TarifasVisitasNuevaRevisionSmartField`. No cross-contamination. ✅
5. **TipoTramiteSmartField is Edificaciones-only**: HU, MS, IV, Taludes do NOT include this component. IO has a different mechanic (inspector selection). ✅
6. **No GenericForm `reset()` after success**: The form doesn't reset its internal state post-submit. This is potentially intentional (re-use for duplicating entries) but could cause confusion. ⚠️
7. **EntidadLookupField uses local state + RHF**: Architecture pattern is sound (local UI state syncs to RHF on lookup success). ⚠️ The sync on tipo change could be improved (Issue 4 above).
8. **AppFormModal is a thin shell**: It wraps `GenericForm` + `GenericModal` with a footer. The primary submit button triggers form submission via `form={formId}` + `onClick={onPrimary}` where `onPrimary={() => undefined}`. The actual submission happens through `GenericForm`'s `onSubmit` handler. This is correct. ✅

---

## Recommended improvements (priority order)

### High-priority

**1. Fix EntidadLookupField — Clear RHF numero_documento on tipo change**
- What: Add `numDocCtrl.field.onChange("")` when `tipo_documento` changes
- Where: `EntidadLookupSmartField.tsx:232-238`
- Effort: Low — one line addition in the onValueChange handler
- Trade-off: None; fixes data contamination between RUC/DNI

**2. Confirm and Implement IO Create Form**
- What: Determine if `InspeccionObraFormModal` needs to be created (mirroring the HU pattern: base + CotizacionVisitasSmartField + inspector selection)
- Where: New file `InspeccionObraFormModal.tsx` + `useCrearInspeccionObra.ts` hook
- Effort: Medium — needs to mirror HU structure with the IO-specific fields
- Trade-off: Without this, IO creation may be impossible or hidden

**3. Add Form Reset on Successful Submit (or Document Intent)**
- What: After `notify.success` and `printLiquidacion`, call `methods.reset()` OR confirm with user whether reopening should pre-fill
- Where: `EdificacionesFormModal.tsx:53-62` (and all other create forms)
- Effort: Low — one `methods.reset()` call
- Trade-off: If re-opening for duplication is the intended flow, this breaks it. Confirm first.

### Medium-priority

**4. Cotización Header — Add Tipo Context Label**
- What: Show per-tipo descriptor in the Cotización section header
- Where: `CotizacionPorcentajeSmartField.tsx:158`, `CotizacionM2SmartField.tsx:141`, `CotizacionVisitasSmartField.tsx:163`
- Effort: Low — change hardcoded "Cotización" to a prop or computed string
- Trade-off: None; improves UX clarity

**5. EntidadLookupField — Lock/Indicate Propietario After Auto-fill**
- What: Disable `nombre_propietario` input after lookup auto-fills it (with an "edit" button to unlock if needed)
- Where: `EntidadLookupSmartField.tsx` + `LiquidacionFormBodyBase.tsx:NombrePropietarioInline`
- Effort: Medium — needs `disabled` prop flow from EntidadLookupField back through LiquidacionFormBodyBase
- Trade-off: May frustrate users who genuinely want to override the auto-filled name; add unlock option

**6. aria-live on Cotización Preview**
- What: Add `aria-live="polite"` to the quote result container in all 3 Cotización variants
- Where: `CotizacionPorcentajeSmartField.tsx:175`, `CotizacionM2SmartField.tsx:157`, `CotizacionVisitasSmartField.tsx:197`
- Effort: Low — add one aria attribute
- Trade-off: None; improves accessibility

### Low-priority / nice-to-have

**7. Schema-UI Consistency on denominacion**
- What: Add visual "(opcional)" label to `DenominacionField`
- Where: `LiquidacionFormBodyBase.tsx:141`
- Effort: Trivial
- Trade-off: None

**8. Separate "Todas las Especialidades" Label**
- What: Rename the specialty selector's "Todas las Especialidades" to avoid confusion with the `TipoTramiteSmartField` dropdown group label
- Where: `TarifasYEspecialidadesSmartField.tsx:169`
- Effort: Trivial — text change
- Trade-off: Small UX improvement for clarity

**9. Mobile Submit Label**
- What: Show meaningful loading text on mobile submit button
- Where: `AppFormModal.tsx:209-213` or accept as-is since modal header gives context
- Effort: Trivial
- Trade-off: None

**10. Contacto Deduplication Warning**
- What: Add confirmation if user replaces an existing contact
- Where: `EdificacionesFormModal.tsx:41-44` (handleContactoSaved)
- Effort: Low — add `window.confirm()` or a small inline prompt
- Trade-off: May be over-engineering for a minor edge case

---

## Affected files (preliminary)

For the high-priority fixes:

| Change | Files |
|--------|-------|
| Fix EntidadLookup tipo change | `EntidadLookupSmartField.tsx` |
| IO create form (if needed) | New: `InspeccionObraFormModal.tsx`, `useCrearInspeccionObra.ts`; may need new schema `liquidacion-inspeccion-obra-form.schema.ts` |
| Form reset after submit | `EdificacionesFormModal.tsx`, `HabilitacionUrbanaFormModal.tsx`, `MecanicaSuelosFormModal.tsx`, `ImpactoVialFormModal.tsx`, `TaludesFormModal.tsx` (and their mutation hooks) |
| Cotización headers | `CotizacionPorcentajeSmartField.tsx`, `CotizacionM2SmartField.tsx`, `CotizacionVisitasSmartField.tsx` |
| aria-live | Same 3 Cotización files above |
| Propietario lock after lookup | `EntidadLookupSmartField.tsx`, `LiquidacionFormBodyBase.tsx` (NombrePropietarioInline) |

---

## Open questions / decisions needed

1. **IO Create Form**: Does `InspeccionObraFormModal` need to be created? Or is IO creation handled through a different flow? Please confirm.

2. **Form Reset After Submit**: Should reopening the "Nueva Liquidación" modal pre-fill the last-entered values (for easy duplication) or start with a clean form? Currently it pre-fills (no reset).

3. **Propietario Override**: After a SUNAT/RENIEC lookup auto-fills the propietario name, should the user be allowed to freely edit it, or should it be locked with an "edit" button?

4. **"TODAS LAS ESPECIALIDADES" in TipoTramite dropdown vs. specialty chips**: These use the same label for different concepts. Is renaming the specialty chip label (e.g., to "X de Y especialidades") acceptable, or is the current behavior understood by users?

---

## Next Recommended Artifact

After user confirms priorities, the recommended path is:
- **If fixes are small and scoped** → direct edits (no SDD ceremony, per user's earlier preference of `no delegues` for targeted fixes)
- **If IO create form needs to be built** → SDD propose phase first, as it's a new feature with significant architecture decisions (new mutation hook, new schema, new form modal pattern)

**Suggested next step**: User reviews this artifact and indicates which high-priority items to address. Small fixes (Issues 1, 4, 6, 7, 8, 14) can go as direct edits. The IO create form needs a decision from the user first.
