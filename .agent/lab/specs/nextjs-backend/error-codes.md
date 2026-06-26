# Error Codes — Registry

Error codes are identical to Django Ninja for full-stack consistency.

## Rule

**REQUIRED**: All domain errors MUST use one of these registered error codes.

## Error Code Registry

| Code | HTTP Status | Use Case | Example |
|------|-------------|----------|---------|
| `NOT_FOUND` | 404 | Resource does not exist | `new NotFoundError('Post')` |
| `VALIDATION_ERROR` | 422 | Input validation failed | `new ValidationError('Invalid email', { fieldErrors: {...} })` |
| `PERMISSION_DENIED` | 403 | User lacks permission | `new PermissionDeniedError('Admin only')` |
| `CONFLICT` | 409 | Resource conflict | `new ConflictError('Email already registered')` |
| `BUSINESS_ERROR` | 400 | Business rule violated | `new BusinessError('Post is archived')` |
| `INTERNAL_ERROR` | 500 | Unexpected error | `new InternalError('Database connection failed')` |

## Implementation

```typescript
// src/core/errors/index.ts
export abstract class AppError extends Error {
  abstract readonly code: ErrorCode;
  abstract readonly statusCode: number;
  readonly details: Record<string, unknown> | null = null;
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

## Usage in Server Actions

```typescript
// src/app/actions/posts.ts
'use server';

export async function getPostAction(id: string) {
  const post = await postRepository.findById(id);
  if (!post) {
    throw new NotFoundError('Post'); // Returns HTTP 404 with code NOT_FOUND
  }
  return post;
}

export async function createPostAction(data: CreatePostDTO) {
  const existing = await postRepository.findByEmail(data.email);
  if (existing) {
    throw new ConflictError('Email already registered');
  }
  // ... create logic
}
```

## Mapping to HTTP Status

| Code | HTTP Status | Notes |
|------|-------------|-------|
| NOT_FOUND | 404 | Resource not found |
| VALIDATION_ERROR | 422 | Field validation errors with field mapping |
| PERMISSION_DENIED | 403 | Role-based access denied |
| CONFLICT | 409 | Duplicate unique constraint |
| BUSINESS_ERROR | 400 | Domain rule violation |
| INTERNAL_ERROR | 500 | Unexpected — log and hide from client |

## See Also

- [Specs: response-format.md](./response-format.md) — ApiResponse envelope
- [Specs: validation.md](./validation.md) — Zod validation with field errors
- [Patterns: domainError.md](../patterns/nextjs-backend/domain-error.md) — Error class implementation