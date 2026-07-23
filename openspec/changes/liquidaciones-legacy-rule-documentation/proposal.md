# Proposal: Liquidaciones Legacy Rule Evaluation

## Intent

Document the mismatch between current active tariff logic and historical `liquidacion` calculations to prevent historical data corruption. Legacy calculations cannot be accurately derived from today's active tariff structures.

## Scope

### In Scope
- Documenting the domain invariant: Tariff != Business Rule.
- Recording the specific calculation drift (e.g., "obra nueva" current 0.15% vs legacy 0.08%).
- Defining architectural constraints for future implementations of historical recalculations.

### Out of Scope
- Code modifications or schema migrations.
- Altering existing live calculation logic.
- Re-introducing `LiquidacionSnapshot` at this time.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- None

## Approach

**Context:** Several `liquidacion` models maintain live foreign keys to tariff models. A prior `LiquidacionSnapshot` model was removed (migration 0019).

**Domain Invariant:** A liquidacion's historical calculation must not be inferred from today's live tariff structure. For example, "obra nueva" currently calculates at 0.15% (summing 3 active specialty tariffs). Legacy calculations used a flat 0.08% without this summation logic. 

**Architectural Decision:** Do not force historical liquidaciones to derive from active tariffs. If the system later requires recalculating or accurately displaying historical data, the legacy logic must be explicitly represented (e.g., a legacy tariff table, regime entity, or explicitly applied-rule source tied to the record). 

No implementation is planned for this phase. This proposal serves as an architectural record.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `liquidaciones` domain | Documentation | Architectural constraint documented |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Data Corruption | High (if ignored) | Documenting this invariant prevents future engineers from writing faulty historical migrations. |

## Rollback Plan

Revert the documentation file addition.

## Dependencies

- None

## Success Criteria

- [x] The domain invariant (Tariff != Business Rule) is clearly recorded.
- [x] Future engineers have explicit context preventing them from forcing current tariff resolution on legacy records.
