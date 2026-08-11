import os
import re

files = [
    "frontend/src/features/liquidaciones/components/LiquidacionEdificacionCard.tsx",
    "frontend/src/features/liquidaciones/components/LiquidacionGeneralCard.tsx",
    "frontend/src/features/liquidaciones/components/LiquidacionListCard.tsx"
]

for filepath in files:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find <LabelValue ... label="Código" ... />
    # We can use a regex that is not greedy on `>` by matching up to the first `/>` after `<LabelValue`.
    # Wait, the `value` prop contains JSX tags, which means it contains `>` but not `/>`.
    # Actually `<span ...>...</span>` contains `>`. But it does NOT contain `/>`.
    # So matching up to `/>` should be perfectly safe!
    
    # regex: <LabelValue\s+label="Código"[\s\S]*?/>
    new_content = re.sub(r'[ \t]*<LabelValue\s+label="C\u00f3digo"[\s\S]*?/>\n?', '', content)

    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Processed {filepath}")
