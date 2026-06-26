# React 19: The Compiler Era

## What is it
React 19 introduces the **React Compiler** (Forget), which auto-memoizes components, props, and values, making `useMemo` and `useCallback` mostly unnecessary.

## Golden Rules
- ✅ DO: Write clean, standard React code without overthinking re-renders.
- ✅ DO: Trust the compiler to optimize the render graph.
- ❌ DON'T: Continue memoizing everything by habit; code without `useMemo` is cleaner and easier to maintain.

## Canonical Code

```jsx
// Before (v18): Noisy manual optimization
const memoizedValue = useMemo(() => compute(a, b), [a, b]);
const memoizedCallback = useCallback(() => doSomething(a), [a]);

// After (v19 + Compiler): Same efficiency, cleaner code
const value = compute(a, b);
const callback = () => doSomething(a);
```

## Gotchas
- The compiler assumes components are "pure". They must not mutate objects outside their scope during render.
- For legacy transitions, use the `"use no memo"` directive if a specific component fails with auto-optimization.