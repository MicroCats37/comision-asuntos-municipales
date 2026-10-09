"""
EDIF legacy helpers — column index constants for EDIF_ALL.csv.

EDIF_ALL.csv: 119 columns, delimiter ';', BOM UTF-8.

Index layout (0-based after splitting on ';'):
    0       ID (legacy auto-incremental)
    1       NRO (número secuencial de la liquidación específica)
    2       RUC
    3       NOMBRE
    4       PROYECTO
    5       DPTOPRDI
    6       DIRECCION
    7       VALOROBRA
    8       PORCENTAJE
    9       SUBTOTAL
    10      IGV
    11      TOTAL
    12      FECHA
    13      DNI
    14      RAZONSOCIAL
    15      NROFACTURA
    16      CODPAGO
    17      NROEXPDTE
    18      NROREV
    19      ESPECIALIDAD
    ...
    22-25   DELEGADO1..4 (nombre del ingeniero)
    26      IMPBRUTO
    27      APORTE_CODEMU
    28      FONDO_COMUN
    31      NETOHONORA
    32      USUARIO
    35-58   RH slot fields for slots 1-4 (PERIODO, MES, FECHAPRES, FECHAREVI, NROORDEN, DICTAMEN)
    60      TFONO
    61      TPERSONA
    64-67   PERIODO1..4
    68-71   MES1..4
    72      RENTACIP
    79-82   CIP1..4
    87-90   NRORH1..4
    91-94   NROMM1..4
"""

import re

#: First delimiter block (DELEGADO1..4) ends at index 25.
DELEGADO_BLOCK_END = 25

# ── Main CSV column indices ──────────────────────────────────────────────────────

COL_ID = 0
COL_RUC = 2
COL_NRO = 1
COL_NOMBRE = 3
COL_PROYECTO = 4
COL_DPTOPRDI = 5
COL_DIRECCION = 6
COL_VALOROBRA = 7
COL_PORCENTAJE = 8
COL_SUBTOTAL = 9
COL_IGV = 10
COL_TOTAL = 11
COL_FECHA = 12
COL_DNI = 13
COL_RAZONSOCIAL = 14
COL_CODPAGO = 16
COL_NROEXPDTE = 17
COL_NROREV = 18
COL_ESPECIALIDAD = 19
COL_TFONO = 60
COL_TPERSONA = 61
COL_USUARIO = 32

# ── RH Slot column indices ──────────────────────────────────────────────────────

# DELEGADO (nombre del ingeniero) slot columns
COL_DELEGADO1 = 22
COL_DELEGADO2 = 23
COL_DELEGADO3 = 24
COL_DELEGADO4 = 25

# CIP slot columns
COL_CIP1 = 79
COL_CIP2 = 80
COL_CIP3 = 81
COL_CIP4 = 82

# PERIODO slot columns
COL_PERIODO1 = 64
COL_PERIODO2 = 65
COL_PERIODO3 = 66
COL_PERIODO4 = 67

# MES slot columns
COL_MES1 = 68
COL_MES2 = 69
COL_MES3 = 70
COL_MES4 = 71

# FECHAPRES (fecha presentación) slot columns
COL_FECHAPRES1 = 35
COL_FECHAPRES2 = 38
COL_FECHAPRES3 = 41
COL_FECHAPRES4 = 44

# FECHAREVI (fecha revisión) slot columns
COL_FECHAREVI1 = 36
COL_FECHAREVI2 = 39
COL_FECHAREVI3 = 42
COL_FECHAREVI4 = 45

# NROORDEN (número de orden) slot columns
COL_NROORDEN1 = 37
COL_NROORDEN2 = 40
COL_NROORDEN3 = 43
COL_NROORDEN4 = 46

# DICTAMEN slot columns
COL_DICTAMEN1 = 55
COL_DICTAMEN2 = 56
COL_DICTAMEN3 = 57
COL_DICTAMEN4 = 58

# NRORH slot columns
COL_NRORH1 = 87
COL_NRORH2 = 88
COL_NRORH3 = 89
COL_NRORH4 = 90

# NROMM slot columns
COL_NROMM1 = 91
COL_NROMM2 = 92
COL_NROMM3 = 93
COL_NROMM4 = 94

# ── Shared monetary column indices ──────────────────────────────────────────────

COL_IMPBRUTO = 26
COL_RENTACIP = 72
COL_APORCODEMU = 27
COL_FONDOCOMUN = 28
COL_NETOHONORA = 31

# Aliases matching legacy_edif.delegado_columns naming
IMP_BRUTO = COL_IMPBRUTO
RENTA_CIP = COL_RENTACIP
APORTE_CODEMU = COL_APORCODEMU
FONDO_COMUN = COL_FONDOCOMUN
NETO_HONORARIO = COL_NETOHONORA

# ── RH Slot column mapping ──────────────────────────────────────────────────────

RH_SLOT_COLUMNS = {
    1: (COL_DELEGADO1, COL_CIP1, COL_PERIODO1, COL_MES1, COL_FECHAPRES1, COL_FECHAREVI1, COL_NROORDEN1, COL_DICTAMEN1, COL_NRORH1, COL_NROMM1),
    2: (COL_DELEGADO2, COL_CIP2, COL_PERIODO2, COL_MES2, COL_FECHAPRES2, COL_FECHAREVI2, COL_NROORDEN2, COL_DICTAMEN2, COL_NRORH2, COL_NROMM2),
    3: (COL_DELEGADO3, COL_CIP3, COL_PERIODO3, COL_MES3, COL_FECHAPRES3, COL_FECHAREVI3, COL_NROORDEN3, COL_DICTAMEN3, COL_NRORH3, COL_NROMM3),
    4: (COL_DELEGADO4, COL_CIP4, COL_PERIODO4, COL_MES4, COL_FECHAPRES4, COL_FECHAREVI4, COL_NROORDEN4, COL_DICTAMEN4, COL_NRORH4, COL_NROMM4),
}

# Alias for backward compatibility with delegado_columns.py consumers
DELEGADO_SLOT_COLUMNS = RH_SLOT_COLUMNS

# ── Slot specialty mapping ──────────────────────────────────────────────────────

# Maps slot number (1..4) to the legacy XLSX display name (used for lookup
# before DB resolution, kept for readability in reports).
_SLOT_SPECIALTY_MAP = {
    1: "Estructuras / Civil",
    2: "Instalaciones Sanitarias",
    3: "Mecánico-Eléctricas",
    4: "Electrónica",
}

# ── Slot → EspecialidadRevision.nombre (canonical DB names) ────────────────────

SLOT_SPECIALTY_DB_MAP = {
    1: "Ingeniería Civil",
    2: "Ingeniería Sanitaria",
    3: "Ingeniería Eléctrica y Mecánica Eléctrica",
    4: "Ingeniería Electrónica",
}

# ── Embedded CIP regex ──────────────────────────────────────────────────────────

# Some legacy rows embed the CIP inside the delegado text rather than in the
# dedicated CIP column (e.g. "CIP 14720 Titular: ..."). This regex captures
# the numeric CIP at the start of the name so we can still process the slot.
CIP_EMBEDDED_RE = re.compile(r'^\s*CIP\s+(\d{2,7})\b', re.IGNORECASE)

COL_ESPECIALIDAD = 19
