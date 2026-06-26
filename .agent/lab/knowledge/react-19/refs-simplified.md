# React 19: Simplified Refs

## What is it
In React 19, `ref` is a standard prop. `forwardRef` is no longer required for functional components.

## Golden Rules
- ✅ DO: Pass `ref` directly as a prop to your child components.
- ✅ DO: Use for direct and clean access to DOM nodes or component instances.
- ❌ DON'T: Keep using `forwardRef` in new projects; it is slated for future deprecation.

## Canonical Code

```jsx
// React 19: Accepts 'ref' as a normal prop
function CustomInput({ label, ref, ...props }) {
  return (
    <label>
      {label}
      <input ref={ref} {...props} />
    </label>
  );
}

// Usage:
function Parent() {
  const inputRef = useRef(null);
  return <CustomInput ref={inputRef} label="Name" />;
}
```

## Gotchas
- Ensure you extract `ref` from the props object if using destructuring.
- For TypeScript, include `ref?: React.Ref<HTMLInputElement>` in your Props interface.