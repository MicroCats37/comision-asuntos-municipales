---
name: chartdb-diagram-layout
description: >
  How to create well-positioned, non-overlapping ChartDB diagrams with colored areas.
  Covers the parentAreaId update bug, pre-calculated layout formulas, and the delete-recreate workflow.
  Trigger: When creating or reorganizing ChartDB diagrams with MCP tools, especially when tables are overlapping or areas are corrupted.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Creating a new ChartDB diagram with multiple tables and colored areas
- Reorganizing an existing diagram where tables overlap or area assignments are broken
- Any time you need to position 5+ tables with proper spacing
- When `chartdb_update_table` parentAreaId corruption is detected

## Critical Bug (ALWAYS REMEMBER)

### The Bug
`chartdb_update_table` does NOT expose `parentAreaId` as a parameter. When you update table positions in bulk, area assignments get corrupted: tables lose their area (parentAreaId: null) or get assigned to the wrong area.

**This was discovered after 4 failed attempts to reorganize the club-cip diagram.**

### The Solution
**Never use iterative updates for layout changes.** Always:
1. Delete the diagram (or its contents)
2. Pre-calculate ALL positions
3. Recreate everything from scratch with correct positions

```text
❌ WRONG: create → update x,y → update parentAreaId (CORRUPTS)
✅ RIGHT: delete all → create all with pre-calculated positions
```

## Layout Calculation Formula

### Table Height
```
height = 60 + (field_count * 24)
```
Where 60px is the header (title + padding) and 24px per field row.

### Positioning Rules
- **Horizontal gap**: minimum 100px between table columns
- **Vertical gap**: minimum 100px between table rows (calculated as: tallest_table_in_row_height + 100)
- **Area margins**: 30px padding inside area bounds
- **Area sizing**: area_height = last_row_y + last_row_tallest_height + 30

### Grid Layout Strategy
For N tables in an area, distribute in rows of 3 (or fewer for the last row):

```
Row 1: tables at x = [30, 30+col_width+gap, 30+2*(col_width+gap)]
Row 2: y = row1_y + max(row1_heights) + 100
Row N: continue...
```

### Area Positioning (2×2 layout for 4 modules)
```
Row 1 areas: y=0, height based on content
Row 2 areas: y = row1_bottom + 30
```

## Complete Workflow

### Step 1: Gather Data
Get current diagram state or field definitions:
```
chartdb_get_diagram(id: "diagram-id")
```

### Step 2: Delete Existing Content
```
chartdb_delete_diagram(id: "diagram-id")
```

### Step 3: Create New Diagram
```
chartdb_create_diagram(id: "diagram-id", name: "Name", databaseType: "sqlite")
```

### Step 4: Create Areas (before tables)
```
chartdb_create_area(id: "area-xxx", diagramId: "diagram-id", name: "Area Name", 
  x: 0, y: 0, width: 820, height: CALCULATED, color: "#hex")
```

### Step 5: Create Tables with Absolute Positions
Tables use ABSOLUTE canvas positions (not relative to area). Position them so they fall WITHIN the area's visual bounds.

```
chartdb_create_table(id: "tbl-xxx", diagramId: "diagram-id", name: "table_name",
  x: ABSOLUTE_X, y: ABSOLUTE_Y, color: "#hex",
  fields: '[{...}]', comments: "Table description")
```

### Step 6: Create Relationships
```
chartdb_create_relationship(id: "rel-xxx", diagramId: "diagram-id", 
  name: "Source → Target", sourceTableId: "tbl-xxx", targetTableId: "tbl-yyy",
  sourceFieldId: "fk_field", targetFieldId: "id",
  sourceCardinality: "many", targetCardinality: "one")
```

### Step 7: Create Notes (with explicit dimensions)
```
chartdb_create_note(id: "note-xxx", diagramId: "diagram-id", 
  content: "Note text...", x: 1700, y: 30, width: 360, height: 480, color: "#4a4a4a")
```

### Step 8: Verify
```
chartdb_get_diagram(id: "diagram-id")
```
Check: no overlapping tables, correct field counts, all relationships present, areas cover their tables.

## Real Example: club-cip (23 tables, 4 areas, 32 relationships)

### Area Layout
| Area | x | y | width | height | Tables |
|------|---|---|-------|--------|--------|
| Alojamiento | 0 | 0 | 820 | 1140 | 9 (3×3 grid) |
| Identidad | 850 | 0 | 820 | 1080 | 6 (2×3 grid) |
| Finanzas | 0 | 1170 | 820 | 360 | 3 (1×3 row) |
| Entradas | 850 | 1170 | 820 | 630 | 5 (3+2 rows) |

### Table X Positions (absolute)
- Area 1 (x=0): 30, 290, 550
- Area 2 (x=850): 880, 1140, 1400
- Area 3 (x=0): 40, 300, 560
- Area 4 (x=850): 880, 1140, 1400 (row1); 990, 1250 (row2)

### Notes
Position notes outside the areas (x=1700) with width≥360 and height≥400 to avoid text compression.

## Key Takeaways

1. **Pre-calculate, never iterate** — layout math before any create calls
2. **No parentAreaId** — tables in area bounds work without it
3. **Absolute positions** — tables use canvas coordinates, not area-relative
4. **100px minimum gaps** — horizontal and vertical
5. **Verify after creation** — count fields, check positions, confirm no overlaps
6. **If reorg fails once, delete & recreate** — don't try to fix with updates
