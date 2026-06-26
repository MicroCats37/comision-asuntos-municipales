# Webhooks

Receive and verify incoming webhooks from third-party services (Stripe, GitHub, etc.).

## Route Handler Structure

```typescript
// app/api/webhooks/[provider]/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { handleStripeWebhook } from '@/core/webhooks/stripe';
import { handleGitHubWebhook } from '@/core/webhooks/github';

export async function POST(req: NextRequest, { params }: { params: { provider: string } }) {
  const { provider } = params;
  
  const rawBody = await req.text(); // keep raw for signature verification
  
  switch (provider) {
    case 'stripe':
      return handleStripeWebhook(rawBody, req.headers);
    case 'github':
      return handleGitHubWebhook(rawBody, req.headers);
    default:
      return NextResponse.json({ error: 'Unknown provider' }, { status: 400 });
  }
}
```

---

## HMAC Signature Verification

### Stripe Pattern

```typescript
// core/webhooks/stripe.ts
import { headers } from 'next/headers';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);
const endpointSecret = process.env.STRIPE_WEBHOOK_SECRET!;

export async function handleStripeWebhook(
  rawBody: string,
  headers: Headers
): Promise<NextResponse> {
  const sig = headers.get('stripe-signature')!;
  
  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(rawBody, sig, endpointSecret);
  } catch (err) {
    console.error('Webhook signature verification failed:', err);
    return NextResponse.json({ error: 'Invalid signature' }, { status: 400 });
  }
  
  // Return 200 immediately — process async
  queueJob('stripe-webhook', { event });
  
  return NextResponse.json({ received: true });
}
```

### GitHub Pattern

```typescript
// core/webhooks/github.ts
import { createHmac } from 'crypto';

const GITHUB_WEBHOOK_SECRET = process.env.GITHUB_WEBHOOK_SECRET!;

function verifyGitHubSignature(payload: string, signature: string): boolean {
  const expected = createHmac('sha256', GITHUB_WEBHOOK_SECRET)
    .update(payload)
    .digest('hex');
  return `sha256=${expected}` === signature;
}

export async function handleGitHubWebhook(
  rawBody: string,
  headers: Headers
): Promise<NextResponse> {
  const sig = headers.get('x-hub-signature-256')!;
  
  if (!verifyGitHubSignature(rawBody, sig)) {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 401 });
  }
  
  const event = headers.get('x-github-event')!;
  const delivery = headers.get('x-github-delivery')!;
  
  // Return 200 immediately, process async
  queueJob('github-webhook', { event, delivery, body: JSON.parse(rawBody) });
  
  return NextResponse.json({ received: true });
}
```

---

## "200-Fast" Pattern

**Always respond 200 within milliseconds.** Third-party webhooks retry based on response time and status code.

```typescript
export async function POST(req: NextRequest) {
  // 1. Verify signature (fast)
  if (!verifySignature(rawBody, headers)) {
    return NextResponse.json({ error: 'Invalid' }, { status: 401 });
  }
  
  // 2. Respond 200 immediately
  // 3. Process in background (queue)
  const job = await import('@/lib/queue').then(m => m.queue);
  await job.enqueue('process-webhook', { provider, body: rawBody });
  
  return NextResponse.json({ ok: true });
}
```

**Queue implementation (Bull/BullMQ or similar):**
```typescript
// lib/queue.ts
import { Queue } from 'bull';
export const queue = new Queue('webhooks', { redis: { url: process.env.REDIS_URL } });
```

---

## Raw Body Parsing

Signature verification requires the **raw** request body — before Next.js parses it.

```typescript
// For Server Actions this happens automatically.
// For Route Handlers, use req.text() directly.

// ⚠️ If you use Next.js custom server and parse the body earlier,
// you must preserve the raw body for signature verification.

// In Next.js App Router, req.text() gives you the raw body:
const rawBody = await req.text();
```

---

## Testing Webhooks Locally

```bash
# Stripe CLI
stripe listen --forward-to localhost:3000/api/webhooks/stripe

# GitHub
ngrok http 3000
# Then configure GitHub webhook URL in repo settings
```

---

## Quick Reference

| Provider | Header for Signature | Algorithm |
|----------|---------------------|-----------|
| Stripe | `stripe-signature` | HMAC SHA256 |
| GitHub | `x-hub-signature-256` | HMAC SHA256 |
| Slack | `x-slack-signature` | HMAC SHA256 |

**Always** verify signatures before processing. **Always** respond 200 fast, queue for async processing.
