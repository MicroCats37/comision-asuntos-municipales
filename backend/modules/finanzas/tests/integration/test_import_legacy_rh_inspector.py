"""Pruebas focalizadas del comando ``import_legacy_rh_inspector``.

Cubre las decisiones de la migración de RH de inspectores:

- Detección de plantilla tolerante (``EXPEDIENTE`` / ``EXPEDIENTES``).
- Detección de periodo con el año pegado al mes (``SETIEMBRE2026``).
- Normalización de texto para el emparejamiento por clave compuesta.
- Regla uno-a-uno: una misma IO no se puede asignar dos veces en un libro.
- Especialidad de revisión resuelta por capítulo, con respaldo genérico.
- El vínculo IO ↔ inspector se crea **sin operatividad** (política aplicada).
- El modo dry-run no escribe nada en la base.
"""
from decimal import Decimal

import pytest
from openpyxl import Workbook

from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.entidades.domain.models.ubigeo import (
    UbigeoDepartamento,
    UbigeoDistrito,
    UbigeoProvincia,
)
from modules.finanzas.management.commands.import_legacy_rh_inspector import (
    _composite_key,
    _composite_matches,
    _especialidad_por_capitulo,
    _ensure_inspector_io,
    _headers,
    _match_text,
    _period,
    _resolve_operativity_key,
)
from modules.liquidaciones.domain.models.inspector import (
    Inspector,
    InspectorOperacion,
    LiquidacionInspector,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.proyecto import Proyecto
from modules.liquidaciones.domain.models.tipo_liquidacion import (
    TipoLiquidacion as TipoLiquidacionModel,
)
from modules.liquidaciones.domain.constants import TipoLiquidacion as TipoLiquidacionConst
from modules.usuarios.domain.models.perfil_ingeniero import (
    Capitulo,
    EspecialidadRevision,
    EspecialidadRevisionCapitulo,
    PerfilIngeniero,
)


# ─────────────────────────── Helpers de worksheet ───────────────────────────


def _build_sheet(headers, period_value="SETIEMBRE 2026"):
    """Builds a worksheet pair (formulas / values) with the expected layout."""
    workbook = Workbook()
    formula_ws = workbook.active
    formula_ws.cell(1, 4, "0=DIC 2024; 1=ENERO 2025")
    formula_ws.cell(1, 9, "DIGITAR N° DEL MES DEL AÑO")
    formula_ws.cell(1, 10, "=HLOOKUP($D$1,$A$1:$Z$1,1,FALSE)")
    for index, name in enumerate(headers, start=1):
        formula_ws.cell(7, index, name)
    values_workbook = Workbook()
    values_ws = values_workbook.active
    values_ws.cell(1, 10, period_value)
    for index, name in enumerate(headers, start=1):
        values_ws.cell(7, index, name)
    return formula_ws, values_ws


# ───────────────────────────── Detección de plantilla ────────────────────────


def test_headers_acepta_expediente_en_singular():
    formula_ws, values_ws = _build_sheet(["ITEM", "EXPEDIENTE", "INSPECCIONES DEL MES"])
    header_row, headers = _headers(values_ws)
    assert header_row == 7
    assert "EXPEDIENTE" in headers


def test_headers_acepta_expedientes_en_plural():
    """El libro de Peña Ruesta trae ``EXPEDIENTES`` y antes quedaba omitido."""
    formula_ws, values_ws = _build_sheet(["ITEM", "EXPEDIENTES", "INSPECCIONES DEL MES"])
    header_row, headers = _headers(values_ws)
    assert header_row == 7
    assert "EXPEDIENTES" in headers


def test_headers_ignora_hoja_sin_columnas_de_visitas():
    formula_ws, values_ws = _build_sheet(["ITEM", "EXPEDIENTE"])
    header_row, headers = _headers(values_ws)
    assert header_row is None


# ─────────────────────────── Detección de periodo ────────────────────────────


def test_period_con_espacio_entre_mes_y_anio():
    formula_ws, values_ws = _build_sheet(["ITEM", "EXPEDIENTE", "INSPECCIONES DEL MES"])
    assert _period(formula_ws, values_ws) == (2026, 9)


def test_period_con_anio_pegado_al_mes():
    """El libro de Martinez Sosa trae ``SETIEMBRE2026`` sin espacio."""
    formula_ws, values_ws = _build_sheet(
        ["ITEM", "EXPEDIENTE", "INSPECCIONES DEL MES"], period_value="SETIEMBRE2026"
    )
    assert _period(formula_ws, values_ws) == (2026, 9)


def test_period_devuelve_none_sin_hlookup():
    workbook = Workbook()
    formula_ws = workbook.active
    values_ws = Workbook().active
    assert _period(formula_ws, values_ws) is None


# ─────────────────────── Normalización y clave compuesta ────────────────────


def test_match_text_normaliza_acentos_mayusculas_y_espacios():
    assert _match_text("  Ingenieria  Civil ") == "INGENIERIA CIVIL"
    assert _match_text("Ingeniería Civil") == _match_text("INGENIERIA CIVIL")


def test_composite_key_usa_propietario_distrito_y_visitas():
    key = _composite_key("Propietario Sac", "San Borja", 4)
    assert key == ("PROPIETARIO SAC", "SAN BORJA", 4)


class _FakeLcv:
    def __init__(self, identifier):
        self.id = identifier


def test_composite_matches_devuelve_el_unico_candidato():
    index = {_composite_key("Propietario Sac", "San Borja", 4): [_FakeLcv(1)]}
    matches = _composite_matches(index, "PROPIETARIO SAC", "SAN BORJA", 4, set())
    assert [item.id for item in matches] == [1]


def test_composite_matches_no_reutiliza_una_io_ya_usada():
    """Regla uno a uno: la misma IO no se asigna dos veces en el mismo libro."""
    index = {_composite_key("Propietario Sac", "San Borja", 4): [_FakeLcv(1)]}
    matches = _composite_matches(index, "PROPIETARIO SAC", "SAN BORJA", 4, {1})
    assert matches == []


def test_composite_matches_es_ambigua_con_dos_candidatos():
    index = {
        _composite_key("Propietario Sac", "San Borja", 4): [_FakeLcv(1), _FakeLcv(2)],
    }
    matches = _composite_matches(index, "PROPIETARIO SAC", "SAN BORJA", 4, set())
    assert len(matches) == 2


def test_composite_matches_ignora_datos_incompletos():
    index = {_composite_key("Propietario Sac", "San Borja", 4): [_FakeLcv(1)]}
    assert _composite_matches(index, "", "SAN BORJA", 4, set()) == []
    assert _composite_matches(index, "PROPIETARIO SAC", "", 4, set()) == []
    assert _composite_matches(index, "PROPIETARIO SAC", "SAN BORJA", 0, set()) == []


# ─────────────────────────────── Fixtures de BD ──────────────────────────────


@pytest.fixture
def ubigeo(db):
    depto = UbigeoDepartamento.objects.create(nombre="LIMA")
    prov = UbigeoProvincia.objects.create(departamento=depto, nombre="LIMA")
    return UbigeoDistrito.objects.create(provincia=prov, nombre="MIRAFLORES", ubigeo="150132")


@pytest.fixture
def municipalidad(db, ubigeo):
    return Municipalidad.objects.create(
        codigo="M001", nombre="Municipalidad de Miraflores", distrito=ubigeo
    )


@pytest.fixture
def tipo_io(db):
    return TipoLiquidacionModel.objects.get_or_create(
        codigo=TipoLiquidacionConst.INSPECCION_OBRA,
        defaults={"nombre": "Inspección de Obra"},
    )[0]


@pytest.fixture
def capitulo(db):
    return Capitulo.objects.create(
        registro_id="02", abreviacion="CIVIL", nombre="INGENIERIA CIVIL"
    )


@pytest.fixture
def especialidad_civil(db):
    return EspecialidadRevision.objects.create(slug="civil", nombre="Ingeniería Civil")


@pytest.fixture
def especialidad_generica(db):
    return EspecialidadRevision.objects.create(
        slug="inspeccion-obra", nombre="Inspección de Obra"
    )


@pytest.fixture
def mapeo_capitulo(db, capitulo, especialidad_civil):
    return EspecialidadRevisionCapitulo.objects.create(
        capitulo=capitulo, especialidad_revision=especialidad_civil
    )


@pytest.fixture
def perfil(db, capitulo):
    return PerfilIngeniero.objects.create(
        cip="076798",
        nombres="RONALD",
        apellido_paterno="AMORETTI",
        apellido_materno="SOTELO",
        capitulo=capitulo,
    )


@pytest.fixture
def inspector(db, perfil):
    return Inspector.objects.create(perfil_ingeniero=perfil)


@pytest.fixture
def liquidacion_io(db, municipalidad, tipo_io, ubigeo):
    proyecto = Proyecto.objects.create(
        nombre_propietario="Propietario IO SAC",
        direccion="Av. Test 123",
        distrito=ubigeo,
        entidad_tipo_documento="RUC",
        entidad_numero_documento="20456789012",
        entidad_razon_social="Propietario IO SAC",
    )
    general = LiquidacionGeneral.objects.create(
        proyecto=proyecto,
        municipalidad=municipalidad,
        tipo_liquidacion=tipo_io,
        expediente="EXP-RH-001",
        estado="REGISTRADO",
        sub_total=Decimal("1000.00"),
        total=Decimal("1180.00"),
    )
    return LiquidacionPorCategoriaVisitas.objects.create(
        liquidacion_general=general,
        cantidad_visitas=10,
        porcentaje_uit=Decimal("0.05"),
        categoria="3",
    )


# ───────────────────── Especialidad resuelta por capítulo ────────────────────


def test_especialidad_por_capitulo_resuelve_el_mapeo(db, perfil, mapeo_capitulo, especialidad_civil):
    especialidad, status = _especialidad_por_capitulo(perfil.capitulo_id)
    assert especialidad == especialidad_civil
    assert status is None


def test_especialidad_por_capitulo_sin_mapeo_usa_la_generica(db, perfil, especialidad_generica):
    """Sin mapeo se usa la especialidad genérica y se reporta la inconsistencia."""
    especialidad, status = _especialidad_por_capitulo(perfil.capitulo_id)
    assert especialidad == especialidad_generica
    assert status == "CAPITULO_SIN_MAPEO"


def test_especialidad_por_capitulo_sin_capitulo(db):
    especialidad, status = _especialidad_por_capitulo(None)
    assert especialidad is None
    assert status == "SIN_CAPITULO"


# ───────────────── Política de operatividad: el vínculo va en NULL ────────────


def test_ensure_inspector_io_crea_el_vinculo_sin_operatividad(
    db, inspector, liquidacion_io, perfil, mapeo_capitulo, especialidad_civil
):
    """La migración NO crea operatividades: el vínculo queda con operatividad nula."""
    resultado, status = _ensure_inspector_io("076798", liquidacion_io, apply=True)
    assert resultado == inspector
    vinculo = LiquidacionInspector.objects.get(
        liquidacion=liquidacion_io, inspector=inspector
    )
    assert vinculo.inspector_operacion_id is None
    assert vinculo.especialidad_revision == especialidad_civil
    assert InspectorOperacion.objects.filter(inspector=inspector).count() == 0


def test_ensure_inspector_io_no_toca_los_vinculos_existentes(
    db, inspector, liquidacion_io, perfil, mapeo_capitulo, especialidad_civil, tipo_io
):
    """Si el vínculo ya existe, no se modifica (idempotencia)."""
    operacion = InspectorOperacion.objects.create(
        inspector=inspector,
        tipo_liquidacion=tipo_io,
        categoria="3",
        especialidad_revision=especialidad_civil,
    )
    LiquidacionInspector.objects.create(
        liquidacion=liquidacion_io,
        inspector=inspector,
        inspector_operacion=operacion,
        especialidad_revision=especialidad_civil,
    )
    _ensure_inspector_io("076798", liquidacion_io, apply=True)
    vinculo = LiquidacionInspector.objects.get(
        liquidacion=liquidacion_io, inspector=inspector
    )
    assert vinculo.inspector_operacion_id == operacion.id
    assert InspectorOperacion.objects.filter(inspector=inspector).count() == 1


def test_resolve_operativity_key_sin_operatividad_para_vinculo_nuevo(
    db, inspector, liquidacion_io, perfil, mapeo_capitulo
):
    assert _resolve_operativity_key(inspector, liquidacion_io) == "SIN_OPERATIVIDAD"


def test_resolve_operativity_key_devuelve_la_operatividad_del_vinculo(
    db, inspector, liquidacion_io, perfil, mapeo_capitulo, especialidad_civil, tipo_io
):
    operacion = InspectorOperacion.objects.create(
        inspector=inspector,
        tipo_liquidacion=tipo_io,
        categoria="3",
        especialidad_revision=especialidad_civil,
    )
    LiquidacionInspector.objects.create(
        liquidacion=liquidacion_io,
        inspector=inspector,
        inspector_operacion=operacion,
        especialidad_revision=especialidad_civil,
    )
    assert _resolve_operativity_key(inspector, liquidacion_io) == str(operacion.id)


# ────────────── Expediente: el comando NO debe tocarlo ────────────────────────


def test_items_anidados_desde_dict_no_marcan_expediente_como_enviado():
    """Al anidar dicts, ``expediente`` queda ausente y el flujo no lo toca.

    Si se pasara una instancia del schema, Pydantic la reconstruye al
    anidarla y marca TODOS sus campos como enviados: ``expediente`` vacio
    significa "limpiar" y borra el expediente de la liquidacion.
    """
    from modules.finanzas.domain.schemas import (
        RHInspectorCotizarIn,
        RHInspectorCotizarItemIn,
    )

    item = RHInspectorCotizarItemIn(
        liquidacion_categoria_visitas_id="abc", cantidad_visitas=2
    )
    payload_instancia = RHInspectorCotizarIn(
        cip="023555", periodo=2026, mes=10, items=[item]
    )
    payload_dict = RHInspectorCotizarIn(
        cip="023555",
        periodo=2026,
        mes=10,
        items=[{"liquidacion_categoria_visitas_id": "abc", "cantidad_visitas": 2}],
    )
    assert "expediente" not in payload_dict.items[0].model_fields_set
    assert "expediente" in payload_instancia.items[0].model_fields_set
