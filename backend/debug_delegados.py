import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from datetime import date
from django.db.models import Q
from modules.liquidaciones.domain.models.liquidacion import TarifaLiquidacionBase, EspecialidadesLiquidacion
from modules.liquidaciones.domain.models.delegado import Delegado
from modules.liquidaciones.domain.constants import TipoLiquidacion, DelegadoStatus

muni = 'f77f106f-a5b6-48b3-b1e8-6fc2bc38710e'
rev = '0ec24c1e-f496-48ea-b26a-8ecd6ea0b56d'
t = date.today()

tb = TarifaLiquidacionBase.objects.get(id=rev)
print(f'TarifaBase: tipo={tb.tipo_liquidacion}, especialidades={list(tb.especialidades.values_list("nombre", flat=True))}')

gv = EspecialidadesLiquidacion.objects.filter(
    tipo_liquidacion=TipoLiquidacion.EDIFICACION,
    periodo_inicio__lte=t
).filter(
    Q(periodo_fin__isnull=True) | Q(periodo_fin__gte=t)
).first()
print(f'GrupoVigente: {gv}')
if gv:
    print(f'Especialidades vigentes: {list(gv.especialidades.values_list("nombre", flat=True))}')

if gv:
    int_ids = set(tb.especialidades.values_list('id', flat=True)) & set(gv.especialidades.values_list('id', flat=True))
    print(f'Interseccion IDs: {int_ids}')

d = Delegado.objects.filter(
    distritos_asignados__municipalidad_id=muni,
    distritos_asignados__activo=True,
    status=DelegadoStatus.ACTIVO
).distinct()
print(f'Delegados en muni (sin filtro especialidad): {d.count()}')
for x in d:
    print(f'  {x.perfil_ingeniero.nombre_completo} - {x.especialidad.nombre} (id={x.especialidad_id})')

if int_ids:
    d2 = d.filter(especialidad_id__in=int_ids)
    print(f'Delegados tras filtro especialidad: {d2.count()}')
    for x in d2:
        print(f'  {x.perfil_ingeniero.nombre_completo} - {x.especialidad.nombre}')
else:
    print('Interseccion vacia -> 0 delegados')
