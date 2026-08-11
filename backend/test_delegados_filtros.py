import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from modules.liquidaciones.domain.services.orchestrators.delegado_orchestrator import DelegadoOrchestrator
from modules.liquidaciones.domain.services.core.delegado.delegado_core_service import DelegadoCoreService

orch = DelegadoOrchestrator(DelegadoCoreService())

# Lista completa
result = orch.list_delegados_proceso(page=1, page_size=5)
print(f"Total delegados: {result.total}")
for d in result.items[:3]:
    print(f"  {d.perfil_ingeniero.cip} - {d.perfil_ingeniero.nombre_completo} - estado={d.estado} - muns={len(d.municipalidades)}")
    for m in d.municipalidades[:2]:
        print(f"    -> {m.municipalidad.codigo} {m.municipalidad.nombre} vigente={m.es_vigente}")

# Filtro por estado
vigentes = orch.list_delegados_proceso(page=1, page_size=10, estado="vigente")
print(f"\nVigentes: {vigentes.total}")

# Filtro por cip
por_cip = orch.list_delegados_proceso(page=1, page_size=10, cip="006502")
print(f"Por cip 006502: {por_cip.total}")
if por_cip.items:
    d = por_cip.items[0]
    print(f"  {d.perfil_ingeniero.cip} - {d.perfil_ingeniero.nombre_completo}")
    print(f"  especialidad: {d.perfil_ingeniero.especialidad.codigo if d.perfil_ingeniero.especialidad else None}")
    print(f"  capitulo: {d.perfil_ingeniero.capitulo.abreviacion if d.perfil_ingeniero.capitulo else None}")
