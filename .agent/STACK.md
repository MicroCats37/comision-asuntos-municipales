# Stack: generic (Universal Shell)

## Active Frameworks
- **Frontend**: Next.js 16 + React 19 + TypeScript + Tailwind v4 + Shadcn/ui
- **State**: Zustand v5 + TanStack Query v5
- **Validation**: Zod 4
- **HTTP**: Axios
- **Backend (optional)**: Django + Ninja Extra

## Agent Knowledge Base
All architectural knowledge lives in `.agent/lab/`. Always read before writing code.
- Master index: `.agent/lab/knowledge/INDEX.md`
- Specs index: `.agent/lab/specs/nextjs/INDEX.md`
- Patterns index: `.agent/lab/patterns/INDEX.md`

## Skills by Task

| Task | Skills to Load | .agent/lab/ paths to read |
|------|---------------|--------------------------|
| Next.js components | nextjs-react-expert, lab-context | `.agent/lab/specs/nextjs/INDEX.md` |
| Forms + validation | react-hook-form-zod, lab-context | `.agent/lab/specs/nextjs/forms/IO.md` |
| Data tables | lab-context | `.agent/lab/specs/nextjs/data-table/IO.md` |
| Modals / dialogs | lab-context | `.agent/lab/specs/nextjs/modals/IO.md` |
| State management | zustand-state-management | `.agent/lab/knowledge/zustand-v5/INDEX.md` |
| API calls / data fetching | tanstack-query, lab-context | `.agent/lab/specs/nextjs/hooks/IO.md` |
| Date formatting | lab-context | `.agent/lab/specs/nextjs/date-formatter/IO.md` |
| Django backend | django-ninja-extra, django-expert | — |
| SDD planning | (global) sdd-explore, sdd-propose, sdd-spec, sdd-design, sdd-tasks | — |
| SDD implementation | (global) sdd-apply, sdd-verify, sdd-archive | — |

## SDD Global Skills (Claude Code)

```
file:///C:/Users/Usuario/.config/opencode/skills/sdd-{phase}/SKILL.md
```

Replace `{phase}` with: `explore` · `propose` · `spec` · `design` · `tasks` · `apply` · `verify` · `archive` · `init`

## For Specific Projects

When this shell is used for a new project:
1. Add project specs → `.agent/lab/projects/{project-name}/`
2. Add project skill (optional) → `.agent/skills/{project-name}/SKILL.md`
3. Update this STACK.md with the project name and any new frameworks
