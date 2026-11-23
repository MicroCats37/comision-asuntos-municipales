# EDIF RH reconciliation

Read-only reconciliation against persisted PO details by specialty.

- Cutover scope: `2026-05-01` onward
- Detail CSV: `rh_reconciliation_final.csv`
- H3 existing-RH mismatch CSV: `rh_reconciliation_final_h3_existing_rh_mismatches.csv`
- Reconciled rows: 2442
- Existing RH discrepancy lines: 0
- Missing PO-to-RH specialty lines: 1457

## Unique parent records

- `legacy_edif_post_cutover_parents`: 1208
- `parents_with_any_rh`: 644
- `parents_without_rh`: 564
- `parents_with_existing_rh_mismatches`: 0
- `parents_with_missing_po_to_rh_specialties`: 715
- `h3_parents_with_existing_rh_mismatches`: 0

## Counts by classification

- `PO_EXCLUSIVO_ESPECIALIDAD+RH_CORRECTO`: 338
- `PO_EXCLUSIVO_ESPECIALIDAD+RH_FALTANTE_PARA_PO_DETALLE`: 223
- `PO_TOTAL_EXPLICITO_POR_DETALLE+RH_CORRECTO`: 16
- `PO_TOTAL_EXPLICITO_POR_DETALLE+RH_FALTANTE_PARA_PO_DETALLE`: 17
- `PO_TRES_DETALLES_PERSISTIDOS+RH_CORRECTO`: 631
- `PO_TRES_DETALLES_PERSISTIDOS+RH_FALTANTE_PARA_PO_DETALLE`: 1217

## Discrepancy examples

| Numero | Specialty | PO classification | RH classification | Expected bruto | Actual bruto |
| --- | --- | --- | --- | ---: | ---: |
| 53966 | Ingeniería Sanitaria | PO_TRES_DETALLES_PERSISTIDOS | RH_FALTANTE_PARA_PO_DETALLE | 835.39 |  |
| 53966 | Ingeniería Eléctrica y Mecánica Eléctrica | PO_TRES_DETALLES_PERSISTIDOS | RH_FALTANTE_PARA_PO_DETALLE | 835.40 |  |
| 53966 | Ingeniería Civil | PO_TRES_DETALLES_PERSISTIDOS | RH_FALTANTE_PARA_PO_DETALLE | 835.39 |  |
| 53967 | Ingeniería Civil | PO_TRES_DETALLES_PERSISTIDOS | RH_FALTANTE_PARA_PO_DETALLE | 2003.64 |  |
| 53970 | Ingeniería Civil | PO_TOTAL_EXPLICITO_POR_DETALLE | RH_FALTANTE_PARA_PO_DETALLE | 5413.06 |  |
| 53971 | Ingeniería Sanitaria | PO_TRES_DETALLES_PERSISTIDOS | RH_FALTANTE_PARA_PO_DETALLE | 36.67 |  |
| 53971 | Ingeniería Eléctrica y Mecánica Eléctrica | PO_TRES_DETALLES_PERSISTIDOS | RH_FALTANTE_PARA_PO_DETALLE | 36.66 |  |
| 53971 | Ingeniería Civil | PO_TRES_DETALLES_PERSISTIDOS | RH_FALTANTE_PARA_PO_DETALLE | 36.67 |  |
| 53972 | Ingeniería Sanitaria | PO_TOTAL_EXPLICITO_POR_DETALLE | RH_FALTANTE_PARA_PO_DETALLE | 5413.06 |  |
| 53973 | Ingeniería Eléctrica y Mecánica Eléctrica | PO_TOTAL_EXPLICITO_POR_DETALLE | RH_FALTANTE_PARA_PO_DETALLE | 5413.06 |  |
