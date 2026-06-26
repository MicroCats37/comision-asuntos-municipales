# Next.js 16: Streaming & Partial Prerendering (PPR)

## What is it
**Streaming** sends parts of the page to the client while others load. **PPR** combines an instant static shell with dynamic holes filled asynchronously.

## Golden Rules
- ✅ DO: Use `loading.tsx` for route-level loading states.
- ✅ DO: Wrap slow components in `<Suspense>` with high-quality skeletons.
- ❌ DON'T: Let a single slow component block the entire page render.

## Canonical Code

```tsx
import { Suspense } from 'react';
import { SlowComponent, FastComponent } from './ui';

export default function Page() {
  return (
    <section>
      <FastComponent /> {/* Renders immediately */}
      
      <Suspense fallback={<Skeleton />}>
        <SlowComponent /> {/* Streams when ready */}
      </Suspense>
    </section>
  );
}
```

## Gotchas
- `loading.tsx` applies to the entire underlying route hierarchy.
- PPR requires activation in `next.config.js` in some versions.