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

    # We match all LabelValue tags.
    # regex to find <LabelValue ... />
    def replacer(match):
        text = match.group(0)
        # Only remove if it's the "Código" label AND it contains "public_id"
        if 'label="C' in text and 'digo"' in text and 'public_id' in text:
            return ''
        return text

    # Matches `<LabelValue` followed by anything up to `/>`
    new_content = re.sub(r'[ \t]*<LabelValue[\s\S]*?/>\n?', replacer, content)

    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Processed {filepath}")
