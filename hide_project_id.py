import os
import re

directory = "frontend/src/features/liquidaciones/components"

for filename in os.listdir(directory):
    if not filename.endswith("Card.tsx") and not filename.endswith("CardHeader.tsx"):
        continue
    filepath = os.path.join(directory, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # We want to remove the UI part that shows the public project ID.
    # Pattern: <LabelValue label="Código" value={<span className="font-mono text-primary font-semibold">{proyecto.public_id}</span>} />
    # Or something similar for `edificaciones.public_id`, `item.public_id` etc. if labelled "Código".
    
    # Let's remove any LabelValue that contains `public_id`
    # e.g., <LabelValue label="Código" value={<span ...>{proyecto.public_id}</span>} />
    new_content = re.sub(r'[ \t]*<LabelValue[^>]*public_id[^>]*/>\n?', '', content)

    # In LiquidacionCardHeader.tsx, the public_id is displayed inside a badge or header
    # Let's just comment it out if it's there, but the user specifically mentioned "en mis cards".
    # Wait, the card header usually shows the public ID of the *Liquidación* (e.g. LIQ-2023-0001), not the *Project* (PROY-2023-0001).
    # The user says "proyect id publico y eso en mis cards".
    # This means they want to hide the PROYECTO public ID, not the LIQUIDACION public ID.
    # The LIQUIDACION public ID is usually just `public_id` (from `item.public_id`).
    # The PROYECTO public ID is `proyecto.public_id`.
    
    new_content = re.sub(r'[ \t]*<LabelValue[^>]*proyecto\.public_id[^>]*/>\n?', '', new_content)
    
    # Sometimes it's wrapped differently:
    # <LabelValue label="Código" value={<span className="font-mono text-primary font-semibold">{proyecto.public_id}</span>} />
    # The regex `[ \t]*<LabelValue[^>]*proyecto\.public_id[^>]*/>\n?` might not match if there are nested elements.
    # A safer regex for <LabelValue ... proyecto.public_id ... />:
    new_content = re.sub(r'[ \t]*<LabelValue\s+label="[^"]*".*?proyecto\.public_id.*?\/>\n?', '', new_content, flags=re.DOTALL)
    
    # Let's also remove this exact block if it spans multiple lines:
    new_content = re.sub(r'[ \t]*<LabelValue\s+label="Código"\s+value=\{\s*<span[^>]*>\{proyecto\.public_id\}</span>\s*\}\s*/>\n?', '', new_content)

    # Also for edificaciones: <LabelValue label="Código" value={edificaciones.public_id} /> or similar if it's there
    new_content = re.sub(r'[ \t]*<LabelValue\s+label="Código"\s+value=\{edificaciones\.public_id\}\s*/>\n?', '', new_content)
    
    # Just to be extremely thorough with anything that says "Código" and shows `proyecto.public_id`
    new_content = re.sub(r'[ \t]*<LabelValue[^>]*label="C\u00f3digo"[^>]*proyecto\.public_id.*?\/>\n?', '', new_content, flags=re.DOTALL)

    # Write back
    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Processed {filename}")
