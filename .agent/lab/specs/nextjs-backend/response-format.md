# Response Format — ApiResponse Envelope

All API responses use a unified envelope identical to Django Ninja's format.

## Rule

**REQUIRED**: All Server Actions return `ApiResponse<T>` with `{ success, data, error, meta }` structure.

## TypeScript Interface

```typescript
// src/core/types/api-response.ts
export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ErrorDetail | null;
  meta?: PaginationMeta | null;
}

export interface ErrorDetail {
  code: ErrorCode;
  message: string;
  details?: Record<string, unknown> | null;
}

export type ErrorCode =
  | 'NOT_FOUND'
  | 'VALIDATION_ERROR'
  | 'PERMISSION_DENIED'
  | 'CONFLICT'
  | 'BUSINESS_ERROR'
  | 'INTERNAL_ERROR';

export interface PaginationMeta {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}
```

## Response Helper Functions

### `src/app/_lib/response.ts`

```typescript
import type { ApiResponse, PaginationMeta } from '@/core/types';
import { AppError } from '@/core/errors';

export function successResponse<T>(data: T, meta?: PaginationMeta): ApiResponse<T> {
  return { success: true, data, error: null, meta: meta ?? null };
}

export function errorResponse(error: AppError): ApiResponse<null> {
  return {
    success: false,
    data: null,
    error: {
      code: error.code,
      message: error.message,
      details: error.details,
    },
  };
}

export function paginationMeta(page: number, pageSize: number, total: number): PaginationMeta {
  return { page, pageSize, total, totalPages: Math.ceil(total / pageSize) };
}
```

## Usage in Server Actions

```typescript
// src/app/actions/posts.ts
'use server';
import { successResponse, errorResponse, paginationMeta } from '../_lib/response';
import { NotFoundError } from '@/core/errors';

export async function getPostsAction(page = 1, pageSize = 20) {
  try {
    const { data, total } = await postRepository.findAll({ page, pageSize });
    return successResponse(data, paginationMeta(page, pageSize, total));
  } catch (e) {
    if (e instanceof AppError) return errorResponse(e);
    throw e;
  }
}

export async function getPostAction(id: string) {
  try {
    const post = await postRepository.findById(id);
    if (!post) return errorResponse(new NotFoundError('Post'));
    return successResponse(post);
  } catch (e) {
    if (e instanceof AppError) return errorResponse(e);
    throw e;
  }
}
```

## Response Examples

### Success Response
```json
{
  "success": true,
  "data": { "id": "clxxx", "title": "Hello" },
  "error": null,
  "meta": null
}
```

### Paginated Response
```json
{
  "success": true,
  "data": [{ "id": "clxxx", "title": "Hello" }],
  "error": null,
  "meta": { "page": 1, "pageSize": 20, "total": 42, "totalPages": 3 }
}
```

### Error Response
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Title is required",
    "details": { "fieldErrors": { "title": ["Title cannot be empty"] } }
  }
}
```

## See Also

- [Specs: error-codes.md](./error-codes.md) — Error code definitions
- [Specs: validation.md](./validation.md) — Zod schema validation
- [Specs: shared/api-format.md](../shared/api-format.md) — Cross-cutting API format