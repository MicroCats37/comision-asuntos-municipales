# Generated migration: remove unique constraints from ReciboHonorarioDelegadoMensual
# to allow multiple RH headers per (delegado_operacion, periodo) or (delegado, periodo).
# User confirmed: "Crear RH" should always create a new RH header without replacing previous ones.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finanzas", "0008_rh_delegado_mensual_delegado_operacion"),
        ("liquidaciones", "0030_liquidaciondelegado_delegado_operacion"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Remove conditional unique constraint on (delegado_operacion, periodo)
        migrations.RemoveConstraint(
            model_name="recibohonorariodelegadomensual",
            name="unique_rh_delegado_mensual",
        ),
        # Remove legacy conditional unique constraint on (delegado, periodo)
        migrations.RemoveConstraint(
            model_name="recibohonorariodelegadomensual",
            name="unique_rh_delegado_mensual_legacy",
        ),
    ]
