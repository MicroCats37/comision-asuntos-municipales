# Axios: Interceptors (Auth & Refresh)

## What is it
Functions that Axios triggers before a request is sent or before a response is handled by `then` or `catch`. Ideal for injecting JWT tokens and handling 401 (Unauthorized) errors globally.

## Golden Rules
- ✅ DO: Inject active tokens (from Zustand or Cookies) in the `request` interceptor.
- ✅ DO: Handle `401` errors in the `response` interceptor to trigger logout or refresh flows.
- ❌ DON'T: Create complex nested logic inside interceptors; keep them fast to avoid request latency.

## Canonical Code

```typescript
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token; // Get token from Zustand
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Trigger global logout or refresh token flow
    }
    return Promise.reject(error);
  }
);
```

## Gotchas
- Response interceptors can get stuck in infinite loops if a "retry" also yields a 401. Always implement a "once-only" or "max-retries" logic.
- Remember to return the `config` or `response` object, otherwise the request flow breaks.


