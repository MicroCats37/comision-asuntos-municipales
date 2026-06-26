# React 19: Action Hooks (useActionState & useFormStatus)

## What is it
A set of hooks designed to simplify form handling and asynchronous actions, removing the need for manual "loading", "error", and "data" state management.

## Golden Rules
- ✅ DO: Use `useActionState` to handle the full lifecycle of a Server Action or async function.
- ✅ DO: Use `useFormStatus` inside child components (e.g., a Button) to know if the parent form is being submitted.
- ❌ DON'T: Create manual states (`useState`) for `isLoading` or `error` when working with form actions.

## Canonical Code

```jsx
import { useActionState } from 'react';
import { useFormStatus } from 'react-dom'; // Note: useFormStatus is in react-dom

// 1. Intelligent button with useFormStatus
function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending}>
      {pending ? "Sending..." : "Save"}
    </button>
  );
}

// 2. Form with useActionState
function MyForm({ updateAction }) {
  const [error, formAction, isPending] = useActionState(async (prevState, formData) => {
    const res = await updateAction(formData);
    return res.error || null;
  }, null);

  return (
    <form action={formAction}>
      <input name="username" />
      <SubmitButton />
      {error && <p>{error}</p>}
    </form>
  );
}
```

## Gotchas
- `useFormStatus` **ONLY** works if the component is **inside** a `<form>`. It will not work in the same component that defines the `<form>`.
- `useActionState` requires a `prevState` as the first argument of the action function.


