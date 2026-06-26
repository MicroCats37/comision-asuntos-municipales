# Date Formatter — IO Contracts

## Type Definitions

```typescript
type DateInput = Date | string | number | null | undefined

interface FormatOptions {
  locale?: Locale
  customFormat?: string
}
```

## Function Signatures

### formatDate

```typescript
export function formatDate(input: DateInput, options?: FormatOptions): string
```

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `input` | `DateInput` | Date to format. Accepts `Date`, ISO string, Unix timestamp, `null`, or `undefined` |
| `options.locale` | `Locale` | Optional `date-fns` locale. Defaults to Spanish (`es`) |
| `options.customFormat` | `string` | Optional `date-fns` format string |

**Returns:** Full date string in format `"PPP"` (e.g., "12 de enero de 2025"). Returns `""` for invalid input.

---

### formatDateTime

```typescript
export function formatDateTime(input: DateInput, options?: FormatOptions): string
```

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `input` | `DateInput` | Date to format. Accepts `Date`, ISO string, Unix timestamp, `null`, or `undefined` |
| `options.locale` | `Locale` | Optional `date-fns` locale. Defaults to Spanish (`es`) |
| `options.customFormat` | `string` | Optional `date-fns` format string |

**Returns:** Date + time string in format `"PPp"` (e.g., "12 de enero de 2025, 14:30"). Returns `""` for invalid input.

---

### formatRelative

```typescript
export function formatRelative(input: DateInput, options?: FormatOptions): string
```

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `input` | `DateInput` | Date to format. Accepts `Date`, ISO string, Unix timestamp, `null`, or `undefined` |
| `options.locale` | `Locale` | Optional `date-fns` locale. Defaults to Spanish (`es`) |

**Returns:** Relative time string with suffix (e.g., "hace 2 horas", "en 3 días"). Returns `""` for invalid input.

**Note:** Does NOT accept `customFormat` option — uses `formatDistanceToNow` internally.

---

### formatShort

```typescript
export function formatShort(input: DateInput, options?: FormatOptions): string
```

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `input` | `DateInput` | Date to format. Accepts `Date`, ISO string, Unix timestamp, `null`, or `undefined` |
| `options.locale` | `Locale` | Optional `date-fns` locale. Defaults to Spanish (`es`) |
| `options.customFormat` | `string` | Optional `date-fns` format string |

**Returns:** Short date string in format `"d MMM"` (e.g., "12 ene"). Returns `""` for invalid input.

---

## Internal Helper

```typescript
function toDate(input: DateInput): Date | null
```

Converts `DateInput` to `Date` or returns `null` for invalid values. Used internally by all formatters.

**Algorithm:**
1. If input is falsy, return `null`
2. If input is string, parse with `parseISO`
3. Otherwise, construct `new Date(input)`
4. Return `null` if `isValid(date)` is false
