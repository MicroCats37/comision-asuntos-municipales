"""
FinanzasPresenter — transforma VariablesVigentesResult a esquema HTTP.

Cumple con el contrato de arquitectura (sección 4.9: presenters).
"""
from modules.finanzas.domain.schemas import VariablesVigentesResult
from modules.finanzas.presentation.schemas.finanzas_schemas import VariablesFinancierasOut


class FinanzasPresenter:
    """
    Presenter para transformación de resultados de dominio a esquemas HTTP.

    Responsabilidad: transformar explícitamente VariablesVigentesResult
    (dominio completo) → VariablesFinancierasOut (respuesta HTTP simplificada para frontend).
    """

    @staticmethod
    def present_variables_vigentes(domain_result: VariablesVigentesResult) -> VariablesFinancierasOut:
        """
        Transforma VariablesVigentesResult (dominio) a VariablesFinancierasOut (HTTP).

        Mapeo:
        - igv_valor → igv_valor
        - igv_periodo_inicio → igv_periodo_inicio (ISO string)
        - uit_valor → uit_valor
        - uit_periodo_inicio → uit_periodo_inicio (ISO string)

        Args:
            domain_result: VariablesVigentesResult del orchestrator

        Returns:
            VariablesFinancierasOut listo para success_response()
        """
        return VariablesFinancierasOut(
            igv_valor=domain_result.igv_valor,
            igv_periodo_inicio=domain_result.igv_periodo_inicio.isoformat(),
            uit_valor=domain_result.uit_valor,
            uit_periodo_inicio=domain_result.uit_periodo_inicio.isoformat(),
        )
