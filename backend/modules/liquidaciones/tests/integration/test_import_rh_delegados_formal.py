"""
Tests for `import_rh_delegados_formal` (recarga formal de RH Delegados).

Cubre el contrato del comando sin tocar la base de datos:

1. Normalizacion pura del CSV (CIP, dictamen, especialidad, fila completa).
2. Resolucion de la operacion habilitada (exacta / wildcard / ambigua / ninguna).
3. Resolucion de la `EspecialidadRevision` desde el nombre canonico.
4. Lectura del CSV con deteccion de filas invalidas.
5. Reglas de asociacion del planificador (una fila solo se asocia si cumple todo).
6. Contrato de seguridad del comando (dry-run por defecto, confirmacion
   destructiva, una sola transaccion, orden de borrado, sin llamadas CIP ni
   creación de operaciones/placeholders).

Tests sin `@pytest.mark.django_db`: el comando se valida por contrato de codigo
y por funciones puras, siguiendo el precedente de
`test_legacy_import_safety_contract.py`.
"""
import csv
from importlib import import_module
from pathlib import Path

import pytest

from modules.liquidaciones.management.commands.import_rh_delegados_formal import (
    Command,
    canonical_especialidad,
    normalize_cip,
    normalize_dictamen,
    normalize_row,
    read_rh_rows,
    resolve_especialidad_id,
    resolve_operacion,
    strip_accents,
)


COMMANDS_DIR = Path(__file__).parents[2] / "management" / "commands"
COMMAND_NAME = "import_rh_delegados_formal"

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
        "NROORDEN": "1",
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
    }
    base.update(overrides)
    return base


# ── Normalizacion pura ────────────────────────────────────────────────────────


class TestNormalizeCip:
    def test_normaliza_a_6_digitos(self):
        assert normalize_cip("12050") == "012050"

    def test_conserva_cip_de_6_digitos(self):
        assert normalize_cip("012050") == "012050"

    def test_ignora_espacios(self):
        assert normalize_cip("  12050  ") == "012050"

    def test_cip_no_numerico_devuelve_vacio(self):
        assert normalize_cip("Titu") == ""

    def test_cip_vacio_devuelve_vacio(self):
        assert normalize_cip(None) == ""


class TestNormalizeDictamen:
    def test_conforme_se_mantiene(self):
        assert normalize_dictamen("CONFORME") == "CONFORME"

    def test_no_conforme_se_normaliza(self):
        assert normalize_dictamen("NO CONFORME") == "NO_CONFORME"

    def test_ap_ob_se_normaliza(self):
        assert normalize_dictamen("AP. OB") == "AP_OB"

    def test_pendiente_se_mantiene(self):
        assert normalize_dictamen("PENDIENTE") == "PENDIENTE"

    def test_null_devuelve_none(self):
        assert normalize_dictamen("NULL") is None

    def test_valor_desconocido_devuelve_none(self):
        assert normalize_dictamen("REVISADO") is None


class TestCanonicalEspecialidad:
    def test_estructuras_mapea_a_civil(self):
        assert canonical_especialidad("Estructuras") == "Ingeniería Civil"

    def test_sanitarias_mapea_a_sanitaria(self):
        assert canonical_especialidad("Inst. Sanitarias") == "Ingeniería Sanitaria"

    def test_mecanico_electricas_mapea_a_electromecanica(self):
        assert (
            canonical_especialidad("Inst. Mecánico Eléctricas")
            == "Ingeniería Eléctrica y Mecánica Eléctrica"
        )

    def test_electronicas_mapea_a_electronica(self):
        assert canonical_especialidad("Inst. Electrónicas") == "Ingeniería Electrónica"

    def test_electricas_mapea_a_electromecanica(self):
        assert (
            canonical_especialidad("Inst. Eléctricas")
            == "Ingeniería Eléctrica y Mecánica Eléctrica"
        )

    def test_todas_no_es_una_especialidad(self):
        assert canonical_especialidad("TODAS") is None

    def test_null_devuelve_none(self):
        assert canonical_especialidad("NULL") is None


class TestResolveEspecialidadId:
    def test_encuentra_exacto(self):
        assert resolve_especialidad_id("Ingeniería Civil", {"INGENIERIA CIVIL": 7}) == 7

    def test_tolera_prefijo_entre_bd_y_csv(self):
        index = {"INGENIERIA ELECTRICA Y MECANICA": 9}
        assert (
            resolve_especialidad_id("Ingeniería Eléctrica y Mecánica Eléctrica", index) == 9
        )

    def test_sin_match_devuelve_none(self):
        assert resolve_especialidad_id("Ingeniería Civil", {"INGENIERIA SANITARIA": 3}) is None

    def test_indice_vacio_devuelve_none(self):
        assert resolve_especialidad_id("Ingeniería Civil", {}) is None


class TestStripAccents:
    def test_quita_acentos(self):
        assert strip_accents("Mecánico Eléctricas") == "Mecanico Electricas"


# ── Resolucion de operacion habilitada ───────────────────────────────────────


class TestResolveOperacion:
    def test_usa_coincidencia_exacta(self):
        candidatas = [
            {"id": 1, "tipo_liquidacion_id": 5, "especialidad_revision_id": 2},
            {"id": 2, "tipo_liquidacion_id": None, "especialidad_revision_id": 3},
        ]
        # exacta + wildcard -> ambiguo (mismo criterio del core service)
        assert resolve_operacion(candidatas, 5) == {"estado": "ambigua"}

    def test_exacta_unica(self):
        candidatas = [{"id": 1, "tipo_liquidacion_id": 5, "especialidad_revision_id": 2}]
        assert resolve_operacion(candidatas, 5)["id"] == 1

    def test_wildcard_unico(self):
        candidatas = [{"id": 1, "tipo_liquidacion_id": None, "especialidad_revision_id": 2}]
        assert resolve_operacion(candidatas, 5)["id"] == 1

    def test_varias_wildcard_son_ambiguas(self):
        candidatas = [
            {"id": 1, "tipo_liquidacion_id": None, "especialidad_revision_id": 2},
            {"id": 2, "tipo_liquidacion_id": None, "especialidad_revision_id": 3},
        ]
        assert resolve_operacion(candidatas, 5) == {"estado": "ambigua"}

    def test_sin_candidatas_devuelve_none(self):
        assert resolve_operacion([], 5) is None


# ── Lectura del CSV ───────────────────────────────────────────────────────────


class TestNormalizeRow:
    def test_fila_valida_mapea_los_campos(self):
        fila, motivo = normalize_row(_fila(), 2)
        assert motivo is None
        assert fila.nro == 2563
        assert fila.cip == "012050"
        assert fila.nro_orden == "1"
        assert fila.especialidad_nombre == "Ingeniería Civil"
        assert fila.mes == 8
        assert fila.periodo == 2012
        assert fila.dictamen == "CONFORME"
        assert fila.fecha_presentacion.isoformat() == "2010-08-04"
        assert fila.fecha_revision.isoformat() == "2010-09-01"
        assert str(fila.imp_bruto) == "103.40"
        assert str(fila.neto_honorario) == "41.36"
        assert str(fila.renta_cip) == "25.85"

    def test_nro_invalido_es_fila_invalida(self):
        fila, motivo = normalize_row(_fila(NRO="NULL"), 2)
        assert fila is None
        assert motivo == "nro_invalido"

    def test_cip_invalido_es_fila_invalida(self):
        fila, motivo = normalize_row(_fila(CIP="Titu"), 2)
        assert fila is None
        assert motivo == "cip_invalido"

    def test_nro_orden_invalido_es_fila_invalida(self):
        fila, motivo = normalize_row(_fila(NROORDEN="NULL"), 2)
        assert fila is None
        assert motivo == "nro_orden_invalido"

    def test_nro_orden_cero_es_fila_invalida(self):
        fila, motivo = normalize_row(_fila(NROORDEN="0"), 2)
        assert fila is None
        assert motivo == "nro_orden_invalido"

    def test_especialidad_invalida_es_fila_invalida(self):
        fila, motivo = normalize_row(_fila(ESPECIALIDAD="TODAS"), 2)
        assert fila is None
        assert motivo == "especialidad_invalida"

    def test_mes_fuera_de_rango_es_fila_invalida(self):
        fila, motivo = normalize_row(_fila(MES="13"), 2)
        assert fila is None
        assert motivo == "mes_invalido"

    def test_mes_nulo_es_fila_invalida(self):
        fila, motivo = normalize_row(_fila(MES="NULL"), 2)
        assert fila is None
        assert motivo == "mes_invalido"

    def test_periodo_nulo_es_fila_invalida(self):
        fila, motivo = normalize_row(_fila(PERIODO="NULL"), 2)
        assert fila is None
        assert motivo == "periodo_invalido"

    def test_neto_honorario_cae_a_honorario(self):
        fila, _ = normalize_row(_fila(NETOHONORA="NULL", HONORARIO="12.34"), 2)
        assert str(fila.neto_honorario) == "12.34"

    def test_fecha_centinela_1900_queda_null(self):
        fila, _ = normalize_row(_fila(FECHAPRES="1900-01-01 00:00:00"), 2)
        assert fila.fecha_presentacion is None

    def test_llave_csv_compone_nro_cip_nroorden(self):
        fila, _ = normalize_row(_fila(), 2)
        assert fila.key_csv == (2563, "012050", "1")


class TestReadRhRows:
    def test_separa_filas_validas_e_invalidas(self, tmp_path):
        path = _write_csv(
            tmp_path / "rh.csv",
            [
                _fila(),
                _fila(NRO="NULL"),
                _fila(CIP="Titu"),
            ],
        )
        filas, invalidas = read_rh_rows(path)

        assert len(filas) == 1
        assert len(invalidas) == 2
        assert {item["motivo"] for item in invalidas} == {"nro_invalido", "cip_invalido"}

    def test_limita_las_filas_leidas(self, tmp_path):
        path = _write_csv(
            tmp_path / "rh.csv",
            [_fila(NRO=str(100 + index)) for index in range(5)],
        )
        filas, invalidas = read_rh_rows(path, limit=2)

        assert len(filas) == 2
        assert invalidas == []


# ── Reglas de asociacion (planificador) ───────────────────────────────────────


class TestPlanificador:
    """El planificador decide que filas se asocian y cuales se omiten."""

    def _indexes(self, **overrides):
        indexes = {
            "liquidaciones": {
                2563: {
                    "liquidacion_id": "LIQ-1",
                    "municipalidad_id": "MUNI-1",
                    "tipo_liquidacion_id": "TIPO-1",
                }
            },
            "delegados": {"012050": "DEL-1"},
            "operaciones": {
                ("DEL-1", "MUNI-1"): [
                    {
                        "id": "OP-1",
                        "delegado_id": "DEL-1",
                        "municipalidad_id": "MUNI-1",
                        "tipo_liquidacion_id": "TIPO-1",
                        "especialidad_revision_id": "ESP-CIVIL",
                    }
                ]
            },
        }
        indexes.update(overrides)
        return indexes

    def _especialidades(self):
        return {"INGENIERIA CIVIL": "ESP-CIVIL"}

    def _planificar(self, filas, indexes=None, especialidades=None, allow_mismatch=False):
        command = Command()
        return command._planificar(
            filas,
            indexes if indexes is not None else self._indexes(),
            especialidades if especialidades is not None else self._especialidades(),
            allow_especialidad_mismatch=allow_mismatch,
        )

    def test_fila_completa_se_asocia(self):
        fila, _ = normalize_row(_fila(), 2)
        plan, omitidas, detalle = self._planificar([fila])

        assert len(plan) == 1
        assert plan[0].liquidacion_id == "LIQ-1"
        assert plan[0].delegado_id == "DEL-1"
        assert plan[0].operacion_id == "OP-1"
        assert plan[0].especialidad_id == "ESP-CIVIL"
        assert omitidas == {}
        assert detalle == []

    def test_sin_liquidacion_se_omite(self):
        fila, _ = normalize_row(_fila(), 2)
        indexes = self._indexes()
        indexes["liquidaciones"] = {}
        plan, omitidas, _ = self._planificar([fila], indexes=indexes)

        assert plan == []
        assert omitidas["sin_liquidacion_nro"] == 1

    def test_sin_delegado_se_omite(self):
        fila, _ = normalize_row(_fila(), 2)
        indexes = self._indexes()
        indexes["delegados"] = {}
        plan, omitidas, _ = self._planificar([fila], indexes=indexes)

        assert plan == []
        assert omitidas["sin_delegado_cip"] == 1

    def test_sin_operacion_habilitada_se_asocia_sin_operacion(self):
        fila, _ = normalize_row(_fila(), 2)
        indexes = self._indexes()
        indexes["operaciones"] = {}
        plan, omitidas, _ = self._planificar([fila], indexes=indexes)

        assert len(plan) == 1
        assert plan[0].operacion_id is None
        assert omitidas == {}

    def test_operacion_ambigua_se_asocia_sin_operacion(self):
        fila, _ = normalize_row(_fila(), 2)
        indexes = self._indexes()
        indexes["operaciones"][("DEL-1", "MUNI-1")] = [
            {
                "id": "OP-1",
                "delegado_id": "DEL-1",
                "municipalidad_id": "MUNI-1",
                "tipo_liquidacion_id": "TIPO-1",
                "especialidad_revision_id": "ESP-CIVIL",
            },
            {
                "id": "OP-2",
                "delegado_id": "DEL-1",
                "municipalidad_id": "MUNI-1",
                "tipo_liquidacion_id": None,
                "especialidad_revision_id": "ESP-CIVIL",
            },
        ]
        plan, omitidas, _ = self._planificar([fila], indexes=indexes)

        assert len(plan) == 1
        assert plan[0].operacion_id is None
        assert omitidas == {}

    def test_especialidad_inexistente_en_bd_se_omite(self):
        fila, _ = normalize_row(_fila(ESPECIALIDAD="Inst. Sanitarias"), 2)
        plan, omitidas, _ = self._planificar([fila])

        assert plan == []
        assert omitidas["especialidad_desconocida"] == 1

    def test_especialidad_distinta_se_asocia_sin_operacion(self):
        fila, _ = normalize_row(_fila(ESPECIALIDAD="Inst. Sanitarias"), 2)
        especialidades = {"INGENIERIA CIVIL": "ESP-CIVIL", "INGENIERIA SANITARIA": "ESP-SAN"}
        plan, omitidas, _ = self._planificar([fila], especialidades=especialidades)

        assert len(plan) == 1
        assert plan[0].operacion_id is None
        assert omitidas == {}

    def test_especialidad_distinta_se_puede_permitir(self):
        fila, _ = normalize_row(_fila(ESPECIALIDAD="Inst. Sanitarias"), 2)
        especialidades = {"INGENIERIA CIVIL": "ESP-CIVIL", "INGENIERIA SANITARIA": "ESP-SAN"}

        plan, omitidas, _ = self._planificar(
            [fila], especialidades=especialidades, allow_mismatch=True
        )

        assert len(plan) == 1
        assert plan[0].especialidad_id == "ESP-SAN"
        assert plan[0].especialidad_distinta is True

    def test_duplicado_csv_se_omite(self):
        fila, _ = normalize_row(_fila(), 2)
        duplicado, _ = normalize_row(_fila(), 3)
        plan, omitidas, _ = self._planificar([fila, duplicado])

        assert len(plan) == 1
        assert omitidas["duplicado_csv"] == 1

    def test_conflicto_de_constraint_se_omite(self):
        # Misma terna (liquidacion, delegado, especialidad) con NROORDEN distinto.
        primera, _ = normalize_row(_fila(NROORDEN="1"), 2)
        segunda, _ = normalize_row(_fila(NROORDEN="2"), 3)
        plan, omitidas, _ = self._planificar([primera, segunda])

        assert len(plan) == 1
        assert omitidas["conflicto_constraint"] == 1


# ── Contrato de seguridad del comando ─────────────────────────────────────────


class TestContratoDeSeguridad:
    def test_el_comando_es_importable(self):
        module = import_module(
            "modules.liquidaciones.management.commands.import_rh_delegados_formal"
        )
        assert module.Command

    def test_dry_run_es_el_default(self):
        source = _source()
        assert '"--apply",\n            action="store_true"' in source
        assert "if apply and not confirm:" in source
        assert "raise CommandError(" in source

    def test_exige_confirmacion_destructiva(self):
        source = _source()
        assert '"--confirm-destructive"' in source
        assert "--apply requiere --confirm-destructive" in source

    def test_el_borrado_y_la_importacion_usan_una_sola_transaccion(self):
        source = _source()
        assert source.count("with transaction.atomic():") == 1
        atomic_index = source.index("with transaction.atomic():")
        assert atomic_index < source.index("self._borrar(DetalleHonorarioDelegado)")
        assert atomic_index < source.index("self._importar(plan)")

    def test_orden_de_borrado_respeta_protect(self):
        source = _source()
        assert source.index("self._borrar(DetalleHonorarioDelegado)") < source.index(
            "self._borrar(LiquidacionDelegado)"
        )

    def test_no_llama_al_endpoint_cip(self):
        source = _source()
        assert "hydrate_perfil_from_cip" not in source
        assert "_ensure_perfil_ingeniero_by_cip" not in source
        assert "CREADO_PLACEHOLDER" not in source
        assert "httpx" not in source
        assert "requests" not in source

    def test_no_crea_operaciones_ni_placeholders(self):
        source = _source()
        assert "DelegadoOperacion.objects.create" not in source
        assert "DelegadoOperacionPeriodo.objects.create" not in source
        assert "Delegado.objects.create" not in source
        assert "PerfilIngeniero.objects.create" not in source
        assert "PerfilIngeniero.objects.get_or_create" not in source

    def test_no_toca_liquidaciones_ni_inspectores(self):
        source = _source()
        assert "LiquidacionGeneral.objects" not in source
        assert "LiquidacionInspector" not in source

    def test_reutiliza_el_mapeo_de_la_curacion_existente(self):
        source = _source()
        assert "from .curar_rh_desde_excel import" in source
        assert "ESPECIALIDAD_ALIAS" in source
