# Next.js 16: Component Architecture

## What is it
Next.js uses **Server Components** by default. Code executes on the server and no JavaScript is sent to the client unless the `'use client'` directive is used.

## Golden Rules
- ✅ DO: Keep most components as **Server Components** (especially those handling data).
- ✅ DO: Move `'use client'` as low as possible in the component tree.
- ❌ DON'T: Place `'use client'` at the page level if only a small child component is interactive.

## Canonical Code

```tsx
// 1. Server Component (Data Fetching + Security)
import 'server-only';
import { UserProfile } from './ui/user-profile';
import { ClientToggle } from './ui/client-toggle'; // Client Component

export default async function Page() {
  const data = await db.user.findMany(); // Direct DB access
  
  return (
    <main>
      <UserProfile data={data} />
      <ClientToggle /> 
    </main>
  );
}

// 2. Client Component (Interactivity)
'use client'
import { useState } from 'react';

export function ClientToggle() {
  const [open, setOpen] = useState(false);
  return <button onClick={() => setOpen(!open)}>Toggle</button>;
}
```

## Gotchas
- You cannot import a Server Component directly into a Client Component. Pass it as `children` or as a `prop` (React nodes are serializable).


