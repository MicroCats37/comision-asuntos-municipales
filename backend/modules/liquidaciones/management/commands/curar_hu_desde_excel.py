"""
curar_hu_desde_excel — Cura datos de HU desde HU_ALL.csv contra la BD.

Lee `HU_ALL.csv` (61 cols, `;`, UTF-8) y reconcilia filas ya importadas contra
el modelo `LiquidacionDelegado` y `DetalleHonorarioDelegado`.

Equivalente HU del comando `curar_rh_desde_excel` (que es para EDIF/RH_EDIF.csv).
HU tiene un único slot por fila, no cuatro como EDIF.

Fases disponibles:
    comprobantes       — corrige tipo_comprobante a partir del DOC (col 29)
    liquidacion_delegado — corrige dictamen_revision, fechas, periodo, mes,
                          numero_rh (NROORDEN col 31)
    detalle_honorario  — corrige imp_bruto, aporte_codemu, fondo_comun,
                          neto_honorario, renta_cip

Read-only por default. Con `--apply` persiste los cambios en BD.

Outputs (CSVs):
    result/HU/curar_<phase>_<dryrun|apply>_<timestamp>.csv

Uso:
    # Simulación (no escribe BD):
    python manage.py curar_hu_desde_excel --phase all

    # Aplicar cambios reales:
    python manage.py curar_hu_desde_excel --phase all --apply
"""
from __future__ import annotations

import csv
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import (
    LiquidacionComprobante,
    TipoComprobante,
)
from modules.liquidaciones.domain.models.delegado import LiquidacionDelegado
from modules.finanzas.domain.models.detalle_honorario_delegado import (
    DetalleHonorarioDelegado,
)
from modules.usuarios.domain.models.perfil_ingeniero import PerfilIngeniero


# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_HU_PATH = Path(
    r"C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\backend\core_application\seeds\historico\HU_ALL.csv"
)
SEP = ";"
TOL_HONORARIO = Decimal("0.01")


def parse_int(s: Any) -> int | None:
    try:
        return int(str(s).strip())
    except Exception:
        return None


def parse_dec(s: Any) -> Decimal | None:
    if s is None:
        return None
    text = str(s).strip()
    if not text or text.upper() in ("NULL", "NONE", ""):
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def parse_date(s: Any) -> date | None:
    if not s:
        return None
    text = str(s).strip()
    if not text or text.upper() in ("NULL", "NONE", ""):
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def normalize_mes(raw: Any) -> str | None:
    text = str(raw).strip() if raw is not None else ""
    if not text or text.upper() in ("NULL", "NONE", ""):
        return None
    digits = "".join(c for c in text if c.isdigit())
    if not digits:
        return None
    return digits.zfill(2)[:2]


def normalize_periodo(raw: Any) -> str | None:
    text = str(raw).strip() if raw is not None else ""
    if not text or text.upper() in ("NULL", "NONE", ""):
        return None
    digits = "".join(c for c in text if c.isdigit())
    return digits[:4] if len(digits) >= 4 else None


def normalize_cip(raw: Any) -> str:
    text = str(raw).strip() if raw is not None else ""
    if not text or text.upper() in ("NULL", "NONE", ""):
        return ""
    digits = "".join(c for c in text if c.isdigit())
    if not digits:
        return ""
    return digits.zfill(6)[:6]


def normalize_nro_orden(raw: Any) -> str:
    """
    NROORDEN llega como '123-2024' o similar en el Excel. Para matchear con
    LiquidacionDelegado.numero_rh (CharField) conservamos solo dígitos.
    """
    text = str(raw).strip() if raw is not None else ""
    if not text or text.upper() in ("NULL", "NONE", ""):
        return ""
    digits = "".join(c for c in text if c.isdigit())
    return digits


def tipo_from_doc(raw: Any) -> str | None:
    """Mapea DOC (col 29) a TipoComprobante value."""
    if not raw:
        return None
    code = str(raw).strip().upper()
    if code in ("F", "FA", "FAC", "FACT"):
        return TipoComprobante.FACTURA
    if code in ("B", "BO", "BOL"):
        return TipoComprobante.BOLETA
    if code == "NC":
        return TipoComprobante.NOTA_CREDITO
    if code == "ND":
        return TipoComprobante.NOTA_DEBITO
    return None


# ── Command ───────────────────────────────────────────────────────────────────
class Command(BaseCommand):
    help = (
        "Cura datos de HU desde HU_ALL.csv. Fases: comprobantes | "
        "liquidacion_delegado | detalle_honorario | all. Read-only por default; usar --apply para escribir."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            dest="csv_path",
            type=str,
            default=str(DEFAULT_HU_PATH),
            help="Ruta al HU_ALL.csv (default: seeds/historico/HU_ALL.csv).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplicar cambios en BD (default: dry-run, solo escribe reporte CSV).",
        )
        parser.add_argument(
            "--phase",
            type=str,
            default="all",
            choices=["comprobantes", "liquidacion_delegado", "detalle_honorario", "all"],
            help="Fase específica o 'all'.",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Directorio destino para los reportes CSV. Default: result/HU/.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        apply = bool(options["apply"])
        phase = options["phase"]

        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"No existe el archivo: {csv_path}"))
            sys.exit(1)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        modo = "APPLY" if apply else "DRY-RUN"
        out_dir = Path(options["output"]) if options.get("output") else (
            Path(r"C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\result\HU")
        )
        out_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.NOTICE("=" * 72))
        self.stdout.write(self.style.NOTICE(f"curar_hu_desde_excel — fase: {phase} ({modo})"))
        self.stdout.write(self.style.NOTICE("=" * 72))
        self.stdout.write(f"  CSV:   {csv_path}")
        self.stdout.write(f"  Out:   {out_dir}")
        self.stdout.write("")

        self.stdout.write(self.style.HTTP_INFO("[1/3] Leyendo HU_ALL.csv..."))
        filas = self._leer(csv_path)
        nros_set = {f["nro"] for f in filas if f["nro"] is not None}
        self.stdout.write(f"  Filas leídas: {len(filas)} | NROs únicos: {len(nros_set)}")
        self.stdout.write("")

        if phase in ("comprobantes", "all"):
            self._fase_comprobantes(filas, apply, out_dir / f"curar_comprobantes_{'apply' if apply else 'dryrun'}_{ts}.csv")
        if phase in ("liquidacion_delegado", "all"):
            self._fase_liquidacion_delegado(
                filas, apply, out_dir / f"curar_liquidacion_delegado_{'apply' if apply else 'dryrun'}_{ts}.csv"
            )
        if phase in ("detalle_honorario", "all"):
            self._fase_detalle_honorario(
                filas, apply, out_dir / f"curar_detalle_honorario_{'apply' if apply else 'dryrun'}_{ts}.csv"
            )

        self.stdout.write(self.style.SUCCESS(f"\nFinalizado ({modo})."))

    # ── Lectura del CSV (mapeo a índices de HU_ALL.csv) ─────────────────────
    def _leer(self, path: Path) -> list[dict]:
        """
        Lee HU_ALL.csv con índice de columnas EXPLÍCITO para evitar
        acoplamiento al orden de columnas. Mismas claves semánticas que
        el script de edificaciones, adaptadas al dataset HU.
        """
        filas: list[dict] = []
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f, delimiter=SEP)
            header = next(reader, None)
            if header is None:
                return filas

            idx = {name: i for i, name in enumerate(header)}

            def _get(row, name):
                i = idx.get(name)
                return row[i] if i is not None and len(row) > i else None

            for n, row in enumerate(reader, start=2):
                nro_val = parse_int(_get(row, "NRO"))
                if nro_val is None:
                    continue
                filas.append({
                    "_linea": n,
                    "nro": nro_val,
                    "cip": _get(row, "CIP") or "",
                    "doc": _get(row, "DOC") or "",
                    "nro_factura": _get(row, "NROFACTURA") or "",
                    "mes": _get(row, "MES") or "",
                    "periodo": _get(row, "PERIODO") or "",
                    "dictamen": _get(row, "DICTAMEN") or "",
                    "fecha_pres": parse_date(_get(row, "FECHAPRES")),
                    "fecha_rev": parse_date(_get(row, "FECHAREVI")),
                    "nro_orden": _get(row, "NROORDEN") or "",   # → LiquidacionDelegado.numero_rh
                    "imp_bruto": parse_dec(_get(row, "IMPBRUTO")),
                    "apor_codemu": parse_dec(_get(row, "APORCODEMU")),
                    "fondo_comun": parse_dec(_get(row, "FONDOCOMUN")),
                    "neto_honorario": parse_dec(_get(row, "NETOHONORA")),
                    "renta_cip": parse_dec(_get(row, "RENTACIP")),
                })
        return filas

    # ── Helpers de matching ────────────────────────────────────────────────
    def _ld_map_by_nro(self, nros_set: set[int]) -> dict[tuple, dict]:
        """
        Construye índice {(nro, cip_normalized) -> dict} desde las
        LiquidacionDelegado existentes, joined con LiquidacionHabilitacionUrbana.

        HU tiene un único slot por fila, así que matchear por (nro, cip) es
        suficiente — no incluimos numero_rh en la clave porque ese campo puede
        contener valores antiguos (NROMEMO) que difieren del Excel (NROORDEN).
        Devuelve campos crudos para evitar N+1.
        """
        ld_qs = (
            LiquidacionDelegado.objects
            .filter(liquidacion__habilitacion_urbana__numero__in=nros_set)
            .values(
                "id",
                "liquidacion__habilitacion_urbana__numero",
                "delegado__perfil_ingeniero__cip",
                "dictamen_revision",
                "fecha_presentacion",
                "fecha_revision",
                "periodo",
                "mes",
                "numero_rh",
            )
        )
        bd: dict[tuple, dict] = {}
        for d in ld_qs:
            nro = d["liquidacion__habilitacion_urbana__numero"]
            cip = d["delegado__perfil_ingeniero__cip"] or ""
            cip_n = normalize_cip(cip)
            bd[(nro, cip_n)] = d
        return bd

    # ── Fase: Comprobantes (DOC -> tipo_comprobante) ───────────────────────
    def _fase_comprobantes(self, filas: list[dict], apply: bool, out_path: Path):
        self.stdout.write(self.style.HTTP_INFO("[2/3] FASE: Comprobantes (DOC -> tipo_comprobante)..."))

        # BD lookup: por (NRO, serie, numero) ── agrupamos por nro de filas Excel
        from collections import defaultdict
        excel_por_nro: dict[int, list[dict]] = defaultdict(list)
        for f in filas:
            excel_por_nro[f["nro"]].append(f)

        cambios: list[dict] = []
        skip_no_match = 0
        cambios_total = 0

        for nro, rows_nro in excel_por_nro.items():
            # Una fila puede tener varios slots de comprobante si nro_factura es único
            # pero en la práctica es 1 por NRO. Buscamos el/los comprobantes por
            # liquidacion del HU.
            lhu = (
                LiquidacionHabilitacionUrbana.objects
                .select_related("liquidacion")
                .filter(numero=nro)
                .first()
            )
            if not lhu or not lhu.liquidacion_id:
                skip_no_match += 1
                continue
            comps = list(
                LiquidacionComprobante.objects.filter(liquidacion_general_id=lhu.liquidacion_id, activo=True)
            )
            if not comps:
                continue

            # Cada fila Excel propone un doc_tipo; si varias filas comparten NRO,
            # usamos la primera con DOC clasificable.
            doc_tipo_per_row = None
            doc_raw = None
            for f in rows_nro:
                t = tipo_from_doc(f["doc"])
                if t:
                    doc_tipo_per_row = t
                    doc_raw = f["doc"]
                    break
            if not doc_tipo_per_row:
                continue

            for comp in comps:
                cur = comp.tipo_comprobante
                if cur != doc_tipo_per_row:
                    cambios.append({
                        "nro": nro,
                        "liquidacion_general_id": str(lhu.liquidacion_id),
                        "comprobante_id": str(comp.id),
                        "campo": "tipo_comprobante",
                        "old": cur or "(null)",
                        "new": doc_tipo_per_row,
                        "doc_raw": doc_raw,
                        "nro_factura": comp.numero or "",
                    })
                    if apply:
                        with transaction.atomic():
                            comp.tipo_comprobante = doc_tipo_per_row
                            comp.save()
                    cambios_total += 1

        self._escribir_reporte(
            out_path,
            ["nro", "liquidacion_general_id", "comprobante_id", "campo", "old", "new", "doc_raw", "nro_factura"],
            cambios,
        )
        self.stdout.write(self.style.SUCCESS(f"  Comprobantes a actualizar: {cambios_total}"))
        self.stdout.write(self.style.WARNING(f"  Sin match en BD (HU sin liquidacion): {skip_no_match}"))
        self.stdout.write(f"  Reporte: {out_path}")
        self.stdout.write("")

    # ── Fase: LiquidacionDelegado ──────────────────────────────────────────
    def _fase_liquidacion_delegado(self, filas: list[dict], apply: bool, out_path: Path):
        self.stdout.write(self.style.HTTP_INFO("[2/3] FASE: LiquidacionDelegado (dictamen, fechas, periodo, mes)..."))

        esperado: list[dict] = []
        skip_nro0_sin_datos = 0
        for f in filas:
            nro_orden = normalize_nro_orden(f["nro_orden"])
            if not nro_orden:
                continue
            mes_n = normalize_mes(f["mes"])
            periodo_n = normalize_periodo(f["periodo"])
            fecha_pres = f["fecha_pres"] if f["fecha_pres"] and f["fecha_pres"] != date(1900, 1, 1) else None
            fecha_rev = f["fecha_rev"] if f["fecha_rev"] and f["fecha_rev"] != date(1900, 1, 1) else None
            tiene_dato = bool(
                mes_n or periodo_n or f["dictamen"].strip() or fecha_pres or fecha_rev
            )
            if not tiene_dato:
                if (f["nro_orden"] or "").strip() == "0":
                    skip_nro0_sin_datos += 1
                continue
            esperado.append({
                "nro": f["nro"],
                "cip": normalize_cip(f["cip"]),
                "nro_orden": nro_orden,
                "mes": mes_n,
                "periodo": periodo_n,
                "dictamen": f["dictamen"].strip(),
                "fecha_pres": fecha_pres,
                "fecha_rev": fecha_rev,
            })

        self.stdout.write(self.style.WARNING(f"  Filas con NROORDEN=0 y sin datos: {skip_nro0_sin_datos}"))
        self.stdout.write(f"  Esperado (con datos): {len(esperado)}")

        nros_set = {e["nro"] for e in esperado}
        bd_por_key = self._ld_map_by_nro(nros_set)
        self.stdout.write(f"  Pares (NRO, CIP, NROORDEN) en BD: {len(bd_por_key)}")

        cambios: list[dict] = []
        skip_no_match = 0
        for e in esperado:
            key = (e["nro"], e["cip"])
            ld = bd_por_key.get(key)
            if not ld:
                skip_no_match += 1
                continue
            updates: dict[str, tuple[Any, Any]] = {}
            if e["mes"] and str(e["mes"]) != str(ld["mes"] or ""):
                updates["mes"] = (ld["mes"] or "", e["mes"])
            if e["periodo"] and str(e["periodo"]) != str(ld["periodo"] or ""):
                updates["periodo"] = (ld["periodo"] or "", e["periodo"])
            if e["dictamen"] and e["dictamen"] != (ld["dictamen_revision"] or ""):
                updates["dictamen_revision"] = (ld["dictamen_revision"] or "", e["dictamen"])
            if e["fecha_pres"] and e["fecha_pres"] != ld["fecha_presentacion"]:
                updates["fecha_presentacion"] = (
                    str(ld["fecha_presentacion"]) if ld["fecha_presentacion"] else "",
                    str(e["fecha_pres"]),
                )
            if e["fecha_rev"] and e["fecha_rev"] != ld["fecha_revision"]:
                updates["fecha_revision"] = (
                    str(ld["fecha_revision"]) if ld["fecha_revision"] else "",
                    str(e["fecha_rev"]),
                )

            if updates:
                cambios.append({
                    "nro": e["nro"], "cip": e["cip"], "nro_orden": e["nro_orden"],
                    "campo": "; ".join(updates.keys()),
                    "old": "; ".join(f"{k}={v[0]!r}" for k, v in updates.items()),
                    "new": "; ".join(f"{k}={v[1]!r}" for k, v in updates.items()),
                })
                if apply:
                    with transaction.atomic():
                        ld_obj = LiquidacionDelegado.objects.get(id=ld["id"])
                        for campo, (_, new_val) in updates.items():
                            setattr(ld_obj, campo, new_val)
                        ld_obj.save()

        self._escribir_reporte(
            out_path,
            ["nro", "cip", "nro_orden", "campo", "old", "new"],
            cambios,
        )
        self.stdout.write(self.style.SUCCESS(f"  LiquidacionDelegado a actualizar: {len(cambios)}"))
        self.stdout.write(self.style.WARNING(f"  Sin match en BD: {skip_no_match}"))
        self.stdout.write(f"  Reporte: {out_path}")
        self.stdout.write("")

    # ── Fase: DetalleHonorarioDelegado ─────────────────────────────────────
    def _fase_detalle_honorario(self, filas: list[dict], apply: bool, out_path: Path):
        self.stdout.write(self.style.HTTP_INFO("[3/3] FASE: DetalleHonorarioDelegado (imp, aporte, fondo, neto, renta)..."))

        esperado: list[dict] = []
        for f in filas:
            nro_orden = normalize_nro_orden(f["nro_orden"])
            if not nro_orden:
                continue
            imp = f["imp_bruto"] or Decimal("0")
            apor = f["apor_codemu"] or Decimal("0")
            fond = f["fondo_comun"] or Decimal("0")
            neto = f["neto_honorario"] or Decimal("0")
            rent = f["renta_cip"] or Decimal("0")
            if not any([imp, apor, fond, neto, rent]):
                continue
            esperado.append({
                "nro": f["nro"],
                "cip": normalize_cip(f["cip"]),
                "nro_orden": nro_orden,
                "imp_bruto": imp,
                "aporte_codemu": apor,
                "fondo_comun": fond,
                "neto_honorario": neto,
                "renta_cip": rent,
            })
        self.stdout.write(f"  Esperado (con importes): {len(esperado)}")

        nros_set = {e["nro"] for e in esperado}
        detalles_qs = (
            DetalleHonorarioDelegado.objects
            .filter(liquidacion_delegado__liquidacion__habilitacion_urbana__numero__in=nros_set)
            .values(
                "id",
                "liquidacion_delegado__liquidacion__habilitacion_urbana__numero",
                "liquidacion_delegado__delegado__perfil_ingeniero__cip",
                "liquidacion_delegado__numero_rh",
                "imp_bruto", "aporte_codemu", "fondo_comun", "neto_honorario", "renta_cip",
            )
        )
        bd: dict[tuple, dict] = {}
        for d in detalles_qs:
            nro = d["liquidacion_delegado__liquidacion__habilitacion_urbana__numero"]
            cip = d["liquidacion_delegado__delegado__perfil_ingeniero__cip"] or ""
            cip_n = normalize_cip(cip)
            bd[(nro, cip_n)] = d
        self.stdout.write(f"  Pares (NRO, CIP) en BD: {len(bd)}")

        campos_map = ["imp_bruto", "aporte_codemu", "fondo_comun", "neto_honorario", "renta_cip"]
        cambios: list[dict] = []
        skip_no_match = 0
        for e in esperado:
            key = (e["nro"], e["cip"])
            b = bd.get(key)
            if not b:
                skip_no_match += 1
                continue
            updates: dict[str, tuple[Decimal, Decimal]] = {}
            for c in campos_map:
                exp = e[c]
                cur = b[c] or Decimal("0")
                if exp == 0 and cur == 0:
                    continue
                if abs(exp - cur) > TOL_HONORARIO:
                    updates[c] = (cur, exp)
            if updates:
                cambios.append({
                    "nro": e["nro"], "cip": e["cip"], "nro_orden": e["nro_orden"],
                    "campo": "; ".join(updates.keys()),
                    "old": "; ".join(f"{k}={v[0]}" for k, v in updates.items()),
                    "new": "; ".join(f"{k}={v[1]}" for k, v in updates.items()),
                })
                if apply:
                    with transaction.atomic():
                        dh = DetalleHonorarioDelegado.objects.get(id=b["id"])
                        for c, (_, new_val) in updates.items():
                            setattr(dh, c, new_val)
                        dh.save()

        self._escribir_reporte(
            out_path,
            ["nro", "cip", "nro_orden", "campo", "old", "new"],
            cambios,
        )
        self.stdout.write(self.style.SUCCESS(f"  DetalleHonorarioDelegado a actualizar: {len(cambios)}"))
        self.stdout.write(self.style.WARNING(f"  Sin match en BD: {skip_no_match}"))
        self.stdout.write(f"  Reporte: {out_path}")
        self.stdout.write("")

    def _escribir_reporte(self, path: Path, headers: list[str], rows: list[dict]):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=SEP)
            writer.writeheader()
            for r in rows:
                writer.writerow({h: r.get(h, "") for h in headers})
