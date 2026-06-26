# Next.js 16: Component Architecture (Server/Client Boundary)

## Context
The foundation of our Monorepo. Allows a powerful backend within the frontend without exposing secrets.

## Recipe
```tsx
// server-only.ts - Prevents client bundle inclusion
import 'server-only';

// Server Component (default - executes on server)
export default async function UserProfile({ userId }: { userId: string }) {
  // Direct database access - no API layer needed
  const user = await db.user.findUnique({ where: { id: userId } });
  
  return (
    <div>
      <h1>{user.name}</h1>
      <ClientToggle initialState={user.isActive} />
    </div>
  );
}

// Client Component (needs interactivity)
'use client';
import { useState } from 'react';

export function ClientToggle({ initialState }: { initialState: boolean }) {
  const [isActive, setIsActive] = useState(initialState);
  return (
    <button onClick={() => setIsActive(!isActive)}>
      {isActive ? 'Active' : 'Inactive'}
    </button>
  );
}

// Page composition
import { UserProfile } from './components/user-profile';
import { serverOnly } from './utils/server-only';

export default async function Page({ params }: { params: { id: string } }) {
  return <UserProfile userId={params.id} />;
}
```

## Why This Way
Server Components keep sensitive logic (DB access, env vars) on the server. The 'use client' directive is placed only on leaf components that need interactivity, minimizing the client JavaScript bundle.

## See Also
- [Knowledge: Component Architecture](../../knowledge/nextjs-16/component-architecture.md)
- [Spec: Project Structure IO](../../specs/nextjs/project-structure/IO.md)
