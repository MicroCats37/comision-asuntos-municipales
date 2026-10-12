"""
import_legacy_mecanica_suelos — Crea LiquidacionMecanicaSuelos desde SUELOS_ALL.csv.

Dataset: ~700 rows. Layout CSV idéntico a HU_ALL.csv (61 cols, 1 slot delegado).
Esta versión NO usa orchestrator legacy (no existe funcionalmente); crea
directamente las ORM records con la misma semántica que el legacy import de EDIF.

Lógica de thresholds (igual que EDIF/HU):
  --rechazar-dif-alta          rechaza filas donde |subtotal_legacy - subtotal_recalc| > --umbral-dif
  --umbral-dif 1.0             (default)

Uso:
    python manage.py import_legacy_mecanica_suelos --dry-run
    python manage.py import_legacy_mecanica_suelos --apply
    python manage.py import_legacy_mecanica_suelos --rechazar-dif-alta --umbral-dif 1 --apply
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from modules.liquidaciones.domain.constants import TipoDelegado, TipoLiquidacion
from modules.liquidaciones.domain.models.delegado import Delegado, DelegadoOperacion, LiquidacionDelegado
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_mecanica_suelos import (
    LiquidacionMecanicaSuelos,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorMetroCuadrado,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
    LiquidacionComprobante,
    TipoComprobante,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionContacto,
    LiquidacionGeneral,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaPorMetroCuadrado,
)
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion as TipoLiqModel
from modules.entidades.domain.models.contacto import Contacto
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.entidades.domain.models.ubigeo import UbigeoDistrito
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorMetroCuadrado,
)
from modules.liquidaciones.domain.services.core.liquidacion_legacy.liquidacion_legacy_por_m2_core_service import (
    LiquidacionLegacyPorM2CoreService,
)
from modules.liquidaciones.domain.services.core.liquidacion_legacy.liquidacion_legacy_por_visitas_core_service import (
    LiquidacionLegacyPorVisitasCoreService,
)
from modules.usuarios.domain.services.core.perfil_ingeniero_core_service import (
    PerfilIngenieroCoreService,
)
from modules.usuarios.domain.models.perfil_ingeniero import (
    EspecialidadRevision,
    PerfilIngeniero,
)


DEFAULT_DATA_PATH = Path(
    r"C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\backend\core_application\seeds\historico\SUELOS_ALL.csv"
)
SEP = ";"
TOL_HONORARIO = Decimal("0.01")
NOMBRE_FALTANTE_LEGACY = "SIN NOMBRE RAZON SOCIAL LEGACY"
DIRECCION_FALTANTE_LEGACY = "SIN DIRECCION LEGACY"


def _clean(value):
    text = str(value).strip() if value is not None else ""
    if not text or text.upper() in ("NULL", "NONE", ""):
        return None
    return text


def _parse_date(value):
    """Parse fecha from string with multiple format support."""
    from datetime import date as _date, datetime as _dt
    text = _clean(value)
    if text is None:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d/%m/%Y %H:%M:%S"):
        try:
            return _dt.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _tipo_from_doc(raw):
    """Mapea DOC col 29 a TipoComprobante value (F/FA/FAC→FACTURA, B/BO/BOL→BOLETA)."""
    if not raw:
        return None
    code = str(raw).strip().upper()
    if code in ("F", "FA", "FAC", "FACT"):
        return "FACTURA"
    if code in ("B", "BO", "BOL"):
        return "BOLETA"
    if code == "NC":
        return "NOTA_CREDITO"
    if code == "ND":
        return "NOTA_DEBITO"
    return None


def _dec(value):
    text = _clean(value)
    if text is None:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _int(value):
    text = _clean(value)
    if text is None:
        return None
    try:
        return int(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def _parse_tpersona(raw):
    text = _clean(raw)
    if text is None:
        return None, None
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    parts = text.split(None, 1)
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


def _lookup_m2_tarifa(fecha) -> TarifaPorMetroCuadrado | None:
    """Lookup via LiquidacionLegacyPorM2CoreService (resuelve por fecha con vigencia)."""
    if fecha is None:
        return None
    return LiquidacionLegacyPorM2CoreService().get_tarifa_m2_por_fecha(
        TipoLiquidacion.MECANICA_SUELOS, fecha
    )


def _lookup_derecho_m2(fecha):
    if fecha is None:
        return None
    return LiquidacionLegacyPorM2CoreService().get_derecho_m2_por_fecha(fecha)


def _normalize_cip(raw) -> str:
    text = _clean(raw)
    if text is None:
        return ""
    digits = "".join(c for c in text if c.isdigit())
    return digits.zfill(6)[:6] if digits else ""


def _row_to_dict(reader_row: dict) -> dict:
    return {k.strip().upper(): (v or "").strip() for k, v in reader_row.items()}


class Command(BaseCommand):
    help = "Importa LiquidacionMecanicaSuelos desde SUELOS_ALL.csv (Crea ORM directo)."

    def add_arguments(self, parser):
        parser.add_argument("--csv", type=str, default=str(DEFAULT_DATA_PATH))
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument(
            "--rechazar-dif-alta", action="store_true",
            help="Rechaza filas con |subtotal_legacy - subtotal_recalc| > umbral-dif.",
        )
        parser.add_argument(
            "--umbral-dif", type=float, default=1.0,
            help="Umbral S/. para rechazo por diff (default 1.0).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Solo lee y reporta. No escribe (default).",
        )
        parser.add_argument(
            "--apply", action="store_true",
            help="Escribe en BD.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        apply = bool(options["apply"])
        rechazar = bool(options["rechazar_dif_alta"])
        umbral = Decimal(str(options["umbral_dif"]))
        limit = options.get("limit")
        modo = "APPLY" if apply else "DRY-RUN"

        if apply:
            self.stdout.write(self.style.WARNING(
                f"  ATENCIÓN: --apply activado. Se escribirá en BD."
            ))

        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"No existe: {csv_path}"))
            sys.exit(1)

        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path(r"C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\result\MECANICA_SUELOS")
        out_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.NOTICE(f"[import_legacy_mecanica_suelos] {modo}"))
        self.stdout.write(f"  CSV: {csv_path}")
        self.stdout.write(f"  Out: {out_dir}/{run_id}")

        # ── 1. Leer CSV ──
        rows: list[tuple[int, dict]] = []
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=SEP)
            for n, r in enumerate(reader, start=2):
                rd = _row_to_dict(r)
                nro = _int(rd.get("NRO"))
                if nro is None:
                    continue
                rows.append((n, rd))
        if limit:
            rows = rows[:limit]
        self.stdout.write(f"  Filas con NRO válido: {len(rows)}")

        # ── 2. Servicio legacy M2 (resuelve tarifa + derecho por fecha) ──
        # Usamos el servicio legacy existente que ya considera vigencia
        # (incluyendo tarifas cerradas que cubren la fecha histórica).
        from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
            TarifaLiquidacionBase,
        )
        from modules.liquidaciones.domain.services.core.liquidacion_tipo.tarifas_historicas_core_service import (
            TarifasHistoricasCoreService,
        )
        self._m2_core = LiquidacionLegacyPorM2CoreService(tarifas_service=TarifasHistoricasCoreService())

        # ── 3. Procesar ──
        report_lines: list[str] = []
        counters = {"created": 0, "reused": 0, "rejected_diff": 0, "errors": 0}

        for linea, raw in rows:
            nro = _int(raw.get("NRO"))
            try:
                # ¿Ya existe?
                existing = LiquidacionMecanicaSuelos.objects.filter(numero=nro).first()
                if existing:
                    counters["reused"] += 1
                    report_lines.append(f"{nro}\t{nro}\treusada\tSI\treusada")
                    continue

                # ── Resolver tarifa M2 por fecha (vía servicio legacy) ──
                fecha_raw = _clean(raw.get("FECHA"))
                if not fecha_raw:
                    counters["errors"] += 1
                    report_lines.append(f"{nro}\t{nro}\tsin fecha\tNO\terror")
                    continue
                try:
                    fecha = datetime.strptime(fecha_raw.split()[0], "%Y-%m-%d").date()
                except ValueError:
                    counters["errors"] += 1
                    report_lines.append(f"{nro}\t{nro}\tfecha invalida {fecha_raw!r}\tNO\terror")
                    continue

                tarifa = self._m2_core.get_tarifa_m2_por_fecha(
                    TipoLiquidacion.MECANICA_SUELOS, fecha
                )
                if tarifa is None:
                    counters["errors"] += 1
                    report_lines.append(f"{nro}\t{nro}\tsin tarifa MS para fecha {fecha}\tNO\terror")
                    continue
                costo_por_m2 = Decimal(str(tarifa.costo_por_m2))
                derecho = self._m2_core.get_derecho_m2_por_fecha(fecha)
                derecho_minimo = Decimal(str(derecho.derecho_minimo)) if derecho else Decimal("0")

                # ── Datos de la liquidación ──
                area = _dec(raw.get("AREA"))
                subtotal_legacy = _dec(raw.get("SUBTOTAL"))
                igv_legacy = _dec(raw.get("IGV")) or Decimal("0")
                total_legacy = _dec(raw.get("TOTAL"))
                if not area or area <= 0 or not subtotal_legacy:
                    counters["errors"] += 1
                    report_lines.append(f"{nro}\t{nro}\tarea/subtotal invalido\tNO\terror")
                    continue

                # ── Recalc legacy: subtotal = area * costo (SIN 1.19, SIN clamps) ──
                # Comparamos con subtotal_legacy (col 11). Las legacy con
                # derecho_minimo se aceptan con diff > umbral SOLO si
                # --rechazar-dif-alta está activo.
                subtotal_recalc = costo_por_m2 * area
                diff = abs(subtotal_recalc - subtotal_legacy)
                if rechazar and diff > umbral:
                    counters["rejected_diff"] += 1
                    report_lines.append(
                        f"{nro}\t{nro}\tarea={area} rec={subtotal_recalc:.2f} excel={subtotal_legacy} diff={diff:.2f} > {umbral}\tNO\trechazada"
                    )
                    continue

                # ── Resolver municipalidad por codpago ──
                codpago = _clean(raw.get("CODPAGO"))
                municipalidad = (
                    Municipalidad.objects.filter(
                        codigo=codpago.upper()
                    ).first() if codpago else None
                )
                if not municipalidad:
                    ubigeo_nombre = (
                        (_clean(raw.get("DPTOPRDI")) or "").split("/")[-1].strip()
                    )
                    if ubigeo_nombre:
                        ubigeo = UbigeoDistrito.objects.filter(
                            nombre__iexact=ubigeo_nombre
                        ).first()
                        if ubigeo:
                            municipalidad = Municipalidad.objects.filter(
                                distrito=ubigeo
                            ).first()
                if not municipalidad:
                    municipalidad = Municipalidad.objects.first()
                if not municipalidad:
                    counters["errors"] += 1
                    report_lines.append(f"{nro}\t{nro}\tsin municipalidad\tNO\terror")
                    continue

                # ── Entidad/proyecto (mismo mapeo HU) ──
                dni = _clean(raw.get("DNI"))
                ruc = _clean(raw.get("RUC"))
                # nombre_propietario viene SOLO de NOMBRE col 3
                nombre_propietario = _clean(raw.get("NOMBRE")) or NOMBRE_FALTANTE_LEGACY
                # entidad_razon_social viene de RAZONSOCIAL col 16 con fallback chain
                razon_social = _clean(raw.get("RAZONSOCIAL")) or _clean(raw.get("NOMBRE")) or (
                    NOMBRE_FALTANTE_LEGACY
                )
                direccion = _clean(raw.get("DIRECCION")) or DIRECCION_FALTANTE_LEGACY
                urbanizacion = _clean(raw.get("URBNZCION"))

                # ── LiquidacionGeneral ──
                # Legacy requiere proyecto. OneToOne: creamos un proyecto por LG.
                from modules.liquidaciones.domain.models.proyecto import Proyecto
                legacy_proyecto = Proyecto.objects.create(
                    nombre_propietario=nombre_propietario or "LEGACY IMPORT",
                    direccion=direccion,
                    distrito_id=getattr(municipalidad, "distrito_id", None),
                    entidad_razon_social=razon_social,
                )
                # Resolver naive vs aware datetime para evitar warnings
                from django.utils import timezone as djtz
                fecha_dt = datetime.combine(fecha, datetime.min.time())
                if djtz.is_naive(fecha_dt) and not djtz.is_naive(datetime.now()):
                    from django.utils.timezone import make_aware
                    fecha_dt = make_aware(fecha_dt)

                # ── Pre-parse contacto (TPERSONA / TFONO / TDNI) ──
                nombres_c, apellidos_c = _parse_tpersona(raw.get("TPERSONA"))
                telefono_c = _clean(raw.get("TFONO"))
                tdni_c = _clean(raw.get("TDNI"))

                if apply:
                    with transaction.atomic():
                        lg = LiquidacionGeneral.objects.create(
                            proyecto=legacy_proyecto,
                            municipalidad=municipalidad,
                            tipo_liquidacion=tipo_ms,
                            expediente=_clean(raw.get("NROEXPDTE")) or "",
                            numero_revision=1,
                            fecha_registro=fecha_dt,
                            sub_total=subtotal_legacy,
                            total=total_legacy or (subtotal_legacy + igv_legacy),
                            modo_calculo="TARIFA",
                            legacy=True,
                            retencion=False,
                            denominacion_de_proyecto=_clean(raw.get("PROYECTO")),
                            descripcion_legacy=(
                                f"Legacy MS import fila {linea} NRO={nro} ID={raw.get('ID', '')}"
                            ),
                        )

                        # ── LiquidacionMecanicaSuelos (vincula LG) ──
                        LiquidacionMecanicaSuelos.objects.create(
                            liquidacion=lg,
                            numero=nro,
                        )
                        # ── LiquidacionPorMetroCuadrado (datos del cálculo) ──
                        # M2: solo area_m2 (sin costo/derecho_minimo/tarifa — los legacy MS no los usaban)
                        LiquidacionPorMetroCuadrado.objects.create(
                            liquidacion_general=lg,
                            area_m2=area,
                        )

                        # ── Inspector (opcional, si hay CIP en col 55) ──
                        # RH detail del delegado liquidación: dictamen, fechas, orden, mes, periodo
                        cip_raw = _normalize_cip(raw.get("CIP"))
                        liquidacion_delegado_fields = {
                            "periodo": _int(raw.get("PERIODO")),
                            "mes": _int(raw.get("MES")),
                            "nro_orden": _int(raw.get("NROORDEN")),
                            "fecha_presentacion": _parse_date(raw.get("FECHAPRES")),
                            "fecha_revision": _parse_date(raw.get("FECHAREVI")),
                            "dictamen_revision": _clean(raw.get("DICTAMEN")),
                        }
                        # limpia los None para no pisar defaults
                        liquidacion_delegado_fields = {k: v for k, v in liquidacion_delegado_fields.items() if v is not None and v != ""}

                        if cip_raw:
                            # Usa el servicio legacy que ya existe (intenta endpoint CIP primero)
                            perfil, _ = PerfilIngenieroCoreService().hydrate_perfil_from_cip(
                                cip_raw, dry_run=False
                            )
                            if perfil is None:
                                # Si el endpoint no devuelve nada, crea placeholder
                                perfil, _ = PerfilIngeniero.objects.get_or_create(
                                    cip=cip_raw,
                                    defaults={
                                        "nombres": f"CIP {cip_raw}",
                                        "apellido_paterno": "CIP",
                                        "apellido_materno": cip_raw,
                                    },
                                )
                            try:
                                esp_rev = EspecialidadRevision.objects.get(
                                    nombre="Ingeniería Civil"
                                )
                                deleg, _ = Delegado.objects.get_or_create(
                                    perfil_ingeniero=perfil,
                                )
                                DelegadoOperacion.objects.get_or_create(
                                    delegado=deleg,
                                    municipalidad=municipalidad,
                                    tipo_liquidacion=tipo_ms,
                                    defaults={"tipo": TipoDelegado.TITULAR},
                                )
                                LiquidacionDelegado.objects.update_or_create(
                                    liquidacion=lg,
                                    delegado=deleg,
                                    defaults={
                                        "especialidad_revision": esp_rev,
                                        **liquidacion_delegado_fields,
                                    },
                                )
                            except Exception:
                                pass

                        # ── Contacto (opcional, si TPERSONA o TFONO) ──
                        # TPERSONA / TFONO / TDNI ya leídos en vars _c
                        if nombres_c or telefono_c:
                            contacto = Contacto.objects.create(
                                nombres=nombres_c or "",
                                apellidos=apellidos_c or "",
                                telefono=telefono_c or "",
                                dni=tdni_c or "",
                            )
                            LiquidacionContacto.objects.create(
                                liquidacion=lg,
                                contacto=contacto,
                                principal=True,
                            )
                            # FK directo para el presenter
                            lg.contacto = contacto
                            lg.save(update_fields=["contacto", "updated_at"])

                        # ── Comprobante (opcional) ──
                        # tipo_comprobante viene de DOC col 29 (no hardcoded)
                        nro_fact_raw = raw.get("NROFACTURA") or ""
                        nro_fact_clean = _clean(nro_fact_raw)
                        if nro_fact_clean:
                            serie = None
                            numero = None
                            if "-" in nro_fact_clean:
                                parts = nro_fact_clean.split("-", 1)
                                serie = parts[0].strip() or None
                                numero = parts[1].strip() or None
                            else:
                                numero = nro_fact_clean
                            tipo_doc_str = _tipo_from_doc(raw.get("DOC"))
                            tipo_doc_enum = (
                                TipoComprobante[tipo_doc_str]
                                if tipo_doc_str in TipoComprobante.names
                                else TipoComprobante.FACTURA
                            )
                            if serie or numero:
                                LiquidacionComprobante.objects.create(
                                    liquidacion_general=lg,
                                    tipo_comprobante=tipo_doc,
                                    serie=serie,
                                    numero=numero,
                                    total=total_legacy,
                                    activo=True,
                                )

                counters["created"] += 1
                report_lines.append(
                    f"{nro}\t{nro}\tarea={area} rec={subtotal_recalc:.2f} excel={subtotal_legacy} diff={diff:.2f}\t{'SI' if apply else 'DRY'}\t{'creada' if apply else 'seria creada'}"
                )
            except Exception as exc:
                counters["errors"] += 1
                report_lines.append(f"{nro}\t{nro}\t{type(exc).__name__}: {exc}\tNO\terror")

        # ── Reporte ──
        report_path = out_dir / f"curar_ms_{run_id}.txt"
        report_path.write_text(
            "\n".join(["linea\tnro\tmotivo\tsubido\tresultado"] + report_lines),
            encoding="utf-8",
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"  Creadas: {counters['created']}"))
        self.stdout.write(f"  Reusadas: {counters['reused']}")
        if rechazar:
            self.stdout.write(self.style.WARNING(f"  Rechazadas (diff alta): {counters['rejected_diff']}"))
        self.stdout.write(self.style.WARNING(f"  Errores: {counters['errors']}"))
        self.stdout.write(f"  Reporte: {report_path}")
        self.stdout.write(f"\nFinalizado ({modo}).")
