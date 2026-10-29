"""
LiquidacionRelacionMiembro — represents the membership of a LiquidacionGeneral in a group.

Each member links a LiquidacionGeneral to a LiquidacionRelacionGrupo with a
relacion_key (e.g., EDIFICACION-OBRA, EDIFICACION-DEMOLICION, HU, MS) and a
numero_revision.

Unique constraint: (liquidacion)
  — Each LiquidacionGeneral belongs to at most one group.

The (grupo, relacion_key, numero_revision) uniqueness was removed: `numero_revision` is a
user-editable classification, not a sequence identity, so several active liquidaciones
may share the same slot (e.g. two EDIFICACION-OBRA at revision 3 in the same group).
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel


class LiquidacionRelacionMiembro(BaseModel):
    """
    Miembro de un grupo de relación de liquidaciones.

    Cada LiquidacionGeneral puede ser miembro de un único grupo (unique en liquidacion).
    El grupo puede contener varias liquidaciones con la misma relacion_key y el mismo
    numero_revision: el número de revisión es una etiqueta editable y no una identidad
    única de secuencia.
    """

    history = HistoricalRecords()

    grupo = models.ForeignKey(
        "LiquidacionRelacionGrupo",
        on_delete=models.CASCADE,
        related_name="miembros",
        verbose_name="Grupo",
    )
    liquidacion = models.ForeignKey(
        "LiquidacionGeneral",
        on_delete=models.CASCADE,
        related_name="relacion_miembros",
        verbose_name="Liquidación",
    )
    relacion_key = models.CharField(
        max_length=120,
        verbose_name="Clave de relación",
        help_text="Clave que identifica el tipo de relación. Ej: EDIFICACION-OBRA, EDIFICACION-DEMOLICION, HU, MS, etc.",
    )
    numero_revision = models.PositiveSmallIntegerField(
        verbose_name="Número de revisión",
        help_text="Número de revisión en que esta liquidación es miembro del grupo.",
    )

    class Meta:
        verbose_name = "Miembro de Relación de Liquidación"
        verbose_name_plural = "Miembros de Relaciones de Liquidaciones"
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion"],
                name="unique_liquidacion_unico_grupo",
            ),
        ]
        indexes = [
            models.Index(fields=["grupo", "relacion_key", "numero_revision"]),
            models.Index(fields=["liquidacion"]),
        ]

    def __str__(self):
        return f"{self.relacion_key} rev.{self.numero_revision} @ {self.grupo.codigo}"
