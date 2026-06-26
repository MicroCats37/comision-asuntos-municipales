# Next.js Patterns Lab

Documentation and patterns for building forms and UI components in Next.js applications.

---

## Forms & Validation

### [Field-Level Validation with superRefine](./field-level-validation.md)
Implementing field-level validation using Zod's `superRefine` method and path mappings for nested form errors.

### [Smart File Field Component](./smart-file-field.md)
Building a file upload component with `useController`, badge display, and generic file validation.

### [Nested Form Fields with Dot Notation](./nested-form-fields.md)
Using dot notation in `GenericForm` field configs to work with nested data structures.

---

## Quick Reference

### GenericForm Usage

```typescript
import { GenericForm } from "@/components/genericForm/GenericForm";
import { userSchema } from "./schemas";

const MyForm = () => {
  const handleSubmit = async (data) => {
    console.log("Form submitted:", data);
  };

  return (
    <GenericForm
      schema={userSchema}
      onSubmit={handleSubmit}
      fields={fields}
      title="User Profile"
      submitButtonText="Save"
    />
  );
};
```

### Field Configuration

```typescript
const fields = [
  { name: "email", type: "text", label: "Email", required: true },
  { name: "address.street", type: "text", label: "Street" },
  { name: "roles", type: "select", label: "Role", options: [...], multiple: true },
];
```

### Custom Fields

```typescript
<GenericForm
  schema={schema}
  onSubmit={handleSubmit}
  fields={[{ name: "avatar", type: "custom" }]}
  customFields={{
    avatar: (methods) => <AvatarUpload control={methods.control} />,
  }}
/>
```

---

## Patterns Index

| Pattern | Description | Use Case |
|---------|-------------|----------|
| [Field Validation](./field-level-validation.md) | superRefine + path mapping | Complex validation rules |
| [File Upload](./smart-file-field.md) | useController + badges | File input fields |
| [Nested Fields](./nested-form-fields.md) | Dot notation paths | Hierarchical data |
| [TanStack Cache Mutations](./tanstack-cache-mutations.md) | Generic cache hooks for TanStack Query v5 | Optimistic updates, cache sync |
