"""
Management command to seed EspecialidadRevision + EspecialidadRevisionCapitulo
from catalogos/especialidades_revision.json.

Por cada especialidad: update_or_create EspecialidadRevision por slug.
Luego, por cada capitulo registro_id en la lista, create EspecialidadRevisionCapitulo
(get_or_create por especialidad_revision + capitulo).

Nota: los slugs del JSON son EXACTOS: "ingenier-a-el-ctrica-y-mec-nica-el-ctrica",
"ingenier-a-electr-nica", etc. No normalizar — usar tal como están.

Uso:
    python manage.py seed_especialidades_revision --settings=config.settings.development
    python manage.py seed_especialidades_revision --dry-run --settings=config.settings.development
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.usuarios.domain.models.perfil_ingeniero import (
    Capitulo,
    EspecialidadRevision,
    EspecialidadRevisionCapitulo,
)


class Command(BaseCommand):
    help = "Seed EspecialidadRevision + EspecialidadRevisionCapitulo from catalogos/especialidades_revision.json"

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds" / "catalogos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        seed_file = self.SEEDS_DIR / "especialidades_revision.json"
        if not seed_file.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {seed_file}"))
            return

        with open(seed_file, encoding="utf-8") as f:
            data = json.load(f)

        especialidades = data.get("especialidades", [])
        esp_creados = 0
        esp_actualizados = 0
        capitulo_links_creados = 0
        capitulo_links_existen = 0
        capitulo_inexistentes = []

        for esp_data in especialidades:
            slug = esp_data["slug"]
            nombre = esp_data["nombre"]
            capitulos_ids = esp_data.get("capitulos", [])

            # ── EspecialidadRevision ─────────────────────────────────────────
            esp_obj = None
            if dry_run:
                existing = EspecialidadRevision.objects.filter(slug=slug).first()
                if existing:
                    self.stdout.write(
                        f"  [DRY-RUN] EspecialidadRevision {slug} -> ya existe: {nombre}"
                    )
                    esp_obj = existing
                else:
                    self.stdout.write(
                        f"  [DRY-RUN] EspecialidadRevision {slug} -> CREAR: {nombre}"
                    )
                    esp_obj = type("MockEsp", (), {"slug": slug, "id": None, "nombre": nombre})()
            else:
                esp_obj, created = EspecialidadRevision.objects.update_or_create(
                    slug=slug,
                    defaults={"nombre": nombre},
                )
                if created:
                    esp_creados += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  [CREADO] EspecialidadRevision: {slug} = {nombre}")
                    )
                else:
                    esp_actualizados += 1
                    self.stdout.write(f"  [ACTUALIZADO] EspecialidadRevision: {slug} = {nombre}")

            # ── EspecialidadRevisionCapitulo ────────────────────────────────────
            for reg_id in capitulos_ids:
                capitulo = Capitulo.objects.filter(registro_id=reg_id).first()

                if not capitulo:
                    capitulo_inexistentes.append((slug, reg_id))
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  [DRY-RUN] [WARN] Capitulo {reg_id} no existe para {slug}"
                            )
                        )
                    continue

                if dry_run:
                    existing_link = EspecialidadRevisionCapitulo.objects.filter(
                        especialidad_revision__slug=slug,
                        capitulo=capitulo,
                    ).exists()
                    if existing_link:
                        self.stdout.write(
                            f"  [DRY-RUN] EspecialidadRevisionCapitulo {slug} x {reg_id} -> ya existe"
                        )
                    else:
                        self.stdout.write(
                            f"  [DRY-RUN] EspecialidadRevisionCapitulo {slug} x {reg_id} -> CREAR"
                        )
                    continue

                link, created = EspecialidadRevisionCapitulo.objects.get_or_create(
                    especialidad_revision=esp_obj,
                    capitulo=capitulo,
                )
                if created:
                    capitulo_links_creados += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [CREADO] EspecialidadRevisionCapitulo: {slug} <-> {reg_id}"
                        )
                    )
                else:
                    capitulo_links_existen += 1

        if capitulo_inexistentes and not dry_run:
            for slug, reg_id in capitulo_inexistentes:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [WARN] Capitulo {reg_id} no existe — saltado para {slug}"
                    )
                )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY-RUN: {len(especialidades)} especialidades validadas, "
                    f"{sum(len(e.get('capitulos', [])) for e in especialidades)} capitulo links."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Especialidades: {esp_creados} creadas, {esp_actualizados} actualizadas.\n"
                    f"Capitulo links: {capitulo_links_creados} creados, {capitulo_links_existen} ya existian."
                )
            )
