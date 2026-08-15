"""
Comando para sembrar tarifas CAM desde seeds/tarifas_cam_2026.json.

Carga:
- DerechoPorcentajeObra (porcentaje_minimo_uit, global)
- DerechoPorMetroCuadrado (min/max, global)
- TarifaLiquidacionBase + TarifaPorcentajeObra (Edificacion x3 esp, IV, Taludes)
- TarifaLiquidacionBase + TarifaPorMetroCuadrado (HU, MS)
- TarifaLiquidacionBase + TarifaPorCategoriaVisitas (IO x4 categorias)

Idempotente: update_or_create por (tipo_liquidacion, periodo, especialidad/categoria).

Uso:
    python manage.py seed_tarifas --settings=config.settings.development
    python manage.py seed_tarifas --dry-run --settings=config.settings.development
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    TarifaPorMetroCuadrado,
    TarifaPorCategoriaVisitas,
    DerechoPorcentajeObra,
    DerechoPorMetroCuadrado,
)
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision as Especialidad


class Command(BaseCommand):
    help = "Siembra tarifas CAM desde seeds/tarifas_cam_2026.json"

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Validar sin escribir.")
        parser.add_argument(
            "--seed-path",
            type=Path,
            default=None,
            help="Ruta alternativa al JSON de tarifas.",
        )

    def _get_tipo(self, codigo: str) -> TipoLiquidacion:
        return TipoLiquidacion.objects.get(codigo=codigo)

    def _get_especialidad(self, codigo: str) -> Especialidad:
        """Devuelve la EspecialidadRevision por codigo; la crea si no existe."""
        esp = Especialidad.objects.filter(codigo=codigo).first()
        if esp:
            return esp
        # Crear la especialidad de revisión faltante (ej. codigo '04' de tarifas)
        return Especialidad.objects.create(codigo=codigo, nombre=codigo)

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        seed_file = options["seed_path"] or (self.SEEDS_DIR / "tarifas_cam_2026.json")

        if not seed_file.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {seed_file}"))
            return

        with open(seed_file, encoding="utf-8") as f:
            data = json.load(f)

        conteo = {"bases": 0, "porcentaje": 0, "m2": 0, "visitas": 0, "derechos": 0}

        # ── Derechos globales ──────────────────────────────────────────────
        dp = data.get("derechos_porcentaje", {})
        dm = data.get("derechos_m2", {})

        if not dry_run:
            derecho_po, _ = DerechoPorcentajeObra.objects.update_or_create(
                periodo_inicio=date.fromisoformat(dp["periodo_inicio"]),
                defaults={
                    "periodo_fin": date.fromisoformat(dp["periodo_fin"]) if dp.get("periodo_fin") else None,
                    "porcentaje_minimo_uit": Decimal(dp["porcentaje_minimo_uit"]),
                    "derecho_minimo": None,  # se calcula en runtime: UIT * porcentaje_minimo_uit
                },
            )
            conteo["derechos"] += 1

            derecho_m2, _ = DerechoPorMetroCuadrado.objects.update_or_create(
                periodo_inicio=date.fromisoformat(dm["periodo_inicio"]),
                defaults={
                    "periodo_fin": date.fromisoformat(dm["periodo_fin"]) if dm.get("periodo_fin") else None,
                    "derecho_minimo": Decimal(dm["derecho_minimo"]),
                    "derecho_maximo": Decimal(dm["derecho_maximo"]),
                },
            )
            conteo["derechos"] += 1

        # ── Tarifas de porcentaje ──────────────────────────────────────────
        # NUEVO: una sola TarifaPorcentajeObra por TarifaLiquidacionBase (sin especialidad).
        # Las especialidades disponibles se gestionan via LiquidacionEspecialidadDisponibles.
        for item in data.get("tarifas_porcentaje", []):
            tipo = self._get_tipo(item["tipo_liquidacion"])
            inicio = date.fromisoformat(item["periodo_inicio"])
            fin = date.fromisoformat(item["periodo_fin"]) if item.get("periodo_fin") else None

            if dry_run:
                self.stdout.write(
                    f"[DRY] % {item['tipo_liquidacion']} "
                    f"{item['porcentaje_liquidacion']}"
                )
                continue

            base, _ = TarifaLiquidacionBase.objects.update_or_create(
                tipo_liquidacion=tipo,
                periodo_inicio=inicio,
                periodo_fin=fin,
            )
            conteo["bases"] += 1

            # Una sola TarifaPorcentajeObra por base — sin especialidad FK.
            TarifaPorcentajeObra.objects.update_or_create(
                tarifa_base=base,
                defaults={"porcentaje_liquidacion": Decimal(item["porcentaje_liquidacion"])},
            )
            conteo["porcentaje"] += 1

        # ── Tarifas M2 ─────────────────────────────────────────────────────
        for item in data.get("tarifas_m2", []):
            tipo = self._get_tipo(item["tipo_liquidacion"])
            inicio = date.fromisoformat(item["periodo_inicio"])
            fin = date.fromisoformat(item["periodo_fin"]) if item.get("periodo_fin") else None

            if dry_run:
                self.stdout.write(
                    f"[DRY] M2 {item['tipo_liquidacion']} {item['costo_por_m2']}/m2"
                )
                continue

            base, _ = TarifaLiquidacionBase.objects.update_or_create(
                tipo_liquidacion=tipo,
                periodo_inicio=inicio,
                periodo_fin=fin,
            )
            conteo["bases"] += 1

            TarifaPorMetroCuadrado.objects.update_or_create(
                tarifa_base=base,
                defaults={"costo_por_m2": Decimal(item["costo_por_m2"])},
            )
            conteo["m2"] += 1

        # ── Tarifas de inspeccion (visitas) ────────────────────────────────
        for item in data.get("tarifas_inspeccion", []):
            tipo = self._get_tipo(item["tipo_liquidacion"])
            inicio = date.fromisoformat(item["periodo_inicio"])
            fin = date.fromisoformat(item["periodo_fin"]) if item.get("periodo_fin") else None

            if dry_run:
                self.stdout.write(
                    f"[DRY] Visitas {item['tipo_liquidacion']} cat {item['categoria_visitas']} "
                    f"{item['porcentaje_uit']} UIT"
                )
                continue

            base, _ = TarifaLiquidacionBase.objects.update_or_create(
                tipo_liquidacion=tipo,
                periodo_inicio=inicio,
                periodo_fin=fin,
            )
            conteo["bases"] += 1

            TarifaPorCategoriaVisitas.objects.update_or_create(
                tarifa_base=base,
                categoria_visitas=item["categoria_visitas"],
                defaults={"porcentaje_uit": Decimal(item["porcentaje_uit"])},
            )
            conteo["visitas"] += 1

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: tarifas validadas."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Tarifas cargadas: bases={conteo['bases']} "
                    f"porcentaje={conteo['porcentaje']} m2={conteo['m2']} "
                    f"visitas={conteo['visitas']} derechos={conteo['derechos']}"
                )
            )
