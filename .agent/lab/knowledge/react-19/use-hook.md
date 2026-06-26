# React 19: The use() Hook

## What is it
A new API that allows reading the value of resources like **Promises** or **Contexts** directly within the component's render function, even inside loops or conditional statements (unlike other hooks).

## Golden Rules
- ✅ DO: Use to consume data fetched on the server (in Server Components) and passed to Client Components.
- ✅ DO: Pair with `Suspense` to handle loading states for consumed promises.
- ❌ DON'T: Create the promise inside the component's render; the promise should be created outside or passed via props to avoid infinite re-renders.

## Canonical Code

```jsx
import { use, Suspense } from 'react';

// 1. Consuming a Promise
function Message({ messagePromise }) {
  const messageContent = use(messagePromise); // Await resolution here
  return <p>{messageContent}</p>;
}

// 2. Consuming a Context conditionally
function ThemedPanel({ showTheme }) {
  if (showTheme) {
    const theme = use(ThemeContext); // Valid in React 19
    return <div style={{ color: theme.color }}>Panel</div>;
  }
  return <div>Simple Panel</div>;
}

export default function App() {
  return (
    <Suspense fallback={<p>Cargando mensaje...</p>}>
      <Message messagePromise={fetchMessage()} />
    </Suspense>
  );
}
```

## Gotchas
- When `use()` receives a promise, the component will "Suspend" until it resolves. You'll need a `Suspense` fallback higher up in the tree.
- It's the only hook-like API that can be called inside an `if` or a `for`.