# typed-liquidacion-lists Specification

## Purpose

Defines the structure and behavior of type-specific liquidacion list API endpoints, introducing a discriminated `detalle` object to expose specific calculation fields without polluting the general schema.

## Requirements

### Requirement: Expose Common Fields

The system MUST expose all general liquidacion fields stably across all specific list endpoints.

#### Scenario: Base properties

- GIVEN a liquidacion exists in the database
- WHEN a specific list endpoint is queried (e.g., `/liquidaciones/mecanica-suelos`)
- THEN the response items MUST contain standard base fields unaffected by the type

### Requirement: Discriminated `detalle` Object

The system MUST encapsulate type-specific fields in a single `detalle` object discriminated by `tipo`.

#### Scenario: M2 Detalle

- GIVEN a Mecanica Suelos liquidacion
- WHEN `/liquidaciones/mecanica-suelos` is queried
- THEN the `detalle` object MUST have `tipo` equals to `"M2"`
- AND it MUST contain M2 snapshot fields (`area_solicitada`, `costo_m2`, `derecho_minimo`, `derecho_maximo`, `derecho_total`) as available

#### Scenario: Inspeccion Obra Detalle

- GIVEN an Inspeccion Obra liquidacion
- WHEN `/liquidaciones/inspeccion-obra` is queried
- THEN the `detalle` object MUST have `tipo` equals to `"InspeccionObra"` (or corresponding value)
- AND it MUST contain calculation fields (category, visits) as available
