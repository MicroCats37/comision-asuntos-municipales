"""
Script to parse delegate documents and generate seed JSON.
Run from project root: python scripts/parse_delegados_docs.py

Parses:
- docs/desarrollo/1.md → Ingeniería Sanitaria
- docs/desarrollo/1 copy.md → Habilitación Urbana (labeled in source)
- docs/desarrollo/1 copy 2.md → Ingeniería Civil
"""

import json
import re
from pathlib import Path


def normalize_cip(cip):
    """Normalize CIP to 6 digits with leading zeros. Returns None if invalid."""
    if not cip or cip == '-' or cip.strip() == '-':
        return None
    cip = cip.strip().replace(',', '').replace('<br>', ' ').split()[0]
    cip = re.sub(r'\D', '', cip)
    if len(cip) < 6:
        cip = cip.zfill(6)
    return cip[:6]


def split_municipalities(muni_str):
    """Split comma-separated municipality names into separate entries."""
    if not muni_str:
        return []
    # Split by comma, but be careful with known patterns like "PROVINCIAL DE..."
    parts = [p.strip() for p in muni_str.split(',')]
    result = []
    for part in parts:
        if part:
            result.append(part)
    return result


def parse_name(name_str):
    """Parse name string into components."""
    if not name_str:
        return None
    name_str = name_str.strip().replace('<br>', ' ').replace('\n', ' ')
    name_str = re.sub(r'\s+', ' ', name_str)
    parts = name_str.split()
    if len(parts) < 2:
        return {'nombre_completo': name_str, 'nombre': name_str, 'paterno': '', 'materno': ''}
    # Assume format: NOMBRE APELLIDO_PATERNO APELLIDO_MATERNO
    # or: APELLIDO_PATERNO APELLIDO_MATERNO NOMBRE (if all caps)
    return {
        'nombre_completo': name_str,
        'nombre': parts[0] if len(parts) >= 1 else '',
        'paterno': parts[-2] if len(parts) >= 2 else '',
        'materno': parts[-1] if len(parts) >= 1 else ''
    }


def parse_row(row_text, specialty):
    """Parse a row from the table."""
    # Pattern: | **N** | Municipalidades | N° CIP Titular | Delegado Titular | N° CIP Alterno | Delegado Alterno |
    parts = [p.strip() for p in row_text.split('|')]
    parts = [p for p in parts if p]

    if len(parts) < 6:
        return None

    # Skip separator rows (e.g., | :--- | :--- | ...)
    if parts[0].startswith(':') or parts[1].startswith(':'):
        return None

    try:
        num = parts[0].replace('**', '').strip()
        municipalidades = parts[1].replace('**', '').strip()
        cip_titular_raw = parts[2].strip()
        delegado_titular_raw = parts[3].strip()
        cip_alterno_raw = parts[4].strip()
        delegado_alterno_raw = parts[5].strip()
    except IndexError:
        return None

    # Parse CIPs
    cip_titular = normalize_cip(cip_titular_raw)
    cip_alterno = normalize_cip(cip_alterno_raw)

    # Parse names
    delegado_titular = parse_name(delegado_titular_raw) if cip_titular else None
    delegado_alterno = parse_name(delegado_alterno_raw) if cip_alterno else None

    # Split municipalities
    muni_list = split_municipalities(municipalidades)

    return {
        'num': num,
        'municipalidades': muni_list,
        'especialidad': specialty,
        'titular': {
            'cip': cip_titular,
            'nombre': delegado_titular['nombre'] if delegado_titular else None,
            'paterno': delegado_titular['paterno'] if delegado_titular else None,
            'materno': delegado_titular['materno'] if delegado_titular else None,
            'nombre_completo': delegado_titular['nombre_completo'] if delegado_titular else None,
        } if cip_titular else None,
        'alterno': {
            'cip': cip_alterno,
            'nombre': delegado_alterno['nombre'] if delegado_alterno else None,
            'paterno': delegado_alterno['paterno'] if delegado_alterno else None,
            'materno': delegado_alterno['materno'] if delegado_alterno else None,
            'nombre_completo': delegado_alterno['nombre_completo'] if delegado_alterno else None,
        } if cip_alterno else None,
    }


def parse_doc(doc_path, specialty):
    """Parse a markdown document and return list of entries."""
    content = Path(doc_path).read_text(encoding='utf-8')
    lines = content.split('\n')

    entries = []
    for line in lines:
        if line.startswith('|') and not line.startswith('|:') and ' Municipalidades' not in line:
            result = parse_row(line, specialty)
            if result and result['municipalidades']:
                entries.append(result)

    return entries


def generate_muni_code(index):
    """Generate a unique municipality code with prefix + zero-padded counter.
    
    Format: MUN + 3-digit zero-padded index (e.g., MUN001, MUN002, ...)
    Max length: 10 chars (MUN + 3 digits = 6 chars, but we use 4 digits for scale)
    Actually: prefix 'MUN' + 4 digits = 7 chars, leaves room for future expansion.
    """
    return f"MUN{index:04d}"


def generate_seed_json():
    """Generate the seed JSON from all documents."""
    docs_base = Path('docs/desarrollo')

    seed_data = {
        'version': '1.0',
        'periodo': 'SEPTIEMBRE 2025 A AGOSTO 2026',
        'fuente': 'docs/desarrollo/',
        'municipalidades': [],
        'delegados': [],
        'asignaciones': [],
    }

    # Track unique municipalities and delegates
    seen_municipalidades = set()
    municipalidad_codes = {}
    seen_delegados = set()
    seen_asignaciones = set()
    muni_index = 1  # Counter for unique municipality codes

    # Parse documents
    # 1.md → Ingeniería Sanitaria
    entries_1 = parse_doc(docs_base / '1.md', 'Ingeniería Sanitaria')
    # 1 copy.md → Habilitación Urbana (labeled as "Habilitación Urbana" since title says "HABILITACIÓN URBANA")
    entries_copy = parse_doc(docs_base / '1 copy.md', 'Habilitación Urbana')
    # 1 copy 2.md → Ingeniería Civil
    entries_copy2 = parse_doc(docs_base / '1 copy 2.md', 'Ingeniería Civil')

    all_entries = entries_1 + entries_copy + entries_copy2

    for entry in all_entries:
        muni_list = entry['municipalidades']

        for muni_name in muni_list:
            muni_key = muni_name.upper().strip()
            if muni_key not in seen_municipalidades:
                seen_municipalidades.add(muni_key)
                seed_data['municipalidades'].append({
                    'nombre': muni_name.upper().strip(),
                    'codigo': generate_muni_code(muni_index),
                    'provincia': None,
                    'distrito': None,
                })
                municipalidad_codes[muni_key] = generate_muni_code(muni_index)
                muni_index += 1

        # Add titular
        if entry['titular'] and entry['titular']['cip']:
            cip = entry['titular']['cip']
            if cip not in seen_delegados:
                seen_delegados.add(cip)
                seed_data['delegados'].append({
                    'cip': cip,
                    'nombre': entry['titular']['nombre'],
                    'paterno': entry['titular']['paterno'],
                    'materno': entry['titular']['materno'],
                    'nombre_completo': entry['titular']['nombre_completo'],
                    'especialidad': entry['especialidad'],
                    'tipo': 'titular',
                })
            for muni_name in muni_list:
                muni_code = municipalidad_codes[muni_name.upper().strip()]
                key = (cip, muni_code)
                if key not in seen_asignaciones:
                    seen_asignaciones.add(key)
                    seed_data['asignaciones'].append({
                        'cip': cip,
                        'municipalidad_codigo': muni_code,
                        'especialidad': entry['especialidad'],
                        'tipo': 'titular',
                    })

        # Add alterno
        if entry['alterno'] and entry['alterno']['cip']:
            cip = entry['alterno']['cip']
            if cip not in seen_delegados:
                seen_delegados.add(cip)
                seed_data['delegados'].append({
                    'cip': cip,
                    'nombre': entry['alterno']['nombre'],
                    'paterno': entry['alterno']['paterno'],
                    'materno': entry['alterno']['materno'],
                    'nombre_completo': entry['alterno']['nombre_completo'],
                    'especialidad': entry['especialidad'],
                    'tipo': 'alterno',
                })
            for muni_name in muni_list:
                muni_code = municipalidad_codes[muni_name.upper().strip()]
                key = (cip, muni_code)
                if key not in seen_asignaciones:
                    seen_asignaciones.add(key)
                    seed_data['asignaciones'].append({
                        'cip': cip,
                        'municipalidad_codigo': muni_code,
                        'especialidad': entry['especialidad'],
                        'tipo': 'alterno',
                    })

    return seed_data


if __name__ == '__main__':
    seed = generate_seed_json()
    output_path = Path('backend/modules/liquidaciones/seeds/delegados_reales.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(seed, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"Generated seed JSON with:")
    print(f"  - {len(seed['municipalidades'])} municipalidades")
    print(f"  - {len(seed['delegados'])} delegados")
    print(f"  - {len(seed['asignaciones'])} asignaciones")
    print(f"  - Saved to: {output_path}")
