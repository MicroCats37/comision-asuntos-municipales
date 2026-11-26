"""Remove the non-legacy IO inspector and contact links contaminated by legacy collisions.

Background
----------
On 2026-11-23 the legacy IO importer resolved existing liquidaciones by
``numero`` without restricting the lookup to ``liquidacion__legacy=True``. When
the current (non-legacy) IO happened to own the lower UUID, ``.first()``
returned the current liquidacion and the importer attached legacy data to it:

* 17 ``LiquidacionInspector`` links (IO 16, 18, 23, 28, 37, 38, 56, 60, 64,
  65, 69, 71, 73, 80, 83, 84, 87).
* 29 ``LiquidacionContacto`` links plus the 29 duplicated ``entidades_contacto``
  records they point to (IO 8, 16, 21, 22, 23, 24, 26, 28, 29, 34, 37, 38, 49,
  50, 56, 59, 60, 61, 64, 68, 69, 70, 71, 73, 80, 83, 84, 86, 87).

The manifest embedded below is closed: every UUID and fingerprint was
reconstructed from the pre-contamination dump and the post-contamination
database. The command never opens the dump at runtime and never resolves a row
by IO number or CIP - the only key is the UUID of the link, and it is removed
only when the whole identity of the row still matches the manifest.

Guarantees
----------
* Dry-run by default; ``--apply`` is required to mutate and ``--csv-output`` is
  mandatory (one CSV row per manifest item, 46 rows).
* Legacy liquidaciones are never touched.
* Any drift (parent mismatch, identity mismatch, timestamp drift, missing
  counterpart, extra references) is reported as ``REVIEW_*`` and mutates
  nothing.
* A duplicated ``entidades_contacto`` is deleted only when its contaminated
  link is its only reference.
* ``LiquidacionComprobante`` is out of scope: this module never imports it and
  never queries it.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from modules.entidades.domain.models.contacto import Contacto
from modules.liquidaciones.domain.models.inspector import LiquidacionInspector
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionContacto,
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)

# Window of the contaminating import run (2026-11-23 07:42:57Z -> 07:43:01Z).
# A link created outside this window is never part of the contamination.
CONTAMINATION_WINDOW_START = datetime(2026, 11, 23, 7, 42, 57, tzinfo=timezone.utc)
CONTAMINATION_WINDOW_END = datetime(2026, 11, 23, 7, 43, 1, tzinfo=timezone.utc)

# Statuses
STATUS_DELETE_LINK = "DELETE_LINK"
STATUS_DELETE_LINK_AND_CONTACTO = "DELETE_LINK_AND_CONTACTO_ENTITY"
STATUS_DELETE_ORPHAN_CONTACTO = "DELETE_ORPHAN_CONTACTO_ENTITY"
STATUS_ALREADY_CLEAN = "ALREADY_CLEAN"
STATUS_REVIEW_PARENT_MISMATCH = "REVIEW_PARENT_MISMATCH"
STATUS_REVIEW_PARENT_LEGACY = "REVIEW_PARENT_LEGACY"
STATUS_REVIEW_STATE_DRIFT = "REVIEW_STATE_DRIFT"
STATUS_REVIEW_REFERENCED_CONTACTO = "REVIEW_REFERENCED_CONTACTO"
STATUS_REVIEW_CONTACTO_MISSING = "REVIEW_CONTACTO_MISSING"
STATUS_REVIEW_LEGITIMATE_LINK_MISSING = "REVIEW_LEGITIMATE_LINK_MISSING"
STATUS_REVIEW_LEGACY_COUNTERPART_MISSING = "REVIEW_LEGACY_COUNTERPART_MISSING"

DELETE_STATUSES = frozenset(
    {
        STATUS_DELETE_LINK,
        STATUS_DELETE_LINK_AND_CONTACTO,
        STATUS_DELETE_ORPHAN_CONTACTO,
    }
)

CSV_FIELDS = [
    "tipo",
    "numero",
    "liquidacion_id",
    "visitas_id",
    "link_contaminado_id",
    "inspector_id",
    "inspector_operacion_id",
    "especialidad_revision_id",
    "cip",
    "contacto_id",
    "legit_link_id",
    "legit_inspector_id",
    "legit_contacto_id",
    "legacy_link_id",
    "legacy_liquidacion_id",
    "created_at_esperado",
    "status",
    "accion",
    "evidencia",
]


@dataclass(frozen=True)
class InspectorCollision:
    """A ``LiquidacionInspector`` link attached to a current IO by the legacy run."""

    numero: int
    liquidacion_id: str
    visitas_id: str
    link_id: str
    inspector_id: str
    inspector_operacion_id: str
    especialidad_revision_id: str
    legit_link_id: str
    legit_inspector_id: str
    legacy_link_id: str
    legacy_liquidacion_id: str
    legacy_visitas_id: str
    cip: str
    created_at: datetime


@dataclass(frozen=True)
class ContactoCollision:
    """A ``LiquidacionContacto`` link attached to a current IO by the legacy run."""

    numero: int
    liquidacion_id: str
    link_id: str
    contacto_id: str
    legit_contacto_id: str | None
    legacy_link_id: str
    legacy_contacto_id: str
    legacy_liquidacion_id: str
    nombres: str
    apellidos: str
    telefono: str
    created_at: datetime
    contacto_created_at: datetime

    @property
    def nombre_contacto(self) -> str:
        return " ".join(part for part in (self.nombres, self.apellidos) if part)


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _i(
    numero: int,
    liquidacion_id: str,
    visitas_id: str,
    link_id: str,
    inspector_id: str,
    inspector_operacion_id: str,
    especialidad_revision_id: str,
    legit_link_id: str,
    legit_inspector_id: str,
    legacy_link_id: str,
    legacy_liquidacion_id: str,
    legacy_visitas_id: str,
    cip: str,
    created_at: str,
) -> InspectorCollision:
    return InspectorCollision(
        numero=numero,
        liquidacion_id=liquidacion_id,
        visitas_id=visitas_id,
        link_id=link_id,
        inspector_id=inspector_id,
        inspector_operacion_id=inspector_operacion_id,
        especialidad_revision_id=especialidad_revision_id,
        legit_link_id=legit_link_id,
        legit_inspector_id=legit_inspector_id,
        legacy_link_id=legacy_link_id,
        legacy_liquidacion_id=legacy_liquidacion_id,
        legacy_visitas_id=legacy_visitas_id,
        cip=cip,
        created_at=_ts(created_at),
    )


def _c(
    numero: int,
    liquidacion_id: str,
    link_id: str,
    contacto_id: str,
    legit_contacto_id: str | None,
    legacy_link_id: str,
    legacy_contacto_id: str,
    legacy_liquidacion_id: str,
    nombres: str,
    apellidos: str,
    telefono: str,
    created_at: str,
    contacto_created_at: str,
) -> ContactoCollision:
    return ContactoCollision(
        numero=numero,
        liquidacion_id=liquidacion_id,
        link_id=link_id,
        contacto_id=contacto_id,
        legit_contacto_id=None if legit_contacto_id == "None" else legit_contacto_id,
        legacy_link_id=legacy_link_id,
        legacy_contacto_id=legacy_contacto_id,
        legacy_liquidacion_id=legacy_liquidacion_id,
        nombres=nombres,
        apellidos=apellidos,
        telefono=telefono,
        created_at=_ts(created_at),
        contacto_created_at=_ts(contacto_created_at),
    )


INSPECTOR_COLLISIONS = (
    _i(
        16,
        "ef5d75a8-2801-4257-9512-d3769576f17e",
        "feb139c1-4d06-48b9-93d1-72a7c2511062",
        "ed49153b-f78c-458d-8145-0af374044628",
        "d62ead07-2b99-46c0-8165-894538584871",
        "fcc3f3d7-2ac2-4ee5-ac29-0ba190dbae8b",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "a9c13ddb-b63f-4308-a6ec-3568051fb445",
        "2e0f78d8-c8a3-4761-856b-0280937ad6f4",
        "2b3a381e-6b5d-4ec8-84a5-7ee954b8d604",
        "1f9eab0e-9028-4609-9398-0f299485ad24",
        "069ceeb8-4a71-4ede-a86b-8d5923b08ba8",
        "019232",
        "2026-11-23T07:42:58.093707+00:00",
    ),
    _i(
        18,
        "4f89547d-27d4-4116-a525-8d8d98f34c9e",
        "2357e09d-4546-45d9-8c87-d49f30c5fa50",
        "25882098-3da9-4c78-b99b-1bde63e7fc48",
        "3bed315c-0a53-474b-ab1b-128180cb64e8",
        "e33fd386-9950-4df7-905a-edfd5f24d80b",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "13b61264-a4dc-4058-9656-2fe2560d4992",
        "921f7a73-2f12-49e0-9e09-be88954d357e",
        "cfc9d81c-e4d7-4249-8ccf-7af0d315417f",
        "4a72e091-1c2a-458e-8799-f03cb7a2e687",
        "3def5344-2be1-4fc9-a454-cee8d999d0f9",
        "002570",
        "2026-11-23T07:42:58.171895+00:00",
    ),
    _i(
        23,
        "74918b02-31b8-43ee-b7b6-19cf6c966a0f",
        "a4de616b-652f-4799-adb6-f9b03a3c36d7",
        "75e0f141-432b-44f3-983c-ece6ce10e755",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "dc06bfb8-7bcc-4f84-a6ba-447edf4c2d57",
        "5e0eb46c-37fc-4cb2-811f-3f9038472bf8",
        "df1670a2-2733-4be5-821c-f1afc912e27f",
        "8811ddaa-318d-4525-ba4f-c0e4d9f6c7aa",
        "6e97062f-b7eb-4e17-adda-63d9a555a690",
        "011470",
        "2026-11-23T07:42:58.360707+00:00",
    ),
    _i(
        28,
        "f5be0d30-9a36-42af-9ec6-2399237a0b9a",
        "8c421317-6306-458a-93d3-f7d93d553b71",
        "2fae1c36-8b63-43b5-b16e-5ad0ed38f3bb",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "93f9c6cb-fc1c-486f-bce9-efc5867de117",
        "90d9b3a0-304a-4db2-a91c-cb1be3eb22f2",
        "8fabac7e-833d-45c9-bd3a-6157d8fa932c",
        "6fa5f4cd-724b-47d3-83ca-d6bf013d0218",
        "861fac26-c938-43de-b8b0-52ca3c3bddb5",
        "011470",
        "2026-11-23T07:42:58.567720+00:00",
    ),
    _i(
        37,
        "9aea4249-12b8-49ac-83b4-81e0486ba543",
        "788aa221-87eb-4b6b-9fbb-e1a7d287841f",
        "31484c0a-d638-4663-906a-648d700a8c27",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "fefdc7da-76d7-49f2-b36d-3df25f3af56d",
        "477c1365-ee2f-4667-b825-4bb8495765ec",
        "0186fe46-344c-42d1-a768-c500557511f0",
        "830921bd-dfc5-4ab3-bbd9-3da0c95e027b",
        "606c7ab9-3e13-4dff-b48a-f355cc66bdc0",
        "011470",
        "2026-11-23T07:42:58.923284+00:00",
    ),
    _i(
        38,
        "a190acf7-a374-4a22-a16f-5074f61fa5c3",
        "40a771c1-d981-43c7-9c97-e50ae4615453",
        "da80e44f-78b0-400a-9b60-1755d50f7494",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "eb2a26d3-4270-431e-be9e-ceb91247f689",
        "c36db293-3e8b-4945-8ffb-e70d1cf0f823",
        "e8bf7b5c-b091-4cfc-af29-65a4b71115d7",
        "d0dd111b-870c-4b49-933f-3a5368e09cf3",
        "c97edf57-9b3b-4820-9270-d6fa614c3252",
        "011470",
        "2026-11-23T07:42:58.980879+00:00",
    ),
    _i(
        56,
        "5737ef11-58c8-48f2-b4f9-6c281581f822",
        "8565ceb0-7f94-43fd-ae56-1fec263a289c",
        "a3b828d3-b4c4-485c-a010-467adcacc5bc",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "ad6c88db-cb1a-40de-b007-f94043914d87",
        "d827a23f-db65-4c60-ad98-a6ded6c075eb",
        "75ebf91c-0a23-4ec5-ad4e-62ab3ecc8f16",
        "307f1e3e-98c8-4db7-98b7-303e6ba95447",
        "8da1b66a-1e46-4a4a-8acf-081b9388a064",
        "011470",
        "2026-11-23T07:42:59.608459+00:00",
    ),
    _i(
        60,
        "61aaf739-c716-465d-a044-3cba9167e084",
        "4450e93f-a1bf-4d2a-90f3-118fbc6227e6",
        "65566826-1562-4a61-9f64-799813d0a4a8",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "4d55db95-9bc8-4a32-a59f-3ab37827d43c",
        "8047bf37-88b7-4c34-89df-a081d35ceb98",
        "bf9329af-fb2b-4680-845e-b7cadc274331",
        "d956e1a2-5379-43b5-855f-80825e1f06ff",
        "bc56ce24-70d4-4f63-bf18-47f548e0da5c",
        "011470",
        "2026-11-23T07:42:59.734043+00:00",
    ),
    _i(
        64,
        "55dc858b-8d46-4762-9ca3-b7904913b92c",
        "46e319fc-edeb-456e-99e9-46ba25bd1169",
        "4cc9b219-1b0b-4a7d-8b29-78aae931317e",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "3cea79fd-7959-43a9-9061-8ac46ba69e15",
        "62d63e65-d571-45fa-a51f-78710b509aad",
        "4f481b60-72bb-4397-a1c9-874e68c61ef5",
        "adbe83de-daa2-4637-ac6c-41378678ee35",
        "36869990-ccb5-476c-8ac9-be07c95a20fd",
        "011470",
        "2026-11-23T07:42:59.906738+00:00",
    ),
    _i(
        65,
        "e6229305-d7e4-4070-afca-3c3318c9e7ee",
        "065e80a3-bf41-423d-a55a-84316ca878cb",
        "101bb71b-0c14-4269-b5a6-4462ebfad1a3",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "2bd126dc-c083-49b7-bcd1-9648bf145b2d",
        "2e0f78d8-c8a3-4761-856b-0280937ad6f4",
        "e3ab81d6-43b4-4d72-8e20-c7aac209ebac",
        "9d18738d-bb61-4257-ab7f-5068c885376d",
        "2f24a640-2fb2-46ab-9dd2-c6794d1ccd0d",
        "011470",
        "2026-11-23T07:42:59.959994+00:00",
    ),
    _i(
        69,
        "5ee7a203-75df-4d59-af99-73473fed520a",
        "39b1563d-a5ab-4133-9bea-fd684bd5edd1",
        "c326fce4-dcc5-4bff-8907-44b6158be603",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "9841945f-2a6e-4155-b4a8-42269df7fec9",
        "562b1d58-eafb-4184-916a-a59ac179ab63",
        "8315d9ec-d8fa-4541-8848-142aad72d091",
        "863653ff-6106-4c01-ac45-f4ac298c0699",
        "a4f3f4a6-491b-41c6-a204-826ac8573fca",
        "011470",
        "2026-11-23T07:43:00.118674+00:00",
    ),
    _i(
        71,
        "cea9966f-a6e4-4b92-aea8-afb19cf554f7",
        "4b286251-b4e2-4a75-a30c-c2cee6104dc8",
        "6649f67f-d0c5-4311-a3ff-a437d38dd66c",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "e8082bed-676c-4e8f-94cf-b9c7f18ffde0",
        "47134732-e76e-4483-8a46-df0d9cceb774",
        "dd268a44-5ce7-42d9-bc8d-da61bf17c11e",
        "d6ff1431-f25c-4c0a-b36f-96d34dea9e0c",
        "dace762b-cf9f-4c7e-a1c1-5c1829db4008",
        "011470",
        "2026-11-23T07:43:00.229659+00:00",
    ),
    _i(
        73,
        "60b1b5c4-ecdb-49e2-9980-83f262ddf46a",
        "a04f116d-f5c8-425a-82a7-bd57cc15ede0",
        "ffb2afce-48f5-4cf6-964c-4ce9996538ff",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "4fff98c7-e62f-47c8-be50-9717b6ec8f9b",
        "dd54d3d4-57d8-4b38-95c7-58d981555d14",
        "d8b22a36-5083-4e63-a8fe-d49075483067",
        "0aeb910e-d988-4997-b44d-2a420d92dff8",
        "f5f5cb2f-c151-4775-9967-b3a161152277",
        "011470",
        "2026-11-23T07:43:00.327018+00:00",
    ),
    _i(
        80,
        "935e2161-275d-4073-b089-ba5358758c45",
        "ff350a48-6e2d-4f52-9fc1-3427ad603626",
        "1927c533-3b1b-47bf-8a49-4f6869dc04e2",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "84b6efdc-fbb7-4df7-b8fc-03c849333151",
        "477c1365-ee2f-4667-b825-4bb8495765ec",
        "41cea280-1150-469c-8b16-9a6998072f88",
        "bc30462e-0b91-45e1-af6f-9d02d3856cba",
        "1cf5da11-54a5-423e-ac88-98bd15d4fdee",
        "011470",
        "2026-11-23T07:43:00.611722+00:00",
    ),
    _i(
        83,
        "6840f11b-7654-4ce1-a8a9-3193c48ff076",
        "5cbe19f2-48c3-477d-a1de-48e0da94c6f6",
        "2aaccae2-9cf9-4958-81b6-d54e8ada8765",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "fc3d67bc-6345-4648-86f8-26f7ae8d031f",
        "9e98b7f6-cf71-4b78-b5dc-fccadf4344e4",
        "a0b4ac3c-67f2-4a09-a0b5-185e08944398",
        "9409a0b9-8744-44b1-83a2-11ec3e0570c3",
        "9bd297a5-39cd-4876-8c0d-ebad7db6de74",
        "011470",
        "2026-11-23T07:43:00.730064+00:00",
    ),
    _i(
        84,
        "2549cca9-37fa-404d-9385-c51ee865e95d",
        "fbb9f77c-7930-4bb7-854b-ac1ce70e3458",
        "41563222-d9d3-4ae2-8269-a61faf8f5813",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "f222d818-1c56-4ba9-b11f-c127b7c24b5d",
        "2e0f78d8-c8a3-4761-856b-0280937ad6f4",
        "eda63090-8723-4b69-8631-9089f0c25e5f",
        "997c3a9d-19dc-40be-90ec-1d16161b351a",
        "74514fc9-05c9-4cb0-83e4-7141f6c26553",
        "011470",
        "2026-11-23T07:43:00.807586+00:00",
    ),
    _i(
        87,
        "b36b7cc4-0c90-43ec-9831-2586d59fbc40",
        "4c992608-7c4f-442f-bfec-37cbe07e71c5",
        "ee012d47-c404-46cd-b632-89a39368a29c",
        "f7a67ae2-7123-437e-bda3-1b2ac57d71f7",
        "42795fae-4537-4398-a54b-0c8b52babcd2",
        "e3ac3edc-e90f-404c-a932-5c771aa0cd21",
        "3b5e352b-a8ba-46d1-adae-a5475d2f6f41",
        "f0f4ddba-a5fa-42c2-bb0a-58a923d1d7ec",
        "bed682f1-1333-4537-9b0b-d80d08ef1aa3",
        "00caa192-3d2c-403f-89d9-9bd9f21e9607",
        "98f0e121-951c-4e4e-a387-c3967ccdd3b6",
        "011470",
        "2026-11-23T07:43:00.909707+00:00",
    ),
)

CONTACTO_COLLISIONS = (
    _c(
        8,
        "61232fd7-f8ef-4551-9104-95235ff3a49f",
        "5622f262-9fa1-4194-b4f0-1f01e78e8997",
        "2030dd37-62e1-4d96-8ab6-fecd4cc97996",
        "5b42bcb5-0f09-48d8-bf85-5289e3909a87",
        "206e4b12-cd26-4b97-836e-4e0a35290b59",
        "f348a85a-f3a7-4430-b77d-c0fc353321c0",
        "2199fc51-2b71-47c4-b182-5a88c89b6e21",
        "NATALIA",
        "DE FARIAS",
        "999376766",
        "2026-11-23T07:42:57.788060+00:00",
        "2026-11-23T07:42:57.767590+00:00",
    ),
    _c(
        16,
        "ef5d75a8-2801-4257-9512-d3769576f17e",
        "f47887d6-2762-4645-81a2-56b8c32f8eeb",
        "e1d5122f-cc05-45a6-b5ef-1f1fdda25097",
        "3329fa05-e8ee-4ae3-af3f-0d6bfe15126a",
        "f889d549-ff93-4f01-b4cc-64403675df02",
        "65891e06-8ae8-4ec8-b49c-748d6aafb356",
        "1f9eab0e-9028-4609-9398-0f299485ad24",
        "MIGUEL",
        "SANTIBAÑEZ",
        "997411609",
        "2026-11-23T07:42:58.140107+00:00",
        "2026-11-23T07:42:58.136107+00:00",
    ),
    _c(
        21,
        "b90fb6e1-4f78-4d65-810a-c217ac7f0ddd",
        "5b5ed430-8162-4544-bbc5-e6b70d82b3ac",
        "b5250d35-865e-4bc3-a16a-64e103e4b837",
        "1ebc1fdf-8642-4ba1-be74-e3a2016575ad",
        "2f0d6086-a61c-49f1-8731-5dadd8cc2534",
        "a3228719-2837-4eb3-bd08-2a483713dc09",
        "95533529-adb3-41d7-b3a5-139aaedfdd8a",
        "ALBERTO",
        "TRINIDAD CASTRO",
        "995091207",
        "2026-11-23T07:42:58.304205+00:00",
        "2026-11-23T07:42:58.296296+00:00",
    ),
    _c(
        22,
        "7fe1ffc9-402b-446c-a12b-360a23b9e5c7",
        "db1301a5-3393-451d-aa57-d60a8584a547",
        "232372c5-c979-4cef-8085-b72a1768690d",
        "84418cfe-8868-4b3c-bae9-aec621b76237",
        "35a0183e-73e5-4b6f-b89d-f719292462fa",
        "fee9a4a9-c63e-41e8-b836-6fbe33640497",
        "46fe754d-8988-4ca1-8cd4-fe8e7a878c75",
        "JOSE",
        "MORI",
        "981045768",
        "2026-11-23T07:42:58.334707+00:00",
        "2026-11-23T07:42:58.330201+00:00",
    ),
    _c(
        23,
        "74918b02-31b8-43ee-b7b6-19cf6c966a0f",
        "990c8515-a045-4375-9cbe-144a7cdd3daf",
        "ab6176d0-ad5a-4cc1-9b35-eb38853b4350",
        "7287cfc9-c3c5-4463-8ee6-66148c2919d3",
        "2e73c188-8028-4340-9c3e-ec43c47933b9",
        "ef371e2f-192a-4278-8691-18ff6c2e1f19",
        "8811ddaa-318d-4525-ba4f-c0e4d9f6c7aa",
        "OSCAR JOSE",
        "LOZANO IBERICO",
        "999693272",
        "2026-11-23T07:42:58.384945+00:00",
        "2026-11-23T07:42:58.381712+00:00",
    ),
    _c(
        24,
        "9eade5d7-42b5-4dff-8240-b546eb8281ca",
        "b040498c-e477-4083-b02d-59de145124d6",
        "1601a1fc-872e-4c76-b14e-b5c47f72f84f",
        "c8fc60fd-45fa-49a1-a812-0f9ca2902c09",
        "eab96216-4b8d-4a2b-ba36-bc99464b3cf7",
        "ce786c61-bb4c-45dc-9f6f-6050190a62bd",
        "3cba0de8-6379-4ae2-9b5b-56b5fcf8c2a5",
        "RAPHAEL PASCUAL",
        "/ 2014 SE LIQUIDO 01 VIS EL 09.05.2014 AL ING. FERREYRA CAYO",
        "993073335",
        "2026-11-23T07:42:58.415196+00:00",
        "2026-11-23T07:42:58.410191+00:00",
    ),
    _c(
        26,
        "f6650426-d87e-4219-a1da-cb8596760fb6",
        "bb9d96e1-4355-401f-810f-b52770f3426e",
        "0a3a4922-b8eb-41b8-a5b2-d3d7b337882d",
        "055201b3-55f7-42b1-af9f-0f60dc94d747",
        "d25ecb6e-210b-4765-a03f-e7108289bc11",
        "c038d8a7-6245-455e-9d9a-6fb9d596521d",
        "3395ba6e-ffe4-4b19-ad35-3455dd01e45f",
        "WILFREDO",
        "BAZAN FLORES",
        "993546082",
        "2026-11-23T07:42:58.499098+00:00",
        "2026-11-23T07:42:58.493094+00:00",
    ),
    _c(
        28,
        "f5be0d30-9a36-42af-9ec6-2399237a0b9a",
        "6af9ae97-15d5-482d-995b-7997079e39d3",
        "3ee7ca96-101d-403d-8fe1-100000e8ab47",
        "171bf7a9-9bc6-4cf5-a235-bc489344c846",
        "0d0685fe-4ce5-4f06-ab9b-ffe72b2452e6",
        "b86d619a-df95-4e61-a072-e76be9b971dd",
        "6fa5f4cd-724b-47d3-83ca-d6bf013d0218",
        "NICOLAS",
        "SUAREZ LOPEZ",
        "4706272",
        "2026-11-23T07:42:58.596384+00:00",
        "2026-11-23T07:42:58.590383+00:00",
    ),
    _c(
        29,
        "ae9456f3-49eb-450f-83a0-6aa004a9bfe8",
        "5739b165-9cd0-487b-b2bc-8b43cbb5d3ba",
        "5c1bbfb3-361d-4bf2-8d34-6162b6f983f4",
        "7097dcff-ff69-4748-bd0d-5d86e18edfbc",
        "8339941b-bd0d-46ce-8ed3-f1289812aa79",
        "a11dda3e-1e2a-409c-bc0f-f014b8652dd2",
        "1605bfde-49ec-41db-9f39-ada3fd6255dd",
        "HUMBERTO",
        "SALINAS ESPINOZA",
        "999113125",
        "2026-11-23T07:42:58.630382+00:00",
        "2026-11-23T07:42:58.625381+00:00",
    ),
    _c(
        34,
        "f8347d53-2cb5-4f26-9bd3-863e972b53ba",
        "a8fd5568-5507-4ed2-bd1e-572132dbbe1c",
        "b8a40e0f-56f8-41f2-99d0-fa28331fa705",
        "80c280fa-81f8-49fc-b1c1-b1f0ebea547d",
        "5ab65d48-2339-4fe9-a8ec-86c217a11b04",
        "d5e1d571-964a-4c42-afd3-ebaf9888c96a",
        "057d74bd-78fc-4f18-be54-d685d10f1e63",
        "LUIS ALBERTO",
        "ASATO TAYRA",
        "993382868",
        "2026-11-23T07:42:58.847054+00:00",
        "2026-11-23T07:42:58.841053+00:00",
    ),
    _c(
        37,
        "9aea4249-12b8-49ac-83b4-81e0486ba543",
        "2e24fb64-5ed8-4f31-b687-97f0c19287fd",
        "141bfdd6-a5b4-4b0e-a721-6061ef36216a",
        "9edf88f1-4b55-4e71-8d63-2b59b7efdeb3",
        "d37eb642-4299-4d9a-a7e7-c5390ac7d7d9",
        "3d8fc4af-f2ae-4e1a-8037-ad10e0e9fe4f",
        "830921bd-dfc5-4ab3-bbd9-3da0c95e027b",
        "FORTUNATO",
        "GUEVARA GUEVARA",
        "996882410",
        "2026-11-23T07:42:58.950879+00:00",
        "2026-11-23T07:42:58.943313+00:00",
    ),
    _c(
        38,
        "a190acf7-a374-4a22-a16f-5074f61fa5c3",
        "6ff468c2-f30c-46a9-a79b-d7f87a327b39",
        "414d035a-1f2b-4a57-b2db-32e3ae122096",
        None,
        "fcdac339-7778-4cff-87b8-f8247e93dfef",
        "8cf03098-af55-4381-94a4-01bdb5da23d9",
        "d0dd111b-870c-4b49-933f-3a5368e09cf3",
        "RUPERTINA EDILBERTA",
        "CORTEZ HUAMANI",
        "5223823",
        "2026-11-23T07:42:59.016290+00:00",
        "2026-11-23T07:42:59.009914+00:00",
    ),
    _c(
        49,
        "59872962-0b38-4b58-b399-0c9fb6cf794c",
        "6dcb1110-ea96-4870-8cfa-c6620a67ec98",
        "b404da1c-506c-43b6-ba9a-615c9a8b7e0b",
        "3d36f521-87c3-499e-89ba-269986ff0c24",
        "ba104809-a4ba-4235-8680-785915502789",
        "3b1dfa3b-97ee-4041-acdf-ec20f3c98f98",
        "5b2b6f7a-6915-4a1d-967c-70f72840babc",
        "RUDY",
        "PONCE",
        "3451884",
        "2026-11-23T07:42:59.381277+00:00",
        "2026-11-23T07:42:59.376863+00:00",
    ),
    _c(
        50,
        "dff3764b-fd4f-481b-9c5f-6c2b38a25197",
        "485c2722-b9dc-499e-b684-fff7268eb247",
        "07df811b-4f2f-4f3b-b586-0c34662faad6",
        "1f0f638f-da10-4709-9fc6-ea502747d440",
        "664ceaee-a72c-47fb-8e20-ca592a17edf9",
        "e59debcc-1404-4ea8-90bd-a53402ef7d72",
        "5cabc73e-7dbd-4e68-85d8-570b119d7cde",
        "HECTOR",
        "TAYCO",
        "4424212",
        "2026-11-23T07:42:59.410421+00:00",
        "2026-11-23T07:42:59.407421+00:00",
    ),
    _c(
        56,
        "5737ef11-58c8-48f2-b4f9-6c281581f822",
        "872a2ec6-aa26-47b4-ad04-cc87cba05050",
        "14f3700b-c0c3-427a-83fd-ba2c61ac87e1",
        "07649833-0f43-4b58-91aa-c558b708328e",
        "a24f3684-d0db-44e9-bdd9-1a8924e91791",
        "b995dad6-add5-41e5-aac5-350991edddf4",
        "307f1e3e-98c8-4db7-98b7-303e6ba95447",
        "CARLOS",
        "CASTRO RODRIGUEZ",
        "5390389",
        "2026-11-23T07:42:59.638083+00:00",
        "2026-11-23T07:42:59.634081+00:00",
    ),
    _c(
        59,
        "44b5f54e-0cdb-4888-8200-664a76f300f9",
        "d2790114-3894-468a-bafb-485693fb9f7e",
        "af92ca6c-97f6-4f05-a686-3c08c54276b1",
        "145886dc-53d3-4447-bb40-15a150e2ff6c",
        "a307e30e-83fa-43c2-9366-f4d476e1228e",
        "f29942d0-d462-48a3-9b78-7efa00ea654a",
        "afd00af5-a6b7-409b-88a0-c347aa487211",
        "GABRIEL",
        "GAMARRA SANCHEZ",
        "4460836",
        "2026-11-23T07:42:59.705297+00:00",
        "2026-11-23T07:42:59.700159+00:00",
    ),
    _c(
        60,
        "61aaf739-c716-465d-a044-3cba9167e084",
        "aaf18fe1-823e-4551-b119-94485c3822ee",
        "f2cc4335-8282-4583-b655-912a7de7590c",
        "72db77bf-55f3-4157-9025-457e97604d81",
        "8b7634d5-cfc1-41bc-a187-69e0a85bf282",
        "f05248bf-8d27-4c6e-ad25-fd1214afd67a",
        "d956e1a2-5379-43b5-855f-80825e1f06ff",
        "JULIO",
        "PINO ROMERO",
        "988350858",
        "2026-11-23T07:42:59.763999+00:00",
        "2026-11-23T07:42:59.759001+00:00",
    ),
    _c(
        61,
        "deb3a149-d135-49bd-b361-da16ad611174",
        "fc831f0e-6512-415e-8a5d-2e307dd75147",
        "77758511-575c-496e-922c-cf1c3454fba1",
        "08bcb2dd-1db8-4fbd-b14a-781667da3275",
        "f7fd4949-8553-4652-9346-be3bb5e4c65e",
        "f1c41207-527c-4c97-aae7-b40bf17d40d4",
        "b56b0239-85e1-4e4f-a29f-2335ce77a081",
        "SANTOS ERNESTO",
        "URQUIZO M.",
        "2765940",
        "2026-11-23T07:42:59.793997+00:00",
        "2026-11-23T07:42:59.789004+00:00",
    ),
    _c(
        64,
        "55dc858b-8d46-4762-9ca3-b7904913b92c",
        "eb2fd136-a3e7-4444-80a4-c28a637f0f14",
        "0e6aaa56-733a-4fcc-bb1a-fbba667f9a2a",
        "2d3be8fa-9ad5-47e9-bb3a-10856dc3376a",
        "63921005-9d08-4637-96b0-bc929647ecee",
        "f0d8d78b-3773-43b4-aecb-4233775dc8a2",
        "adbe83de-daa2-4637-ac6c-41378678ee35",
        "SEGUNDO",
        "JULON JULON",
        "4243373",
        "2026-11-23T07:42:59.932434+00:00",
        "2026-11-23T07:42:59.926837+00:00",
    ),
    _c(
        68,
        "66059e9b-ab9c-4a97-90db-77c9cfde4ede",
        "d6897a0b-3fc6-4d26-8f57-54d9260f2735",
        "e4af90f9-ba5d-43fb-a788-aff201f2e230",
        None,
        "756ebb63-f1d1-4c63-92cb-b7eabe1ed30a",
        "b99feb5b-c022-44ce-8c46-892667212e6d",
        "f02093cc-ccd7-4e36-9074-661ff60954ec",
        "ERNESTO",
        "CHANCAFE ESPINOZA",
        "998126246",
        "2026-11-23T07:43:00.087471+00:00",
        "2026-11-23T07:43:00.083474+00:00",
    ),
    _c(
        69,
        "5ee7a203-75df-4d59-af99-73473fed520a",
        "c8dfcd29-8571-4943-9aed-a89bb0d1fa9c",
        "1f55b4d8-7c47-4277-abc9-d9ebcd9ceea9",
        "7097dcff-ff69-4748-bd0d-5d86e18edfbc",
        "a4ac4ffe-bb4c-4834-8158-28508dd0ba09",
        "7c312188-990a-422b-acf5-02d976bfdad5",
        "863653ff-6106-4c01-ac45-f4ac298c0699",
        "MIGUEL",
        "ESPINOZA",
        "992847802",
        "2026-11-23T07:43:00.147673+00:00",
        "2026-11-23T07:43:00.143669+00:00",
    ),
    _c(
        70,
        "2f5b2abd-8304-43db-84cf-feff7e21b3cf",
        "43083e11-bb87-40ca-bc45-05b8d5508c4b",
        "4f06276d-c79a-42ea-a114-961caf74c6cb",
        "a46c6b5b-3073-4670-8a18-ba362dce4ea9",
        "1c41983b-8de6-4d96-a8bb-d3d0a7789303",
        "430da85d-332e-41ac-ac05-e07d5cd6b03c",
        "24b1ef49-7cf2-4c29-893c-4ff792500e81",
        "CESAR",
        "PASTOR YTURRIZAGA",
        "5336240",
        "2026-11-23T07:43:00.179661+00:00",
        "2026-11-23T07:43:00.174659+00:00",
    ),
    _c(
        71,
        "cea9966f-a6e4-4b92-aea8-afb19cf554f7",
        "fd1ba0ff-3cd1-493c-9e2c-3c67c472e423",
        "e781c681-86d5-45f3-a4f0-68e406539313",
        "95c71429-6005-4a5a-9626-6301e0cbc84b",
        "d805bfba-d2e8-4210-a545-5359f76db8e4",
        "bc82f55a-aa92-48be-8456-823d0e639c9c",
        "d6ff1431-f25c-4c0a-b36f-96d34dea9e0c",
        "MARCELO",
        "HERNANDEZ PAREDES",
        "996456164",
        "2026-11-23T07:43:00.265811+00:00",
        "2026-11-23T07:43:00.260809+00:00",
    ),
    _c(
        73,
        "60b1b5c4-ecdb-49e2-9980-83f262ddf46a",
        "b24b7884-7aca-4b27-8570-3e6ac8aded74",
        "35e8b49c-58ed-49e0-9300-f10345646a2e",
        "a74dcff4-5fff-4639-9f23-5a514bc10416",
        "6c268050-2884-47c6-8697-4ddcf740f56d",
        "87701cbb-bc35-4146-af76-a35574821f47",
        "0aeb910e-d988-4997-b44d-2a420d92dff8",
        "JOSE",
        "LUIS ORTEGA",
        "981562220",
        "2026-11-23T07:43:00.354544+00:00",
        "2026-11-23T07:43:00.350548+00:00",
    ),
    _c(
        80,
        "935e2161-275d-4073-b089-ba5358758c45",
        "5d07864f-bfe1-40ee-b911-eb66a4b6e534",
        "f2e6688e-17e8-4a86-a3a4-474c11a6c82e",
        "48291d12-ed99-4bf9-9a56-981d3ff4bff4",
        "ebc79db3-fb9c-4c17-9843-5ab4f709d18c",
        "2973b424-cb83-4327-9bb7-1a38e36ba9fc",
        "bc30462e-0b91-45e1-af6f-9d02d3856cba",
        "NERY",
        "CABRERA",
        "5283534",
        "2026-11-23T07:43:00.640883+00:00",
        "2026-11-23T07:43:00.638366+00:00",
    ),
    _c(
        83,
        "6840f11b-7654-4ce1-a8a9-3193c48ff076",
        "ba557b77-d570-43c5-be01-1aaa296117be",
        "36894cdb-3ef7-4863-a867-a9ec1e79c7cf",
        "8892ccf5-9f45-428c-b179-fd4f70f9ebfe",
        "66f69c1d-0d84-4594-9656-44ada02096db",
        "fd8d9e0e-b9e1-4331-86ce-5ef7ffc17d7e",
        "9409a0b9-8744-44b1-83a2-11ec3e0570c3",
        "SALVADOR",
        "PRADO",
        "5337001",
        "2026-11-23T07:43:00.770587+00:00",
        "2026-11-23T07:43:00.763588+00:00",
    ),
    _c(
        84,
        "2549cca9-37fa-404d-9385-c51ee865e95d",
        "0512a4a1-1d0c-472e-83e0-4de0ce0787e8",
        "3b3a0770-c948-4c00-b647-9dddb26b1fea",
        "4f64260a-b636-44d4-a6a4-497061a07920",
        "1ae542d1-9f60-4fdf-9817-4ea27465e310",
        "427f3649-24b1-4c82-b159-eae89371f9d5",
        "997c3a9d-19dc-40be-90ec-1d16161b351a",
        "WILFREDO",
        "NUÑEZ",
        "5230886",
        "2026-11-23T07:43:00.832099+00:00",
        "2026-11-23T07:43:00.829126+00:00",
    ),
    _c(
        86,
        "eb93bd0e-a44e-46d6-a4db-1987993ddf2e",
        "cefcb8a1-96c9-48ff-b993-ecd8a5dcb7ca",
        "85f78096-9310-48d8-9bb6-40b9f0f93293",
        "95c0af1f-1346-41d3-8303-6d50933293e0",
        "5bff23c8-df0c-4fc5-9a64-695d7c56862f",
        "2b08e867-0a85-46cd-adb2-d659efbdb419",
        "40dafe3f-c9a9-4ca1-970c-7caaa239ff57",
        "LUCERO",
        "MENDOZA",
        "5341200",
        "2026-11-23T07:43:00.889707+00:00",
        "2026-11-23T07:43:00.886708+00:00",
    ),
    _c(
        87,
        "b36b7cc4-0c90-43ec-9831-2586d59fbc40",
        "002ccf14-3406-40b9-9f31-ccd74b8be07d",
        "595c64c0-4d63-427e-b206-b76f96c3b07a",
        "469da2bc-8690-4ebc-a789-d5a68348f631",
        "6fe24410-ac68-4991-a0ed-7fb7c7c0db69",
        "de833971-be8e-404a-8728-0021c8b0fb1d",
        "00caa192-3d2c-403f-89d9-9bd9f21e9607",
        "SERGIO",
        "ALMEYDA MURRUGARRA",
        "994091360",
        "2026-11-23T07:43:00.936288+00:00",
        "2026-11-23T07:43:00.929290+00:00",
    ),
)


def _uuid(value) -> str:
    """Normalize a nullable UUID relation into a comparable string."""
    return "" if value is None else str(value)


def _contacto_references(contacto: Contacto) -> int:
    """Count every live reference to a contacto across the whole schema."""
    return (
        contacto.liquidaciones.count()
        + contacto.liquidaciones_contacto.count()
        + contacto.bancos.count()
        + contacto.municipalidades.count()
    )


def _plan_inspector(item: InspectorCollision) -> tuple[str, str, dict | None]:
    """Decide what to do with one contaminated inspector link."""
    link = LiquidacionInspector.objects.filter(id=item.link_id).first()
    if link is None:
        return (
            STATUS_ALREADY_CLEAN,
            "el link de inspector ya no existe",
            None,
        )

    if _uuid(link.liquidacion_id) != item.visitas_id:
        return (
            STATUS_REVIEW_PARENT_MISMATCH,
            f"el link apunta a liquidacion_por_categoriavisitas={link.liquidacion_id} "
            f"y el manifiesto espera {item.visitas_id}",
            None,
        )

    visitas = LiquidacionPorCategoriaVisitas.objects.filter(id=item.visitas_id).first()
    if visitas is None:
        return (
            STATUS_REVIEW_PARENT_MISMATCH,
            f"no existe la liquidacion por categoria de visitas {item.visitas_id}",
            None,
        )

    if _uuid(visitas.liquidacion_general_id) != item.liquidacion_id:
        return (
            STATUS_REVIEW_PARENT_MISMATCH,
            f"la liquidacion por categoria de visitas {item.visitas_id} apunta a "
            f"{visitas.liquidacion_general_id} y el manifiesto espera {item.liquidacion_id}",
            None,
        )

    liquidacion = LiquidacionGeneral.objects.filter(id=item.liquidacion_id).first()
    if liquidacion is None:
        return (
            STATUS_REVIEW_PARENT_MISMATCH,
            f"no existe la liquidacion {item.liquidacion_id}",
            None,
        )

    if liquidacion.legacy:
        return (
            STATUS_REVIEW_PARENT_LEGACY,
            "la liquidacion padre es legacy: el lado legacy nunca se toca",
            None,
        )

    if _uuid(link.inspector_id) != item.inspector_id:
        return (
            STATUS_REVIEW_STATE_DRIFT,
            f"inspector_id={link.inspector_id} difiere del manifiesto {item.inspector_id}",
            None,
        )

    if _uuid(link.inspector_operacion_id) != item.inspector_operacion_id:
        return (
            STATUS_REVIEW_STATE_DRIFT,
            f"inspector_operacion_id={link.inspector_operacion_id} difiere del "
            f"manifiesto {item.inspector_operacion_id}",
            None,
        )

    if _uuid(link.especialidad_revision_id) != item.especialidad_revision_id:
        return (
            STATUS_REVIEW_STATE_DRIFT,
            f"especialidad_revision_id={link.especialidad_revision_id} difiere del "
            f"manifiesto {item.especialidad_revision_id}",
            None,
        )

    if not (CONTAMINATION_WINDOW_START <= link.created_at <= CONTAMINATION_WINDOW_END):
        return (
            STATUS_REVIEW_STATE_DRIFT,
            f"created_at={link.created_at.isoformat()} esta fuera de la ventana "
            f"contaminante {CONTAMINATION_WINDOW_START.isoformat()}"
            f"/{CONTAMINATION_WINDOW_END.isoformat()}",
            None,
        )

    if link.created_at != item.created_at:
        return (
            STATUS_REVIEW_STATE_DRIFT,
            f"created_at={link.created_at.isoformat()} difiere de la huella del "
            f"manifiesto {item.created_at.isoformat()}",
            None,
        )

    if not (CONTAMINATION_WINDOW_START <= link.updated_at <= CONTAMINATION_WINDOW_END):
        return (
            STATUS_REVIEW_STATE_DRIFT,
            "el link fue modificado despues de la corrida contaminante "
            f"(updated_at={link.updated_at.isoformat()})",
            None,
        )

    legit = LiquidacionInspector.objects.filter(id=item.legit_link_id).first()
    if legit is None:
        return (
            STATUS_REVIEW_LEGITIMATE_LINK_MISSING,
            f"el link legitimo {item.legit_link_id} de la IO current ya no existe",
            None,
        )

    if (
        _uuid(legit.liquidacion_id) != item.visitas_id
        or _uuid(legit.inspector_id) != item.legit_inspector_id
    ):
        return (
            STATUS_REVIEW_STATE_DRIFT,
            f"el link legitimo {item.legit_link_id} no coincide con el manifiesto",
            None,
        )

    legacy_link = LiquidacionInspector.objects.filter(id=item.legacy_link_id).first()
    if legacy_link is None:
        return (
            STATUS_REVIEW_LEGACY_COUNTERPART_MISSING,
            f"el link legacy equivalente {item.legacy_link_id} ya no existe",
            None,
        )

    if _uuid(legacy_link.liquidacion_id) != item.legacy_visitas_id:
        return (
            STATUS_REVIEW_LEGACY_COUNTERPART_MISSING,
            f"el link legacy {item.legacy_link_id} apunta a "
            f"{legacy_link.liquidacion_id} y el manifiesto espera {item.legacy_visitas_id}",
            None,
        )

    return (
        STATUS_DELETE_LINK,
        "link de inspector duplicado creado por la colision de numeros legacy "
        "sobre una IO current",
        {"tipo": "INSPECTOR", "link_id": item.link_id},
    )


def _plan_contacto(item: ContactoCollision) -> tuple[str, str, dict | None]:
    """Decide what to do with one contaminated contact link."""
    link = LiquidacionContacto.objects.filter(id=item.link_id).first()
    if link is None:
        contacto = Contacto.objects.filter(id=item.contacto_id).first()
        if contacto is None:
            return (
                STATUS_ALREADY_CLEAN,
                "el link de contacto y la entidad duplicada ya no existen",
                None,
            )
        references = _contacto_references(contacto)
        if references:
            return (
                STATUS_ALREADY_CLEAN,
                f"el link ya no existe pero la entidad duplicada {item.contacto_id} "
                f"sigue referenciada ({references} referencias): se conserva",
                None,
            )
        return (
            STATUS_DELETE_ORPHAN_CONTACTO,
            f"el link ya no existe y la entidad duplicada {item.contacto_id} esta "
            "huerfana (0 referencias)",
            {"tipo": "CONTACTO_ORPHAN", "contacto_id": item.contacto_id},
        )

    if _uuid(link.liquidacion_id) != item.liquidacion_id:
        return (
            STATUS_REVIEW_PARENT_MISMATCH,
            f"el link apunta a liquidacion={link.liquidacion_id} y el manifiesto "
            f"espera {item.liquidacion_id}",
            None,
        )

    liquidacion = LiquidacionGeneral.objects.filter(id=item.liquidacion_id).first()
    if liquidacion is None:
        return (
            STATUS_REVIEW_PARENT_MISMATCH,
            f"no existe la liquidacion {item.liquidacion_id}",
            None,
        )

    if liquidacion.legacy:
        return (
            STATUS_REVIEW_PARENT_LEGACY,
            "la liquidacion padre es legacy: el lado legacy nunca se toca",
            None,
        )

    if _uuid(link.contacto_id) != item.contacto_id:
        return (
            STATUS_REVIEW_STATE_DRIFT,
            f"contacto_id={link.contacto_id} difiere del manifiesto {item.contacto_id}",
            None,
        )

    if not (CONTAMINATION_WINDOW_START <= link.created_at <= CONTAMINATION_WINDOW_END):
        return (
            STATUS_REVIEW_STATE_DRIFT,
            f"created_at={link.created_at.isoformat()} esta fuera de la ventana "
            f"contaminante {CONTAMINATION_WINDOW_START.isoformat()}"
            f"/{CONTAMINATION_WINDOW_END.isoformat()}",
            None,
        )

    if link.created_at != item.created_at:
        return (
            STATUS_REVIEW_STATE_DRIFT,
            f"created_at={link.created_at.isoformat()} difiere de la huella del "
            f"manifiesto {item.created_at.isoformat()}",
            None,
        )

    if not (CONTAMINATION_WINDOW_START <= link.updated_at <= CONTAMINATION_WINDOW_END):
        return (
            STATUS_REVIEW_STATE_DRIFT,
            "el link fue modificado despues de la corrida contaminante "
            f"(updated_at={link.updated_at.isoformat()})",
            None,
        )

    contacto = Contacto.objects.filter(id=item.contacto_id).first()
    if contacto is None:
        return (
            STATUS_REVIEW_CONTACTO_MISSING,
            f"no existe la entidad de contacto duplicada {item.contacto_id}",
            None,
        )

    if contacto.created_at != item.contacto_created_at:
        return (
            STATUS_REVIEW_STATE_DRIFT,
            f"la entidad duplicada {item.contacto_id} fue creada en "
            f"{contacto.created_at.isoformat()} y el manifiesto espera "
            f"{item.contacto_created_at.isoformat()}",
            None,
        )

    if not (
        CONTAMINATION_WINDOW_START <= contacto.updated_at <= CONTAMINATION_WINDOW_END
    ):
        return (
            STATUS_REVIEW_STATE_DRIFT,
            "la entidad duplicada fue modificada despues de la corrida "
            f"contaminante (updated_at={contacto.updated_at.isoformat()})",
            None,
        )

    references = _contacto_references(contacto)
    if references != 1:
        return (
            STATUS_REVIEW_REFERENCED_CONTACTO,
            f"la entidad duplicada {item.contacto_id} tiene {references} referencias "
            "(debe tener exactamente 1: su link contaminado)",
            None,
        )

    legacy_link = LiquidacionContacto.objects.filter(id=item.legacy_link_id).first()
    if legacy_link is None:
        return (
            STATUS_REVIEW_LEGACY_COUNTERPART_MISSING,
            f"el link legacy equivalente {item.legacy_link_id} ya no existe",
            None,
        )

    if _uuid(legacy_link.contacto_id) != item.legacy_contacto_id:
        return (
            STATUS_REVIEW_LEGACY_COUNTERPART_MISSING,
            f"el link legacy {item.legacy_link_id} apunta a {legacy_link.contacto_id} "
            f"y el manifiesto espera {item.legacy_contacto_id}",
            None,
        )

    return (
        STATUS_DELETE_LINK_AND_CONTACTO,
        "link de contacto duplicado creado por la colision de numeros legacy "
        "sobre una IO current (entidad de contacto huerfana, 1 referencia)",
        {
            "tipo": "CONTACTO",
            "link_id": item.link_id,
            "contacto_id": item.contacto_id,
        },
    )


def _inspector_row(
    item: InspectorCollision, status: str, evidence: str
) -> dict[str, object]:
    return {
        "tipo": "INSPECTOR",
        "numero": item.numero,
        "liquidacion_id": item.liquidacion_id,
        "visitas_id": item.visitas_id,
        "link_contaminado_id": item.link_id,
        "inspector_id": item.inspector_id,
        "inspector_operacion_id": item.inspector_operacion_id,
        "especialidad_revision_id": item.especialidad_revision_id,
        "cip": item.cip,
        "contacto_id": "",
        "legit_link_id": item.legit_link_id,
        "legit_inspector_id": item.legit_inspector_id,
        "legit_contacto_id": "",
        "legacy_link_id": item.legacy_link_id,
        "legacy_liquidacion_id": item.legacy_liquidacion_id,
        "created_at_esperado": item.created_at.isoformat(),
        "status": status,
        "accion": "DELETE" if status in DELETE_STATUSES else "NONE",
        "evidencia": evidence,
    }


def _contacto_row(
    item: ContactoCollision, status: str, evidence: str
) -> dict[str, object]:
    return {
        "tipo": "CONTACTO",
        "numero": item.numero,
        "liquidacion_id": item.liquidacion_id,
        "visitas_id": "",
        "link_contaminado_id": item.link_id,
        "inspector_id": "",
        "inspector_operacion_id": "",
        "especialidad_revision_id": "",
        "cip": "",
        "contacto_id": item.contacto_id,
        "legit_link_id": "",
        "legit_inspector_id": "",
        "legit_contacto_id": item.legit_contacto_id or "",
        "legacy_link_id": item.legacy_link_id,
        "legacy_liquidacion_id": item.legacy_liquidacion_id,
        "created_at_esperado": item.created_at.isoformat(),
        "status": status,
        "accion": "DELETE" if status in DELETE_STATUSES else "NONE",
        "evidencia": evidence,
    }


def _apply_operations(operations: list[dict]) -> None:
    """Execute the planned deletions. Callers must open the transaction."""
    for operation in operations:
        if operation["tipo"] == "INSPECTOR":
            LiquidacionInspector.objects.filter(id=operation["link_id"]).delete()
        elif operation["tipo"] == "CONTACTO":
            LiquidacionContacto.objects.filter(id=operation["link_id"]).delete()
            Contacto.objects.filter(id=operation["contacto_id"]).delete()
        elif operation["tipo"] == "CONTACTO_ORPHAN":
            Contacto.objects.filter(id=operation["contacto_id"]).delete()


class Command(BaseCommand):
    help = (
        "Reconcile the 17 non-legacy IO inspector links and the 29 non-legacy IO "
        "contact links (plus their 29 duplicated contactos) contaminated by the "
        "legacy number collision of 2026-11-23. Dry-run by default."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Ejecuta las eliminaciones. Sin este flag solo se escribe el CSV.",
        )
        parser.add_argument(
            "--csv-output",
            required=True,
            help="Ruta del CSV de auditoria (una fila por caso del manifiesto).",
        )

    def handle(self, *args, **options):
        rows: list[dict[str, object]] = []
        operations: list[dict] = []

        with transaction.atomic():
            for item in INSPECTOR_COLLISIONS:
                status, evidence, operation = _plan_inspector(item)
                rows.append(_inspector_row(item, status, evidence))
                if operation is not None:
                    operations.append(operation)

            for item in CONTACTO_COLLISIONS:
                status, evidence, operation = _plan_contacto(item)
                rows.append(_contacto_row(item, status, evidence))
                if operation is not None:
                    operations.append(operation)

            if options["apply"]:
                _apply_operations(operations)

        output = Path(options["csv_output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

        counts = Counter(row["status"] for row in rows)
        mode = "APPLY" if options["apply"] else "DRY-RUN"
        self.stdout.write(
            self.style.SUCCESS(
                f"=== Non-legacy IO inspector/contact reconciliation ({mode}) ==="
            )
        )
        for status, count in sorted(counts.items()):
            self.stdout.write(f"{status}: {count}")
        self.stdout.write(f"CSV: {output}")
