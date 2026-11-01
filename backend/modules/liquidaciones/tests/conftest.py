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
    tarifa_liquidacion_base_taludes,
    especialidad_taludes,
    tarifa_porcentaje_obra_taludes,
    tarifa_liquidacion_base_iv,
    especialidad_impacto_vial,
    tarifa_porcentaje_obra_iv,
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
from modules.liquidaciones.tests.fixtures.legacy_historico_fixtures import (
    fecha_registro_historica,
    igv_historico_2023,
    uit_historico_2023,
    derecho_porcentaje_historico_2023,
    derecho_m2_historico_2023,
    especialidad_historica_edificaciones,
    especialidades_disponibles_historicas_edificacion,
    tarifa_base_po_historica_edificacion,
    tarifa_po_historica_edificacion,
    especialidad_historica_taludes,
    especialidad_disponible_historica_taludes,
    tarifa_base_po_historica_taludes,
    tarifa_po_historica_taludes,
    especialidad_historica_impacto_vial,
    especialidad_disponible_historica_impacto_vial,
    tarifa_base_po_historica_impacto_vial,
    tarifa_po_historica_impacto_vial,
    tarifa_base_m2_historica_habilitacion_urbana,
    tarifa_m2_historica_habilitacion_urbana,
    tarifa_base_m2_historica_mecanica_suelos,
    tarifa_m2_historica_mecanica_suelos,
    tarifa_base_visitas_historica_inspeccion_obra,
    tarifa_visitas_historica_inspeccion_obra,
    catalogo_legacy_historico,
)
