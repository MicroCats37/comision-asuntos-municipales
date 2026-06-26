# Empty State Spec

## Metadata
- Version: 1.0
- Stack: Next.js 16 + React 19 + TypeScript
- Scope: EmptyState component for tables, lists, and cards

---

## Core Principle

> **Use `EmptyState` for ALL empty data states in tables, lists, and cards.**

Empty state is a visual communication pattern. It tells users there is no data, why there might be no data, and what they can do about it. Keep it simple — the component does not fetch data or contain business logic.

---

## Rules

### ✅ REQUIRED

- `icon` + `title` are the minimum required content
- `action` slot is provided for a CTA button or link
- Component is a simple presentational wrapper — no internal data fetching
- Visual treatment: centered, with muted text for description

### ❌ FORBIDDEN

- Internal data fetching or loading states
- Complex logic inside the component
- State management or callbacks beyond simple prop passing

---

## Anatomy

```
┌─────────────────────────────────────┐
│                                     │
│              [icon]                 │
│                                     │
│            [title]                  │
│                                     │
│         [description]               │
│                                     │
│           [action]                  │
│                                     │
└─────────────────────────────────────┘
```

- **icon**: Optional visual indicator (illustrations, icons from lucide-react)
- **title**: Required — what the user is seeing
- **description**: Optional — why it's empty or what to do next
- **action**: Optional — CTA button or link

---

## Source References

→ [`references/SOURCES.md`](./references/SOURCES.md)