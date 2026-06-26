# React 19: Action Hooks (useActionState & useFormStatus)

## Context
Founds our Lego Form Components. Enables native integration with Next.js Server Actions.

## Recipe
```tsx
import { useActionState } from 'react';
import { useFormStatus } from 'react-dom';
import { submitForm } from './actions';

// Smart submit button - knows form state without prop drilling
function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending}>
      {pending ? 'Sending...' : 'Save'}
    </button>
  );
}

// Form with full state management
function MyForm({ updateAction }: { updateAction: (prev: unknown, data: FormData) => Promise<Result> }) {
  const [error, formAction, isPending] = useActionState(async (prevState, formData) => {
    const result = await updateAction(formData);
    return result.error || null;
  }, null);

  return (
    <form action={formAction}>
      <input name="email" type="email" required />
      <SubmitButton />
      {error && <p role="alert">{error}</p>}
    </form>
  );
}
```

## Why This Way
useActionState eliminates manual useState for loading/error states. useFormStatus enables semantic button states without prop drilling. Together they provide native React-Next.js form handling.

## See Also
- [Knowledge: Action Hooks](../../knowledge/react-19/action-hooks.md)
- [Spec: Forms IO](../../specs/nextjs/forms/IO.md)
