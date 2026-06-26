# .lab Documentation

> A modular, AI-optimized knowledge system for enterprise platform development.

---

## What is `.lab/`?

The `.lab/` directory is the **Source of Truth** for how we build software. It contains:

- **Technical facts** about the libraries we use (what they do, how to use them correctly).
- **Recipes** that show how we integrate those libraries in our specific stack.
- **Architectural contracts** that define how those libraries work together in our projects.
- **Project-specific overrides** for monorepo variations.

Think of it as a **private technical wiki** that travels with your codebase and is designed to be read by both humans and AI agents efficiently.

---

## Architecture Overview

The `.lab/` follows a **4-layer architecture**:

```
.lab/
├── README.md              ← Entry point
├── DOCS.md                ← This file: architecture overview
├── CONTRIBUTING.md        ← Governance rules
│
├── knowledge/             ← LAYER 1: Pure Technical Facts
│   ├── INDEX.md           ← Master routing table
│   └── {tech}/            ← 7 tech folders (react-19, nextjs-16, zod, etc.)
│       ├── INDEX.md        ← Per-tech routing
│       └── *.md           ← Semantic filenames (no numbered prefixes)
│
├── patterns/              ← LAYER 2: HOW WE USE technologies
│   ├── INDEX.md           ← Master routing table
│   └── {tech}/            ← Recipes extracted from "In our Stack" sections
│       ├── INDEX.md        ← Per-tech routing
│       └── *.md           ← Usage patterns specific to our stack
│
├── specs/                 ← LAYER 3: Architectural Contracts
│   ├── INDEX.md           ← Master routing (shared + framework links)
│   ├── shared/            ← Cross-cutting contracts
│   │   ├── error-handling.md
│   │   ├── api-format.md
│   │   ├── types.md
│   │   └── env-conventions.md
│   └── nextjs/            ← Framework-specific specs
│       ├── INDEX.md        ← Framework routing
│       ├── forms/
│       │   ├── SPEC.md     ← Rules (REQUIRED/FORBIDDEN)
│       │   ├── IO.md       ← Props, data contracts
│       │   └── EXAMPLES.md ← Runnable code examples
│       ├── modals/
│       └── project-structure/
│
└── projects/              ← LAYER 4: Domain Context & Overrides
    ├── README.md          ← Project overview
    ├── DOMAIN.md          ← Entities & Rules (Pre-requisite for Code)
    ├── API-INVENTORY.md   ← Backend endpoint mapping
    └── _example/          ← Master project template
```

### Layer 1: `knowledge/` — WHAT a technology IS

Pure, framework-agnostic facts. These documents answer:
- "What does `useActionState` do?"
- "How does Zod inference work?"
- "What changed between TanStack Query v4 and v5?"

**Rules:**
- Content is factual. No "we", no "our", no decisions.
- No numbered prefixes (`01-`, `02-`) — use semantic names.
- Max ~40 lines per document.

### Layer 2: `patterns/` — HOW WE USE a technology

Recipes with "our" context. These documents answer:
- "How do we set up Zod inference in our forms?"
- "How do we configure the Axios interceptors for our auth?"

**Rules:**
- Contains code snippets showing our specific integration.
- Links back to knowledge for the "what" and specs for the "rules".

### Layer 3: `specs/` — WHAT WE DECIDED to build

Opinionated architectural contracts. These documents answer:
- "How do we build forms in Next.js?" → `specs/nextjs/forms/SPEC.md`
- "What is our error handling strategy?" → `specs/shared/error-handling.md`

**Rules:**
- Each spec has exactly **3 files**: `SPEC.md`, `IO.md`, `EXAMPLES.md`
- MUST include `❌ FORBIDDEN` and `✅ REQUIRED` sections.
- Shared contracts in `specs/shared/` apply across all frameworks.

### Layer 4: `projects/` — Domain Context & Overrides

This is the **Context Concentrator**. It provides the business vocabulary and API landscape required to build functional features.

**Mandatory Files:**
- `DOMAIN.md`: Defines the "What" (Entities, rules, constraints).
- `API-INVENTORY.md`: Defines the "Where" (Available endpoints).
- `README.md`: Overall project context and tech overrides.

**Rules:**
- Use the `_example/` directory as a template for new projects.
- Must be read BEFORE starting any feature implementation in a specific domain.

---

## Agent Routing Flow

```
Agent receives task
        ↓
    Read DOCS.md or project README
        ↓
    specs/{framework}/INDEX.md
        ↓
┌─── SPEC.md (rules)
│        ↓
├── IO.md (contracts) ──→ EXAMPLES.md (worked examples)
│
└── If needs tech detail → knowledge/{tech}/INDEX.md
└── If needs recipe → patterns/{tech}/INDEX.md
└── If needs cross-cutting → specs/shared/{contract}.md
```

Steps: (1) Agent reads specs INDEX for the task domain. (2) Loads SPEC.md for rules. (3) Loads IO.md only if building interfaces. (4) Loads EXAMPLES.md only if needs concrete patterns. (5) Dives into knowledge/ or patterns/ only for deep understanding.

### Anti-Hallucination Strategy

Most AI models are trained on older patterns. Our specs explicitly mark what is outdated:

```markdown
## ❌ FORBIDDEN (React 18 / Next.js 14)
- useState + useEffect for form state
- forwardRef

## ✅ REQUIRED (React 19 / Next.js 16)
- useActionState for form lifecycle
- ref as prop (no forwardRef)
```

This forces the AI to generate modern code even when its training data pulls toward older patterns.

---

## How to Extend This

### Adding a New Technology to `knowledge/`

1. Create the folder:
```
knowledge/
└── new-tech-v2/
    ├── INDEX.md
    ├── core-concept.md
    ├── advanced-pattern.md
    └── breaking-changes.md
```

2. Write the `INDEX.md` following the routing table pattern.

3. Update `knowledge/INDEX.md` to include the new entry.

4. Write each document:
   - **Max ~40 lines** per document.
   - **Code examples** are mandatory.
   - **No opinions** — just facts.

### Adding a New Pattern to `patterns/`

1. Extract from knowledge or write fresh:
```
patterns/
└── new-tech-v2/
    ├── INDEX.md
    └── our-usage-recipe.md
```

2. Pattern documents answer "How do we use X?" with our specific context.

### Adding a New Spec to `specs/`

1. Create the 3-file structure:
```
specs/nextjs/
└── new-feature/
    ├── SPEC.md    ← Rules + decisions
    ├── IO.md      ← Props + contracts
    └── EXAMPLES.md ← Worked code examples
```

2. Write `SPEC.md` following the template:
```markdown
# {Feature} Spec

## Metadata
- Version: 1.0
- Stack: Next.js 16 + React 19
- Depends on: [Knowledge: {topic}](../../knowledge/{tech}/{topic}.md)

## ✅ REQUIRED Pattern
[Code example]

## ❌ FORBIDDEN Pattern
[Code example + why]

## Decision Log
| Decision | Rationale |
|----------|-----------|
| Use X over Y | Because Z |
```

3. Update `specs/nextjs/INDEX.md` with the new entry.

### Adding a Cross-Cutting Contract

```
specs/shared/
└── new-contract.md
```

Cross-cutting contracts apply to ALL specs regardless of framework.

---

## Governance Rules

| Rule | Description |
|------|-------------|
| **English Only** | All documents must be written in English |
| **Relative Paths** | All internal links use relative paths (`./`, `../`) |
| **Max ~40 Lines** | Knowledge documents stay token-efficient |
| **Semantic Names** | No numbered prefixes in any layer |
| **INDEX Required** | Every folder MUST have an `INDEX.md` routing table |
| **Forbidden/Required** | Every SPEC.md MUST explicitly show what's banned vs required |
| **3-File Specs** | Each spec has SPEC.md + IO.md + EXAMPLES.md |
| **No Duplicates** | Facts → knowledge/, Recipes → patterns/, Contracts → specs/ |

---

## FAQ

### Can I use this without AI agents?
Yes. The `.lab/` is perfectly readable by humans as a structured wiki. The routing tables (`INDEX.md`) serve as a table of contents.

### What if I need project-specific knowledge?
Use `.lab/projects/` for monorepo variations. For project-local knowledge, use `.agent/knowledge/` inside your specific project.

### What's the difference between `.lab/` and `.agent/skills/`?
| `.lab/` | `.agent/skills/` |
|---------|------------------|
| Knowledge, patterns, and architecture contracts | Executable instructions for AI |
| "What is true", "how we use it", "what we decided" | "What to do step by step" |
| Read by humans AND AI | Read primarily by AI |
| Changes rarely | Changes with workflow needs |

### Why 4 layers instead of 2?
The original 2-layer (knowledge + specs) conflated "how we use a technology" (a recipe) with "what a technology is" (a fact). The patterns layer extracts recipes, making knowledge purely factual and specs purely about rules.
