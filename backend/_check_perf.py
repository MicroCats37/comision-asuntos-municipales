import time
from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero
from modules.liquidaciones.management.commands.import_legacy_habilitacion_urbana import _ensure_perfil_ingeniero_by_cip

print("=== Antes (BD state) ===")
print('  CIP 069197 exists?', PerfilIngeniero.objects.filter(cip='069197').exists())
print('  CIP 001950 exists?', PerfilIngeniero.objects.filter(cip='001950').exists())

print()
print("=== Resolución rápida (use_endpoint=False, dry_run=False) ===")
for cip_str in ['69197', '1950', '12345']:
    t0 = time.perf_counter()
    p, status = _ensure_perfil_ingeniero_by_cip(int(cip_str), dry_run=False, use_endpoint=False)
    dt = (time.perf_counter() - t0) * 1000
    print(f'  CIP {cip_str:>6s} → status={status!r:<26} elapsed={dt:6.2f}ms perfil.cip={p.cip if p else None}')

print()
print("=== Después (BD state) ===")
print('  CIP 069197 exists?', PerfilIngeniero.objects.filter(cip='069197').exists())
print('  CIP 001950 exists?', PerfilIngeniero.objects.filter(cip='001950').exists())
