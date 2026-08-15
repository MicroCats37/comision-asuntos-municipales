"""
Shared fixtures index for liquidaciones integration tests.

Fixtures organized into the fixtures/ subpackage.
This file re-exports them directly so pytest discovers them.

Factories (make_payload_*) are NOT re-exported — import directly:
    from modules.liquidaciones.tests.fixtures.factories import make_payload_po
"""
from modules.liquidaciones.tests.fixtures.usuarios_fixtures import (
    api_client,
    create_user,
    auth_client,
    usuario_admin,
)
from modules.liquidaciones.tests.fixtures.ubigeo_fixtures import (
    ubigeo_departamento,
    ubigeo_provincia,
    ubigeo_distrito,
    municipalidad,
    proyecto,
)
from modules.liquidaciones.tests.fixtures.finanzas_fixtures import (
    igv_vigente,
    uit_vigente,
)
from modules.liquidaciones.tests.fixtures.tipos_fixtures import (
    tipo_edificacion,
    tipo_habilitacion_urbana,
    tipo_mecanica_suelos,
    tipo_impacto_vial,
    tipo_taludes,
    tipo_inspeccion_obra,
)
from modules.liquidaciones.tests.fixtures.tarifas_po_fixtures import (
    tarifa_liquidacion_base_edificacion,
    especialidad_estructuras,
    especialidad_arquitectura,
    especialidad_installaciones,
    tarifa_porcentaje_obra_estructuras,
    tarifa_porcentaje_obra_arquitectura,
    tarifa_porcentaje_obra_installaciones,
    especialidades_disponibles_edificacion,
    derecho_porcentaje_vigente,
)
from modules.liquidaciones.tests.fixtures.tarifas_m2_fixtures import (
    tarifa_liquidacion_base_hu,
    tarifa_m2_hu,
    tarifa_liquidacion_base_ms,
    tarifa_m2_ms,
    derecho_m2_vigente,
)
from modules.liquidaciones.tests.fixtures.tarifas_io_fixtures import (
    tarifa_liquidacion_base_io,
    tarifa_visitas_io,
)
from modules.liquidaciones.tests.fixtures.setup_po_fixtures import (
    po_base_setup,
)
from modules.liquidaciones.tests.fixtures.setup_m2_fixtures import (
    m2_base_setup,
)
from modules.liquidaciones.tests.fixtures.setup_io_fixtures import (
    io_base_setup,
)
