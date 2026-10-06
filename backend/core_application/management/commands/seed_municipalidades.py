"""
Management command to seed Municipalidades from catalogos/municipalidades.json.

Por cada entrada: resuelve UbigeoDistrito por ubigeo (si no es null);
Municipalidad.objects.update_or_create(codigo=..., defaults={nombre, distrito}).
Si ubigeo es null, crear sin distrito (distrito=None).

Uso:
    python manage.py seed_municipalidades --settings=config.settings.development
    python manage.py seed_municipalidades --dry-run --settings=config.settings.development
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.entidades.domain.models import Municipalidad, UbigeoDistrito


class Command(BaseCommand):
    help = "Seed Municipalidades from catalogos/municipalidades.json and municipalidades_operativas_extra.json"

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds" / "catalogos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )

    def _load_municipalidades_from_file(self, filepath: Path) -> list:
        """Load municipalidades list from a JSON seed file."""
        if not filepath.exists():
            raise FileNotFoundError(f"No se encontró {filepath}")
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("municipalidades", [])

    def _process_file(self, filepath: Path, dry_run: bool):
        """Process a single municipalidades seed file. Returns (creados, actualizados, skipped_ubigeo, ubigeo_not_found)."""
        municipalidades = self._load_municipalidades_from_file(filepath)
        creados = 0
        actualizados = 0
        skipped_ubigeo = 0
        ubigeo_not_found = []

        for item in municipalidades:
            codigo = item["codigo"]
            nombre = item["nombre"]
            ubigeo = item.get("ubigeo")  # 6-digit string or null

            # Resolve UbigeoDistrito by ubigeo
            distrito = None
            if ubigeo:
                distrito = UbigeoDistrito.objects.filter(ubigeo=ubigeo).first()
                if not distrito:
                    ubigeo_not_found.append((codigo, nombre, ubigeo))

            if dry_run:
                if distrito:
                    self.stdout.write(
                        f"  [DRY] {codigo} -> {nombre} | ubigeo={ubigeo} | distrito={distrito.nombre} (id={distrito.id})"
                    )
                elif ubigeo:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [DRY] [WARN] {codigo}: ubigeo {ubigeo} no encontrado para {nombre}"
                        )
                    )
                else:
                    self.stdout.write(f"  [DRY] {codigo} -> {nombre} (sin ubigeo)")
                continue

            defaults = {"nombre": nombre}
            if distrito:
                defaults["distrito"] = distrito

            mun, created = Municipalidad.objects.update_or_create(
                codigo=codigo,
                defaults=defaults,
            )
            if created:
                creados += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  [CREADO] {codigo}: {nombre}")
                )
            else:
                actualizados += 1
                self.stdout.write(f"  [ACTUALIZADO] {codigo}: {nombre}")

            if not ubigeo:
                skipped_ubigeo += 1

        return creados, actualizados, skipped_ubigeo, ubigeo_not_found

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        seed_file = self.SEEDS_DIR / "municipalidades.json"
        extra_file = self.SEEDS_DIR / "municipalidades_operativas_extra.json"

        # Load main catalog
        try:
            main_mun = self._load_municipalidades_from_file(seed_file)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"No se encontró {seed_file}"))
            return

        # Process main catalog first
        self.stdout.write(f"Procesando archivo principal: {seed_file.name}")
        c1, a1, s1, unf1 = self._process_file(seed_file, dry_run)

        # Process extra file (required - error if missing or malformed)
        if extra_file.exists():
            self.stdout.write(f"Procesando archivo extra: {extra_file.name}")
            try:
                c2, a2, s2, unf2 = self._process_file(extra_file, dry_run)
                creados = c1 + c2
                actualizados = a1 + a2
                skipped_ubigeo = s1 + s2
                ubigeo_not_found = unf1 + unf2
            except (json.JSONDecodeError, KeyError) as e:
                self.stdout.write(self.style.ERROR(f"Archivo extra malformed: {extra_file} - {e}"))
                return
        else:
            self.stdout.write(self.style.ERROR(f"Archivo extra requerido no encontrado: {extra_file}"))
            return

        if ubigeo_not_found:
            for codigo, nombre, ubigeo in ubigeo_not_found:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [WARN] {codigo}: ubigeo '{ubigeo}' no encontrado para '{nombre}'"
                    )
                )

        if dry_run:
            total = len(main_mun) + 5  # 5 extra entries
            self.stdout.write(
                self.style.WARNING(
                    f"DRY-RUN: {total} municipalidades validadas."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Municipalidades: {creados} creadas, {actualizados} actualizadas, "
                    f"{skipped_ubigeo} sin ubigeo."
                )
            )
