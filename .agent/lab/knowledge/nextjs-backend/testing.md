# Testing Next.js Applications

## Vitest Setup

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    include: ['src/**/*.test.{ts,tsx}'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

```typescript
// src/test/setup.ts
import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock Next.js server components
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => '/',
  redirect: vi.fn(),
}));

// Mock revalidate functions
vi.mock('next/cache', () => ({
  revalidatePath: vi.fn(),
  revalidateTag: vi.fn(),
}));
```

---

## Testing Server Actions

Server Actions contain business logic. Test them directly without React rendering.

```typescript
// src/core/posts/actions.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createPostAction } from './actions';

// Mock Prisma
vi.mock('@/infra/prisma/client', () => ({
  prisma: {
    post: {
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      findUnique: vi.fn(),
    },
  },
}));

import { prisma } from '@/infra/prisma/client';

describe('createPostAction', () => {
  beforeEach(() => vi.clearAllMocks());
  
  it('creates a post and revalidates path', async () => {
    const mockPost = { id: '1', title: 'Test', content: 'Content', published: false };
    vi.mocked(prisma.post.create).mockResolvedValue(mockPost);
    
    const formData = new FormData();
    formData.set('title', 'Test');
    formData.set('content', 'Content');
    
    const result = await createPostAction({ status: 'idle', errors: {} }, formData);
    
    expect(result.status).toBe('success');
    expect(prisma.post.create).toHaveBeenCalledWith({
      data: { title: 'Test', content: 'Content' }
    });
  });
  
  it('returns error on validation failure', async () => {
    const formData = new FormData();
    // missing title
    
    const result = await createPostAction({ status: 'idle', errors: {} }, formData);
    
    expect(result.status).toBe('error');
    expect(result.errors.title).toBeDefined();
  });
});
```

---

## Integration Tests with Prisma + SQLite

For integration tests, use SQLite (mirrors Django's `USE_SQLITE` pattern).

```typescript
// vitest.config.ts (test environment)
export default defineConfig({
  test: {
    setupFiles: ['./src/test/setup.ts', './src/test/prisma-sqlite.ts'],
  },
});
```

```typescript
// src/test/prisma-sqlite.ts
import { PrismaClient } from '@prisma/client';
import { execSync } from 'child_process';

const prisma = new PrismaClient({
  datasources: {
    db: { url: 'file:./test.db' }
  }
});

// Reset database before each test suite
beforeAll(async () => {
  execSync('npx prisma migrate reset --force', { 
    env: { ...process.env, DATABASE_URL: 'file:./test.db' } 
  });
});

afterAll(() => prisma.$disconnect());
```

---

## Component Testing with Testing Library

```typescript
// src/components/PostForm.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PostForm } from './PostForm';
import { createPostAction } from '@/core/posts/actions';

vi.mock('@/core/posts/actions', () => ({
  createPostAction: vi.fn(),
}));

describe('PostForm', () => {
  it('submits form data to Server Action', async () => {
    const mockAction = vi.mocked(createPostAction).mockResolvedValue({
      status: 'success',
      data: { id: '1', title: 'Test' }
    });
    
    render(<PostForm />);
    
    fireEvent.change(screen.getByLabelText(/title/i), { target: { value: 'Test' } });
    fireEvent.change(screen.getByLabelText(/content/i), { target: { value: 'Content' } });
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));
    
    expect(mockAction).toHaveBeenCalled();
  });
});
```

---

## Test Naming Conventions

| Pattern | Example | Purpose |
|---------|---------|---------|
| Unit | `actions.test.ts` | Pure function logic |
| Integration | `prisma.test.ts` | DB operations with SQLite |
| Component | `PostForm.test.tsx` | React component behavior |
| E2E | `posts.spec.ts` | Full user flows (Playwright) |

---

## Running Tests

```bash
# Unit + integration
npx vitest run

# Watch mode
npx vitest

# Specific file
npx vitest run src/core/posts/actions.test.ts

# With coverage
npx vitest run --coverage
```

---

## Mocking Priority

1. **Infrastructure** (Prisma, S3, Redis) — always mock in unit tests
2. **Next.js internals** (revalidate, router) — mock via `vi.mock`
3. **External APIs** — mock at the HTTP layer with MSW if needed

Keep tests fast: unit tests should run in <100ms each.
