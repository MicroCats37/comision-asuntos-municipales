#!/usr/bin/env python3
import re
import json
from pathlib import Path

# File paths and specialties
FILES = [
    ("docs/desarrollo/delegados-sanitaria.md", "Ingeniería Sanitaria"),
    ("docs/desarrollo/delegados-habilitacion-urbana.md", "Habilitación Urbana"),
    ("docs/desarrollo/delegados-civil.md", "Ingeniería Civil"),
    ("docs/desarrollo/delegados-electrica-mecanica.md", "Ingeniería Eléctrica y Mecánica Eléctrica"),
]

def normalize_cip(cip_str):
    """Normalize CIP to 6 digits with leading zeros"""
    if not cip_str or cip_str.strip() == '-' or cip_str.strip() == '':
        return None
    digits = re.sub(r'\D', '', cip_str.strip())
    if digits:
        return digits.zfill(6)
    return None

def parse_full_name(full_name):
    """Parse 'APELLIDO_PATERNO APELLIDO_MATERNO NOMBRES' format"""
    if not full_name or full_name.strip() == '-' or full_name.strip() == '':
        return None, None, None
    parts = full_name.strip().split()
    if len(parts) >= 2:
        paterno = parts[0]
        materno = parts[1] if len(parts) > 1 else ""
        nombres = " ".join(parts[2:]) if len(parts) > 2 else ""
        return paterno, materno, nombres
    return parts[0], "", ""

def split_br_values(cell):
    """Split a cell by <br> and return list of stripped values"""
    if not cell or cell.strip() == '-' or cell.strip() == '':
        return []
    parts = re.split(r'<br\s*/?\s*>', cell, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip() and p.strip() != '-']

def split_municipalities(muni_str):
    """Split comma-separated municipalities, handling grouped entries"""
    if not muni_str:
        return []
    # Skip if this looks like a row number (e.g., "**1**" or "1-1")
    if re.match(r'^\s*\*?\*?\d', muni_str):
        return []
    # Split by comma and clean up
    parts = [p.strip() for p in muni_str.split(',')]
    result = []
    for p in parts:
        p = p.strip()
        if p:
            result.append(p)
    return result

def parse_table_row(row, specialty):
    """Parse a single table row and return assignments"""
    # Table format: | N° | Municipalidades | N° CIP Titular | Delegado Titular | N° CIP Alterno | Delegado Alterno |
    cells = row.split('|')
    if len(cells) < 7:
        return [], [], [], [], []

    # Table cells: | N° | Municipalidades | CIP Titular | Delegado Titular | CIP Alterno | Delegado Alterno |
    # After split('|'), cells[0] is empty, cells[1] is N°, cells[2] is municipality, etc.
    muni_cell = cells[2].strip() if len(cells) > 2 else ""
    cip_titular_cell = cells[3].strip() if len(cells) > 3 else ""
    nombre_titular_cell = cells[4].strip() if len(cells) > 4 else ""
    cip_alterno_cell = cells[5].strip() if len(cells) > 5 else ""
    nombre_alterno_cell = cells[6].strip() if len(cells) > 6 else ""

    municipalities = split_municipalities(muni_cell)
    cip_titular_list = split_br_values(cip_titular_cell)
    nombre_titular_list = split_br_values(nombre_titular_cell)
    cip_alterno_list = split_br_values(cip_alterno_cell)
    nombre_alterno_list = split_br_values(nombre_alterno_cell)

    return municipalities, cip_titular_list, nombre_titular_list, cip_alterno_list, nombre_alterno_list

def parse_file(filepath, specialty):
    """Parse a markdown file and return municipalities and assignments"""
    content = Path(filepath).read_text(encoding='utf-8')
    lines = content.split('\n')

    municipalities = []  # List of municipality names (raw)
    assignments = []  # List of (muni_name, cip, tipo) tuples

    for line in lines:
        if '|' not in line:
            continue
        # Skip header rows
        if line.startswith('| :---') or line.startswith('| N° |'):
            continue
        if not re.match(r'\|\s*\*\*?\d', line):
            continue

        muni_list, cip_t_list, nom_t_list, cip_a_list, nom_a_list = parse_table_row(line, specialty)

        # For grouped municipalities (row 44+), ALL municipalities share the same delegate
        # For regular rows, each delegate (from <br> splits) goes to the municipality
        if len(muni_list) > 1:
            # Grouped row - all municipalities get all delegates
            for i, muni in enumerate(muni_list):
                municipalities.append(muni)
                # Titular (if any)
                for j, cip in enumerate(cip_t_list):
                    cip_norm = normalize_cip(cip)
                    if cip_norm:
                        nombre = nom_t_list[j] if j < len(nom_t_list) else ""
                        assignments.append((muni, cip_norm, nombre, specialty, "titular"))
                # Alterno (if any)
                for j, cip in enumerate(cip_a_list):
                    cip_norm = normalize_cip(cip)
                    if cip_norm:
                        nombre = nom_a_list[j] if j < len(nom_a_list) else ""
                        assignments.append((muni, cip_norm, nombre, specialty, "alterno"))
        else:
            # Regular row - single municipality but possibly multiple delegates from <br>
            for muni in muni_list:
                municipalities.append(muni)

                # Titular - all of them
                for j, cip in enumerate(cip_t_list):
                    cip_norm = normalize_cip(cip)
                    if cip_norm:
                        nombre = nom_t_list[j] if j < len(nom_t_list) else ""
                        assignments.append((muni, cip_norm, nombre, specialty, "titular"))

                # Alterno - all of them
                for j, cip in enumerate(cip_a_list):
                    cip_norm = normalize_cip(cip)
                    if cip_norm:
                        nombre = nom_a_list[j] if j < len(nom_a_list) else ""
                        assignments.append((muni, cip_norm, nombre, specialty, "alterno"))

    return municipalities, assignments

def main():
    all_municipalities = {}  # name -> code
    all_delegados = {}  # cip -> {nombre, paterno, materno, nombres}
    all_assignments = []  # List of (cip, muni_code, especialidad, tipo) tuples

    muni_counter = 1

    for filepath, specialty in FILES:
        municipalities, assignments = parse_file(filepath, specialty)

        for muni in municipalities:
            muni_upper = muni.upper()
            if muni_upper not in all_municipalities:
                all_municipalities[muni_upper] = f"MUN{muni_counter:04d}"
                muni_counter += 1

        for muni, cip, nombre, espec, tipo in assignments:
            muni_code = all_municipalities[muni.upper()]

            # Add delegado if not exists
            if cip and cip not in all_delegados:
                paterno, materno, nombres = parse_full_name(nombre)
                if paterno:
                    all_delegados[cip] = {
                        "nombre": nombres if nombres else "",
                        "paterno": paterno,
                        "materno": materno if materno else "",
                        "nombre_completo": f"{paterno} {materno if materno else ''} {nombres if nombres else ''}".strip().upper(),
                        "especialidad": espec,
                        "tipo": tipo
                    }

            # Add assignment
            if cip:
                all_assignments.append((cip, muni_code, espec, tipo))

    # Deduplicate assignments
    seen_assignments = set()
    deduped_assignments = []
    for cip, muni_code, espec, tipo in all_assignments:
        key = (cip, muni_code, espec, tipo)
        if key not in seen_assignments:
            seen_assignments.add(key)
            deduped_assignments.append({
                "cip": cip,
                "municipalidad_codigo": muni_code,
                "especialidad": espec,
                "tipo": tipo
            })

    # Build final JSON structure
    result = {
        "version": "1.0",
        "periodo": "SEPTIEMBRE 2025 A AGOSTO 2026",
        "fuente": "docs/desarrollo/",
        "municipalidades": [
            {"nombre": name, "codigo": code, "provincia": None, "distrito": None}
            for name, code in sorted(all_municipalities.items(), key=lambda x: x[1])
        ],
        "delegados": [
            {**d, "cip": cip} for cip, d in sorted(all_delegados.items(), key=lambda x: x[0])
        ],
        "asignaciones": deduped_assignments
    }

    output_path = "backend/modules/liquidaciones/seeds/delegados_reales.json"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"Municipalidades: {len(result['municipalidades'])}")
    print(f"Delegados: {len(result['delegados'])}")
    print(f"Asignaciones: {len(result['asignaciones'])}")

    # Verification: check specific items
    print("\n=== VERIFICATION ===")

    # Check MIRAFLORES entries with <br>
    miraflores_asign = [a for a in result['asignaciones'] if 'MIRAFLORES' in a.get('municipalidad_codigo', '')]
    print(f"\nMIRAFLORES assignments: {len(miraflores_asign)}")

    # Find MIRAFLORES code
    miraflores_code = all_municipalities.get('MIRAFLORES', 'MUNXXXX')
    miraflores_asign = [a for a in result['asignaciones'] if a['municipalidad_codigo'] == miraflores_code]
    print(f"MIRAFLORES ({miraflores_code}) assignments:")
    for a in miraflores_asign:
        print(f"  - CIP {a['cip']}: {a['especialidad']} ({a['tipo']})")

    # Check SAN ISIDRO
    san_isidro_code = all_municipalities.get('SAN ISIDRO', 'MUNXXXX')
    san_isidro_asign = [a for a in result['asignaciones'] if a['municipalidad_codigo'] == san_isidro_code]
    print(f"\nSAN ISIDRO ({san_isidro_code}) assignments:")
    for a in san_isidro_asign:
        print(f"  - CIP {a['cip']}: {a['especialidad']} ({a['tipo']})")

    # Check SAN MIGUEL
    san_miguel_code = all_municipalities.get('SAN MIGUEL', 'MUNXXXX')
    san_miguel_asign = [a for a in result['asignaciones'] if a['municipalidad_codigo'] == san_miguel_code]
    print(f"\nSAN MIGUEL ({san_miguel_code}) assignments:")
    for a in san_miguel_asign:
        print(f"  - CIP {a['cip']}: {a['especialidad']} ({a['tipo']})")

    # Check SAN BORJA
    san_borja_code = all_municipalities.get('SAN BORJA', 'MUNXXXX')
    san_borja_asign = [a for a in result['asignaciones'] if a['municipalidad_codigo'] == san_borja_code]
    print(f"\nSAN BORJA ({san_borja_code}) assignments:")
    for a in san_borja_asign:
        print(f"  - CIP {a['cip']}: {a['especialidad']} ({a['tipo']})")

    # Check for duplicate municipalidad codes
    codes = [m['codigo'] for m in result['municipalidades']]
    print(f"\nDuplicate codes check: {len(codes)} total, {len(set(codes))} unique - {'OK' if len(codes) == len(set(codes)) else 'FAIL'}")

    print(f"\nOutput written to: {output_path}")

if __name__ == "__main__":
    main()
