"""
LiquidacionRelacionMiembro — represents the membership of a LiquidacionGeneral in a group.

Each member links a LiquidacionGeneral to a LiquidacionRelacionGrupo with a
relacion_key (e.g., EDIFICACION-OBRA, EDIFICACION-DEMOLICION, HU, MS) and a
numero_revision.

Unique constraint: (grupo, relacion_key, numero_revision)
  — Allows EDIFICACION-OBRA+REV1 and EDIFICACION-DEMOLICION+REV1 in the same group
     (different relacion_key even with same revision).
  — Rejects two EDIFICACION-OBRA+REV1 in the same group (duplicate slot).
  — nueva-revision uses higher revision numbers (3, 5) so it never conflicts with
     the first revision (1) in the same group.
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel


class LiquidacionRelacionMiembro(BaseModel):
    """
    Miembro de un grupo de relación de liquidaciones.

    Cada LiquidacionGeneral puede ser miembro de un único grupo (unique en liquidacion).
    El constraint unique (grupo, relacion_key, numero_revision) previene duplicados
    del mismo slot, pero permite /relacionada entre subtipos distintos (OBRA vs
    DEMOLICION) porque generan relacion_key diferentes.
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
            models.UniqueConstraint(
                fields=["grupo", "relacion_key", "numero_revision"],
                name="unique_grupo_relacion_key_revision",
            ),
        ]
        indexes = [
            models.Index(fields=["grupo", "relacion_key", "numero_revision"]),
            models.Index(fields=["liquidacion"]),
        ]

    def __str__(self):
        return f"{self.relacion_key} rev.{self.numero_revision} @ {self.grupo.codigo}"
