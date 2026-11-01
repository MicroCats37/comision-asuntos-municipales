"use client";

import { HardHat, Loader2, Search, UserCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { useInspectorOperatividades } from "../../hooks/useInspectorOperatividades";

interface BuscarInspectorPorCipModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedOperacionId?: string;
  onSelect: (
    inspectorId: string,
    nombreCompleto: string,
    inspectorOperacionId: string,
  ) => void;
}

/** Selector histórico: busca por CIP y no condiciona el resultado por vigencia. */
export function BuscarInspectorPorCipModal({
  open,
  onOpenChange,
  selectedOperacionId,
  onSelect,
}: BuscarInspectorPorCipModalProps) {
  const [cipInput, setCipInput] = useState("");
  const [cipBuscado, setCipBuscado] = useState("");
  const [pickedOperacionId, setPickedOperacionId] = useState(
    selectedOperacionId ?? "",
  );
  const {
    data: inspectores = [],
    isLoading,
    isError,
  } = useInspectorOperatividades(
    cipBuscado,
    undefined,
    open && Boolean(cipBuscado),
  );

  useEffect(() => {
    if (!open) return;
    setCipInput("");
    setCipBuscado("");
    setPickedOperacionId(selectedOperacionId ?? "");
  }, [open, selectedOperacionId]);

  const handleSearch = () => {
    const cip = cipInput.trim();
    if (!cip) return;
    setPickedOperacionId("");
    setCipBuscado(cip);
  };

  const handleConfirm = () => {
    const picked = inspectores.find(
      (item) => item.inspector_operacion_id === pickedOperacionId,
    );
    if (!picked) return;
    onSelect(picked.id, picked.nombre_completo, picked.inspector_operacion_id);
    onOpenChange(false);
  };

  return (
    <div
      className={[
        "fixed inset-0 z-50 flex items-center justify-center p-4",
        open ? "pointer-events-auto" : "pointer-events-none",
      ].join(" ")}
    >
      <button
        type="button"
        aria-label="Cerrar"
        className={[
          "absolute inset-0 cursor-default bg-black/40 transition-opacity",
          open ? "opacity-100" : "opacity-0",
        ].join(" ")}
        onClick={() => onOpenChange(false)}
      />

      <div
        className={[
          "relative w-full max-w-xl rounded-2xl border border-border bg-card shadow-xl transition-all",
          open ? "scale-100 opacity-100" : "scale-95 opacity-0",
        ].join(" ")}
      >
        <div className="flex items-center gap-2 border-b border-border/60 px-5 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-primary/20 bg-primary/10 text-primary">
            <UserCheck className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-base font-bold text-foreground">
              Buscar inspector por CIP
            </h2>
            <p className="text-xs text-muted-foreground">
              Incluye operatividades vigentes e históricas.
            </p>
          </div>
        </div>

        <div className="max-h-[60vh] space-y-4 overflow-y-auto p-5">
          <div className="flex gap-2">
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={cipInput}
              onChange={(event) =>
                setCipInput(event.target.value.replace(/\D/g, "").slice(0, 6))
              }
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  event.stopPropagation();
                  handleSearch();
                }
              }}
              placeholder="Ingrese CIP"
              className="h-10 min-w-0 flex-1 rounded-xl border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
            <Button
              type="button"
              onClick={handleSearch}
              disabled={cipInput.length !== 6}
            >
              <Search className="h-4 w-4" />
              Buscar
            </Button>
          </div>

          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Buscando inspector...
            </div>
          )}
          {cipBuscado && !isLoading && isError && (
            <p className="text-sm text-destructive">
              No se pudo buscar el inspector.
            </p>
          )}
          {cipBuscado && !isLoading && !isError && inspectores.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No se encontraron operatividades para el CIP {cipBuscado}.
            </p>
          )}

          <div className="space-y-2">
            {inspectores.map((inspector) => {
              const selected =
                inspector.inspector_operacion_id === pickedOperacionId;
              return (
                <button
                  key={inspector.inspector_operacion_id}
                  type="button"
                  onClick={() =>
                    setPickedOperacionId(inspector.inspector_operacion_id)
                  }
                  className={[
                    "flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition-all",
                    selected
                      ? "border-primary/60 bg-primary/10 ring-2 ring-primary/30"
                      : "border-border/70 bg-card hover:border-primary/40",
                  ].join(" ")}
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-muted/80 text-muted-foreground">
                    <HardHat className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-bold text-foreground">
                      {inspector.nombre_completo}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      CIP {inspector.cip} · {inspector.numero_registro} · Cat.{" "}
                      {inspector.categoria ?? "-"}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {inspector.especialidad.nombre}
                    </p>
                    {inspector.periodo_inicio && (
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        Período: {inspector.periodo_inicio}
                        {inspector.periodo_fin
                          ? ` a ${inspector.periodo_fin}`
                          : " - Sin fecha fin"}
                      </p>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-border/60 px-5 py-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              handleConfirm();
            }}
            disabled={!pickedOperacionId}
          >
            Asignar inspector
          </Button>
        </div>
      </div>
    </div>
  );
}
