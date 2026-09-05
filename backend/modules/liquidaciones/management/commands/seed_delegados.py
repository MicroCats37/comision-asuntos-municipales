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
from modules.liquidaciones.domain.models.tipo_liquidacion import (
    TipoLiquidacion,
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
        # Sinónimos: el CSV/seed usa nombres largos, la BD usa nombres cortos.
        SINONIMOS_ESP = {
            "Ingeniería Eléctrica y Mecánica Eléctrica": "Eléctrica/Mecánica",
            "Ingenieria Electrica y Mecanica Electrica": "Eléctrica/Mecánica",
            "Ingeniería Eléctrica": "Eléctrica/Mecánica",
        }
        sinonimo = SINONIMOS_ESP.get(nombre_esp)
        if sinonimo:
            esp = EspecialidadRevision.objects.filter(nombre__iexact=sinonimo).first()
            if esp:
                return esp
        # Fallback: comparar normalizado (sin acentos)
        norm = normalize(nombre_esp)
        for cand in EspecialidadRevision.objects.all():
            if normalize(cand.nombre) == norm:
                return cand
        return None

    def _resolver_tipo_liquidacion(self, asign):
        """
        Resuelve TipoLiquidacion desde el campo `tipo_liquidacion` de la asignación
        (valor canónico como 'EDIFICACION' o 'HABILITACION_URBANA').

        Retorna el objeto TipoLiquidacion o None si no se encuentra.
        Emite un warning cuando el campo está ausente para no ocultar tipos desconocidos.
        """
        tipo_liq = str(asign.get("tipo_liquidacion", "") or "").strip()
        if not tipo_liq:
            self.stdout.write(
                self.style.WARNING(
                    f"    tipo_liquidacion ausente en asignación "
                    f"CIP={asign.get('cip')} -> municipalidad={asign.get('municipalidad_codigo')}"
                )
            )
            return None
        tipo = TipoLiquidacion.objects.filter(codigo=tipo_liq).first()
        if tipo is None:
            self.stdout.write(
                self.style.WARNING(
                    f"    TipoLiquidacion '{tipo_liq}' no encontrado en BD para "
                    f"CIP={asign.get('cip')} -> municipalidad={asign.get('municipalidad_codigo')}"
                )
            )
        return tipo

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        seed_file = options["seed_path"] or (self.SEEDS_DIR / "delegados_reales.json")

        if not seed_file.exists():
            self.stdout.write(self.style.ERROR(f"No se encontró {seed_file}"))
            return

        with open(seed_file, encoding="utf-8") as f:
            data = json.load(f)

        # Mapa de municipalidades por código y por nombre normalizado
        municipios_por_codigo = {}
        municipios = {}
        for m in Municipalidad.objects.all():
            municipios[normalize(m.nombre)] = m
            if m.codigo:
                municipios_por_codigo[m.codigo] = m

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

            # Resolver municipalidad: primero por código L, luego por nombre normalizado
            codigo_seed = str(asign.get("municipalidad_codigo", "")).strip()
            municipio = municipios_por_codigo.get(codigo_seed)

            if municipio is None:
                # Resolver por nombre en el seed municipalidades
                nombre_mun = normalize(asign.get("municipalidad_nombre", ""))
                if not nombre_mun and codigo_seed:
                    mun_seed = next(
                        (m for m in data.get("municipalidades", [])
                         if m.get("codigo") == codigo_seed),
                        None,
                    )
                    nombre_mun = normalize((mun_seed or {}).get("nombre", ""))
                municipio = municipios.get(nombre_mun)

            # Si no existe, crearla (incluye códigos L-FALTANTE N)
            if municipio is None and not dry_run and codigo_seed:
                nombre_seed = next(
                    (m.get("nombre") for m in data.get("municipalidades", [])
                     if m.get("codigo") == codigo_seed),
                    codigo_seed,
                )
                municipio, _ = Municipalidad.objects.get_or_create(
                    codigo=codigo_seed,
                    defaults={"nombre": nombre_seed},
                )
                municipios[normalize(nombre_seed)] = municipio
                municipios_por_codigo[codigo_seed] = municipio

            if not municipio:
                sin_municipio.append(f"{cip} -> {codigo_seed or asign.get('municipalidad_nombre')}")
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

            tipo_liq = self._resolver_tipo_liquidacion(asign)

            # Backward compatibility: if DelegadoMunicipalidad already exists for
            # (delegado, municipalidad) with tipo_liquidacion=NULL, update it in-place
            # so we don't get unique-constraint violations when we now have a tipo_liq.
            existing_null = DelegadoMunicipalidad.objects.filter(
                delegado=delegado,
                municipalidad=municipio,
                tipo_liquidacion__isnull=True,
            ).first()

            if existing_null is not None:
                if tipo_liq is not None:
                    existing_null.tipo_liquidacion = tipo_liq
                    existing_null.save(update_fields=["tipo_liquidacion"])
                    self.stdout.write(
                        self.style.WARNING(
                            f"    Actualizado tipo_liquidacion en DelegadoMunicipalidad "
                            f"existente para {cip} -> {municipio.codigo}: "
                            f"{tipo_liq.codigo}"
                        )
                    )
                else:
                    # Keep the existing NULL; nothing new to set
                    pass
                dm = existing_null
            else:
                dm, _ = DelegadoMunicipalidad.objects.get_or_create(
                    delegado=delegado,
                    municipalidad=municipio,
                    tipo_liquidacion=tipo_liq,
                    defaults={
                        "tipo": tipo,
                        "especialidad_revision": esp_rev,
                    },
                )
            asignaciones_creadas += 1

            # Periodo de vigencia
            # Soporte nuevo: periodos[] array ( Approach A — múltiples periodos en una entrada).
            # Cada entry: {vigencia_inicio, vigencia_fin}. Para cada uno se llama
            # close_current_and_open_new, que cierra el abierto y abre el nuevo.
            # Idempotencia: si el periodo cerrado ya existe (mismo periodo_inicio), se salta.
            #
            # Fallback legacy: si no hay periodos[], se comporta como antes:
            # - Si vigencia_inicio presente: close_current_and_open_new(vigencia_inicio)
            # - Si no: legacy (hoy-365, open)
            periodos_list = asign.get("periodos")
            vigencia_inicio_str = asign.get("vigencia_inicio")  # legacy single-field format
            if periodos_list and isinstance(periodos_list, list) and len(periodos_list) > 0:
                for periodo_entry in periodos_list:
                    vigencia_inicio_str_item = periodo_entry.get("vigencia_inicio")
                    vigencia_fin_str_item = periodo_entry.get("vigencia_fin")
                    if not vigencia_inicio_str_item:
                        continue
                    try:
                        from datetime import datetime

                        vigencia_inicio = datetime.strptime(vigencia_inicio_str_item, "%Y-%m-%d").date()
                        vigencia_fin = None
                        if vigencia_fin_str_item:
                            vigencia_fin = datetime.strptime(vigencia_fin_str_item, "%Y-%m-%d").date()

                        DelegadoMunicipalidadPeriodo.objects.update_or_create(
                            delegado_municipalidad=dm,
                            periodo_inicio=vigencia_inicio,
                            defaults={
                                "periodo_fin": vigencia_fin
                            }
                        )
                        periodo_creado += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(
                                f"    Error creando periodo para CIP={cip} -> {municipio.codigo}: {e}"
                            )
                        )
            elif vigencia_inicio_str:
                # Legacy: single vigencia_inicio (v2.0 sin periodos[]), backward compat
                try:
                    from datetime import datetime

                    vigencia_inicio = datetime.strptime(vigencia_inicio_str, "%Y-%m-%d").date()
                    existing_closed = DelegadoMunicipalidadPeriodo.objects.filter(
                        delegado_municipalidad=dm,
                        periodo_inicio=vigencia_inicio,
                        periodo_fin__isnull=False,
                    ).exists()
                    if not existing_closed:
                        DelegadoMunicipalidadPeriodo.close_current_and_open_new(dm, vigencia_inicio)
                        periodo_creado += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"    Periodo vigencia_inicio={vigencia_inicio} ya existe (cerrado) "
                                f"para CIP={cip} -> {municipio.codigo}, saltando"
                            )
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f"    Error creando periodo para CIP={cip} -> {municipio.codigo}: {e}"
                        )
                    )
            else:
                # Legacy behavior (backward compat con v1.0 sin vigencia_inicio ni periodos[])
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
