# Modals Architecture Spec

**Status:** ✅ Active
**Focus:** Compound Components, Dynamic Widths, State Injection, React 19 Ref Pattern

## 1. Architectural Mandates

### 1.1 The Rule of Total Freedom (Compound Components)
Modals MUST NEVER enforce a rigid visual structure (e.g., forcing a header, body, or footer). They must be implemented as *Compound Components* to allow deep compositional freedom inside the implementing view.

- ❌ **FORBIDDEN:** Creating monolithic modals (e.g., `<GenericModal title="x" footerButtons={[]} />`).
- ❌ **FORBIDDEN:** Using `GenericModal.Headless`, `GenericModal.Title`, `GenericModal.Description`, `GenericModal.Dialog` — these do not exist.
- ✅ **REQUIRED:** Composing modals atom by atom:
  ```tsx
  <GenericModal>
    <GenericModal.Trigger asChild>
      <Button>Open</Button>
    </GenericModal.Trigger>
    <GenericModal.Content>
      <GenericModal.Header title="Visual Title" />
      <GenericModal.Body>...</GenericModal.Body>
      <GenericModal.Footer>
        <GenericModal.Close asChild>
          <Button variant="outline">Cancel</Button>
        </GenericModal.Close>
      </GenericModal.Footer>
    </GenericModal.Content>
  </GenericModal>
  ```

### 1.2 The "Hug Content" Rule (Dynamic Widths)
Modals MUST NOT enforce arbitrary fixed widths (e.g., `sm:max-w-sm` or `w-[425px]`) at the core level. They must default to `w-fit` (Hug Content).
- If a modal needs to be wide, the *implementing developer* passes `className="sm:min-w-3xl"` to `<GenericModal.Content>`.
- Core handles global responsive capping so it never exceeds screen limits (`max-h-[90vh]`, `max-w-full`).

### 1.3 Internal Scroll & Sticky Actions
- **Body:** Content that has unpredictable length MUST be placed inside `<GenericModal.Body>`. This component automatically injects `overflow-y-auto` and `flex-1`. Default `scrollable={true}`.
- **Footer/Header:** Actions that must remain visible (e.g., "Submit", "Cancel") MUST NOT be inside the body. They must be placed in `<GenericModal.Footer>`, which defaults to `sticky={true}` (stays at the bottom even if body scrolls).
- **CloseX:** The `GenericModal.CloseX` component renders a predefined X button (close icon) in the top-right corner. It auto-hides when `preventClose={true}`.

### 1.4 Deep State Injection (No Prop Drilling)
Elements deep inside the modal tree (like a custom Close button or a form submission handler) MUST NOT require physical `close` functions drilled down via props.
- ✅ **REQUIRED:** Use the internal context to close the modal programmatically from anywhere inside:
  ```tsx
  const { close, forceClose, isOpen, preventClose } = useGenericModal();
  ```
- Or use the headless wrapper to inject `onClick={close}` automatically:
  ```tsx
  <GenericModal.Close asChild><Button>Cancel</Button></GenericModal.Close>
  ```

### 1.5 React 19 Ref Standard
Modals MUST NOT use `forwardRef`. The root component must accept `ref` strictly as a native property in its interface, aligning with the `react-19` knowledge base rules.

---

## 2. Canonical Structure

All modals in this project extend or compose `GenericModal`.

```tsx
// 1. Uncontrolled Composition (Preferred for simple flows)
<GenericModal preventClose>
  {/* The Trigger lives outside the dialog portal but inside the context provider */}
  <GenericModal.Trigger asChild>
    <Button>Open</Button>
  </GenericModal.Trigger>

  <GenericModal.Content>
    <GenericModal.Header title="Warning" />
    <GenericModal.Body>
      <p>Content goes here. It will scroll if it gets too large.</p>
    </GenericModal.Body>
    <GenericModal.Footer>
      <GenericModal.Close asChild>
        <Button variant="outline">Dismiss</Button>
      </GenericModal.Close>
    </GenericModal.Footer>
  </GenericModal.Content>
</GenericModal>

// 2. Controlled via React 19 Ref (Preferred for complex asynchronous triggers)
const modalRef = useRef<GenericModalRef>(null);

const handleAsyncFetch = async () => {
    await fetchSomething();
    modalRef.current?.open(); // Imperative open
}

<GenericModal ref={modalRef}>
   <GenericModal.Content>
      <GenericModal.Body>Success!</GenericModal.Body>
   </GenericModal.Content>
</GenericModal>
```

## 3. Integration with Radix UI (Smart Accessibility)

We build on top of Shadcn's `<Dialog>` primitive (which implements Radix).

### 3.1 Smart A11y Auto-Detection
Radix UI *requires* a `DialogTitle` inside `DialogContent`. Traditionally, omitting a visible header caused console errors.
- **Project Solution:** The core component uses **Context-based Auto-Detection**.
- **How it works:** 
  1. `<GenericModal.Header>` registers its existence on mount via context.
  2. `<GenericModal.Content>` checks if a header was registered.
  3. If **no header** is detected, the component automatically injects a `<DialogTitle className="sr-only">Modal Content</DialogTitle>`.
- **Developer Experience:** You can safely omit headers for minimal designs without seeing errors or writing `sr-only` hacks manually.

### 3.2 Interception & Control
The `<GenericModal>` accepts an `onBeforeClose` async callback. If the backdrop is clicked or the modal triggers a close, this interceptor runs first. Returning `false` aborts the closing sequence (ideal for "Unsaved Changes" checks).

### 3.3 Prevent Close Mode
When `preventClose={true}`:
- Clicking outside the modal does nothing
- Pressing ESC does nothing
- The `GenericModal.CloseX` button is hidden automatically
- Use `forceClose()` on the ref to bypass this (e.g., after form submission succeeds)
