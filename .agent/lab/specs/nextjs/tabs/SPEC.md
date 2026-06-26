# Tabs Spec

## Metadata
- Version: 1.0
- Stack: Next.js 16 + React 19 + TypeScript
- Scope: GenericTabs component usage, tab content patterns

---

## Core Principle

> **GenericTabs wraps Shadcn Tabs with a consistent API. Tab content is always a ReactNode passed in the tab definition.**

`GenericTabs` provides two modes:
1. **Local state** — tab selection lives in component state
2. **URL-synced** — tab selection persists in URL query param for shareability

---

## Rule

Use `GenericTabs` for all tabbed content areas.

---

## ✅ REQUIRED

| Pattern | Description |
|---------|-------------|
| Pass `content` as `ReactNode` in tab definition | Content is rendered directly |
| Use `syncUrl=true` for shareable tab state | Persists selected tab to URL |
| Wrap in `Suspense` when `syncUrl=true` | Required for Next.js App Router compatibility |

---

## ❌ FORBIDDEN

| Pattern | Why |
|---------|-----|
| Data fetching inside tab content `ReactNode` directly | Causes waterfall requests, move data to parent |
| Using Shadcn Tabs primitives without `GenericTabs` wrapper | Loses consistent API and conventions |

---

## URL Sync Pattern

```tsx
"use client";

import { Suspense } from "react";
import { GenericTabs } from "@/components/ui/generic-tabs";

export function ProductTabs() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <GenericTabs
        tabs={[
          { value: "info", label: "Información", content: <InfoTab /> },
          { value: "history", label: "Historial", content: <HistoryTab /> },
        ]}
        syncUrl
        paramName="seccion"
      />
    </Suspense>
  );
}
```

---

## Source References

→ [`references/SOURCES.md`](./references/SOURCES.md)
