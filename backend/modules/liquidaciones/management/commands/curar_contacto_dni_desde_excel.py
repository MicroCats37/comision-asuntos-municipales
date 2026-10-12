"""
curar_contacto_dni_desde_excel — Crea / rellena Contacto + LiquidacionContacto
desde las columnas TPERSONA, TFONO, TDNI del Excel legacy (HU / EDIF).

El import legacy original (pre-fix) tenía un bug crítico: a pesar de generar
un `contacto_inline` en el payload, el `LiquidacionContacto` resultado **nunca
se persistió** para HU ni EDIF. IO sí lo tenía bien.

Resultado: 52,021 liquidaciones importadas sin contacto alguno, aunque el Excel
trae los datos. Este comando los crea/rellena.

Read-only por default. Con `--apply` persiste en BD.

Uso:
    # EDIF dry-run
    python manage.py curar_contacto_dni_desde_excel --tipo edif

    # EDIF apply (CREA si no existe, RELLENA si está vacío)
    python manage.py curar_contacto_dni_desde_excel --tipo edif --apply

    # HU
    python manage.py curar_contacto_dni_desde_excel --tipo hu --apply

Lógica:
    Para cada fila del CSV con TPERSONA o TFONO no vacío:
      1. Encuentra LiquidacionEdificacion/HU por numero = CSV.NRO.
      2. Si no existe la liquidación, skip (no match).
      3. Busca o crea un Contacto con (nombres, apellidos, telefono, dni).
         (Deduplicación simple: si ya existe Contacto idéntico por NOMBRE+DNI,
         reusar; si no, crear uno nuevo.)
      4. Crea LiquidacionContacto (vincula Contacto a Liquidacion, principal=True)
         si no existía.
      5. Reporta cambios propuestos (dry-run) o aplica (apply).

NO pisa campos ya poblados (idempotente).
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_edificaciones import (
    LiquidacionEdificacion,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_especifico.liquidacion_habilitacion_urbana import (
    LiquidacionHabilitacionUrbana,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionContacto,
    LiquidacionGeneral,
)
from modules.entidades.domain.models.contacto import Contacto


DEFAULT_EDIF_PATH = Path(
    r"C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\backend\core_application\seeds\historico\EDIF_ALL.csv"
)
DEFAULT_HU_PATH = Path(
    r"C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\backend\core_application\seeds\historico\HU_ALL.csv"
)
SEP = ";"


def _clean(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    if not text or text.upper() in ("NULL", "NONE", ""):
        return None
    return text


def parse_int(s: Any) -> int | None:
    try:
        return int(str(s).strip())
    except Exception:
        return None


def parse_tpersona(raw: Any) -> tuple[str | None, str | None]:
    """
    TPERSONA llega como:
        "Titular: JUAN PEREZ" o "JUAN PEREZ" o similar.
    Heurística: tomar el último segmento después de los dos puntos si existe,
    y dividir en nombres/apellidos por espacio.
    """
    text = _clean(raw)
    if text is None:
        return None, None
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    parts = text.split(None, 1)
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


class Command(BaseCommand):
    help = (
        "Crea/rellena Contacto + LiquidacionContacto desde TPERSONA, TFONO, TDNI. "
        "Read-only por default; --apply para escribir."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tipo",
            type=str,
            required=True,
            choices=["edif", "hu"],
            help="Tipo de liquidación (edif=EDIF_ALL.csv, hu=HU_ALL.csv).",
        )
        parser.add_argument(
            "--csv",
            dest="csv_path",
            type=str,
            default=None,
            help="Ruta al CSV. Default: seeds/historico/{EDIF|HU}_ALL.csv.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplicar cambios en BD (default: dry-run).",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Directorio destino del reporte CSV.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Procesar solo las primeras N filas (útil para prueba).",
        )

    def handle(self, *args, **options):
        tipo = options["tipo"]
        csv_path = Path(options["csv_path"]) if options["csv_path"] else (
            DEFAULT_EDIF_PATH if tipo == "edif" else DEFAULT_HU_PATH
        )
        apply = bool(options["apply"])
        limit = options.get("limit")

        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"No existe: {csv_path}"))
            sys.exit(1)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        modo = "APPLY" if apply else "DRY-RUN"
        out_dir = Path(options["output"]) if options.get("output") else (
            Path(r"C:\Users\Usuario\Desktop\Aplicaciones\CIP\CAM\aplicacion\result")
            / tipo.upper()
            / "contacto"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"curar_contacto_{'apply' if apply else 'dryrun'}_{ts}.csv"

        self.stdout.write(self.style.NOTICE("=" * 72))
        self.stdout.write(self.style.NOTICE(
            f"curar_contacto_dni_desde_excel --tipo={tipo} ({modo})"
        ))
        self.stdout.write(self.style.NOTICE("=" * 72))
        self.stdout.write(f"  CSV:   {csv_path}")
        self.stdout.write(f"  Out:   {out_path}")
        if limit:
            self.stdout.write(f"  Limit: {limit}")
        self.stdout.write("")

        # ── 1. Leer CSV ─────────────────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("[1/3] Leyendo CSV..."))
        filas = self._leer(csv_path)
        if limit:
            filas = filas[:limit]
        self.stdout.write(f"  Filas con TPERSONA o TFONO no vacío: {len(filas)}")
        self.stdout.write("")

        # ── 2. Cache de BD: por liquidación -> estado actual ───────────────
        self.stdout.write(self.style.HTTP_INFO("[2/3] Cargando estado actual de BD..."))
        nros_set = {f["nro"] for f in filas if f["nro"] is not None}
        if tipo == "edif":
            espec_qs = (
                LiquidacionEdificacion.objects
                .filter(numero__in=nros_set)
                .values("id", "numero", "liquidacion_id")
            )
        else:
            espec_qs = (
                LiquidacionHabilitacionUrbana.objects
                .filter(numero__in=nros_set)
                .values("id", "numero", "liquidacion_id")
            )
        liq_por_nro = {e["numero"]: e["liquidacion_id"] for e in espec_qs if e["liquidacion_id"]}

        # Cargar LiquidacionContacto principal existente por liquidacion_id
        lc_qs = (
            LiquidacionContacto.objects
            .filter(liquidacion_id__in=set(liq_por_nro.values()))
            .values(
                "id", "liquidacion_id", "contacto_id",
                "contacto__nombres", "contacto__apellidos",
                "contacto__telefono", "contacto__dni",
                "contacto__celular", "contacto__cargo",
            )
        )
        lc_por_liq: dict[int, dict] = {}
        for lc in lc_qs:
            existing = lc_por_liq.get(lc["liquidacion_id"])
            # Si ya hay uno, quedarnos con el primero (no sobrescribimos)
            if existing is None:
                lc_por_liq[lc["liquidacion_id"]] = lc
        self.stdout.write(f"  Liquidaciones encontradas: {len(liq_por_nro)}")
        self.stdout.write(f"  Con LiquidacionContacto ya existente: {len(lc_por_liq)}")
        self.stdout.write("")

        # ── 3. Procesar cada fila ───────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO("[3/3] Procesando filas..."))
        cambios: list[dict] = []
        skip_no_match = 0
        skip_sin_datos_contacto = 0
        crear_contacto = 0
        crear_lc = 0
        updates_campo = 0
        fk_updates = 0

        seen_liq_en_run: set[int] = set()  # Liquidacion ids ya procesados en este run
        for f in filas:
            nro = f["nro"]
            nombres, apellidos = f["nombres"], f["apellidos"]
            telefono = f["telefono"]
            dni = f["dni"]
            tpersona_raw = f["tpersona_raw"]
            tfono_raw = f["tfono_raw"]
            tdni_raw = f["tdni_raw"]

            if not (nombres or telefono):
                skip_sin_datos_contacto += 1
                continue

            liq_id = liq_por_nro.get(nro)
            if not liq_id:
                skip_no_match += 1
                continue

            # Si ya procesamos esta liquidación en este run (mismo NRO repetido en CSV),
            # saltar para evitar crear Contactos duplicados para la misma liquidación.
            if liq_id in seen_liq_en_run:
                continue
            seen_liq_en_run.add(liq_id)

            existing_lc = lc_por_liq.get(liq_id)
            contacto_id = existing_lc["contacto_id"] if existing_lc else None
            contacto_existente = existing_lc is not None

            # Determinar la operación a hacer
            updates = {
                "nombres": (existing_lc["contacto__nombres"] if existing_lc else "",
                            nombres or None),
                "apellidos": (existing_lc["contacto__apellidos"] if existing_lc else "",
                               apellidos or None),
                "telefono": (existing_lc["contacto__telefono"] if existing_lc else "",
                             telefono or None),
                "dni": (existing_lc["contacto__dni"] if existing_lc else "",
                        dni or None),
            }
            # Solo marcar como cambio si el campo BD está vacío y el Excel trae valor
            fields_to_set = {
                k: v[1]
                for k, v in updates.items()
                if (not v[0] or v[0] == "") and v[1]
            }
            if not fields_to_set and not existing_lc:
                # No hay nada que crear ni actualizar — el LC existe con datos completos,
                # o no hay datos suficientes. Registrarlo como skip.
                continue

            accion = "UPDATE" if existing_lc else "CREATE"
            if not existing_lc:
                crear_contacto += 1
                crear_lc += 1
            if fields_to_set:
                updates_campo += len(fields_to_set)

            cambios.append({
                "nro": nro,
                "liquidacion_id": str(liq_id),
                "liquidacion_contacto_id": str(existing_lc["id"]) if existing_lc else "(nuevo)",
                "contacto_id": str(contacto_id) if contacto_id else "(nuevo)",
                "accion": accion,
                "campos_a_setear": "; ".join(fields_to_set.keys()) if fields_to_set else "(ninguno)",
                "tpersona_raw": tpersona_raw,
                "tfono_raw": tfono_raw,
                "tdni_raw": tdni_raw,
            })

            if apply:
                with transaction.atomic():
                    # Load the LiquidacionGeneral instance — needed to set the
                    # `contacto` FK (separate from the LiquidacionContacto bridge).
                    liquidacion_obj = LiquidacionGeneral.objects.get(id=liq_id)
                    contacto_fk_changed = False
                    if existing_lc:
                        contacto = Contacto.objects.get(id=contacto_id)
                    else:
                        contacto = Contacto.objects.create(
                            nombres=nombres or "",
                            apellidos=apellidos or "",
                            telefono=telefono or "",
                            dni=dni or "",
                        )
                        LiquidacionContacto.objects.create(
                            liquidacion_id=liq_id,
                            contacto=contacto,
                            principal=True,
                        )

                    # Aplicar updates solo a campos vacíos
                    changed = False
                    for k, new_val in fields_to_set.items():
                        cur = getattr(contacto, k) or ""
                        if not cur:
                            setattr(contacto, k, new_val or "")
                            changed = True
                    if changed:
                        contacto.save()

                    # Populate the LiquidacionGeneral.contacto FK (direct) —
                    # the flujo/presenter reads this. The LiquidacionContacto
                    # bridge is also created/updated above.
                    if liquidacion_obj.contacto_id != contacto.id:
                        liquidacion_obj.contacto = contacto
                        liquidacion_obj.save(update_fields=["contacto", "updated_at"])
                        contacto_fk_changed = True

                    if contacto_fk_changed:
                        fk_updates += 1

        # ── Reporte ──
        self._escribir_reporte(
            out_path,
            [
                "accion", "nro", "liquidacion_id", "liquidacion_contacto_id",
                "contacto_id", "campos_a_setear", "tpersona_raw", "tfono_raw", "tdni_raw",
            ],
            cambios,
        )

        self.stdout.write(self.style.SUCCESS(f"  Acciones CREATE  (Contacto nuevo + LC): {crear_contacto}"))
        self.stdout.write(self.style.SUCCESS(f"  Acciones UPDATE  (campos vacíos a llenar): {len(cambios) - crear_contacto}"))
        self.stdout.write(self.style.SUCCESS(f"  FK LiquidacionGeneral.contacto poblado: {fk_updates}"))
        self.stdout.write(self.style.WARNING(f"  Sin match (sin LiquidacionEdif/HU):       {skip_no_match}"))
        self.stdout.write(self.style.WARNING(f"  Sin datos de contacto (TPERSONA y TFONO vacíos): {skip_sin_datos_contacto}"))
        self.stdout.write(f"  Reporte: {out_path}")
        self.stdout.write(self.style.SUCCESS(f"\nFinalizado ({modo})."))

    def _leer(self, path: Path) -> list[dict]:
        filas: list[dict] = []
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=SEP)
            for r in reader:
                nro = parse_int(r.get("NRO"))
                if nro is None:
                    continue
                tpersona_raw = r.get("TPERSONA", "") or ""
                tfono_raw = r.get("TFONO", "") or ""
                tdni_raw = r.get("TDNI", "") or ""

                nombres, apellidos = parse_tpersona(tpersona_raw)
                telefono = _clean(tfono_raw)
                dni = _clean(tdni_raw)
                # Aceptamos fila si trae al menos UN dato: nombre, telefono O dni.
                # El Excel real suele tener solo DNI o solo nombre.
                if not (nombres or telefono or dni):
                    continue
                filas.append({
                    "nro": nro,
                    "nombres": nombres,
                    "apellidos": apellidos,
                    "telefono": telefono,
                    "dni": dni,
                    "tpersona_raw": tpersona_raw.strip(),
                    "tfono_raw": tfono_raw.strip(),
                    "tdni_raw": tdni_raw.strip(),
                })
        return filas

    def _escribir_reporte(self, path: Path, headers: list[str], rows: list[dict]):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=SEP)
            writer.writeheader()
            for r in rows:
                writer.writerow({h: r.get(h, "") for h in headers})
