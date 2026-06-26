# Idea: Automating Knowledge Updates with Context7

## Context
As the `.lab/` grows and new versions of frameworks are released (e.g., React 19 -> React 20, Next.js 16 -> 17), manually updating the `knowledge/` and `patterns/` layers will become tedious and error-prone. We want to ensure our universal shell remains the most easily updatable project.

## Proposed Solution
Create an automation script (or an AI agent routine) that uses **Context7** to fetch the latest documentation and breaking changes for a given technology and automatically generate or update the `.lab/` files.

## Workflow Example
When React 20 is released, we can run a command or agent task:

1. **Resolve ID**: Use the Context7 `resolve-library-id` tool to find the exact Context7 library ID for `react@20`.
2. **Query Docs**: Use `query-docs` to ask specific questions:
   - "What are the core breaking changes in React 20 compared to React 19?"
   - "Are there any new hooks or deprecated hooks?"
3. **Generate Knowledge**:
   - The agent reads the Context7 response and automatically drafts a `knowledge/react-20/breaking-changes.md` file.
   - It also drafts other factual documents (`knowledge/react-20/core-concepts.md`).
4. **Update Patterns**:
   - The agent cross-references our existing `patterns/react-19/` to see if our recipes need updating for React 20.
   - If breaking changes affect our forms or modals specs, the agent flags those `specs/` for human review or automatically proposes a PR.

## Why this matters
This will allow our "cascaron" (shell) to evolve organically and stay up-to-date with minimal human effort. The AI will do the heavy lifting of reading the new framework documentation and translating it into our strict `.lab/` 4-layer semantic format.

## Future Action Items
- [ ] Build a script or SDD skill (`sdd-update-tech`) that orchestrates the Context7 tool calls.
- [ ] Define a prompt template that strictly enforces the rules from `CONTRIBUTING.md` (no "we", max ~40 lines, semantic names) when generating the new markdown files.
