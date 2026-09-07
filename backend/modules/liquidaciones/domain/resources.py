"""
django-import-export Resources for DelegadoOperacion and InspectorOperacion.

Allows flat Excel/CSV import with CIP API enrichment and automatic
period creation — one row = one (Delegado|Inspector)Operacion instance.

Excel column mapping (Delegados sheet):
    cip, municipalidad_codigo, tipo (TITULAR|ALTERNO),
    tipo_liquidacion_codigo, especialidad_nombre, vigencia_inicio, vigencia_fin

Excel column mapping (Inspectores sheet):
    cip, categoria (1|2|3|4), tipo_liquidacion_codigo,
    especialidad_nombre, vigencia_inicio, vigencia_fin

Both sheets require virtual field dehydration so the admin preview shows
readable values (e.g. municipalidad codigo instead of pk).
"""

import logging
import unicodedata
from datetime import date, datetime
from typing import Optional

from django.core.exceptions import ValidationError
from import_export import fields, resources, widgets

from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.liquidaciones.domain.constants import CategoriaIO, TipoDelegado
from modules.liquidaciones.domain.models import (
    Delegado,
    DelegadoOperacion,
    DelegadoOperacionPeriodo,
    Inspector,
    InspectorOperacion,
    InspectorOperacionPeriodo,
    TipoLiquidacion,
)
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision, PerfilIngeniero
from modules.usuarios.infrastructure.services import CipServiceUnavailableError, get_cip_client

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize_name(name: str) -> str:
    """Normalize string: uppercase, strip accents, collapse whitespace."""
    if not name:
        return ""
    n = unicodedata.normalize("NFD", name.upper())
    return " ".join(
        c
        for c in n
        if unicodedata.category(c) != "Mn"
    ).replace("-", " ")


def normalize_cip(cip: str) -> str:
    """Normalize CIP to 6-digit zero-padded string."""
    digits = "".join(ch for ch in (cip or "").strip() if ch.isdigit())
    return digits.zfill(6)[:6]


def _normalize_tipo_codigo(codigo: str) -> str:
    """Normaliza el código de tipo de liquidación (espacios, plurales)."""
    c = (codigo or "").strip().upper().replace(" ", "_")
    if c == "EDIFICACIONES":
        return "EDIFICACION"
    return c


def cip_sin_ceros(cip: str) -> str:
    """Strip leading zeros from CIP for numero_registro generation."""
    return str(int(cip or "0"))


def parse_date(value: str) -> Optional[date]:
    """Parse YYYY-MM-DD string to date, return None if empty/invalid."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _resolve_especialidad(nombre_esp: str) -> Optional[EspecialidadRevision]:
    """
    Resolve EspecialidadRevision by normalized name matching.
    Mirrors seed_delegados._resolver_especialidad_revision logic:
    1. Split on ' - ' and take the first part
    2. Match __iexact on nombre
    3. Apply known synonyms
    4. Fall back to normalized comparison
    Returns None if not found.
    """
    if not nombre_esp:
        return None
    raw = str(nombre_esp).strip()
    base = raw.split(" - ")[0].strip()

    # Direct iexact match
    obj = EspecialidadRevision.objects.filter(nombre__iexact=base).first()
    if obj:
        return obj

    # Known synonyms used by seeds / CSV exports
    SYNONYMS = {
        "Ingeniería Eléctrica y Mecánica Eléctrica": "Ingeniería Eléctrica y Mecánica Eléctrica",
        "Ingenieria Electrica y Mecanica Electrica": "Ingeniería Eléctrica y Mecánica Eléctrica",
        "Ingeniería Eléctrica": "Ingeniería Eléctrica y Mecánica Eléctrica",
        "Eléctrica/Mecánica": "Ingeniería Eléctrica y Mecánica Eléctrica",
        "INGENIERIA CIVIL": "Ingeniería Civil",
        "INGENIERIA SANITARIA": "Ingeniería Sanitaria",
    }
    sinonimo = SYNONYMS.get(base)
    if sinonimo:
        obj = EspecialidadRevision.objects.filter(nombre__iexact=sinonimo).first()
        if obj:
            return obj

    # Final fallback: compare normalized names
    norm = normalize_name(base)
    for cand in EspecialidadRevision.objects.all():
        if normalize_name(cand.nombre) == norm:
            return cand
    return None


def _resolve_municipalidad(codigo: str = "", nombre: str = "") -> Optional[Municipalidad]:
    """
    Resolve Municipalidad by normalized nombre first, then by codigo fallback.
    Returns None if not found.
    """
    # 0. Aliases explícitos (nombres del Excel legacy -> nombre canónico en DB)
    ALIASES = {
        "ASIA": "SAN VICENTE DE CAÑETE/ASIA",
        "BARRANCA": "BARRANCA - NORTE",
        "CENTRO HISTORICO": "CENTRO HISTÓRICO DE LIMA",
        "COMISION AD HOC": "COMISION AD HOC SEGUNDA INSTANCIA ADMINISTRATIVA",
        "LURIGANCHO – CHOSICA": "LURIGANCHO - CHOSICA",
        "PROVINCIA DE HUAROCHIRI": "HUAROCHIRI",
        "PROVINCIAL DE BARRANCA": "BARRANCA - NORTE",
        "PROVINCIAL DE CAÑETE": "SAN ANTONIO - CAÑETE",
        "PROVINCIAL DE HUAURA": "HUAURA",
        "SAN ANTONIO DE CAÑETE": "SAN ANTONIO - CAÑETE",
        "SAN LUIS DE CAÑETE": "SAN LUIS - CAÑETE",
        "STA MARIA": "SANTA MARIA",
        "SATA MARIA": "SANTA MARIA",
        "SUPE PUERTO": "SUPE",
    }
    if nombre:
        clave = nombre.strip().upper()
        objetivo = ALIASES.get(clave)
        if objetivo:
            m = Municipalidad.objects.filter(nombre__iexact=objetivo).first()
            if m:
                return m
    # 1. Try normalized name match across ALL municipalidades
    if nombre:
        norm = normalize_name(nombre)
        for m in Municipalidad.objects.all():
            if normalize_name(m.nombre) == norm:
                return m
    # 2. Fallback: try codigo match
    if codigo:
        m = Municipalidad.objects.filter(codigo=codigo).first()
        if m:
            return m
    return None


# Alias for typo in previous version
Municipio = Municipalidad


def _upsert_perfil_from_cip(cip: str, cip_data: dict) -> tuple[PerfilIngeniero, bool]:
    """
    Get or create a PerfilIngeniero from CIP API data.
    Updates existing profiles with new CIP data.
    Returns (perfil, created).
    """
    if not cip_data:
        return None, False

    nombres_api = " ".join(
        p
        for p in [cip_data.get("nombre1") or "", cip_data.get("nombre2") or ""]
        if p and str(p).lower() != "none"
    )
    fields_map = {
        "dni": cip_data.get("dni", ""),
        "nombres": nombres_api,
        "apellido_paterno": cip_data.get("paterno", ""),
        "apellido_materno": cip_data.get("materno", ""),
        "correo_personal": cip_data.get("correopers") or None,
        "celular": cip_data.get("celular") or None,
    }
    # Filter out empty strings
    fields_map = {k: v for k, v in fields_map.items() if v}

    try:
        perfil = PerfilIngeniero.objects.get(cip=cip)
        for field, value in fields_map.items():
            setattr(perfil, field, value)
        perfil.save(update_fields=list(fields_map.keys()))
        return perfil, False
    except PerfilIngeniero.DoesNotExist:
        fields_map["cip"] = cip
        return PerfilIngeniero.objects.create(**fields_map), True


# ── DelegadoOperacionResource ─────────────────────────────────────────────────

class DelegadoOperacionResource(resources.ModelResource):
    """
    Import resource for DelegadoOperacion with flat Excel format.

    Virtual Excel columns (read from row, resolved in before_import_row):
        cip, municipalidad_codigo, tipo, tipo_liquidacion_codigo,
        especialidad_nombre, vigencia_inicio, vigencia_fin

    after_save_instance creates DelegadoOperacionPeriodo entries.
    """

    # ── Virtual Excel columns (NOT model fields) ────────────────────────────────
    cip = fields.Field(
        column_name="cip",
        widget=widgets.CharWidget(),
        saves_null_values=False,
    )
    municipalidad_codigo = fields.Field(
        column_name="municipalidad_codigo",
        widget=widgets.CharWidget(),
    )
    tipo = fields.Field(
        column_name="tipo",
        widget=widgets.CharWidget(),
    )
    tipo_liquidacion_codigo = fields.Field(
        column_name="tipo_liquidacion_codigo",
        widget=widgets.CharWidget(),
    )
    especialidad_nombre = fields.Field(
        column_name="especialidad_nombre",
        widget=widgets.CharWidget(),
    )
    vigencia_inicio = fields.Field(
        column_name="vigencia_inicio",
        widget=widgets.DateWidget(format="%Y-%m-%d"),
    )
    vigencia_fin = fields.Field(
        column_name="vigencia_fin",
        widget=widgets.DateWidget(format="%Y-%m-%d"),
        saves_null_values=True,
    )

    # ── Explicit FK/id fields ──────────────────────────────────────────────────
    # These map the injected row keys (from before_import_row) to actual model
    # fields so import_export's hydrate_instance populates the instance and
    # skip_unchanged diffs correctly (row value != blank instance → not skipped).
    delegado_id = fields.Field(
        attribute="delegado_id",
        column_name="delegado_id",
        saves_null_values=False,
    )
    municipalidad_id = fields.Field(
        attribute="municipalidad_id",
        column_name="municipalidad_id",
        saves_null_values=False,
    )
    tipo_liquidacion_id = fields.Field(
        attribute="tipo_liquidacion_id",
        column_name="tipo_liquidacion_id",
        saves_null_values=True,
    )
    especialidad_revision_id = fields.Field(
        attribute="especialidad_revision_id",
        column_name="especialidad_revision_id",
        saves_null_values=False,
    )

    class Meta:
        model = DelegadoOperacion
        batch_size = 500
        skip_unchanged = True
        report_skipped = True  # enabled for debugging
        # Use empty import_id_fields — we override get_instance instead
        import_id_fields = []

    def skip_row(self, instance, original, row, import_validation_errors=None, **kwargs):
        """
        Never skip a row — get_instance already returns None for new records,
        and the FK field mappings ensure hydrate_instance populates the instance,
        so skip_unchanged diff is reliable for update detection.
        """
        return False

    def before_import_row(self, row, **kwargs):
        """
        Enrich row from CIP API and resolve all FK references.
        Raises ValidationError if CIP cannot be resolved (safe for admin import).
        """
        """
        Enrich row from CIP API and resolve all FK references.
        Raises ValidationError if CIP cannot be resolved (safe for admin import).
        """
        # ── 1. Normalize CIP ─────────────────────────────────────────────────
        cip_raw = str(row.get("cip", "")).strip()
        cip = normalize_cip(cip_raw)
        if not cip:
            raise ValidationError(f"CIP vacío o inválido: '{cip_raw}'")

        # ── 2. Enrich from CIP API (solo si el perfil NO existe) ──────────
        perfil = PerfilIngeniero.objects.filter(cip=cip).first()
        if perfil is None:
            try:
                cip_data = get_cip_client().get_colegiado(cip)
            except CipServiceUnavailableError as e:
                raise ValidationError(
                    f"Servicio CIP no disponible para CIP {cip}: {e}"
                ) from e

            if not cip_data:
                raise ValidationError(
                    f"CIP {cip} no encontrado en el servicio CIP ni en la base local. "
                    "Verifique el número de CIP."
                )

            perfil, _ = _upsert_perfil_from_cip(cip, cip_data)

        # ── 3. Get or create Delegado ───────────────────────────────────────
        delegado, _ = Delegado.objects.get_or_create(
            perfil_ingeniero=perfil,
        )

        # ── 4. Resolve FKs ────────────────────────────────────────────────
        codigo = str(row.get("municipalidad_codigo", "")).strip()
        # La columna puede traer el nombre o el código L; probar ambos.
        municipalidad = _resolve_municipalidad(codigo=codigo, nombre=codigo)
        if not municipalidad:
            raise ValidationError(
                f"Municipalidad no encontrada para código/nombre: '{codigo}'"
            )

        tipo_liq_codigo = str(row.get("tipo_liquidacion_codigo", "")).strip()
        tipo_liq = None
        if tipo_liq_codigo:
            tipo_liq = TipoLiquidacion.objects.filter(
                codigo=_normalize_tipo_codigo(tipo_liq_codigo)
            ).first()
            if not tipo_liq:
                raise ValidationError(
                    f"TipoLiquidacion no encontrado: '{tipo_liq_codigo}'"
                )

        esp_nombre = str(row.get("especialidad_nombre", "")).strip()
        esp = _resolve_especialidad(esp_nombre)
        if not esp:
            raise ValidationError(
                f"EspecialidadRevision no encontrada para: '{esp_nombre}'"
            )

        # ── 5. Inject resolved IDs so hydrate_for_lib / ORM can use them ──
        row["delegado_id"] = delegado.id
        row["municipalidad_id"] = municipalidad.id
        row["tipo_liquidacion_id"] = tipo_liq.id if tipo_liq else None
        row["especialidad_revision_id"] = esp.id
        # Store for after_save_instance
        row["_delegado"] = delegado
        row["_municipalidad"] = municipalidad
        row["_tipo_liq"] = tipo_liq
        row["_esp"] = esp

    def dehydrate_cip(self, obj: DelegadoOperacion) -> str:
        return obj.delegado.perfil_ingeniero.cip

    def dehydrate_municipalidad_codigo(self, obj: DelegadoOperacion) -> str:
        return obj.municipalidad.codigo

    def dehydrate_tipo(self, obj: DelegadoOperacion) -> str:
        return obj.tipo

    def dehydrate_tipo_liquidacion_codigo(self, obj: DelegadoOperacion) -> str:
        return obj.tipo_liquidacion.codigo if obj.tipo_liquidacion else ""

    def dehydrate_especialidad_nombre(self, obj: DelegadoOperacion) -> str:
        return obj.especialidad_revision.nombre

    def get_instance(self, instance_loader, row):
        """
        Retrieve an existing DelegadoOperacion by (delegado, municipalidad, tipo_liquidacion)
        or return a new instance if not found.
        This prevents unique-constraint violations from duplicate creates.
        """
        delegado_id = row.get("delegado_id")
        municipalidad_id = row.get("municipalidad_id")
        tipo_liq_id = row.get("tipo_liquidacion_id")

        if not all([delegado_id, municipalidad_id]):
            return None

        # Match on the unique_together: (delegado, municipalidad, tipo_liquidacion)
        # tipo_liquidacion can be null, so we filter accordingly
        query = DelegadoOperacion.objects.filter(
            delegado_id=delegado_id,
            municipalidad_id=municipalidad_id,
        )
        if tipo_liq_id:
            query = query.filter(tipo_liquidacion_id=tipo_liq_id)
        else:
            query = query.filter(tipo_liquidacion__isnull=True)

        existing = query.first()
        if existing:
            return existing
        return None

    def after_save_instance(self, instance, row, **kwargs):
        """
        Create DelegadoOperacionPeriodo from row's vigencia_inicio / vigencia_fin.
        Uses update_or_create on (delegado_municipalidad, periodo_inicio) to allow
        exact date ranges and support re-imports.
        """
        vigencia_inicio = parse_date(row.get("vigencia_inicio"))
        if not vigencia_inicio:
            return

        vigencia_fin = parse_date(row.get("vigencia_fin")) if row.get("vigencia_fin") else None

        DelegadoOperacionPeriodo.objects.update_or_create(
            delegado_municipalidad=instance,
            periodo_inicio=vigencia_inicio,
            defaults={"periodo_fin": vigencia_fin},
        )


# ── InspectorOperacionResource ─────────────────────────────────────────────────

class InspectorOperacionResource(resources.ModelResource):
    """
    Import resource for InspectorOperacion with flat Excel format.

    Virtual Excel columns (read from row, resolved in before_import_row):
        cip, categoria (1|2|3|4), tipo_liquidacion_codigo,
        especialidad_nombre, vigencia_inicio, vigencia_fin

    after_save_instance creates InspectorOperacionPeriodo entries.
    """

    # ── Virtual Excel columns (NOT model fields) ────────────────────────────────
    cip = fields.Field(
        column_name="cip",
        widget=widgets.CharWidget(),
        saves_null_values=False,
    )
    categoria = fields.Field(
        column_name="categoria",
        widget=widgets.CharWidget(),
    )
    tipo_liquidacion_codigo = fields.Field(
        column_name="tipo_liquidacion_codigo",
        widget=widgets.CharWidget(),
    )
    especialidad_nombre = fields.Field(
        column_name="especialidad_nombre",
        widget=widgets.CharWidget(),
    )
    vigencia_inicio = fields.Field(
        column_name="vigencia_inicio",
        widget=widgets.DateWidget(format="%Y-%m-%d"),
    )
    vigencia_fin = fields.Field(
        column_name="vigencia_fin",
        widget=widgets.DateWidget(format="%Y-%m-%d"),
        saves_null_values=True,
    )

    # ── Explicit FK/id fields ──────────────────────────────────────────────────
    inspector_id = fields.Field(
        attribute="inspector_id",
        column_name="inspector_id",
        saves_null_values=False,
    )
    tipo_liquidacion_id = fields.Field(
        attribute="tipo_liquidacion_id",
        column_name="tipo_liquidacion_id",
        saves_null_values=True,
    )
    especialidad_revision_id = fields.Field(
        attribute="especialidad_revision_id",
        column_name="especialidad_revision_id",
        saves_null_values=False,
    )
    numero_registro = fields.Field(
        attribute="numero_registro",
        column_name="numero_registro",
        saves_null_values=False,
    )

    class Meta:
        model = InspectorOperacion
        batch_size = 500
        skip_unchanged = True
        report_skipped = True  # enabled for debugging
        import_id_fields = []

    def skip_row(self, instance, original, row, import_validation_errors=None, **kwargs):
        """
        Never skip a row — get_instance already returns None for new records,
        and the FK field mappings ensure hydrate_instance populates the instance.
        """
        return False

    def before_import_row(self, row, **kwargs):
        """
        Enrich row from CIP API and resolve all FK references.
        Raises ValidationError if CIP cannot be resolved.
        """
        self._current_row = row
        # ── 1. Normalize CIP ───────────────────────────────────────────────
        cip_raw = str(row.get("cip", "")).strip()
        cip = normalize_cip(cip_raw)
        if not cip:
            raise ValidationError(f"CIP vacío o inválido: '{cip_raw}'")

        # ── 2. Enrich from CIP API (solo si el perfil NO existe) ─────────
        perfil = PerfilIngeniero.objects.filter(cip=cip).first()
        if perfil is None:
            try:
                cip_data = get_cip_client().get_colegiado(cip)
            except CipServiceUnavailableError as e:
                raise ValidationError(
                    f"Servicio CIP no disponible para CIP {cip}: {e}"
                ) from e

            if not cip_data:
                raise ValidationError(
                    f"CIP {cip} no encontrado en el servicio CIP ni en la base local."
                )

            perfil, _ = _upsert_perfil_from_cip(cip, cip_data)

        # ── 3. Get or create Inspector ────────────────────────────────────
        inspector, _ = Inspector.objects.get_or_create(
            perfil_ingeniero=perfil,
        )

        # ── 4. Resolve FKs ────────────────────────────────────────────────
        tipo_liq_codigo = str(row.get("tipo_liquidacion_codigo", "")).strip()
        tipo_liq = None
        if tipo_liq_codigo:
            tipo_liq = TipoLiquidacion.objects.filter(
                codigo=_normalize_tipo_codigo(tipo_liq_codigo)
            ).first()
            if not tipo_liq:
                raise ValidationError(
                    f"TipoLiquidacion no encontrado: '{tipo_liq_codigo}'"
                )

        esp_nombre = str(row.get("especialidad_nombre", "")).strip()
        esp = _resolve_especialidad(esp_nombre)
        if not esp:
            raise ValidationError(
                f"EspecialidadRevision no encontrada para: '{esp_nombre}'"
            )

        # ── 5. Compute numero_registro for uniqueness matching ────────────
        categoria = str(row.get("categoria", "")).strip()
        numero_registro = f"CAM{cip_sin_ceros(cip)}{categoria}"

        # ── 6. Inject resolved IDs ───────────────────────────────────────
        row["inspector_id"] = inspector.id
        row["tipo_liquidacion_id"] = tipo_liq.id if tipo_liq else None
        row["especialidad_revision_id"] = esp.id
        row["numero_registro"] = numero_registro
        row["categoria"] = categoria
        row["_inspector"] = inspector
        row["_tipo_liq"] = tipo_liq
        row["_esp"] = esp

    def dehydrate_cip(self, obj: InspectorOperacion) -> str:
        return obj.inspector.perfil_ingeniero.cip

    def dehydrate_categoria(self, obj: InspectorOperacion) -> str:
        return obj.categoria

    def dehydrate_tipo_liquidacion_codigo(self, obj: InspectorOperacion) -> str:
        return obj.tipo_liquidacion.codigo if obj.tipo_liquidacion else ""

    def dehydrate_especialidad_nombre(self, obj: InspectorOperacion) -> str:
        return obj.especialidad_revision.nombre

    def get_instance(self, instance_loader, row):
        """
        Retrieve an existing InspectorOperacion by
        (inspector, tipo_liquidacion, numero_registro).
        numero_registro is deterministic from (cip + categoria).
        """
        inspector_id = row.get("inspector_id")
        numero_registro = row.get("numero_registro")

        if not inspector_id:
            return None

        query = InspectorOperacion.objects.filter(
            inspector_id=inspector_id,
            numero_registro=numero_registro,
        )
        # Filter by tipo_liquidacion if provided
        tipo_liq_id = row.get("tipo_liquidacion_id")
        if tipo_liq_id:
            query = query.filter(tipo_liquidacion_id=tipo_liq_id)
        else:
            query = query.filter(tipo_liquidacion__isnull=True)

        existing = query.first()
        if existing:
            return existing
        return None

    def before_save_instance(self, instance, row, **kwargs):
        """Asegura que categoria y numero_registro se asignen al modelo antes de guardar."""
        if "categoria" in row:
            instance.categoria = str(row["categoria"]).strip()
        if "numero_registro" in row:
            instance.numero_registro = row["numero_registro"]

    def after_save_instance(self, instance, row, **kwargs):
        """
        Create InspectorOperacionPeriodo from row's vigencia_inicio / vigencia_fin.
        Uses update_or_create on (inspector_tipo_liquidacion, periodo_inicio).
        """
        vigencia_inicio = parse_date(row.get("vigencia_inicio"))
        if not vigencia_inicio:
            return

        vigencia_fin = parse_date(row.get("vigencia_fin")) if row.get("vigencia_fin") else None

        InspectorOperacionPeriodo.objects.update_or_create(
            inspector_tipo_liquidacion=instance,
            periodo_inicio=vigencia_inicio,
            defaults={"periodo_fin": vigencia_fin},
        )
