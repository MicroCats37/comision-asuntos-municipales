"""
Comando para sembrar colegiados (PerfilIngeniero + Especialidad + Capitulo + IngenieroHabilitacion)
desde seeds/colegiados_reales.json (materializado desde el endpoint CIP).

Idempotente: usa get_or_create por cip.

Uso:
    python manage.py seed_colegiados --settings=config.settings.development
    python manage.py seed_colegiados --dry-run --settings=config.settings.development
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.usuarios.domain.models.perfil_ingeniero import (
    Capitulo,
    EspecialidadIngeniero,
    PerfilIngeniero,
    IngenieroHabilitacion,
)


class Command(BaseCommand):
    help = "Siembra colegiados (PerfilIngeniero) desde seeds/colegiados_reales.json"

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "liquidaciones" / "seeds"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos.",
        )
        parser.add_argument(
            "--seed-path",
            type=Path,
            default=None,
            help="Ruta alternativa al JSON de colegiados.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        seed_file = options["seed_path"] or (self.SEEDS_DIR / "colegiados_reales.json")

        if not seed_file.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {seed_file}"))
            return

        with open(seed_file, encoding="utf-8") as f:
            data = json.load(f)

        colegiados = data.get("colegiados", [])
        creados = 0
        actualizados = 0
        especialidades = set()
        capitulos = set()

        for item in colegiados:
            cip = item["cip"]

            # Capitulo (get_or_create por registro_id)
            capitulo = None
            cap_raw = item.get("capitulo") or {}
            if cap_raw.get("registro_id"):
                cap_defaults = {
                    "abreviacion": cap_raw.get("abreviacion", ""),
                    "nombre": cap_raw.get("nombre", ""),
                    "grupo_envio_intitucional": cap_raw.get("grupo_envio_intitucional", ""),
                }
                capitulo, _ = Capitulo.objects.get_or_create(
                    registro_id=cap_raw["registro_id"],
                    defaults=cap_defaults,
                )
                capitulos.add(cap_raw["registro_id"])

            # EspecialidadIngeniero (codigo + capitulo para distinguir Civil vs Sanitaria con codigo 01)
            cod_esp = item.get("codigo_especialidad", "")
            especialidad = None
            if cod_esp and capitulo:
                # Unique key: (codigo, capitulo) — permite mismo codigo en capitulos diferentes
                especialidad, _ = EspecialidadIngeniero.objects.get_or_create(
                    codigo=cod_esp,
                    capitulo=capitulo,
                    defaults={"nombre": cod_esp},
                )
                especialidades.add((cod_esp, capitulo.registro_id))

            perfil_defaults = {
                "dni": item.get("dni", ""),
                "nombres": item.get("nombres", ""),
                "apellido_paterno": item.get("apellido_paterno", ""),
                "apellido_materno": item.get("apellido_materno", ""),
                "fecha_nacimiento": item.get("fecha_nacimiento") or None,
                "genero": item.get("genero", ""),
                "correo_personal": item.get("correo_personal") or None,
                "correo_institucional": item.get("correo_institucional") or None,
                "celular": item.get("celular") or None,
                "direccion": item.get("direccion") or None,
                "ubigeo": item.get("ubigeo") or None,
                "especialidad": especialidad,
                "capitulo": capitulo,
            }

            if dry_run:
                self.stdout.write(f"[DRY] CIP {cip}: {item.get('nombres', '')} {item.get('apellido_paterno', '')}")
                continue

            perfil, was_created = PerfilIngeniero.objects.get_or_create(
                cip=cip,
                defaults=perfil_defaults,
            )
            if not was_created:
                # Actualizar campos (sin tocar usuario)
                for k, v in perfil_defaults.items():
                    setattr(perfil, k, v)
                perfil.save()
                actualizados += 1
            else:
                creados += 1

            # IngenieroHabilitacion
            hab = item.get("habilitacion") or {}
            if hab.get("condicion_cip") or hab.get("ultimo_periodo_pagado_cip"):
                IngenieroHabilitacion.objects.update_or_create(
                    perfil_ingeniero=perfil,
                    fecha_busqueda=None,
                    defaults={
                        "condicion_cip": hab.get("condicion_cip"),
                        "ultimo_periodo_pagado_cip": hab.get("ultimo_periodo_pagado_cip"),
                    },
                )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: {len(colegiados)} colegiados validados | "
                    f"{len(especialidades)} especialidades | {len(capitulos)} capitulos"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Colegiados: {creados} creados, {actualizados} actualizados | "
                    f"{len(especialidades)} especialidades | {len(capitulos)} capitulos"
                )
            )
