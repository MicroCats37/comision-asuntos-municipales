"""
Management command to delete ALL liquidaciones (pruebas) and their related
specific/calculation/child records, leaving catalogos (tarifas, municipalidades,
ubigeo, especialidades) intact.

Usage:
    python manage.py limpiar_liquidaciones --settings=config.settings.development
    python manage.py limpiar_liquidaciones --dry-run --settings=config.settings.development

Deletion order respects on_delete=PROTECT constraints:
    1. LiquidacionInspector / LiquidacionDelegado / LiquidacionContacto / LiquidacionDocumentos
    2. LiquidacionPorcentajeObraDetalle (child of LiquidacionPorcentajeObra)
    3. Specific identity wrappers (edificacion, habilitacion-urbana, mecanica-suelos,
       impacto-vial, taludes, inspeccion-obra)
    4. Calculation models (LiquidacionPorcentajeObra, LiquidacionPorMetroCuadrado,
       LiquidacionPorCategoriaVisitas)
    5. LiquidacionGeneral
    6. Proyecto / Entidad / Contacto (creados por la ingesta de prueba)

NO borra: TarifaLiquidacionBase, tarifas hijas, Municipalidad, Ubigeo, Especialidad,
usuarios, delegados/ingenieros seed.
"""
import logging

from django.core.management.base import BaseCommand

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
    LiquidacionContacto,
    LiquidacionDocumentos,
    LiquidacionProyectista,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorMetroCuadrado,
    LiquidacionPorCategoriaVisitas,
    LiquidacionPorcentajeObra,
    LiquidacionPorcentajeObraDetalle,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_mecanica_suelos import (
    LiquidacionMecanicaSuelos,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_impacto_vial import (
    LiquidacionImpactoVial,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_taludes import (
    LiquidacionTaludes,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_inspeccion_obra import (
    LiquidacionInspeccionObra,
)
from modules.liquidaciones.domain.models.delegado import LiquidacionDelegado
from modules.liquidaciones.domain.models.inspector import LiquidacionInspector
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.entidades.domain.models.entidad import Entidad
from modules.entidades.domain.models.contacto import Contacto

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Elimina todas las liquidaciones (prueba) y sus registros hijos, sin tocar catálogos."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Solo reportar conteos sin borrar.")

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])

        # Orden de borrado: de hijos a padres (por PROTECT).
        # NOTA: Proyecto/Entidad/Contacto se borran SOLO los vinculados a liquidaciones
        # (los del seed de delegados/inspectores se conservan).
        pasos = [
            ("LiquidacionInspector", LiquidacionInspector),
            ("LiquidacionDelegado", LiquidacionDelegado),
            ("LiquidacionContacto", LiquidacionContacto),
            ("LiquidacionDocumentos", LiquidacionDocumentos),
            ("LiquidacionProyectista", LiquidacionProyectista),
            ("LiquidacionPorcentajeObraDetalle", LiquidacionPorcentajeObraDetalle),
            ("LiquidacionEdificacion", LiquidacionEdificacion),
            ("LiquidacionHabilitacionUrbana", LiquidacionHabilitacionUrbana),
            ("LiquidacionMecanicaSuelos", LiquidacionMecanicaSuelos),
            ("LiquidacionImpactoVial", LiquidacionImpactoVial),
            ("LiquidacionTaludes", LiquidacionTaludes),
            ("LiquidacionInspeccionObra", LiquidacionInspeccionObra),
            ("LiquidacionPorcentajeObra", LiquidacionPorcentajeObra),
            ("LiquidacionPorMetroCuadrado", LiquidacionPorMetroCuadrado),
            ("LiquidacionPorCategoriaVisitas", LiquidacionPorCategoriaVisitas),
            ("LiquidacionGeneral", LiquidacionGeneral),
        ]

        total = 0
        for nombre, modelo in pasos:
            conteo = modelo.objects.count()
            total += conteo
            if dry_run:
                self.stdout.write(f"  [DRY] {nombre}: {conteo}")
            else:
                borrados, _ = modelo.objects.all().delete()
                self.stdout.write(f"  {nombre}: {conteo} (borrados {borrados})")

        # Proyectos huérfanos (de liquidaciones) — las entidades de seed se conservan.
        proyectos_huerfanos = Proyecto.objects.all()
        n_proy = proyectos_huerfanos.count()
        total += n_proy
        if dry_run:
            self.stdout.write(f"  [DRY] Proyecto (huérfanos de liquidación): {n_proy}")
        else:
            borrados, _ = proyectos_huerfanos.delete()
            self.stdout.write(f"  Proyecto (huérfanos de liquidación): {n_proy} (borrados {borrados})")

        if dry_run:
            self.stdout.write(self.style.WARNING(f"\nDRY RUN — {total} registros de liquidación a borrar (sin cambios)."))
            self.stdout.write(self.style.WARNING("Las Entidades/Contactos de seed (delegados/inspectores) NO se tocan."))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nLimpieza completada. {total} registros de liquidación eliminados."))
            self.stdout.write(self.style.SUCCESS("Las Entidades/Contactos de seed (delegados/inspectores) NO se tocaron."))
