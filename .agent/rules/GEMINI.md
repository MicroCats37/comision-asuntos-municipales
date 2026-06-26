---
trigger: always_on
---

# GEMINI.md - Lab-Centric Protocol (Project Layer)

> This file acts as a project-specific extension to the Global Antigravity Core Protocol.

---

## 🏗️ Master Architectural Core: THE LAB

> 🔴 **MANDATORY:** The `.agent/lab/` directory is the ONLY Source of Truth for architecture and domain logic.

**Two-Layer Reading Protocol:**

| Layer | Path | Purpose |
|-------|------|---------|
| **Generic Core** | `.agent/lab/specs/` | Contracts (REQUIRED/FORBIDDEN), patterns, and recipes. |
| **Project Context** | `.agent/lab/projects/` | Business rules, Domain (DOMAIN.md), and APIs (API-INVENTORY.md). |

**Priority Rule:**
1. `projects/` rules OVERRIDE generic `specs/` rules.
2. `specs/` rules OVERRIDE generic AI knowledge.

---

## 🐚 MANDATORY SHELL: POWERSHELL

**Rule:** For this project (Windows), you MUST use PowerShell native syntax for ALL `run_command` calls.
- ❌ **FORBIDDEN (Linux Chains)**: `&&`, `||`, `ls`, `grep`, `rm -rf`, `mkdir -p`.
- ✅ **MANDATORY (PowerShell Native)**: `;` (sequential chaining), `Get-ChildItem`, `Select-String`, `Remove-Item -Recurse -Force`, `New-Item -ItemType Directory`.

---

## 🧹 Clean Code & Standards

- **Code**: Follow the REQUIRED/FORBIDDEN patterns defined in `.agent/lab/specs/`. No ad-hoc solutions.
- **Logic**: All business logic must align with `DOMAIN.md`.
- **API**: All requests/responses must follow `API-INVENTORY.md` and `specs/shared/api-format.md`.

---

## 🧠 MEMORY PROTOCOL (ENGRAM)

**Rule:** You MUST use the Engram MCP server to persist and recall SDD progress.

### 1. SDD State Persistence
Call `mem_save` at the end of EVERY phase.
- **Topic Key**: `sdd/{change-name}/{phase}`
- **Project**: `generic`

### 2. Session Context Recovery
At the start of every session, run:
```javascript
mem_context(project: "generic")
```
To retrieve the last active SDD phase and historical decisions.

---

## 🚦 Phase Integrity

**Rule:** ONE SDD PHASE PER TURN.
When a phase is complete:
1. Save artifact to Engram.
2. Yield control.
3. Recommend the next model (Flash for text/Verify, Pro/Opus for Design/Apply).
