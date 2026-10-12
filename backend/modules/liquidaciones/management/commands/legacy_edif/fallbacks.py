"""
EDIF legacy helpers — fallback markers for missing data in EDIF_ALL.csv.

These strings are used in place of rejecting a row, allowing the liquidation
to be created and flagged for human review. The corresponding observation is
also appended to the row's anomalies list so the data is traceable.
"""

# Marcadores para datos faltantes del Excel legacy.
# Estos strings se usan en lugar de rechazar la fila, permitiendo que la
# liquidación se cree y quede marcada para revisión humana.
# También se agrega la observación en el campo descripcion_legacy (o el que
# tenga el modelo) indicando que el dato fue completado por fallback.
NOMBRE_FALTANTE_LEGACY = "SIN NOMBRE RAZON SOCIAL LEGACY"
DIRECCION_FALTANTE_LEGACY = "SIN DIRECCION LEGACY"
DISTRITO_FALTANTE_LEGACY = "SIN DISTRITO LEGACY"
MUNICIPALIDAD_FALTANTE_LEGACY = "SIN CODIGO OG LEGACY"
