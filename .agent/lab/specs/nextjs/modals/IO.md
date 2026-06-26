# Modals: Inputs & Outputs

## Component API

### GenericModal Root Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `children` | `ReactNode` | Yes | — | Modal trigger, content, and compound parts |
| `open` | `boolean` | No | — | Controlled open state. If omitted, operates uncontrolled |
| `onOpenChange` | `(open: boolean) => void` | No | — | Callback fired when open state changes. Required for controlled mode |
| `ref` | `Ref<GenericModalRef>` | No | — | Imperative control via React 19 ref pattern |
| `preventClose` | `boolean` | No | `false` | Blocks backdrop click and ESC from closing |
| `onBeforeClose` | `() => boolean \| Promise<boolean>` | No | — | Interceptor before closing. Return `false` to abort |

### Compound Component Props

#### `GenericModal.Trigger`
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `children` | `ReactNode` | Yes | — | Trigger element |
| `asChild` | `boolean` | No | `false` | Merge props onto child element |

#### `GenericModal.Content`
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `children` | `ReactNode` | Yes | — | Modal content |
| `className` | `string` | No | — | Custom width styles (e.g., `sm:min-w-3xl`) |

#### `GenericModal.Header`
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | `ReactNode` | No | — | Modal title |
| `description` | `ReactNode` | No | — | Modal description |
| `className` | `string` | No | — | Custom styles |
| `children` | `ReactNode` | No | — | Additional header content |

#### `GenericModal.Body`
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `children` | `ReactNode` | Yes | — | Scrollable content |
| `className` | `string` | No | — | Custom styles |
| `scrollable` | `boolean` | No | `true` | Enable y-scroll when content exceeds height |

#### `GenericModal.Footer`
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `children` | `ReactNode` | Yes | — | Footer content (buttons, etc.) |
| `className` | `string` | No | — | Custom styles |
| `sticky` | `boolean` | No | `true` | Stay at bottom when body scrolls |

#### `GenericModal.Close`
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `children` | `ReactNode` | Yes | — | Element to wrap |
| `asChild` | `boolean` | No | `false` | Merge `onClick={close}` into child |

#### `GenericModal.CloseX`
| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `className` | `string` | No | — | Custom styles |

---

## Ref API (GenericModalRef)

```typescript
interface GenericModalRef {
  open: () => void;
  close: () => void;
  forceClose: () => void;
  isOpen: boolean;
  preventClose?: boolean;
  hasHeader: boolean;
  registerHeader: (exists: boolean) => void;
}
```

```tsx
// Usage with React 19 ref pattern (no forwardRef)
const modalRef = useRef<GenericModalRef>(null);

<GenericModal ref={modalRef}>
  {/* ... */}
</GenericModal>

// Later:
modalRef.current?.open();
modalRef.current?.close();
modalRef.current?.forceClose(); // Bypasses preventClose
```

---

## Context API

```typescript
// For deep state injection (no prop drilling)
const { isOpen, open, close, forceClose, preventClose, hasHeader, registerHeader } = useGenericModal();

// Inside any component within the modal tree
```

---

## Accessibility Contract

### Auto Title Injection
If no `GenericModal.Header` is provided, the modal automatically injects:
```tsx
<DialogTitle className="sr-only">Modal Content</DialogTitle>
```

### CloseX Button
- Renders as a predefined `<button>` with X icon in top-right corner
- Auto-hidden when `preventClose={true}`

---

## Dynamic Width Behavior

| Props on `GenericModal.Content` | Result |
|---------------------------------|--------|
| None | `w-full sm:max-w-fit` (hug content up to `sm`) |
| `className="sm:min-w-3xl"` | Wide modal |
| `className="sm:max-w-sm"` | Narrow modal |

Core CSS: `max-h-[90vh] max-w-full` prevents overflow.

---

## ❌ FORBIDDEN

| Pattern | Why |
|---------|-----|
| `<GenericModal title="..." footerButtons={[]} />` | Monolithic, no compositional freedom |
| `GenericModal.Headless` | Does not exist |
| `GenericModal.Title` | Does not exist — use `GenericModal.Header title={...}` |
| `GenericModal.Description` | Does not exist — use `GenericModal.Header description={...}` |
| `GenericModal.Dialog` | Does not exist |
| `forwardRef` on modal root | Violates React 19 ref standard |
| Fixed `w-[425px]` in core | Kills "hug content" flexibility |
| Putting sticky actions in `Body` | Use Footer instead |

---

## See Also
- [Spec: Modals](./SPEC.md) — full spec
- [Knowledge: React 19 Ref Pattern](../../knowledge/react-19/refs-simplified.md)
