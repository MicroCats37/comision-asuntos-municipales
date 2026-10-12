"""
compare_rh_edif — Compara RH_EDIF.csv contra DetalleHonorarioDelegado en BD.
READ-ONLY. Genera reporte CSV con diffs por registro (no suma).

Uso:
    python manage.py compare_rh_edif --rh-csv=<path> [--limit=100] [--output=<path>]
"""
import csv
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Sum

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import LiquidacionEdificacion
from modules.finanzas.domain.models.detalle_honorario_delegado import DetalleHonorarioDelegado


DEFAULT_RH_PATH = Path(r"C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\backend\core_application\seeds\historico\RH_EDIF.csv")
DEFAULT_OUT_DIR = Path(r"C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\result\EDIF")
SEP = ";"
TOL = Decimal("0.01")
CAMPOS = ["impbruto", "aporcodemu", "fondocomun", "honorario", "rentacip", "netohonora"]


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


def parse_int(s):
    try:
        return int(str(s).strip())
    except Exception:
        return None


def normalize_cip(cip):
    s = str(cip).strip()
    if not s:
        return ""
    digits = "".join(c for c in s if c.isdigit())
    if not digits:
        return s
    return digits.zfill(6)


def progress(iterable, total, label=""):
    """Barra de progreso simple sin dependencias externas."""
    n = 0
    last_pct = -1
    for item in iterable:
        yield item
        n += 1
        pct = int(n * 100 / total) if total else 0
        if pct != last_pct:
            bar = "=" * (pct // 2) + " " * (50 - pct // 2)
            sys.stdout.write(f"\r  {label}[{bar}] {pct:>3}% ({n}/{total})")
            sys.stdout.flush()
            last_pct = pct
    if total:
        sys.stdout.write(f"\r  {label}[{'='*50}] 100% ({total}/{total})\n")
        sys.stdout.flush()


class Command(BaseCommand):
    help = "Compara RH_EDIF.csv contra DetalleHonorarioDelegado en BD. READ-ONLY."

    def add_arguments(self, parser):
        parser.add_argument(
            "--rh-csv",
            type=str,
            default=str(DEFAULT_RH_PATH),
            help=f"Path al RH_EDIF.csv (default: {DEFAULT_RH_PATH})",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limitar a N NROs unicos (default: todos)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Path al reporte CSV de salida (default: result/EDIF/rh_comparison_<ts>.csv)",
        )

    def handle(self, *args, **options):
        rh_path = Path(options["rh_csv"])
        limit = options["limit"]
        out_path = Path(options["output"]) if options["output"] else None

        if not rh_path.exists():
            self.stderr.write(self.style.ERROR(f"No existe: {rh_path}"))
            return

        if out_path is None:
            out_dir = DEFAULT_OUT_DIR
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = out_dir / f"rh_comparison_{ts}.csv"

        self.stdout.write(self.style.NOTICE("=" * 70))
        self.stdout.write(self.style.NOTICE("compare_rh_edif — RH_EDIF.csv vs DetalleHonorarioDelegado (BD)"))
        self.stdout.write(self.style.NOTICE("=" * 70))
        self.stdout.write(f"  RH CSV:  {rh_path}")
        self.stdout.write(f"  Output:  {out_path}")
        if limit:
            self.stdout.write(f"  Limit:   {limit} NROs")
        self.stdout.write("")

        # ── Paso 1: leer RH CSV ──
        self.stdout.write(self.style.HTTP_INFO("[1/4] Leyendo RH CSV..."))
        esperado = {}
        nros_set = set()
        with rh_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=SEP)
            total_lines = sum(1 for _ in f) - 1
        with rh_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=SEP)
            for i, r in enumerate(progress(reader, total_lines, label="leyendo ")):
                nro = parse_int(r.get("NRO"))
                if nro is None:
                    continue
                nros_set.add(nro)
                cip = normalize_cip(r.get("CIP", ""))
                if not cip:
                    continue
                key = (nro, cip)
                e = esperado.setdefault(key, {c: Decimal("0") for c in CAMPOS})
                e["impbruto"] += parse_dec(r["IMPBRUTO"])
                e["aporcodemu"] += parse_dec(r["APORCODEMU"])
                e["fondocomun"] += parse_dec(r["FONDOCOMUN"])
                e["honorario"] += parse_dec(r["HONORARIO"])
                e["rentacip"] += parse_dec(r["RENTACIP"])
                e["netohonora"] += parse_dec(r["NETOHONORA"])
        if limit:
            nros_set = set(sorted(nros_set)[:limit])
            esperado = {k: v for k, v in esperado.items() if k[0] in nros_set}
        self.stdout.write(self.style.SUCCESS(
            f"  -> {sum(1 for _ in esperado)} pares (NRO, CIP) | {len(nros_set)} NROs únicos"
        ))
        self.stdout.write("")

        # ── Paso 2: consultar BD ──
        self.stdout.write(self.style.HTTP_INFO("[2/4] Consultando BD (LiquidacionEdificacion + DetalleHonorarioDelegado)..."))
        edifs = list(LiquidacionEdificacion.objects.filter(numero__in=nros_set).values("id", "numero", "liquidacion_id"))
        nro_to_edif = {e["numero"]: e for e in edifs}
        self.stdout.write(f"  Edificaciones encontradas: {len(nro_to_edif)}")
        nros_no_en_bd = nros_set - nro_to_edif.keys()
        self.stdout.write(self.style.WARNING(f"  NROs no importados: {len(nros_no_en_bd)}"))

        lg_ids = [e["liquidacion_id"] for e in edifs]
        self.stdout.write(f"  Consultando detalles para {len(lg_ids)} liquidaciones...")
        detalles_qs = DetalleHonorarioDelegado.objects.filter(
            liquidacion_delegado__liquidacion_id__in=lg_ids
        ).values(
            "liquidacion_delegado__liquidacion__edificaciones__numero",
            "liquidacion_delegado__delegado__perfil_ingeniero__cip",
            "imp_bruto", "aporte_codemu", "fondo_comun", "neto_honorario", "renta_cip",
        )
        detalles = list(progress(detalles_qs, detalles_qs.count(), label="bd       "))
        bd_por_key = {}
        bd_cips_por_nro = defaultdict(set)
        for d in detalles:
            nro = d["liquidacion_delegado__liquidacion__edificaciones__numero"]
            cip = normalize_cip(d["liquidacion_delegado__delegado__perfil_ingeniero__cip"])
            if not cip:
                continue
            b = bd_por_key.setdefault((nro, cip), {c: Decimal("0") for c in CAMPOS})
            b["impbruto"] += d["imp_bruto"] or Decimal("0")
            b["aporcodemu"] += d["aporte_codemu"] or Decimal("0")
            b["fondocomun"] += d["fondo_comun"] or Decimal("0")
            b["honorario"] += d["neto_honorario"] or Decimal("0")
            b["rentacip"] += d["renta_cip"] or Decimal("0")
            b["netohonora"] += d["neto_honorario"] or Decimal("0")
            bd_cips_por_nro[nro].add(cip)
        self.stdout.write(self.style.SUCCESS(f"  -> {len(bd_por_key)} pares (NRO, CIP) en BD"))
        self.stdout.write("")

        # ── Paso 3: comparar y escribir reporte ──
        self.stdout.write(self.style.HTTP_INFO("[3/4] Comparando y escribiendo reporte..."))
        counts = {"ok": 0, "dif_valor": 0, "falta_en_bd": 0, "nro_no_en_bd": 0, "extra_en_bd": 0}
        diffs_por_campo = defaultdict(int)

        self.stdout.write(self.style.HTTP_INFO("[3/4] Comparando y escribiendo reporte..."))
        self.stdout.write("  Escribiendo en " + str(out_path) + " ...")
        sys.stdout.flush()

        with out_path.open("w", encoding="utf-8-sig", newline="") as fout:
            w = csv.writer(fout, delimiter=SEP)
            w.writerow(["nro", "cip", "estado", "campo", "esperado", "bd", "diff"])

            for (nro, cip), e in progress(sorted(esperado.items()), len(esperado), label="cmp      "):
                if nro not in nro_to_edif:
                    counts["nro_no_en_bd"] += 1
                    w.writerow([nro, cip, "NRO_NO_EN_BD", "", "", "", ""])
                    continue
                b = bd_por_key.get((nro, cip))
                if b is None:
                    counts["falta_en_bd"] += 1
                    w.writerow([nro, cip, "FALTA_EN_BD", "", "", "", ""])
                    continue
                problemas = []
                for c in CAMPOS:
                    d = e[c] - b[c]
                    if abs(d) > TOL:
                        problemas.append((c, e[c], b[c], d))
                        diffs_por_campo[c] += 1
                if problemas:
                    counts["dif_valor"] += 1
                    for c, ev, bv, dv in problemas:
                        w.writerow([nro, cip, "DIF_VALOR", c, ev, bv, dv])
                else:
                    counts["ok"] += 1
                    w.writerow([nro, cip, "OK", "", "", "", ""])

            for nro, cips_bd in bd_cips_por_nro.items():
                cips_esp = {c for (n, c) in esperado.keys() if n == nro}
                extras = cips_bd - cips_esp
                for c in extras:
                    counts["extra_en_bd"] += 1
                    w.writerow([nro, c, "EXTRA_EN_BD", "", "", "", ""])

        self.stdout.write("")
        sys.stdout.flush()

        # ── Paso 4: resumen ──
        self.stdout.write(self.style.HTTP_INFO("[4/4] Resumen"))
        sys.stdout.flush()
        self.stdout.write(self.style.NOTICE("=" * 70))
        self.stdout.write(self.style.SUCCESS(f"  OK:              {counts['ok']:>8}"))
        self.stdout.write(self.style.WARNING(f"  DIF_VALOR:       {counts['dif_valor']:>8}"))
        self.stdout.write(self.style.WARNING(f"  FALTA_EN_BD:     {counts['falta_en_bd']:>8}"))
        self.stdout.write(self.style.ERROR(f"  NRO_NO_EN_BD:    {counts['nro_no_en_bd']:>8}"))
        self.stdout.write(self.style.WARNING(f"  EXTRA_EN_BD:     {counts['extra_en_bd']:>8}"))
        self.stdout.write("")
        self.stdout.write("  Diffs por campo:")
        for c, n in sorted(diffs_por_campo.items(), key=lambda x: -x[1]):
            self.stdout.write(f"    {c:<14} {n:>8}")
        self.stdout.write(self.style.NOTICE("=" * 70))
        self.stdout.write(self.style.SUCCESS(f"  Reporte: {out_path}"))
        self.stdout.write(self.style.SUCCESS(f"  {out_path.stat().st_size:,} bytes"))
        sys.stdout.flush()
