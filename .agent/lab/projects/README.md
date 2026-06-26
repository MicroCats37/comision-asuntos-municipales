# Projects Layer

This directory acts as the **Domain Context Concentrator**. It provides the AI with the specific business vocabulary, rules, and API landscape of a project, preventing architecture improvisation.

## File Hierarchy

```
projects/
├── {project-name}/           # One directory per project
│   ├── README.md            # Project overview & tech overrides
│   ├── DOMAIN.md            # Entities, Relationships & Rules (The "WHAT")
│   ├── API-INVENTORY.md     # Backend endpoints & schemas (The "WHERE")
│   ├── patterns/            # Project-specific usage recipes
│   └── specs/               # Project-specific architectural rules
└── _example/                # TEMPLATE PROJECT (Copy-paste from here)
```

## Layer Purpose

1.  **Context**: "What is this project about? (Club management, E-commerce, etc.)"
2.  **Vocabulary**: "How are things named? (Socio vs Miembro)"
3.  **Inventory**: "What backend endpoints already exist?"
4.  **Deviations**: "How does this project differ from our standard Lab specs?"

## Creating a New Project

To start a new project:
1.  Copy the `_example/` directory.
2.  Rename it to your `{project-name}`.
3.  Fill in the `DOMAIN.md` and `API-INVENTORY.md` templates.

> [!TIP]
> Always fill `DOMAIN.md` first. It provides the source of truth for all data types used in the frontend and backend.
