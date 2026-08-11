import os
filepath = 'frontend/src/features/liquidaciones/components/NuevaRevisionEdificacionesFormModal.tsx'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'value={`${formulario.liquidacion_previa_id.slice(0, 8)}...`}',
    'value={((formulario as any).liquidacion_public_id || formulario.liquidacion_previa_id).slice(-10)}'
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated liquidacion_previa_id.slice to slice(-10)")
