# Next.js 16: Security & Boundaries

## What is it
Implementing barriers to ensure sensitive data (API keys, private logic) never reaches the client's browser.

## Golden Rules
- ✅ DO: Use the `server-only` package in backend services and DB utilities.
- ✅ DO: Prefix environment variables with `NEXT_PUBLIC_` **ONLY** if intended for client use.
- ❌ DON'T: Import functions using private secret `process.env` in `'use client'` components.

## Canonical Code

```typescript
// lib/db.ts
import 'server-only'; // Build will fail if imported in Client Component

export async function getSecureData() {
  const secretKey = process.env.DATABASE_URL; // Safe here
  // ...
}

// .env
DATABASE_URL="postgres://..." # Private
NEXT_PUBLIC_ANALYTICS_ID="UA-123" # Public
```

## Gotchas
- Next.js 16 supports `taint` (experimental) to mark objects that must never be sent to the client.
- The `server-only` build error is your best friend for avoiding security debt.