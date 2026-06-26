# Axios: Types & Generics

## What is it
Enforcing strict TypeScript typing for API responses to ensure the entire application respects the backend contract.

## Golden Rules
- ✅ DO: Always pass a Generic type to the axios method: `api.get<User>('/url')`.
- ✅ DO: Use `Zod` shortly after receiving the data to ensure the type actually matches the reality of the API.
- ❌ DON'T: Use `any` for response data; it destroys the purpose of the platform's type safety.

## Canonical Code

```typescript
import { z } from 'zod';

const UserSchema = z.object({
  id: z.string(),
  name: z.string(),
});

type User = z.infer<typeof UserSchema>;

async function getUser(id: string): Promise<User> {
  const { data } = await api.get<User>(`/users/${id}`);
  // Best practice: double check with Zod
  return UserSchema.parse(data);
}
```

## Gotchas
- Axios generics only type the `data` property of the response object.
- The generic type is a "promise" to TS, but not a runtime guarantee—that's why Zod is mandatory for critical data.