"use client";

import { FileText, HardHat, Loader2, Receipt, User, X } from "lucide-react";
/**
 * CrearReciboInspectorModal — Modal para crear un Recibo de Honorario de Inspector.
 *
 * Usa el hook useCrearReciboInspector y el contenido BuscarAsignacionInspectorContent.
 * El usuario busca una asignación por CIP, ingresa las inspecciones del mes y confirma.
 */
import { useCallback, useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { notify } from "@/errors";
import { useCrearReciboInspector } from "@/features/finanzas/hooks/useCrearReciboInspector";
import type { LiquidacionInspectorAsignacion } from "@/features/finanzas/schemas/inspector-asignacion.schema";
import { BuscarAsignacionInspectorContent } from "./BuscarAsignacionInspectorContent";

interface CrearReciboInspectorModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function CrearReciboInspectorModal({
  open,
  onOpenChange,
  onSuccess,
}: CrearReciboInspectorModalProps) {
  const crearMutation = useCrearReciboInspector();
  const [asignacionSeleccionada, setAsignacionSeleccionada] =
    useState<LiquidacionInspectorAsignacion | null>(null);
  const [inspeccionesMes, setInspeccionesMes] = useState("");

  const handleSelectAsignacion = useCallback(
    (asignacion: LiquidacionInspectorAsignacion) => {
      setAsignacionSeleccionada(asignacion);
    },
    [],
  );

  const handleCrear = useCallback(async () => {
    if (!asignacionSeleccionada) return;
    const mes = Number(inspeccionesMes);
    if (!mes || mes <= 0) {
      notify.error("Ingresa un número de inspecciones válido");
      return;
    }
    try {
      await crearMutation.mutateAsync({
        liquidacion_inspector_id: asignacionSeleccionada.id,
        inspecciones_mes: mes,
      });
      notify.success("Recibo de honorario de inspector creado correctamente");
      setAsignacionSeleccionada(null);
      setInspeccionesMes("");
      onSuccess?.();
      onOpenChange(false);
    } catch {
      // Error handled by mutation
    }
  }, [
    asignacionSeleccionada,
    inspeccionesMes,
    crearMutation,
    onSuccess,
    onOpenChange,
  ]);

  const handleClose = () => {
    setAsignacionSeleccionada(null);
    setInspeccionesMes("");
    onOpenChange(false);
  };

  const lg = asignacionSeleccionada?.liquidacion;
  const insp = asignacionSeleccionada?.inspector;
  const esp = asignacionSeleccionada?.especialidad_revision;

  return (
    <>
      <GenericModal open={open} onOpenChange={handleClose} preventClose={false}>
        <GenericModal.Content size="md">
          <GenericModal.Header
            title=""
            className="bg-primary/[0.03] border-b border-border px-6 py-5"
          >
            <div className="flex items-center gap-3 w-full">
              <div className="p-2 bg-primary/10 rounded-xl border border-primary/20 shadow-sm shrink-0">
                <Receipt className="h-5 w-5 text-primary" />
              </div>
              <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                  Recibos de Honorario - Inspectores
                </span>
                <h2 className="text-2xl font-black tracking-tight text-foreground leading-tight">
                  {asignacionSeleccionada
                    ? "Nuevo Recibo de Honorario"
                    : "Buscar Asignación"}
                </h2>
                <p className="hidden sm:block text-sm text-muted-foreground leading-relaxed">
                  {asignacionSeleccionada
                    ? "Revisa los datos de la asignación de inspector para generar el recibo"
                    : "Busca la asignación de inspector para generar el recibo"}
                </p>
              </div>
              <div className="w-9 shrink-0" aria-hidden="true" />
            </div>
          </GenericModal.Header>

          <GenericModal.Body className="space-y-6">
            {/* Asignación seleccionada */}
            {asignacionSeleccionada ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-muted-foreground">
                    Asignación seleccionada
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setAsignacionSeleccionada(null)}
                    className="h-7 px-2 gap-1 text-xs text-muted-foreground hover:text-destructive"
                  >
                    <X className="h-3 w-3" />
                    Cambiar
                  </Button>
                </div>

                <div className="rounded-xl border border-border/60 bg-muted/10 p-4 space-y-3">
                  {/* Inspector */}
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg shrink-0">
                      <HardHat className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        Inspector
                      </p>
                      <p className="text-sm font-semibold">
                        {insp?.nombre_completo ?? "—"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        CIP: {insp?.cip ?? "—"} · DNI: {insp?.dni ?? "—"}
                      </p>
                    </div>
                  </div>

                  {/* Especialidad */}
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg shrink-0">
                      <FileText className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        Especialidad
                      </p>
                      <p className="text-sm font-semibold">
                        {esp?.nombre ?? "—"}
                      </p>
                    </div>
                  </div>

                  {/* Liquidación */}
                  {lg && (
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-primary/10 rounded-lg shrink-0">
                        <FileText className="h-4 w-4 text-primary" />
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                          Liquidación
                        </p>
                        <p className="text-sm font-semibold truncate">
                          {lg.proyecto_denominacion ?? "—"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {lg.municipalidad_nombre ?? "—"} · Exp:{" "}
                          {lg.expediente ?? "—"} · Rev: {lg.numero_revision}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Inspecciones del mes */}
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg shrink-0">
                      <User className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1">
                      <label
                        htmlFor="inspecciones-mes"
                        className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider block"
                      >
                        N° Inspecciones del Mes
                      </label>
                      <input
                        id="inspecciones-mes"
                        type="number"
                        min={1}
                        value={inspeccionesMes}
                        onChange={(e) =>
                          setInspeccionesMes(e.target.value.replace(/\D/g, ""))
                        }
                        placeholder="Ej. 2"
                        className="mt-1 w-full h-10 rounded-xl border border-input bg-background px-3 py-2 text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      />
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <BuscarAsignacionInspectorContent
                onSelect={handleSelectAsignacion}
              />
            )}
          </GenericModal.Body>

          <GenericModal.Footer className="px-6 py-4 bg-muted/30 border-t border-border">
            <div className="flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={handleClose}
                disabled={crearMutation.isPending}
                className="h-10 rounded-xl font-semibold"
              >
                Cancelar
              </Button>
              {asignacionSeleccionada && (
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
                  Crear Recibo
                </Button>
              )}
            </div>
          </GenericModal.Footer>

          <GenericModal.CloseX />
        </GenericModal.Content>
      </GenericModal>
    </>
  );
}
