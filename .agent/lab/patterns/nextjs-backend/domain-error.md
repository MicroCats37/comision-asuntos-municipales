# DomainError — Error Class Hierarchy

## Context

All errors in the backend follow a typed hierarchy with codes that map to HTTP status codes. This ensures consistent error responses across the API.

## Recipe

```typescript
// src/core/errors/index.ts
import type { ErrorCode } from '@/core/types';

export abstract class AppError extends Error {
  abstract readonly code: ErrorCode;
  abstract readonly statusCode: number;
  readonly details: Record<string, unknown> | null = null;
  
  constructor(message: string, details?: Record<string, unknown>) {
    super(message);
    this.name = this.constructor.name;
    this.details = details ?? null;
    Error.captureStackTrace(this, this.constructor);
  }
}

export class NotFoundError extends AppError {
  readonly code = 'NOT_FOUND' as const;
  readonly statusCode = 404;
}

export class ValidationError extends AppError {
  readonly code = 'VALIDATION_ERROR' as const;
  readonly statusCode = 422;
  readonly fieldErrors?: Record<string, string[]>;
  
  constructor(message = 'Validation failed', fieldErrors?: Record<string, string[]>) {
    super(message);
    this.fieldErrors = fieldErrors;
  }
}

export class PermissionDeniedError extends AppError {
  readonly code = 'PERMISSION_DENIED' as const;
  readonly statusCode = 403;
}

export class ConflictError extends AppError {
  readonly code = 'CONFLICT' as const;
  readonly statusCode = 409;
}

export class BusinessError extends AppError {
  readonly code = 'BUSINESS_ERROR' as const;
  readonly statusCode = 400;
}

export class InternalError extends AppError {
  readonly code = 'INTERNAL_ERROR' as const;
  readonly statusCode = 500;
}
```

## Error Codes Type

```typescript
// src/core/types/index.ts
export type ErrorCode =
  | 'NOT_FOUND'
  | 'VALIDATION_ERROR'
  | 'PERMISSION_DENIED'
  | 'CONFLICT'
  | 'BUSINESS_ERROR'
  | 'INTERNAL_ERROR';
```

## Mapping to Response Envelope

```typescript
// src/app/_lib/response.ts
import type { ApiResponse, ErrorDetail } from '@/core/types';
import { AppError } from '@/core/errors';

export function errorResponse(error: AppError): ApiResponse<null> {
  const detail: ErrorDetail = {
    code: error.code,
    message: error.message,
    details: error.details,
  };
  
  return { success: false, data: null, error: detail };
}
```

## Usage in Server Actions

```typescript
// src/app/actions/posts.ts
'use server';
import { NotFoundError, ValidationError } from '@/core/errors';

export async function getPost(id: string) {
  const post = await prisma.post.findUnique({ where: { id } });
  if (!post) throw new NotFoundError('Post');
  return post;
}

export async function createPost(data: CreatePostDTO) {
  if (!data.title?.trim()) {
    throw new ValidationError('Title is required', { title: ['Title cannot be empty'] });
  }
  // ... create logic
}
```

## Error Code to HTTP Status Mapping

| Error Code | HTTP Status | Use Case |
|------------|-------------|----------|
| NOT_FOUND | 404 | Resource doesn't exist |
| VALIDATION_ERROR | 422 | Input validation failed |
| PERMISSION_DENIED | 403 | User lacks permission |
| CONFLICT | 409 | Resource conflict (duplicate) |
| BUSINESS_ERROR | 400 | Business rule violation |
| INTERNAL_ERROR | 500 | Unexpected server error |

## See Also

- [Specs: error-codes](../../specs/nextjs-backend/error-codes.md) — Full error code registry
- [Specs: response-format](../../specs/nextjs-backend/response-format.md) — Response envelope format