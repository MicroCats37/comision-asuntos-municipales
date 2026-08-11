import re

filepath = "frontend/src/features/liquidaciones/components/LiquidacionPDFModal.tsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update `details` container to be 30% larger (14px -> 18px) and bold
# Find: fontSize: "14px",
content = re.sub(
    r'fontSize: "14px",\s*lineHeight: "1\.35",',
    'fontSize: "18px",\n      fontWeight: "800",\n      lineHeight: "1.35",',
    content
)

# 2. Update `appendReceiptRow` to be extra bold
# Find: appendText(row, "span", label, { fontWeight: "700", minWidth: "180px", flexShrink: "0" });
content = re.sub(
    r'appendText\(row, "span", label, \{ fontWeight: "700"',
    'appendText(row, "span", label, { fontWeight: "900"',
    content
)
# Make the value text bold too
content = re.sub(
    r'appendText\(row, "span", `: \$\{value\}`, \{ overflow: "hidden"',
    'appendText(row, "span", `: ${value}`, { fontWeight: "800", overflow: "hidden"',
    content
)

# 3. Update footer left block
# Find:
# const left = append(footer, "div", { lineHeight: "1.35" });
# appendText(left, "p", "COMISION DE ASUNTOS MUNICIPALES", { margin: "0", fontSize: "10px", fontWeight: "700" });
# appendText(left, "p", "Tel.: 202-5066", { margin: "0", fontSize: "10px" });
# appendText(left, "p", `Tramitado por ${contactName}`, { margin: "8px 0 0" });
# appendText(left, "p", `TELEFONO      ${contactPhone}`, { margin: "10px 0 0" });
# appendText(left, "p", printedDateTime, { margin: "16px 0 0", letterSpacing: "0.08em" });

def repl_footer(m):
    return """const left = append(footer, "div", { lineHeight: "1.35", fontSize: "16px", fontWeight: "900" });
    appendText(left, "p", "COMISION DE ASUNTOS MUNICIPALES", { margin: "0", fontSize: "13px", fontWeight: "900" });
    appendText(left, "p", "Tel.: 202-5066", { margin: "0", fontSize: "13px", fontWeight: "900" });
    appendText(left, "p", `Tramitado por ${contactName}`, { margin: "8px 0 0", fontWeight: "900" });
    appendText(left, "p", `TELEFONO      ${contactPhone}`, { margin: "10px 0 0", fontWeight: "900" });
    appendText(left, "p", printedDateTime, { margin: "16px 0 0", letterSpacing: "0.08em", fontWeight: "900" });"""

content = re.sub(
    r'const left = append\(footer, "div", \{ lineHeight: "1\.35" \}\);.*?(?=appendText\(footer, "div", "ESTE DOCUMENTO NO ES\\n)',
    repl_footer,
    content,
    flags=re.DOTALL
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated LiquidacionPDFModal.tsx successfully.")
