"use client";

/**
 * RhInspectorMensualModal — Modal de 4 pasos para RH Mensual de Inspector.
 *
 * - Paso 1: Ingresar CIP + Periodo
 * - Paso 2: Listado de candidatas con selección por checkbox + cantidad_visitas
 * - Paso 3: Previsualización de totales
 * - Paso 4: Confirmar → crear
 *
 * Endpoints:
 *   GET  /finanzas/recibos-inspectores/candidatos?cip={cip}&periodo={periodo}
 *   POST /finanzas/recibos-inspectores/cotizar
 *   POST /finanzas/recibos-inspectores/crear
 */
import { FileSpreadsheet, Loader2, Receipt, Search, X } from "lucide-react";
import { useCallback, useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { notify } from "@/errors";
import {
  useCotizarRHInspector,
  useCrearRHInspector,
} from "@/features/finanzas/hooks/useRHInspectorMensual";
import { useCandidatasInspector } from "@/features/finanzas/hooks/useCandidatasInspector";
import type {
  InspectorCandidataItem,
  RHInspectorCotizar,
  RHInspectorCotizarIn,
} from "@/features/finanzas/schemas/rh-inspector-mensual.schema";

interface RhInspectorMensualModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

type Step = 1 | 2 | 3 | 4;

/** Per-candidate selection: cantidad_visitas chosen by the user */
export interface InspectorCandidateSelection {
  cantidad_visitas: number;
}

export function RhInspectorMensualModal({
  open,
  onOpenChange,
  onSuccess,
}: RhInspectorMensualModalProps) {
  const [step, setStep] = useState<Step>(1);
  const [cip, setCip] = useState("");
  const [periodo, setPeriodo] = useState("");
  const [cotizarResult, setCotizarResult] = useState<RHInspectorCotizar | null>(null);

  /**
   * Map of InspectorCandidataItem.liquidacion_categoria_visitas_id → selection.
   * Only entries for checked rows are present.
   */
  const [selectedRows, setSelectedRows] = useState<
    Record<string, InspectorCandidateSelection>
  >({});

  const cotizarMutation = useCotizarRHInspector();
  const crearMutation = useCrearRHInspector();

  const {
    data: candidatosData,
    isLoading: isLoadingCandidatos,
    isError: isErrorCandidatos,
    refetch: refetchCandidatos,
  } = useCandidatasInspector({
    cip,
    periodo,
    enabled: false,
  });

  const candidatos: InspectorCandidataItem[] = candidatosData?.candidatos ?? [];
  const inspectorInfo = candidatosData
    ? {
        id: candidatosData.inspector_id,
        nombre: candidatosData.inspector_nombre,
        cip: candidatosData.inspector_cip,
        dni: candidatosData.inspector_dni,
      }
    : null;

  const resetForm = useCallback(() => {
    setStep(1);
    setCip("");
    setPeriodo("");
    setCotizarResult(null);
    setSelectedRows({});
  }, []);

  const handleClose = useCallback(() => {
    resetForm();
    onOpenChange(false);
  }, [onOpenChange, resetForm]);

  // ── Paso 1 → 2: buscar candidatas ────────────────────────────────────
  const handleBuscar = useCallback(async () => {
    if (!cip.trim()) {
      notify.error("Ingresa el CIP del inspector");
      return;
    }
    // Periodo es opcional para buscar candidatas (puede ingresarse luego)
    if (periodo.trim() && !/^\d{4}-\d{2}$/.test(periodo.trim())) {
      notify.error("El periodo debe tener formato YYYY-MM");
      return;
    }
    setSelectedRows({});
    setCotizarResult(null);
    try {
      await refetchCandidatos();
      setStep(2);
    } catch {
      notify.error("No se pudieron buscar las candidatas");
    }
  }, [cip, periodo, refetchCandidatos]);

  // ── Toggle row selection ────────────────────────────────────────────────
  const isSelected = useCallback(
    (id: string) => id in selectedRows,
    [selectedRows],
  );

  const toggleRow = useCallback(
    (c: InspectorCandidataItem, checked: boolean) => {
      setSelectedRows((prev) => {
        if (checked) {
          return {
            ...prev,
            [c.liquidacion_categoria_visitas_id]: {
              cantidad_visitas: Math.min(1, c.saldo_disponible),
            },
          };
        } else {
          const next = { ...prev };
          delete next[c.liquidacion_categoria_visitas_id];
          return next;
        }
      });
    },
    [],
  );

  const updateCantidadVisitas = useCallback(
    (id: string, value: number) => {
      setSelectedRows((prev) => ({
        ...prev,
        [id]: { cantidad_visitas: value },
      }));
    },
    [],
  );

  // ── Paso 2 → 3: cotizar ──────────────────────────────────────────────
  const handleCotizar = useCallback(async () => {
    const selectedIds = Object.keys(selectedRows);
    if (selectedIds.length === 0) {
      notify.error("Selecciona al menos una candidata");
      return;
    }

    // Periodo es requerido para cotizar
    if (!periodo.trim()) {
      notify.error("Ingresa el periodo (YYYY-MM) antes de cotizar");
      return;
    }
    if (!/^\d{4}-\d{2}$/.test(periodo.trim())) {
      notify.error("El periodo debe tener formato YYYY-MM");
      return;
    }

    // Validate cantidad_visitas per row
    for (const c of candidatos) {
      const sel = selectedRows[c.liquidacion_categoria_visitas_id];
      if (!sel) continue;
      if (sel.cantidad_visitas <= 0) {
        notify.error(
          `Cantidad visitas debe ser mayor a 0 para expediente ${c.expediente}`,
        );
        return;
      }
      if (sel.cantidad_visitas > c.saldo_disponible) {
        notify.error(
          `Cantidad visitas excede saldo disponible (${c.saldo_disponible}) para expediente ${c.expediente}`,
        );
        return;
      }
    }

    const items: RHInspectorCotizarIn["items"] = candidatos
      .filter((c) => selectedIds.includes(c.liquidacion_categoria_visitas_id))
      .map((c) => ({
        liquidacion_categoria_visitas_id: c.liquidacion_categoria_visitas_id,
        cantidad_visitas: selectedRows[c.liquidacion_categoria_visitas_id].cantidad_visitas,
      }));

    try {
      const result = await cotizarMutation.cotizar({
        cip,
        periodo,
        items,
      });
      setCotizarResult(result.data);
      setStep(3);
    } catch {
      // Error handled by mutation
    }
  }, [selectedRows, candidatos, cip, periodo, cotizarMutation]);

  // ── Paso 3 → 4: confirmar ────────────────────────────────────────────
  const handleConfirmar = useCallback(() => {
    setStep(4);
  }, []);

  // ── Paso 4: crear ───────────────────────────────────────────────────
  const handleCrear = useCallback(async () => {
    if (!cotizarResult) return;

    const selectedIds = Object.keys(selectedRows);
    const items: RHInspectorCotizarIn["items"] = candidatos
      .filter((c) => selectedIds.includes(c.liquidacion_categoria_visitas_id))
      .map((c) => ({
        liquidacion_categoria_visitas_id: c.liquidacion_categoria_visitas_id,
        cantidad_visitas: selectedRows[c.liquidacion_categoria_visitas_id].cantidad_visitas,
      }));

    try {
      await crearMutation.crear({ cip, periodo, items });
      notify.success("RH Mensual de inspector creado correctamente");
      handleClose();
      onSuccess?.();
    } catch {
      // Error handled by mutation
    }
  }, [cotizarResult, selectedRows, candidatos, cip, periodo, crearMutation, handleClose, onSuccess]);

  const isPending = cotizarMutation.isPending || crearMutation.isPending;
  const selectedCount = Object.keys(selectedRows).length;

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
                RH Mensual — Inspectores
              </h2>
              <p className="hidden sm:block text-sm text-muted-foreground leading-relaxed">
                {step === 1 && "Ingresa el CIP del inspector"}
                {step === 2 && "Selecciona las candidatas e ingresa la cantidad de visitas por item"}
                {step === 3 && "Revisa la previsualización antes de confirmar"}
                {step === 4 && "Confirma los datos y genera el RH mensual"}
              </p>
            </div>
            <div className="w-9 shrink-0" aria-hidden="true" />
          </div>
        </GenericModal.Header>

        <GenericModal.Body className="space-y-6">
          {/* Step indicator */}
          <div className="flex items-center gap-2">
            {[1, 2, 3, 4].map((s) => (
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
                {s < 4 && (
                  <div
                    className={`h-0.5 w-8 rounded ${
                      step > s ? "bg-primary/40" : "bg-muted"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>

          {/* ── Paso 1: CIP ── */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="max-w-xs">
                <div className="space-y-2">
                  <Label htmlFor="cip">CIP del Inspector</Label>
                  <Input
                    id="cip"
                    value={cip}
                    onChange={(e) => setCip(e.target.value)}
                    placeholder="Ej. 12345"
                    className="h-10 rounded-xl font-semibold"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void handleBuscar();
                    }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* ── Paso 2: Listado de Candidatas ── */}
          {step === 2 && (
            <div className="space-y-4">
              {/* Inspector info bar */}
              {inspectorInfo && (
                <div className="rounded-xl border border-border/60 bg-muted/10 p-4 space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground font-semibold">
                      Inspector:
                    </span>
                    <span className="font-bold">{inspectorInfo.nombre}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground font-semibold">
                      CIP:
                    </span>
                    <span className="font-bold">{inspectorInfo.cip}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground font-semibold">
                      DNI:
                    </span>
                    <span className="font-bold">{inspectorInfo.dni}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm gap-2">
                    <span className="text-muted-foreground font-semibold shrink-0">
                      Periodo:
                    </span>
                    <Input
                      id="periodo-step2"
                      value={periodo}
                      onChange={(e) => setPeriodo(e.target.value)}
                      placeholder="YYYY-MM"
                      className="h-7 w-28 text-xs rounded border border-input bg-background font-semibold text-right"
                    />
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground font-semibold">
                      Candidatas encontradas:
                    </span>
                    <span className="font-bold">{candidatos.length}</span>
                  </div>
                </div>
              )}

              {/* Row-based grid (compact, horizontal, spreadsheet-like) */}
              {isLoadingCandidatos ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : isErrorCandidatos ? (
                <div className="flex flex-col items-center justify-center p-8 text-destructive text-sm">
                  Error al cargar las candidatas
                </div>
              ) : (
                <ScrollArea className="max-h-[520px] pr-1">
                  {/* Header row */}
                  <div className="flex items-center gap-3 px-3 py-2 bg-muted/40 rounded-t-lg border border-b-0 border-border text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    <div className="w-6 shrink-0" />
                    <div className="w-28 shrink-0">Expediente</div>
                    <div className="flex-1 min-w-0">Especialidad</div>
                    <div className="w-16 shrink-0 text-right">Prog.</div>
                    <div className="w-16 shrink-0 text-right">Liq.</div>
                    <div className="w-16 shrink-0 text-right">Saldo</div>
                    <div className="w-20 shrink-0 text-right">Costo/Und.</div>
                    <div className="w-20 shrink-0">Cant. Visitas</div>
                  </div>
                  <div className="border border-t-0 border-border rounded-b-lg overflow-hidden">
                    {candidatos.map((c) => {
                      const selected = isSelected(c.liquidacion_categoria_visitas_id);
                      const cantidad = selectedRows[c.liquidacion_categoria_visitas_id]?.cantidad_visitas ?? 0;
                      return (
                        <div
                          key={c.liquidacion_categoria_visitas_id}
                          className={`flex items-center gap-3 px-3 py-2 border-b border-border/50 last:border-b-0 transition-all duration-150 ${
                            selected
                              ? "bg-primary/[0.04]"
                              : "hover:bg-muted/30"
                          }`}
                        >
                          {/* Checkbox */}
                          <Checkbox
                            id={`row-${c.liquidacion_categoria_visitas_id}`}
                            checked={selected}
                            onCheckedChange={(v) => toggleRow(c, !!v)}
                            className="shrink-0"
                          />

                          {/* Expediente (read-only) */}
                          <div
                            className="w-28 shrink-0 cursor-pointer"
                            onClick={() => toggleRow(c, !selected)}
                          >
                            <p className="font-mono font-bold text-xs text-foreground truncate">
                              {c.expediente ?? "—"}
                            </p>
                          </div>

                          {/* Especialidad (read-only) */}
                          <div
                            className="flex-1 min-w-0 cursor-pointer"
                            onClick={() => toggleRow(c, !selected)}
                          >
                            <p className="text-xs font-medium text-foreground truncate">
                              {c.especialidad_nombre}
                            </p>
                          </div>

                          {/* Inspecciones programadas (read-only) */}
                          <div
                            className="w-16 shrink-0 text-right cursor-pointer"
                            onClick={() => toggleRow(c, !selected)}
                          >
                            <p className="text-xs font-semibold text-foreground">
                              {c.cantidad_visitas}
                            </p>
                          </div>

                          {/* Inspecciones pagadas (read-only) */}
                          <div
                            className="w-16 shrink-0 text-right cursor-pointer"
                            onClick={() => toggleRow(c, !selected)}
                          >
                            <p className="text-xs text-muted-foreground">
                              {c.inspecciones_pagadas}
                            </p>
                          </div>

                          {/* Saldo disponible (read-only) */}
                          <div
                            className="w-16 shrink-0 text-right cursor-pointer"
                            onClick={() => toggleRow(c, !selected)}
                          >
                            <p className={`text-xs font-semibold ${
                              c.saldo_disponible === 0
                                ? "text-muted-foreground"
                                : "text-foreground"
                            }`}>
                              {c.saldo_disponible}
                            </p>
                          </div>

                          {/* Costo por inspección (read-only) */}
                          <div
                            className="w-20 shrink-0 text-right cursor-pointer"
                            onClick={() => toggleRow(c, !selected)}
                          >
                            <p className="text-xs font-black text-primary">
                              {c.costo_por_inspeccion != null
                                ? `S/ ${c.costo_por_inspeccion.toFixed(2)}`
                                : "—"}
                            </p>
                          </div>

                          {/* Cantidad visitas (inline number input) */}
                          <Input
                            id={`cant-visitas-${c.liquidacion_categoria_visitas_id}`}
                            type="number"
                            min={1}
                            max={c.saldo_disponible}
                            value={cantidad || ""}
                            onChange={(e) =>
                              updateCantidadVisitas(
                                c.liquidacion_categoria_visitas_id,
                                Number(e.target.value),
                              )
                            }
                            disabled={!selected}
                            placeholder="0"
                            className="w-20 shrink-0 h-7 text-xs rounded border border-input bg-background disabled:opacity-40 disabled:cursor-not-allowed"
                          />
                        </div>
                      );
                    })}
                  </div>
                  {candidatos.length === 0 && (
                    <div className="py-12 text-center text-muted-foreground text-sm border border-t-0 border-border rounded-b-lg">
                      No hay liquidaciones candidatas para este inspector
                    </div>
                  )}
                </ScrollArea>
              )}

              <p className="text-xs text-muted-foreground text-right">
                {selectedCount} de {candidatos.length} seleccionada(s)
              </p>
            </div>
          )}

          {/* ── Paso 3: Previsualización — Tabla de Liquidación ── */}
          {step === 3 && cotizarResult && (
            <div className="space-y-4">
              {/* Header info */}
              <div className="rounded-xl border border-border/60 bg-muted/10 p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Inspector:
                  </span>
                  <span className="font-bold">
                    {cotizarResult.inspector.nombre_completo}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    CIP:
                  </span>
                  <span className="font-bold">{cotizarResult.inspector.cip}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground font-semibold">
                    Periodo:
                  </span>
                  <span className="font-bold">{cotizarResult.periodo}</span>
                </div>
              </div>

              {/* Tabla de items con pie de totales —对齐 like delegado */}
              <div className="rounded-xl border border-border overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="text-left px-3 py-2 font-semibold text-muted-foreground">
                        Expediente
                      </th>
                      <th className="text-left px-3 py-2 font-semibold text-muted-foreground">
                        Administrado
                      </th>
                      <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                        Prog.
                      </th>
                      <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                        Pag. Mes Ant.
                      </th>
                      <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                        Liq.
                      </th>
                      <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                        Saldo
                      </th>
                      <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                        Importe Ref.
                      </th>
                      <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                        Costo/Unidad
                      </th>
                      <th className="text-right px-3 py-2 font-semibold text-muted-foreground">
                        Monto Contrib.
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/60">
                    {cotizarResult.items.map((item) => (
                      <tr key={item.exp_liqui} className="hover:bg-muted/30">
                        <td className="px-3 py-2 font-mono font-semibold">
                          {item.exp_liqui}
                        </td>
                        <td className="px-3 py-2 text-muted-foreground max-w-[160px] truncate">
                          {item.nombre_propietario || "—"}
                        </td>
                        <td className="px-3 py-2 text-right">
                          {item.inspecciones_programadas}
                        </td>
                        <td className="px-3 py-2 text-right text-muted-foreground">
                          {item.inspecciones_pagadas_hasta_mes_anterior}
                        </td>
                        <td className="px-3 py-2 text-right font-semibold">
                          {item.inspecciones_liquidadas}
                        </td>
                        <td className="px-3 py-2 text-right">
                          {item.saldo_restante}
                        </td>
                        <td className="px-3 py-2 text-right">
                          S/ {item.importe_bruto.toFixed(2)}
                        </td>
                        <td className="px-3 py-2 text-right">
                          S/ {item.costo_por_inspeccion.toFixed(2)}
                        </td>
                        <td className="px-3 py-2 text-right font-semibold">
                          S/ {item.monto_contribuido.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  {/* Footer con totales — alineado con las columnas de la tabla */}
                  <tfoot className="bg-muted/30 border-t-2 border-border">
                    <tr>
                      <td colSpan={8} className="px-3 py-2 text-right font-semibold text-muted-foreground">
                        Sub Total:
                      </td>
                      <td className="px-3 py-2 text-right font-bold">
                        S/ {cotizarResult.totales.sub_total.toFixed(2)}
                      </td>
                    </tr>
                    <tr>
                      <td colSpan={8} className="px-3 py-1.5 text-right text-muted-foreground">
                        Descuento ({cotizarResult.totales.tasa_descuento_aplicada}%):
                      </td>
                      <td className="px-3 py-1.5 text-right font-bold text-destructive">
                        - S/ {cotizarResult.totales.descuento.toFixed(2)}
                      </td>
                    </tr>
                    <tr className="border-t border-border">
                      <td colSpan={8} className="px-3 py-2 text-right font-bold text-foreground">
                        Honorarios:
                      </td>
                      <td className="px-3 py-2 text-right font-black text-primary text-sm">
                        S/ {cotizarResult.totales.honorarios.toFixed(2)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          )}
        </GenericModal.Body>

        <GenericModal.Footer className="px-6 py-4 bg-muted/30 border-t border-border">
          <div className="flex items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                if (step === 1) {
                  handleClose();
                } else {
                  setStep((s) =>
                    (s === 4 ? 3 : s === 3 ? 2 : 1) as Step,
                  );
                }
              }}
              disabled={isPending}
              className="h-10 rounded-xl font-semibold"
            >
              {step === 1 ? "Cancelar" : "Atrás"}
            </Button>

            {step === 1 && (
              <Button
                type="button"
                onClick={handleBuscar}
                className="h-10 rounded-xl font-bold gap-1.5"
              >
                <Search className="h-4 w-4" />
                Buscar Candidatas
              </Button>
            )}

            {step === 2 && (
              <Button
                type="button"
                onClick={handleCotizar}
                disabled={cotizarMutation.isPending || selectedCount === 0}
                className="h-10 rounded-xl font-bold gap-1.5"
              >
                {cotizarMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" />
                )}
                Cotizar ({selectedCount})
              </Button>
            )}

            {step === 3 && (
              <Button
                type="button"
                onClick={handleConfirmar}
                className="h-10 rounded-xl font-bold gap-1.5"
              >
                Confirmar
              </Button>
            )}

            {step === 4 && (
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
