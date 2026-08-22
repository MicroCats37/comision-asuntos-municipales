"use client";

/**
 * RhInspectorMensualModal — Modal de 3 pasos para importar RH Mensual de Inspector.
 *
 * - Paso 1: CIP + periodo (YYYY-MM) + botón "Subir Excel"
 * - Paso 2: File input → parser → previsualización en tabla + totales
 * - Paso 3: Confirmar → cotizar → crear
 *
 * Endpoints:
 *   POST /finanzas/recibos-inspectores/cotizar
 *   POST /finanzas/recibos-inspectores/crear
 */
import { FileSpreadsheet, Loader2, Receipt, Upload } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { notify } from "@/errors";
import {
  useCotizarRHInspector,
  useCrearRHInspector,
} from "@/features/finanzas/hooks/useRHInspectorMensual";
import type {
  RHInspectorCotizar,
  RHInspectorCotizarIn,
} from "@/features/finanzas/schemas/rh-inspector-mensual.schema";
import { parseExcelFile } from "@/features/finanzas/utils/parse-excel";

interface RhInspectorMensualModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

type Step = 1 | 2 | 3;

export function RhInspectorMensualModal({
  open,
  onOpenChange,
  onSuccess,
}: RhInspectorMensualModalProps) {
  const [step, setStep] = useState<Step>(1);
  const [cip, setCip] = useState("");
  const [periodo, setPeriodo] = useState("");
  const [archivoExcel, setArchivoExcel] = useState<File | null>(null);
  const [parsedData, setParsedData] = useState<RHInspectorCotizar | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const cotizarMutation = useCotizarRHInspector();
  const crearMutation = useCrearRHInspector();

  const resetForm = useCallback(() => {
    setStep(1);
    setCip("");
    setPeriodo("");
    setArchivoExcel(null);
    setParsedData(null);
  }, []);

  const handleClose = useCallback(() => {
    resetForm();
    onOpenChange(false);
  }, [onOpenChange, resetForm]);

  // ── Paso 1 → 2: parsear Excel ──────────────────────────────────────
  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      try {
        const parsed = await parseExcelFile(file);
        if (!parsed.items.length) {
          notify.error("El archivo no contiene filas válidas");
          return;
        }
        setArchivoExcel(file);
        // Pre-fill CIP from file if modal CIP is empty
        if (!cip && parsed.cip) setCip(parsed.cip);
        setStep(2);
      } catch {
        notify.error("No se pudo leer el archivo Excel");
      }
    },
    [cip],
  );

  // ── Paso 2 → 3: cotizar ────────────────────────────────────────────
  const handleCotizar = useCallback(async () => {
    if (!archivoExcel) return;

    let items: RHInspectorCotizarIn["items"];
    try {
      const parsed = await parseExcelFile(archivoExcel);
      items = parsed.items;
    } catch {
      notify.error("No se pudo leer el archivo Excel");
      return;
    }

    try {
      const result = await cotizarMutation.cotizar({
        cip,
        periodo,
        items,
      });
      setParsedData(result.data);
      setStep(3);
    } catch {
      // Error handled by mutation
    }
  }, [archivoExcel, cip, periodo, cotizarMutation]);

  // ── Paso 3: crear ───────────────────────────────────────────────────
  const handleCrear = useCallback(async () => {
    if (!archivoExcel) return;

    let items: RHInspectorCotizarIn["items"];
    try {
      const parsed = await parseExcelFile(archivoExcel);
      items = parsed.items;
    } catch {
      notify.error("No se pudo leer el archivo Excel");
      return;
    }

    try {
      await crearMutation.crear({ cip, periodo, items });
      notify.success("RH Mensual de inspector creado correctamente");
      handleClose();
      onSuccess?.();
    } catch {
      // Error handled by mutation
    }
  }, [archivoExcel, cip, periodo, crearMutation, onSuccess, handleClose]);

  const isPending = cotizarMutation.isPending || crearMutation.isPending;

  return (
    <GenericModal open={open} onOpenChange={handleClose} preventClose={false}>
      <GenericModal.Content size="lg">
        <GenericModal.Header
          title=""
          className="bg-primary/[0.03] border-b border-border px-6 py-5"
        >
          <div className="flex items-center gap-3 w-full">
            <div className="p-2 bg-primary/10 rounded-xl border border-primary/20 shadow-sm shrink-0">
              <FileSpreadsheet className="h-5 w-5 text-primary" />
            </div>
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                Recibos de Honorario - Inspectores
              </span>
              <h2 className="text-2xl font-black tracking-tight text-foreground leading-tight">
                RH Mensual — Importar desde Excel
              </h2>
              <p className="hidden sm:block text-sm text-muted-foreground leading-relaxed">
                {step === 1 &&
                  "Ingresa CIP, periodo y selecciona el archivo Excel"}
                {step === 2 &&
                  "Revisa la previsualización de datos antes de continuar"}
                {step === 3 && "Confirma los datos y genera el RH mensual"}
              </p>
            </div>
            <div className="w-9 shrink-0" aria-hidden="true" />
          </div>
        </GenericModal.Header>

        <GenericModal.Body className="space-y-6">
          {/* Step indicator */}
          <div className="flex items-center gap-2">
            {[1, 2, 3].map((s) => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold border-2 ${
                    step === s
                      ? "bg-primary text-primary-foreground border-primary"
                      : step > s
                        ? "bg-primary/20 text-primary border-primary/40"
                        : "bg-muted text-muted-foreground border-muted"
                  }`}
                >
                  {s}
                </div>
                {s < 3 && (
                  <div
                    className={`h-0.5 w-8 rounded ${
                      step > s ? "bg-primary/40" : "bg-muted"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>

          {/* ── Paso 1: CIP + Periodo + Upload ── */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="cip">CIP del Inspector</Label>
                  <Input
                    id="cip"
                    value={cip}
                    onChange={(e) => setCip(e.target.value)}
                    placeholder="Ej. CIP-2024-001"
                    className="h-10 rounded-xl font-semibold"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="periodo">Periodo (YYYY-MM)</Label>
                  <Input
                    id="periodo"
                    value={periodo}
                    onChange={(e) => setPeriodo(e.target.value)}
                    placeholder="Ej. 2025-06"
                    className="h-10 rounded-xl font-semibold"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Archivo Excel</Label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <Button
                  type="button"
                  variant="outline"
                  className="w-full h-24 rounded-xl border-dashed text-muted-foreground hover:border-primary hover:text-primary cursor-pointer flex flex-col gap-2"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className="h-6 w-6" />
                  <span className="text-sm font-semibold">
                    Subir Excel con columnas: CIP, Expediente, Cantidad_Visitas
                  </span>
                </Button>
              </div>
            </div>
          )}

          {/* ── Paso 2: Previsualización ── */}
          {step === 2 && parsedData && (
            <div className="space-y-4">
              <div className="rounded-xl border border-border/60 bg-muted/10 p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Inspector:
                  </span>
                  <span className="font-bold">
                    {parsedData.inspector_nombre}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    CIP:
                  </span>
                  <span className="font-bold">{parsedData.inspector_cip}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Periodo:
                  </span>
                  <span className="font-bold">{parsedData.periodo}</span>
                </div>
              </div>

              {/* Tabla de items */}
              <div className="rounded-xl border border-border overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="text-left px-3 py-2 font-semibold text-muted-foreground">
                        Expediente
                      </th>
                      <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                        Prog.
                      </th>
                      <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                        Liq.
                      </th>
                      <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                        Costo/Unidad
                      </th>
                      <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                        Monto Contrib.
                      </th>
                      <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                        Saldo Disp.
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {parsedData.items.map((item) => (
                      <tr key={item.exp_liqui} className="hover:bg-muted/30">
                        <td className="px-3 py-2 font-mono font-semibold">
                          {item.exp_liqui}
                        </td>
                        <td className="px-3 py-2 text-right">
                          {item.inspecciones_programadas}
                        </td>
                        <td className="px-3 py-2 text-right">
                          {item.inspecciones_liquidadas}
                        </td>
                        <td className="px-3 py-2 text-right">
                          S/ {item.costo_por_inspeccion.toFixed(2)}
                        </td>
                        <td className="px-3 py-2 text-right">
                          S/ {item.monto_contribuido.toFixed(2)}
                        </td>
                        <td className="px-3 py-2 text-right">
                          S/ {item.saldo_disponible.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Totales */}
              <div className="rounded-xl border border-border bg-muted/10 p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Sub Total:
                  </span>
                  <span className="font-bold">
                    S/ {parsedData.totales.sub_total.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Descuento ({parsedData.totales.tasa_descuento_aplicada}%):
                  </span>
                  <span className="font-bold text-destructive">
                    - S/ {parsedData.totales.descuento.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between text-sm border-t border-border/60 pt-2 mt-2">
                  <span className="text-muted-foreground font-semibold">
                    Honorarios:
                  </span>
                  <span className="font-black text-primary">
                    S/ {parsedData.totales.honorarios.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {step === 2 && !parsedData && (
            <div className="flex flex-col items-center justify-center p-8 text-center">
              <p className="text-muted-foreground mb-4">
                Haz clic en "Previsualizar" para cargar los datos del Excel
              </p>
              <Button
                type="button"
                variant="outline"
                className="h-10 rounded-xl font-semibold"
                onClick={handleCotizar}
                disabled={cotizarMutation.isPending}
              >
                {cotizarMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                )}
                Previsualizar
              </Button>
            </div>
          )}
        </GenericModal.Body>

        <GenericModal.Footer className="px-6 py-4 bg-muted/30 border-t border-border">
          <div className="flex items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={
                step === 1
                  ? handleClose
                  : () => setStep((s) => (s === 3 ? 2 : 1) as Step)
              }
              disabled={isPending}
              className="h-10 rounded-xl font-semibold"
            >
              {step === 1 ? "Cancelar" : "Atrás"}
            </Button>
            {step === 2 && (
              <Button
                type="button"
                onClick={handleCotizar}
                disabled={cotizarMutation.isPending}
                className="h-10 rounded-xl font-bold gap-1.5"
              >
                {cotizarMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                Previsualizar
              </Button>
            )}
            {step === 3 && (
              <Button
                type="button"
                onClick={handleCrear}
                disabled={crearMutation.isPending}
                className="h-10 rounded-xl font-bold gap-1.5"
              >
                {crearMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                <Receipt className="h-4 w-4" />
                Crear RH
              </Button>
            )}
          </div>
        </GenericModal.Footer>

        <GenericModal.CloseX />
      </GenericModal.Content>
    </GenericModal>
  );
}
