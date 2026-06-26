# Breadcrumbs Spec

## Metadata
- Version: 1.0
- Stack: Next.js 16 + React 19 + TypeScript
- Scope: Breadcrumbs component usage, navigation hierarchy patterns

---

## Core Principle

> **Breadcrumbs provide orientation within page-level navigation hierarchies. Always pass items manually to maintain explicit control.**

`Breadcrumbs` renders a semantic `<nav>` with proper ARIA attributes. Each segment is either a link (has `href`) or the current page (no `href`).

---

## Rule

Use `Breadcrumbs` for all page-level navigation hierarchies.

Examples of appropriate use:
- E-commerce: Inicio → Productos → Categoría → Detalle
- Admin: Dashboard → Usuarios → Editar Usuario
- Settings: Configuración → Cuenta → Preferencias

---

## ✅ REQUIRED

| Pattern | Description |
|---------|-------------|
| Always pass `items` array manually | Explicit control over each segment |
| Last item = current page | Omit `href` on the final segment |
| Include `icon` in segments when needed | Use Lucide icons for visual cues |

---

## ❌ FORBIDDEN

| Pattern | Why |
|---------|-----|
| Auto-generating from `usePathname` | Loses semantic meaning, creates fragile coupling to route structure |
| Hardcoding route segments | No flexibility for localized or dynamic labels |
| Using plain HTML `<nav>` without `BreadcrumbSegment` interface | Missing ARIA, accessibility issues |

---

## Source References

→ [`references/SOURCES.md`](./references/SOURCES.md)
