---
name: lab-context
description: >
  Bridge module that provides a standardized protocol for reading the two-layer documentation system:
  the generic architectural core (.lab) and the specific project business rules (.lab-project).
  Loaded by SDD phases and orchestrator agents.
license: MIT
metadata:
  version: "1.0"
---

# `lab-context` — The Master Architectural Core Reader

This is a shared skill loaded by SDD phases and planners. It dictates EXACTLY how you must interact with the documentation layers before writing proposals, specs, designs, or code.

## The Two-Layer Architecture

You operate in an environment with two parallel documentation systems:

1. **The Generic Core (`c:\Users\Usuario\Desktop\generic\.lab\`)**
   - **What it is:** The immutable architectural truth for this stack. Contains knowledge about libraries, design patterns, and "how" we build things (e.g., "How to build forms in Next.js").
   - **When to read:** During `sdd-design`, `sdd-apply`, or before writing architecture/boilerplate.
   - **Rule:** This layer overrides your generic AI knowledge. If a `.agent/lab/specs/` document exists for your task, its `✅ REQUIRED` and `❌ FORBIDDEN` patterns are absolute law.

2. **The Project Specifics (`{project}/.lab-project/`)**
   - **What it is:** The business rules, domain models, and constraints for the *specific app* you are working on (e.g., `next/.lab-project/domain/`).
   - **When to read:** During `sdd-propose`, `sdd-spec`, or any feature planning.
   - **Rule:** This layer overrides the Generic Core if a conflict arises regarding business logic.

---

## 🛑 MANDATORY READING PROTOCOL

Before you proceed with your primary task, you MUST perform the context retrieval associated with your current phase:

### If you are ideating or specifying (e.g., `sdd-propose`, `sdd-spec`, planning workflows):
1. Determine the domain of the change (e.g., "users", "payments").
2. Check if a domain file exists in `{project}/.lab-project/domain/{domain}.md` or check `INDEX.md`.
3. If it exists, **READ IT**. Your proposal or specs MUST NOT contradict established business rules.

### If you are designing technical architecture (e.g., `sdd-design`):
1. Determine the technical patterns involved (e.g., "forms", "auth", "data-fetching").
2. Read the generic spec index: `c:\Users\Usuario\Desktop\generic\.lab\specs\nextjs\INDEX.md` (or the relevant framework).
3. If a relevant spec exists (e.g., `forms/SPEC.md`), **READ IT**.
4. Your technical design MUST explicitly inherit and cite the patterns recommended in the spec.

### If you are implementing code (e.g., `sdd-apply`, `enhance`):
1. If the design document says to follow a specific `.agent/lab/specs/` pattern, YOU MUST DO SO.
2. If you need reference code, read `c:\Users\Usuario\Desktop\generic\.lab\specs\{framework}\{feature}\references\SOURCES.md` to find the canonical internal file paths, completely decoupled from libraries like Shadcn.

---

## ⚠️ Prime Directives

- **DO NOT** modify the `.agent/lab/` generic files during daily tasks. It is for read-only boilerplate. Any evolution of generic patterns is handled by the architect later.
- **DO NOT** invent new architectural patterns (like complex form wrappers or state management) if a `.agent/lab/` spec already defines how to do it.
- **USE ENGRAM** (`mem_save`) for saving daily discoveries, bugs, or specific implementation details. Do not dump them into the `.agent/lab/` directly.
