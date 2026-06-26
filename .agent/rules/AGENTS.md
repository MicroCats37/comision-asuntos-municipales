# Claude Code — Agent Rules for generic

## 1. Knowledge Base is Mandatory

Before writing ANY code, check `.agent/lab/`:
- Read `.agent/lab/specs/nextjs/INDEX.md` for architecture contracts
- Read the relevant `IO.md` for component interfaces
- Read `SPEC.md` for REQUIRED/FORBIDDEN patterns

**FORBIDDEN**: Writing code that contradicts `.agent/lab/specs/` FORBIDDEN sections.

## 2. Skill Routing

Read `.agent/STACK.md` to know which skills to load for each task.
Do not guess — the stack is explicitly defined there.

## 3. SDD Workflow

For any substantial change (new component, new feature, refactor), use SDD:

- Skills path: `file:///C:/Users/Usuario/.config/opencode/skills/sdd-{phase}/SKILL.md`
- Persistence: engram (project: 'generic')
- Artifacts saved with topic_key: `sdd/{change-name}/{phase}`

SDD phases in order: `explore` → `propose` → `spec` + `design` → `tasks` → `apply` → `verify` → `archive`

## 4. Project Structure Rules

| What | Where |
|------|-------|
| Generic headless components | `next/src/components/generic{Name}/` |
| Feature-specific code | `next/src/features/{feature-name}/` |
| Shared utilities | `next/src/utils/` |
| Shared hooks | `next/src/hooks/` |
| Generic UI wrappers | `next/src/components/{name}/` |

**FORBIDDEN**: Putting feature-specific logic inside generic components.

## 5. When Starting a Session

1. Check engram context: `mem_context(project: 'generic')`
2. Read `.agent/STACK.md` to understand the stack
3. Read relevant `.agent/lab/specs/` before implementing
