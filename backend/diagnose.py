import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()

from datetime import date
from modules.entidades.models import Municipal
from modules.liquidaciones.domain.models import Delegado, MunicipalDelegado, PeriodoDelegado
from modules.liquidaciones.domain.constants import DelegadoStatus

# Buscar municipalidades con nombre tipo 'Ambar' o 'Ámbar'
print('=== MUNICIPALIDADES ===')
municipalidades = Municipal.objects.filter(nombre__icontains='mbar')
for m in municipalidades:
    print(f'ID: {m.id}, Nombre: {m.nombre}, Codigo: {m.codigo}')

print()
print('=== MUNICIPALIDADDELEGADO para municipalidades encontradas ===')
for m in municipalidades:
    mds = MunicipalDelegado.objects.filter(municipalidad=m)
    for md in mds:
        print(f'MD ID: {md.id}, Delegado: {md.delegado_id}, Activo: {md.activo}')
        dele = md.delegado
        print(f'  -> Delegado status: {dele.status}')
        print(f'  -> Delegado nombre: {dele.perfil_ingeniero.nombre_completo if dele.perfil_ingeniero else None}')

print()
print('=== PERIODOS PARA ESOS DELEGADOS ===')
for m in municipalidades:
    mds = MunicipalDelegado.objects.filter(municipalidad=m)
    for md in mds:
        periodos = PeriodoDelegado.objects.filter(delegado=md.delegado)
        for p in periodos:
            print(f'Periodo ID: {p.id}, Delegado: {p.delegado_id}, Inicio: {p.periodo_inicio}, Fin: {p.periodo_fin}')