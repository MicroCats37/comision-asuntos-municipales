"""
One-shot cleanup: set LiquidacionDelegado sentinel dates (1900-XX-XX) to NULL.

Run with:
    uv run python manage.py shell --settings=config.settings.development < clean_sentinel_1900.py
"""
from django.db import transaction
from django.db.models import Q
from modules.liquidaciones.domain.models.delegado import LiquidacionDelegado
from modules.liquidaciones.domain.constants import TipoLiquidacion as TL

QS = LiquidacionDelegado.objects.filter(
    liquidacion__legacy=True,
    liquidacion__tipo_liquidacion__codigo=TL.EDIFICACION,
)

BEFORE_PRES = QS.filter(fecha_presentacion__year=1900).count()
BEFORE_REV = QS.filter(fecha_revision__year=1900).count()
BEFORE_TOTAL = QS.filter(Q(fecha_presentacion__year=1900) | Q(fecha_revision__year=1900)).distinct().count()

print(f"Before cleanup:")
print(f"  fecha_presentacion 1900: {BEFORE_PRES}")
print(f"  fecha_revision 1900:     {BEFORE_REV}")
print(f"  total distinct affected: {BEFORE_TOTAL}")
print()

with transaction.atomic():
    up1 = QS.filter(fecha_presentacion__year=1900).update(fecha_presentacion=None)
    up2 = QS.filter(fecha_revision__year=1900).update(fecha_revision=None)
    print(f"UPDATE fecha_presentacion: {up1} filas -> NULL")
    print(f"UPDATE fecha_revision:     {up2} filas -> NULL")
    print(f"Total: {up1 + up2} campos corregidos")
