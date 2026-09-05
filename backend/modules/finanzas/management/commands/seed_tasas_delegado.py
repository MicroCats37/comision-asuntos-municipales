"""
Comando para sembrar las tasas de delegado vigentes, una por tipo de liquidación.

Replica la misma tasa por defecto (vigente "desde siempre") para cada uno de los
6 tipos de liquidación canónicos:
    - renta_cip: 0.25 (25%)
    - aporte_codemu: 0.05 (5%)
    - fondo_comun: 0.10 (10%)
    - periodo_inicio: 1900-01-01
    - periodo_fin: NULL (vigente)

Garantiza que las 6 filas TipoLiquidacion existan (get_or_create por codigo).
"""
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from modules.liquidaciones.domain.constants import (
    TipoLiquidacion as TipoLiquidacionConst,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
from modules.finanzas.domain.models.tasa_delegado import TasaDelegado


# Codigo canónico → nombre legible de los 6 tipos de liquidación.
TIPOS = [
    (TipoLiquidacionConst.EDIFICACION, "Edificaciones"),
    (TipoLiquidacionConst.HABILITACION_URBANA, "Habilitación Urbana"),
    (TipoLiquidacionConst.MECANICA_SUELOS, "Mecánica de Suelos"),
    (TipoLiquidacionConst.IMPACTO_VIAL, "Impacto Vial"),
    (TipoLiquidacionConst.TALUDES, "Taludes"),
    (TipoLiquidacionConst.INSPECCION_OBRA, "Inspección de Obra"),
]


class Command(BaseCommand):
    help = "Siembra las tasas de delegado vigentes (vigencia desde 1900) por tipo de liquidación."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        periodo_inicio = date(1900, 1, 1)
        renta_cip = Decimal("0.25")
        aporte_codemu = Decimal("0.05")
        fondo_comun = Decimal("0.10")

        for codigo, nombre in TIPOS:
            # Asegurar que la fila TipoLiquidacion existe (no modifica el nombre
            # si la fila ya existe por codigo).
            tipo, _ = TipoLiquidacion.objects.get_or_create(
                codigo=codigo, defaults={"nombre": nombre}
            )
            tasa_nombre = f"Tasas Delegado {tipo.nombre} (vigencia histórica)"

            if dry_run:
                existing = TasaDelegado.objects.filter(
                    tipo_liquidacion=tipo,
                    periodo_inicio=periodo_inicio,
                    periodo_fin__isnull=True,
                ).first()
                if existing:
                    self.stdout.write(
                        f"  [DRY-RUN] {tipo.nombre} -> ya existe "
                        f"(renta_cip={existing.renta_cip}, aporte_codemu={existing.aporte_codemu}, "
                        f"fondo_comun={existing.fondo_comun})"
                    )
                else:
                    self.stdout.write(
                        f"  [DRY-RUN] {tipo.nombre} -> CREAR "
                        f"(renta_cip={renta_cip}, aporte_codemu={aporte_codemu}, fondo_comun={fondo_comun})"
                    )
                continue

            tasa, created = TasaDelegado.objects.update_or_create(
                tipo_liquidacion=tipo,
                periodo_inicio=periodo_inicio,
                defaults={
                    "nombre": tasa_nombre,
                    "renta_cip": renta_cip,
                    "aporte_codemu": aporte_codemu,
                    "fondo_comun": fondo_comun,
                    "periodo_fin": None,
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"TasaDelegado creada: {tipo.nombre}, "
                        f"periodo_inicio={periodo_inicio}, "
                        f"renta_cip={renta_cip}, aporte_codemu={aporte_codemu}, fondo_comun={fondo_comun}"
                    )
                )
            else:
                self.stdout.write(
                    f"TasaDelegado ya existía ({tipo.nombre}, periodo_inicio={periodo_inicio}) — actualizada"
                )