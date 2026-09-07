"""
Comando para sembrar tarifas CIP CAM enrichecidas desde seeds/tarifas_enriquecido.json.

Carga:
- DerechoPorcentajeObra (global)
- DerechoPorMetroCuadrado (global)
- TarifaLiquidacionBase + TarifaPorcentajeObra (EDIFICACION legacy + current, IV, Taludes)
- TarifaLiquidacionBase + TarifaPorMetroCuadrado (HU, MS)
- TarifaLiquidacionBase + TarifaPorCategoriaVisitas (IO x4 categorias)
- LiquidacionEspecialidadDisponibles bridge (EDIFICACION: legacy 4 esp + current 3; IV, TALUDES x 3)

Idempotente: update_or_create por (tipo_liquidacion, periodo_inicio) para bases;
update_or_create por (tarifa_base) para detalles;
get_or_create por (tipo_liquidacion, especialidad) para el bridge.

Uso:
    python manage.py seed_tarifas_enriquecido --settings=config.settings.development
    python manage.py seed_tarifas_enriquecido --dry-run --settings=config.settings.development
    python manage.py seed_tarifas_enriquecido --seed-path=custom/path.json --settings=config.settings.development
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    TarifaPorMetroCuadrado,
    TarifaPorCategoriaVisitas,
    DerechoPorcentajeObra,
    DerechoPorMetroCuadrado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionEspecialidadDisponibles,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision


class Command(BaseCommand):
    help = "Siembra tarifas CIP CAM enrichecidas desde seeds/tarifas_enriquecido.json"

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds"

    def _log(self, msg: str):
        """Escribe a stdout manejando codificacion en Windows (cp1252)."""
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
            safe_msg = msg.encode("ascii", "replace").decode("ascii")
            self.stdout.write(safe_msg)

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en base de datos.",
        )
        parser.add_argument(
            "--seed-path",
            type=Path,
            default=None,
            help="Ruta alternativa al JSON de tarifas.",
        )

    def _get_or_create_tipo(self, codigo: str, label: str) -> TipoLiquidacion:
        """Obtiene o crea un TipoLiquidacion por codigo."""
        tipo, _ = TipoLiquidacion.objects.get_or_create(
            codigo=codigo,
            defaults={"nombre": label},
        )
        return tipo

    def _get_or_create_especialidad(self, nombre: str, dry_run: bool = False) -> EspecialidadRevision:
        """Obtiene o crea una EspecialidadRevision por nombre (match por nombre, fallback slug)."""
        import re

        # 1) Match por nombre exacto (nombre canónico: "Ingeniería Eléctrica y Mecánica Eléctrica").
        esp = EspecialidadRevision.objects.filter(nombre=nombre).first()
        if esp:
            return esp

        # 2) Fallback por slug normalizado (para nombres que existen con otro acento/formato).
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", nombre).lower().strip("-")
        esp = EspecialidadRevision.objects.filter(slug=slug).first()
        if esp:
            return esp

        if dry_run:
            self._log(f"  [DRY] Would create EspecialidadRevision: {nombre} (slug={slug})")
            # Return a mock-like object for dry-run traversal (not persisted)
            from types import SimpleNamespace
            return SimpleNamespace(id=None, slug=slug, nombre=nombre)
        esp = EspecialidadRevision.objects.create(slug=slug, nombre=nombre)
        self._log(f"  [CREATED] EspecialidadRevision: {nombre} (slug={slug})")
        return esp

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        seed_file = options["seed_path"] or (self.SEEDS_DIR / "tarifas_enriquecido.json")

        if not seed_file.exists():
            self._log(self.style.ERROR(f"No se encontro {seed_file}"))
            return

        with open(seed_file, encoding="utf-8") as f:
            data = json.load(f)

        counts = {
            "bases": 0,
            "porcentaje": 0,
            "m2": 0,
            "visitas": 0,
            "derechos": 0,
            "especialidades_bridge": 0,
        }

        # ── Derechos globales ───────────────────────────────────────────────────
        dp = data.get("derechos_porcentaje", {})
        dm = data.get("derechos_m2", {})

        self._log("=== Derechos globales ===")
        if not dry_run:
            DerechoPorcentajeObra.objects.update_or_create(
                periodo_inicio=date.fromisoformat(dp["periodo_inicio"]),
                defaults={
                    "periodo_fin": (
                        date.fromisoformat(dp["periodo_fin"])
                        if dp.get("periodo_fin")
                        else None
                    ),
                    "porcentaje_minimo_uit": Decimal(dp["porcentaje_minimo_uit"]),
                    "derecho_minimo": (
                        Decimal(dp["derecho_minimo"]) if dp.get("derecho_minimo") else None
                    ),
                    "derecho_maximo": (
                        Decimal(dp["derecho_maximo"]) if dp.get("derecho_maximo") else None
                    ),
                },
            )
            counts["derechos"] += 1
            self._log(f"  [OK] DerechoPorcentajeObra: {dp['periodo_inicio']}")

            DerechoPorMetroCuadrado.objects.update_or_create(
                periodo_inicio=date.fromisoformat(dm["periodo_inicio"]),
                defaults={
                    "periodo_fin": (
                        date.fromisoformat(dm["periodo_fin"])
                        if dm.get("periodo_fin")
                        else None
                    ),
                    "derecho_minimo": Decimal(dm["derecho_minimo"]),
                    "derecho_maximo": (
                        Decimal(dm["derecho_maximo"]) if dm.get("derecho_maximo") else None
                    ),
                },
            )
            counts["derechos"] += 1
            self._log(f"  [OK] DerechoPorMetroCuadrado: {dm['periodo_inicio']}")

        # ── Tarifas de porcentaje ───────────────────────────────────────────────
        self._log("\n=== Tarifas porcentaje ===")
        for item in data.get("tarifas_porcentaje", []):
            tipo = self._get_or_create_tipo(item["tipo_liquidacion"], item["tipo_liquidacion"].replace("_", " ").title())
            inicio = date.fromisoformat(item["periodo_inicio"])
            fin = date.fromisoformat(item["periodo_fin"]) if item.get("periodo_fin") else None

            if dry_run:
                self._log(
                    f"  [DRY] % {item['tipo_liquidacion']} "
                    f"{item['periodo_inicio']} → {item.get('periodo_fin') or 'null'} "
                    f"{item['porcentaje_liquidacion']}"
                )
                continue

            base, base_created = TarifaLiquidacionBase.objects.update_or_create(
                tipo_liquidacion=tipo,
                periodo_inicio=inicio,
                defaults={"periodo_fin": fin},
            )
            counts["bases"] += 1
            if base_created:
                self._log(f"  [CREATED] TarifaLiquidacionBase: {tipo.codigo} {inicio}")

            TarifaPorcentajeObra.objects.update_or_create(
                tarifa_base=base,
                defaults={"porcentaje_liquidacion": Decimal(item["porcentaje_liquidacion"])},
            )
            counts["porcentaje"] += 1
            self._log(
                f"  [OK] TarifaPorcentajeObra: {tipo.codigo} {inicio} → "
                f"{item['porcentaje_liquidacion']}"
            )

        # ── Tarifas M2 ─────────────────────────────────────────────────────────
        self._log("\n=== Tarifas M2 ===")
        for item in data.get("tarifas_m2", []):
            tipo = self._get_or_create_tipo(item["tipo_liquidacion"], item["tipo_liquidacion"].replace("_", " ").title())
            inicio = date.fromisoformat(item["periodo_inicio"])
            fin = date.fromisoformat(item["periodo_fin"]) if item.get("periodo_fin") else None

            if dry_run:
                self._log(
                    f"  [DRY] M2 {item['tipo_liquidacion']} "
                    f"{item['periodo_inicio']} → {item.get('periodo_fin') or 'null'} "
                    f"{item['costo_por_m2']}/m2"
                )
                continue

            base, base_created = TarifaLiquidacionBase.objects.update_or_create(
                tipo_liquidacion=tipo,
                periodo_inicio=inicio,
                defaults={"periodo_fin": fin},
            )
            counts["bases"] += 1
            if base_created:
                self._log(f"  [CREATED] TarifaLiquidacionBase: {tipo.codigo} {inicio}")

            TarifaPorMetroCuadrado.objects.update_or_create(
                tarifa_base=base,
                defaults={"costo_por_m2": Decimal(item["costo_por_m2"])},
            )
            counts["m2"] += 1
            self._log(
                f"  [OK] TarifaPorMetroCuadrado: {tipo.codigo} {inicio} → "
                f"{item['costo_por_m2']}/m2"
            )

        # ── Tarifas de inspeccion (visitas) ────────────────────────────────────
        self._log("\n=== Tarifas visitas ===")
        for item in data.get("tarifas_visitas", []):
            tipo = self._get_or_create_tipo(item["tipo_liquidacion"], item["tipo_liquidacion"].replace("_", " ").title())
            inicio = date.fromisoformat(item["periodo_inicio"])
            fin = date.fromisoformat(item["periodo_fin"]) if item.get("periodo_fin") else None
            categoria = item["categoria"]  # "1"-"4"

            if dry_run:
                self._log(
                    f"  [DRY] Visitas {item['tipo_liquidacion']} cat {categoria} "
                    f"{item['porcentaje_uit']} UIT"
                )
                continue

            base, base_created = TarifaLiquidacionBase.objects.update_or_create(
                tipo_liquidacion=tipo,
                periodo_inicio=inicio,
                defaults={"periodo_fin": fin},
            )
            counts["bases"] += 1
            if base_created:
                self._log(f"  [CREATED] TarifaLiquidacionBase: {tipo.codigo} {inicio}")

            TarifaPorCategoriaVisitas.objects.update_or_create(
                tarifa_base=base,
                categoria_visitas=categoria,
                defaults={"porcentaje_uit": Decimal(item["porcentaje_uit"])},
            )
            counts["visitas"] += 1
            self._log(
                f"  [OK] TarifaPorCategoriaVisitas: {tipo.codigo} cat {categoria} → "
                f"{item['porcentaje_uit']} UIT"
            )

        # ── Especialidades disponibles (bridge) ─────────────────────────────────
        self._log("\n=== Especialidades disponibles ===")
        esp_data = data.get("especialidades_disponibles", [])
        for entry in esp_data:
            tipo_codigo = entry["tipo_liquidacion"]
            esp_nombre = entry["especialidad"]
            inicio = date.fromisoformat(entry["periodo_inicio"])
            fin = date.fromisoformat(entry["periodo_fin"]) if entry.get("periodo_fin") else None

            tipo = self._get_or_create_tipo(tipo_codigo, tipo_codigo.replace("_", " ").title())
            esp = self._get_or_create_especialidad(esp_nombre, dry_run=dry_run)

            if dry_run:
                self._log(
                    f"  [DRY] LiquidacionEspecialidadDisponibles: "
                    f"{tipo_codigo} × {esp_nombre} [{inicio} → {fin or 'null'}]"
                )
                continue

            # update_or_create para respetar UniqueConstraint(tipo_liquidacion, especialidad).
            # Una sola fila por (tipo, especialidad); la vigencia se ajusta por periodo.
            bridge, created = LiquidacionEspecialidadDisponibles.objects.update_or_create(
                tipo_liquidacion=tipo,
                especialidad=esp,
                defaults={
                    "activo": True,
                    "periodo_inicio": inicio,
                    "periodo_fin": fin,
                },
            )
            if created:
                counts["especialidades_bridge"] += 1
                self._log(
                    f"  [CREATED] LiquidacionEspecialidadDisponibles: "
                    f"{tipo_codigo} × {esp_nombre} [{inicio} → {fin or 'null'}]"
                )
            else:
                self._log(
                    f"  [UPDATED] LiquidacionEspecialidadDisponibles: "
                    f"{tipo_codigo} × {esp_nombre} [{inicio} → {fin or 'null'}]"
                )

        # ── Resumen ────────────────────────────────────────────────────────────
        if dry_run:
            self._log(self.style.WARNING("\nDRY RUN: estructuras validadas, sin escritura."))
        else:
            self._log(
                self.style.SUCCESS(
                    f"\nTarifas enrichecidas cargadas: "
                    f"bases={counts['bases']} "
                    f"porcentaje={counts['porcentaje']} "
                    f"m2={counts['m2']} "
                    f"visitas={counts['visitas']} "
                    f"derechos={counts['derechos']} "
                    f"especialidades_bridge={counts['especialidades_bridge']}"
                )
            )
