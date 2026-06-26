# Rate Limiting

Protect APIs from abuse with middleware-based rate limiting.

## Middleware Setup

```typescript
// middleware.ts (root of project)
import { NextRequest, NextResponse } from 'next/server';

interface RateLimitEntry {
  count: number;
  resetAt: number;
}

const rateLimitStore = new Map<string, RateLimitEntry>();

const WINDOW_MS = 60 * 1000;  // 1 minute
const MAX_REQUESTS = 100;

function getRateLimitKey(req: NextRequest): string {
  return req.headers.get('x-forwarded-for')?.split(',')[0]?.trim()
    || req.headers.get('x-real-ip')
    || 'anonymous';
}

function isRateLimited(key: string): { limited: boolean; remaining: number; resetAt: number } {
  const now = Date.now();
  const entry = rateLimitStore.get(key);
  
  if (!entry || now > entry.resetAt) {
    rateLimitStore.set(key, { count: 1, resetAt: now + WINDOW_MS });
    return { limited: false, remaining: MAX_REQUESTS - 1, resetAt: now + WINDOW_MS };
  }
  
  if (entry.count >= MAX_REQUESTS) {
    return { limited: true, remaining: 0, resetAt: entry.resetAt };
  }
  
  entry.count++;
  return { limited: false, remaining: MAX_REQUESTS - entry.count, resetAt: entry.resetAt };
}

export function middleware(req: NextRequest) {
  const key = getRateLimitKey(req);
  const { limited, remaining, resetAt } = isRateLimited(key);
  
  const res = NextResponse.next();
  res.headers.set('X-RateLimit-Remaining', String(remaining));
  res.headers.set('X-RateLimit-Reset', String(Math.ceil(resetAt / 1000)));
  
  if (limited) {
    return NextResponse.json(
      { error: 'Too Many Requests', retryAfter: Math.ceil((resetAt - Date.now()) / 1000) },
      { status: 429, headers: { 'Retry-After': String(Math.ceil((resetAt - Date.now()) / 1000)) } }
    );
  }
  
  return res;
}

export const config = {
  matcher: '/api/:path*'
};
```

---

## Development vs Production

| Environment | Store | Notes |
|------------|-------|-------|
| Development | `Map` in-memory | Simple, single instance only |
| Production | Upstash Redis | Distributed, persists across instances |

---

## Upstash Redis (Production)

```typescript
// lib/rate-limit.ts
import { Redis } from '@upstash/redis';

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL!,
  token: process.env.UPSTASH_REDIS_REST_TOKEN!,
});

interface RateLimitResult {
  limited: boolean;
  remaining: number;
  resetAt: number;
}

export async function checkRateLimit(ip: string, limit = 100, window = 60): Promise<RateLimitResult> {
  const key = `rate:${ip}`;
  const now = Date.now();
  const windowStart = now - window * 1000;
  
  // Sliding window: remove old entries, count recent
  await redis.zremrangebyscore(key, 0, windowStart);
  const count = await redis.zcard(key);
  
  if (count >= limit) {
    const oldest = await redis.zrange(key, 0, 0, { withScores: true });
    const resetAt = oldest[1] ? (oldest[1] as number) + window * 1000 : now + window * 1000;
    return { limited: true, remaining: 0, resetAt };
  }
  
  await redis.zadd(key, { score: now, member: `${now}-${Math.random()}` });
  await redis.expire(key, window);
  
  return { limited: false, remaining: limit - count - 1, resetAt: now + window * 1000 };
}
```

**In middleware:**
```typescript
import { checkRateLimit } from '@/lib/rate-limit';

export async function middleware(req: NextRequest) {
  const ip = getRateLimitKey(req);
  const { limited, remaining, resetAt } = await checkRateLimit(ip);
  // ... same response handling as in-memory version
}
```

---

## What to Rate Limit

| Route Pattern | Limit | Window | Why |
|---------------|-------|--------|-----|
| `POST /api/auth/*` | 5 | 60s | Login attempts |
| `POST /api/comments` | 20 | 60s | Spam prevention |
| `GET /api/search` | 30 | 60s | Search abuse |
| `POST /api/upload` | 10 | 60s | Storage abuse |
| `* /api/*` | 100 | 60s | General API protection |

Apply stricter limits to mutation-heavy and expensive endpoints.
