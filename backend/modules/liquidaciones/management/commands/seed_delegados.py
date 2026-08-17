"""
Comando para sembrar delegados desde seeds/delegados_reales.json.

Requiere que ya estén cargados:
  1. seed_colegiados (PerfilIngeniero por CIP)
  2. seed_municipalidades (códigos L* por nombre)

El seed viejo usa MUN0001-MUN0100; se matchea por NOMBRE normalizado contra
las municipalidades L* actuales. Las asignaciones sin match se ignoran
(distritos/provincias que no son municipalidades principales).

Idempotente: get_or_create por (delegado, municipalidad).

Uso:
    python manage.py seed_delegados --settings=config.settings.development
    python manage.py seed_delegados --dry-run --settings=config.settings.development
"""

import json
import unicodedata
from datetime import date, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.liquidaciones.domain.constants import TipoDelegado
from modules.liquidaciones.domain.models.delegado import (
    Delegado,
    DelegadoMunicipalidad,
    DelegadoMunicipalidadPeriodo,
)
from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero, EspecialidadRevision


def normalize(name: str) -> str:
    """Normaliza nombre: mayúsculas, sin acentos, sin guiones/espacios raros."""
    if not name:
        return ""
    normalized = unicodedata.normalize("NFD", name.upper())
    ascii_name = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    return " ".join(ascii_name.replace("-", " ").replace("/", " ").split())


class Command(BaseCommand):
    help = "Siembra delegados desde seeds/delegados_reales.json"

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Validar sin escribir.")
        parser.add_argument(
            "--seed-path",
            type=Path,
            default=None,
            help="Ruta alternativa al JSON de delegados.",
        )

    def _resolver_especialidad_revision(self, asign):
        """
        Resuelve la EspecialidadRevision desde el campo `especialidad` de la
        asignación (formato 'Ingeniería Civil - Edificaciones').

        Extrae el nombre de la especialidad antes del ' - ' y lo busca en
        EspecialidadRevision. Retorna None si no se puede resolver.
        """
        raw = str(asign.get("especialidad", "") or "").strip()
        if not raw:
            return None
        # "Ingeniería Civil - Edificaciones" → "Ingeniería Civil"
        nombre_esp = raw.split(" - ")[0].strip()
        esp = EspecialidadRevision.objects.filter(nombre__iexact=nombre_esp).first()
        if esp:
            return esp
        # Fallback: comparar normalizado (sin acentos)
        norm = normalize(nombre_esp)
        for cand in EspecialidadRevision.objects.all():
            if normalize(cand.nombre) == norm:
                return cand
        return None

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        seed_file = options["seed_path"] or (self.SEEDS_DIR / "delegados_reales.json")

        if not seed_file.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {seed_file}"))
            return

        with open(seed_file, encoding="utf-8") as f:
            data = json.load(f)

        # Mapa de municipalidades por nombre normalizado
        municipios = {}
        for m in Municipalidad.objects.all():
            municipios[normalize(m.nombre)] = m

        delegados_creados = 0
        asignaciones_creadas = 0
        sin_perfil = []
        sin_municipio = []
        periodo_creado = 0

        for item in data.get("delegados", []):
            cip = str(item.get("cip", "")).strip()
            perfil = PerfilIngeniero.objects.filter(cip=cip).first()
            if not perfil:
                sin_perfil.append(cip)
                continue

            if dry_run:
                self.stdout.write(f"[DRY] Delegado {cip}: {perfil.nombre_completo}")
                continue

            delegado, _ = Delegado.objects.get_or_create(
                perfil_ingeniero=perfil,
            )
            delegados_creados += 1

        # Asignaciones
        for asign in data.get("asignaciones", []):
            cip = str(asign.get("cip", "")).strip()
            perfil = PerfilIngeniero.objects.filter(cip=cip).first()
            if not perfil:
                continue

            delegado = Delegado.objects.filter(perfil_ingeniero=perfil).first()
            if not delegado:
                continue

            # Resolver municipalidad por nombre normalizado
            nombre_mun = normalize(asign.get("municipalidad_nombre", ""))
            if not nombre_mun and asign.get("municipalidad_codigo"):
                # Fallback: buscar por nombre en el seed municipalidades
                mun_seed = next(
                    (m for m in data.get("municipalidades", [])
                     if m.get("codigo") == asign.get("municipalidad_codigo")),
                    None,
                )
                nombre_mun = normalize((mun_seed or {}).get("nombre", ""))

            municipio = municipios.get(nombre_mun)
            if not municipio:
                sin_municipio.append(f"{cip} -> {asign.get('municipalidad_codigo')}")
                continue

            tipo_str = str(asign.get("tipo", "")).upper()
            tipo = tipo_str if tipo_str in ("TITULAR", "ALTERNO") else TipoDelegado.TITULAR

            if dry_run:
                self.stdout.write(f"[DRY] Asignación {cip} -> {municipio.nombre} ({tipo})")
                continue

            esp_rev = self._resolver_especialidad_revision(asign)
            if esp_rev is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"    Sin especialidad_revision para {cip} -> {asign.get('municipalidad_codigo')}, saltando"
                    )
                )
                continue

            dm, _ = DelegadoMunicipalidad.objects.get_or_create(
                delegado=delegado,
                municipalidad=municipio,
                defaults={
                    "tipo": tipo,
                    "especialidad_revision": esp_rev,
                },
            )
            asignaciones_creadas += 1

            # Periodo de vigencia (inicio = hace 1 año, sin fin)
            hoy = date.today()
            DelegadoMunicipalidadPeriodo.objects.get_or_create(
                delegado_municipalidad=dm,
                periodo_inicio=hoy - timedelta(days=365),
                periodo_fin=None,
            )
            periodo_creado += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: {len(data.get('delegados', []))} delegados validados."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Delegados: {delegados_creados} | Asignaciones: {asignaciones_creadas} | Periodos: {periodo_creado}"
                )
            )

        if sin_perfil:
            self.stdout.write(self.style.WARNING(f"Sin PerfilIngeniero ({len(sin_perfil)}): {', '.join(sin_perfil[:10])}"))
        if sin_municipio:
            self.stdout.write(self.style.WARNING(f"Sin municipalidad ({len(sin_municipio)}): {', '.join(sin_municipio[:10])}"))
