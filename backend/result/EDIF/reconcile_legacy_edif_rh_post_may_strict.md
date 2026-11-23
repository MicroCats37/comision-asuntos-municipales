# EDIF RH reconciliation

Read-only reconciliation against persisted PO details by specialty.

- Cutover scope: `2026-06-01` onward
- Detail CSV: `reconcile_legacy_edif_rh_post_may_strict.csv`
- H3 existing-RH mismatch CSV: `reconcile_legacy_edif_rh_post_may_strict_h3_existing_rh_mismatches.csv`
- Reconciled rows: 2065
- Existing RH discrepancy lines: 494
- Missing PO-to-RH specialty lines: 1289

## Unique parent records

- `legacy_edif_post_cutover_parents`: 1021
- `parents_with_any_rh`: 523
- `parents_without_rh`: 498
- `parents_with_existing_rh_mismatches`: 241
- `parents_with_missing_po_to_rh_specialties`: 620
- `h3_parents_with_existing_rh_mismatches`: 225

## Counts by classification

- `PO_EXCLUSIVO_ESPECIALIDAD+RH_CORRECTO`: 282
- `PO_EXCLUSIVO_ESPECIALIDAD+RH_DISCREPANTE_PO_DETALLE`: 10
- `PO_EXCLUSIVO_ESPECIALIDAD+RH_FALTANTE_PARA_PO_DETALLE`: 198
- `PO_TOTAL_EXPLICITO_POR_DETALLE+RH_DISCREPANTE_PO_DETALLE`: 7
- `PO_TOTAL_EXPLICITO_POR_DETALLE+RH_FALTANTE_PARA_PO_DETALLE`: 5
- `PO_TRES_DETALLES_PERSISTIDOS+RH_DISCREPANTE_PO_DETALLE`: 477
- `PO_TRES_DETALLES_PERSISTIDOS+RH_FALTANTE_PARA_PO_DETALLE`: 1086

## Discrepancy examples

| Numero | Specialty | PO classification | RH classification | Expected bruto | Actual bruto |
| --- | --- | --- | --- | ---: | ---: |
| 54163 | Ingeniería Sanitaria | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 42.12 | 31.59 |
| 54163 | Ingeniería Eléctrica y Mecánica Eléctrica | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 42.11 | 31.59 |
| 54163 | Ingeniería Civil | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 42.12 | 31.59 |
| 54165 | Ingeniería Eléctrica y Mecánica Eléctrica | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 155.21 | 116.41 |
| 54165 | Ingeniería Civil | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 155.21 | 116.41 |
| 54166 | Ingeniería Sanitaria | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 36.67 | 27.50 |
| 54166 | Ingeniería Eléctrica y Mecánica Eléctrica | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 36.66 | 27.50 |
| 54168 | Ingeniería Sanitaria | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 140.13 | 105.10 |
| 54168 | Ingeniería Eléctrica y Mecánica Eléctrica | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 140.14 | 105.10 |
| 54168 | Ingeniería Civil | PO_TRES_DETALLES_PERSISTIDOS | RH_DISCREPANTE_PO_DETALLE | 140.13 | 105.10 |
