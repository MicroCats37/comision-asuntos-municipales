# Date Formatter Spec

## Overview

Centralized date formatting utility using `date-fns` v4. All date formatting in the application MUST use these functions — never format dates inline.

## Architecture

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Library | `date-fns` v4 | Tree-shakeable, pure, predictable |
| Locale | Spanish (`es`) default | Project default locale |
| Error handling | Return `""` on invalid | Never throw on bad input |
| File | `next/src/utils/date-formatter.ts` | Co-located with other utilities |

## Functions

| Function | Output | Default Format |
|----------|--------|----------------|
| `formatDate` | Full date | `"PPP"` → "12 de enero de 2025" |
| `formatDateTime` | Date + time | `"PPp"` → "12 de enero de 2025, 14:30" |
| `formatRelative` | Relative time | `"hace 2 horas"` / `"en 3 días"` |
| `formatShort` | Short date | `"d MMM"` → "12 ene" |

## ✅ REQUIRED

- **Always** use `date-formatter.ts` functions — never format dates inline
- **Always** pass `DateInput` type (handles null/undefined gracefully)
- **Always** use the barrel export from `next/src/utils/index.ts`
- Pass `locale` option only when non-Spanish locale is needed

## ❌ FORBIDDEN

- `new Date().toLocaleDateString()` — inconsistent across browsers and locales
- Inline `format(date, 'dd/MM/yyyy')` without the shared formatter
- Manual string concatenation for dates (e.g., `${day}/${month}/${year}`)

## Locale Strategy

| Scenario | Approach |
|----------|----------|
| Spanish (default) | No option needed — `es` is the default |
| Other locale | Pass `locale` option: `formatDate(date, { locale: enLocale })` |
| Custom format | Pass `customFormat` option: `formatDate(date, { customFormat: 'yyyy-MM-dd' })` |

## Error Handling Policy

All functions accept `DateInput` which includes `null` and `undefined`. Invalid inputs return empty string `""`:

| Input | Behavior |
|-------|----------|
| `null` | Return `""` |
| `undefined` | Return `""` |
| Invalid string | Return `""` |
| Invalid number | Return `""` |
| Valid date | Return formatted string |

## Integration

```typescript
// Re-exported from barrel
export { formatDate, formatDateTime, formatRelative, formatShort } from './date-formatter'
```

## Testing Requirements

| Edge Case | Expected Output |
|-----------|-----------------|
| `null` | `""` |
| `undefined` | `""` |
| `"invalid-date"` | `""` |
| `new Date('2025-01-12')` | Localized string |
| Epoch 0 | `""` (invalid) |
