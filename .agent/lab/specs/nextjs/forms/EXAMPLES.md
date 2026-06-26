# Forms: Worked Examples

## Example 1: Mode 1 — Manual Production Form

Complete login form with all render props:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { GenericForm } from "@/components/genericForm/GenericForm";
import { LoginFormSchema, type LoginFormData } from "@/features/auth/schemas";
import { useLogin } from "@/features/auth/hooks";

export function LoginForm() {
  const router = useRouter();
  const { mutate: login, isPending } = useLogin();

  return (
    <GenericForm
      schema={LoginFormSchema}
      onSubmit={(data: LoginFormData) => {
        login(data, {
          onSuccess: () => router.push("/dashboard"),
        });
      }}
      isLoading={isPending}
    >
      {({ methods, isSubmitting, onSubmit }) => (
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label htmlFor="email">Email</label>
            <Input
              id="email"
              {...methods.register("email")}
              type="email"
              placeholder="you@example.com"
            />
            {methods.formState.errors.email && (
              <p className="text-red-500">
                {methods.formState.errors.email.message}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="password">Password</label>
            <Input
              id="password"
              {...methods.register("password")}
              type="password"
            />
            {methods.formState.errors.password && (
              <p className="text-red-500">
                {methods.formState.errors.password.message}
              </p>
            )}
          </div>

          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Sign In"}
          </Button>
        </form>
      )}
    </GenericForm>
  );
}
```

## Example 2: Mode 2 — Automatic (Internal Tool)

Quick prototyping form with automatic field rendering:

```tsx
import { GenericForm } from "@/components/genericForm/GenericForm";
import { CreateUserFormSchema, type CreateUserData } from "./schemas";

const fields = [
  { name: "name", label: "Full Name", type: "text", required: true },
  { name: "email", label: "Email", type: "email", required: true },
  { name: "role", label: "Role", type: "select", options: [
    { label: "Admin", value: "admin" },
    { label: "User", value: "user" },
  ]},
];

export function CreateUserForm() {
  return (
    <GenericForm
      schema={CreateUserFormSchema}
      fields={fields}
      onSubmit={async (data: CreateUserData) => {
        await createUser(data);
      }}
    />
  );
}
```

**❌ FORBIDDEN in production screens** — use Mode 1 instead.

## Example 3: Mode 4 — Hybrid (Multi-Step Wizard)

Sharing form state across multiple components:

```tsx
"use client";

import { GenericForm } from "@/components/genericForm/GenericForm";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { WizardStep1, WizardStep2, WizardReview } from "./wizard";
import { FullProductFormSchema, type FullProductData } from "./schemas";

export function ProductWizard() {
  const methods = useForm<FullProductData>({
    resolver: zodResolver(FullProductFormSchema),
    defaultValues: { name: "", price: 0, description: "" },
  });

  return (
    <GenericForm
      schema={FullProductFormSchema}
      formMethods={methods}
      onSubmit={async (data) => {
        await createProduct(data);
      }}
    >
      {({ isSubmitting }) => (
        <div>
          <WizardStep1 />   {/* Reads from shared methods */}
          <WizardStep2 />   {/* Reads from shared methods */}
          <WizardReview />
          <Button type="submit" disabled={isSubmitting}>
            Create Product
          </Button>
        </div>
      )}
    </GenericForm>
  );
}
```

## Example 4: Edit Form with Async Data

Loading existing data into the form:

```tsx
"use client";

import { GenericForm } from "@/components/genericForm/GenericForm";
import { UpdateProductFormSchema, type UpdateProductData } from "./schemas";
import { useProduct } from "@/features/products/hooks";

export function EditProductForm({ productId }: { productId: string }) {
  const { data: product, isLoading } = useProduct(productId);

  return (
    <GenericForm
      schema={UpdateProductFormSchema}
      initialData={product}
      isLoading={isLoading}
      onSubmit={async (data: UpdateProductData) => {
        await updateProduct({ id: productId, ...data });
      }}
    >
      {/* Form fields */}
    </GenericForm>
  );
}
```

## Example 5: With File Upload

Using `buildApiPayload` via the mutation hook:

```tsx
// In the hook (not the component):
export function useCreateProduct() {
  return useApiCreate<CreateProductData, FormData>(
    (data) => buildApiPayload(data)  // Lives in hook, not component
  );
}

// In the component:
<GenericForm
  schema={CreateProductFormSchema}
  onSubmit={(data) => createProduct(data)}
>
  {/* File input fields */}
</GenericForm>
```

## See Also
- [Spec: Forms](./SPEC.md) — full spec
- [Shared: API Format](../shared/api-format.md) — payload builder contract
