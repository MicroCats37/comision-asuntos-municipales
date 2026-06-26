# Zod: Form Integration (React Hook Form)

## What is it
The standard integration between Zod validation and React Hook Form (RHF).

## Golden Rules
- ✅ DO: Use `@hookform/resolvers/zod` to connect Zod with RHF.
- ✅ DO: Use `useActionState` (React 19) for the server-side part of the validation.
- ❌ DON'T: Validate manually inside the `onSubmit`; let the resolver handle errors automatically.

## Canonical Code

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

const form = useForm<UserInput>({
  resolver: zodResolver(UserSchema),
});
```

## Gotchas
- RHF uses input types from Zod, ensure you are inferring `UserInput` where appropriate.


