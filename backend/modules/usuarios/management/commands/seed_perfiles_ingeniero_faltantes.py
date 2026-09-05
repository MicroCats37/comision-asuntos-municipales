"""
Comando para seedear PerfilIngeniero faltantes para CIPs que aparecen en
delegados_reales.json / inspectores_reales.json pero que nunca fueron
materializados al JSON de colegiados_reales.

Esto resuelve el problema donde seed_delegados/seed_inspectores saltan
CIPs porque PerfilIngeniero.objects.filter(cip=cip).first() retorna None.

Idempotente: usa get_or_create por cip (no duplicates).

Uso:
    # Derived mode: detecta CIPs faltantes desde seed JSONs
    python manage.py seed_perfiles_ingeniero_faltantes \
        --settings=config.settings.development

    # Explicit CIP list
    python manage.py seed_perfiles_ingeniero_faltantes \
        --cips=243475,065257,095196 \
        --settings=config.settings.development

    # Dry-run
    python manage.py seed_perfiles_ingeniero_faltantes --dry-run \
        --settings=config.settings.development
"""

import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand

from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero
from modules.usuarios.domain.schemas.ingeniero_habilitado_schemas import CipColegiadoData
from modules.usuarios.domain.services.core.perfil_ingeniero_core_service import (
    PerfilIngenieroCoreService,
)
from modules.usuarios.infrastructure.services import (
    RealCipClient,
    CipServiceUnavailableError,
)


class Command(BaseCommand):
    help = "Siembra PerfilIngeniero para CIPs faltantes desde seed JSONs o lista explícita"

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "liquidaciones" / "seeds"

    def add_arguments(self, parser):
        parser.add_argument(
            "--cips",
            type=str,
            default=None,
            help="Lista de CIPs separados por coma (ej: 243475,065257,095196)",
        )
        parser.add_argument(
            "--delegados-seed",
            type=Path,
            default=None,
            help="Ruta al JSON de delegados (default: <seeds>/delegados_reales.json)",
        )
        parser.add_argument(
            "--inspectores-seed",
            type=Path,
            default=None,
            help="Ruta al JSON de inspectores (default: <seeds>/inspectores_reales.json)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validar sin escribir en la base de datos",
        )
        parser.add_argument(
            "--retries",
            type=int,
            default=3,
            help="Número de reintentos en caso de error de red (default: 3)",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.1,
            help="Delay en segundos entre requests al endpoint CIP (default: 0.1)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Forzar update de PerfilIngeniero existente (default: skip)",
        )

    def _normalize_cip(self, cip: str) -> str:
        """Normaliza CIP a 6 dígitos con ceros iniciales."""
        if not cip:
            return ""
        cip = str(cip).strip().replace("-", "").replace(" ", "")
        if not cip.isdigit():
            return ""
        return cip.zfill(6)[:6]

    def _collect_cips_from_seed(self, seed_path: Path) -> set[str]:
        """Lee un seed JSON y retorna CIPs únicos de delegados + asignaciones."""
        if not seed_path.exists():
            self.stdout.write(self.style.WARNING(f"Seed file not found: {seed_path}"))
            return set()

        with open(seed_path, encoding="utf-8") as f:
            data = json.load(f)

        cips = set()

        # Handle dict structure (delegados_reales.json) with delegados + asignaciones
        if isinstance(data, dict):
            for item in data.get("delegados", []):
                cip = self._normalize_cip(item.get("cip", ""))
                if cip:
                    cips.add(cip)
            for asign in data.get("asignaciones", []):
                cip = self._normalize_cip(asign.get("cip", ""))
                if cip:
                    cips.add(cip)
        # Handle list structure (inspectores_reales.json) — each item has a cip field
        elif isinstance(data, list):
            for item in data:
                # inspectores_reales.json: cip is at top level
                cip = self._normalize_cip(item.get("cip", ""))
                if cip:
                    cips.add(cip)
        return cips

    def _find_missing_cips(self, cips: set[str]) -> list[str]:
        """Filtra CIPs que NO tienen PerfilIngeniero en la BD."""
        missing = []
        for cip in sorted(cips):
            if not PerfilIngeniero.objects.filter(cip=cip).exists():
                missing.append(cip)
        return missing

    def _fetch_colegiado_with_retry(
        self, cip: str, client: RealCipClient, retries: int, delay: float
    ) -> dict | None:
        """Llama a RealCipClient.get_colegiado con retry exponencial."""
        for attempt in range(1, retries + 1):
            try:
                return client.get_colegiado(cip)
            except CipServiceUnavailableError as e:
                if attempt < retries:
                    wait = delay * (2 ** (attempt - 1))
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [WARN] CIP {cip} intento {attempt}/{retries} falló: {e}. "
                            f"Reintentando en {wait:.1f}s..."
                        )
                    )
                    time.sleep(wait)
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  [ERROR] CIP {cip} no disponible tras {retries} intentos: {e}"
                        )
                    )
                    return None
        return None

    def _obtener_o_crear_capitulo(self, capitulo_data: dict):
        """Obtiene o crea un Capitulo desde dict con campos del API CIP."""
        if not capitulo_data:
            return None
        registro_id = capitulo_data.get("id") or capitulo_data.get("codCapitulo")
        if not registro_id:
            return None
        from modules.usuarios.domain.models.perfil_ingeniero import Capitulo
        capitulo, _ = Capitulo.objects.update_or_create(
            registro_id=registro_id,
            defaults={
                "nombre": capitulo_data.get("descripcion") or f"Capítulo {registro_id}",
                "abreviacion": capitulo_data.get("abreviatura") or f"CAP{registro_id}",
                "grupo_envio_intitucional": capitulo_data.get("grupoEnviosInst") or None,
            },
        )
        return capitulo

    def _upsert_perfil(
        self, cip: str, cip_data: CipColegiadoData, force: bool
    ) -> tuple[PerfilIngeniero, bool]:
        """
        Crea o actualiza un PerfilIngeniero con datos del CIP API.
        Solo usa campos reales del modelo PerfilIngeniero.
        Retorna (perfil, was_created_or_updated).
        """
        from modules.usuarios.domain.models.perfil_ingeniero import (
            Capitulo,
            PerfilIngeniero,
            IngenieroHabilitacion,
        )

        # Obtener o crear capitulo
        capitulo = None
        if cip_data.capitulo:
            capitulo = self._obtener_o_crear_capitulo(cip_data.capitulo.model_dump())

        # Construir campos validos para PerfilIngeniero
        perfil_fields = {
            "dni": cip_data.dni,
            "nombres": cip_data.nombres_completo,
            "apellido_paterno": cip_data.paterno,
            "apellido_materno": cip_data.materno,
            "fecha_nacimiento": cip_data.fechaNacimiento,  # string "YYYY-MM-DD" o None
            "genero": cip_data.codGenero,
            "correo_personal": cip_data.correoPers,
            "correo_institucional": cip_data.correoInst,
            "direccion": cip_data.direccion,
            "ubigeo": cip_data.distritoId,
            "capitulo": capitulo,
        }

        existing = PerfilIngeniero.objects.filter(cip=cip).first()
        if existing:
            if force:
                for k, v in perfil_fields.items():
                    setattr(existing, k, v)
                existing.save()
                # Actualizar IngenieroHabilitacion
                self._upsert_habilitacion(
                    existing,
                    cip_data.habilitado,
                    cip_data.condicion,
                    cip_data.ultimoPeriodoPagado,
                )
                return existing, False
            return existing, False

        # Crear nuevo
        perfil_fields["cip"] = cip
        perfil = PerfilIngeniero.objects.create(**perfil_fields)

        # Crear IngenieroHabilitacion
        self._upsert_habilitacion(
            perfil,
            cip_data.habilitado,
            cip_data.condicion,
            cip_data.ultimoPeriodoPagado,
        )

        return perfil, True

    def _upsert_habilitacion(self, perfil, habilitado: bool, condicion: str, ultimo_periodo: str):
        """Crea o actualiza IngenieroHabilitacion para el PerfilIngeniero."""
        from modules.usuarios.domain.models.perfil_ingeniero import IngenieroHabilitacion
        from django.utils import timezone

        IngenieroHabilitacion.objects.update_or_create(
            perfil_ingeniero=perfil,
            fecha_busqueda=None,  # Null = registro actual
            defaults={
                "condicion_cip": condicion,
                "ultimo_periodo_pagado_cip": ultimo_periodo,
            },
        )

    def handle(self, *args, **options):
        cips_arg = options.get("cips")
        delegados_seed_path = options.get("delegados_seed")
        inspectores_seed_path = options.get("inspectores_seed")
        dry_run = options.get("dry_run", False)
        retries = options.get("retries", 3)
        delay = options.get("delay", 0.1)
        force = options.get("force", False)

        # Collect target CIPs
        target_cips: set[str] = set()

        if cips_arg:
            # Explicit CIP list
            for c in cips_arg.split(","):
                cip = self._normalize_cip(c.strip())
                if cip:
                    target_cips.add(cip)
        else:
            # Derived from seed files
            if delegados_seed_path:
                cips = self._collect_cips_from_seed(Path(delegados_seed_path))
                self.stdout.write(f"  CIPs de delegados_reales: {len(cips)}")
                target_cips |= cips
            elif inspectores_seed_path:
                cips = self._collect_cips_from_seed(Path(inspectores_seed_path))
                self.stdout.write(f"  CIPs de inspectores_reales: {len(cips)}")
                target_cips |= cips
            else:
                # Default: use both seed files
                default_delegados = self.SEEDS_DIR / "delegados_reales.json"
                default_inspectores = self.SEEDS_DIR / "inspectores_reales.json"

                if default_delegados.exists():
                    cips = self._collect_cips_from_seed(default_delegados)
                    self.stdout.write(f"  CIPs de delegados_reales: {len(cips)}")
                    target_cips |= cips

                if default_inspectores.exists():
                    cips = self._collect_cips_from_seed(default_inspectores)
                    self.stdout.write(f"  CIPs de inspectores_reales: {len(cips)}")
                    target_cips |= cips

        if not target_cips:
            self.stdout.write(self.style.WARNING("No CIPs specified or found."))
            return

        # Filter to missing
        missing_cips = self._find_missing_cips(target_cips)
        self.stdout.write(f"  Total CIPs objetivo: {len(target_cips)}")
        self.stdout.write(f"  CIPs faltantes (sin PerfilIngeniero): {len(missing_cips)}")
        if missing_cips:
            self.stdout.write(f"  CIPs faltantes: {', '.join(missing_cips[:20])}")
            if len(missing_cips) > 20:
                self.stdout.write(f"  ... y {len(missing_cips) - 20} más")

        if not missing_cips:
            self.stdout.write(self.style.SUCCESS("Todos los CIPs ya tienen PerfilIngeniero."))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY RUN] Se crearían {len(missing_cips)} PerfilIngeniero"))
            for cip in missing_cips:
                self.stdout.write(f"  [DRY] CIP {cip}")
            return

        # Process each missing CIP
        client = RealCipClient()
        seeded = 0
        skipped = 0
        updated = 0

        for i, cip in enumerate(missing_cips, 1):
            self.stdout.write(f"[{i}/{len(missing_cips)}] Procesando CIP {cip}...")

            data = self._fetch_colegiado_with_retry(cip, client, retries, delay)
            if data is None:
                self.stdout.write(
                    self.style.WARNING(f"  [SKIP] CIP {cip} — API no disponible o 404")
                )
                skipped += 1
                continue

            try:
                cip_data = CipColegiadoData(**data)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  [ERROR] CIP {cip} — datos inválidos: {e}")
                )
                skipped += 1
                continue

            try:
                perfil, was_new = self._upsert_perfil(cip, cip_data, force=force)
                if was_new:
                    seeded += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [OK] CIP {cip} — Creado: {perfil.nombre_completo}"
                        )
                    )
                else:
                    updated += 1
                    self.stdout.write(
                        self.style.WARNING(f"  [SKIP] CIP {cip} — Ya existe (use --force to update)")
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  [ERROR] CIP {cip} — Error al crear PerfilIngeniero: {e}")
                )
                skipped += 1
                continue

            # Rate limiting delay between API calls
            if delay > 0 and i < len(missing_cips):
                time.sleep(delay)

        # Summary
        self.stdout.write("")
        if seeded:
            self.stdout.write(self.style.SUCCESS(f"  Creados: {seeded}"))
        if updated:
            self.stdout.write(self.style.WARNING(f"  Omitidos (ya existen): {updated}"))
        if skipped:
            self.stdout.write(self.style.ERROR(f"  Fallidos/Saltados: {skipped}"))
        self.stdout.write(self.style.SUCCESS(f"Done. Total: {len(missing_cips)} CIPs procesados."))
