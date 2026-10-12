"""
curar_rh_desde_excel — Cura datos de RH desde RH_EDIF.csv contra BD.
READ-ONLY por default. Con --apply aplica los cambios.
Fases: comprobantes | liquidacion_delegado | all
"""
import csv
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import LiquidacionEdificacion
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.comprobante import LiquidacionComprobante
from modules.liquidaciones.domain.models.delegado import Delegado, DelegadoOperacion, LiquidacionDelegado
from modules.finanzas.domain.models.detalle_honorario_delegado import DetalleHonorarioDelegado
from modules.entidades.domain.models.municipalidad import Municipalidad
from modules.liquidaciones.domain.models.tipo_liquidacion import TipoLiquidacion
from modules.usuarios.domain.models.perfil_ingeniero import EspecialidadRevision, PerfilIngeniero
from .import_legacy_edificaciones import (
    _ensure_perfil_ingeniero_by_cip,
    _ensure_delegado_for_perfil,
    _ensure_delegado_operacion,
    _ensure_liquidacion_delegado,
    _ensure_detalle_honorario_delegado,
)

DEFAULT_RH_PATH = Path(r"C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\backend\core_application\seeds\historico\RH_EDIF.csv")
SEP = ";"
TOL_HONORARIO = Decimal("0.01")
MAP_TIPO = {"BOL": "BOLETA", "FAC": "FACTURA", "BOLETA": "BOLETA", "FACTURA": "FACTURA"}
ESPECIALIDAD_ALIAS = {
    "ESTRUCTURAS": "Ingeniería Civil",
    "INST. SANITARIAS": "Ingeniería Sanitaria",
    "INST. MECANICO ELECTRICAS": "Ingeniería Eléctrica y Mecánica Eléctrica",
    "INST. ELECTRICAS": "Ingeniería Eléctrica y Mecánica Eléctrica",
    "INST. ELECTRONICAS": "Ingeniería Electrónica",
}
ESPECIALIDAD_TODAS = "TODAS"
MES_MAP = {
    "ENERO": "01", "FEBRERO": "02", "MARZO": "03", "ABRIL": "04", "MAYO": "05", "JUNIO": "06",
    "JULIO": "07", "AGOSTO": "08", "SEPTIEMBRE": "09", "OCTUBRE": "10", "NOVIEMBRE": "11", "DICIEMBRE": "12",
}


def parse_int(s):
    try:
        return int(str(s).strip())
    except Exception:
        return None


def parse_dec(s):
    if not s:
        return Decimal("0")
    s = str(s).strip()
    if s.upper() in ("NULL", "NONE", ""):
        return Decimal("0")
    try:
        return Decimal(s)
    except Exception:
        return Decimal("0")


def split_factura(raw):
    s = str(raw).strip()
    if not s or s.upper() in ("NULL", "NONE", ""):
        return None, None
    s = s.replace(" ", "")
    if "-" in s:
        partes = s.split("-", 1)
        return (partes[0].strip() or None, partes[1].strip() or None)
    return None, s


def normalize_mes(raw):
    s = str(raw).strip()
    if not s or s.upper() in ("NULL", "NONE", ""):
        return None
    s = s.upper()
    for nombre, num in MES_MAP.items():
        if nombre in s:
            return num
    digits = "".join(c for c in s if c.isdigit())
    if digits:
        return digits.zfill(2)[:2]
    return None


def normalize_periodo(raw):
    s = str(raw).strip()
    if not s or s.upper() in ("NULL", "NONE", ""):
        return None
    digits = "".join(c for c in s if c.isdigit())
    return digits[:4] if len(digits) >= 4 else None


def normalize_nro_rh(raw):
    s = str(raw).strip()
    if not s or s.upper() in ("NULL", "NONE", ""):
        return None
    digits = "".join(c for c in s if c.isdigit())
    return digits if digits else None


def parse_date(s):
    if not s:
        return None
    s = str(s).strip()
    if s.upper() in ("NULL", "NONE", ""):
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


class Command(BaseCommand):
    help = "Cura datos de RH desde RH_EDIF.csv. Fases: comprobantes | liquidacion_delegado | all"

    def add_arguments(self, parser):
        parser.add_argument("--rh-csv", type=str, default=str(DEFAULT_RH_PATH))
        parser.add_argument(
            "--edif-wide",
            type=str,
            default=r"C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\backend\core_application\seeds\historico\EDIF_ALL.csv",
            help="Path al EDIF_ALL.csv (wide format) para fase validar_fks",
        )
        parser.add_argument("--apply", action="store_true", help="Aplicar cambios (default: dry-run)")
        parser.add_argument(
            "--phase",
            type=str,
            default="comprobantes",
            choices=["comprobantes", "liquidacion_delegado", "detalle_honorario", "validar_fks", "especialidad", "crear_faltantes", "corregir_especialidad", "consolidar_duplicados", "corregir_detalle", "all"],
        )
        parser.add_argument("--output", type=str, default=None)

    def handle(self, *args, **options):
        rh_path = Path(options["rh_csv"])
        apply = options["apply"]
        phase = options["phase"]
        out_path = Path(options["output"]) if options["output"] else None
        ts = self._now_ts()
        if out_path is None:
            suffix = f"{phase}_{'apply' if apply else 'dryrun'}_{ts}.csv"
            out_path = Path(r"C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\result\EDIF") / f"curar_{suffix}"
        self.params = options

        self.stdout.write(self.style.NOTICE("=" * 70))
        self.stdout.write(self.style.NOTICE(f"curar_rh_desde_excel — fase: {phase} ({'APPLY' if apply else 'DRY-RUN'})"))
        self.stdout.write(self.style.NOTICE("=" * 70))
        self.stdout.write(f"  RH CSV: {rh_path}")
        self.stdout.write(f"  Output: {out_path}")
        self.stdout.write("")

        self.stdout.write(self.style.HTTP_INFO("[1/4] Leyendo RH_EDIF.csv..."))
        filas = self._leer(rh_path)
        nros_set = {f["nro"] for f in filas}
        self.stdout.write(f"  Filas: {len(filas)} | NROs unicos: {len(nros_set)}")
        self.stdout.write("")

        if phase in ("comprobantes", "all"):
            self._fase_comprobantes(filas, nros_set, apply, out_path.with_name(out_path.stem + "_comprobantes.csv"))

        if phase in ("liquidacion_delegado", "all"):
            self._fase_liquidacion_delegado(filas, nros_set, apply, out_path.with_name(out_path.stem + "_liquidacion_delegado.csv"))

        if phase in ("detalle_honorario", "all"):
            self._fase_detalle_honorario(filas, nros_set, apply, out_path.with_name(out_path.stem + "_detalle_honorario.csv"))

        if phase in ("validar_fks", "all"):
            self._fase_validar_fks(options["edif_wide"], nros_set, out_path.with_name(out_path.stem + "_validar_fks.csv"))

        if phase in ("especialidad", "all"):
            self._fase_especialidad(filas, apply, out_path.with_name(out_path.stem + "_especialidad.csv"))

        if phase in ("crear_faltantes", "all"):
            self._fase_crear_faltantes(options["edif_wide"], filas, apply, out_path.with_name(out_path.stem + "_crear_faltantes.csv"))

        if phase in ("corregir_especialidad", "all"):
            self._fase_corregir_especialidad(filas, apply, out_path.with_name(out_path.stem + "_corregir_especialidad.csv"))

        if phase in ("consolidar_duplicados", "all"):
            self._fase_consolidar_duplicados(filas, apply, out_path.with_name(out_path.stem + "_consolidar_duplicados.csv"))

        if phase in ("corregir_detalle", "all"):
            self._fase_corregir_detalle_honorario(filas, apply, out_path.with_name(out_path.stem + "_corregir_detalle.csv"))

    def _leer(self, rh_path):
        filas = []
        with rh_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=SEP)
            for r in reader:
                nro = parse_int(r.get("NRO"))
                if nro is None:
                    continue
                filas.append({
                    "nro": nro,
                    "cip": r.get("CIP", "").strip(),
                    "doc": r.get("DOC", "").strip(),
                    "nro_factura": r.get("NROFACTURA", "").strip(),
                    "mes": r.get("MES", "").strip(),
                    "periodo": r.get("PERIODO", "").strip(),
                    "dictamen": r.get("DICTAMEN", "").strip(),
                    "fecha_pres": parse_date(r.get("FECHAPRES", "")),
                    "fecha_rev": parse_date(r.get("FECHAREVI", "")),
                    "nro_orden": r.get("NROORDEN", "").strip(),
                    "impbruto": r.get("IMPBRUTO", ""),
                    "aporcodemu": r.get("APORCODEMU", ""),
                    "fondocomun": r.get("FONDOCOMUN", ""),
                    "honorario": r.get("HONORARIO", ""),
                    "rentacip": r.get("RENTACIP", ""),
                    "netohonora": r.get("NETOHONORA", ""),
                    "especialidad": r.get("ESPECIALIDAD", "").strip(),
                })
        return filas

    def _fase_comprobantes(self, filas, nros_set, apply, out_path):
        self.stdout.write(self.style.HTTP_INFO("[2/4] FASE: Comprobantes (por NRO)..."))
        por_nro = {}
        for f in filas:
            nro = f["nro"]
            if nro not in por_nro:
                por_nro[nro] = {"doc": f["doc"], "nro_factura": f["nro_factura"]}
        self.stdout.write(f"  NROs unicos: {len(por_nro)}")

        validados, inconsistentes = {}, {}
        for nro, data in por_nro.items():
            if not (data["doc"] or data["nro_factura"]):
                continue
            validados[nro] = data
        self.stdout.write(f"  NROs con datos: {len(validados)}")

        nro_to_lg = {e["numero"]: e["liquidacion_id"] for e in LiquidacionEdificacion.objects.filter(numero__in=set(validados.keys())).values("numero", "liquidacion_id")}
        self.stdout.write(f"  Liquidaciones en BD: {len(nro_to_lg)}")

        cambios = []
        skip_no_comp = []
        for nro, data in sorted(validados.items()):
            if nro not in nro_to_lg:
                continue
            comp = LiquidacionComprobante.objects.filter(liquidacion_general_id=nro_to_lg[nro], activo=True).first()
            if not comp:
                skip_no_comp.append(nro)
                continue
            doc, nro_factura = data["doc"], data["nro_factura"]
            serie_new, numero_new = split_factura(nro_factura)
            tipo_new = MAP_TIPO.get(doc.upper()) if doc else None
            serie_old, numero_old, tipo_old = comp.serie or "", comp.numero or "", comp.tipo_comprobante or ""
            cambia = (tipo_new and tipo_new != tipo_old) or (serie_new and serie_new != serie_old) or (numero_new and numero_new != numero_old)
            if cambia and apply:
                with transaction.atomic():
                    if tipo_new and tipo_new != tipo_old:
                        comp.tipo_comprobante = tipo_new
                    if serie_new and serie_new != serie_old:
                        comp.serie = serie_new
                    if numero_new and numero_new != numero_old:
                        comp.numero = numero_new
                    comp.save()
            cambios.append({
                "nro": nro, "doc": doc, "nro_factura": nro_factura,
                "tipo_old": tipo_old, "serie_old": serie_old, "numero_old": numero_old,
                "tipo_new": tipo_new or "", "serie_new": serie_new or "", "numero_new": numero_new or "",
                "cambia": cambia,
            })
        self._escribir_reporte(out_path, ["nro", "doc", "nro_factura", "tipo_old", "serie_old", "numero_old", "tipo_new", "serie_new", "numero_new", "cambia"], cambios)
        n_cambios = sum(1 for c in cambios if c["cambia"])
        self.stdout.write(self.style.SUCCESS(f"  Comprobantes actualizados: {n_cambios}"))
        self.stdout.write(self.style.WARNING(f"  Sin comprobante activo: {len(skip_no_comp)}"))
        self.stdout.write(f"  Reporte: {out_path}")
        self.stdout.write("")

    def _fase_liquidacion_delegado(self, filas, nros_set, apply, out_path):
        self.stdout.write(self.style.HTTP_INFO("[2/4] FASE: LiquidacionDelegado (por NRO+CIP+NROORDEN)..."))
        esperado = []
        skip_nro0_sin_datos = 0
        for f in filas:
            nro_orden_raw = f["nro_orden"].strip()
            nro_orden_norm = normalize_nro_rh(nro_orden_raw)
            if not nro_orden_norm:
                continue
            mes_n = normalize_mes(f["mes"])
            periodo_n = normalize_periodo(f["periodo"])
            tiene_dato = bool(mes_n or periodo_n or f["dictamen"] or f["fecha_pres"] or f["fecha_rev"])
            if not tiene_dato:
                if nro_orden_raw == "0":
                    skip_nro0_sin_datos += 1
                continue
            esperado.append({
                "nro": f["nro"],
                "cip": f["cip"],
                "nro_orden": nro_orden_norm,
                "mes": mes_n or "",
                "periodo": periodo_n or "",
                "dictamen": f["dictamen"],
                "fecha_pres": f["fecha_pres"] if f["fecha_pres"] and f["fecha_pres"] != date(1900, 1, 1) else None,
                "fecha_rev": f["fecha_rev"] if f["fecha_rev"] and f["fecha_rev"] != date(1900, 1, 1) else None,
            })
        self.stdout.write(self.style.WARNING(f"  BLOQUEADO NROORDEN=0 sin campos actualizables: {skip_nro0_sin_datos}"))
        self.stdout.write(f"  Registros con datos normalizados: {len(esperado)}")

        edifs = {e["numero"]: e["liquidacion_id"] for e in LiquidacionEdificacion.objects.filter(numero__in=nros_set).values("numero", "liquidacion_id")}
        detalles = DetalleHonorarioDelegado.objects.filter(liquidacion_delegado__liquidacion_id__in=set(edifs.values())).values(
            "id", "liquidacion_delegado_id", "liquidacion_delegado__liquidacion__edificaciones__numero",
            "liquidacion_delegado__delegado__perfil_ingeniero__cip", "liquidacion_delegado__numero_rh"
        )
        bd_por_key = {}
        for d in detalles:
            nro = d["liquidacion_delegado__liquidacion__edificaciones__numero"]
            cip = d["liquidacion_delegado__delegado__perfil_ingeniero__cip"] or ""
            cip_n = cip.strip().zfill(6) if cip else ""
            nro_orden = (d["liquidacion_delegado__numero_rh"] or "").strip()
            bd_por_key[(nro, cip_n, nro_orden)] = d["liquidacion_delegado_id"]
        self.stdout.write(f"  Pares (NRO, CIP, NROORDEN) en BD: {len(bd_por_key)}")

        cambios = []
        skip_no_match = 0
        for e in esperado:
            cip_n = e["cip"].strip().zfill(6) if e["cip"] else ""
            key = (e["nro"], cip_n, e["nro_orden"])
            ld_id = bd_por_key.get(key)
            if not ld_id:
                skip_no_match += 1
                continue
            ld = LiquidacionDelegado.objects.get(id=ld_id)
            cambios_dict = {
                "nro": e["nro"], "cip": cip_n, "nro_orden": e["nro_orden"],
                "campo": "", "old": "", "new": "", "cambia": False,
            }
            updates = {}
            if e["mes"] and e["mes"] != (ld.mes or ""):
                updates["mes"] = (ld.mes or "", e["mes"])
            if e["periodo"] and e["periodo"] != (ld.periodo or ""):
                updates["periodo"] = (ld.periodo or "", e["periodo"])
            if e["dictamen"] and e["dictamen"] != (ld.dictamen_revision or ""):
                updates["dictamen_revision"] = (ld.dictamen_revision or "", e["dictamen"])
            if e["fecha_pres"] and e["fecha_pres"] != ld.fecha_presentacion:
                updates["fecha_presentacion"] = (str(ld.fecha_presentacion) if ld.fecha_presentacion else "", str(e["fecha_pres"]))
            if e["fecha_rev"] and e["fecha_rev"] != ld.fecha_revision:
                updates["fecha_revision"] = (str(ld.fecha_revision) if ld.fecha_revision else "", str(e["fecha_rev"]))
            if updates:
                cambios_dict["cambia"] = True
                if apply:
                    with transaction.atomic():
                        for campo, (old, new) in updates.items():
                            setattr(ld, campo, new if campo not in ("fecha_presentacion", "fecha_revision") else new)
                        ld.save()
                cambios.append({
                    "nro": e["nro"], "cip": cip_n, "nro_orden": e["nro_orden"],
                    "campo": "; ".join(updates.keys()),
                    "old": "; ".join(f"{k}={v[0]}" for k, v in updates.items()),
                    "new": "; ".join(f"{k}={v[1]}" for k, v in updates.items()),
                    "cambia": True,
                })
        self._escribir_reporte(out_path, ["nro", "cip", "nro_orden", "campo", "old", "new", "cambia"], cambios)
        n_cambios = sum(1 for c in cambios if c["cambia"])
        self.stdout.write(self.style.SUCCESS(f"  Delegados actualizados: {n_cambios}"))
        self.stdout.write(self.style.WARNING(f"  Sin match en BD: {skip_no_match}"))
        self.stdout.write(f"  Reporte: {out_path}")
        self.stdout.write("")

    def _fase_detalle_honorario(self, filas, nros_set, apply, out_path):
        self.stdout.write(self.style.HTTP_INFO("[2/4] FASE: DetalleHonorarioDelegado (por NRO+CIP+NROORDEN)..."))
        esperado = []
        for f in filas:
            nro_orden_norm = normalize_nro_rh(f["nro_orden"].strip())
            if not nro_orden_norm:
                continue
            imp = parse_dec(f.get("impbruto", ""))
            apor = parse_dec(f.get("aporcodemu", ""))
            fond = parse_dec(f.get("fondocomun", ""))
            hon = parse_dec(f.get("honorario", ""))
            rent = parse_dec(f.get("rentacip", ""))
            neto = parse_dec(f.get("netohonora", ""))
            if not any([imp, apor, fond, hon, rent, neto]):
                continue
            esperado.append({
                "nro": f["nro"],
                "cip": f["cip"],
                "nro_orden": nro_orden_norm,
                "imp_bruto": imp,
                "aporte_codemu": apor,
                "fondo_comun": fond,
                "neto_honorario": hon,
                "renta_cip": rent,
            })
        self.stdout.write(f"  Registros con importes: {len(esperado)}")

        edifs = {e["numero"]: e["liquidacion_id"] for e in LiquidacionEdificacion.objects.filter(numero__in=nros_set).values("numero", "liquidacion_id")}
        detalles = DetalleHonorarioDelegado.objects.filter(liquidacion_delegado__liquidacion_id__in=set(edifs.values())).values(
            "id", "liquidacion_delegado__liquidacion__edificaciones__numero",
            "liquidacion_delegado__delegado__perfil_ingeniero__cip", "liquidacion_delegado__numero_rh",
            "imp_bruto", "aporte_codemu", "fondo_comun", "neto_honorario", "renta_cip",
        )
        bd_por_key = {}
        for d in detalles:
            nro = d["liquidacion_delegado__liquidacion__edificaciones__numero"]
            cip = d["liquidacion_delegado__delegado__perfil_ingeniero__cip"] or ""
            cip_n = cip.strip().zfill(6) if cip else ""
            nro_orden = (d["liquidacion_delegado__numero_rh"] or "").strip()
            bd_por_key[(nro, cip_n, nro_orden)] = {
                "id": d["id"],
                "imp_bruto": d["imp_bruto"] or Decimal("0"),
                "aporte_codemu": d["aporte_codemu"] or Decimal("0"),
                "fondo_comun": d["fondo_comun"] or Decimal("0"),
                "neto_honorario": d["neto_honorario"] or Decimal("0"),
                "renta_cip": d["renta_cip"] or Decimal("0"),
            }
        self.stdout.write(f"  Pares (NRO, CIP, NROORDEN) en BD: {len(bd_por_key)}")

        cambios = []
        skip_no_match = 0
        campos_map = ["imp_bruto", "aporte_codemu", "fondo_comun", "neto_honorario", "renta_cip"]
        for e in esperado:
            cip_n = e["cip"].strip().zfill(6) if e["cip"] else ""
            key = (e["nro"], cip_n, e["nro_orden"])
            b = bd_por_key.get(key)
            if not b:
                skip_no_match += 1
                continue
            updates = {}
            for c in campos_map:
                exp = e[c]
                if exp == 0:
                    continue
                if abs(exp - b[c]) > TOL_HONORARIO:
                    updates[c] = (b[c], exp)
            if updates:
                if apply:
                    with transaction.atomic():
                        dh = DetalleHonorarioDelegado.objects.get(id=b["id"])
                        for c, (old, new) in updates.items():
                            setattr(dh, c, new)
                        dh.save()
                cambios.append({
                    "nro": e["nro"], "cip": cip_n, "nro_orden": e["nro_orden"],
                    "campo": "; ".join(updates.keys()),
                    "old": "; ".join(f"{k}={v[0]}" for k, v in updates.items()),
                    "new": "; ".join(f"{k}={v[1]}" for k, v in updates.items()),
                    "cambia": True,
                })
        self._escribir_reporte(out_path, ["nro", "cip", "nro_orden", "campo", "old", "new", "cambia"], cambios)
        n_cambios = sum(1 for c in cambios if c["cambia"])
        self.stdout.write(self.style.SUCCESS(f"  Detalles actualizados: {n_cambios}"))
        self.stdout.write(self.style.WARNING(f"  Sin match en BD: {skip_no_match}"))
        self.stdout.write(f"  Reporte: {out_path}")
        self.stdout.write("")

    def _escribir_reporte(self, out_path, header, rows):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8-sig", newline="") as fout:
            w = csv.writer(fout, delimiter=SEP)
            w.writerow(header)
            for r in rows:
                w.writerow([r.get(h, "") for h in header])

    def _fase_validar_fks(self, edif_wide_path, nros_set, out_path):
        self.stdout.write(self.style.HTTP_INFO("[2/4] FASE: Validar FKs (delegado, especialidad, delegado_operacion)..."))
        edif_path = Path(edif_wide_path)
        if not edif_path.exists():
            self.stdout.write(self.style.ERROR(f"  No existe: {edif_path}"))
            return
        excel_por_nro = {}
        with edif_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            for r in reader:
                try:
                    nro = int(r.get("ID") or r.get("NRO") or 0)
                except Exception:
                    continue
                if not nro or nro not in nros_set:
                    continue
                cips = []
                for slot in range(1, 5):
                    cip = (r.get(f"CIP{slot}") or "").strip()
                    if cip:
                        cips.append((slot, cip.zfill(6)))
                excel_por_nro[nro] = {
                    "codpago": (r.get("CODPAGO") or "").strip(),
                    "especialidad": (r.get("ESPECIALIDAD") or "").strip(),
                    "cips": cips,
                }
        self.stdout.write(f"  NROs en EDIF_ALL con CODPAGO/ESPECIALIDAD: {len(excel_por_nro)}")

        edifs = {e["numero"]: e["liquidacion_id"] for e in LiquidacionEdificacion.objects.filter(numero__in=set(excel_por_nro.keys())).values("numero", "liquidacion_id")}
        lds = LiquidacionDelegado.objects.filter(liquidacion_id__in=set(edifs.values())).select_related(
            "delegado__perfil_ingeniero", "especialidad_revision",
            "delegado_operacion__municipalidad", "delegado_operacion__especialidad_revision",
        ).values(
            "liquidacion__edificaciones__numero",
            "delegado__perfil_ingeniero__cip",
            "delegado_operacion__municipalidad__codigo",
            "especialidad_revision__nombre",
            "delegado_operacion__especialidad_revision__nombre",
            "delegado_operacion__tipo_liquidacion__codigo",
        )
        bd_por_nro_cip = {}
        for ld in lds:
            nro = ld["liquidacion__edificaciones__numero"]
            cip = (ld["delegado__perfil_ingeniero__cip"] or "").zfill(6) if ld["delegado__perfil_ingeniero__cip"] else ""
            if cip:
                bd_por_nro_cip[(nro, cip)] = {
                    "muni_codigo": (ld["delegado_operacion__municipalidad__codigo"] or "").strip() if ld["delegado_operacion__municipalidad__codigo"] else "",
                    "esp_nombre": (ld["especialidad_revision__nombre"] or "").strip() if ld["especialidad_revision__nombre"] else "",
                    "esp_op_nombre": (ld["delegado_operacion__especialidad_revision__nombre"] or "").strip() if ld["delegado_operacion__especialidad_revision__nombre"] else "",
                }
        self.stdout.write(f"  Pares (NRO, CIP) en BD: {len(bd_por_nro_cip)}")

        resultados = []
        ok = 0
        for nro, data in excel_por_nro.items():
            esp_excel = data["especialidad"]
            muni_excel = data["codpago"]
            for slot, cip in data["cips"]:
                bd = bd_por_nro_cip.get((nro, cip))
                if not bd:
                    continue
                problemas = []
                if muni_excel and bd["muni_codigo"] and muni_excel.strip().upper() != bd["muni_codigo"].strip().upper():
                    problemas.append(f"CODPAGO: excel={muni_excel!r} bd={bd['muni_codigo']!r}")
                if esp_excel and bd["esp_nombre"] and not self._especialidad_match(esp_excel, bd["esp_nombre"]):
                    problemas.append(f"ESPECIALIDAD: excel={esp_excel!r} bd={bd['esp_nombre']!r}")
                if esp_excel and bd["esp_op_nombre"] and not self._especialidad_match(esp_excel, bd["esp_op_nombre"]):
                    problemas.append(f"ESP_OP: excel={esp_excel!r} bd={bd['esp_op_nombre']!r}")
                if problemas:
                    resultados.append({"nro": nro, "cip": cip, "slot": slot, "problemas": "; ".join(problemas), "estado": "DIFF"})
                else:
                    ok += 1
        with out_path.open("w", encoding="utf-8-sig", newline="") as fout:
            w = csv.writer(fout, delimiter=SEP)
            w.writerow(["nro", "cip", "slot", "estado", "problemas"])
            for r in resultados:
                w.writerow([r["nro"], r["cip"], r["slot"], r["estado"], r["problemas"]])
        self.stdout.write(f"  Pares validados OK: {ok}")
        self.stdout.write(f"  Pares con DIFF: {len(resultados)}")
        self.stdout.write(f"  Reporte: {out_path}")
        self.stdout.write("")

    def _especialidad_match(self, excel, bd_nombre):
        import unicodedata
        def strip_accents(s):
            return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        e = strip_accents(excel.upper().strip())
        b = strip_accents(bd_nombre.upper().strip())
        if not e or not b:
            return True
        if e == "TODAS":
            return True
        if e in b or b in e:
            return True
        aliases = {
            "ESTRUCTURAS": "CIVIL",
            "INST. MECANICO ELECTRICAS": "ELECTRICA",
            "INST. SANITARIAS": "SANITARIA",
            "INST. ELECTRONICAS": "ELECTRONICA",
        }
        e_norm = aliases.get(e, e)
        b_norm = aliases.get(b, b)
        return e_norm in b_norm or b_norm in e_norm

    def _now_ts(self):
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _fase_corregir_detalle_honorario(self, filas, apply, out_path):
        self.stdout.write(self.style.HTTP_INFO("[2/4] FASE: Corregir DetalleHonorarioDelegado (5 importes) vs Excel..."))
        excel_data = {}
        for r in filas:
            try: nro = int(r.get("NRO", 0))
            except: continue
            cip = r.get("CIP", "").strip().zfill(6)
            nroorden = r.get("NROORDEN", "").strip()
            if not cip or cip == "000000":
                continue
            def fld(v):
                if not v: return Decimal("0")
                s = str(v).strip()
                if s.upper() in ("NULL", "NONE", ""): return Decimal("0")
                try: return Decimal(s)
                except: return Decimal("0")
            imp = fld(r.get("IMPBRUTO"))
            apor = fld(r.get("APORCODEMU"))
            fond = fld(r.get("FONDOCOMUN"))
            hon = fld(r.get("HONORARIO"))
            rent = fld(r.get("RENTACIP"))
            if imp == 0 and apor == 0 and fond == 0 and hon == 0 and rent == 0:
                continue
            excel_data[(nro, cip, nroorden)] = {
                "imp": imp, "apor": apor, "fond": fond, "hon": hon, "rent": rent,
            }
        nro_to_lg = {e.numero: e.liquidacion_id for e in LiquidacionEdificacion.objects.all()}
        nro_ids_set = {v for k, v in nro_to_lg.items() if k in {k[0] for k in excel_data}}; nro_ids = list(nro_ids_set)
        self.stdout.write(f"  Cargando {len(nro_ids)} LDs en 1 sola query con JOIN...")
        # 1 sola query con JOIN; trae 5 importes
        dhs_data = list(DetalleHonorarioDelegado.objects.filter(
            liquidacion_delegado__liquidacion_id__in=nro_ids,
            liquidacion_delegado__delegado__perfil_ingeniero__cip__in={k[1] for k in excel_data},
            liquidacion_delegado__numero_rh__in={k[2] for k in excel_data},
        ).select_related("liquidacion_delegado__delegado__perfil_ingeniero", "liquidacion_delegado__liquidacion__edificaciones").values(
            "id", "liquidacion_delegado_id", "imp_bruto", "aporte_codemu", "fondo_comun", "neto_honorario", "renta_cip",
            "liquidacion_delegado__delegado__perfil_ingeniero__cip",
            "liquidacion_delegado__liquidacion__edificaciones__numero",
            "liquidacion_delegado__numero_rh",
        ))
        self.stdout.write(f"  Total revisado: {len(dhs_data)}")
        cambios = []
        objetos_a_actualizar = []
        for d in dhs_data:
            nro = d["liquidacion_delegado__liquidacion__edificaciones__numero"]
            cip = d["liquidacion_delegado__delegado__perfil_ingeniero__cip"]
            nroorden = d["liquidacion_delegado__numero_rh"]
            key = (nro, cip, nroorden)
            ex = excel_data.get(key)
            if not ex:
                continue
            campos_actualizar = {}
            for campo_excel, campo_bd in [("imp", "imp_bruto"), ("apor", "aporte_codemu"), ("fond", "fondo_comun"), ("hon", "neto_honorario"), ("rent", "renta_cip")]:
                ex_v = ex[campo_excel]
                bd_v = d[campo_bd] or Decimal("0")
                if abs(ex_v - bd_v) > TOL_HONORARIO:
                    cambios.append({
                        "ld_id": str(d["id"]), "nro": nro, "cip": cip, "nro_orden": nroorden,
                        "campo": campo_bd, "bd_old": str(bd_v), "excel_new": str(ex_v),
                        "estado": "OK" if apply else "DRY_RUN",
                    })
                    if apply:
                        campos_actualizar[campo_bd] = ex_v
            if apply and campos_actualizar:
                # Bulk update
                DetalleHonorarioDelegado.objects.filter(id=d["id"]).update(**campos_actualizar)
        with out_path.open("w", encoding="utf-8-sig", newline="") as fout:
            w = csv.writer(fout, delimiter=SEP)
            w.writerow(["ld_id", "nro", "cip", "nro_orden", "campo", "bd_old", "excel_new", "estado"])
            for c in cambios:
                w.writerow([c["ld_id"], c["nro"], c["cip"], c["nro_orden"], c["campo"], c["bd_old"], c["excel_new"], c["estado"]])
        self.stdout.write(self.style.SUCCESS(f"  Updates: {len(cambios)}"))
        self.stdout.write(f"  Reporte: {out_path}")

    def _fase_consolidar_duplicados(self, filas, apply, out_path):
        from collections import defaultdict
        self.stdout.write(self.style.HTTP_INFO("[2/4] FASE: Consolidar duplicados de LiquidacionDelegado (OPTIMIZADO)..."))
        # OPTIMIZADO: 1 sola query trae TODOS los LD; agrupar en memoria por (liquidacion, delegado)
        self.stdout.write("  Cargando todos los LD (1 sola query)...")
        qs = LiquidacionDelegado.objects.values_list("id", "liquidacion_id", "delegado_id", "delegado__perfil_ingeniero__cip", "especialidad_revision__nombre")
        por_par = defaultdict(list)
        for ld in qs.iterator(chunk_size=10000):
            cip = (ld[3] or "").zfill(6) if ld[3] else ""
            por_par[(ld[1], cip)].append({"id": ld[0], "esp": ld[4]})
        eliminados = 0
        cambios = []
        for par, ld_group in por_par.items():
            if len(ld_group) < 2:
                continue
            civiles = [ld for ld in ld_group if ld["esp"] == "Ingenier\u00eda Civil"]
            if not civiles:
                continue
            otros = [ld for ld in ld_group if ld["esp"] != "Ingenier\u00eda Civil"]
            if not otros:
                continue
            for civ in civiles:
                ld_correcto = otros[0]
                if apply:
                    with transaction.atomic():
                        DetalleHonorarioDelegado.objects.filter(liquidacion_delegado_id=civ["id"]).update(liquidacion_delegado_id=ld_correcto["id"])
                        LiquidacionDelegado.objects.filter(id=civ["id"]).delete()
                        eliminados += 1
                cambios.append({"ld_civil_id": str(civ["id"]), "ld_correcto_id": str(ld_correcto["id"]), "otro_esp": ld_correcto["esp"], "estado": "OK" if apply else "DRY_RUN"})
        with out_path.open("w", encoding="utf-8-sig", newline="") as fout:
            w = csv.writer(fout, delimiter=SEP)
            w.writerow(["ld_civil_id", "ld_correcto_id", "otro_esp", "estado"])
            for c in cambios:
                w.writerow([c["ld_civil_id"], c["ld_correcto_id"], c["otro_esp"], c["estado"]])
        self.stdout.write(self.style.SUCCESS(f"  Eliminados: {eliminados}"))
        self.stdout.write(f"  Reporte: {out_path}")

    def _fase_corregir_especialidad(self, filas, apply, out_path):
        import unicodedata
        def _strip(s):
            return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")
        self.stdout.write(self.style.HTTP_INFO("[2/4] FASE: Corregir especialidad (LiquidacionDelegado + DelegadoOperacion)..."))
        excel_data = {}
        for f in filas:
            nro = f["nro"]
            nro_orden = f["nro_orden"].strip()
            cip_excel = f["cip"].strip().zfill(6) if f["cip"] else ""
            if not nro_orden or not cip_excel or cip_excel == "000000":
                continue
            excel_data.setdefault(nro, {}).setdefault((cip_excel, nro_orden), f)
        esp_map = {e.nombre: e for e in EspecialidadRevision.objects.all()}
        alias = {
            "ESTRUCTURAS": "Ingeniería Civil",
            "INST. SANITARIAS": "Ingeniería Sanitaria",
            "INST. MECANICO ELECTRICAS": "Ingeniería Eléctrica y Mecánica Eléctrica",
            "INST. ELECTRICAS": "Ingeniería Eléctrica y Mecánica Eléctrica",
            "INST. ELECTRONICAS": "Ingeniería Electrónica",
        }
        qs = LiquidacionDelegado.objects.select_related("delegado__perfil_ingeniero", "especialidad_revision", "delegado_operacion").values(
            "id", "liquidacion__edificaciones__numero", "delegado__perfil_ingeniero__cip", "numero_rh",
            "especialidad_revision__nombre", "delegado_operacion_id",
        )
        cambios = []
        corregidos = 0
        skip_duplicado = 0
        for d in qs.iterator(chunk_size=5000):
            nro = d["liquidacion__edificaciones__numero"]
            cip = (d["delegado__perfil_ingeniero__cip"] or "").zfill(6) if d["delegado__perfil_ingeniero__cip"] else ""
            nroorden = d["numero_rh"] or ""
            excel = excel_data.get(nro, {}).get((cip, nroorden))
            if not excel:
                continue
            esp_excel_raw = excel.get("especialidad", "").strip()
            if not esp_excel_raw or _strip(esp_excel_raw.upper()) == "TODAS":
                continue
            esp_excel_norm = alias.get(_strip(esp_excel_raw.upper()), _strip(esp_excel_raw))
            esp_bd = d["especialidad_revision__nombre"] or ""
            if _strip(esp_bd.upper()) == _strip(esp_excel_norm.upper()):
                continue
            esp_obj = esp_map.get(esp_excel_norm)
            if not esp_obj:
                continue
            ld_id = d["id"]
            op_id = d["delegado_operacion_id"]
            if apply:
                with transaction.atomic():
                    # Si ya existe otro LiquidacionDelegado con la misma (liquidacion, delegado, nueva_especialidad), skip
                    duplicado = LiquidacionDelegado.objects.filter(
                        liquidacion_id=LiquidacionDelegado.objects.get(id=ld_id).liquidacion_id,
                        delegado_id=LiquidacionDelegado.objects.get(id=ld_id).delegado_id,
                        especialidad_revision_id=esp_obj.id,
                    ).exclude(id=ld_id).first()
                    if duplicado:
                        skip_duplicado += 1
                        cambios.append({
                            "ld_id": ld_id, "nro": nro, "cip": cip, "nro_orden": nroorden,
                            "esp_bd_old": esp_bd, "esp_bd_new": str(esp_excel_norm),
                            "delegado_operacion_id": op_id or "",
                            "estado": "SKIP_DUPLICADO",
                        })
                        continue
                    ld = LiquidacionDelegado.objects.get(id=ld_id)
                    ld.especialidad_revision = esp_obj
                    ld.save()
                    if op_id:
                        try:
                            op = DelegadoOperacion.objects.get(id=op_id)
                            op.especialidad_revision = esp_obj
                            op.save()
                        except Exception:
                            pass
            cambios.append({
                "ld_id": ld_id, "nro": nro, "cip": cip, "nro_orden": nroorden,
                "esp_bd_old": esp_bd, "esp_bd_new": str(esp_excel_norm),
                "delegado_operacion_id": op_id or "",
                "estado": "OK" if apply else "DRY_RUN",
            })
            corregidos += 1
        with out_path.open("w", encoding="utf-8-sig", newline="") as fout:
            w = csv.writer(fout, delimiter=SEP)
            w.writerow(["ld_id", "nro", "cip", "nro_orden", "esp_bd_old", "esp_bd_new", "delegado_operacion_id", "estado"])
            for c in cambios:
                w.writerow([c["ld_id"], c["nro"], c["cip"], c["nro_orden"], c["esp_bd_old"], c["esp_bd_new"], c["delegado_operacion_id"], c["estado"]])
        self.stdout.write(self.style.SUCCESS(f"  Corregidos: {corregidos}"))
        self.stdout.write(f"  Reporte: {out_path}")

    def _fase_crear_faltantes(self, edif_wide_path, filas, apply, out_path):
        self.stdout.write(self.style.HTTP_INFO("[2/4] FASE: Crear LiquidacionDelegado faltantes (long + wide)..."))
        edif_path = Path(edif_wide_path)
        if not edif_path.exists():
            self.stdout.write(self.style.ERROR(f"  No existe: {edif_path}"))
            return
        nro_to_edif = {e["numero"]: e for e in LiquidacionEdificacion.objects.filter(
            numero__in={f["nro"] for f in filas}
        ).values("numero", "liquidacion_id", "liquidacion__municipalidad_id")}
        edif_to_muni = {n: nro_to_edif[n]["liquidacion__municipalidad_id"] for n in nro_to_edif}
        excel_data = {}
        for f in filas:
            nro = f["nro"]
            nro_orden = f["nro_orden"].strip()
            cip_excel_raw = f["cip"].strip().zfill(6) if f["cip"] else ""
            if not nro_orden or not cip_excel_raw or cip_excel_raw == "000000":
                continue
            if nro not in excel_data:
                excel_data[nro] = {}
            excel_data[nro][(cip_excel_raw, nro_orden)] = f
        bd_por_key = {}
        detalles = DetalleHonorarioDelegado.objects.filter(
            liquidacion_delegado__liquidacion_id__in={e["liquidacion_id"] for e in nro_to_edif.values()}
        ).values(
            "liquidacion_delegado_id", "liquidacion_delegado__liquidacion__edificaciones__numero",
            "liquidacion_delegado__delegado__perfil_ingeniero__cip", "liquidacion_delegado__numero_rh",
        )
        for d in detalles:
            nro = d["liquidacion_delegado__liquidacion__edificaciones__numero"]
            cip = (d["liquidacion_delegado__delegado__perfil_ingeniero__cip"] or "").zfill(6) if d["liquidacion_delegado__delegado__perfil_ingeniero__cip"] else ""
            nro_orden = (d["liquidacion_delegado__numero_rh"] or "").strip()
            bd_por_key[(nro, cip, nro_orden)] = True
        self.stdout.write(f"  Pares (NRO, CIP, NROORDEN) en BD: {len(bd_por_key)}")
        self.stdout.write(f"  NROs en BD: {len(nro_to_edif)}")
        esp_map = {e.nombre: e for e in EspecialidadRevision.objects.all()}
        self.stdout.write(f"  EspecialidadesRevision en BD: {len(esp_map)}")
        faltantes = []
        for nro, slots in excel_data.items():
            if nro not in nro_to_edif:
                continue
            for (cip_excel, nro_orden), f in slots.items():
                if not cip_excel or cip_excel == "000000":
                    continue
                key = (nro, cip_excel, nro_orden)
                if key in bd_por_key:
                    continue
                esp_excel = f.get("especialidad", "").strip()
                import unicodedata
                def _strip_accents(s):
                    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
                esp_norm = ESPECIALIDAD_ALIAS.get(_strip_accents(esp_excel.upper()), esp_excel)
                esp_obj = esp_map.get(esp_norm) if _strip_accents(esp_norm.upper()) != "TODAS" else None
                faltantes.append({
                    "nro": nro,
                    "cip": cip_excel,
                    "nro_orden": nro_orden,
                    "especialidad_excel": esp_norm if esp_norm.upper() != "TODAS" else "",
                    "municipalidad_id": edif_to_muni.get(nro),
                    "imp_bruto": f.get("impbruto", ""),
                    "aporcodemu": f.get("aporcodemu", ""),
                    "fondocomun": f.get("fondocomun", ""),
                    "honorario": f.get("honorario", ""),
                    "rentacip": f.get("rentacip", ""),
                    "netohonora": f.get("netohonora", ""),
                    "periodo": f.get("periodo", ""),
                    "mes": f.get("mes", ""),
                    "fecha_pres": f.get("fecha_pres"),
                    "fecha_rev": f.get("fecha_rev"),
                    "dictamen": f.get("dictamen", ""),
                })
        self.stdout.write(self.style.WARNING(f"  Faltantes detectados: {len(faltantes)}"))
        if not faltantes:
            self.stdout.write(self.style.SUCCESS("  No hay faltantes"))
            return
        cambios = []
        for f in faltantes:
            cip_int = int(f["cip"]) if f["cip"].isdigit() else 0
            if not cip_int:
                continue
            nro_orden_norm = f["nro_orden"] if f["nro_orden"] not in ("0", "") else "0"
            try:
                if apply:
                    with transaction.atomic():
                        perfil, perfil_status = _ensure_perfil_ingeniero_by_cip(cip_int, dry_run=False)
                        if not perfil:
                            cambios.append({**f, "perfil_status": perfil_status, "delegado_status": "ERROR", "delegado_operacion_status": "ERROR", "ld_status": "ERROR", "dh_status": "ERROR", "final_status": "ERROR"})
                            continue
                        delegado, del_status = _ensure_delegado_for_perfil(perfil, dry_run=False)
                        if not delegado:
                            cambios.append({**f, "perfil_status": perfil_status, "delegado_status": del_status, "delegado_operacion_status": "SKIP", "ld_status": "SKIP", "dh_status": "SKIP", "final_status": "ERROR"})
                            continue
                        muni = Municipalidad.objects.filter(id=f["municipalidad_id"]).first() if f["municipalidad_id"] else None
                        if not muni:
                            cambios.append({**f, "perfil_status": perfil_status, "delegado_status": del_status, "delegado_operacion_status": "SIN_MUNI", "ld_status": "SKIP", "dh_status": "SKIP", "final_status": "ERROR_SIN_MUNI"})
                            continue
                        tipo_liq = TipoLiquidacion.objects.filter(codigo="EDIFICACION").first()
                        esp_obj = esp_map.get(f["especialidad_excel"]) if f["especialidad_excel"] else esp_map.get("Ingeniería Civil")
                        if not esp_obj:
                            esp_obj = esp_map.get("Ingeniería Civil")
                        op, op_status = _ensure_delegado_operacion(delegado, muni, tipo_liq, esp_obj, dry_run=False)
                        slot_data = {
                            "periodo": int(f["periodo"]) if f["periodo"].isdigit() else None,
                            "mes": int(f["mes"]) if f["mes"].isdigit() else None,
                            "fecha_presentacion": f["fecha_pres"],
                            "fecha_revision": f["fecha_rev"],
                            "nro_rh": nro_orden_norm,
                            "dictamen": f["dictamen"],
                        }
                        lg_id = nro_to_edif[f["nro"]]["liquidacion_id"]
                        liquidacion = LiquidacionDelegado.objects.filter(liquidacion_id=lg_id).first().liquidacion if LiquidacionDelegado.objects.filter(liquidacion_id=lg_id).exists() else None
                        from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import LiquidacionGeneral
                        liquidacion = LiquidacionGeneral.objects.get(id=lg_id)
                        ld, ld_status = _ensure_liquidacion_delegado(liquidacion, delegado, esp_obj, op, slot_data, dry_run=False)
                        if not ld:
                            cambios.append({**f, "perfil_status": perfil_status, "delegado_status": del_status, "delegado_operacion_status": op_status, "ld_status": ld_status, "dh_status": "SKIP", "final_status": "ERROR_LD"})
                            continue
                        monetary = {
                            "imp_bruto": parse_dec(f["imp_bruto"]) if f["imp_bruto"] else Decimal("0"),
                            "aporte_codemu": parse_dec(f["aporcodemu"]) if f["aporcodemu"] else Decimal("0"),
                            "fondo_comun": parse_dec(f["fondocomun"]) if f["fondocomun"] else Decimal("0"),
                            "neto_honorario": parse_dec(f["netohonora"]) if f["netohonora"] else Decimal("0"),
                            "renta_cip": parse_dec(f["rentacip"]) if f["rentacip"] else Decimal("0"),
                        }
                        dh, dh_status = _ensure_detalle_honorario_delegado(ld, monetary, dry_run=False)
                        cambios.append({
                            "nro": f["nro"], "cip": f["cip"], "nro_orden": nro_orden_norm,
                            "perfil_status": perfil_status, "delegado_status": del_status,
                            "delegado_operacion_status": op_status, "ld_status": ld_status, "dh_status": dh_status if dh else "ERROR",
                            "final_status": "OK" if (ld and dh) else "PARTIAL",
                        })
                else:
                    cambios.append({**f, "perfil_status": "DRY_RUN", "delegado_status": "DRY_RUN", "delegado_operacion_status": "DRY_RUN", "ld_status": "DRY_RUN", "dh_status": "DRY_RUN", "final_status": "DRY_RUN"})
            except Exception as e:
                cambios.append({**f, "perfil_status": "ERROR", "delegado_status": "ERROR", "delegado_operacion_status": "ERROR", "ld_status": "ERROR", "dh_status": "ERROR", "final_status": f"ERROR: {str(e)[:100]}"})
        self._escribir_reporte(out_path, ["nro", "cip", "nro_orden", "perfil_status", "delegado_status", "delegado_operacion_status", "ld_status", "dh_status", "final_status"], cambios)
        ok_count = sum(1 for c in cambios if c.get("final_status") == "OK")
        self.stdout.write(self.style.SUCCESS(f"  Creados OK: {ok_count}"))
        self.stdout.write(f"  Reporte: {out_path}")

    def _fase_especialidad(self, filas, apply, out_path):
        self.stdout.write(self.style.HTTP_INFO("[2/4] FASE: Especialidad (long format, por NRO+CIP+NROORDEN)..."))
        esperado = []
        for f in filas:
            esp_excel_raw = (f.get("dictamen") or "").strip()  # not used
            nro_orden_norm = normalize_nro_rh(f["nro_orden"].strip())
            if not nro_orden_norm:
                continue
            esp_excel = (f.get("dictamen") or "").strip()  # not used
            esp_excel_col = (f.get("especialidad") or "").strip()
            if not esp_excel_col or esp_excel_col.upper() in ("NULL", "NONE", ""):
                continue
            esperado.append({
                "nro": f["nro"],
                "cip": f["cip"],
                "nro_orden": nro_orden_norm,
                "especialidad": esp_excel_col,
            })
        self.stdout.write(f"  Registros con especialidad: {len(esperado)}")

        edifs = {e["numero"]: e["liquidacion_id"] for e in LiquidacionEdificacion.objects.filter(numero__in={f["nro"] for f in esperado}).values("numero", "liquidacion_id")}
        detalles = DetalleHonorarioDelegado.objects.filter(liquidacion_delegado__liquidacion_id__in=set(edifs.values())).values(
            "liquidacion_delegado_id", "liquidacion_delegado__liquidacion__edificaciones__numero",
            "liquidacion_delegado__delegado__perfil_ingeniero__cip", "liquidacion_delegado__numero_rh",
            "liquidacion_delegado__especialidad_revision_id",
        )
        bd_por_key = {}
        for d in detalles:
            nro = d["liquidacion_delegado__liquidacion__edificaciones__numero"]
            cip = (d["liquidacion_delegado__delegado__perfil_ingeniero__cip"] or "").zfill(6) if d["liquidacion_delegado__delegado__perfil_ingeniero__cip"] else ""
            nro_orden = (d["liquidacion_delegado__numero_rh"] or "").strip()
            bd_por_key[(nro, cip, nro_orden)] = {
                "ld_id": d["liquidacion_delegado_id"],
                "esp_id": d["liquidacion_delegado__especialidad_revision_id"],
            }
        self.stdout.write(f"  Pares (NRO, CIP, NROORDEN) en BD: {len(bd_por_key)}")

        esp_map = {e.nombre: e for e in EspecialidadRevision.objects.all()}

        cambios = []
        skip_no_match = 0
        sin_esp_bd = 0
        for e in esperado:
            cip_n = e["cip"].strip().zfill(6) if e["cip"] else ""
            key = (e["nro"], cip_n, e["nro_orden"])
            b = bd_por_key.get(key)
            if not b:
                skip_no_match += 1
                continue
            esp_excel_norm = ESPECIALIDAD_ALIAS.get(e["especialidad"].upper(), e["especialidad"])
            if esp_excel_norm.upper() == "TODAS":
                continue
            esp_obj = esp_map.get(esp_excel_norm)
            if not esp_obj:
                continue
            if b["esp_id"] == esp_obj.id:
                continue
            cambios.append({
                "nro": e["nro"], "cip": cip_n, "nro_orden": e["nro_orden"],
                "especialidad_excel": esp_excel_norm,
                "esp_id_bd": b["esp_id"],
                "esp_id_nuevo": esp_obj.id,
                "delegado_operacion_id_actualizado": "",
                "skip_por_duplicado": "",
                "cambia": True,
            })
            if apply:
                with transaction.atomic():
                    ld = LiquidacionDelegado.objects.get(id=b["ld_id"])
                    duplicado = LiquidacionDelegado.objects.filter(
                        liquidacion_id=ld.liquidacion_id, delegado_id=ld.delegado_id,
                        especialidad_revision_id=esp_obj.id,
                    ).exclude(id=ld.id).first()
                    if duplicado:
                        cambios[-1]["skip_por_duplicado"] = f"ya existe ld.id={duplicado.id} con misma especialidad; mantengo el viejo"
                    else:
                        ld.especialidad_revision = esp_obj
                        ld.save()
                    if ld.delegado_operacion and ld.delegado_operacion.especialidad_revision_id != esp_obj.id:
                        ld.delegado_operacion.especialidad_revision = esp_obj
                        ld.delegado_operacion.save()
                        cambios[-1]["delegado_operacion_id_actualizado"] = ld.delegado_operacion_id
        self._escribir_reporte(out_path, ["nro", "cip", "nro_orden", "especialidad_excel", "esp_id_bd", "esp_id_nuevo", "cambia"], cambios)
        n_cambios = sum(1 for c in cambios if c["cambia"])
        self.stdout.write(self.style.SUCCESS(f"  Especialidades actualizadas: {n_cambios}"))
        self.stdout.write(self.style.WARNING(f"  Sin match en BD: {skip_no_match}"))
        self.stdout.write(f"  Reporte: {out_path}")
        self.stdout.write("")
