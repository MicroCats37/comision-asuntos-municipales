import csv
from pathlib import Path

from modules.liquidaciones.management.commands.legacy_edif.columns import (
    COL_FECHAPRES1,
    COL_FECHAPRES2,
    COL_FECHAPRES3,
    COL_FECHAPRES4,
    COL_FECHAREVI1,
    COL_FECHAREVI2,
    COL_FECHAREVI3,
    COL_FECHAREVI4,
    COL_MES1,
    COL_MES2,
    COL_MES3,
    COL_MES4,
    COL_NROORDEN1,
    COL_NROORDEN2,
    COL_NROORDEN3,
    COL_NROORDEN4,
    COL_PERIODO1,
    COL_PERIODO2,
    COL_PERIODO3,
    COL_PERIODO4,
    COL_TDNI,
    COL_TFONO,
    COL_TPERSONA,
)


def test_column_constants_match_edif_csv_header():
    csv_path = (
        Path(__file__).resolve().parents[4]
        / "core_application"
        / "seeds"
        / "historico"
        / "EDIF_ALL.csv"
    )
    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        header = next(csv.reader(source, delimiter=";"))

    expected_columns = {
        COL_TDNI: "TDNI",
        COL_TFONO: "TFONO",
        COL_TPERSONA: "TPERSONA",
        COL_FECHAPRES1: "FECHAPRES1",
        COL_FECHAPRES2: "FECHAPRES2",
        COL_FECHAPRES3: "FECHAPRES3",
        COL_FECHAPRES4: "FECHAPRES4",
        COL_FECHAREVI1: "FECHAREVI1",
        COL_FECHAREVI2: "FECHAREVI2",
        COL_FECHAREVI3: "FECHAREVI3",
        COL_FECHAREVI4: "FECHAREVI4",
        COL_NROORDEN1: "NROORDEN1",
        COL_NROORDEN2: "NROORDEN2",
        COL_NROORDEN3: "NROORDEN3",
        COL_NROORDEN4: "NROORDEN4",
        COL_PERIODO1: "PERIODO1",
        COL_PERIODO2: "PERIODO2",
        COL_PERIODO3: "PERIODO3",
        COL_PERIODO4: "PERIODO4",
        COL_MES1: "MES1",
        COL_MES2: "MES2",
        COL_MES3: "MES3",
        COL_MES4: "MES4",
    }

    assert {index: header[index] for index in expected_columns} == expected_columns
