"""Curate the obsolete `inspeccion-obra` review specialty by engineer chapter.

Run without ``--apply`` first. The command only removes the obsolete specialty
after every protected reference has been reassigned or is absent.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.deletion import ProtectedError

from modules.liquidaciones.domain.models.inspector import (
    InspectorOperacion,
    LiquidacionInspector,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    EspecialidadRevisionCapitulo,
)


class Command(BaseCommand):
    help = (
        "Reasigna la especialidad de revisión 'inspeccion-obra' según el capítulo "
        "del ingeniero y la elimina cuando ya no tenga referencias."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica los cambios. Sin esta opción solo informa el resultado.",
        )

    def handle(self, *args, **options):
        fallback = EspecialidadRevision.objects.filter(slug="inspeccion-obra").first()
        if fallback is None:
            self.stdout.write(self.style.SUCCESS("No existe la especialidad inspeccion-obra."))
            return

        mappings = self._mappings_por_capitulo(fallback.id)
        operaciones = list(
            InspectorOperacion.objects.filter(especialidad_revision=fallback)
            .select_related("inspector__perfil_ingeniero")
        )
        liquidaciones = list(
            LiquidacionInspector.objects.filter(especialidad_revision=fallback)
            .select_related("inspector__perfil_ingeniero", "inspector_operacion")
        )

        operables = [op for op in operaciones if self._target(op.inspector, mappings)]
        liquidables = [item for item in liquidaciones if self._target(item.inspector, mappings)]
        sin_mapeo = [
            *[op.inspector.perfil_ingeniero.cip for op in operaciones if not self._target(op.inspector, mappings)],
            *[
                item.inspector.perfil_ingeniero.cip
                for item in liquidaciones
                if not self._target(item.inspector, mappings)
            ],
        ]
        self.stdout.write(
            "Especialidad inspeccion-obra: "
            f"{len(operaciones)} operaciones ({len(operables)} reasignables), "
            f"{len(liquidaciones)} liquidaciones ({len(liquidables)} reasignables)."
        )

        pendientes = (len(operaciones) - len(operables)) + (
            len(liquidaciones) - len(liquidables)
        )
        if pendientes:
            self.stdout.write(
                self.style.WARNING(
                    f"{pendientes} referencias no tienen un capítulo con mapeo y requieren revisión."
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    "CIP pendientes: " + ", ".join(sorted(set(sin_mapeo)))
                )
            )
        if not options["apply"]:
            self.stdout.write("Dry run. Use --apply to persist changes.")
            return

        with transaction.atomic():
            for operacion in operables:
                target = self._target(operacion.inspector, mappings)
                operacion.especialidad_revision_id = target
                operacion.save(update_fields=["especialidad_revision"])

            for liquidacion in liquidables:
                target = self._target(liquidacion.inspector, mappings)
                liquidacion.especialidad_revision_id = target
                liquidacion.save(update_fields=["especialidad_revision"])

            if not pendientes:
                try:
                    fallback.delete()
                except ProtectedError as error:
                    raise CommandError(
                        "La especialidad aún tiene referencias protegidas fuera de InspectorOperacion "
                        f"o LiquidacionInspector ({len(error.protected_objects)})."
                    )

        if pendientes:
            self.stdout.write(
                self.style.SUCCESS(
                    "Referencias mapeadas curadas. La especialidad inspeccion-obra se conserva "
                    "para los CIP pendientes."
                )
            )
            return
        self.stdout.write(self.style.SUCCESS("Especialidad inspeccion-obra curada y eliminada."))

    @staticmethod
    def _mappings_por_capitulo(fallback_id):
        mappings = {}
        for mapping in EspecialidadRevisionCapitulo.objects.exclude(
            especialidad_revision_id=fallback_id,
        ):
            if mapping.capitulo_id in mappings:
                raise CommandError(
                    "Un capítulo tiene más de una especialidad de revisión configurada."
                )
            mappings[mapping.capitulo_id] = mapping.especialidad_revision_id
        return mappings

    @staticmethod
    def _target(inspector, mappings):
        return mappings.get(inspector.perfil_ingeniero.capitulo_id)
