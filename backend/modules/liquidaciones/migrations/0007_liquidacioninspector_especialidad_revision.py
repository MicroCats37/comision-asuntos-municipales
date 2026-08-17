# Generated manually: add especialidad_revision to LiquidacionInspector (NOT NULL).
# La tabla está vacía en este punto del desarrollo (datos de prueba recreados),
# por lo que se puede añadir como NOT NULL sin default.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("liquidaciones", "0006_remove_especialidad_revision_base"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalliquidacioninspector",
            name="especialidad_revision",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="usuarios.especialidadrevision",
                verbose_name="Especialidad de Revisión",
            ),
        ),
        migrations.AddField(
            model_name="liquidacioninspector",
            name="especialidad_revision",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="liquidacion_inspectores",
                to="usuarios.especialidadrevision",
                verbose_name="Especialidad de Revisión",
            ),
            preserve_default=False,
        ),
    ]
