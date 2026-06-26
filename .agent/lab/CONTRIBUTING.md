# Contributing to .lab/

This document defines governance rules for all 4 layers in the `.lab/` documentation architecture.

---

## Layer Rules

Each layer has a distinct purpose and boundary:

| Layer | Purpose | Answer | Content Rules |
|-------|---------|--------|---------------|
| **knowledge/** | WHAT a technology IS | "What does X do?" | Pure facts, no "we", no decisions |
| **patterns/** | HOW we use a technology | "How do we use X?" | Recipes with our context, code snippets |
| **specs/** | WHAT we decided to build | "What are the rules for Y?" | Contracts with REQUIRED/FORBIDDEN |
| **projects/** | Domain Context & Overrides | "What is the business context?" | `DOMAIN.md`, `API-INVENTORY.md`, Overrides |

### Boundary Enforcement

- **knowledge/**: No "In our Stack" sections, no "we" pronouns, no decisions
- **patterns/**: No contracts/rules — only descriptive recipes
- **specs/**: No tutorials — only enforceable contracts
- **projects/**: Must reference the base convention being overridden

---

## Adding Knowledge

### Template

```markdown
# {Technology}: {Topic}

## Overview
{2-3 sentences: what this technology does}

## Key Concepts
- {Concept 1}: {brief explanation}
- {Concept 2}: {brief explanation}

## When to Use
{One sentence: when this topic is relevant}

## See Also
- [Pattern: {name}](../../patterns/{tech}/{pattern}.md)
- [Spec: {name}](../../specs/{framework}/{spec}/SPEC.md)
```

### Checklist

- [ ] Does NOT contain "In our Stack" — that content goes to patterns/
- [ ] No "we", "our", or decisions — pure factual description
- [ ] Under ~40 lines
- [ ] INDEX.md updated with new file link
- [ ] All links use relative paths
- [ ] Title matches filename exactly (semantic naming)

---

## Adding Patterns

### Template

```markdown
# {Tech}: {Recipe Title}

## Context
{One sentence: what problem this solves in our stack}

## Recipe
```{language}
{code block showing our specific usage}
```

## Why This Way
{1-2 sentences linking to architectural decisions}

## See Also
- [Knowledge: {topic}](../../knowledge/{tech}/{topic}.md)
- [Spec: {spec}](../../specs/{framework}/{spec}/SPEC.md)
```

### Checklist

- [ ] Contains concrete code from our actual codebase
- [ ] Context explains WHY this pattern was chosen, not just what it does
- [ ] No duplicate content with specs/ contracts
- [ ] INDEX.md updated with new pattern link
- [ ] All links use relative paths
- [ ] Under ~40 lines

---

## Adding/Updating Specs

### File Structure

Each spec directory must contain:

| File | Purpose | Required |
|------|---------|----------|
| `SPEC.md` | Rules and contracts | Yes |
| `IO.md` | Input/output interfaces | Yes (if interfaces exist) |
| `EXAMPLES.md` | Worked examples | Yes (if examples help) |

### SPEC.md Template

```markdown
# {Spec Name}

## Rule
{One-sentence rule statement}

## Context
{Background: why this rule exists}

## REQUIRED
```{language}
{correct implementation}
```

## FORBIDDEN
```{language}
{incorrect implementation + why}
```

## See Also
- [Shared Contract: {name}](../../specs/shared/{contract}.md)
- [Pattern: {name}](../../patterns/{tech}/{pattern}.md)
```

### Checklist

- [ ] Has REQUIRED and FORBIDDEN sections
- [ ] Links to relevant shared contracts in `specs/shared/`
- [ ] IO.md created if spec defines interfaces (see IO.md template)
- [ ] EXAMPLES.md created if examples aid understanding
- [ ] INDEX.md updated
- [ ] All links use relative paths
- [ ] No duplicate rules with existing specs

---

## Naming Conventions

| Layer | Pattern | Example |
|-------|---------|---------|
| Knowledge | `{topic}.md` | `action-hooks.md` |
| Knowledge | `{tech}/{topic}.md` | `react-19/action-hooks.md` |
| Patterns | `{tech}-{recipe}.md` | `zod-inference-usage.md` |
| Patterns | `{tech}/{recipe}.md` | `react-19/action-hooks-usage.md` |
| Specs | `SPEC.md` | `forms/SPEC.md` |
| Specs | `IO.md` | `forms/IO.md` |
| Specs | `EXAMPLES.md` | `forms/EXAMPLES.md` |
| Shared Contracts | `{contract-name}.md` | `error-handling.md` |

### Rules

- **Knowledge files**: Semantic names, lowercase, hyphenated, NO numbered prefixes
- **Pattern files**: Descriptive recipe names, may include tech prefix
- **Spec files**: Fixed names (`SPEC.md`, `IO.md`, `EXAMPLES.md`) per directory
- **Shared contracts**: Single lowercase words or hyphenated compound names

---

## Review Checklist

Before submitting any PR to `.lab/`:

- [ ] **Correct layer?** (fact vs recipe vs contract vs project-specific)
- [ ] **INDEX.md updated?** (every new file needs an index entry)
- [ ] **Links use relative paths?** (no absolute paths)
- [ ] **Under ~40 lines per knowledge/pattern doc?**
- [ ] **Code examples included?** (for patterns and specs)
- [ ] **FORBIDDEN/REQUIRED sections in specs?**
- [ ] **No "In our Stack" in knowledge/?**
- [ ] **No decisions/facts confusion?**
- [ ] **No duplicate content across layers?**
- [ ] **File naming matches convention?**

---

## Shared Contracts (specs/shared/)

Cross-cutting contracts that apply to ALL specs:

| Contract | Scope | Source |
|----------|-------|--------|
| `error-handling.md` | Error parsing, toast adapter pattern | forms SPEC.md |
| `api-format.md` | Request/response shape, payload builders | forms SPEC.md |
| `types.md` | Schema naming conventions | forms + zod knowledge |
| `env-conventions.md` | Env variable naming, test flags | forms SPEC.md |

When updating a shared contract, verify it doesn't break existing spec references.

---

## Architecture Diagram

```
.lab/
├── knowledge/          ← WHAT (facts, no decisions)
├── patterns/           ← HOW (recipes, our context)
├── specs/              ← WHAT WE DECIDED (contracts)
│   └── shared/         ← Cross-cutting contracts
└── projects/           ← Project-specific overrides
```

For full architecture documentation, see [DOCS.md](./DOCS.md).
