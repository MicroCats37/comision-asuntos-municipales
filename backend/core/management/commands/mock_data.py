"""
Management command to populate mock data for all domain tables.

Usage:
    python manage.py mock_data --settings=config.settings.development

This command is idempotent — running it multiple times will not create duplicates.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction

from django.core.management.base import BaseCommand

Usuario = get_user_model()

# Import all domain models
from modules.usuarios.models import PerfilIngeniero
from modules.usuarios.domain.models.perfil_ingeniero import Capitulo
from modules.entidades.models import Empresa, Municipalidad, Banco, Contacto
from modules.entidades.models import EmpresaContacto, MunicipalidadContacto, BancoContacto
from modules.liquidaciones.models import Delegado, Proyectista, Liquidacion, Revision, RevisionDelegado, Igv, Uit
from modules.liquidaciones.domain.constants import DelegadoStatus


# Valid districts from ubigeo.json (Lima metro area) — full hierarchical format
VALID_DISTRICTS = [
    "LIMA - LIMA - MIRAFLORES",
    "LIMA - LIMA - SAN ISIDRO",
    "LIMA - LIMA - SAN BORJA",
    "LIMA - LIMA - LINCE",
    "LIMA - LIMA - PUEBLO LIBRE",
    "LIMA - LIMA - MAGDALENA DEL MAR",
    "LIMA - LIMA - SURQUILLO",
    "LIMA - LIMA - BARRANCO",
]


class Command(BaseCommand):
    help = "Populate mock data for all domain tables (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-admin",
            action="store_true",
            help="Skip creating the admin user (if already created via create_admin)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("Starting mock data seed..."))
        self.stdout.write(self.style.SUCCESS("=" * 60))

        if not options["skip_admin"]:
            self._create_admin_user()
        else:
            self.stdout.write(self.style.WARNING("Skipping admin user creation"))

        self._create_capitulos()
        self._create_igv_uit()
        self._create_bancos()
        self._create_municipalidades()
        self._create_empresas()
        self._create_contactos()
        self._create_entity_contact_relations()
        self._create_perfiles_ingenieros()
        self._create_delegados()
        self._create_proyectistas()
        self._create_liquidaciones()

        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("Mock data seed completed successfully!"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

    def _create_admin_user(self):
        self.stdout.write("\n[1/11] Creating admin user...")
        defaults = {
            "nombres": "Admin",
            "apellidos": "Sistema",
            "email": "admin@example.com",
            "username": "admin",
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        }
        user, created = Usuario.objects.update_or_create(
            dni="00000000",
            defaults=defaults,
        )
        user.set_password("admin")
        user.save(update_fields=["password"])
        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"  Admin user {action}: DNI=00000000"))

    def _create_capitulos(self):
        self.stdout.write("\n[2/11] Creating capítulos profesionales...")
        capitulos_data = [
            {"registro_id": "01", "abreviacion": "CIVIL", "nombre": "Capítulo de Ingeniería Civil"},
            {"registro_id": "02", "abreviacion": "ELECT", "nombre": "Capítulo de Ingeniería Electrónica"},
            {"registro_id": "03", "abreviacion": "ARQUI", "nombre": "Capítulo de Arquitectura"},
        ]
        for data in capitulos_data:
            capitulo, created = Capitulo.objects.update_or_create(
                registro_id=data["registro_id"],
                defaults=data,
            )
            action = "created" if created else "updated"
            self.stdout.write(self.style.SUCCESS(f"  Capítulo {action}: { capitulo.nombre }"))

    def _create_igv_uit(self):
        self.stdout.write("\n[3/11] Creating IGV and UIT rates...")
        today = date.today()

        # IGV - 18% (current rate)
        igv, created = Igv.objects.update_or_create(
            porcentaje=Decimal("18.00"),
            fecha_inicio=date(1991, 3, 1),
            defaults={"fecha_fin": None},
        )
        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"  IGV {action}: {igv.porcentaje}%"))

        # IGV - 19% (older rate for testing)
        igv_old, created = Igv.objects.update_or_create(
            porcentaje=Decimal("19.00"),
            fecha_inicio=date(1990, 2, 1),
            defaults={"fecha_fin": date(1991, 2, 28)},
        )
        self.stdout.write(self.style.SUCCESS(f"  IGV old {created and 'created' or 'updated'}: {igv_old.porcentaje}%"))

        # UIT - current year
        uit_current, created = Uit.objects.update_or_create(
            porcentaje=Decimal("6.00"),  # 6% UIT rate
            fecha_inicio=date(today.year, 1, 1),
            defaults={"fecha_fin": None},
        )
        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"  UIT current {action}: {uit_current.porcentaje}%"))

        # UIT - previous year
        uit_prev, created = Uit.objects.update_or_create(
            porcentaje=Decimal("6.00"),
            fecha_inicio=date(today.year - 1, 1, 1),
            defaults={"fecha_fin": date(today.year - 1, 12, 31)},
        )
        self.stdout.write(self.style.SUCCESS(f"  UIT prev {created and 'created' or 'updated'}: {uit_prev.porcentaje}%"))

    def _create_bancos(self):
        self.stdout.write("\n[4/11] Creating bancos...")
        bancos_data = [
            {"codigo": "001", "nombre": "Banco de la Nación"},
            {"codigo": "002", "nombre": "Banco de Crédito del Perú"},
            {"codigo": "003", "nombre": "Scotiabank Perú"},
        ]
        for data in bancos_data:
            banco, created = Banco.objects.update_or_create(
                codigo=data["codigo"],
                defaults={**data, "activo": True},
            )
            action = "created" if created else "updated"
            self.stdout.write(self.style.SUCCESS(f"  Banco {action}: {banco.nombre}"))

    def _create_municipalidades(self):
        self.stdout.write("\n[5/11] Creating municipalidades...")
        municipalidades_data = [
            {
                "codigo": "MUN001",
                "nombre": "Municipalidad Provincial de Lima",
                "alcalde": "Janet Show Cut",
                "gerente_urbano": "Carlos Mendoza Pérez",
                "telefono_contacto": "01-123-4567",
                "direccion": "Av. Paseo de la República S/N",
            },
            {
                "codigo": "MUN002",
                "nombre": "Municipalidad Distrital de Miraflores",
                "alcalde": "Jorge Muñoz Wells",
                "gerente_urbano": "María Elena Cevallos",
                "telefono_contacto": "01-234-5678",
                "direccion": "Av. Larco 1300",
            },
            {
                "codigo": "MUN003",
                "nombre": "Municipalidad Distrital de San Isidro",
                "alcalde": "Gustavo Rivera Pérez",
                "gerente_urbano": "Roberto López García",
                "telefono_contacto": "01-345-6789",
                "direccion": "Av. Javier Prado Este 2100",
            },
        ]
        for data in municipalidades_data:
            muni, created = Municipalidad.objects.update_or_create(
                codigo=data["codigo"],
                defaults={**data, "activo": True},
            )
            action = "created" if created else "updated"
            self.stdout.write(self.style.SUCCESS(f"  Municipalidad {action}: {muni.nombre}"))

    def _create_empresas(self):
        self.stdout.write("\n[6/11] Creating empresas...")
        empresas_data = [
            {
                "ruc": "20123456789",
                "razon_social": "Constructora Nacional S.A.",
                "nombre_comercial": "Cons Nacional",
                "direccion": "Av. Arenales 1234, Lima",
                "distrito": "MIRAFLORES",
                "telefono": "01-456-7890",
                "email": "contacto@consnacional.com",
            },
            {
                "ruc": "20987654321",
                "razon_social": "Ingeniería y Proyectos S.A.C.",
                "nombre_comercial": "Ingeniería & Proyectos",
                "direccion": "Calle Las Palmeras 456, Lima",
                "distrito": "SAN ISIDRO",
                "telefono": "01-567-8901",
                "email": "info@ingenieriaproyectos.com",
            },
            {
                "ruc": "20555111333",
                "razon_social": "Consultora Andina E.I.R.L.",
                "nombre_comercial": "Consultora Andina",
                "direccion": "Av. Libertadores 789, Lima",
                "distrito": "SAN BORJA",
                "telefono": "01-678-9012",
                "email": "ventas@consultoraandina.com",
            },
        ]
        for data in empresas_data:
            empresa, created = Empresa.objects.update_or_create(
                ruc=data["ruc"],
                defaults={**data, "activo": True},
            )
            action = "created" if created else "updated"
            self.stdout.write(self.style.SUCCESS(f"  Empresa {action}: {empresa.razon_social}"))

    def _create_contactos(self):
        self.stdout.write("\n[7/11] Creating contactos...")
        contactos_data = [
            {
                "nombres": "Juan",
                "apellidos": "Pérez García",
                "cargo": "Gerente de Proyectos",
                "telefono": "01-111-2222",
                "celular": "999-111-222",
                "email": "juan.perez@empresa.com",
            },
            {
                "nombres": "María",
                "apellidos": "López Fernández",
                "cargo": "Jefe de Compras",
                "telefono": "01-222-3333",
                "celular": "999-222-333",
                "email": "maria.lopez@empresa.com",
            },
            {
                "nombres": "Carlos",
                "apellidos": "Rodríguez Sánchez",
                "cargo": "Director Técnico",
                "telefono": "01-333-4444",
                "celular": "999-333-444",
                "email": "carlos.rodriguez@municipalidad.com",
            },
            {
                "nombres": "Ana",
                "apellidos": "Martínez Rivera",
                "cargo": "Coordinadora de Área",
                "telefono": "01-444-5555",
                "celular": "999-444-555",
                "email": "ana.martinez@banco.com",
            },
            {
                "nombres": "Pedro",
                "apellidos": "González Torres",
                "cargo": "Subgerente de Obras",
                "telefono": "01-555-6666",
                "celular": "999-555-666",
                "email": "pedro.gonzalez@municipalidad.com",
            },
        ]
        for data in contactos_data:
            contacto, created = Contacto.objects.update_or_create(
                email=data["email"],
                defaults={**data, "activo": True},
            )
            action = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(f"  Contacto {action}: {contacto.nombres} {contacto.apellidos}")
            )

    def _create_entity_contact_relations(self):
        self.stdout.write("\n[8/11] Creating entity-contact relations...")

        # Get entities
        try:
            empresa1 = Empresa.objects.get(ruc="20123456789")
            empresa2 = Empresa.objects.get(ruc="20987654321")
            muni1 = Municipalidad.objects.get(codigo="MUN001")
            muni2 = Municipalidad.objects.get(codigo="MUN002")
            banco1 = Banco.objects.get(codigo="001")
            banco2 = Banco.objects.get(codigo="002")
            contacto1 = Contacto.objects.get(email="juan.perez@empresa.com")
            contacto2 = Contacto.objects.get(email="maria.lopez@empresa.com")
            contacto3 = Contacto.objects.get(email="carlos.rodriguez@municipalidad.com")
            contacto4 = Contacto.objects.get(email="ana.martinez@banco.com")
            contacto5 = Contacto.objects.get(email="pedro.gonzalez@municipalidad.com")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error getting entities: {e}"))
            return

        # EmpresaContacto relations
        relations = [
            (empresa1, contacto1, True, "Gerente de Proyectos principal"),
            (empresa1, contacto2, False, "Jefe de Compras"),
            (empresa2, contacto2, True, "Contacto principal de compras"),
        ]
        for empresa, contacto, principal, desc in relations:
            rel, created = EmpresaContacto.objects.update_or_create(
                empresa=empresa,
                contacto=contacto,
                defaults={"principal": principal, "descripcion": desc, "activo": True},
            )
            action = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(f"  EmpresaContacto {action}: {contacto.nombres} @ {empresa.razon_social}")
            )

        # MunicipalidadContacto relations
        muni_relations = [
            (muni1, contacto3, True, "Director Técnico principal"),
            (muni2, contacto5, False, "Subgerente de Obras"),
        ]
        for muni, contacto, principal, desc in muni_relations:
            rel, created = MunicipalidadContacto.objects.update_or_create(
                municipalidad=muni,
                contacto=contacto,
                defaults={"principal": principal, "descripcion": desc, "activo": True},
            )
            action = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(f"  MunicipalidadContacto {action}: {contacto.nombres} @ {muni.nombre}")
            )

        # BancoContacto relations
        banco_relations = [
            (banco1, contacto4, True, "Coordinadora de Área principal"),
            (banco2, contacto4, False, "Coordinadora de Área"),
        ]
        for banco, contacto, principal, desc in banco_relations:
            rel, created = BancoContacto.objects.update_or_create(
                banco=banco,
                contacto=contacto,
                defaults={"principal": principal, "descripcion": desc, "activo": True},
            )
            action = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(f"  BancoContacto {action}: {contacto.nombres} @ {banco.nombre}")
            )

    def _create_perfiles_ingenieros(self):
        self.stdout.write("\n[9/11] Creating perfiles de ingenieros...")

        capitulo_civil = Capitulo.objects.get(registro_id="01")

        perfiles_data = [
            {
                "dni": "12345678",
                "nombres": "Roberto Carlos",
                "apellido_paterno": "García",
                "apellido_materno": "López",
                "cip": "CIP-12345",
                "correo_personal": "roberto.garcia@gmail.com",
                "correo_institucional": "rgarcia@cip.pe",
                "direccion": "Av. Brasil 1234, Lima",
                "ubigeo": "140101",
                "codigo_especialidad": "CIV",
                "genero": "M",
            },
            {
                "dni": "23456789",
                "nombres": "Carmen Rosa",
                "apellido_paterno": "Vega",
                "apellido_materno": "Sánchez",
                "cip": "CIP-23456",
                "correo_personal": "carmen.vega@hotmail.com",
                "correo_institucional": "cvega@cip.pe",
                "direccion": "Calle 2 de Mayo 567, Lima",
                "ubigeo": "140102",
                "codigo_especialidad": "CIV",
                "genero": "F",
            },
            {
                "dni": "34567890",
                "nombres": "Miguel Ángel",
                "apellido_paterno": "Torres",
                "apellido_materno": "Flores",
                "cip": "CIP-34567",
                "correo_personal": "miguel.torres@yahoo.com",
                "correo_institucional": "mtorres@cip.pe",
                "direccion": "Av. Arenales 890, Lima",
                "ubigeo": "140103",
                "codigo_especialidad": "CIV",
                "genero": "M",
            },
        ]
        for data in perfiles_data:
            dni = data.pop("dni")

            # Create or get user
            user, user_created = Usuario.objects.update_or_create(
                dni=dni,
                defaults={
                    "nombres": data["nombres"],
                    "apellidos": f"{data['apellido_paterno']} {data['apellido_materno']}",
                    "email": data["correo_institucional"],
                    "is_staff": False,
                    "is_superuser": False,
                    "is_active": True,
                },
            )
            user.set_password("demo1234")
            user.save(update_fields=["password"])

            # Create or get perfil
            perfil, created = PerfilIngeniero.objects.update_or_create(
                cip=data["cip"],
                defaults={**data, "usuario": user, "capitulo": capitulo_civil},
            )
            action = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(f"  PerfilIngeniero {action}: {perfil.nombre_completo} (CIP: {perfil.cip})")
            )

    def _create_delegados(self):
        self.stdout.write("\n[10/11] Creating delegados...")

        try:
            perfil1 = PerfilIngeniero.objects.get(cip="CIP-12345")
            perfil2 = PerfilIngeniero.objects.get(cip="CIP-23456")
            perfil3 = PerfilIngeniero.objects.get(cip="CIP-34567")
            muni1 = Municipalidad.objects.get(codigo="MUN001")
            muni2 = Municipalidad.objects.get(codigo="MUN002")
            banco1 = Banco.objects.get(codigo="001")
            banco2 = Banco.objects.get(codigo="002")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error getting related entities: {e}"))
            return

        delegados_data = [
            {
                "perfil_ingeniero": perfil1,
                "municipalidad": muni1,
                "banco": banco1,
                "especialidad": "Ingeniería Civil",
                "distrito": "LIMA - LIMA - MIRAFLORES",
                "status": DelegadoStatus.ACTIVO,
            },
            {
                "perfil_ingeniero": perfil2,
                "municipalidad": muni2,
                "banco": banco2,
                "especialidad": "Ingeniería Civil",
                "distrito": "LIMA - LIMA - SAN ISIDRO",
                "status": DelegadoStatus.ACTIVO,
            },
            {
                "perfil_ingeniero": perfil3,
                "municipalidad": muni1,
                "banco": banco1,
                "especialidad": "Ingeniería Civil",
                "distrito": "LIMA - LIMA - SAN BORJA",
                "status": DelegadoStatus.ACTIVO,
            },
        ]
        for data in delegados_data:
            # Use unique constraint fields for lookup
            delegado, created = Delegado.objects.update_or_create(
                perfil_ingeniero=data["perfil_ingeniero"],
                defaults={
                    "municipalidad": data["municipalidad"],
                    "banco": data["banco"],
                    "especialidad": data["especialidad"],
                    "distrito": data["distrito"],
                    "status": data["status"],
                },
            )
            action = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Delegado {action}: {delegado.perfil_ingeniero.nombre_completo} @ {delegado.municipalidad.nombre}"
                )
            )

    def _create_proyectistas(self):
        self.stdout.write("\n[11a/11] Creating proyectistas...")
        proyectistas_data = [
            {"nombre": "Pedro Luis Mendoza Ramírez"},
            {"nombre": "Lucía Fernanda Quiroz Peña"},
        ]
        for data in proyectistas_data:
            proy, created = Proyectista.objects.update_or_create(
                nombre=data["nombre"],
                defaults=data,
            )
            action = "created" if created else "updated"
            self.stdout.write(self.style.SUCCESS(f"  Proyectista {action}: {proy.nombre}"))

    def _create_liquidaciones(self):
        self.stdout.write("\n[11b/11] Creating liquidaciones con revisiones...")

        try:
            proy1 = Proyectista.objects.get(nombre="Pedro Luis Mendoza Ramírez")
            proy2 = Proyectista.objects.get(nombre="Lucía Fernanda Quiroz Peña")
            empresa1 = Empresa.objects.get(ruc="20123456789")
            empresa2 = Empresa.objects.get(ruc="20987654321")
            igv = Igv.objects.filter(fecha_fin__isnull=True).first()
            uit = Uit.objects.filter(fecha_fin__isnull=True).first()
            delegado1 = Delegado.objects.get(perfil_ingeniero__cip="CIP-12345")
            delegado2 = Delegado.objects.get(perfil_ingeniero__cip="CIP-23456")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error getting related entities: {e}"))
            return

        liquidaciones_data = [
            {
                "proyectista": proy1,
                "empresa": empresa1,
                "igv": igv,
                "uit": uit,
                "valor_obra": Decimal("150000.00"),
                "derecho_minimo": Decimal("2.00"),
                "porcentaje": Decimal("10.50"),
            },
            {
                "proyectista": proy2,
                "empresa": empresa2,
                "igv": igv,
                "uit": uit,
                "valor_obra": Decimal("85000.00"),
                "derecho_minimo": Decimal("2.00"),
                "porcentaje": Decimal("12.00"),
            },
        ]
        for idx, data in enumerate(liquidaciones_data, 1):
            # Create liquidacion (will be unique per proyectista+empresa+igv+uit combo)
            liq, created = Liquidacion.objects.update_or_create(
                proyectista=data["proyectista"],
                empresa=data["empresa"],
                igv=data["igv"],
                uit=data["uit"],
                defaults={
                    "valor_obra": data["valor_obra"],
                    "derecho_minimo": data["derecho_minimo"],
                    "porcentaje": data["porcentaje"],
                },
            )
            action = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(f"  Liquidación {action}: {liq.id} - {liq.proyectista.nombre}")
            )

            # Create 1-2 revisions for each liquidacion
            if created or not liq.revisiones.exists():
                revisions = [
                    {"numero": 1, "delegado": delegado1},
                    {"numero": 2, "delegado": delegado2},
                ][: idx]  # First liquidacion gets 2 revisions, second gets 1

                for rev_data in revisions:
                    rev, rev_created = Revision.objects.update_or_create(
                        liquidacion=liq,
                        numero=rev_data["numero"],
                        defaults={},
                    )
                    rev_action = "created" if rev_created else "updated"
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"    Revisión {rev_action}: #{rev.numero}"
                        )
                    )
                    # Create RevisionDelegado entry
                    rd, rd_created = RevisionDelegado.objects.update_or_create(
                        revision=rev,
                        delegado=rev_data["delegado"],
                        defaults={},
                    )
                    rd_action = "created" if rd_created else "updated"
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"      RevisionDelegado {rd_action}: {rd.delegado.perfil_ingeniero.nombre_completo}"
                        )
                    )