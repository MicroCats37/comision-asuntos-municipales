# Nested Form Fields with Dot Notation

This pattern explains how to use dot notation in `GenericForm` field configs to work with nested data structures.

## Overview

`GenericForm` supports dot notation in field names to represent nested object paths. This allows you to:
- Work with hierarchical data structures
- Display fields from nested objects in flat form sections
- Leverage Zod's path mapping for validation errors

## Dot Notation Basics

When you specify a field name with dots, `GenericForm` uses it directly as the:
1. **Form field name** - passed to `register()`
2. **Error lookup path** - used by `getNestedError` to find validation errors

### Example: Simple Nested Object

```typescript
// Data structure
interface Address {
  street: string;
  city: string;
  country: string;
}

interface UserFormData {
  name: string;
  address: Address;
}

// Form configuration
const fields: FormField[] = [
  { name: "name", type: "text", label: "Nombre" },
  { name: "address.street", type: "text", label: "Calle" },
  { name: "address.city", type: "text", label: "Ciudad" },
  { name: "address.country", type: "select", label: "País", options: [...] },
];
```

### Generated Form HTML

```html
<input name="name" ... />
<input name="address.street" ... />
<input name="address.city" ... />
<select name="address.country" ... />
```

## How getNestedError Works

The `getNestedError` utility traverses nested objects using dot notation:

```typescript
const getNestedError = (obj: any, path: string) => {
  return path.split(".").reduce((acc, part) => acc && acc[part], obj);
};

// Example
const errors = {
  address: {
    street: { message: "La calle es requerida" },
    city: { message: "La ciudad es requerida" },
  },
};

getNestedError(errors, "address.street");
// → { message: "La calle es requerida" }

getNestedError(errors, "address.country");
// → undefined (no error)
```

## Array Fields with Index Notation

For arrays, use numeric indices in dot notation:

```typescript
const fields: FormField[] = [
  { name: "tasks.0.title", type: "text", label: "Tarea 1" },
  { name: "tasks.0.completed", type: "checkbox", label: "Completada" },
  { name: "tasks.1.title", type: "text", label: "Tarea 2" },
  { name: "tasks.1.completed", type: "checkbox", label: "Completada" },
];
```

## Zod Schema Path Mapping

For validation errors to display correctly, your Zod schema must use matching paths:

```typescript
import { z } from "zod";

const taskSchema = z.object({
  tasks: z.array(z.object({
    title: z.string().min(1, "El título es requerido"),
    completed: z.boolean(),
  })),
});

// Using superRefine for cross-field validation
const formSchema = z.object({
  tasks: z.array(z.object({
    title: z.string(),
    deadline: z.date(),
  })),
}).superRefine((data, ctx) => {
  data.tasks.forEach((task, index) => {
    if (!task.completed && !task.deadline) {
      ctx.addIssue({
        code: "custom",
        message: "Deadline required for incomplete tasks",
        path: ["tasks", index.toString(), "deadline"],
      });
    }
  });
});
```

## Section Organization

You can organize nested fields into form sections for better UX:

```typescript
const formSections: FormSection[] = [
  {
    title: "Información Personal",
    fields: [
      { name: "name", type: "text", label: "Nombre completo" },
      { name: "email", type: "text", label: "Correo electrónico" },
      { name: "phone", type: "text", label: "Teléfono" },
    ],
  },
  {
    title: "Dirección",
    fields: [
      { name: "address.street", type: "text", label: "Calle y número" },
      { name: "address.city", type: "text", label: "Ciudad" },
      { name: "address.state", type: "text", label: "Estado/Provincia" },
      { name: "address.zip", type: "text", label: "Código postal" },
      { name: "address.country", type: "select", label: "País", options: countries },
    ],
  },
  {
    title: "Información del Trabajo",
    fields: [
      { name: "employment.company", type: "text", label: "Empresa" },
      { name: "employment.position", type: "text", label: "Puesto" },
      { name: "employment.salary", type: "number", label: "Salario" },
    ],
  },
];
```

## GenericInput Error Traversal

`GenericInput` automatically uses `getNestedError` to resolve nested paths:

```typescript
// In GenericInput.tsx
const error = getNestedError(errors, field.name) as { message?: string } | undefined;

// For field.name = "address.street"
// It looks up errors.address.street
// Returns undefined if no error exists at that path
```

## Complete Example

### 1. Define Types

```typescript
interface ContactInfo {
  email: string;
  phone: string;
}

interface Address {
  street: string;
  city: string;
  country: string;
}

interface UserProfile {
  name: string;
  contact: ContactInfo;
  address: Address;
}
```

### 2. Create Zod Schema

```typescript
const userProfileSchema = z.object({
  name: z.string().min(2, "Nombre muy corto"),
  contact: z.object({
    email: z.string().email("Email inválido"),
    phone: z.string().min(10, "Teléfono inválido"),
  }),
  address: z.object({
    street: z.string().min(5, "Dirección muy corta"),
    city: z.string().min(2, "Ciudad muy corta"),
    country: z.string().min(2, "País requerido"),
  }),
});
```

### 3. Configure Form Fields

```typescript
const fields: FormField[] = [
  { name: "name", type: "text", label: "Nombre completo", required: true },
  
  // Nested contact
  { name: "contact.email", type: "text", label: "Email", required: true },
  { name: "contact.phone", type: "text", label: "Teléfono", required: true },
  
  // Nested address
  { name: "address.street", type: "text", label: "Calle", required: true },
  { name: "address.city", type: "text", label: "Ciudad", required: true },
  { name: "address.country", type: "text", label: "País", required: true },
];
```

## Best Practices

1. **Use consistent naming** - decide on a convention (e.g., always nested, never flat)
2. **Group related fields** in sections for better UX
3. **Match Zod paths exactly** - ensure schema paths match field names
4. **Keep nesting reasonable** - deeply nested structures (>3 levels) become hard to manage
5. **Consider flattening** - if data is mostly independent, flat structures may be cleaner

## Limitations

- Dot notation in field names creates a flat structure in react-hook-form's internal state
- Zod validation must map errors to these flat paths
- Complex nested arrays (dynamic length) require additional handling with `useFieldArray`
