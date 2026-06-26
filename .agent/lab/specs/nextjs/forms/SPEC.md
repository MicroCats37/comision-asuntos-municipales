# Forms Spec

## Metadata
- Version: 1.0
- Stack: Next.js 16 + React 19 + TypeScript + React Hook Form v7 + Zod v4
- Scope: GenericForm rendering modes, payload strategy, schema conventions, error handling

---

## Core Principle

> **`GenericForm` owns validation and state. Features own layout and data transformation.**

`GenericForm` is a headless controller. Its job is React Hook Form setup, Zod validation, and submission lifecycle.
It does **not** own: visual layout, field components, or payload transformation.

---

## The 4 Rendering Modes

### Mode 1 — Manual (`children` render prop) ✅ REQUIRED for all production screens

The `children` prop receives `{ methods, isSubmitting, onSubmit, submissionMessage }`.
The feature builds the **entire HTML tree** — grids, Cards, Tabs — using native Shadcn components.

**When to use:** Every user-facing, production-quality screen.

### Mode 2 — Automatic (`fields` array)

Pass a flat `fields: FormField[]` config. `GenericForm` renders each input via the internal registry (`GhostWrapper`).

**When to use:** Prototyping, internal tools, dynamic forms where layout is irrelevant.
**❌ FORBIDDEN in production screens.**

### Mode 3 — Sections (`formSections` array)

Pass `formSections: FormSection[]`. Each section renders inside a `CardWrapper` by default, or any injected wrapper.

**When to use:** Quick admin dashboards, CMS tables, dynamic multi-section forms.
**❌ FORBIDDEN in production screens.**

### Mode 4 — Hybrid (`formMethods` prop)

Pass an external `UseFormReturn<T>` instance created by the feature. Used for multi-step wizards or when two components share the same form state.

**When to use:** Wizards, multi-step flows, forms split across several UI sections.

---

## Decision Matrix

| Scenario | Mode |
|---|---|
| Final production screen, user-facing | Mode 1 — Manual ✅ |
| Quick prototype / internal admin tool | Mode 2 or 3 |
| Multi-step wizard, shared form state | Mode 4 — Hybrid |
| Dynamic form schema from API | Mode 2 or 3 |

---

## Payload Strategy

> **`buildApiPayload` lives in the mutation hook (`useApiCreate` / `useApiUpdate`), never in the form component.**

`GenericForm.onSubmit` always receives **plain typed data** (`T`). The feature hook transforms it before hitting the API.

```
Feature Component → mutate(data: T) → useApiCreate → buildApiPayload(data) → API
```

- `buildApiPayload` auto-detects `File` objects and converts the payload to `FormData`.
- If there are no files, it returns data as-is (sent as JSON by Axios).
- **Source:** `src/utils/payload-builder.ts`
- **UUID generation** is controlled by `NEXT_PUBLIC_IS_TEST_UUID` in `.env.local` (forces manual fallback for HTTP environments).

---

## Schema Conventions

Two schemas per feature, one file:

| Export | Purpose | Located in |
|---|---|---|
| `CreateProductFormSchema` | Zod schema for form validation | `features/.../schemas/` |
| `CreateProductData` | `z.infer<typeof CreateProductFormSchema>` | same file |

Schema naming pattern: `{Action}{Resource}FormSchema` → `{Action}{Resource}Data`

---

## Async Data (Edit Forms)

Pass `initialData` from `useApiQuery` directly. GenericForm uses `values: initialData` in RHF's `useForm`, so when the query resolves, the form reinitializes automatically — no manual `useEffect` needed.

Pass `isLoading` to disable the fieldset while data is in-flight.

---

## Error Handling

On submission failure, `GenericForm` automatically:
1. Calls `handleApiError` from `src/errors/error-handler.ts`
2. Runs the parser chain (Django Ninja → DRF → Generic REST)
3. Applies `fieldErrors` to their corresponding form fields via RHF `setError`
4. Shows a `notify.error(message)` toast via the swappable adapter in `src/errors/toast-adapter.ts`

Feature components handle **zero** raw error logic.

---

## React Compiler Rule

> **Do NOT write `useMemo` or `useCallback` in forms.** React 19's compiler handles memoization automatically.

---

## ❌ Forbidden Patterns

| Pattern | Why |
|---|---|
| Automatic or Sections mode in production screens | Kills layout control |
| `buildApiPayload` called inside `onSubmit` of the component | Wrong layer, ruins TypeScript inference |
| `useMemo` / `useCallback` in form components | Redundant with React Compiler |
| Handling API errors manually in the component with `try/catch` | `GenericForm` already does this |

---

## Source References

→ [`references/SOURCES.md`](./references/SOURCES.md)
