# Patterns Layer

This directory contains **recipes** — concrete patterns showing *how we use* each technology in our stack. Unlike knowledge files (which describe *what* a technology is), patterns describe *how we integrate* it.

## Layer Purpose

**Answer**: "How do we use X in our stack?"

## Routing Table

| Technology | Patterns | Description |
|------------|----------|-------------|
| Next.js 16 | [nextjs-16/](./nextjs-16/) | Server Actions, Streaming, PPR, Security boundaries |
| **Next.js Backend** | [nextjs-backend/](./nextjs-backend/) | withAuth, baseRepository, domainError, proxyMiddleware |
| React 19 | [react-19/](./react-19/) | Action hooks, Optimistic UI, use() hook |
| Zod | [zod/](./zod/) | Schema inference, forms integration |
| TanStack Query v5 | [tanstack-query-v5/](./tanstack-query-v5/) | Core patterns, mutations, suspense |
| Axios | [axios/](./axios/) | Instance config, interceptors, error handling |
| Django Ninja | [django-ninja/](./django-ninja/) | Service DI, Schema validation, TestClient |

## Pattern Structure

Each pattern file follows this template:

```markdown
# {Tech}: {Recipe Title}

## Context
{One sentence: what problem this solves in our stack}

## Recipe
{Code block showing our specific usage pattern}

## Why This Way
{1-2 sentences linking to the architectural decision}

## See Also
- [Knowledge: {topic}](../../knowledge/{tech}/{topic}.md)
- [Spec: {spec}](../../specs/{framework}/{spec}/SPEC.md)
```

## Adding Patterns

1. Create `{tech}/{recipe-name}.md` using the template above
2. Update `{tech}/INDEX.md` with the new pattern
3. Update this master INDEX.md if adding a new technology
4. Keep each pattern under ~40 lines
5. Include concrete code from our actual codebase

## Boundaries

- **DO**: Document our specific integration patterns, our code conventions, our naming
- **DON'T**: Write generic tutorials, explain what a technology is (that's knowledge layer)
- **DON'T**: Write contract-level rules (that's specs layer)

## See Also

- [Knowledge Layer](../knowledge/) — WHAT each technology is
- [Specs Layer](../specs/) — WHAT we decided to build (contracts)
- [Projects Layer](../projects/) — Project-specific overrides
