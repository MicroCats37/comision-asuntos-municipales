# typed-liquidacion-cards Specification

## Purpose

Defines the behavior of frontend React cards for Mecanica Suelos and Inspeccion Obra list views to render real, typed calculation values.

## Requirements

### Requirement: Render M2 specific data

The system MUST render actual calculation data from the `detalle` object on Mecanica Suelos cards.

#### Scenario: Rendering M2 fields

- GIVEN a typed `LiquidacionM2ListItemOut` response
- WHEN the `LiquidacionMecanicaSuelosCard` is rendered
- THEN it MUST extract and display `area_solicitada` and other M2 snapshot fields from the `detalle` object
- AND it MUST NOT use "TODO" placeholders or hardcoded mock text

### Requirement: Render Inspeccion Obra specific data

The system MUST render actual calculation data from the `detalle` object on Inspeccion Obra cards.

#### Scenario: Rendering IO fields

- GIVEN a typed `LiquidacionIOListItemOut` response
- WHEN the `LiquidacionInspeccionObraCard` is rendered
- THEN it MUST extract and display category/visits calculation fields from the `detalle` object
- AND it MUST NOT use "TODO" placeholders or hardcoded mock text

### Requirement: Safe Types without Casts

The frontend MUST consume the specific API schemas directly without unsafe TypeScript casts.

#### Scenario: Removing 'as' casts

- GIVEN the generated frontend API clients
- WHEN the card wrapper components receive list items
- THEN they MUST naturally accept the inferred types from the specific queries without requiring `as unknown as X` or similar manual type assertions
