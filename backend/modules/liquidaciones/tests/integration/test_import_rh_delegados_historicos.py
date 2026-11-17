"""
Tests for `import_rh_delegados_historicos` (carga historica formal de RH Delegados).

Cubre el contrato del comando:

1. Normalizacion pura del CSV (CIP, dictamen, especialidad, fila completa, fechas).
2. Resolucion contextual de la `DelegadoOperacion` (exacta / wildcard / ambigua /
   especialidad distinta / ninguna).
3. Resolucion de la `EspecialidadRevision` desde el nombre canonico.
4. Lectura del CSV con deteccion de filas invalidas.
5. Reglas de asociacion del planificador (liquidacion legacy, duplicados,
   conflictos de constraint, idempotencia, CODPAGO como solo validacion).
6. Contrato de seguridad del comando (dry-run por defecto, confirmacion
   explicita, una sola transaccion, NO borra, NO crea recibos ni operaciones).

Tests sin `@pytest.mark.django_db`: el comando se valida por contrato de codigo
y por funciones puras, siguiendo el precedente de
`test_legacy_import_safety_contract.py`.
"""
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from modules.liquidaciones.management.commands.import_rh_delegados_historicos import (
    OPERACION_AMBIGUA,
    OPERACION_ESPECIALIDAD,
    OPERACION_LINK,
    OPERACION_NULA,
    SKIP_CONFLICTO,
    SKIP_DUPLICADO,
    SKIP_ESPECIALIDAD_INVALIDA,
    SKIP_ESPECIALIDAD_INEXISTENTE,
    SKIP_LIQUIDACION_AMBIGUA,
    SKIP_MES_INVALIDO,
    SKIP_NRO_INVALIDO,
    SKIP_NRO_ORDEN_INVALIDO,
    SKIP_PERIODO_INVALIDO,
    SKIP_SIN_LIQUIDACION,
    SKIP_YA_EXISTENTE,
    Command,
    build_especialidad_index,
    canonical_especialidad,
    normalize_dictamen,
    normalize_row,
    read_rh_rows,
    resolve_especialidad_id,
    resolve_operacion,
    strip_accents,
)


COMMANDS_DIR = Path(__file__).parents[2] / "management" / "commands"
COMMAND_NAME = "import_rh_delegados_historicos"

CSV_HEADERS = [
    "NRO",
    "CIP",
    "ESPECIALIDAD",
    "NROORDEN",
    "MES",
    "PERIODO",
    "DICTAMEN",
    "FECHAPRES",
    "FECHAREVI",
    "IMPBRUTO",
    "APORCODEMU",
    "FONDOCOMUN",
    "NETOHONORA",
    "HONORARIO",
    "RENTACIP",
    "CODPAGO",
]


def _source() -> str:
    return (COMMANDS_DIR / f"{COMMAND_NAME}.py").read_text(encoding="utf-8")


def _write_csv(path: Path, rows: list[dict]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter=";", fieldnames=CSV_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in CSV_HEADERS})
    return path


def _fila(**overrides) -> dict:
    base = {
        "NRO": "2563",
        "CIP": "12050",
        "ESPECIALIDAD": "Estructuras",
        "NROORDEN": "10",
        "MES": "08",
        "PERIODO": "2012",
        "DICTAMEN": "CONFORME",
        "FECHAPRES": "2010-08-04 00:00:00",
        "FECHAREVI": "2010-09-01 00:00:00",
        "IMPBRUTO": "103.40",
        "APORCODEMU": "10.34",
        "FONDOCOMUN": "51.70",
        "NETOHONORA": "41.36",
        "HONORARIO": "41.36",
        "RENTACIP": "25.85",
        "CODPAGO": "L5",
    }
    base.update(overrides)
    return base


# ── Normalizacion pura ────────────────────────────────────────────────────────


class TestNormalizeRow:
    def test_fila_completa_se_mapea(self):
        row, motivo = normalize_row(_fila(), 2)
        assert motivo is None
        assert row.nro == 2563
        assert row.cip == "012050"
        assert row.nro_orden == "10"
        assert row.especialidad_nombre == "Ingeniería Civil"
        assert row.mes == 8
        assert row.periodo == 2012
        assert row.dictamen == "CONFORME"
        assert row.fecha_presentacion == date(2010, 8, 4)
        assert row.fecha_revision == date(2010, 9, 1)
        assert row.imp_bruto == Decimal("103.40")
        assert row.aporte_codemu == Decimal("10.34")
        assert row.fondo_comun == Decimal("51.70")
        assert row.neto_honorario == Decimal("41.36")
        assert row.renta_cip == Decimal("25.85")
        assert row.codpago == "L5"

    def test_nro_no_numerico_es_invalida(self):
        row, motivo = normalize_row(_fila(NRO="Titu"), 2)
        assert row is None
        assert motivo == SKIP_NRO_INVALIDO

    def test_cip_no_numerico_es_invalida(self):
        row, motivo = normalize_row(_fila(CIP="Titu"), 2)
        assert row is None
        assert motivo == "cip_invalido"

    @pytest.mark.parametrize("nro_orden", ["0", "00", "NULL", ""])
    def test_nro_orden_no_positivo_es_invalido(self, nro_orden):
        row, motivo = normalize_row(_fila(NROORDEN=nro_orden), 2)
        assert row is None
        assert motivo == SKIP_NRO_ORDEN_INVALIDO

    @pytest.mark.parametrize("mes", ["0", "13", "NULL", ""])
    def test_mes_ausente_o_invalido_no_crea_rh(self, mes):
        row, motivo = normalize_row(_fila(MES=mes), 2)
        assert row is None
        assert motivo == SKIP_MES_INVALIDO

    @pytest.mark.parametrize("periodo", ["0", "NULL", ""])
    def test_periodo_ausente_o_invalido_no_crea_rh(self, periodo):
        row, motivo = normalize_row(_fila(PERIODO=periodo), 2)
        assert row is None
        assert motivo == SKIP_PERIODO_INVALIDO

    def test_especialidad_null_es_invalida(self):
        row, motivo = normalize_row(_fila(ESPECIALIDAD="NULL"), 2)
        assert row is None
        assert motivo == SKIP_ESPECIALIDAD_INVALIDA

    def test_fecha_sentinel_queda_none(self):
        row, motivo = normalize_row(_fila(FECHAPRES="1900-01-01 00:00:00"), 2)
        assert motivo is None
        assert row.fecha_presentacion is None

    def test_neto_honorario_cae_a_honorario(self):
        row, motivo = normalize_row(_fila(NETOHONORA="NULL", HONORARIO="7.77"), 2)
        assert motivo is None
        assert row.neto_honorario == Decimal("7.77")

    def test_importes_null_quedan_en_cero(self):
        row, motivo = normalize_row(
            _fila(IMPBRUTO="NULL", APORCODEMU="NULL", FONDOCOMUN="NULL", RENTACIP="NULL"), 2
        )
        assert motivo is None
        assert row.imp_bruto == Decimal("0")
        assert row.renta_cip == Decimal("0")


class TestCanonicalEspecialidad:
    @pytest.mark.parametrize(
        "raw,esperado",
        [
            ("Estructuras", "Ingeniería Civil"),
            ("Inst. Sanitarias", "Ingeniería Sanitaria"),
            ("Inst. Mecánico Eléctricas", "Ingeniería Eléctrica y Mecánica Eléctrica"),
            ("Inst. Eléctricas", "Ingeniería Eléctrica y Mecánica Eléctrica"),
            ("Inst. Electrónicas", "Ingeniería Electrónica"),
        ],
    )
    def test_aliases_del_csv(self, raw, esperado):
        assert canonical_especialidad(raw) == esperado

    def test_null_devuelve_none(self):
        assert canonical_especialidad("NULL") is None
        assert canonical_especialidad("") is None

    def test_especialidad_desconocida_devuelve_none(self):
        assert canonical_especialidad("Geotecnia") is None


class TestResolveEspecialidadId:
    def test_coincidencia_exacta(self):
        index = build_especialidad_index([_esp("Ingeniería Civil", "esp-1")])
        assert resolve_especialidad_id("Ingeniería Civil", index) == "esp-1"

    def test_fallback_por_prefijo(self):
        index = build_especialidad_index([_esp("Ingeniería Eléctrica y Mecánica Eléctrica", "e2")])
        assert resolve_especialidad_id("Ingeniería Eléctrica y Mecánica", index) == "e2"

    def test_inexistente_devuelve_none(self):
        index = build_especialidad_index([_esp("Ingeniería Civil", "esp-1")])
        assert resolve_especialidad_id("Inspección de Obra", index) is None


class TestNormalizeDictamen:
    def test_conforme(self):
        assert normalize_dictamen("CONFORME") == "CONFORME"

    def test_no_conforme(self):
        assert normalize_dictamen("NO CONFORME") == "NO_CONFORME"

    def test_ap_ob(self):
        assert normalize_dictamen("AP. OB") == "AP_OB"

    def test_null_devuelve_none(self):
        assert normalize_dictamen("NULL") is None

    def test_valor_invalido_devuelve_none(self):
        assert normalize_dictamen("CUALQUIERA") is None


class TestStripAccents:
    def test_quita_acentos(self):
        assert strip_accents("Ingeniería Civil") == "Ingenieria Civil"


def _esp(nombre, id_):
    class _Fake:
        def __init__(self):
            self.nombre = nombre
            self.id = id_

    return _Fake()


# ── Resolucion contextual de la operacion ─────────────────────────────────────


class TestResolveOperacion:
    def test_coincidencia_exacta(self):
        candidatas = [{"id": "op-1", "tipo_liquidacion_id": 7, "especialidad_revision_id": 3}]
        operacion, estado = resolve_operacion(candidatas, 7, 3)
        assert operacion == "op-1"
        assert estado == OPERACION_LINK

    def test_wildcard_cuando_no_hay_exacta(self):
        candidatas = [{"id": "op-1", "tipo_liquidacion_id": None, "especialidad_revision_id": 3}]
        operacion, estado = resolve_operacion(candidatas, 7, 3)
        assert operacion == "op-1"
        assert estado == OPERACION_LINK

    def test_exacta_y_wildcard_es_ambigua(self):
        candidatas = [
            {"id": "op-1", "tipo_liquidacion_id": 7, "especialidad_revision_id": 3},
            {"id": "op-2", "tipo_liquidacion_id": None, "especialidad_revision_id": 3},
        ]
        operacion, estado = resolve_operacion(candidatas, 7, 3)
        assert operacion is None
        assert estado == OPERACION_AMBIGUA

    def test_varias_wildcards_es_ambigua(self):
        candidatas = [
            {"id": "op-1", "tipo_liquidacion_id": None, "especialidad_revision_id": 3},
            {"id": "op-2", "tipo_liquidacion_id": None, "especialidad_revision_id": 3},
        ]
        operacion, estado = resolve_operacion(candidatas, 7, 3)
        assert operacion is None
        assert estado == OPERACION_AMBIGUA

    def test_especialidad_distinta_deja_operacion_null(self):
        candidatas = [{"id": "op-1", "tipo_liquidacion_id": 7, "especialidad_revision_id": 9}]
        operacion, estado = resolve_operacion(candidatas, 7, 3)
        assert operacion is None
        assert estado == OPERACION_ESPECIALIDAD

    def test_sin_operaciones_devuelve_null(self):
        operacion, estado = resolve_operacion([], 7, 3)
        assert operacion is None
        assert estado == OPERACION_NULA


# ── Lectura del CSV ───────────────────────────────────────────────────────────


class TestReadRhRows:
    def test_separa_filas_validas_e_invalidas(self, tmp_path):
        path = _write_csv(
            tmp_path / "rh.csv",
            [_fila(), _fila(NRO="Titu"), _fila(ESPECIALIDAD="NULL")],
        )
        filas, invalidas = read_rh_rows(path)
        assert len(filas) == 1
        assert len(invalidas) == 2
        assert invalidas[0]["motivo"] == SKIP_NRO_INVALIDO
        assert invalidas[1]["motivo"] == SKIP_ESPECIALIDAD_INVALIDA

    def test_limit_corta_la_lectura(self, tmp_path):
        path = _write_csv(tmp_path / "rh.csv", [_fila(), _fila()])
        filas, invalidas = read_rh_rows(path, limit=1)
        assert len(filas) == 1
        assert invalidas == []


# ── Reglas de asociacion del planificador ─────────────────────────────────────


def _indexes(**overrides) -> dict:
    base = {
        "liquidaciones": {
            2563: [
                {
                    "liquidacion_id": "liq-1",
                    "municipalidad_id": "mun-1",
                    "tipo_liquidacion_id": 7,
                    "municipalidad_codigo": "L5",
                }
            ]
        },
        "delegados": {"012050": "del-1"},
        "operaciones": {
            ("del-1", "mun-1"): [
                {"id": "op-1", "tipo_liquidacion_id": 7, "especialidad_revision_id": "esp-1"}
            ]
        },
        "existentes": {},
    }
    base.update(overrides)
    return base


def _planificar(filas, indexes=None, especialidad_ids=None):
    command = Command()
    indexes = indexes if indexes is not None else _indexes()
    especialidad_ids = especialidad_ids or {"INGENIERIA CIVIL": "esp-1"}
    return command._planificar(filas, indexes, especialidad_ids)


class TestPlanificar:
    def test_fila_valida_entra_al_plan_con_operacion(self):
        fila, _ = normalize_row(_fila(), 2)
        plan, omitidas, detalle, avisos = _planificar([fila])
        assert len(plan) == 1
        assert plan[0].liquidacion_id == "liq-1"
        assert plan[0].delegado_id == "del-1"
        assert plan[0].especialidad_id == "esp-1"
        assert plan[0].operacion_id == "op-1"
        assert plan[0].operacion_estado == OPERACION_LINK
        assert omitidas == {}
        assert avisos == []

    def test_sin_liquidacion_legacy_se_omite(self):
        fila, _ = normalize_row(_fila(), 2)
        indexes = _indexes(liquidaciones={})
        plan, omitidas, detalle, avisos = _planificar([fila], indexes)
        assert plan == []
        assert omitidas[SKIP_SIN_LIQUIDACION] == 1
        assert detalle[0]["motivo"] == SKIP_SIN_LIQUIDACION

    def test_liquidacion_ambigua_se_omite(self):
        fila, _ = normalize_row(_fila(), 2)
        indexes = _indexes()
        indexes["liquidaciones"][2563].append(dict(indexes["liquidaciones"][2563][0]))
        plan, omitidas, detalle, avisos = _planificar([fila], indexes)
        assert plan == []
        assert omitidas[SKIP_LIQUIDACION_AMBIGUA] == 1

    def test_especialidad_inexistente_se_omite(self):
        fila, _ = normalize_row(_fila(), 2)
        # El indice de especialidades no contiene "Ingenieria Civil" -> se omite.
        plan, omitidas, detalle, avisos = _planificar(
            [fila], None, {"INGENIERIA SANITARIA": "otro"}
        )
        assert plan == []
        assert omitidas[SKIP_ESPECIALIDAD_INEXISTENTE] == 1

    def test_duplicado_csv_se_omite(self):
        fila, _ = normalize_row(_fila(), 2)
        plan, omitidas, detalle, avisos = _planificar([fila, fila])
        assert len(plan) == 1
        assert omitidas[SKIP_DUPLICADO] == 1

    def test_conflicto_de_constraint_se_omite(self):
        # Mismo NRO/CIP/especialidad pero distinto NROORDEN -> choca el constraint.
        fila1, _ = normalize_row(_fila(NROORDEN="1"), 2)
        fila2, _ = normalize_row(_fila(NROORDEN="2"), 3)
        plan, omitidas, detalle, avisos = _planificar([fila1, fila2])
        assert len(plan) == 1
        assert omitidas[SKIP_CONFLICTO] == 1

    def test_asignacion_ya_existente_se_omite(self):
        fila, _ = normalize_row(_fila(), 2)
        indexes = _indexes(existentes={("liq-1", "del-1", "esp-1"): "ld-1"})
        plan, omitidas, detalle, avisos = _planificar([fila], indexes)
        assert plan == []
        assert omitidas[SKIP_YA_EXISTENTE] == 1

    def test_codpago_distinto_solo_avisa_no_omite(self):
        fila, _ = normalize_row(_fila(CODPAGO="L9"), 2)
        plan, omitidas, detalle, avisos = _planificar([fila])
        assert len(plan) == 1
        assert omitidas == {}
        assert len(avisos) == 1
        assert avisos[0]["codpago_csv"] == "L9"
        assert avisos[0]["codpago_bd"] == "L5"

    def test_delegado_inexistente_queda_pendiente(self):
        fila, _ = normalize_row(_fila(), 2)
        indexes = _indexes(delegados={})
        plan, omitidas, detalle, avisos = _planificar([fila], indexes)
        assert len(plan) == 1
        assert plan[0].delegacion_pendiente is True
        assert plan[0].delegado_id is None


# ── Contrato de seguridad del comando ─────────────────────────────────────────


class TestContratoDeSeguridad:
    def test_dry_run_por_defecto(self):
        source = _source()
        assert 'action="store_true"' in source
        assert "--apply" in source
        assert source.count("DRY-RUN") >= 2

    def test_apply_exige_confirmacion_destructiva(self):
        source = _source()
        assert "--confirm-destructive" in source
        assert "if apply and not confirm:" in source
        assert "CommandError" in source

    def test_una_sola_transaccion(self):
        source = _source()
        assert "transaction.atomic()" in source
        assert source.count("transaction.atomic()") == 1

    def test_no_borra_nada(self):
        source = _source()
        assert ".delete(" not in source
        assert "objects.all().delete()" not in source

    def test_no_crea_recibo_honorario(self):
        source = _source()
        assert "ReciboHonorarioDelegado.objects" not in source
        assert "ReciboHonorarioDelegadoMensual.objects" not in source
        assert "recibo_honorario" not in source

    def test_no_crea_ni_habilita_operaciones(self):
        source = _source()
        assert "DelegadoOperacion.objects.create" not in source
        assert "DelegadoOperacion.objects.get_or_create" not in source
        assert "DelegadoOperacionPeriodo.objects" not in source

    def test_resuelve_solo_liquidaciones_legacy(self):
        source = _source()
        assert "liquidacion__legacy=True" in source
        assert "LiquidacionEdificacion.objects.filter" in source

    def test_el_municipio_se_hereda_de_la_liquidacion(self):
        source = _source()
        assert "liquidacion__municipalidad__codigo" in source
        # El CODPAGO del CSV solo se usa para comparar, nunca para asignar.
        assert "fila.codpago != codpago_bd" in source

    def test_idempotencia_por_constraint(self):
        source = _source()
        assert "indexes[\"existentes\"]" in source
        assert "SKIP_YA_EXISTENTE" in source
