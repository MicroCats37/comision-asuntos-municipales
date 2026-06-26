# Axios: Instance Configuration

## What is it
Creating a custom Axios client with project-wide defaults to prevent repeating settings in every request.

## Golden Rules
- ✅ DO: Always define a `baseURL` to handle environments (dev/prod) easily via environment variables.
- ✅ DO: Set a reasonable `timeout` (e.g., 10s) to prevent infinitely hanging requests.
- ❌ DON'T: Hardcode the base URL in components; always use the centralized singleton instance.

## Canonical Code

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'https://api.example.com',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

export default api;
```

## Gotchas
- Headers defined in `axios.create` are static. If you need dynamic headers (like a changing Token), use **Interceptors**.
- In Next.js (Server Side), `process.env` keys without `NEXT_PUBLIC_` are only accessible on the server.