# Generated manually — Fase 8-10: Add VigenciaModel fields to LiquidacionEspecialidadDisponibles
# and especialidad_revision FK to LiquidacionDelegado.
# Default for periodo_inicio: 2020-01-01 (safe historical default; real data already has correct values).

import uuid
from datetime import date
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("liquidaciones", "0020_remove_tarifaporcentajeobra_especialidad"),
    ]

    operations = [
        # ── LiquidacionEspecialidadDisponibles (VigenciaModel: periodo_inicio, periodo_fin) ──
        migrations.AddField(
            model_name="liquidacionespecialidaddisponibles",
            name="periodo_fin",
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name="Periodo de Fin",
            ),
        ),
        migrations.AddField(
            model_name="liquidacionespecialidaddisponibles",
            name="periodo_inicio",
            field=models.DateField(
                default=date(2020, 1, 1),
                verbose_name="Periodo de Inicio",
            ),
            preserve_default=False,
        ),
        # ── LiquidacionDelegado (especialidad_revision FK) ──
        migrations.AddField(
            model_name="liquidaciondelegado",
            name="especialidad_revision",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="liquidacion_delegados",
                to="usuarios.especialidadrevision",
                verbose_name="Especialidad de Revision",
            ),
        ),
        # ── Historical models ──
        migrations.AddField(
            model_name="historicalliquidacionespecialidaddisponibles",
            name="periodo_fin",
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name="Periodo de Fin",
            ),
        ),
        migrations.AddField(
            model_name="historicalliquidacionespecialidaddisponibles",
            name="periodo_inicio",
            field=models.DateField(
                default=date(2020, 1, 1),
                verbose_name="Periodo de Inicio",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="historicalliquidaciondelegado",
            name="especialidad_revision",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="usuarios.especialidadrevision",
                verbose_name="Especialidad de Revision",
            ),
        ),
    ]
