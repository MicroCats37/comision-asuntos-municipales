"""
Comando para sembrar las tasas de delegado vigentes.

Las tasas por defecto (vigentes "desde siempre"):
    - renta_cip: 0.25 (25%)
    - aporte_codemu: 0.05 (5%)
    - fondo_comun: 0.10 (10%)
    - periodo_inicio: 1900-01-01
    - periodo_fin: NULL (vigente)
"""
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from modules.finanzas.domain.models.tasa_delegado import TasaDelegado


class Command(BaseCommand):
    help = "Siembra las tasas de delegado vigentes (vigencia desde 1900)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        tasa_nombre = "Tasas Delegado (vigencia histórica)"
        periodo_inicio = date(1900, 1, 1)
        renta_cip = Decimal("0.25")
        aporte_codemu = Decimal("0.05")
        fondo_comun = Decimal("0.10")

        if dry_run:
            existing = TasaDelegado.objects.filter(
                periodo_inicio=periodo_inicio,
                periodo_fin__isnull=True,
            ).first()
            if existing:
                self.stdout.write(
                    f"  [DRY-RUN] TasaDelegado({periodo_inicio}) -> ya existe "
                    f"(renta_cip={existing.renta_cip}, aporte_codemu={existing.aporte_codemu}, "
                    f"fondo_comun={existing.fondo_comun})"
                )
            else:
                self.stdout.write(
                    f"  [DRY-RUN] TasaDelegado({periodo_inicio}) -> CREAR "
                    f"(renta_cip={renta_cip}, aporte_codemu={aporte_codemu}, fondo_comun={fondo_comun})"
                )
            return

        tasa, created = TasaDelegado.objects.update_or_create(
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
                    f"TasaDelegado creada: periodo_inicio={periodo_inicio}, "
                    f"renta_cip={renta_cip}, aporte_codemu={aporte_codemu}, fondo_comun={fondo_comun}"
                )
            )
        else:
            self.stdout.write(
                f"TasaDelegado ya existía (periodo_inicio={periodo_inicio}) — actualizada"
            )
