"""Diagnostic script for distritos issue - AMBAR municipalidad."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()

from datetime import date
from modules.entidades.models import Municipal
from modules.liquidaciones.domain.models import Delegado, MunicipalDelegado, PeriodoDelegado
from modules.liquidaciones.domain.constants import DelegadoStatus

print('=== TODAY:', date.today())
print()

# Get the AMBAR municipalidad
ambar = Municipal.objects.filter(nombre__icontains='ambar').first()
print(f'AMBAR: ID={ambar.id}, Nombre={ambar.nombre}')

# Get all MunicipalDelegado for AMBAR
mds = MunicipalDelegado.objects.filter(municipalidad=ambar)
print(f'MunicipalDelegado rows: {mds.count()}')

# Get all Delegate IDs
delegado_ids = mds.values_list('delegado_id', flat=True)
print(f'Delegado IDs: {list(delegado_ids)}')

# Get ALL PeriodoDelegado for these delegados (not just date filter)
print()
print('=== ALL PeriodoDelegado for these delegados ===')
periodos = PeriodoDelegado.objects.filter(delegado_id__in=delegado_ids)
print(f'Total: {periodos.count()}')
for p in periodos:
    print(f'  ID={p.id}, delegado={p.delegado_id}, inicio={p.periodo_inicio}, fin={p.periodo_fin}')

# Check if the periods in DB match today
print()
print('=== Periodos que contain today 2026-06-25 ===')
for p in periodos:
    if p.periodo_inicio <= date.today() and (p.periodo_fin is None or p.periodo_fin >= date.today()):
        print(f'  MATCH: {p.delegado_id}, {p.periodo_inicio} to {p.periodo_fin}')

# Show all periodo ranges
print()
print('=== All periodo ranges ===')
for p in periodos:
    print(f'  {p.periodo_inicio} to {p.periodo_fin}')