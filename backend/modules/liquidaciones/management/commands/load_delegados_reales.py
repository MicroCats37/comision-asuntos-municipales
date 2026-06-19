"""
Management command to load real delegados data from seed JSON.

Usage:
    python manage.py load_delegados_reales --settings=config.settings.development
    python manage.py load_delegados_reales --dry-run --settings=config.settings.development
    python manage.py load_delegados_reales --skip-endpoint --settings=config.settings.development

Seed data sources:
  - backend/modules/liquidaciones/seeds/delegados_reales.json   (municipalidades/delegados/asignaciones)
  - backend/modules/liquidaciones/seeds/colegiados_reales.json  (PerfilIngeniero/Capitulo materializado)
Endpoint: http://172.16.93.83:9001/api/v1/colegiado/{cip}
"""

import json
import logging
from pathlib import Path

import requests
from django.conf import settings
from django.db import IntegrityError, transaction

from django.core.management.base import BaseCommand, CommandError

from modules.entidades.models import Banco
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.liquidaciones.domain.models.delegado import Delegado, TipoDelegado, MunicipalidadDelegado
from modules.liquidaciones.domain.models.especialidades import Especialidad
from modules.liquidaciones.domain.constants import DelegadoStatus
from modules.usuarios.models import PerfilIngeniero
from modules.usuarios.domain.models.perfil_ingeniero import Capitulo


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Cargar datos reales de delegados desde JSON seed"

    COLEGIADO_ENDPOINT = "http://172.16.93.83:9001/api/v1/colegiado/{cip}"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validar datos seed y parsing sin escribir en la base de datos',
        )
        parser.add_argument(
            '--skip-endpoint',
            action='store_true',
            help='Omitir obtener detalles del Colegio desde el endpoint, usar solo datos seed',
        )
        parser.add_argument(
            '--seed-path',
            type=str,
            default=None,
            help='Ruta al archivo JSON seed de delegados',
        )
        parser.add_argument(
            '--colegiados-seed-path',
            type=str,
            default=None,
            help='Ruta al archivo JSON seed de colegiados (datos de PerfilIngeniero/Capitulo)',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.skip_endpoint = options['skip_endpoint']
        self.seed_path = (
            Path(options['seed_path'])
            if options['seed_path']
            else Path(settings.BASE_DIR) / 'modules' / 'liquidaciones' / 'seeds' / 'delegados_reales.json'
        )
        self.colegiados_seed_path = (
            Path(options['colegiados_seed_path'])
            if options['colegiados_seed_path']
            else Path(settings.BASE_DIR) / 'modules' / 'liquidaciones' / 'seeds' / 'colegiados_reales.json'
        )

        self._log(f"\n[load_delegados_reales] Starting...")

        if self.dry_run:
            self._log(self.style.WARNING("  DRY-RUN MODE - No database writes will occur"))

        # Load colegiados seed into memory by CIP
        self.colegiados_seed_data = self._load_colegiados_seed()

        # Load seed data
        seed_data = self._load_seed()
        if not seed_data:
            raise CommandError("Failed to load seed data")

        # Ensure required specialties exist
        self._ensure_especialidades()

        # Process municipalities
        muni_count = self._process_municipalidades(seed_data.get('municipalidades', []))

        # Process delegates
        dele_count = self._process_delegados(seed_data.get('delegados', []))

        # Process municipality-delegate assignments
        asign_count = self._process_asignaciones(seed_data.get('asignaciones', []))

        self._log(self.style.SUCCESS(
            f"\n  Completed: {muni_count} municipalidades, {dele_count} delegados, {asign_count} asignaciones processed"
        ))

    def _log(self, msg):
        """Registra mensaje de forma segura, manejando problemas de codificación en Windows."""
        try:
            self.stdout.write(msg)
        except UnicodeEncodeError:
            # Respaldo para problemas de codificación en consola Windows
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
            return data
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in seed file: {e}")

    def _load_colegiados_seed(self):
        """Cargar archivo JSON seed de colegiados en memoria, indexado por CIP."""
        if not self.colegiados_seed_path.exists():
            self._log(self.style.WARNING(
                f"  Colegiados seed file not found: {self.colegiados_seed_path} - will use endpoint or fallback"
            ))
            return {}

        try:
            content = self.colegiados_seed_path.read_text(encoding='utf-8')
            data = json.loads(content)
            colegiados = data.get('colegiados', [])
            by_cip = {item['cip']: item for item in colegiados}
            self._log(f"  Loaded colegiados seed: {len(by_cip)} records")
            return by_cip
        except json.JSONDecodeError as e:
            self._log(self.style.WARNING(
                f"  Invalid JSON in colegiados seed file: {e} - will use endpoint or fallback"
            ))
            return {}

    def _ensure_especialidades(self):
        """Asegurar que las especialidades requeridas existan en la base de datos."""
        required_specialties = [
            'Ingeniería Sanitaria',
            'Ingeniería Civil',
            'Habilitación Urbana',
        ]

        for spec_name in required_specialties:
            if self.dry_run:
                self._log(f"    [DRY-RUN] Would create/find especialidad: {spec_name}")
            else:
                spec, created = Especialidad.objects.get_or_create(
                    nombre=spec_name,
                    defaults={}
                )
                if created:
                    self._log(self.style.SUCCESS(f"    Created especialidad: {spec_name}"))
                else:
                    self._log(f"    Found existing especialidad: {spec_name}")

    def _normalize_cip(self, cip):
        """Normaliza CIP a 6 dígitos con ceros iniciales."""
        if not cip:
            return None
        cip = str(cip).strip().replace('-', '').replace(' ', '')
        if not cip.isdigit():
            return None
        return cip.zfill(6)[:6]

    def _get_or_fetch_colegiado(self, cip):
        """Obtiene detalles del colegiado desde el endpoint o retorna None."""
        if self.skip_endpoint:
            return None

        normalized_cip = self._normalize_cip(cip)
        if not normalized_cip:
            return None

        url = self.COLEGIADO_ENDPOINT.format(cip=normalized_cip)
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self._log(f"    Fetched endpoint data for CIP {normalized_cip}")
                return data
            else:
                self._log(self.style.WARNING(
                    f"    Endpoint returned {response.status_code} for CIP {normalized_cip}"
                ))
                return None
        except requests.RequestException as e:
            self._log(self.style.WARNING(
                f"    Endpoint unavailable for CIP {normalized_cip}: {e}"
            ))
            return None

    def _process_municipalidades(self, municipalidades):
        """Crear/actualizar municipalidades desde datos seed."""
        count = 0
        seen_codes = set()  # Seguimiento de códigos en esta ejecución para detectar duplicados
        duplicate_codes = set()

        for muni_data in municipalidades:
            nombre = muni_data.get('nombre', '').strip()
            if not nombre:
                continue

            # Use pre-generated code from seed data
            code = muni_data.get('codigo', '').strip()
            if not code:
                self._log(self.style.ERROR(
                    f"    ERROR: Municipality '{nombre}' is missing a 'codigo' field in seed data"
                ))
                continue

            # Check for duplicate codes within this seed data
            if code in seen_codes:
                duplicate_codes.add(code)
                self._log(self.style.ERROR(
                    f"    DUPLICATE CODE: '{code}' used for both '{nombre}' and previously seen municipality"
                ))
            seen_codes.add(code)

            if self.dry_run:
                self._log(f"    [DRY-RUN] Would create/update municipalidad: {nombre} (code={code})")
            else:
                muni, created = Municipalidad.objects.update_or_create(
                    codigo=code,
                    defaults={
                        'nombre': nombre,
                        'provincia': muni_data.get('provincia'),
                        'distrito': muni_data.get('distrito'),
                        'activo': True,
                    }
                )
                action = "created" if created else "updated"
                self._log(f"    {action} municipalidad: {nombre}")

            count += 1

        # Report any duplicates found
        if duplicate_codes:
            dup_list = ', '.join(sorted(duplicate_codes))
            self._log(self.style.ERROR(
                f"\n  ERROR: Found {len(duplicate_codes)} duplicate municipality codes in seed data: {dup_list}"
            ))
            raise CommandError(f"Duplicate municipality codes detected: {dup_list}")

        return count

    def _process_asignaciones(self, asignaciones):
        """Crear/actualizar asignaciones MunicipalidadDelegado desde datos seed."""
        count = 0
        for asignacion in asignaciones:
            cip = self._normalize_cip(asignacion.get('cip', ''))
            muni_code = asignacion.get('municipalidad_codigo')
            if not cip or not muni_code:
                continue

            if self.dry_run:
                self._log(
                    f"    [DRY-RUN] Would assign delegado CIP={cip} to municipalidad={muni_code}"
                )
                count += 1
                continue

            try:
                delegado = Delegado.objects.select_related('perfil_ingeniero').get(
                    perfil_ingeniero__cip=cip
                )
                municipalidad = Municipalidad.objects.get(codigo=muni_code)
                _, created = MunicipalidadDelegado.objects.update_or_create(
                    delegado=delegado,
                    municipalidad=municipalidad,
                    defaults={'activo': True},
                )
                action = 'created' if created else 'updated'
                self._log(
                    f"    {action} asignación: {delegado.perfil_ingeniero.cip} @ {municipalidad.nombre}"
                )
                count += 1
            except Delegado.DoesNotExist:
                self._log(self.style.WARNING(f"    Delegado not found for CIP {cip}, skipping assignment"))
            except Municipalidad.DoesNotExist:
                self._log(self.style.WARNING(f"    Municipalidad not found for code {muni_code}, skipping assignment"))

        return count

    def _process_delegados(self, delegados):
        """Crear/actualizar delegados desde datos seed."""
        count = 0
        endpoint_data_cache = {}

        for dele_data in delegados:
            cip = self._normalize_cip(dele_data.get('cip', ''))
            if not cip:
                self._log(self.style.WARNING(
                    f"    Skipping delegado with invalid CIP: {dele_data.get('cip')}"
                ))
                continue

            nombre_completo = dele_data.get('nombre_completo', '')
            especialidad_nombre = dele_data.get('especialidad', 'Ingeniería Civil')
            tipo = dele_data.get('tipo', 'titular')

            # Fetch from endpoint if not skipped
            if not self.skip_endpoint and cip not in endpoint_data_cache:
                endpoint_data_cache[cip] = self._get_or_fetch_colegiado(cip)

            endpoint_data = endpoint_data_cache.get(cip)

            # Get or create PerfilIngeniero
            perfil = self._get_or_create_perfil(
                cip=cip,
                dele_data=dele_data,
                endpoint_data=endpoint_data,
            )

            if not perfil and not self.dry_run:
                self._log(self.style.ERROR(
                    f"    Failed to get/create PerfilIngeniero for CIP {cip}"
                ))
                continue

            # Get especialidad
            especialidad = None
            try:
                especialidad = Especialidad.objects.get(nombre=especialidad_nombre)
            except Especialidad.DoesNotExist:
                if self.dry_run:
                    self._log(f"    [DRY-RUN] Especialidad '{especialidad_nombre}' not found in DB, skipping DB validation")
                else:
                    self._log(self.style.WARNING(
                        f"    Especialidad not found: {especialidad_nombre}, skipping delegado {cip}"
                    ))
                    continue

            # Determine tipo
            tipo_delegado = TipoDelegado.TITULAR if tipo == 'titular' else TipoDelegado.ALTERNO

            if self.dry_run:
                self._log(f"    [DRY-RUN] Would create/update delegado: {nombre_completo} (CIP={cip}, tipo={tipo})")
            else:
                delegado, created = Delegado.objects.update_or_create(
                    perfil_ingeniero=perfil,
                    defaults={
                        'tipo': tipo_delegado,
                        'especialidad': especialidad,
                        'banco': None,  # Banco remains null
                        'status': DelegadoStatus.ACTIVO,
                    }
                )
                action = "created" if created else "updated"
                self._log(f"    {action} delegado: {nombre_completo}")

            count += 1

        return count

    def _get_or_create_perfil(self, cip, dele_data, endpoint_data):
        """Obtener o crear PerfilIngeniero.

        Prioridad:
        a) Usar colegiados_seed_data si está disponible (seed local - preferido)
        b) Obtener desde endpoint si no se omitió
        c) Recurrir a datos seed mínimos de delegados_reales.json
        """
        # Check if we have colegiados seed data for this CIP
        colegiados_seed_item = self.colegiados_seed_data.get(cip)

        # Try to find existing
        try:
            perfil = PerfilIngeniero.objects.get(cip=cip)
            # Update from colegiados seed, endpoint, or skip if dry-run
            if not self.dry_run:
                if colegiados_seed_item:
                    self._update_perfil_from_seed(perfil, colegiados_seed_item)
                elif endpoint_data:
                    self._update_perfil_from_endpoint(perfil, endpoint_data)
            return perfil
        except PerfilIngeniero.DoesNotExist:
            pass

        if self.dry_run:
            if colegiados_seed_item:
                self._log(f"    [DRY-RUN] Would create PerfilIngeniero from colegiados_seed: CIP={cip}")
            elif endpoint_data:
                self._log(f"    [DRY-RUN] Would create PerfilIngeniero from endpoint: CIP={cip}")
            else:
                self._log(f"    [DRY-RUN] Would create PerfilIngeniero from seed: CIP={cip}")
            return None

        # Create from colegiados seed (preferred), endpoint, or fallback seed
        if colegiados_seed_item:
            return self._create_perfil_from_colegiados_seed(cip, colegiados_seed_item)
        elif endpoint_data:
            return self._create_perfil_from_endpoint(cip, endpoint_data)
        else:
            return self._create_perfil_from_seed(cip, dele_data)

    def _create_perfil_from_seed(self, cip, dele_data):
        """Crear PerfilIngeniero desde datos seed."""
        try:
            perfil = PerfilIngeniero.objects.create(
                cip=cip,
                nombres=dele_data.get('nombre', ''),
                apellido_paterno=dele_data.get('paterno', ''),
                apellido_materno=dele_data.get('materno', ''),
            )
            self._log(f"    Created PerfilIngeniero from seed: {dele_data.get('nombre_completo')}")
            return perfil
        except Exception as e:
            self._log(self.style.ERROR(f"    Error creating PerfilIngeniero: {e}"))
            return None

    def _create_perfil_from_colegiados_seed(self, cip, colegiados_seed_item):
        """Crear PerfilIngeniero desde datos seed materializados de colegiados."""
        try:
            capitulo = self._get_or_create_capitulo_from_seed(colegiados_seed_item.get('capitulo'))
            defaults = {
                'dni': colegiados_seed_item.get('dni') or '',
                'nombres': colegiados_seed_item.get('nombres') or '',
                'apellido_paterno': colegiados_seed_item.get('apellido_paterno') or '',
                'apellido_materno': colegiados_seed_item.get('apellido_materno') or '',
                'fecha_nacimiento': colegiados_seed_item.get('fecha_nacimiento') or None,
                'genero': colegiados_seed_item.get('genero') or None,
                'correo_personal': colegiados_seed_item.get('correo_personal') or None,
                'correo_institucional': colegiados_seed_item.get('correo_institucional') or None,
                'direccion': colegiados_seed_item.get('direccion') or None,
                'ubigeo': colegiados_seed_item.get('ubigeo') or None,
                'codigo_especialidad': colegiados_seed_item.get('codigo_especialidad') or None,
                'capitulo': capitulo,
            }
            perfil = PerfilIngeniero.objects.create(cip=cip, **defaults)
            self._log(f"    Created PerfilIngeniero from colegiados_seed: {perfil.nombre_completo}")
            return perfil
        except Exception as e:
            self._log(self.style.ERROR(f"    Error creating PerfilIngeniero from colegiados_seed for CIP {cip}: {e}"))
            return None

    def _update_perfil_from_seed(self, perfil, colegiados_seed_item):
        """Actualizar PerfilIngeniero existente desde datos seed de colegiados."""
        try:
            capitulo = self._get_or_create_capitulo_from_seed(colegiados_seed_item.get('capitulo'))
            fields_to_update = [
                'dni', 'nombres', 'apellido_paterno', 'apellido_materno',
                'fecha_nacimiento', 'genero', 'correo_personal', 'correo_institucional',
                'direccion', 'ubigeo', 'codigo_especialidad', 'capitulo',
            ]
            for field in fields_to_update:
                if field == 'capitulo':
                    setattr(perfil, field, capitulo)
                else:
                    value = colegiados_seed_item.get(field)
                    if value is not None:
                        setattr(perfil, field, value)
            perfil.save()
            self._log(f"    Updated PerfilIngeniero from colegiados_seed: {perfil.nombre_completo}")
        except Exception as e:
            self._log(self.style.WARNING(f"    Error updating PerfilIngeniero from seed: {e}"))

    def _get_or_create_capitulo_from_seed(self, capitulo_data):
        """Obtener o crear Capitulo desde datos seed."""
        if not capitulo_data:
            return None

        registro_id = capitulo_data.get('registro_id')
        abreviacion = capitulo_data.get('abreviacion')
        if not registro_id:
            return None

        capitulo = Capitulo.objects.filter(registro_id=registro_id).first()
        if not capitulo and abreviacion:
            capitulo = Capitulo.objects.filter(abreviacion=abreviacion).first()

        if capitulo:
            capitulo.nombre = capitulo_data.get('nombre') or capitulo.nombre
            capitulo.grupo_envio_intitucional = (
                capitulo_data.get('grupo_envio_intitucional') or capitulo.grupo_envio_intitucional
            )
            capitulo.save()
            return capitulo

        capitulo, _ = Capitulo.objects.update_or_create(
            registro_id=registro_id,
            defaults={
                'abreviacion': abreviacion or f'CAP{registro_id}',
                'nombre': capitulo_data.get('nombre') or f'Capítulo {registro_id}',
                'grupo_envio_intitucional': capitulo_data.get('grupo_envio_intitucional') or None,
            },
        )
        return capitulo

    def _create_perfil_from_endpoint(self, cip, endpoint_data):
        """Crear o reutilizar PerfilIngeniero desde datos del endpoint."""
        try:
            defaults = self._perfil_defaults_from_endpoint(endpoint_data)
            dni = defaults.get('dni')
            perfil = PerfilIngeniero.objects.filter(dni=dni).first() if dni else None

            if perfil:
                perfil.cip = cip
                for field, value in defaults.items():
                    setattr(perfil, field, value)
                perfil.save()
                self._log(f"    Updated PerfilIngeniero by DNI from endpoint: {perfil.nombre_completo}")
            else:
                perfil = PerfilIngeniero.objects.create(cip=cip, **defaults)
                self._log(f"    Created PerfilIngeniero from endpoint: {perfil.nombre_completo}")
            return perfil
        except Exception as e:
            self._log(self.style.ERROR(f"    Error creating PerfilIngeniero from endpoint for CIP {cip}: {e}"))
            return None

    def _update_perfil_from_endpoint(self, perfil, endpoint_data):
        """Actualizar PerfilIngeniero existente con datos del endpoint."""
        try:
            defaults = self._perfil_defaults_from_endpoint(endpoint_data)
            for field, value in defaults.items():
                setattr(perfil, field, value)
            perfil.save()
            self._log(f"    Updated PerfilIngeniero from endpoint: {perfil.nombre_completo}")
        except Exception as e:
            self._log(self.style.WARNING(f"    Error updating PerfilIngeniero: {e}"))

    def _perfil_defaults_from_endpoint(self, endpoint_data):
        """Mapear payload del endpoint CIP a campos de PerfilIngeniero."""
        nombre1 = (endpoint_data.get('nombre1') or '').strip()
        nombre2 = (endpoint_data.get('nombre2') or '').strip()
        nombres = ' '.join(part for part in [nombre1, nombre2] if part).strip()
        capitulo = self._get_or_create_capitulo_from_endpoint(endpoint_data)
        return {
            'dni': (endpoint_data.get('dni') or '').strip(),
            'nombres': nombres,
            'apellido_paterno': (endpoint_data.get('paterno') or '').strip(),
            'apellido_materno': (endpoint_data.get('materno') or '').strip(),
            'fecha_nacimiento': endpoint_data.get('fechaNacimiento') or None,
            'genero': endpoint_data.get('codGenero') or None,
            'correo_personal': endpoint_data.get('correoPers') or None,
            'correo_institucional': endpoint_data.get('correoInst') or None,
            'direccion': endpoint_data.get('direccion') or None,
            'ubigeo': endpoint_data.get('distritoId') or None,
            'codigo_especialidad': endpoint_data.get('codEspecialidad') or None,
            'capitulo': capitulo,
        }

    def _get_or_create_capitulo_from_endpoint(self, endpoint_data):
        capitulo_data = endpoint_data.get('capitulo') or {}
        registro_id = endpoint_data.get('codCapitulo') or capitulo_data.get('id')
        abreviacion = capitulo_data.get('abreviatura') or registro_id
        if not registro_id:
            return None

        capitulo = Capitulo.objects.filter(registro_id=registro_id).first()
        if not capitulo and abreviacion:
            capitulo = Capitulo.objects.filter(abreviacion=abreviacion).first()

        if capitulo:
            capitulo.nombre = capitulo_data.get('descripcion') or capitulo.nombre
            capitulo.grupo_envio_intitucional = (
                capitulo_data.get('grupoEnviosInst') or capitulo.grupo_envio_intitucional
            )
            capitulo.save()
            return capitulo

        capitulo, _ = Capitulo.objects.update_or_create(
            registro_id=registro_id,
            defaults={
                'abreviacion': abreviacion,
                'nombre': capitulo_data.get('descripcion') or f'Capítulo {registro_id}',
                'grupo_envio_intitucional': capitulo_data.get('grupoEnviosInst') or None,
            },
        )
        return capitulo
