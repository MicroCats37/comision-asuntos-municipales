# Empty State: Inputs & Outputs

## Component API

### EmptyStateProps

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `icon` | `ReactNode` | No | — | Visual indicator (icon, illustration) |
| `title` | `string` | Yes | — | Primary message for the empty state |
| `description` | `string` | No | — | Secondary explanation or call to action |
| `action` | `ReactNode` | No | — | CTA button, link, or any interactive element |
| `className` | `string` | No | `""` | Additional CSS classes |

## Layout Contract

The component uses flexbox with:
- `flex-col` — vertical stacking
- `items-center justify-center` — centered alignment
- `text-center` — centered text
- `py-12` — vertical padding

## Usage Patterns

```tsx
// Minimum usage (icon + title)
<EmptyState icon={<InboxIcon />} title="No messages" />

// Full usage (icon + title + description + action)
<EmptyState
  icon={<SearchIcon />}
  title="No results found"
  description="Try adjusting your search terms"
  action={<Button>Clear filters</Button>}
/>
```

## See Also
- [Spec: Empty State](./SPEC.md) — full spec
- [Examples: Empty State](./EXAMPLES.md) — usage patterns