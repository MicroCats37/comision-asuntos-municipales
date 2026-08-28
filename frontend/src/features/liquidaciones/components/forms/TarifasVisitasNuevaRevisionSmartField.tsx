"use client";

import { useMutation } from "@tanstack/react-query";
import { Calculator, Loader2, Minus, Plus } from "lucide-react";
/**
 * TarifasVisitasNuevaRevisionSmartField — Smart Field de tarifas para nueva revisión de IO.
 *
 * VARÍA POR 2 VALORES: cantidad_visitas + categoria (el costo_por_visita depende de la
 * categoría, y el total = cantidad_visitas × costo_por_visita + IGV).
 *
 * NOTA: el numero_revision NO altera el monto en IO — el flujo backend lo fija en 1
 * y el endpoint /cotizar no lo recibe. Este smart field calcula con lo que el backend
 * realmente cotiza (cantidad_visitas + categoria).
 *
 * Endpoints:
 * - GET /liquidaciones/inspeccion-obra/tarifas/vigentes → { tarifas: [{ id, costo_por_visita, categoria }] }
 *   (via useTarifasVigentesVisitas)
 * - POST /liquidaciones/inspeccion-obra/cotizar → { datos: {...}, calculo: { monto_bruto, subtotal, total } }
 */
import { useEffect, useMemo, useState } from "react";
import { useDebounce } from "@/hooks/system/useDebounce";
import api from "@/lib/api";
import { useTarifasVigentesVisitas } from "../../hooks/useTarifasVigentes";

interface CotizacionVisitasOutput {
  datos: {
    entrada: {
      datos: { cantidad_visitas: number; categoria: string };
      tarifa: { tarifa_visitas_id: string };
    };
    tarifa: { id: string; costo_por_visita: number };
    variables_financieras: {
      igv: { valor: number };
      uit: { valor: number };
    };
  };
  calculo: {
    monto_bruto: number;
    subtotal: number;
    total: number;
  };
}

interface TarifasVisitasNuevaRevisionSmartFieldProps {
  /** Cantidad de visitas seleccionada (controlada por el form) */
  cantidadVisitas: number;
  /** Categoría seleccionada (viene del form) */
  categoria: string;
  /** Tarifa seleccionada (viene del form) */
  tarifaVisitasId: string | null;
  onCantidadVisitasChange: (cantidad: number) => void;
  onCategoriaChange: (categoria: string) => void;
  onTarifaChange: (tarifaId: string) => void;
}

const toNumber = (value: unknown): number => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};
const formatSoles = (value: unknown): string =>
  `S/ ${toNumber(value).toFixed(2)}`;

export function TarifasVisitasNuevaRevisionSmartField({
  cantidadVisitas,
  categoria,
  tarifaVisitasId,
  onCantidadVisitasChange,
  onCategoriaChange,
  onTarifaChange,
}: TarifasVisitasNuevaRevisionSmartFieldProps) {
  const [quote, setQuote] = useState<CotizacionVisitasOutput | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: tarifasData, isLoading } = useTarifasVigentesVisitas();
  const tarifas = tarifasData?.tarifas ?? [];

  // Categorías únicas disponibles (orden estables: A, B, C...)
  const categorias = useMemo(
    () => [...new Set((tarifas || []).map((t) => t.categoria))].sort(),
    [tarifas],
  );
  const tarifasDeCategoria = useMemo(
    () => (tarifas || []).filter((t) => t.categoria === categoria),
    [tarifas, categoria],
  );
  const tarifaSeleccionada = useMemo(
    () => (tarifas || []).find((t) => t.id === tarifaVisitasId) || null,
    [tarifas, tarifaVisitasId],
  );

  // Preseleccionar la primera categoría + su primera tarifa si no hay selección
  useEffect(() => {
    if (tarifas && tarifas.length > 0) {
      if (!categoria) {
        const primeraCategoria = categorias[0];
        if (primeraCategoria) {
          onCategoriaChange(primeraCategoria);
          const tarifaPrimera = tarifas.find(
            (t) => t.categoria === primeraCategoria,
          );
          if (tarifaPrimera) onTarifaChange(tarifaPrimera.id);
        }
      } else if (!tarifaVisitasId) {
        const tarifaCategoria = tarifas.find((t) => t.categoria === categoria);
        if (tarifaCategoria) onTarifaChange(tarifaCategoria.id);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tarifas]);

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
      return data.data;
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

  const debouncedTarifa = useDebounce(tarifaVisitasId, 400);
  const debouncedCantidad = useDebounce(cantidadVisitas, 400);

  // Auto-recalcular cuando cambia cantidad_visitas o tarifa (debounced)
  useEffect(() => {
    const v = toNumber(debouncedCantidad);

    if (!v || v <= 0 || !debouncedTarifa) {
      setQuote(null);
      setError(null);
      return;
    }

    cotizacionMutation.mutate({
      cantidad_visitas: v,
      categoria,
      tarifa_visitas_id: debouncedTarifa,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedTarifa, debouncedCantidad, categoria]);

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

      {/* Cantidad de visitas */}
      <div className="space-y-2">
        <label className="text-sm font-medium">
          Cantidad de Visitas <span className="text-destructive">*</span>
        </label>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() =>
              onCantidadVisitasChange(Math.max(1, cantidadVisitas - 1))
            }
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-background hover:border-primary/40"
            aria-label="Disminuir visitas"
          >
            <Minus className="h-4 w-4" />
          </button>
          <input
            type="number"
            min={1}
            value={cantidadVisitas}
            onChange={(e) =>
              onCantidadVisitasChange(Math.max(1, toNumber(e.target.value)))
            }
            className="h-9 w-20 rounded-lg border border-border bg-background px-3 text-center text-sm font-semibold tabular-nums focus:border-primary focus:ring-1 focus:ring-primary/30"
          />
          <button
            type="button"
            onClick={() => onCantidadVisitasChange(cantidadVisitas + 1)}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-background hover:border-primary/40"
            aria-label="Aumentar visitas"
          >
            <Plus className="h-4 w-4" />
          </button>
          <span className="text-xs text-muted-foreground">visitas</span>
        </div>
      </div>

      {/* Selector de categoría */}
      <div className="space-y-2">
        <label className="text-sm font-medium">
          Categoría <span className="text-destructive">*</span>
        </label>
        {isLoading ? (
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
                  className={[
                    "rounded-lg border bg-background px-3 py-2.5 transition-all duration-200 text-left flex-1 min-w-[100px] flex items-center justify-center gap-2 cursor-pointer",
                    isSelected
                      ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                      : "border-border hover:border-primary/40",
                  ].join(" ")}
                >
                  <span
                    className={[
                      "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
                      isSelected ? "border-primary" : "border-border",
                    ].join(" ")}
                  >
                    {isSelected && (
                      <span className="h-2 w-2 rounded-full bg-primary" />
                    )}
                  </span>
                  <span className="text-sm font-semibold">Categoría {cat}</span>
                  <input
                    type="radio"
                    name="categoria_io"
                    className="sr-only"
                    checked={isSelected}
                    onChange={() => {
                      onCategoriaChange(cat);
                      const tarifaCat =
                        tarifasDeCategoria.length > 0
                          ? tarifasDeCategoria[0]
                          : null;
                      const primerTarifaCat =
                        (tarifas || []).find((t) => t.categoria === cat) ||
                        tarifaCat;
                      if (primerTarifaCat) onTarifaChange(primerTarifaCat.id);
                    }}
                  />
                </label>
              );
            })}
          </div>
        )}
      </div>

      {/* Tarifa de la categoría seleccionada */}
      {categoria && tarifasDeCategoria.length > 0 && (
        <div className="space-y-2">
          <label className="text-sm font-medium">
            Tarifa por Visita <span className="text-destructive">*</span>
          </label>
          <div className="flex flex-row flex-wrap gap-2">
            {tarifasDeCategoria.map((tarifa) => {
              const isSelected = tarifaVisitasId === tarifa.id;
              return (
                <label
                  key={tarifa.id}
                  role="radio"
                  aria-checked={isSelected}
                  className={[
                    "rounded-lg border bg-background px-3 py-2.5 transition-all duration-200 text-left flex-1 min-w-[160px] flex flex-col gap-1 cursor-pointer",
                    isSelected
                      ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                      : "border-border hover:border-primary/40",
                  ].join(" ")}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={[
                        "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
                        isSelected ? "border-primary" : "border-border",
                      ].join(" ")}
                    >
                      {isSelected && (
                        <span className="h-2 w-2 rounded-full bg-primary" />
                      )}
                    </span>
                    <span className="text-sm font-medium">
                      Cat. {tarifa.categoria}
                    </span>
                  </div>
                  <span className="text-xs font-semibold text-primary pl-6">
                    {formatSoles(tarifa.costo_por_visita)}/visita
                  </span>
                  <input
                    type="radio"
                    name="tarifa_io"
                    className="sr-only"
                    checked={isSelected}
                    onChange={() => onTarifaChange(tarifa.id)}
                  />
                </label>
              );
            })}
          </div>
        </div>
      )}

      {/* Cotización */}
      {error && <p className="text-xs text-destructive">{error}</p>}

      {isCalculating && !quote && (
        <p className="text-xs text-muted-foreground animate-pulse">
          Calculando cotización...
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
