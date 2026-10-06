"""
LiquidacionRelacionGrupo code generator helper.

Provides a pure function to generate unique technical codes for grupos.
Format: LQG-YYYYMMDD-HHMMSS-XXXX  (where XXXX = 4 hex chars from UUID4)

This is a pure helper — no DB access. The caller (core service or flow)
is responsible for ensuring uniqueness (e.g., retry loop or pre-check).

Usage:
    from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_codigo_helper import generar_codigo_grupo

    codigo = generar_codigo_grupo()  # e.g. "LQG-20260926-153012-A8F3"
"""

import uuid
from datetime import datetime, timezone


def generar_codigo_grupo() -> str:
    """
    Generate a unique technical code for LiquidacionRelacionGrupo.

    Format: LQG-YYYYMMDD-HHMMSS-XXXX
    - YYYYMMDD: date in UTC
    - HHMMSS: time in UTC
    - XXXX: last 4 uppercase hex chars of a UUID v4

    The code is not guaranteed unique across concurrent calls — caller must
    handle uniqueness (e.g., retry loop or DB unique-constraint violation catch).

    Returns:
        str: A code string in the format LQG-YYYYMMDD-HHMMSS-XXXX
    """
    now = datetime.now(timezone.utc)
    suffix = uuid.uuid4().hex[-4:].upper()
    return f"LQG-{now.strftime('%Y%m%d-%H%M%S')}-{suffix}"


def generar_codigo_grupo_con_reintento(max_intentos: int = 3) -> tuple[str, bool]:
    """
    Generate a unique code with retry logic.

    Since this helper has no DB access, it cannot pre-check uniqueness.
    It returns a candidate code and a flag indicating whether the suffix
    was regenerated (hinting at a potential collision in high-concurrency scenarios).

    The caller is still responsible for catching IntegrityError on insert
    and retrying at the DB level if needed.

    Args:
        max_intentos: Number of suffix regeneration attempts (default 3).

    Returns:
        tuple[str, bool]: (codigo, fue_reintentado)
            - codigo: the generated code
            - fue_reintentado: True if a collision was likely and suffix was regenerated
    """
    intento = 0
    suffix_base = uuid.uuid4().hex[-4:].upper()
    now = datetime.now(timezone.utc)
    codigo = f"LQG-{now.strftime('%Y%m%d-%H%M%S')}-{suffix_base}"

    # Simple heuristic: if max_intentos > 1, regenerate suffix
    # to reduce probability of concurrent collision
    if max_intentos > 1:
        for i in range(1, max_intentos):
            # Low probability event — regenerate to be safe
            suffix = uuid.uuid4().hex[-4:].upper()
            codigo = f"LQG-{now.strftime('%Y%m%d-%H%M%S')}-{suffix}"
            intento = i

    return codigo, intento > 0
