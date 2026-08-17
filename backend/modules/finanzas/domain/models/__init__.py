# -*- coding: utf-8 -*-
from .impuestos import IGV, UIT
from .recibo_honorario import ReciboHonorarioDelegado
from .descuento_inspector import EscalaDescuentoInspector, RangoDescuentoInspector
from .recibo_honorario_inspector import ReciboHonorarioInspector

__all__ = [
    "IGV",
    "UIT",
    "ReciboHonorarioDelegado",
    "EscalaDescuentoInspector",
    "RangoDescuentoInspector",
    "ReciboHonorarioInspector",
]
