from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero

p = PerfilIngeniero.objects.filter(cip='069197').first()
print('=== CIP 069197 ===')
print('Existe:', p is not None)
if p:
    print(' nombres:', repr(p.nombres))
    print(' apellido_paterno:', repr(p.apellido_paterno))
    print(' apellido_materno:', repr(p.apellido_materno))

print()
print('=== Placeholders detectados (nombres empieza con CIP ) ===')
n = PerfilIngeniero.objects.filter(nombres__startswith='CIP ').count()
print('Count:', n)
if n > 0:
    for x in PerfilIngeniero.objects.filter(nombres__startswith='CIP ')[:5]:
        print(' -', x.cip, '|', x.nombres, '|', x.apellido_paterno, '|', x.apellido_materno)

print()
print('=== Hydrate simulation for CIP 69197 ===')
from modules.usuarios.domain.services.core.perfil_ingeniero_core_service import PerfilIngenieroCoreService
service = PerfilIngenieroCoreService()
perfil, status = service.hydrate_perfil_from_cip('69197', dry_run=False)
print('perfil:', perfil, 'status:', status)
