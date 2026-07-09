"""
Management command para poblar TODAS las tarifas de liquidaciones.

Pobla:
    - EDIFICACION: TarifaLiquidacionBase + TarifaPorcentajeObra + ReglaTarifaEdificacion
    - HABILITACION_URBANA, MECANICA_SUELOS, IMPACTO_VIAL, TALUDES:
      TarifaLiquidacionBase + TarifaPorMetroCuadrado + ReglaTarifaEdificacion
    - INSPECCION_OBRA: TarifaLiquidacionBase + TarifaPorCategoriaVisitas + ReglaTarifaInspeccionObra

Uso:
    python manage.py seed_tarifas_all --settings=config.settings.development
    python manage.py seed_tarifas_all --dry-run --settings=config.settings.development

Notas:
    - IMPACTO_VIAL y TALUDES: La cartilla indica 0.15% valor obra,
      pero el modelo actual usa LiquidacionPorMetroCuadrado.
      Se poblarán como M2 para mantener consistencia.
    - PLANTAS_TIPICAS: No hay modelo para "monto declarado en presupuesto". No se pobla.
    - INSPECCION_OBRA: Los costos son 0.032/0.037/0.042/0.088 * UIT(2026)=5500.
      Si la UIT cambia, este seed queda obsoleto.
"""

import json
import logging
import unicodedata
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from modules.liquidaciones.domain.models.liquidacion.liquidacion import (
    TarifaLiquidacionBase,
    TarifaPorcentajeObra,
    ReglaTarifaEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.tarifas_reglas import (
    TarifaPorMetroCuadrado,
    TarifaPorCategoriaVisitas,
    ReglaTarifaLiquidacion,
    ReglaTarifaInspeccionObra,
)
from modules.liquidaciones.domain.models.especialidades import Especialidad
from modules.liquidaciones.domain.constants import (
    TipoLiquidacion,
    TipoTramiteEdificaciones,
    TramiteAccion,
)


logger = logging.getLogger(__name__)


def normalize_specialty_name(name: str) -> str:
    """Remove accents/diacritics from a specialty name for canonical comparison."""
    if not name:
        return name
    normalized = unicodedata.normalize('NFD', name)
    return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')


CANONICAL_SPECIALTY_NAMES = [
    'Ingeniería Civil',
    'Ingeniería Sanitaria',
    'Ingeniería Eléctrica y Mecánica Eléctrica',
]

SPECIALTY_NORMALIZATION_MAP = {
    'ingenieria civil': 'Ingeniería Civil',
    'ingenieria sanitaria': 'Ingeniería Sanitaria',
    'ingenieria electrica y mecanica electrica': 'Ingeniería Eléctrica y Mecánica Eléctrica',
}


def get_canonical_specialty_name(raw_name: str) -> str:
    """Return the canonical accented specialty name for a raw name from seed data."""
    if not raw_name:
        return raw_name
    normalized = normalize_specialty_name(raw_name).lower()
    return SPECIALTY_NORMALIZATION_MAP.get(normalized, raw_name)


class Command(BaseCommand):
    help = "Poblar todas las tarifas de liquidaciones (Edificacion, HU, MS, IV, Taludes, Inspeccion)"

    SEEDS_DIR = Path(__file__).resolve().parent.parent.parent / "seeds"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validar datos seed sin escribir en la base de datos',
        )
        parser.add_argument(
            '--seed-path',
            type=str,
            default=None,
            help='Ruta al archivo JSON seed de tarifas',
        )
        parser.add_argument(
            '--skip-edificacion',
            action='store_true',
            help='Omitir poblar tarifas de Edificacion',
        )
        parser.add_argument(
            '--skip-m2',
            action='store_true',
            help='Omitir poblar tarifas M2 (HU, MS, IV, Taludes)',
        )
        parser.add_argument(
            '--skip-inspeccion',
            action='store_true',
            help='Omitir poblar tarifas de Inspeccion',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.skip_edificacion = options['skip_edificacion']
        self.skip_m2 = options['skip_m2']
        self.skip_inspeccion = options['skip_inspeccion']
        self.seed_path = (
            Path(options['seed_path'])
            if options['seed_path']
            else self.SEEDS_DIR / "tarifas_all.json"
        )

        self._log(f"\n[seed_tarifas_all] Starting...")

        if self.dry_run:
            self._log(self.style.WARNING("  DRY-RUN MODE - No database writes will occur"))

        # Load seed data
        seed_data = self._load_seed()
        if not seed_data:
            raise CommandError("Failed to load seed data")

        # Report notas
        notas = seed_data.get('notas', [])
        if notas:
            self._log(self.style.WARNING("\n  [NOTAS/GAPS]"))
            for nota in notas:
                self._log(f"    - {nota}")

        totals = {'created': 0, 'updated': 0}

        # Process each section
        if not self.skip_edificacion:
            self._log(self.style.SUCCESS("\n=== EDIFICACION ==="))
            c, u = self._process_edificacion(seed_data.get('tarifas_edificacion', []))
            totals['created'] += c['tarifas'] + c['reglas']
            totals['updated'] += u['tarifas'] + u['reglas']
        else:
            self._log("\n[EDIFICACION] SKIPPED (--skip-edificacion)")

        if not self.skip_m2:
            self._log(self.style.SUCCESS("\n=== M2 (HU, MS, IV, TALUDES) ==="))
            c, u = self._process_m2(seed_data.get('tarifas_m2', []))
            totals['created'] += c['tarifas'] + c['reglas']
            totals['updated'] += u['tarifas'] + u['reglas']
        else:
            self._log("\n[M2] SKIPPED (--skip-m2)")

        if not self.skip_inspeccion:
            self._log(self.style.SUCCESS("\n=== INSPECCION OBRA ==="))
            c, u = self._process_inspeccion(seed_data.get('tarifas_inspeccion', []))
            totals['created'] += c['tarifas'] + c['reglas']
            totals['updated'] += u['tarifas'] + u['reglas']
        else:
            self._log("\n[INSPECCION] SKIPPED (--skip-inspeccion)")

        self._log(self.style.SUCCESS(
            f"\n[seed_tarifas_all] Completed:"
        ))
        self._log(f"  Total created: {totals['created']}")
        self._log(f"  Total updated: {totals['updated']}")

    def _log(self, msg):
        """Registra mensaje de forma segura."""
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
            safe_msg = msg.encode('ascii', 'replace').decode('ascii')
            self.stdout.write(safe_msg)

    def _load_seed(self):
        """Cargar archivo JSON seed."""
        if not self.seed_path.exists():
            raise CommandError(f"Seed file not found: {self.seed_path}")

        try:
            content = self.seed_path.read_text(encoding='utf-8')
            data = json.loads(content)
            self._log(f"  Loaded seed: version={data.get('version')}, periodo={data.get('periodo')}")
            self._log(f"  Descripcion: {data.get('descripcion', 'N/A')}")
            return data
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in seed file: {e}")

    def _ensure_especialidades(self, especialidad_nombres):
        """Ensure all especialidades exist, creating if needed."""
        created_count = 0
        for raw_nombre in especialidad_nombres:
            nombre = get_canonical_specialty_name(raw_nombre)
            if self.dry_run:
                self._log(f"    [DRY-RUN] Would create/find especialidad: {nombre}")
                continue

            spec, created = Especialidad.objects.get_or_create(
                nombre=nombre,
                defaults={}
            )
            if created:
                self._log(self.style.SUCCESS(f"    Created especialidad: {nombre}"))
                created_count += 1

        return created_count if not self.dry_run else len(especialidad_nombres)

    def _get_especialidades(self, especialidad_nombres):
        """Get Especialidad objects by canonical nombre match."""
        especialidades = []
        for raw_nombre in especialidad_nombres:
            nombre = get_canonical_specialty_name(raw_nombre)
            try:
                spec = Especialidad.objects.get(nombre=nombre)
                especialidades.append(spec)
            except Especialidad.DoesNotExist:
                raise CommandError(
                    f"Especialidad '{nombre}' not found. Run load_delegados_reales first."
                )
        return especialidades

    def _validate_choice(self, value, choice_class, choice_name):
        """Validate that a value is a valid Django TextChoices value."""
        valid_values = [c.value for c in choice_class]
        if value in valid_values:
            return value

        for valid_value in valid_values:
            if valid_value.upper() == value.upper():
                self._log(self.style.WARNING(
                    f"    Case mismatch in {choice_name}: '{value}' -> '{valid_value}'"
                ))
                return valid_value

        self._log(self.style.ERROR(
            f"    Invalid {choice_name} value: '{value}'. Valid: {valid_values}"
        ))
        return None

    # =========================================================================
    # EDIFICACION
    # =========================================================================

    def _process_edificacion(self, tarifas_data):
        """Process tarifas de edificacion."""
        created = {'tarifas': 0, 'reglas': 0}
        updated = {'tarifas': 0, 'reglas': 0}

        for tarifa_data in tarifas_data:
            c, u = self._process_tarifa_edificacion(tarifa_data)
            created['tarifas'] += c['tarifa']
            updated['tarifas'] += u['tarifa']
            created['reglas'] += c['reglas']
            updated['reglas'] += u['reglas']

        self._log(f"  Edificacion: {created['tarifas']} tarifas created, {updated['tarifas']} updated")
        self._log(f"  Edificacion: {created['reglas']} reglas created, {updated['reglas']} updated")
        return created, updated

    def _process_tarifa_edificacion(self, tarifa_data):
        """Process a single tarifa entry for Edificacion."""
        result = {'tarifa': 0, 'reglas': 0}
        update_result = {'tarifa': 0, 'reglas': 0}

        tipo_liquidacion = tarifa_data.get('tipo_liquidacion', 'EDIFICACION')
        periodo_inicio_str = tarifa_data.get('periodo_inicio', '2026-01-01')
        periodo_fin_str = tarifa_data.get('periodo_fin')
        especialidad_nombres = tarifa_data.get('especialidades', [])
        porcentaje_liquidacion = Decimal(str(tarifa_data.get('porcentaje_liquidacion', '0')))
        derecho_minimo = Decimal(str(tarifa_data.get('derecho_minimo', '0')))
        derecho_maximo_str = tarifa_data.get('derecho_maximo')
        porcentaje_minimo_uit = Decimal(str(tarifa_data.get('porcentaje_minimo_uit', '0.02')))
        reglas = tarifa_data.get('reglas', [])

        periodo_inicio = date.fromisoformat(periodo_inicio_str)
        periodo_fin = None if periodo_fin_str is None else date.fromisoformat(periodo_fin_str)
        derecho_maximo = None if derecho_maximo_str is None else Decimal(str(derecho_maximo_str))

        # Ensure especialidades
        self._ensure_especialidades(especialidad_nombres)
        especialidades = self._get_especialidades(especialidad_nombres)

        if self.dry_run:
            self._log(f"\n  [DRY-RUN] Would create/update TarifaLiquidacionBase EDIFICACION:")
            self._log(f"    periodo_inicio={periodo_inicio}, especialidades={especialidad_nombres}")
            self._log(f"    porcentaje={porcentaje_liquidacion}, derecho_min={derecho_minimo}")
            result['tarifa'] = 1
            result['reglas'] = len(reglas)
            return result, update_result

        # Find or create TarifaLiquidacionBase
        sorted_specs = sorted(especialidad_nombres)
        existing_bases = TarifaLiquidacionBase.objects.filter(
            tipo_liquidacion=tipo_liquidacion,
            periodo_inicio=periodo_inicio,
        ).prefetch_related('especialidades', 'detalle_porcentual')

        tarifa_base = None
        tarifa_created = False
        for candidate in existing_bases:
            candidate_specs = sorted(candidate.especialidades.values_list('nombre', flat=True))
            candidate_pct = getattr(candidate.detalle_porcentual, 'porcentaje_liquidacion', None)
            if list(candidate_specs) == sorted_specs and candidate_pct == porcentaje_liquidacion:
                tarifa_base = candidate
                tarifa_created = False
                break

        if tarifa_base is None:
            tarifa_base = TarifaLiquidacionBase.objects.create(
                tipo_liquidacion=tipo_liquidacion,
                periodo_inicio=periodo_inicio,
                periodo_fin=periodo_fin,
            )
            tarifa_created = True

        if tarifa_created:
            self._log(self.style.SUCCESS(f"    Created TarifaLiquidacionBase: {tarifa_base}"))
            result['tarifa'] = 1
        else:
            self._log(f"    Found existing TarifaLiquidacionBase: {tarifa_base}")
            update_result['tarifa'] = 1

        # Sync especialidades
        tarifa_base.especialidades.set(especialidades)

        # Create/update TarifaPorcentajeObra
        _, porcentaje_created = TarifaPorcentajeObra.objects.update_or_create(
            tarifa_base=tarifa_base,
            defaults={
                'porcentaje_liquidacion': porcentaje_liquidacion,
                'derecho_minimo': derecho_minimo,
                'derecho_maximo': derecho_maximo,
                'porcentaje_minimo_uit': porcentaje_minimo_uit,
            },
        )
        self._log(f"    TarifaPorcentajeObra: {'created' if porcentaje_created else 'updated'}")

        # Create/update ReglaTarifaEdificacion entries
        for regla_data in reglas:
            tipo_tramite = regla_data.get('tipo_tramite')
            tramite_accion = regla_data.get('tramite_accion')

            if not tipo_tramite or not tramite_accion:
                self._log(self.style.WARNING(f"    Skipping rule with missing tipo_tramite or tramite_accion"))
                continue

            valid_tipo_tramite = self._validate_choice(
                tipo_tramite, TipoTramiteEdificaciones, 'TipoTramiteEdificaciones'
            )
            valid_tramite_accion = self._validate_choice(
                tramite_accion, TramiteAccion, 'TramiteAccion'
            )

            if not valid_tipo_tramite or not valid_tramite_accion:
                continue

            _, regla_created = ReglaTarifaEdificacion.objects.update_or_create(
                tipo_tramite=valid_tipo_tramite,
                tramite_accion=valid_tramite_accion,
                tarifa_base=tarifa_base,
                defaults={},
            )

            if regla_created:
                self._log(self.style.SUCCESS(
                    f"    Created ReglaTarifaEdificacion: {valid_tipo_tramite}/{valid_tramite_accion}"
                ))
                result['reglas'] += 1
            else:
                self._log(f"    Found existing ReglaTarifaEdificacion: {valid_tipo_tramite}/{valid_tramite_accion}")
                update_result['reglas'] += 1

        return result, update_result

    # =========================================================================
    # M2 (HABILITACION_URBANA, MECANICA_SUELOS, IMPACTO_VIAL, TALUDES)
    # =========================================================================

    def _process_m2(self, tarifas_data):
        """Process tarifas M2."""
        created = {'tarifas': 0, 'reglas': 0}
        updated = {'tarifas': 0, 'reglas': 0}

        for tarifa_data in tarifas_data:
            c, u = self._process_tarifa_m2(tarifa_data)
            created['tarifas'] += c['tarifa']
            updated['tarifas'] += u['tarifa']
            created['reglas'] += c['reglas']
            updated['reglas'] += u['reglas']

        self._log(f"  M2: {created['tarifas']} tarifas created, {updated['tarifas']} updated")
        self._log(f"  M2: {created['reglas']} reglas created, {updated['reglas']} updated")
        return created, updated

    def _process_tarifa_m2(self, tarifa_data):
        """Process a single tarifa entry for M2."""
        result = {'tarifa': 0, 'reglas': 0}
        update_result = {'tarifa': 0, 'reglas': 0}

        tipo_liquidacion = tarifa_data.get('tipo_liquidacion')
        periodo_inicio_str = tarifa_data.get('periodo_inicio', '2026-01-01')
        periodo_fin_str = tarifa_data.get('periodo_fin')
        costo_por_m2 = Decimal(str(tarifa_data.get('costo_por_m2', '0')))
        area_minima = Decimal(str(tarifa_data.get('area_minima', '0')))
        derecho_minimo = Decimal(str(tarifa_data.get('derecho_minimo', '0')))
        derecho_maximo_str = tarifa_data.get('derecho_maximo')
        reglas = tarifa_data.get('reglas', [])
        nota = tarifa_data.get('nota', '')

        if nota:
            self._log(self.style.WARNING(f"    Nota: {nota}"))

        periodo_inicio = date.fromisoformat(periodo_inicio_str)
        periodo_fin = None if periodo_fin_str is None else date.fromisoformat(periodo_fin_str)
        derecho_maximo = None if derecho_maximo_str is None else Decimal(str(derecho_maximo_str))

        if self.dry_run:
            self._log(f"\n  [DRY-RUN] Would create/update TarifaLiquidacionBase M2:")
            self._log(f"    tipo_liquidacion={tipo_liquidacion}, periodo_inicio={periodo_inicio}")
            self._log(f"    costo_por_m2={costo_por_m2}, area_min={area_minima}")
            self._log(f"    derecho_min={derecho_minimo}, derecho_max={derecho_maximo}")
            result['tarifa'] = 1
            result['reglas'] = len(reglas)
            return result, update_result

        # Find or create TarifaLiquidacionBase (no especialidades for M2 types)
        existing_bases = TarifaLiquidacionBase.objects.filter(
            tipo_liquidacion=tipo_liquidacion,
            periodo_inicio=periodo_inicio,
        )

        tarifa_base = None
        tarifa_created = False
        for candidate in existing_bases:
            # Check if it has detalle_m2
            if hasattr(candidate, 'detalle_m2') and candidate.detalle_m2:
                if candidate.detalle_m2.costo_por_m2 == costo_por_m2:
                    tarifa_base = candidate
                    tarifa_created = False
                    break

        if tarifa_base is None:
            tarifa_base = TarifaLiquidacionBase.objects.create(
                tipo_liquidacion=tipo_liquidacion,
                periodo_inicio=periodo_inicio,
                periodo_fin=periodo_fin,
            )
            tarifa_created = True

        if tarifa_created:
            self._log(self.style.SUCCESS(f"    Created TarifaLiquidacionBase: {tarifa_base}"))
            result['tarifa'] = 1
        else:
            self._log(f"    Found existing TarifaLiquidacionBase: {tarifa_base}")
            update_result['tarifa'] = 1

        # Create/update TarifaPorMetroCuadrado
        _, m2_created = TarifaPorMetroCuadrado.objects.update_or_create(
            tarifa_base=tarifa_base,
            defaults={
                'costo_por_m2': costo_por_m2,
                'area_minima': area_minima,
                'derecho_minimo': derecho_minimo,
                'derecho_maximo': derecho_maximo,
            },
        )
        self._log(f"    TarifaPorMetroCuadrado: {'created' if m2_created else 'updated'}")

        # Create/update ReglaTarifaLiquidacion entries (M2 only uses tramite_accion)
        for regla_data in reglas:
            tramite_accion = regla_data.get('tramite_accion')

            if not tramite_accion:
                self._log(self.style.WARNING(f"    Skipping rule with missing tramite_accion"))
                continue

            valid_tramite_accion = self._validate_choice(
                tramite_accion, TramiteAccion, 'TramiteAccion'
            )

            if not valid_tramite_accion:
                continue

            _, regla_created = ReglaTarifaLiquidacion.objects.update_or_create(
                tramite_accion=valid_tramite_accion,
                tarifa_base=tarifa_base,
                defaults={},
            )

            if regla_created:
                self._log(self.style.SUCCESS(
                    f"    Created ReglaTarifaLiquidacion: {valid_tramite_accion}"
                ))
                result['reglas'] += 1
            else:
                self._log(f"    Found existing ReglaTarifaLiquidacion: {valid_tramite_accion}")
                update_result['reglas'] += 1

        return result, update_result

    # =========================================================================
    # INSPECCION OBRA
    # =========================================================================

    def _process_inspeccion(self, tarifas_data):
        """Process tarifas de inspeccion obra."""
        created = {'tarifas': 0, 'reglas': 0}
        updated = {'tarifas': 0, 'reglas': 0}

        for tarifa_data in tarifas_data:
            c, u = self._process_tarifa_inspeccion(tarifa_data)
            created['tarifas'] += c['tarifa']
            updated['tarifas'] += u['tarifa']
            created['reglas'] += c['reglas']
            updated['reglas'] += u['reglas']

        self._log(f"  Inspeccion: {created['tarifas']} tarifas created, {updated['tarifas']} updated")
        self._log(f"  Inspeccion: {created['reglas']} reglas created, {updated['reglas']} updated")
        return created, updated

    def _process_tarifa_inspeccion(self, tarifa_data):
        """Process a single tarifa entry for Inspeccion."""
        result = {'tarifa': 0, 'reglas': 0}
        update_result = {'tarifa': 0, 'reglas': 0}

        tipo_liquidacion = tarifa_data.get('tipo_liquidacion', 'INSPECCION_OBRA')
        periodo_inicio_str = tarifa_data.get('periodo_inicio', '2026-01-01')
        periodo_fin_str = tarifa_data.get('periodo_fin')
        categoria = tarifa_data.get('categoria', 'C1')
        costo_por_visita = Decimal(str(tarifa_data.get('costo_por_visita', '0')))
        visitas_minimas = tarifa_data.get('visitas_minimas', 1)
        reglas = tarifa_data.get('reglas', [])

        # Log UIT info
        uit_año = tarifa_data.get('uit_año')
        uit_valor = tarifa_data.get('uit_valor')
        porcentaje_uit = tarifa_data.get('porcentaje_uit')
        if uit_año and uit_valor and porcentaje_uit:
            self._log(f"    UIT {uit_año}={uit_valor}, porcentaje={porcentaje_uit} -> costo={costo_por_visita}")

        periodo_inicio = date.fromisoformat(periodo_inicio_str)
        periodo_fin = None if periodo_fin_str is None else date.fromisoformat(periodo_fin_str)

        if self.dry_run:
            self._log(f"\n  [DRY-RUN] Would create/update TarifaLiquidacionBase INSPECCION:")
            self._log(f"    tipo_liquidacion={tipo_liquidacion}, periodo_inicio={periodo_inicio}")
            self._log(f"    categoria={categoria}, costo_por_visita={costo_por_visita}")
            result['tarifa'] = 1
            result['reglas'] = len(reglas)
            return result, update_result

        # Find or create TarifaLiquidacionBase
        # Buscar por tipo_liquidacion + periodo_inicio y verificar si tiene ReglaTarifaInspeccionObra con la categoria
        existing_bases = TarifaLiquidacionBase.objects.filter(
            tipo_liquidacion=tipo_liquidacion,
            periodo_inicio=periodo_inicio,
        ).prefetch_related('reglas_tarifa_inspeccion')

        tarifa_base = None
        tarifa_created = False
        for candidate in existing_bases:
            # Verificar si alguna ReglaTarifaInspeccionObra tiene esta categoria
            has_this_categoria = candidate.reglas_tarifa_inspeccion.filter(
                categoria=categoria
            ).exists()
            if has_this_categoria:
                tarifa_base = candidate
                tarifa_created = False
                break

        if tarifa_base is None:
            tarifa_base = TarifaLiquidacionBase.objects.create(
                tipo_liquidacion=tipo_liquidacion,
                periodo_inicio=periodo_inicio,
                periodo_fin=periodo_fin,
            )
            tarifa_created = True

        if tarifa_created:
            self._log(self.style.SUCCESS(f"    Created TarifaLiquidacionBase: {tarifa_base}"))
            result['tarifa'] = 1
        else:
            self._log(f"    Found existing TarifaLiquidacionBase: {tarifa_base}")
            update_result['tarifa'] = 1

        # Create/update TarifaPorCategoriaVisitas (NO tiene campo categoria - es solo costo/visitas)
        _, visitas_created = TarifaPorCategoriaVisitas.objects.update_or_create(
            tarifa_base=tarifa_base,
            defaults={
                'costo_por_visita': costo_por_visita,
                'visitas_minimas': visitas_minimas,
            },
        )
        self._log(f"    TarifaPorCategoriaVisitas: {'created' if visitas_created else 'updated'}")

        # Create/update ReglaTarifaInspeccionObra entries
        for regla_data in reglas:
            tramite_accion = regla_data.get('tramite_accion')

            if not tramite_accion:
                self._log(self.style.WARNING(f"    Skipping rule with missing tramite_accion"))
                continue

            valid_tramite_accion = self._validate_choice(
                tramite_accion, TramiteAccion, 'TramiteAccion'
            )

            if not valid_tramite_accion:
                continue

            _, regla_created = ReglaTarifaInspeccionObra.objects.update_or_create(
                categoria=categoria,
                tramite_accion=valid_tramite_accion,
                tarifa_base=tarifa_base,
                defaults={},
            )

            if regla_created:
                self._log(self.style.SUCCESS(
                    f"    Created ReglaTarifaInspeccionObra: {categoria}/{valid_tramite_accion}"
                ))
                result['reglas'] += 1
            else:
                self._log(f"    Found existing ReglaTarifaInspeccionObra: {categoria}/{valid_tramite_accion}")
                update_result['reglas'] += 1

        return result, update_result
