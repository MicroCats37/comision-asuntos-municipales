# Axios: Error Handling & Cancellation

## What is it
Standardized patterns to detect if an error comes from the server, the network, or a manual request cancellation using `AbortController`.

## Golden Rules
- ✅ DO: Use `axios.isAxiosError(error)` to get full type safety for API responses.
- ✅ DO: Use `AbortController` to cancel pending requests when a component unmounts or a search query changes.
- ❌ DON'T: Rely on generic `try/catch` strings; always check the `error.response?.data` for specific backend messages.

## Canonical Code

```typescript
// 1. Safe Error Handling
try {
  await api.get('/user');
} catch (error) {
  if (axios.isAxiosError(error)) {
    console.error(error.response?.data?.message || 'API Error');
  } else {
    console.error('Unexpected error', error);
  }
}

// 2. Request Cancellation
const controller = new AbortController();
api.get('/search', { signal: controller.signal });
controller.abort(); // Cancel the request
```

## Gotchas
- An "aborted" request throws an error. You must check `axios.isCancel(error)` to ignore it and avoid showing generic error messages to the user.
- Timeouts also trigger an error; ensure your UI distinguishes between a dead server and a manual cancellation.