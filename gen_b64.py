import os
import base64

script = """
import os
filepath = 'frontend/src/features/liquidaciones/components/LiquidacionPDFModal.tsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

original_text = '''  const right = append(footer, "div", { lineHeight: "1.45" });
  appendText(right, "p", `Hecho por ${hechoPor}`, { margin: "0" });
  appendText(right, "p", printedDateTime, { margin: "12px 0 0" });'''

new_text = '''  const right = append(footer, "div", { lineHeight: "1.45" });
  appendText(right, "p", `Hecho por ${hechoPor}`, { margin: "0", fontSize: "16px", fontWeight: "900" });
  appendText(right, "p", printedDateTime, { margin: "12px 0 0", fontSize: "16px", fontWeight: "900" });'''

content = content.replace(original_text, new_text)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated 'Hecho por' section successfully.")
"""

encoded = base64.b64encode(script.encode('utf-8')).decode('utf-8')
print(encoded)
