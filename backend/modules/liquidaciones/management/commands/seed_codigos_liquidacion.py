"""
Comando para sembrar los códigos de cuenta (LiquidacionCodigo) por tipo de liquidación.

Pobla una fila de LiquidacionCodigo por cada uno de los 6 tipos canónicos:
    - EDIFICACION: 46201
    - HABILITACION_URBANA: 703179999
    - INSPECCION_OBRA: 462021
    - TALUDES: 7032018
    - IMPACTO_VIAL: 46201
    - MECANICA_SUELOS: 46201

Idempotente: update_or_create sobre (tipo_liquidacion).
Uso:
    python manage.py seed_codigos_liquidacion --settings=config.settings.development
    python manage.py seed_codigos_liquidacion --dry-run --settings=config.settings.development
"""
from django.core.management.base import BaseCommand

from modules.liquidaciones.domain.constants import TipoLiquidacion as TipoLiquidacionConst
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionCodigo,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion


# Codigo canónico → codigo_cta de cuenta contable.
CODIGOS_POR_TIPO = [
    (TipoLiquidacionConst.EDIFICACION, "46201"),
    (TipoLiquidacionConst.HABILITACION_URBANA, "703179999"),
    (TipoLiquidacionConst.INSPECCION_OBRA, "462021"),
    (TipoLiquidacionConst.TALUDES, "7032018"),
    (TipoLiquidacionConst.IMPACTO_VIAL, "46201"),
    (TipoLiquidacionConst.MECANICA_SUELOS, "46201"),
]


class Command(BaseCommand):
    help = "Siembra los códigos de cuenta (LiquidacionCodigo) por tipo de liquidación."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        creados = 0
        actualizados = 0

        for codigo, codigo_cta in CODIGOS_POR_TIPO:
            tipo, _ = TipoLiquidacion.objects.get_or_create(
                codigo=codigo, defaults={"nombre": TipoLiquidacionConst(codigo).label}
            )

            if dry_run:
                existing = LiquidacionCodigo.objects.filter(
                    tipo_liquidacion=tipo, codigo_cta=codigo_cta
                ).first()
                if existing:
                    self.stdout.write(f"  [DRY-RUN] {codigo} -> ya existe ({codigo_cta})")
                else:
                    self.stdout.write(f"  [DRY-RUN] {codigo} -> CREAR ({codigo_cta})")
                continue

            _, created = LiquidacionCodigo.objects.update_or_create(
                tipo_liquidacion=tipo,
                defaults={"codigo_cta": codigo_cta},
            )
            if created:
                creados += 1
            else:
                actualizados += 1

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: No se escribió en la base de datos."))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"LiquidacionCodigo: {creados} creados, {actualizados} actualizados"
            )
        )
