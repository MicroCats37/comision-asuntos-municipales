#!/usr/bin/env python3
"""Debug script to check parsing logic"""
import re
from pathlib import Path

# Test line parsing
line = '| **44** | PROVINCIAL DE CAÑETE, SAN ANTONIO DE CAÑETE, ASIA, CERRO AZUL, LUNAHUANA, MALA, CHILCA, IMPERIAL, NUEVO IMPERIAL, SAN LUIS DE CAÑETE, CALANGO, COAYLLO, PACARAN, QUILMANA, SANTA CRUZ DE FLORES, ZUÑIGA | 74281 | LOPEZ REAL GABRIEL ROBERTO | 72389 | CASTILLO CHAVEZ JORGE LUIS |'
cells = line.split('|')
print(f'Cells count: {len(cells)}')
for i, c in enumerate(cells):
    print(f'{i}: [{c.strip()}]')

# Check row detection regex
test_lines = [
    '| **1** | CERCADO DE LIMA | 6502 | ALBINAGORTA JARAMILLO JORGE ALBERTO | 8311 | RAMOS SAAVEDRA JOSE UBALDO |',
    '| **18** | MIRAFLORES | 115447 <br> 38284 | PADILLA MISAJEL ROMULO ALBERTO <br> VIDAL VALENZUELA ERNESTO ABELARDO | 16932 | ESTEBAN PALOMINO YONEL CLEVER |',
    '| **44** | PROVINCIAL DE CAÑETE, SAN ANTONIO DE CAÑETE, ASIA, CERRO AZUL, LUNAHUANA, MALA, CHILCA, IMPERIAL, NUEVO IMPERIAL, SAN LUIS DE CAÑETE, CALANGO, COAYLLO, PACARAN, QUILMANA, SANTA CRUZ DE FLORES, ZUÑIGA | 74281 | LOPEZ REAL GABRIEL ROBERTO | 72389 | CASTILLO CHAVEZ JORGE LUIS |',
]

print("\nRow detection:")
for tl in test_lines:
    match = re.match(r'\|\s*\*\*?\d', tl)
    print(f"  Match: {bool(match)} for {tl[:50]}...")

def split_br_values(cell):
    if not cell or cell.strip() == '-' or cell.strip() == '':
        return []
    parts = re.split(r'<br\s*/?\s*>', cell, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip() and p.strip() != '-']

# Test split_br_values
test_cell = "115447 <br> 38284"
print(f"\nSplit br test: {split_br_values(test_cell)}")

# Test municipality split
muni_str = "PROVINCIAL DE CAÑETE, SAN ANTONIO DE CAÑETE, ASIA, CERRO AZUL, LUNAHUANA, MALA, CHILCA, IMPERIAL, NUEVO IMPERIAL, SAN LUIS DE CAÑETE, CALANGO, COAYLLO, PACARAN, QUILMANA, SANTA CRUZ DE FLORES, ZUÑIGA"
parts = [p.strip() for p in muni_str.split(',')]
print(f"\nMunicipalities split: {len(parts)} items")
for p in parts:
    print(f"  - {p}")
