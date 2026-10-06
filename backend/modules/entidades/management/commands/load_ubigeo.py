"""
Comando de gestión para cargar datos de Ubigeo desde ubigeo_constants.py a modelos de base de datos.

Este comando es IDEMPOTENTE - ejecutarlo múltiples veces produce el mismo resultado.
Utiliza update_or_create para ejecutarse de forma segura sin duplicar datos.

Uso:
    python manage.py load_ubigeo --settings=config.settings.development
"""

from django.core.management.base import BaseCommand

from modules.entidades.domain.models import UbigeoDepartamento, UbigeoProvincia, UbigeoDistrito
from utils.ubigeo_constants import UBIGEO


class Command(BaseCommand):
    help = "Load Ubigeo data from ubigeo_constants.py into database models"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing Ubigeo data before loading (for clean reload)",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing Ubigeo data...")
            deleted_distritos = UbigeoDistrito.objects.count()
            deleted_provincias = UbigeoProvincia.objects.count()
            deleted_departamentos = UbigeoDepartamento.objects.count()

            UbigeoDistrito.objects.all().delete()
            UbigeoProvincia.objects.all().delete()
            UbigeoDepartamento.objects.all().delete()

            self.stdout.write(
                self.style.WARNING(
                    f"Deleted {deleted_departamentos} departamentos, "
                    f"{deleted_provincias} provincias, {deleted_distritos} distritos"
                )
            )

        self.stdout.write("Loading Ubigeo data...")

        depts_created = 0
        depts_updated = 0
        provs_created = 0
        provs_updated = 0
        dists_created = 0
        dists_updated = 0

        for dept_nombre, provincias in sorted(UBIGEO.items()):
            dept, created = UbigeoDepartamento.objects.update_or_create(
                nombre=dept_nombre,
                defaults={},
            )
            if created:
                depts_created += 1
            else:
                depts_updated += 1

            for prov_nombre, distritos in sorted(provincias.items()):
                prov, created = UbigeoProvincia.objects.update_or_create(
                    departamento=dept,
                    nombre=prov_nombre,
                    defaults={},
                )
                if created:
                    provs_created += 1
                else:
                    provs_updated += 1

                for dist_nombre, dist_data in sorted(distritos.items()):
                    dist_obj, created = UbigeoDistrito.objects.update_or_create(
                        provincia=prov,
                        nombre=dist_nombre,
                        defaults={
                            "ubigeo": dist_data.get("ubigeo", ""),
                            "inei": dist_data.get("inei"),
                        },
                    )
                    if created:
                        dists_created += 1
                    else:
                        dists_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Ubigeo data loaded successfully:\n"
                f"  Departamentos: {depts_created} created, {depts_updated} updated\n"
                f"  Provincias: {provs_created} created, {provs_updated} updated\n"
                f"  Distritos: {dists_created} created, {dists_updated} updated"
            )
        )