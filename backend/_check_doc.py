from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import LiquidacionComprobante
from collections import Counter

todos = LiquidacionComprobante.objects.all()
n = todos.count()
print(f"Total comprobantes: {n}")
print()

dist_tipo = Counter([str(t) for t in todos.values_list('tipo_comprobante', flat=True)])
print("=== Distribucion tipo_comprobante ===")
for k in sorted(dist_tipo.keys()):
    print(f"  {k:20s}  {dist_tipo[k]:6d}  ({100*dist_tipo[k]/n:.1f}%)")
print()

print("=== Muestra (10 comprobantes NO-null) ===")
muestra = list(todos.exclude(tipo_comprobante__isnull=True)[:10])
for c in muestra:
    print(f"  id={c.id:6d}  tipo={c.tipo_comprobante!r:10s}  serie={str(c.serie):4s}  numero={str(c.numero):10s}  monto={c.monto}")

print()
print("=== Comprobantes CREADOS en el ultimo run (last 24h) ===")
from django.utils import timezone
from datetime import timedelta
ayer = timezone.now() - timedelta(days=1)
recientes = LiquidacionComprobante.objects.filter(created_at__gte=ayer)
print(f"Total recientes: {recientes.count()}")
dist_rec = Counter([str(t) for t in recientes.values_list('tipo_comprobante', flat=True)])
for k in sorted(dist_rec.keys()):
    print(f"  {k:20s}  {dist_rec[k]:6d}")
