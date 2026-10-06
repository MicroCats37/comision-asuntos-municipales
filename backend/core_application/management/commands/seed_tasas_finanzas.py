"""
Comando para sembrar las tasas de delegado y escalas de descuento de inspector
desde core_application/seeds/catalogos/.
"""
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from modules.liquidaciones.domain.constants import TipoLiquidacion as TipoLiquidacionConst
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
from modules.finanzas.domain.models.tasa_delegado import TasaDelegado
from modules.finanzas.domain.models.descuento_inspector import (
    EscalaDescuentoInspector,
    RangoDescuentoInspector,
)

# Código canónico → nombre legible (para get_or_create del TipoLiquidacion).
NOMBRES_TIPO = {
    TipoLiquidacionConst.EDIFICACION: "Edificaciones",
    TipoLiquidacionConst.HABILITACION_URBANA: "Habilitación Urbana",
    TipoLiquidacionConst.MECANICA_SUELOS: "Mecánica de Suelos",
    TipoLiquidacionConst.IMPACTO_VIAL: "Impacto Vial",
    TipoLiquidacionConst.TALUDES: "Taludes",
    TipoLiquidacionConst.INSPECCION_OBRA: "Inspección de Obra",
}

class Command(BaseCommand):
    help = "Siembra tasas de delegado y escalas de descuento desde seeds/catalogos/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        base_seeds_dir = Path(settings.BASE_DIR) / "core_application" / "seeds" / "catalogos"

        self.stdout.write(self.style.SUCCESS("--- Sembrando Tasas de Delegado ---"))
        self._seed_tasas_delegado(base_seeds_dir / "tasas_delegado.json", dry_run)

        self.stdout.write(self.style.SUCCESS("\n--- Sembrando Escala de Descuento Inspector ---"))
        self._seed_escala_inspector(base_seeds_dir / "escala_descuento_inspector.json", dry_run)

    def _seed_tasas_delegado(self, json_path: Path, dry_run: bool):
        if not json_path.exists():
            self.stdout.write(self.style.ERROR(f"Archivo no encontrado: {json_path}"))
            return

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        creadas, actualizadas = 0, 0

        for item in data.get("tasas_delegado", []):
            codigo = item["tipo_liquidacion"]
            periodo_inicio = date.fromisoformat(item["periodo_inicio"])
            periodo_fin = None if item.get("periodo_fin") is None else date.fromisoformat(item["periodo_fin"])
            
            renta_cip = Decimal(str(item["renta_cip"]))
            aporte_codemu = Decimal(str(item["aporte_codemu"]))
            fondo_comun = Decimal(str(item["fondo_comun"]))

            nombre_tipo = NOMBRES_TIPO.get(codigo, codigo.replace("_", " ").title())
            tipo, _ = TipoLiquidacion.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre_tipo})
            
            tasa_nombre = f"Tasas Delegado {tipo.nombre} (vigencia histórica)"

            if dry_run:
                existing = TasaDelegado.objects.filter(
                    tipo_liquidacion=tipo, periodo_inicio=periodo_inicio
                ).filter(periodo_fin__isnull=True).first()
                if existing:
                    self.stdout.write(f"  [DRY] TasaDelegado {codigo} ya existe")
                else:
                    self.stdout.write(f"  [DRY] TasaDelegado {codigo} a CREAR")
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
                self.stdout.write(self.style.SUCCESS(f"  [CREADA] TasaDelegado: {codigo}"))
            else:
                actualizadas += 1
                self.stdout.write(f"  [ACTUALIZADA] TasaDelegado: {codigo}")

        if not dry_run:
            self.stdout.write(f"Resumen Tasas: {creadas} creadas, {actualizadas} actualizadas.")

    def _seed_escala_inspector(self, json_path: Path, dry_run: bool):
        if not json_path.exists():
            self.stdout.write(self.style.ERROR(f"Archivo no encontrado: {json_path}"))
            return

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)

        escala_data = data.get("escala", {})
        if not escala_data:
            return

        nombre = escala_data["nombre"]
        periodo_inicio = date.fromisoformat(escala_data["periodo_inicio"])
        periodo_fin = None if escala_data.get("periodo_fin") is None else date.fromisoformat(escala_data["periodo_fin"])

        if dry_run:
            self.stdout.write(f"  [DRY] EscalaDescuentoInspector '{nombre}' validada.")
            return

        escala, created = EscalaDescuentoInspector.objects.update_or_create(
            nombre=nombre,
            defaults={
                "periodo_inicio": periodo_inicio,
                "periodo_fin": periodo_fin,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"  [CREADA] Escala: {nombre}"))
        else:
            self.stdout.write(f"  [ACTUALIZADA] Escala: {nombre}")

        creados, actualizados = 0, 0
        for rango in escala_data.get("rangos", []):
            m_min = Decimal(str(rango["monto_minimo"]))
            m_max = Decimal(str(rango["monto_maximo"])) if rango.get("monto_maximo") is not None else None
            pct = Decimal(str(rango["porcentaje_descuento"]))

            _, r_created = RangoDescuentoInspector.objects.update_or_create(
                escala=escala,
                monto_minimo=m_min,
                defaults={
                    "monto_maximo": m_max,
                    "porcentaje_descuento": pct,
                },
            )
            if r_created: creados += 1
            else: actualizados += 1

        self.stdout.write(f"Resumen Rangos: {creados} creados, {actualizados} actualizados.")
