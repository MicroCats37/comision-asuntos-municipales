"use client";

import { FileText, Loader2, Receipt, User, X } from "lucide-react";
/**
 * ReciboHonorarioFormModal — Modal para crear un Recibo de Honorario.
 *
 * Usa el hook useCrearReciboDelegado y el contenido BuscarAsignacionDelegadoContent.
 * El usuario busca una asignación por CIP, selecciona, y confirma la creación.
 */
import { useCallback, useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { notify } from "@/errors";
import { useCrearReciboDelegado } from "@/features/finanzas/hooks/useCrearReciboDelegado";
import type { LiquidacionDelegado } from "@/features/finanzas/schemas/delegado-asignacion.schema";
import { BuscarAsignacionDelegadoContent } from "./BuscarAsignacionDelegadoContent";

interface ReciboHonorarioFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function ReciboHonorarioFormModal({
  open,
  onOpenChange,
  onSuccess,
}: ReciboHonorarioFormModalProps) {
  const crearMutation = useCrearReciboDelegado();
  const [asignacionSeleccionada, setAsignacionSeleccionada] =
    useState<LiquidacionDelegado | null>(null);

  const handleSelectAsignacion = useCallback(
    (asignacion: LiquidacionDelegado) => {
      setAsignacionSeleccionada(asignacion);
    },
    [],
  );

  const handleCrear = useCallback(async () => {
    if (!asignacionSeleccionada) return;
    try {
      await crearMutation.mutateAsync({
        liquidacion_delegado_id: asignacionSeleccionada.id,
      });
      notify.success("Recibo de honorario creado correctamente");
      setAsignacionSeleccionada(null);
      onSuccess?.();
      onOpenChange(false);
    } catch {
      // Error handled by mutation
    }
  }, [asignacionSeleccionada, crearMutation, onSuccess, onOpenChange]);

  const handleClose = () => {
    setAsignacionSeleccionada(null);
    onOpenChange(false);
  };

  const lg = asignacionSeleccionada?.liquidacion;
  const del = asignacionSeleccionada?.delegado;
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
                  Recibos de Honorario
                </span>
                <h2 className="text-2xl font-black tracking-tight text-foreground leading-tight">
                  {asignacionSeleccionada
                    ? "Nuevo Recibo de Honorario"
                    : "Buscar Asignación"}
                </h2>
                <p className="hidden sm:block text-sm text-muted-foreground leading-relaxed">
                  {asignacionSeleccionada
                    ? "Revisa los datos de la asignación de delegado para generar el recibo"
                    : "Busca la asignación de delegado para generar el recibo"}
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
                  {/* Delegado */}
                  <div className="flex items-start gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg shrink-0">
                      <User className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        Delegado
                      </p>
                      <p className="text-sm font-semibold">
                        {del?.nombre_completo ?? "—"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        CIP: {del?.cip ?? "—"} · DNI: {del?.dni ?? "—"}
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
                </div>
              </div>
            ) : (
              <BuscarAsignacionDelegadoContent
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
