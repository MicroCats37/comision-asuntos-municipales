from django.db import models


class VigenciaQuerySet(models.QuerySet):
    """QuerySet for VigenciaModel with filtering by date."""

    def vigentes(self, fecha=None):
        """
        Return objects that are currently valid (vigentes).

        Args:
            fecha: Optional date to check against. Defaults to today.
        """
        from datetime import date

        if fecha is None:
            fecha = date.today()

        return self.filter(
            models.Q(periodo_fin__isnull=True)
            | models.Q(periodo_fin__gte=fecha),
            periodo_inicio__lte=fecha,
        )

    def vigente(self, fecha=None):
        """
        Return the newest single record vigente at fecha, or None.

        Args:
            fecha: Optional date to check against. Defaults to today.

        Returns:
            A single model instance or None.
        """
        return self.vigentes(fecha).order_by("-periodo_inicio", "pk").first()


class VigenciaManager(models.Manager):
    """Manager for VigenciaModel."""

    def get_queryset(self):
        return VigenciaQuerySet(self.model, using=self._db)

    def vigentes(self, fecha=None):
        """Proxy to VigenciaQuerySet.vigentes()."""
        return self.get_queryset().vigentes(fecha=fecha)

    def vigente(self, fecha=None):
        """Proxy to VigenciaQuerySet.vigente()."""
        return self.get_queryset().vigente(fecha=fecha)


class VigenciaModel(models.Model):
    """
    Abstract base model for objects with a validity period (vigencia).

    Attributes:
        periodo_inicio: Start date of the validity period.
        periodo_fin: End date of the validity period (optional, null means ongoing).
    """

    periodo_inicio = models.DateField(verbose_name="Periodo de Inicio")
    periodo_fin = models.DateField(
        null=True, blank=True, verbose_name="Periodo de Fin"
    )

    objects = VigenciaManager()

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                check=models.Q(periodo_fin__isnull=True)
                | models.Q(periodo_inicio__lt=models.F("periodo_fin")),
                name="vigencia_rango_valido",
            ),
        ]


class AutoNumeroModel(models.Model):
    """
    Abstract base model for objects with automatic sequential numbering.

    The `numero` field is auto-incremented on save to the next available
    sequential integer based on existing records.
    """

    numero = models.PositiveIntegerField(
        verbose_name="Numero",
        help_text="Numero asignado automaticamente por el sistema.",
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Auto-increment `numero` to the next sequential value on first save."""
        if (
            self._state.adding
            and getattr(self, "numero", None) is None
            and not getattr(self, "_skip_autonumero", False)
        ):
            last = (
                self.__class__.objects.all()
                .order_by("numero")
                .values_list("numero", flat=True)
                .last()
            )
            self.numero = (last or 0) + 1
        super().save(*args, **kwargs)
