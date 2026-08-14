"""Diagnóstico del bug de porcentaje 0.0002"""
import os
import json
from decimal import Decimal

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.development'

import django
django.setup()

from modules.liquidaciones.domain.models.liquidacion.liquidacion import TarifaLiquidacionBase, TarifaPorcentajeObra, ReglaTarifaEdificacion
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadIngeniero as Especialidad

# Load seed
with open('modules/liquidaciones/seeds/tarifas_edificacion.json') as f:
    seed_data = json.load(f)

print("=== DIAGNOSTIC ===")
print()

# Check existing DB state
print("DB state BEFORE deletion:")
for tb in TarifaLiquidacionBase.objects.all().prefetch_related('especialidades', 'detalle_porcentual'):
    pct = tb.detalle_porcentual
    specs = sorted([e.nombre for e in tb.especialidades.all()])
    print(f"  {tb.id} pct={pct.porcentaje_liquidacion} specs={specs}")

print()
print("Seed entries with (specs_sorted, pct):")
for i, t in enumerate(seed_data['tarifas']):
    specs = sorted(t['especialidades'])
    pct_raw = t['porcentaje_liquidacion']
    pct_decimal = Decimal(pct_raw)
    rules = [(r['tipo_tramite'], r['tramite_accion']) for r in t['reglas']]
    print(f"  Entry {i}: pct_raw={repr(pct_raw)} pct_decimal={pct_decimal} specs={specs}")
    print(f"    rules: {rules}")

print()
print("Looking for existing bases that match entry 7 (PROYECTO_CON_PLANTAS_TIPICAS):")
entry7_specs = sorted(['Ingeniería Civil', 'Ingeniería Sanitaria', 'Ingeniería Eléctrica y Mecánica Eléctrica'])
entry7_pct = Decimal('0.00015')

for tb in TarifaLiquidacionBase.objects.filter(
    tipo_liquidacion='EDIFICACION'
).prefetch_related('especialidades', 'detalle_porcentual'):
    db_specs = sorted([e.nombre for e in tb.especialidades.all()])
    db_pct = tb.detalle_porcentual.porcentaje_liquidacion
    specs_match = db_specs == entry7_specs
    pct_match = db_pct == entry7_pct
    print(f"  {tb.id}: specs_match={specs_match} pct_match={pct_match}")
    print(f"    db_specs={db_specs}")
    print(f"    db_pct={db_pct} (expected {entry7_pct})")
