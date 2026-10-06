"""
Comando para sembrar las tasas de delegado desde
core_application/seeds/catalogos/tasas_delegado.json.

Cada tasa tiene vigencia (periodo_inicio/periodo_fin) y valores propios
por tipo de liquidación (renta_cip, aporte_codemu, fondo_comun).
"""
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from modules.liquidaciones.domain.constants import (
    TipoLiquidacion as TipoLiquidacionConst,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
from modules.finanzas.domain.models.tasa_delegado import TasaDelegado


# Código canónico → nombre legible (para get_or_create del TipoLiquidacion).
NOMBRES = {
    TipoLiquidacionConst.EDIFICACION: "Edificaciones",
    TipoLiquidacionConst.HABILITACION_URBANA: "Habilitación Urbana",
    TipoLiquidacionConst.MECANICA_SUELOS: "Mecánica de Suelos",
    TipoLiquidacionConst.IMPACTO_VIAL: "Impacto Vial",
    TipoLiquidacionConst.TALUDES: "Taludes",
    TipoLiquidacionConst.INSPECCION_OBRA: "Inspección de Obra",
}


class Command(BaseCommand):
    help = "Siembra las tasas de delegado desde catalogos/tasas_delegado.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        seed_file = (
            Path(settings.BASE_DIR)
            / "core_application"
            / "seeds"
            / "catalogos"
            / "tasas_delegado.json"
        )
        if not seed_file.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {seed_file}"))
            return

        with open(seed_file, encoding="utf-8") as f:
            data = json.load(f)

        creadas = 0
        actualizadas = 0

        for item in data["tasas_delegado"]:
            codigo = item["tipo_liquidacion"]
            periodo_inicio = date.fromisoformat(item["periodo_inicio"])
            periodo_fin = (
                None if item["periodo_fin"] is None else date.fromisoformat(item["periodo_fin"])
            )
            renta_cip = Decimal(item["renta_cip"])
            aporte_codemu = Decimal(item["aporte_codemu"])
            fondo_comun = Decimal(item["fondo_comun"])

            nombre = NOMBRES.get(codigo, codigo.replace("_", " ").title())
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
                    actualizadas += 1
                else:
                    self.stdout.write(
                        f"  [DRY-RUN] {tipo.nombre} -> CREAR "
                        f"(renta_cip={renta_cip}, aporte_codemu={aporte_codemu}, fondo_comun={fondo_comun})"
                    )
                    creadas += 1
                continue

            _, created = TasaDelegado.objects.update_or_create(
                tipo_liquidacion=tipo,
                periodo_inicio=periodo_inicio,
                defaults={
                    "nombre": tasa_nombre,
                    "renta_cip": renta_cip,
                    "aporte_codemu": aporte_codemu,
                    "fondo_comun": fondo_comun,
                    "periodo_fin": periodo_fin,
                },
            )

            if created:
                creadas += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"TasaDelegado creada: {tipo.nombre}, "
                        f"periodo_inicio={periodo_inicio}, "
                        f"renta_cip={renta_cip}, aporte_codemu={aporte_codemu}, fondo_comun={fondo_comun}"
                    )
                )
            else:
                actualizadas += 1
                self.stdout.write(
                    f"TasaDelegado ya existía ({tipo.nombre}, periodo_inicio={periodo_inicio}) — actualizada"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"TasaDelegado: {creadas} creadas, {actualizadas} actualizadas"
            )
        )
