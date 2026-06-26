# Next.js 16: Data Fetching Patterns

## What is it
In Next.js 16, fetching happens in Server Components using native `fetch` or direct database/service calls.

## Golden Rules
- ✅ DO: Use `fetch` with the `next: { revalidate: ... }` object for caching control.
- ✅ DO: Parallelize independent requests using `Promise.all` to avoid waterfalls.
- ❌ DON'T: Use `useEffect` for initial page data if it can be pre-rendered on the server.

## Canonical Code

```tsx
// Parallel Fetching in Server Component
export default async function DashboardPage() {
  // Both start at the same time
  const [userData, postsData] = await Promise.all([
    getUser(1),
    getPosts(),
  ]);

  return (
    <div>
      <UserInfo user={userData} />
      <PostList posts={postsData} />
    </div>
  );
}

// Smart Caching
async function getPosts() {
  const res = await fetch('https://api.example.com/posts', {
    next: { tags: ['posts'] }, // For granular invalidation
    cache: 'force-cache',      // SSG Behavior
  });
  return res.json();
}
```

## Gotchas
- The `fetch` cache is persistent. Use `revalidateTag` in Server Actions to clear it.
- Using cookies or headers will cause the page to be dynamic automatically.