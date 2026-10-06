"use client";

import { useMutation } from "@tanstack/react-query";
import { Calculator, HardHat, Loader2 } from "lucide-react";
/**
 * TarifasVisitasSinPreviaSmartField — Smart field de IO sin liquidación previa.
 *
 * Incluye dentro del mismo card-wrapper:
 *  · Selector de categoría (C1/C2/C3/C4) — radio group
 *  · Botón "Inspector Asignado" — abre SeleccionarInspectorModal via callback
 *  · Tarifa informativa
 *  · Cotización auto-debounceada (400ms)
 *
 * Lee del form vía `useWatch`:
 *  - `cantidad_visitas` (vive en Datos del Trámite via IncrementerInput)
 *  - `categoria`, `tarifa_visitas_id`
 *
 * NO persiste en form: solo lee. La categoría se escribe via `methods.setValue`
 * cuando el usuario hace click en un chip.
 *
 * Endpoint: POST /liquidaciones/inspeccion-obra/cotizar
 */
import { useEffect, useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import { useWatch } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { useDebounce } from "@/hooks/system/useDebounce";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import { useTarifasVigentesVisitas } from "../../hooks/useTarifasVigentes";

interface CotizacionVisitasOutput {
  datos: {
    entrada: {
      datos: { cantidad_visitas: number; categoria: string };
      tarifa: { tarifa_visitas_id: string };
    };
    tarifa: { id: string; costo_por_visita: number };
    variables_financieras: { igv: { valor: number }; uit: { valor: number } };
  };
  calculo: { monto_bruto: number; subtotal: number; total: number };
}

interface TarifasVisitasSinPreviaSmartFieldProps {
  // biome-ignore lint/suspicious/noExplicitAny: Pattern matches existing smart fields (CotizacionM2SmartField, CotizacionPorcentajeSmartField).
  methods: UseFormReturn<any>;
  /** Inspector ya seleccionado (nombre para mostrar en el botón) */
  inspectorNombre?: string;
  /** Callback al hacer click en el botón "Inspector Asignado" */
  onOpenInspector: () => void;
  /** Deshabilita el botón si no hay categoría seleccionada */
  disabled?: boolean;
}

const toNumber = (value: unknown): number => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};
const formatSoles = (value: unknown): string =>
  `S/ ${toNumber(value).toFixed(2)}`;

const normalizeCategoria = (cat: string): string => {
  if (["1", "2", "3", "4"].includes(cat)) return `C${cat}`;
  return cat;
};

export function TarifasVisitasSinPreviaSmartField({
  methods,
  inspectorNombre,
  onOpenInspector,
  disabled,
}: TarifasVisitasSinPreviaSmartFieldProps) {
  const [quote, setQuote] = useState<CotizacionVisitasOutput | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Lee del form (sin local state, sin bridge)
  const cantidadVisitasForm = useWatch({
    control: methods.control,
    name: "cantidad_visitas",
  });
  const categoria = useWatch({
    control: methods.control,
    name: "categoria",
  }) as string | undefined;
  const tarifaVisitasId = useWatch({
    control: methods.control,
    name: "tarifa_visitas_id",
  }) as string | undefined;

  // Tarifas para mostrar info de la categoría seleccionada
  const { data: tarifasData, isLoading: isTarifasLoading } =
    useTarifasVigentesVisitas();
  const tarifas = tarifasData?.tarifas ?? [];

  // Categorías únicas (orden estable: C1, C2, C3, C4)
  const categorias = Array.from(
    new Set(tarifas.map((t) => normalizeCategoria(t.categoria))),
  ).sort();

  // Auto-seleccionar primera categoría si no hay
  useEffect(() => {
    if (tarifas.length > 0 && !categoria && categorias[0]) {
      methods.setValue("categoria", categorias[0] as never, {
        shouldValidate: false,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tarifas]);

  // Tarifas que coinciden con la categoría seleccionada
  const tarifasDeCategoria = tarifas.filter(
    (t) => normalizeCategoria(t.categoria) === categoria,
  );

  // Auto-seleccionar primera tarifa cuando cambia la categoría
  useEffect(() => {
    if (!categoria || tarifasDeCategoria.length === 0) return;
    const tarifaValida = tarifasDeCategoria.find(
      (t) => t.id === tarifaVisitasId,
    );
    if (!tarifaValida) {
      methods.setValue("tarifa_visitas_id", tarifasDeCategoria[0].id, {
        shouldValidate: false,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoria, tarifasDeCategoria]);

  const tarifaSeleccionada = tarifas.find((t) => t.id === tarifaVisitasId);

  const cotizacionMutation = useMutation({
    mutationFn: async (payload: {
      cantidad_visitas: number;
      categoria: string;
      tarifa_visitas_id: string;
    }): Promise<CotizacionVisitasOutput> => {
      const { data } = await api.post(
        "/liquidaciones/inspeccion-obra/cotizar",
        {
          liquidacion_especifica: {
            datos: {
              cantidad_visitas: payload.cantidad_visitas,
              categoria: payload.categoria,
            },
            tarifa: { tarifa_visitas_id: payload.tarifa_visitas_id },
          },
        },
      );
      return data.data as CotizacionVisitasOutput;
    },
    onSuccess: (result) => {
      setQuote(result);
      setError(null);
    },
    onError: (err) => {
      setQuote(null);
      setError(
        err instanceof Error ? err.message : "Error al calcular cotización",
      );
    },
  });

  const cantidadVisitas = toNumber(cantidadVisitasForm);
  const categoriaNorm = categoria ? normalizeCategoria(categoria) : "";
  const debouncedCantidad = useDebounce(cantidadVisitas, 400);

  useEffect(() => {
    if (
      !debouncedCantidad ||
      debouncedCantidad <= 0 ||
      !tarifaVisitasId ||
      !categoriaNorm
    ) {
      setQuote(null);
      setError(null);
      return;
    }
    cotizacionMutation.mutate({
      cantidad_visitas: debouncedCantidad,
      categoria: categoriaNorm,
      tarifa_visitas_id: tarifaVisitasId,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedCantidad, tarifaVisitasId, categoriaNorm]);

  const isCalculating = cotizacionMutation.isPending;

  return (
    <div className="space-y-4 rounded-xl border border-primary/20 bg-primary/[0.03] p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <Calculator className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
          Cálculo de Visitas
        </h3>
        {isCalculating && (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
        )}
      </div>

      {/* Botón Inspector Asignado (top) */}
      <div className="rounded-xl border border-border/50 bg-card p-3 space-y-2">
        <div className="flex items-center gap-2">
          <HardHat className="h-4 w-4 text-primary" />
          <h4 className="text-sm font-semibold uppercase tracking-wide">
            Inspector Asignado
          </h4>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onOpenInspector}
          disabled={disabled}
          className="w-full gap-1"
        >
          <HardHat className="h-3 w-3" />
          {inspectorNombre
            ? `Inspector: ${inspectorNombre}`
            : "Seleccionar inspector"}
        </Button>
      </div>

      {/* Selector de Categoría — sin label ni dot, solo el nombre */}
      {isTarifasLoading ? (
        <div className="h-10 rounded-lg border bg-card animate-pulse" />
      ) : categorias.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No hay tarifas vigentes de Inspección de Obra
        </p>
      ) : (
        <div
          className="flex flex-row flex-wrap gap-2"
          role="radiogroup"
          aria-label="Categorías"
        >
          {categorias.map((cat) => {
            const isSelected = categoria === cat;
            return (
              <label
                key={cat}
                role="radio"
                aria-checked={isSelected}
                className={cn(
                  "rounded-lg border bg-background px-3 py-2 transition-all duration-200 text-left flex-1 min-w-[100px] flex items-center justify-center cursor-pointer text-sm font-semibold",
                  isSelected
                    ? "border-primary ring-1 ring-primary/30 bg-primary/5 text-primary"
                    : "border-border text-foreground hover:border-primary/40",
                )}
              >
                <span>Categoría {cat}</span>
                <input
                  type="radio"
                  name="categoria_io"
                  className="sr-only"
                  checked={isSelected}
                  onChange={() => {
                    methods.setValue("categoria", cat as never, {
                      shouldValidate: true,
                    });
                  }}
                />
              </label>
            );
          })}
        </div>
      )}

      {error && <p className="text-xs text-destructive">{error}</p>}

      {isCalculating && !quote && (
        <p className="text-xs text-muted-foreground animate-pulse">
          Calculando cotización…
        </p>
      )}

      {quote && (
        <div className="space-y-2 rounded-lg border border-border bg-card p-3">
          <div className="grid grid-cols-2 gap-1 text-sm">
            <span className="text-muted-foreground">Costo por visita:</span>
            <span className="font-medium text-right">
              {formatSoles(
                quote.datos?.tarifa?.costo_por_visita ??
                  tarifaSeleccionada?.costo_por_visita,
              )}
            </span>
            <span className="text-muted-foreground">Cantidad de visitas:</span>
            <span className="font-medium text-right tabular-nums">
              {quote.datos?.entrada?.datos?.cantidad_visitas ?? cantidadVisitas}
            </span>
            <span className="text-muted-foreground">Subtotal:</span>
            <span className="font-medium text-right">
              {formatSoles(quote.calculo?.subtotal)}
            </span>
            <span className="text-muted-foreground">I.G.V.:</span>
            <span className="font-medium text-right">
              {formatSoles(
                toNumber(quote.calculo?.total) -
                  toNumber(quote.calculo?.subtotal),
              )}
            </span>
          </div>
          <div className="border-t border-border pt-1.5 flex justify-between font-semibold text-sm">
            <span>Total a Pagar:</span>
            <span className="text-primary">
              {formatSoles(quote.calculo?.total)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
