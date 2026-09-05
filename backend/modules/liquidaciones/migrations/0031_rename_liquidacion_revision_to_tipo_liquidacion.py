"""
Rename DelegadoOperacion.liquidacion_revision to tipo_liquidacion.

This is a semantic rename only — data is preserved via Django RenameField migration.
The field FK target (TipoLiquidacion), null/blank behavior remain unchanged.

Operation: RenameField
Model: DelegadoOperacion
Field: liquidacion_revision -> tipo_liquidacion

Additionally updates the unique_together constraint reference.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("liquidaciones", "0030_liquidaciondelegado_delegado_operacion"),
    ]

    operations = [
        migrations.RenameField(
            model_name="delegadooperacion",
            old_name="liquidacion_revision",
            new_name="tipo_liquidacion",
        ),
        migrations.RenameField(
            model_name="historicaldelegadooperacion",
            old_name="liquidacion_revision",
            new_name="tipo_liquidacion",
        ),
        migrations.AlterUniqueTogether(
            name="delegadooperacion",
            unique_together={("delegado", "municipalidad", "tipo_liquidacion")},
        ),
        migrations.AlterUniqueTogether(
            name="historicaldelegadooperacion",
            unique_together={("delegado", "municipalidad", "tipo_liquidacion")},
        ),
    ]
