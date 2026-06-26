# Confirmation Dialog Spec

## Metadata
- Version: 1.0
- Stack: Next.js 16 + React 19 + TypeScript
- Scope: ConfirmationDialog component + useConfirmationDialog hook for destructive confirmations

---

## Core Principle

> **Use `ConfirmationDialog` + `useConfirmationDialog` for ALL destructive confirmations.**

Never use `window.confirm()` — it blocks the main thread, looks inconsistent, and cannot be styled. The hook pattern returns a promise that resolves to a boolean, enabling async/await confirmation flows.

---

## Rules

### ✅ REQUIRED

- Always use `useConfirmationDialog` hook for confirmation logic
- Use `variant="danger"` for destructive actions (delete, remove, revoke)
- Render `Dialog` in the JSX tree (it's a controlled component that renders based on state)
- The `confirm()` function returns a `Promise<boolean>` for async/await flows

### ❌ FORBIDDEN

- `window.confirm()` — blocks thread, cannot be styled, breaks UX
- Mutating state inside the dialog component itself
- Not rendering `Dialog` in the JSX tree — the dialog is controlled by the hook state
- Passing `onConfirm` that performs state mutations — `handleConfirm` closes the dialog automatically

---

## Architecture

### Hook Pattern

`useConfirmationDialog` manages:
- `open` state for dialog visibility
- `options` state for dialog config (title, description, variant)
- `resolveRef` for Promise resolution

Returns `{ confirm, Dialog }` where:
- `confirm(opts)` opens the dialog and returns a Promise that resolves to `true` (confirm) or `false` (cancel)
- `Dialog` is a React element to render in JSX

### Dialog Flow

```
User calls confirm({ title, variant: 'danger' })
        ↓
Promise created, dialog opens
        ↓
User clicks Confirm → Promise resolves true → handleConfirm closes dialog
        ↓
User clicks Cancel/Escape → Promise resolves false → handleCancel closes dialog
```

---

## Source References

→ [`references/SOURCES.md`](./references/SOURCES.md)