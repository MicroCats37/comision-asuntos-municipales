"use client";

import { useMutation } from "@tanstack/react-query";
import { Calculator, Info, Loader2 } from "lucide-react";
/**
 * CotizacionPorcentajeSmartField — Smart Field for cotizacion preview.
 *
 * Architecture:
 * - Receives `methods: UseFormReturn<EdificacionesFormData>` from parent
 * - Reads `valor_declarado`, `tarifa_unica_id`, `especialidades_seleccionadas`,
 *   `tipo_tramite` from form
 * - "Calcular" button (or auto-recalculate) triggers POST /liquidaciones/edificaciones/cotizar
 * - Shows result: subtotal, IGV, total in its OWN state
 * - Does NOT write back to form until user confirms
 *
 * Mensajes informativos (en orden de prioridad, solo uno a la vez):
 *   1. hasTipoTramite && tipo_tramite==null → "Selecciona un tipo de trámite"
 *   2. valor_declarado<=0                 → "Ingresa un valor declarado mayor a 0"
 *   3. especialidades.length===0          → "Selecciona al menos una especialidad"
 *   4. (condición normal)                 → cotización calculada
 */
import { useEffect, useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import { useWatch } from "react-hook-form";
import { useDebounce } from "@/hooks/system/useDebounce";
import api from "@/lib/api";
import type { CotizacionOutput } from "../../schemas/cotizacion.schema";

interface CotizacionPorcentajeSmartFieldProps {
  // biome-ignore lint/suspicious/noExplicitAny: Smart field is reused by several form schemas that share field names but not a single concrete type.
  methods: UseFormReturn<any>;
  /** Liquidation type path segment for quote endpoints. */
  tipo?: string;
  /** Edit mode calls /{id}/cotizar-edicion and sends liquidacion_tipo. */
  mode?: "create" | "edit";
  liquidacionId?: string;
  /** Fixed declared value used when the value is inherited instead of form-owned. */
  valorDeclaradoFijo?: number;
  /**
   * Si true, el tipo TIENE concepto de `tipo_tramite` (edificaciones, M2).
   * Cuando true, se valida que `tipo_tramite` esté set antes de cotizar.
   * Default false (taludes/IV: sin concepto de tipo_tramite).
   */
  hasTipoTramite?: boolean;
}

// Backend serializes Decimal as strings — coerce to Number defensively
const toNumber = (value: unknown): number => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};

const formatSoles = (value: unknown): string =>
  `S/ ${toNumber(value).toFixed(2)}`;

export function CotizacionPorcentajeSmartField({
  methods,
  tipo = "edificaciones",
  mode = "create",
  liquidacionId,
  valorDeclaradoFijo,
  hasTipoTramite = false,
}: CotizacionPorcentajeSmartFieldProps) {
  const [quote, setQuote] = useState<CotizacionOutput | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cotizacionMutation = useMutation({
    mutationFn: async (payload: {
      valor_declarado: number;
      tarifa_id: string;
      especialidades_ids: string[];
      tipo_tramite?: string;
    }): Promise<CotizacionOutput> => {
      const liquidacionTipo = {
        datos: {
          valor_declarado: payload.valor_declarado,
          ...(payload.tipo_tramite && { tipo_tramite: payload.tipo_tramite }),
        },
        tarifas: payload.especialidades_ids.map((espId) => ({
          tarifa_porcentaje_obra_id: payload.tarifa_id,
          especialidad_id: espId,
        })),
      };

      const endpoint =
        mode === "edit" && liquidacionId
          ? `/liquidaciones/${tipo}/${liquidacionId}/cotizar-edicion`
          : `/liquidaciones/${tipo}/cotizar`;

      const body =
        mode === "edit"
          ? { liquidacion_tipo: liquidacionTipo }
          : {
              liquidacion_especifica: liquidacionTipo,
            };

      const { data } = await api.post(endpoint, body);
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

  // Auto-recalculate when valor_declarado changes (debounced). Empty especialidades = backend auto-fill.
  const valorDeclaradoForm = useWatch({
    control: methods.control,
    name: "valor_declarado",
  });
  const tarifaUnicaId = useWatch({
    control: methods.control,
    name: "tarifa_unica_id",
  });
  const especialidadesSeleccionadas = useWatch({
    control: methods.control,
    name: "especialidades_seleccionadas",
  });
  const tipoTramite = useWatch({
    control: methods.control,
    name: "tipo_tramite",
  }) as string | undefined;
  // Use fixed value (new revision) or form value (first revision).
  const effectiveValor = valorDeclaradoFijo ?? valorDeclaradoForm;
  const debouncedValor = useDebounce(effectiveValor, 500);

  useEffect(() => {
    const v = Number(debouncedValor);
    const espIds = (especialidadesSeleccionadas || []) as string[];

    // Do not quote without selected specialties; this avoids backend auto-fill.
    if (
      !v ||
      v <= 0 ||
      espIds.length === 0 ||
      (mode === "edit" && !liquidacionId)
    ) {
      setQuote(null);
      setError(null);
      return;
    }

    cotizacionMutation.mutate({
      valor_declarado: v,
      tarifa_id: tarifaUnicaId ?? "",
      especialidades_ids: espIds,
      tipo_tramite: tipoTramite,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    debouncedValor,
    tarifaUnicaId,
    especialidadesSeleccionadas,
    tipoTramite,
    mode,
    liquidacionId,
    cotizacionMutation.mutate,
  ]);

  const isLoading = cotizacionMutation.isPending;

  // ── Mensaje informativo (primer match en orden de prioridad) ──────────
  const bloqueanteTipoTramite =
    hasTipoTramite && (tipoTramite === undefined || tipoTramite === null);
  const bloqueanteValor =
    valorDeclaradoForm === undefined ||
    valorDeclaradoForm === null ||
    valorDeclaradoForm <= 0;
  const bloqueanteEspecialidades =
    !especialidadesSeleccionadas ||
    (especialidadesSeleccionadas as unknown[]).length === 0;

  const informativeMessage = bloqueanteTipoTramite
    ? "Selecciona un tipo de trámite para poder cotizar."
    : bloqueanteValor
      ? "Ingresa un valor declarado mayor a 0 para poder cotizar."
      : bloqueanteEspecialidades
        ? "Selecciona al menos una especialidad para poder cotizar."
        : null;

  return (
    <div className="space-y-3 rounded-xl border border-primary/20 bg-primary/[0.03] p-4 shadow-sm">
      <div className="flex items-center gap-2">
        <Calculator className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
          Cotización
        </h3>
        {isLoading && (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
        )}
      </div>

      {error && <p className="text-xs text-destructive">{error}</p>}

      {informativeMessage && (
        <div className="flex items-start gap-2 rounded-lg border border-dashed border-primary/30 bg-primary/[0.02] p-3">
          <Info className="h-4 w-4 text-primary/70 mt-0.5 shrink-0" />
          <p className="text-sm text-muted-foreground italic">
            {informativeMessage}
          </p>
        </div>
      )}

      {isLoading && !quote && (
        <p className="text-xs text-muted-foreground animate-pulse">
          Calculando cotización...
        </p>
      )}

      {quote && (
        <div className="space-y-2 rounded-lg border border-border bg-card p-3">
          <div className="grid grid-cols-2 gap-1 text-sm">
            <span className="text-muted-foreground">% Liquidación:</span>
            <span className="font-medium text-right">
              {(Number(quote.porcentaje_liquidacion) * 100).toFixed(2)}%
            </span>
            <span className="text-muted-foreground">Subtotal:</span>
            <span className="font-medium text-right">
              {formatSoles(quote.total_subtotal)}
            </span>
          </div>
          <div className="border-t border-border pt-1.5 flex justify-between font-semibold text-sm">
            <span>Total a Pagar:</span>
            <span className="text-primary">{formatSoles(quote.total)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
