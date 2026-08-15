"""
Helpers compartidos de presenters de liquidaciones.

Agrupa mapeos idénticos entre presenters del mismo motor para evitar duplicación.
"""


def present_tarifas_vigentes_po(tarifas, especialidades_disponibles) -> dict:
    """
    Mapea TarifaPorcentajeObra domain objects y LiquidacionEspecialidadDisponibles
    a un dict de respuesta (motor PorcentajeObra).

    Con tarifa-unica-especialidades: la tarifa única ya no tiene FK especialidad.
    El frontend usa LiquidacionEspecialidadDisponibles para elegir qué especialidades
    aplicar. Presenter solo conoce Domain objects y dicts — sin ORM.
    """
    return {
        "tarifas": [
            {
                "id": str(t.id),
                "porcentaje_liquidacion": float(t.porcentaje_liquidacion),
            }
            for t in tarifas
        ],
        "especialidades_disponibles": [
            {
                "id": str(e.especialidad.id),
                "codigo": e.especialidad.codigo if hasattr(e.especialidad, "codigo") else None,
                "nombre": e.especialidad.nombre,
            }
            for e in especialidades_disponibles
        ],
    }
