#!/usr/bin/env python3
import json

with open('backend/modules/liquidaciones/seeds/delegados_reales.json', encoding='utf-8') as f:
    data = json.load(f)

print("JSON is valid!")
print(f"Municipalidades: {len(data['municipalidades'])}")
print(f"Delegados: {len(data['delegados'])}")
print(f"Asignaciones: {len(data['asignaciones'])}")

# Verify MIRAFLORES (MUN0021) has correct assignments
miraflores_assign = [a for a in data['asignaciones'] if a['municipalidad_codigo'] == 'MUN0021']
print(f"\nMIRAFLORES (MUN0021) assignments: {len(miraflores_assign)}")
for a in miraflores_assign:
    print(f"  - CIP {a['cip']}: {a['especialidad']} ({a['tipo']})")

# Verify SAN ISIDRO (MUN0030) - should have 2 TITULAR and 1 ALTERN from <br> in row 27
san_isidro_assign = [a for a in data['asignaciones'] if a['municipalidad_codigo'] == 'MUN0030']
print(f"\nSAN ISIDRO (MUN0030) assignments: {len(san_isidro_assign)}")
for a in san_isidro_assign:
    print(f"  - CIP {a['cip']}: {a['especialidad']} ({a['tipo']})")

# Check for duplicate municipalidad codes
codes = [m['codigo'] for m in data['municipalidades']]
print(f"\nDuplicate codes: {'YES - FAIL' if len(codes) != len(set(codes)) else 'NO - OK'}")

# Check grouped municipalities (CAÑETE province entries)
canietes = [m for m in data['municipalidades'] if 'CAÑETE' in m['nombre'] or 'CAYLLOMA' in m['nombre']]
print(f"\nCañete/Caylloma related municipalities: {len(canietes)}")
for m in canietes:
    print(f"  - {m['nombre']}: {m['codigo']}")

# Check specific CIP that should exist (018554)
cip_18554 = [d for d in data['delegados'] if d['cip'] == '018554']
print(f"\nCIP 018554 exists: {len(cip_18554) > 0}")
if cip_18554:
    print(f"  Data: {cip_18554[0]}")
