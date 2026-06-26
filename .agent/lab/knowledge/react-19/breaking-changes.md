# React 19: Breaking Changes & Migration

## What is it
Depreciated or removed features and behavior changes to immediately address when upgrading from React 18.

## Golden Rules
- ✅ DO: Remove all `string refs` (e.g. `ref="myInput"`) and replace them with `useRef`.
- ✅ DO: Replace `defaultProps` in functional components with ES6 destructuring defaults.
- ❌ DON'T: Ignore console warnings; many will become fatal errors in subsequent releases.

## Critical Changes
- **forwardRef removed**: `ref` is now a normal prop.
- **Context as Provider**: Use `<MyContext>` directly instead of `<MyContext.Provider>`.
- **Legacy Context**: Removed entirely.
- **string refs**: Removed entirely.
- **defaultProps**: Removed for functional components.

## Migration Code (Example Context)

```jsx
// Before (v18)
<ThemeContext.Provider value="dark">
  {children}
</ThemeContext.Provider>

// After (v19 - Cleaner)
<ThemeContext value="dark">
  {children}
</ThemeContext>
```

## Gotchas
- `useActionState` was called `useFormState` in early canary versions. Ensure you use the final stable name.
- `useFormStatus` is from `react-dom`, not `react`.