# Confirmation Dialog: Inputs & Outputs

## Component API

### ConfirmationDialogProps

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `open` | `boolean` | Yes | — | Controls dialog visibility |
| `onOpenChange` | `(open: boolean) => void` | Yes | — | Called when dialog should close |
| `title` | `string` | Yes | — | Dialog title |
| `description` | `string` | No | — | Dialog description |
| `confirmLabel` | `string` | No | `"Confirmar"` | Confirm button label |
| `cancelLabel` | `string` | No | `"Cancelar"` | Cancel button label |
| `onConfirm` | `() => void` | Yes | — | Called when confirm is clicked |
| `variant` | `"default" \| "danger"` | No | `"default"` | Button variant |

## Hook API

### useConfirmationDialog Return Type

```typescript
interface useConfirmationDialog {
  confirm: (opts: ConfirmOptions) => Promise<boolean>
  Dialog: ReactNode | null
}

interface ConfirmOptions {
  title: string
  description?: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: "default" | "danger"
}
```

## Data Flow

```
confirm({ title, description, variant }) → Promise<boolean>
        ↓
Dialog opens with provided options
        ↓
User clicks Confirm → Promise resolves true → dialog closes
User clicks Cancel → Promise resolves false → dialog closes
User presses Escape → Promise resolves false → dialog closes
```

## Integration with GenericModal

`ConfirmationDialog` uses `GenericModal` as its underlying implementation:

- `GenericModal` provides the dialog portal, overlay, and close behavior
- `ConfirmationDialog` composes Header + Footer with action buttons
- `variant="danger"` renders the confirm button with `variant="destructive"`

## See Also
- [Spec: Confirmation Dialog](./SPEC.md) — full spec
- [Examples: Confirmation Dialog](./EXAMPLES.md) — usage patterns
- [Spec: GenericModal](../modals/SPEC.md) — modal compound components