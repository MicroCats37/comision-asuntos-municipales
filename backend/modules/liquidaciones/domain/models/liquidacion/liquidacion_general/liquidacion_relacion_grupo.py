"""
LiquidacionRelacionGrupo — represents a group of related liquidaciones.

A group is identified by a unique technical code and contains multiple
LiquidacionRelacionMiembro members.
"""

from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel


class LiquidacionRelacionGrupo(BaseModel):
    """
    Grupo de relación entre liquidaciones relacionadas.

    El código es único y se genera mediante un helper (Batch 2).
    No tiene soft-delete propio — la auditoría está dada por HistoricalRecords.
    """

    history = HistoricalRecords()

    codigo = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Código técnico del grupo",
        help_text="Código único generado automáticamente. Formato: LQG-YYYYMMDD-HHMMSS-XXXX",
    )

    class Meta:
        verbose_name = "Grupo de Relación de Liquidación"
        verbose_name_plural = "Grupos de Relaciones de Liquidaciones"
        indexes = [
            models.Index(fields=["codigo"]),
        ]

    def __str__(self):
        return self.codigo

    @property
    def display_name(self) -> str:
        """
        Nombre para mostrar derivado del timestamp del código.
        NO se persiste — se calcula en tiempo de consulta.
        Formato: 'Grupo del 26/09/2026 a las 15:30:12'
        """
        parts = self.codigo.split("-")
        if len(parts) >= 3:
            fecha_parte = parts[1]  # YYYYMMDD
            hora_parte = parts[2]   # HHMMSS
            from datetime import datetime
            try:
                dt = datetime.strptime(f"{fecha_parte}{hora_parte}", "%Y%m%d%H%M%S")
                return f"Grupo del {dt.strftime('%d/%m/%Y a las %H:%M:%S')}"
            except ValueError:
                return self.codigo
        return self.codigo
