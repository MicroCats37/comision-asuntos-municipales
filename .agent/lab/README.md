# The .lab: Enterprise AI Knowledge & Specs

This directory is the **Universal Shell (Cascaron)** and **Source of Truth** for our technical architecture. It travels with all our projects to provide an AI-optimized, modular knowledge system.

> 📖 **New here?** Start by reading the full [DOCS.md](./DOCS.md) to understand the architecture and how AI agents navigate this folder.

## 🏛 The 4-Layer Architecture

Our documentation is strictly separated by semantic purpose to save AI tokens and prevent hallucinations:

1. **`knowledge/`** (WHAT it is): Pure technical facts about libraries. No decisions, no opinions.
2. **`patterns/`** (HOW we use it): Recipes and standard ways to use technologies in our stack.
3. **`specs/`** (WHAT WE DECIDED): Architectural contracts, rules (`REQUIRED`/`FORBIDDEN`), and interfaces (`IO.md`).
4. **`projects/`** (OVERRIDES): Project-specific rules when a new app is born from this shell.

## 🚦 Quick Navigation

- [📖 Full Architecture Documentation](./DOCS.md)
- [⚖️ Contribution & Governance Rules](./CONTRIBUTING.md)
- [📚 Knowledge Master Index](./knowledge/INDEX.md)
- [🧩 Patterns Master Index](./patterns/INDEX.md)
- [🏗️ Specs Master Index](./specs/INDEX.md)

## ✍ Governance TL;DR

- **Strict Boundaries:** Never mix facts (knowledge) with recipes (patterns) or rules (specs).
- **Semantic Naming:** Files use descriptive names, no numeric prefixes (`01-`, `02-`).
- **Token Efficiency:** Keep files small. AI agents read `IO.md` first to understand a component, not the whole spec.

Read [CONTRIBUTING.md](./CONTRIBUTING.md) before adding or modifying files in `.lab/`.
