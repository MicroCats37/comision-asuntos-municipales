# Axios: Interceptors (Auth & Refresh)

## Context
Combined with Zustand for state management and server-only logic in Next.js to ensure secure credentials handling.

## Recipe
```typescript
import { api } from './axios-instance';
import { useAuthStore } from './stores/auth-store';
import 'server-only';

// Request interceptor: inject JWT token
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 with refresh flow
let isRefreshing = false;
let refreshPromise: Promise<string> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      if (!isRefreshing) {
        isRefreshing = true;
        refreshPromise = useAuthStore.getState().refreshToken()
          .then(token => {
            isRefreshing = false;
            return token;
          })
          .catch(() => {
            isRefreshing = false;
            useAuthStore.getState().logout();
            return null;
          });
      }
      
      const token = await refreshPromise;
      if (token) {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      }
    }
    
    return Promise.reject(error);
  }
);
```

## Why This Way
Interceptors provide a centralized place to inject auth tokens and handle token refresh. Using Zustand's getState() (not a hook) ensures interceptors work outside React components and maintain a single token state.

## See Also
- [Knowledge: Interceptors](../../knowledge/axios/interceptors.md)
- [Spec: Auth (pending)](../../specs/nextjs/auth/SPEC.md)
