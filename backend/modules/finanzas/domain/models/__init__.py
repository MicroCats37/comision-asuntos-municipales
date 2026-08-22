# -*- coding: utf-8 -*-
from .impuestos import IGV, UIT
from .recibo_honorario import ReciboHonorarioDelegado
from .descuento_inspector import EscalaDescuentoInspector, RangoDescuentoInspector
from .recibo_honorario_inspector import ReciboHonorarioInspector
from .recibo_honorario_inspector_mensual import ReciboHonorarioInspectorMensual
from .detalle_honorario_inspector import DetalleHonorarioInspector
from .registro_pago_inspector import RegistroPagoInspector

__all__ = [
    "IGV",
    "UIT",
    "ReciboHonorarioDelegado",
    "EscalaDescuentoInspector",
    "RangoDescuentoInspector",
    "ReciboHonorarioInspector",
    "ReciboHonorarioInspectorMensual",
    "DetalleHonorarioInspector",
    "RegistroPagoInspector",
]
