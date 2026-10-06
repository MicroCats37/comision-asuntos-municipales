# -*- coding: utf-8 -*-
"""
RHReparticionEstacional — Snapshot model for seasonal/common fund distribution.

Stores the result of distributing the accumulated `fondo_comun` across selected
delegates and chapters for a given especialidad_revision and period (year).

Formula:
    numero_capitulos = count(EspecialidadRevisionCapitulo for especialidad_revision)
    cantidad_delegados = len(selected delegates)
    divisor_total = cantidad_delegados + numero_capitulos
    monto_por_participacion = total_fondo_comun / divisor_total

Each selected delegado receives one share.
Each linked capitulo receives one share.
"""
from django.db import models
from simple_history.models import HistoricalRecords

from core.models import BaseModel


class RHReparticionEstacional(BaseModel):
    """
    Main snapshot for a seasonal fund distribution.

    Unique constraint on (especialidad_revision, periodo) WHERE is_deleted=False
    to prevent overlapping active distributions for the same specialty and year.
    """

    history = HistoricalRecords()

    especialidad_revision = models.ForeignKey(
        "usuarios.EspecialidadRevision",
        on_delete=models.PROTECT,
        related_name="reparticiones_estacionales",
        verbose_name="Especialidad de Revisión",
    )

    periodo = models.PositiveSmallIntegerField(
        verbose_name="Año del Periodo",
        help_text="Año de la repartición (e.g., 2026)",
    )

    total_fondo_comun = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Total Fondo Común",
        help_text="Suma del fondo_comun de los DetalleHonorarioDelegado relacionados",
    )

    numero_capitulos = models.PositiveSmallIntegerField(
        verbose_name="Número de Capítulos",
        help_text="Cantidad de capítulos vinculados a la especialidad en este cálculo",
    )

    numero_delegados = models.PositiveSmallIntegerField(
        verbose_name="Número de Delegados",
        help_text="Cantidad de delegados seleccionados",
    )

    monto_por_participacion = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        verbose_name="Monto por Participación",
        help_text="Monto por cada delegado o capítulo (4 decimales)",
    )

    residual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Residual",
        help_text="Diferencia no distribuible (total_fondo_comun - suma de partes)",
    )

    mes_desde = models.PositiveSmallIntegerField(
        verbose_name="Mes Desde (1-12)",
        help_text="Mes inicial del rango de la repartición",
    )

    mes_hasta = models.PositiveSmallIntegerField(
        verbose_name="Mes Hasta (1-12)",
        help_text="Mes final del rango de la repartición",
    )

    is_deleted = models.BooleanField(
        default=False,
        verbose_name="Eliminado",
        help_text="Soft delete flag",
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Eliminación",
    )

    class Meta:
        verbose_name = "Repartición Estacional"
        verbose_name_plural = "Reparticiones Estacionales"
        ordering = ["-periodo", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["especialidad_revision", "periodo"],
                condition=models.Q(is_deleted=False),
                name="unique_reparticion_estacional_active",
            ),
            models.CheckConstraint(
                check=models.Q(mes_desde__gte=1, mes_desde__lte=12),
                name="reparticion_estacional_mes_desde_valid",
            ),
            models.CheckConstraint(
                check=models.Q(mes_hasta__gte=1, mes_hasta__lte=12),
                name="reparticion_estacional_mes_hasta_valid",
            ),
        ]

    def __str__(self):
        return f"RepEstacional {self.especialidad_revision_id} - {self.periodo}"


class RHReparticionEstacionalDelegado(BaseModel):
    """
    Detail record: one per selected delegate in a reparticion estacional.

    Stores the calculated share for each delegate.
    """

    history = HistoricalRecords()

    reparticion = models.ForeignKey(
        RHReparticionEstacional,
        on_delete=models.CASCADE,
        related_name="detalles_delegados",
        verbose_name="Repartición Estacional",
    )

    delegado = models.ForeignKey(
        "liquidaciones.Delegado",
        on_delete=models.PROTECT,
        related_name="reparticiones_estacionales_delegado",
        verbose_name="Delegado",
    )

    monto = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        verbose_name="Monto Asignado",
        help_text="Monto recibido por este delegado (4 decimales)",
    )

    class Meta:
        verbose_name = "Detalle de Delegado en Repartición Estacional"
        verbose_name_plural = "Detalles de Delegados en Reparticiones Estacionales"
        ordering = ["reparticion", "delegado"]
        constraints = [
            models.UniqueConstraint(
                fields=["reparticion", "delegado"],
                name="unique_reparticion_delegado",
            ),
        ]

    def __str__(self):
        return f"DetDelegado {self.delegado_id} @ {self.reparticion_id}"


class RHReparticionEstacionalCapitulo(BaseModel):
    """
    Detail record: one per linked chapter in a reparticion estacional.

    Stores the calculated share for each chapter.
    """

    history = HistoricalRecords()

    reparticion = models.ForeignKey(
        RHReparticionEstacional,
        on_delete=models.CASCADE,
        related_name="detalles_capitulos",
        verbose_name="Repartición Estacional",
    )

    capitulo = models.ForeignKey(
        "usuarios.Capitulo",
        on_delete=models.PROTECT,
        related_name="reparticiones_estacionales_capitulo",
        verbose_name="Capítulo",
    )

    monto = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        verbose_name="Monto Asignado",
        help_text="Monto recibido por este capítulo (4 decimales)",
    )

    class Meta:
        verbose_name = "Detalle de Capítulo en Repartición Estacional"
        verbose_name_plural = "Detalles de Capítulos en Reparticiones Estacionales"
        ordering = ["reparticion", "capitulo"]
        constraints = [
            models.UniqueConstraint(
                fields=["reparticion", "capitulo"],
                name="unique_reparticion_capitulo",
            ),
        ]

    def __str__(self):
        return f"DetCapitulo {self.capitulo_id} @ {self.reparticion_id}"