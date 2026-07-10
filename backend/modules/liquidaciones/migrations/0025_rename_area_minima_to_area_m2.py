# Generated migration for renaming area_minima to area_m2 in TarifaPorMetroCuadrado

import django.db.models.deletion
import simple_history.models
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("liquidaciones", "0024_historicalliquidacionporcategoriavisitas_derecho_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(
            model_name="tarifapormetrocuadrado",
            old_name="area_minima",
            new_name="area_m2",
        ),
        migrations.RenameField(
            model_name="historicaltarifapormetrocuadrado",
            old_name="area_minima",
            new_name="area_m2",
        ),
        migrations.AlterField(
            model_name="historicalliquidacionpormetrocuadrado",
            name="area_base_calculo",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Área real aplicada tras evaluar area_m2 (max(area_solicitada, area_m2)).",
                max_digits=12,
                verbose_name="Área Base de Cálculo",
            ),
        ),
        migrations.AlterField(
            model_name="liquidacionpormetrocuadrado",
            name="area_base_calculo",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Área real aplicada tras evaluar area_m2 (max(area_solicitada, area_m2)).",
                max_digits=12,
                verbose_name="Área Base de Cálculo",
            ),
        ),
    ]
