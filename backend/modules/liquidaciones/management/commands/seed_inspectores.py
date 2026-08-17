"""
Comando para sembrar inspectores desde seeds/inspectores_reales.json
(adaptado del seed alpha `load_inspectores_reales.py` al modelo nuevo).

Modelo nuevo (post-refactor):
    Inspector (perfil_ingeniero 1:1)
        └── InspectorTipoLiquidacion (inspector FK, tipo_liquidacion FK→TipoLiquidacion,
                                       categoria, numero_registro)
                └── InspectorAsignacionPeriodo (periodo_inicio, periodo_fin)

El JSON alpha trae registros por inspector con: cip, identidad (dni, nombres,
apellidos, correo, capitulo), registros[{numero_registro, categoria,
tipo_liquidacion, especialidad, vigencia}].

Mapeo:
    - InspectorTipoLiquidacion.tipo_liquidacion ← por codigo (EDIFICACION, HABILITACION_URBANA)
    - InspectorTipoLiquidacion.categoria ← str(categoria) del JSON (CharField max_length=1)
    - InspectorTipoLiquidacion.numero_registro ← del JSON
    - InspectorAsignacionPeriodo.periodo_fin ← vigencia del JSON (fin de vigencia)
    - InspectorAsignacionPeriodo.periodo_inicio ← hoy - 365 días (misma convención que delegados)

Idempotente: get_or_create por (inspector, tipo_liquidacion, numero_registro).

Uso:
    python manage.py seed_inspectores --settings=config.settings.development
    python manage.py seed_inspectores --dry-run --settings=config.settings.development
"""

import json
from datetime import date, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    InspectorOperacion,
    InspectorOperacionPeriodo,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiquidacionModel
from modules.usuarios.domain.models.perfil_ingeniero import (
    Capitulo,
    EspecialidadIngeniero,
    PerfilIngeniero,
)

# Mapeo de tipos del JSON alpha → códigos TipoLiquidacion en DB
TIPO_MAP = {
    "EDIFICACION": "EDIFICACION",
    "HABILITACION_URBANA": "HABILITACION_URBANA",
}


class Command(BaseCommand):
    help = "Siembra inspectores desde seeds/inspectores_reales.json"

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Validar sin escribir.")
        parser.add_argument(
            "--seed-path",
            type=Path,
            default=None,
            help="Ruta alternativa al JSON de inspectores.",
        )

    def _get_or_create_perfil(self, cip, identidad, dry_run=False):
        """Crea/actualiza el PerfilIngeniero desde los datos de identidad del JSON."""
        capitulo = None
        cap_raw = identidad.get("capitulo") or {}
        if cap_raw.get("registro_id"):
            capitulo, _ = Capitulo.objects.get_or_create(
                registro_id=cap_raw["registro_id"],
                defaults={
                    "abreviacion": cap_raw.get("abreviacion", ""),
                    "nombre": cap_raw.get("nombre", ""),
                },
            )

        cod_esp = identidad.get("codigo_especialidad", "")
        especialidad = None
        if cod_esp and capitulo:
            especialidad, _ = EspecialidadIngeniero.objects.get_or_create(
                codigo=cod_esp,
                capitulo=capitulo,
                defaults={"nombre": cod_esp},
            )

        perfil_defaults = {
            "dni": identidad.get("dni", ""),
            "nombres": identidad.get("nombres", ""),
            "apellido_paterno": identidad.get("apellido_paterno", ""),
            "apellido_materno": identidad.get("apellido_materno", ""),
            "correo_personal": identidad.get("correo_personal") or None,
            "especialidad": especialidad,
            "capitulo": capitulo,
        }

        perfil = PerfilIngeniero.objects.filter(cip=cip).first()
        if not perfil:
            if dry_run:
                return None, True
            perfil = PerfilIngeniero.objects.create(cip=cip, **perfil_defaults)
            return perfil, True

        # Actualizar campos si cambiaron (sin tocar usuario)
        updated = False
        for k, v in perfil_defaults.items():
            if getattr(perfil, k) != v:
                setattr(perfil, k, v)
                updated = True
        if updated:
            perfil.save()
        return perfil, False

    def _resolver_especialidad_revision(self, reg):
        """
        Resuelve la EspecialidadRevision para una operación de inspector,
        desde el nombre de especialidad del registro del JSON
        (ej. 'Ingeniería Civil').

        La especialidad vive en la operación (InspectorOperacion), no en el
        Inspector base. Retorna None si no se puede resolver.
        """
        from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision

        # Mapeo de sinónimos: especialidades del CIP → EspecialidadRevision (3 canónicas)
        MAPEO_SINONIMOS = {
            "ingenieria civil": "Ingeniería Civil",
            "ingenieria sanitaria": "Ingeniería Sanitaria",
            "ingenieria electrica": "Eléctrica/Mecánica",
            "ingenieria mecanica electrica": "Eléctrica/Mecánica",
            "ingenieria mecanica": "Eléctrica/Mecánica",
            "ingenieria electronica": "Eléctrica/Mecánica",
        }

        nombre_esp = (reg.get("especialidad") or "").strip()
        if nombre_esp:
            key = nombre_esp.lower().strip()
            canon = MAPEO_SINONIMOS.get(key)
            if canon:
                esp = EspecialidadRevision.objects.filter(nombre__iexact=canon).first()
                if esp:
                    return esp
            esp = EspecialidadRevision.objects.filter(nombre__iexact=nombre_esp).first()
            if esp:
                return esp
            # Fallback: normalizar sin acentos para el mapeo de sinónimos
            from unicodedata import normalize as uni_norm
            key_norm = uni_norm("NFD", key).encode("ascii", "ignore").decode()
            canon_norm = {
                "ingenieria civil": "Ingeniería Civil",
                "ingenieria sanitaria": "Ingeniería Sanitaria",
                "ingenieria electrica": "Eléctrica/Mecánica",
                "ingenieria mecanica electrica": "Eléctrica/Mecánica",
                "ingenieria mecanica": "Eléctrica/Mecánica",
                "ingenieria electronica": "Eléctrica/Mecánica",
            }
            canon2 = canon_norm.get(key_norm)
            if canon2:
                esp = EspecialidadRevision.objects.filter(nombre__iexact=canon2).first()
                if esp:
                    return esp
        return None

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        seed_file = options["seed_path"] or (self.SEEDS_DIR / "inspectores_reales.json")

        if not seed_file.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {seed_file}"))
            return

        with open(seed_file, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            self.stdout.write(self.style.ERROR("El seed debe ser un array JSON."))
            return

        # Cache de tipos liquidacion
        tipos_cache = {}
        for codigo in TIPO_MAP.values():
            tipo = TipoLiquidacionModel.objects.filter(codigo=codigo).first()
            if tipo:
                tipos_cache[codigo] = tipo

        inspectores_creados = 0
        perfiles_creados = 0
        registros_creados = 0
        periodos_creados = 0
        sin_tipo = []
        sin_registro = []
        hoy = date.today()
        inicio_default = hoy - timedelta(days=365)

        for entry in data:
            cip = str(entry.get("cip", "")).strip()
            identidad = entry.get("identidad", {}) or {}

            perfil, perfil_created = self._get_or_create_perfil(cip, identidad, dry_run)
            if not perfil:
                continue
            if perfil_created:
                perfiles_creados += 1

            if dry_run:
                self.stdout.write(f"[DRY] Inspector {cip}: {perfil.nombre_completo}")
                continue

            inspector, created = Inspector.objects.get_or_create(
                perfil_ingeniero=perfil,
            )
            if created:
                inspectores_creados += 1

            for reg in entry.get("registros", []):
                numero_registro = str(reg.get("numero_registro", "")).strip()
                tipo_key = str(reg.get("tipo_liquidacion", "")).strip().upper()
                categoria = reg.get("categoria")
                vigencia_str = str(reg.get("vigencia", "")).strip()

                if not numero_registro:
                    sin_registro.append(f"{cip} (sin numero_registro)")
                    continue

                tipo = tipos_cache.get(TIPO_MAP.get(tipo_key))
                if not tipo:
                    sin_tipo.append(f"{cip} -> {tipo_key}")
                    continue

                # Resolver especialidad_revision desde el nombre de especialidad del registro
                # (o desde la especialidad del inspector como fallback).
                especialidad_rev = self._resolver_especialidad_revision(reg)
                if especialidad_rev is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"    Sin especialidad_revision para {cip} -> {tipo_key}, saltando"
                        )
                    )
                    continue

                itl, itl_created = InspectorOperacion.objects.get_or_create(
                    inspector=inspector,
                    tipo_liquidacion=tipo,
                    categoria=str(categoria) if categoria is not None else "",
                    defaults={
                        "numero_registro": numero_registro,
                        "especialidad_revision": especialidad_rev,
                    },
                )
                if itl_created:
                    registros_creados += 1

                # Periodo de vigencia:
                # - Si el JSON trae vigencia NO vencida → usarla como periodo_fin
                # - Si la vigencia del JSON ya venció (seed alpha del periodo anterior)
                #   o no trae fecha → periodo_fin=None (vigencia ABIERTA, vigente hoy),
                #   misma convención que seed_delegados.
                periodo_fin = None
                if vigencia_str:
                    try:
                        vigencia = date.fromisoformat(vigencia_str)
                        if vigencia >= hoy:
                            periodo_fin = vigencia
                    except ValueError:
                        periodo_fin = None

                periodo, periodo_created = InspectorOperacionPeriodo.objects.get_or_create(
                    inspector_tipo_liquidacion=itl,
                    periodo_inicio=inicio_default,
                    periodo_fin=periodo_fin,
                )
                if periodo_created:
                    periodos_creados += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: {len(data)} inspectores validados."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Inspectores: {inspectores_creados} nuevos | "
                    f"Perfiles creados: {perfiles_creados} | "
                    f"Registros (inspector-tipo): {registros_creados} nuevos | "
                    f"Periodos: {periodos_creados} nuevos"
                )
            )

        if sin_tipo:
            self.stdout.write(self.style.WARNING(f"Tipo no encontrado ({len(sin_tipo)}): {', '.join(sin_tipo[:10])}"))
        if sin_registro:
            self.stdout.write(self.style.WARNING(f"Registros sin número ({len(sin_registro)}): {', '.join(sin_registro[:10])}"))
