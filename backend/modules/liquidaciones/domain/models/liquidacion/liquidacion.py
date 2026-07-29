"""
LiquidacionGeneral — general liquidacion classes and enums.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords
from core.models import BaseModel
from ...constants import (
    EstadoLiquidacion,
    TipoLiquidacion,
    TipoTramiteEdificaciones,
    TramiteAccion,
)


class LiquidacionGeneral(BaseModel):
    """
    Liquidación de pago a proyectistas para un proyecto.
    Representa la instancia operacional de liquidación/revisión de un proyecto.
    """

    history = HistoricalRecords()

    proyecto_propiedad = models.ForeignKey(
        "ProyectoPropiedad",
        on_delete=models.PROTECT,
        related_name="liquidaciones",
        verbose_name="Proyecto",
    )

    municipalidad = models.ForeignKey(
        "entidades.Municipalidad",
        on_delete=models.PROTECT,
        related_name="liquidaciones",
        verbose_name="Municipalidad",
        null=True,
        blank=True,
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Registro",
        help_text="Fecha y hora en que se registró la liquidación en el sistema.",
    )

    usuario_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="liquidaciones_creadas",
        verbose_name="Usuario Creador",
        null=True,
        blank=True,
    )

    igv_id = models.ForeignKey(
        "finanzas.IGV",
        on_delete=models.PROTECT,
        verbose_name="IGV",
    )

    uit_id = models.ForeignKey(
        "finanzas.UIT",
        on_delete=models.PROTECT,
        verbose_name="UIT",
    )

    igv_utilizado = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="IGV Utilizado",
        help_text="Valor del IGV utilizado en el cálculo de la liquidación.",
    )

    uit_utilizado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="UIT Utilizado",
        help_text="Valor de la UIT utilizado en el cálculo de la liquidación.",
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoLiquidacion.choices,
        default="PENDIENTE",
        verbose_name="Estado de la Revisión",
    )

    sub_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Sub Total",
        help_text="Subtotal calculado de la liquidación . Se llena después del cálculo.",
    )

    sub_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Sub Total",
        help_text="Subtotal calculado de la liquidación . Se llena después del cálculo.",
    )

    observacion = models.CharField(max_length=2000, null=True, blank=True)

    expediente = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Expediente",
        help_text="Número de expediente associated with the liquidacion.",
    )

    liquidaciones_previas = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="revisiones",
        blank=True,
        verbose_name="Liquidaciones Previas",
        help_text="Referencias a liquidaciones anteriores en caso de revisiones sucesivas.",
    )

    tipo_liquidacion = models.CharField(
        max_length=30,
        choices=TipoLiquidacion.choices,
        default=TipoLiquidacion.EDIFICACION,
        verbose_name="Tipo de Liquidación",
        help_text="Tipo de liquidación/formulario: EDIFICACION, HABILITACION_URBANA, MECANICA_SUELOS, IMPACTO_VIAL, TALUDES, INSPECCION_OBRA.",
    )

    numero_revision = models.PositiveIntegerField(
        default=1,
        verbose_name="Número de Revisión",
        help_text="Número secuencial de revisión (1 = primera revisión).",
    )

    periodo_incio = models.DateField(
        blank=True,
        null=True,
        verbose_name="Periodo de Inicio",
        help_text="Fecha de inicio del período de vigencia de la liquidación.",
    )

    periodo_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name="Periodo de Fin",
        help_text="Fecha de fin del período de vigencia de la liquidación (opcional).",
    )

    class Meta:
        verbose_name = "Liquidación"
        verbose_name_plural = "Liquidaciones"
        ordering = ["proyecto", "-fecha_registro"]

    def __str__(self):
        return f"Liquidación de {self.proyecto}"

class LiquidacionGeneralCodigo(BaseModel):
    
    tipo_liquidacion = models.CharField(
        max_length=30,
        choices=TipoLiquidacion.choices,
        default=TipoLiquidacion.EDIFICACION,
        verbose_name="Tipo de Liquidación",
        help_text="Tipo de liquidación/formulario: EDIFICACION, HABILITACION_URBANA, MECANICA_SUELOS, IMPACTO_VIAL, TALUDES, INSPECCION_OBRA.",
    )
    
    codigo_cta = models.CharField(
        max_length=20,
        verbose_name="Código de Cuenta",
        help_text="Código de cuenta asociado a la liquidación.",
    )    

class LiquidacionContacto(BaseModel):
    """
    Tabla puente que asocia un Contacto a una Liquidación.
    Permite marcar un contacto como principal y agregar notas específicas
    de la relación liquidación-contacto.
    """

    liquidacion = models.ForeignKey(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="contactos",
        verbose_name="Liquidación",
    )
    contacto = models.ForeignKey(
        "entidades.Contacto",
        on_delete=models.PROTECT,
        related_name="liquidaciones",
        verbose_name="Contacto",
    )
    principal = models.BooleanField(
        default=True,
        verbose_name="¿Principal?",
        help_text="Indica si este es el contacto principal de la liquidación.",
    )

    class Meta:
        verbose_name = "Liquidación - Contacto"
        verbose_name_plural = "Liquidaciones - Contactos"
        ordering = ["-principal", "liquidacion__proyecto__denominacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion", "contacto"],
                name="unique_liquidacion_contacto",
            ),
        ]

    def __str__(self):
        return f"{self.contacto} @ {self.liquidacion}"


class LiquidacionDocumentos(BaseModel):
    """
    Documentos asociados a una LiquidacionGeneral, con su valor de obra.
    Se vincula a una LiquidacionGeneral y almacena los detalles de cada documento.
    """

    history = HistoricalRecords()

    liquidacion_maestra = models.ForeignKey(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="documentos",
        verbose_name="Liquidación Maestra",
    )
    nombre_documento = models.CharField(
        max_length=255,
        verbose_name="Nombre del Documento",
    )
    documento = models.FileField(
        upload_to="liquidaciones/documentos/",
        verbose_name="Archivo del Documento",
    )


# =============================================================================
# Nuevos modelos del refactor — ver contract/PLAN_REFACTORIZACION.md
# =============================================================================


class LiquidacionProyectista(BaseModel):
    """
    Proyectistas separados de una LiquidacionGeneral.

    Diseño simple — solo FK a LiquidacionGeneral y FK a Proyectista.
    NO agregar campos extra como especialidad, rol, estado, importe, numero_revision.
    """

    liquidacion_general = models.ForeignKey(
        LiquidacionGeneral,
        on_delete=models.CASCADE,
        related_name="liquidacion_proyectistas",
        verbose_name="Liquidación General",
    )
    proyectista = models.ForeignKey(
        "Proyectista",
        on_delete=models.PROTECT,
        related_name="liquidaciones_proyectista",
        verbose_name="Proyectista",
    )

    class Meta:
        verbose_name = "Proyectista de Liquidación"
        verbose_name_plural = "Proyectistas de Liquidaciones"
        constraints = [
            models.UniqueConstraint(
                fields=["liquidacion_general", "proyectista"],
                name="unique_liquidacion_proyectista",
            ),
        ]

    def __str__(self):
        return f"Proyectista {self.proyectista} @ {self.liquidacion_general}"


class TarifaPorcentajeObra(BaseModel):
    """
    Tarifa porcentual para liquidaciones de obra.

    Contiene el porcentaje de liquidación y los límites de derecho mínimo/máximo
    y el mínimo como porcentaje de UIT.

    Relación: Tiene OneToOneField hacia TarifaLiquidacionBase.
    Una TarifaPorcentajeObra pertenece a exactamente una TarifaLiquidacionBase.
    """

    history = HistoricalRecords()

    # FK/OneToOne hacia TarifaLiquidacionBase — la cabecera de esta tarifa.
    # Cada TarifaPorcentajeObra tiene una única TarifaLiquidacionBase.
    # NOTA: null=True/blank=True temporalmente para permitir migración sin datos existentes.
    # La BD de desarrollo se reseteará, así que todas las filas tendrán el valor correcto.
    tarifa_base = models.OneToOneField(
        "TarifaLiquidacionBase",
        on_delete=models.CASCADE,
        related_name="detalle_porcentual",
        verbose_name="Tarifa Base",
        help_text="Tarifa base asociada a esta tarifa porcentual.",
        null=True,
        blank=True,
    )

    porcentaje_liquidacion = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        verbose_name="Porcentaje de Liquidación",
        help_text="Porcentaje aplicado para el cálculo del derecho (ej: 0.0015 para 0.15%).",
    )
    derecho_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name="Derecho Mínimo",
        help_text="Monto mínimo absoluto del derecho en soles.",
    )
    derecho_maximo = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Derecho Máximo",
        help_text="Monto máximo absoluto del derecho en soles (nulo = sin tope).",
    )
    porcentaje_minimo_uit = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        verbose_name="Porcentaje Mínimo UIT",
        help_text="Mínimo como porcentaje de la UIT (protección para montos bajos).",
    )

    class Meta:
        verbose_name = "Tarifa Porcentual de Obra"
        verbose_name_plural = "Tarifas Porcentuales de Obra"

    def __str__(self):
        return (
            f"Tarifa {self.porcentaje_liquidacion * 100}% (min: {self.derecho_minimo})"
        )


class TarifaLiquidacionBase(BaseModel):
    """
    Tarifa base que define qué tarifa aplica a un conjunto de especialidades
    para un tipo de liquidación en un período determinado.

    Relaciona M2M a especialidades porque una misma tarifa puede aplicar
    a combinaciones (A+B+C con 0.15%) o a especialidades individuales.

    Relación con TarifaPorcentajeObra: TarifaPorcentajeObra tiene FK/OneToOne
    hacia TarifaLiquidacionBase (una tarifa base tiene un solo detalle porcentual).
    """

    history = HistoricalRecords()

    tipo_liquidacion = models.CharField(
        max_length=30,
        choices=TipoLiquidacion.choices,
        default=TipoLiquidacion.EDIFICACION,
        verbose_name="Tipo de Liquidación",
        help_text="Tipo de formulario/liquidación al que aplica esta tarifa.",
    )
    especialidades = models.ManyToManyField(
        "Especialidad",
        related_name="tarifas_liquidacion_base",
        verbose_name="Especialidades",
        help_text="Especialidades a las que aplica esta tarifa base.",
    )
    periodo_inicio = models.DateField(
        verbose_name="Periodo de Inicio",
    )
    periodo_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name="Periodo de Fin",
    )
    # NOTA: La FK hacia TarifaPorcentajeObra se eliminó de aquí.
    # TarifaPorcentajeObra ahora tiene tarifa_base = OneToOneField hacia TarifaLiquidacionBase.
    # Una TarifaLiquidacionBase puede obtenerse desde TarifaPorcentajeObra via reverse relation:
    # TarifaPorcentajeObra.objects.filter(tarifa_base__tipo_liquidacion=X)

    class Meta:
        verbose_name = "Tarifa Base de Liquidación"
        verbose_name_plural = "Tarifas Base de Liquidación"
        ordering = ["-periodo_inicio"]

    def __str__(self):
        return f"Tarifa Base {self.tipo_liquidacion} desde {self.periodo_inicio}"


class EspecialidadesLiquidacion(BaseModel):
    """
    Define qué especialidades están habilitadas para cada tipo de formulario
    de liquidación en un período determinado.

    Reemplaza y generaliza a EdificacionesEspecialidades, añadiendo soporte
    para todos los tipos de formulario (no solo Edificación).
    """

    history = HistoricalRecords()

    tipo_liquidacion = models.CharField(
        max_length=30,
        choices=TipoLiquidacion.choices,
        default=TipoLiquidacion.EDIFICACION,
        verbose_name="Tipo de Liquidación",
        help_text="Tipo de formulario: edificacion, habilitacion_urbana, etc.",
    )
    especialidades = models.ManyToManyField(
        "Especialidad",
        related_name="especialidades_liquidacion_grupo",
        verbose_name="Especialidades",
        help_text="Especialidades habilitadas para este tipo de formulario.",
    )
    periodo_inicio = models.DateField(
        verbose_name="Periodo de Inicio",
    )
    periodo_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name="Periodo de Fin",
    )

    class Meta:
        verbose_name = "Especialidades de Liquidación"
        verbose_name_plural = "Grupos de Especialidades de Liquidación"
        ordering = ["-periodo_inicio"]

    def __str__(self):
        return f"Especialidades {self.tipo_liquidacion} desde {self.periodo_inicio}"


class ReglaTarifaEdificacion(BaseModel):
    """
    Mapea una tarifa base a una combinación de tipo_tramite y tramite_accion.

    Una misma TarifaLiquidacionBase puede tener múltiples reglas (ej. 0.15% para
    OBRA_NUEVA+PRIMERA_REVISION y para DEMOLICION+PRIMERA_REVISION).

    La combinación (tipo_tramite, tramite_accion, tarifa_base) debe ser única.
    """

    history = HistoricalRecords()

    tipo_tramite = models.CharField(
        max_length=30,
        choices=TipoTramiteEdificaciones.choices,
        verbose_name="Tipo de Trámite",
        help_text="Tipo de trámite de edificación al que aplica esta regla.",
    )
    tramite_accion = models.CharField(
        max_length=20,
        choices=TramiteAccion.choices,
        verbose_name="Acción de Trámite",
        help_text="Acción de trámite: PRIMERA_REVISION o REVISION.",
    )
    tarifa_base = models.ForeignKey(
        "TarifaLiquidacionBase",
        on_delete=models.CASCADE,
        related_name="reglas_tarifa",
        verbose_name="Tarifa Base",
        help_text="Tarifa base asociada a esta regla.",
    )

    class Meta:
        verbose_name = "Regla de Tarifa de Edificación"
        verbose_name_plural = "Reglas de Tarifas de Edificación"
        ordering = ["tipo_tramite", "tramite_accion"]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_tramite", "tramite_accion", "tarifa_base"],
                name="unique_regla_tarifa_edificacion",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tipo_tramite", "tramite_accion"],
                name="idx_regla_tipo_tramite_accion",
            ),
        ]

    def __str__(self):
        return f"Regla {self.tipo_tramite}/{self.tramite_accion} -> {self.tarifa_base}"
