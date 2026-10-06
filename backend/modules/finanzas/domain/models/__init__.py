# -*- coding: utf-8 -*-
from .impuestos import IGV, UIT
from .recibo_honorario import ReciboHonorarioDelegado
from .tasa_delegado import TasaDelegado
from .descuento_inspector import EscalaDescuentoInspector, RangoDescuentoInspector
from .recibo_honorario_inspector import ReciboHonorarioInspector
from .recibo_honorario_inspector_mensual import ReciboHonorarioInspectorMensual
from .recibo_honorario_delegado_mensual import ReciboHonorarioDelegadoMensual
from .detalle_honorario_inspector import DetalleHonorarioInspector
from .detalle_honorario_delegado import DetalleHonorarioDelegado
from .registro_pago_inspector import RegistroPagoInspector
from .rh_reparticion_estacional import (
    RHReparticionEstacional,
    RHReparticionEstacionalDelegado,
    RHReparticionEstacionalCapitulo,
)

__all__ = [
    "IGV",
    "UIT",
    "ReciboHonorarioDelegado",
    "TasaDelegado",
    "EscalaDescuentoInspector",
    "RangoDescuentoInspector",
    "ReciboHonorarioInspector",
    "ReciboHonorarioInspectorMensual",
    "ReciboHonorarioDelegadoMensual",
    "DetalleHonorarioInspector",
    "DetalleHonorarioDelegado",
    "RegistroPagoInspector",
    "RHReparticionEstacional",
    "RHReparticionEstacionalDelegado",
    "RHReparticionEstacionalCapitulo",
]
