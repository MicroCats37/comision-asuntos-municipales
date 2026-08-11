import re

filepath = "frontend/src/features/liquidaciones/components/NuevaRevisionFormModal.tsx"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Schema
schema_replacement = """const nuevaRevisionSchema = z.object({
  expediente_dummy: z.string().optional(),
  observacion: z.string().optional(),
});"""
content = re.sub(r'const nuevaRevisionSchema = z\.object\(\{\s*observacion: z\.string\(\)\.optional\(\),\s*\}\);', schema_replacement, content)

# 2. Update initialData
initial_replacement = 'initialData={{ expediente_dummy: (formulario as any)?.expediente ?? "", observacion: "" }}'
content = re.sub(r'initialData=\{\{\s*observacion:\s*""\s*\}\}', initial_replacement, content)

# 3. Update fields array
fields_replacement = """fields={[
          {
            name: "expediente_dummy",
            label: "Nº de Expediente (Simulado)",
            type: "text",
            placeholder: "Ej: EXP-2026...",
            icon: FileText,
            labelClassName: "text-primary font-semibold",
          },
          {
            name: "observacion",
            label: "Observación (opcional)","""
# Note: Since the file might have "Observacin" due to encoding, we match it flexibly
content = re.sub(r'fields=\{\[\s*\{\s*name:\s*"observacion",\s*label:\s*"Observaci[^"]+",', fields_replacement, content)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("File updated successfully.")
