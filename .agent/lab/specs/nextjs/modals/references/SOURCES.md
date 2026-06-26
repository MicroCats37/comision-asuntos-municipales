# Modal Sources Reference

This document maps the architectural specification for Modals to the actual implementation in the project.

## 1. Implementation Files

| Layer | Path | Description |
|-------|------|-------------|
| **Component** | `next/src/components/genericModal/GenericModal.tsx` | Main logic + Compound Atoms |
| **Types** | `next/src/components/genericModal/GenericModal.types.ts` | Shared interfaces |
| **Examples** | `next/src/app/modal-examples/page.tsx` | Usage patterns & Stress tests |

## 2. Framework Dependencies

- **Platform:** [Next.js](https://nextjs.org/)
- **Primitive:** [Radix UI Dialog](https://www.radix-ui.com/docs/primitives/components/dialog)
- **UI Library:** [Shadcn UI](https://ui.shadcn.com/docs/components/dialog)
- **Icons:** [Lucide React](https://lucide.dev/)

## 3. Key Discoveries (Gotchas)

### 3.1 DialogTitle Accessibility
**Discovery:** Radix UI's `DialogContent` requires a child `DialogTitle` to be present for ARIA compliance. 
**Fix:** Our `GenericModal.Content` automatically injects a `<DialogTitle className="sr-only">` to ensure screen reader compatibility when a visual header is not used. 

### 3.2 React 19 Ref Handling
**Discovery:** `forwardRef` is now legacy.
**Fix:** The implementation uses the native `ref` prop as a standard object key in compliant functional components. This is strictly enforced in the `GenericModalRoot` component.
