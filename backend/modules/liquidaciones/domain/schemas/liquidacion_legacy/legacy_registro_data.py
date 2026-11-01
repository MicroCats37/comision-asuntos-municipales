"""
LegacyRegistroContexto — contexto de dominio del REGISTRO LEGACY MANUAL.

Es el DTO que transporta la identidad histórica explícita (`numero` +
`fecha_registro`) y los valores financieros RESUELTOS en esa fecha.

Reglas del contrato de este change:
- `numero` es un dato histórico INFORMATIVO: se persiste tal cual y PUEDE
  repetirse. No hay unicidad, ni constraint, ni 409.
- `fecha_registro` es explícita y gobierna TODA la resolución histórica
  (IGV, UIT, tarifas, derechos).
- `legacy=True` lo asigna el SERVIDOR (la ruta es el discriminador); el
  cliente nunca lo envía.

Ciclo de vida:
1. El CONTROLLER construye el contexto con la identidad (`numero`,
   `fecha_registro`) que llega del payload tipado.
2. El ORCHESTRATOR lo completa con las entidades históricas resueltas por el
   resolver canónico (`igv`, `uit`, `derecho`, `tarifa`).
3. El FLUJO lo consume para persistir `fecha_registro`, `legacy=True`, los
   FK de IGV/UIT y el `numero` explícito del wrapper específico.

Los campos `igv`/`uit`/`derecho`/`tarifa` son instancias ORM (arbitrary types
permitido) porque el flujo las usa como FKs y como snapshots de la fila
específica; el contexto NO abre transacciones ni muta nada.
"""
from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class LegacyRegistroContexto(BaseModel):
    """
    Identidad histórica explícita + valores financieros resueltos en esa fecha.

    Attributes:
        numero: Número explícito del registro (informativo, repetible).
        fecha_registro: Fecha efectiva que gobierna el cálculo histórico.
        igv: Entidad IGV vigente en `fecha_registro` (la resuelve el orchestrator).
        uit: Entidad UIT vigente en `fecha_registro` (la resuelve el orchestrator).
        derecho: DerechoPorcentajeObra | DerechoPorMetroCuadrado vigente en la fecha.
        tarifa: TarifaPorMetroCuadrado | TarifaPorCategoriaVisitas vigente en la fecha.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    numero: int
    fecha_registro: date
    igv: Optional[Any] = None
    uit: Optional[Any] = None
    derecho: Optional[Any] = None
    tarifa: Optional[Any] = None
