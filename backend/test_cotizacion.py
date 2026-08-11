import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from decimal import Decimal
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_porcentaje_obra_core_service import LiquidacionPorcentajeObraCoreService
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import DerechoPorcentajeObra, TarifaPorcentajeObra

core = LiquidacionPorcentajeObraCoreService()

# 3 tarifas de edificacion (0.05% c/u)
tarifas = list(TarifaPorcentajeObra.objects.filter(
    tarifa_base__tipo_liquidacion__codigo="EDIFICACION"
)[:3])
derecho = DerechoPorcentajeObra.objects.first()

print(f"Tarifas: {[(t.especialidad.codigo, float(t.porcentaje_liquidacion)) for t in tarifas]}")
print(f"Suma porcentajes: {sum(float(t.porcentaje_liquidacion) for t in tarifas)}")

# Caso A: valor 100000 -> subtotal 150 > minimo 110
r = core.calcular_cotizacion_po(
    valor_declarado=Decimal("100000"),
    tarifas=tarifas,
    igv_porcentaje=Decimal("0.18"),
    derecho=derecho,
    uit_valor=Decimal("5500"),
)
print(f"\nCaso A (100000):")
print(f"  Subtotal total: {r.total_subtotal} (esperado 150.00)")
print(f"  Total: {r.total} (esperado 177.00)")
print(f"  Detalles: {len(r.detalles)}")
print(f"  Suma detalles subtotal: {sum(d.subtotal for d in r.detalles)}")

# Caso B: valor 1000 -> subtotal 1.50 < minimo 110 -> aplica minimo una vez
r2 = core.calcular_cotizacion_po(
    valor_declarado=Decimal("1000"),
    tarifas=tarifas,
    igv_porcentaje=Decimal("0.18"),
    derecho=derecho,
    uit_valor=Decimal("5500"),
)
print(f"\nCaso B (1000, minimo debe aplicar UNA vez = 110):")
print(f"  Subtotal total: {r2.total_subtotal} (esperado 110.00, NO 330)")
print(f"  Total: {r2.total} (esperado 129.80)")
print(f"  Suma detalles subtotal: {sum(d.subtotal for d in r2.detalles)}")
