"""
RevisionDelegado — Tabla explícita N:N entre Revision y Delegado.
"""

from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class RevisionDelegado(BaseModel):
    """
    Relación muchos-a-muchos entre Revision y Delegado mediante tabla explícita.
    Permite que una revisión sea realizada por múltiples delegados.
    """

    history = HistoricalRecords()

    revision = models.ForeignKey(
        "Revision",
        on_delete=models.CASCADE,
        related_name="revision_delegados",
        verbose_name="Revisión",
    )
    delegado = models.ForeignKey(
        "Delegado",
        on_delete=models.PROTECT,
        related_name="revision_delegados",
        verbose_name="Delegado",
    )

    class Meta:
        verbose_name = "Delegado de Revisión"
        verbose_name_plural = "Delegados de Revisiones"
        ordering = ["revision", "delegado"]
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "delegado"],
                name="unique_revision_delegado",
            ),
        ]

    def __str__(self):
        return f"{self.delegado} @ Revisión {self.revision.numero}"
