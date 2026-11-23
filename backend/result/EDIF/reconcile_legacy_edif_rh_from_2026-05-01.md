# EDIF RH reconciliation

Read-only reconciliation against persisted PO details by specialty.

- Cutover scope: `2026-05-01` onward
- Detail CSV: `reconcile_legacy_edif_rh_from_2026-05-01.csv`
- H3 existing-RH mismatch CSV: `reconcile_legacy_edif_rh_from_2026-05-01_h3_existing_rh_mismatches.csv`
- Reconciled rows: 2442
- Existing RH discrepancy lines: 658
- Missing PO-to-RH specialty lines: 1457

## Unique parent records

- `legacy_edif_post_cutover_parents`: 1208
- `parents_with_any_rh`: 644
- `parents_without_rh`: 564
- `parents_with_existing_rh_mismatches`: 317
- `parents_with_missing_po_to_rh_specialties`: 715
- `h3_parents_with_existing_rh_mismatches`: 291

## Counts by classification

- `PO_EXCLUSIVO_ESPECIALIDAD+RH_CORRECTO`: 327
- `PO_EXCLUSIVO_ESPECIALIDAD+RH_DISCREPANTE_PO_DETALLE`: 11
- `PO_EXCLUSIVO_ESPECIALIDAD+RH_FALTANTE_PARA_PO_DETALLE`: 223
- `PO_TOTAL_EXPLICITO_POR_DETALLE+RH_DISCREPANTE_PO_DETALLE`: 16
- `PO_TOTAL_EXPLICITO_POR_DETALLE+RH_FALTANTE_PARA_PO_DETALLE`: 17
- `PO_TRES_DETALLES_PERSISTIDOS+RH_DISCREPANTE_PO_DETALLE`: 631
- `PO_TRES_DETALLES_PERSISTIDOS+RH_FALTANTE_PARA_PO_DETALLE`: 1217

## Discrepancy examples

| Numero | Specialty | PO classification | RH classification | Expected bruto | Actual bruto |
| --- | --- | --- | --- | ---: | ---: |
| 53965 | Ingeniería Sanitaria | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 4251.77 | 3188.82 |
| 53965 | Ingeniería Eléctrica y Mecánica Eléctrica | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 4251.76 | 3188.82 |
| 53965 | Ingeniería Civil | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 4251.77 | 3188.82 |
| 53967 | Ingeniería Sanitaria | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 2003.64 | 1502.73 |
| 53967 | Ingeniería Eléctrica y Mecánica Eléctrica | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 2003.63 | 1502.73 |
| 53968 | Ingeniería Civil | PO_TOTAL_EXPLICITO_POR_DETALLE | RH_DISCREPANTE_PO_DETALLE | 113.12 | 339.36 |
| 53969 | Ingeniería Sanitaria | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 495.07 | 371.30 |
| 53969 | Ingeniería Eléctrica y Mecánica Eléctrica | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 495.08 | 371.30 |
| 53969 | Ingeniería Civil | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 495.07 | 371.30 |
| 53977 | Ingeniería Sanitaria | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 13309.17 | 9981.88 |
