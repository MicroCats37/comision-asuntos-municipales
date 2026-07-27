"""
Management command to load real inspectores data from seed JSON.

Usage:
    python manage.py load_inspectores_reales --settings=config.settings.development
    python manage.py load_inspectores_reales --dry-run --settings=config.settings.development

Seed data:
    - backend/modules/liquidaciones/seeds/inspectores_reales.json
"""

import json
import logging
import unicodedata
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from modules.liquidaciones.domain.models.especialidades import Especialidad
from modules.liquidaciones.domain.models.inspector import Inspector
from modules.liquidaciones.domain.constants import DelegadoStatus
from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero, Capitulo


logger = logging.getLogger(__name__)


def normalize_specialty_name(name: str) -> str:
    """Remove accents/diacritics from specialty name for canonical comparison."""
    if not name:
        return name
    normalized = unicodedata.normalize('NFD', name)
    return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')


SPECIALTY_NORMALIZATION_MAP = {
    'ingenieria civil': 'Ingeniería Civil',
    'ingenieria mecanica electrica': 'Ingeniería Mecánica Eléctrica',
    'ingenieria electrica': 'Ingeniería Eléctrica',
    'ingenieria sanitaria': 'Ingeniería Sanitaria',
    'ingenieria electronica': 'Ingeniería Electrónica',
    'ingenieria de seguridad': 'Ingeniería de Seguridad',
}


def get_canonical_specialty_name(raw_name: str) -> str:
    """Return the canonical accented specialty name for a raw name from seed data."""
    if not raw_name:
        return raw_name
    base_name = raw_name.split(' - ')[0].strip()
    normalized = normalize_specialty_name(base_name).lower()
    return SPECIALTY_NORMALIZATION_MAP.get(normalized, base_name)


class Command(BaseCommand):
    help = "Cargar datos reales de inspectores desde JSON seed"

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
            help='Ruta al archivo JSON seed de inspectores',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.seed_path = (
            Path(options['seed_path'])
            if options['seed_path']
            else Path(settings.BASE_DIR) / 'modules' / 'liquidaciones' / 'seeds' / 'inspectores_reales.json'
        )

        self._log(f"\n[load_inspectores_reales] Starting...")

        if self.dry_run:
            self._log(self.style.WARNING("  DRY-RUN MODE - No database writes will occur"))

        # Load seed data
        seed_data = self._load_seed()
        if not seed_data:
            raise CommandError("Failed to load seed data")

        # Process all entries
        perfil_count = 0
        inspector_count = 0
        skipped = 0

        for idx, entry in enumerate(seed_data):
            result = self._process_entry(entry, idx + 1)
            if result['status'] == 'created':
                perfil_count += result.get('perfil_action', 0)
                inspector_count += result.get('inspector_action', 0)
            elif result['status'] == 'updated':
                inspector_count += result.get('inspector_action', 0)
            elif result['status'] == 'skipped':
                skipped += 1

        self._log(self.style.SUCCESS(
            f"\n[load_inspectores_reales] Completed successfully"
        ))
        self._log(
            f"  PerfilIngeniero records processed: {perfil_count}"
        )
        self._log(
            f"  Inspector records (created/updated): {inspector_count}"
        )
        self._log(
            f"  Skipped (no valid registros): {skipped}"
        )

    def _log(self, msg):
        """Log message safely, handling encoding issues on Windows."""
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
            safe_msg = msg.encode('ascii', 'replace').decode('ascii')
            self.stdout.write(safe_msg)

    def _load_seed(self):
        """Load JSON seed file."""
        if not self.seed_path.exists():
            raise CommandError(f"Seed file not found: {self.seed_path}")

        try:
            content = self.seed_path.read_text(encoding='utf-8')
            data = json.loads(content)
            if not isinstance(data, list):
                raise CommandError(f"Seed file must be a JSON array, got {type(data).__name__}")
            self._log(f"  Loaded seed: {len(data)} entries")
            return data
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in seed file: {e}")

    def _normalize_cip(self, cip):
        """Normalize CIP to 6 digits with leading zeros."""
        if not cip:
            return None
        cip = str(cip).strip().replace('-', '').replace(' ', '')
        if not cip.isdigit():
            return None
        return cip.zfill(6)[:6]

    def _get_or_create_capitulo(self, capitulo_data):
        """Get or create Capitulo from capitulo data in seed."""
        if not capitulo_data:
            return None

        registro_id = capitulo_data.get('registro_id')
        abreviacion = capitulo_data.get('abreviacion')
        nombre = capitulo_data.get('nombre')

        if not registro_id:
            return None

        capitulo = Capitulo.objects.filter(registro_id=registro_id).first()
        if not capitulo and abreviacion:
            capitulo = Capitulo.objects.filter(abreviacion=abreviacion).first()

        if capitulo:
            # Update if name changed
            if nombre and capitulo.nombre != nombre:
                capitulo.nombre = nombre
                capitulo.save()
            return capitulo

        capitulo, _ = Capitulo.objects.update_or_create(
            registro_id=registro_id,
            defaults={
                'abreviacion': abreviacion or f'CAP{registro_id}',
                'nombre': nombre or f'Capítulo {registro_id}',
            },
        )
        return capitulo

    def _get_or_create_especialidad(self, especialidad_nombre):
        """Get or create Especialidad by canonical name."""
        if not especialidad_nombre:
            return None

        canonical = get_canonical_specialty_name(especialidad_nombre)

        if self.dry_run:
            self._log(f"    [DRY-RUN] Would get/create especialidad: {canonical}")
            return None

        especialidad, created = Especialidad.objects.get_or_create(
            nombre=canonical,
            defaults={}
        )
        if created:
            self._log(f"    Created especialidad: {canonical}")
        return especialidad

    def _get_or_create_perfil(self, cip, identidad_data):
        """Get or create PerfilIngeniero from identidad data in seed."""
        dni = identidad_data.get('dni', '').strip()
        nombres = identidad_data.get('nombres', '').strip()
        paterno = identidad_data.get('apellido_paterno', '').strip()
        materno = identidad_data.get('apellido_materno', '').strip()
        correo = identidad_data.get('correo_personal', '').strip() or None
        codigo_esp = identidad_data.get('codigo_especialidad', '').strip() or None

        capitulo = self._get_or_create_capitulo(identidad_data.get('capitulo'))

        defaults = {
            'dni': dni,
            'nombres': nombres,
            'apellido_paterno': paterno,
            'apellido_materno': materno,
            'correo_personal': correo,
            'codigo_especialidad': codigo_esp,
            'capitulo': capitulo,
        }

        try:
            perfil = PerfilIngeniero.objects.get(cip=cip)
            # Update fields if different
            updated = False
            for field, value in defaults.items():
                if field == 'capitulo':
                    continue  # handle separately
                current = getattr(perfil, field, None)
                if current != value:
                    setattr(perfil, field, value)
                    updated = True
            if capitulo and perfil.capitulo != capitulo:
                perfil.capitulo = capitulo
                updated = True
            if updated:
                perfil.save()
                self._log(f"    Updated PerfilIngeniero CIP={cip}")
            return perfil, False
        except PerfilIngeniero.DoesNotExist:
            pass

        if self.dry_run:
            self._log(f"    [DRY-RUN] Would create PerfilIngeniero: CIP={cip}")
            return None, True

        try:
            perfil = PerfilIngeniero.objects.create(cip=cip, **defaults)
            self._log(f"    Created PerfilIngeniero: CIP={cip}")
            return perfil, True
        except Exception as e:
            self._log(self.style.ERROR(f"    Error creating PerfilIngeniero CIP={cip}: {e}"))
            return None, False

    def _process_entry(self, entry, entry_idx):
        """Process a single entry from the seed array.

        Returns dict with status, perfil_action, inspector_action.
        """
        cip = self._normalize_cip(entry.get('cip', ''))
        if not cip:
            self._log(self.style.WARNING(
                f"  Entry {entry_idx}: Invalid CIP '{entry.get('cip')}', skipping"
            ))
            return {'status': 'skipped'}

        identidad = entry.get('identidad', {})
        registros = entry.get('registros', [])

        if not registros:
            self._log(self.style.WARNING(
                f"  Entry {entry_idx}: No registros for CIP {cip}, skipping"
            ))
            return {'status': 'skipped'}

        # Get or create PerfilIngeniero
        perfil, perfil_created = self._get_or_create_perfil(cip, identidad)
        if not perfil:
            return {'status': 'skipped'}

        perfil_action = 1 if perfil_created else 0

        # Process each registro — creates one Inspector per registro entry
        inspector_created = 0
        inspector_updated = 0

        for reg in registros:
            tipo_liq = reg.get('tipo_liquidacion', '').strip()
            especialidad_nombre = reg.get('especialidad', '').strip()
            numero_registro = reg.get('numero_registro', '').strip()
            categoria = reg.get('categoria')
            vigencia_str = reg.get('vigencia', '').strip()

            if not tipo_liq or not numero_registro:
                self._log(self.style.WARNING(
                    f"  Entry {entry_idx} CIP={cip}: Missing tipo_liquidacion or numero_registro, skipping registro"
                ))
                continue

            # Get or create Especialidad
            especialidad = self._get_or_create_especialidad(especialidad_nombre)
            if not especialidad and not self.dry_run:
                self._log(self.style.WARNING(
                    f"  Entry {entry_idx} CIP={cip}: Especialidad '{especialidad_nombre}' not found, skipping"
                ))
                continue

            reg_result = self._upsert_inspector(
                perfil=perfil,
                especialidad=especialidad,
                tipo_liquidacion=tipo_liq,
                numero_registro=numero_registro,
                categoria=categoria,
                vigencia_str=vigencia_str,
                entry_idx=entry_idx,
                cip=cip,
            )

            if reg_result == 'created':
                inspector_created += 1
            elif reg_result == 'updated':
                inspector_updated += 1

        total = inspector_created + inspector_updated
        if total == 0:
            return {
                'status': 'skipped',
                'perfil_action': perfil_action,
                'inspector_action': 0,
            }

        return {
            'status': 'created' if inspector_created > 0 else 'updated',
            'perfil_action': perfil_action,
            'inspector_action': total,
        }

    def _upsert_inspector(
        self, perfil, especialidad, tipo_liquidacion, numero_registro,
        categoria, vigencia_str, entry_idx, cip
    ):
        """Upsert a single Inspector record.

        Returns 'created', 'updated', or 'skipped'.
        """
        from datetime import datetime

        # Parse vigencia date
        vigencia = None
        if vigencia_str:
            try:
                vigencia = datetime.strptime(vigencia_str, '%Y-%m-%d').date()
            except ValueError:
                self._log(self.style.WARNING(
                    f"  Entry {entry_idx} CIP={cip}: Invalid vigencia '{vigencia_str}', skipping"
                ))
                return 'skipped'

        if self.dry_run:
            self._log(
                f"    [DRY-RUN] Would upsert Inspector: CIP={cip}, "
                f"tipo={tipo_liquidacion}, esp={especialidad}, "
                f"registro={numero_registro}, vigencia={vigencia_str}"
            )
            return 'created'

        defaults = {
            'categoria': categoria,
            'vigencia': vigencia,
            'status': DelegadoStatus.ACTIVO,
        }
        if especialidad:
            defaults['especialidad'] = especialidad

        inspector, created = Inspector.objects.update_or_create(
            perfil_ingeniero=perfil,
            tipo_liquidacion=tipo_liquidacion,
            numero_registro=numero_registro,
            defaults=defaults,
        )

        action = 'created' if created else 'updated'
        self._log(
            f"    {action} Inspector: CIP={cip}, tipo={tipo_liquidacion}, "
            f"esp={especialidad}, registro={numero_registro}"
        )
        return 'created' if created else 'updated'
