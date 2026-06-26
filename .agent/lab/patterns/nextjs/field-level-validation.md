# Field-Level Validation with superRefine

This pattern explains how to implement field-level validation using Zod's `superRefine` method and path mappings for nested form errors.

## Overview

When using `GenericForm` with Zod schemas, `superRefine` allows you to add custom validation logic that can report errors to specific field paths. This is essential for displaying validation errors at the correct field location in nested forms.

## superRefine Basics

`superRefine` is a Zod method that gives you access to the parsing context to add custom issues:

```typescript
import { z } from "zod";

const mySchema = z.object({
  fecha_nacimiento: z.date(),
  edad: z.number(),
}).refine(
  (data) => {
    // Custom validation logic
    const birthDate = data.fecha_nacimiento;
    const today = new Date();
    const age = today.getFullYear() - birthDate.getFullYear();
    return age >= 18;
  },
  {
    message: "Debes ser mayor de 18 años",
    path: ["fecha_nacimiento"], // Maps error to this field
  }
);
```

## Using superRefine for Complex Validation

For more complex validation that needs access to multiple fields:

```typescript
const formSchema = z.object({
  fecha_inicio: z.date(),
  fecha_fin: z.date(),
}).superRefine((data, ctx) => {
  if (data.fecha_fin <= data.fecha_inicio) {
    ctx.addIssue({
      code: "custom",
      message: "La fecha de fin debe ser posterior a la fecha de inicio",
      path: ["fecha_fin"],
    });
  }
});
```

## Path Mappings

The `path` array in `addIssue` determines which field receives the error:

| Path Format | Maps To | Example Usage |
|-------------|---------|---------------|
| `["field_name"]` | Top-level field | Single field validation |
| `["parent", "child"]` | Nested object | Object hierarchies |
| `["parent", "0"]` | Array index | List items |

### Example: Array Item Validation

```typescript
const taskSchema = z.object({
  tasks: z.array(z.object({
    title: z.string().min(1, "El título es requerido"),
    completed: z.boolean(),
  })),
}).superRefine((data, ctx) => {
  data.tasks.forEach((task, index) => {
    if (!task.completed && !task.title) {
      ctx.addIssue({
        code: "custom",
        message: "Tarea incompleta requiere título",
        path: ["tasks", index, "title"],
      });
    }
  });
});
```

## Integration with GenericForm

When using `GenericForm` with nested fields using dot notation (e.g., `name="tasks.0.title"`), ensure your Zod path matches:

```typescript
// In your form field config
{
  name: "tasks.0.title",
  type: "text",
  label: "Task Title",
}

// In your Zod schema - the path must match
ctx.addIssue({
  code: "custom",
  message: "Required",
  path: ["tasks", "0", "title"], // Array index as string
});
```

## Error Display

The `GenericInput` component uses `getNestedError` to traverse nested error objects using dot notation paths. This utility function handles:

- Simple paths: `"email"` → `errors.email`
- Nested paths: `"address.city"` → `errors.address.city`
- Array paths: `"items.0.name"` → `errors.items[0].name`

## Best Practices

1. **Always specify the path** when adding issues to ensure errors appear at the correct field
2. **Use string indices** for array paths when using dot notation in field names
3. **Leverage `superRefine`** when validation depends on multiple fields
4. **Keep error messages user-friendly** - they display directly in the form
