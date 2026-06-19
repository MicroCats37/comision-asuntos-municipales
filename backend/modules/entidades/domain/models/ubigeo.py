"""
Modelos de Ubigeo — jerarquía geográfica del Perú (Departamento > Provincia > Distrito).

Estos modelos reemplazan el dict estático UBIGEO en utils/ubigeo_constants.py con
entidades respaldadas en base de datos, permitiendo consultas dinámicas y gestión en admin.
"""

from django.db import models

from core.models import BaseModel


class UbigeoDepartamento(BaseModel):
    """
    Nivel superior de la jerarquía ubigeo del Perú.
    Ejemplo: "LIMA", "ANCASH", "APURIMAC".
    """

    nombre = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Nombre",
        help_text="Nombre del departamento (e.g. LIMA, ANCASH)",
    )

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class UbigeoProvincia(BaseModel):
    """
    Segundo nivel de la jerarquía ubigeo del Perú.
    Pertenece a un Departamento y contiene varios Distritos.
    Ejemplo: "LIMA" (dentro del Departamento "LIMA"), "BAGUA" (dentro de "AMAZONAS").
    """

    departamento = models.ForeignKey(
        UbigeoDepartamento,
        on_delete=models.CASCADE,
        related_name="provincias",
        verbose_name="Departamento",
    )
    nombre = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Nombre",
        help_text="Nombre de la provincia (e.g. LIMA, BAGUA)",
    )

    class Meta:
        verbose_name = "Provincia"
        verbose_name_plural = "Provincias"
        ordering = ["departamento__nombre", "nombre"]
        # A provincia is unique within its departamento
        constraints = [
            models.UniqueConstraint(
                fields=["departamento", "nombre"],
                name="unique_departamento_provincia",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.departamento.nombre})"


class UbigeoDistrito(BaseModel):
    """
    Tercer y último nivel de la jerarquía ubigeo del Perú.
    Pertenece a una Provincia y contiene el código ubigeo real.
    Ejemplo: "MIRAFLORES" (dentro de la Provincia "LIMA", Departamento "LIMA").
    """

    provincia = models.ForeignKey(
        UbigeoProvincia,
        on_delete=models.CASCADE,
        related_name="distritos",
        verbose_name="Provincia",
    )
    nombre = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Nombre",
        help_text="Nombre del distrito (e.g. MIRAFLORES, BAGUA)",
    )
    ubigeo = models.CharField(
        max_length=6,
        unique=True,
        db_index=True,
        verbose_name="Código Ubigeo",
        help_text="Código ubigeo de 6 dígitos (e.g. 150101)",
    )
    inei = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        verbose_name="Código INEI",
        help_text="Código INEI alternativo (si existe)",
    )

    class Meta:
        verbose_name = "Distrito"
        verbose_name_plural = "Distritos"
        ordering = ["provincia__departamento__nombre", "provincia__nombre", "nombre"]
        # Un distrito es único dentro de su provincia
        constraints = [
            models.UniqueConstraint(
                fields=["provincia", "nombre"],
                name="unique_provincia_distrito",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.provincia})"

    @property
    def departamento(self):
        """Propiedad auxiliar para acceder directamente al departamento."""
        return self.provincia.departamento

    @property
    def hierarchical_label(self):
        """Retorna la etiqueta jerárquica completa: DEPARTAMENTO - PROVINCIA - DISTRITO."""
        return f"{self.provincia.departamento.nombre} - {self.provincia.nombre} - {self.nombre}"