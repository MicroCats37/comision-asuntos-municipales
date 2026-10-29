"use client";

import { useMutation } from "@tanstack/react-query";
import { Calculator, Info, Layers, Loader2 } from "lucide-react";
/**
 * CotizacionPorcentajeSmartField — Smart Field for cotizacion preview.
 *
 * Architecture:
 * - Receives `methods: UseFormReturn<EdificacionesFormData>` from parent
 * - Reads `valor_declarado` / `total_explicito`, `estrategia_cotizacion`,
 *   `tarifa_unica_id`, `especialidades_seleccionadas`, `tipo_tramite` from form
 * - "Calcular" button (or auto-recalculate) triggers POST /liquidaciones/edificaciones/cotizar
 * - Shows result: subtotal, IGV y total; participant detail lives in a tooltip
 * - Does NOT write back to form until user confirms
 *
 * Mensajes informativos (en orden de prioridad, solo uno a la vez):
 *   1. hasTipoTramite && tipo_tramite==null → "Selecciona un tipo de trámite"
 *   2. valor declarado / total explícito <= 0 → "Ingresa ... mayor a 0"
 *   3. especialidades.length===0          → "Selecciona al menos una especialidad"
 *   4. (condición normal)                 → cotización calculada
 *
 * Las ESTRATEGIAS solo existen en Edificaciones: por eso el payload discriminado
 * va detrás de `soportaEstrategia`. Taludes e Impacto Vial siguen enviando su
 * payload legacy intacto.
 */
import { useEffect, useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import { useWatch } from "react-hook-form";
import { useDebounce } from "@/hooks/system/useDebounce";
import { useLatestRequestGuard } from "@/hooks/system/useLatestRequestGuard";
import api from "@/lib/api";
import { formatCurrencyTrimmed } from "@/utils/number-formatter";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { CotizacionOutput } from "../../schemas/cotizacion.schema";
import {
  construirEstrategiaPayload,
  ESTRATEGIA_NORMAL,
  esEstrategiaValida,
  type EstrategiaCotizacionPO,
} from "../../schemas/liquidacion-po-estrategia.schema";
import { estrategiaUsaTotalExplicito } from "../../utils/estrategiaCotizacion";

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
  /**
   * Si true, el motor soporta estrategias de cotización (SOLO Edificaciones).
   * Cuando true, el preview envía la union discriminada y el resultado muestra
   * H, el detalle por participante y la proyección de acumulación.
   * Default false: Taludes e Impacto Vial conservan su payload intacto.
   */
  soportaEstrategia?: boolean;
}

// Backend serializes Decimal as strings — coerce to Number defensively
const toNumber = (value: unknown): number => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};

const formatSoles = (value: unknown): string =>
  formatCurrencyTrimmed(toNumber(value), 2);

const formatPorcentaje = (value: unknown): string =>
  `${(toNumber(value) * 100).toFixed(2)}%`;

const formatPorcentajePreciso = (value: unknown): string =>
  `${(toNumber(value) * 100).toFixed(4)}%`;

export function CotizacionPorcentajeSmartField({
  methods,
  tipo = "edificaciones",
  mode = "create",
  liquidacionId,
  valorDeclaradoFijo,
  hasTipoTramite = false,
  soportaEstrategia = false,
}: CotizacionPorcentajeSmartFieldProps) {
  const [quote, setQuote] = useState<CotizacionOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestGuard = useLatestRequestGuard();

  const cotizacionMutation = useMutation({
    mutationFn: async (payload: {
      requestId: number;
      estrategia: EstrategiaCotizacionPO;
      valor_declarado?: number;
      total_explicito?: number;
      tarifa_id: string;
      especialidades_ids: string[];
      tipo_tramite?: string;
    }): Promise<CotizacionOutput> => {
      const tarifas = payload.especialidades_ids.map((espId) => ({
        tarifa_porcentaje_obra_id: payload.tarifa_id,
        especialidad_id: espId,
      }));

      // Union discriminada de estrategias (solo Edificaciones) o payload legacy.
      const liquidacionTipo = soportaEstrategia
        ? construirEstrategiaPayload({
            estrategia: payload.estrategia,
            valor_declarado: payload.valor_declarado,
            total_explicito: payload.total_explicito,
            tipo_tramite: payload.tipo_tramite,
            tarifas,
          })
        : {
            datos: {
              valor_declarado: payload.valor_declarado ?? 0,
              ...(payload.tipo_tramite
                ? { tipo_tramite: payload.tipo_tramite }
                : {}),
            },
            tarifas,
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
    onSuccess: (result, variables) => {
      if (!requestGuard.isLatest(variables.requestId)) return;
      setQuote(result);
      setError(null);
    },
    onError: (err, variables) => {
      if (!requestGuard.isLatest(variables.requestId)) return;
      setQuote(null);
      setError(
        err instanceof Error ? err.message : "Error al calcular cotización",
      );
    },
  });

  // Auto-recalculate when the strategy-relevant value changes (debounced).
  // Empty especialidades = backend auto-fill.
  const valorDeclaradoForm = useWatch({
    control: methods.control,
    name: "valor_declarado",
  }) as number | undefined;
  const totalExplicitoForm = useWatch({
    control: methods.control,
    name: "total_explicito",
  }) as number | undefined;
  const estrategiaForm = useWatch({
    control: methods.control,
    name: "estrategia_cotizacion",
  }) as EstrategiaCotizacionPO | undefined;
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

  const estrategia = esEstrategiaValida(estrategiaForm)
    ? estrategiaForm
    : ESTRATEGIA_NORMAL;

  // TOTAL_EXPLICITO se cotiza al cambiar el total; el valor declarado sigue
  // siendo obligatorio para guardar, pero no participa en la fórmula.
  const effectiveValor = valorDeclaradoFijo ?? valorDeclaradoForm ?? 0;
  const effectiveTotal = totalExplicitoForm ?? 0;
  const valorActivoCotizacion = estrategiaUsaTotalExplicito(estrategia)
    ? effectiveTotal
    : effectiveValor;
  const debouncedValorActivo = useDebounce(valorActivoCotizacion, 500);
  const debouncedEstrategia = useDebounce(estrategia, 500);

  useEffect(() => {
    const valorActivo = Number(debouncedValorActivo);
    const usaTotal = estrategiaUsaTotalExplicito(debouncedEstrategia);
    const valorInformativo = Number(
      valorDeclaradoFijo ?? valorDeclaradoForm ?? 0,
    );
    const espIds = (especialidadesSeleccionadas || []) as string[];
    const tarifaId =
      typeof tarifaUnicaId === "string" ? tarifaUnicaId.trim() : "";

    // Wait until the tariff smart field has populated the form to avoid
    // sending an empty UUID during its initial loading cycle.
    if (
      !valorActivo ||
      valorActivo <= 0 ||
      !tarifaId ||
      espIds.length === 0 ||
      (mode === "edit" && !liquidacionId)
    ) {
      requestGuard.invalidate();
      setQuote(null);
      setError(null);
      return;
    }

    const requestId = requestGuard.begin();
    cotizacionMutation.mutate({
      requestId,
      estrategia: debouncedEstrategia,
      valor_declarado: usaTotal
        ? valorInformativo > 0
          ? valorInformativo
          : valorActivo
        : valorActivo,
      total_explicito: usaTotal ? valorActivo : undefined,
      tarifa_id: tarifaId,
      especialidades_ids: espIds,
      tipo_tramite: tipoTramite,
    });
    return () => requestGuard.invalidate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    debouncedValorActivo,
    debouncedEstrategia,
    tarifaUnicaId,
    especialidadesSeleccionadas,
    tipoTramite,
    mode,
    liquidacionId,
    cotizacionMutation.mutate,
    requestGuard,
  ]);

  const isLoading = cotizacionMutation.isPending;

  // ── Mensaje informativo (primer match en orden de prioridad) ──────────
  const bloqueanteTipoTramite =
    hasTipoTramite && (tipoTramite === undefined || tipoTramite === null);
  const usaTotalExplicito = estrategiaUsaTotalExplicito(estrategia);
  const bloqueanteValor = valorActivoCotizacion <= 0;
  const bloqueanteEspecialidades =
    !especialidadesSeleccionadas ||
    (especialidadesSeleccionadas as unknown[]).length === 0;
  const bloqueanteTarifa =
    typeof tarifaUnicaId !== "string" || tarifaUnicaId.trim() === "";

  const informativeMessage = bloqueanteTipoTramite
    ? "Selecciona un tipo de trámite para poder cotizar."
    : bloqueanteValor
      ? usaTotalExplicito
        ? "Ingresa un total final mayor a 0 para poder cotizar."
        : "Ingresa un valor declarado mayor a 0 para poder cotizar."
      : bloqueanteEspecialidades
        ? "Selecciona al menos una especialidad para poder cotizar."
        : bloqueanteTarifa
          ? "Esperando la tarifa vigente para poder cotizar."
          : null;

  // IGV derivado por RESTA de los dos totales que devuelve el backend:
  // no se recalcula la fórmula de cotización en el frontend.
  const igv = quote ? toNumber(quote.total) - toNumber(quote.total_subtotal) : 0;
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
        <div
          className="space-y-2 rounded-lg border border-border bg-card p-3"
          aria-live="polite"
        >
          <div className="grid grid-cols-2 gap-1 text-sm">
            <span className="text-muted-foreground">Valor declarado:</span>
            <span className="font-medium text-right">
              {formatSoles(effectiveValor)}
            </span>
            {quote.porcentaje_liquidacion != null && (
              <>
                <span className="text-muted-foreground">% Liquidación:</span>
                <span className="font-medium text-right">
                  {formatPorcentaje(quote.porcentaje_liquidacion)}
                </span>
              </>
            )}
            <span className="text-muted-foreground">Subtotal:</span>
            <span className="font-medium text-right">
              {formatSoles(quote.total_subtotal)}
            </span>
            <span className="text-muted-foreground">IGV:</span>
            <span className="font-medium text-right">{formatSoles(igv)}</span>
          </div>
          <div className="border-t border-border pt-1.5 flex justify-between font-semibold text-sm">
            <span className="flex items-center gap-1.5">
              Total a Pagar:
              {quote.detalles.length > 0 ? (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        className="inline-flex size-5 items-center justify-center rounded-full border border-primary/25 text-primary transition-colors hover:bg-primary/10"
                        aria-label="Ver detalle por participante"
                      >
                        <Layers className="size-3" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent
                      side="right"
                      sideOffset={8}
                      className="block w-72 max-w-[calc(100vw-2rem)] space-y-2 p-3"
                    >
                      <p className="text-[11px] font-semibold uppercase tracking-wide opacity-75">
                        Detalle por participante
                      </p>
                      <div className="space-y-1.5">
                        {quote.detalles.map((detalle, index) => (
                          <div
                            key={`${detalle.tarifa_id ?? "tarifa"}-${detalle.especialidad?.id ?? index}-${index}`}
                            className="flex items-start justify-between gap-3 text-xs"
                          >
                            <span className="min-w-0 flex-1 truncate">
                              {detalle.especialidad?.nombre ?? "Especialidad"}
                            </span>
                            <span className="shrink-0 font-semibold">
                              {detalle.porcentaje_aplicado != null
                                ? `${formatPorcentajePreciso(detalle.porcentaje_aplicado)} · `
                                : ""}
                              {formatSoles(detalle.subtotal)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              ) : null}
            </span>
            <span className="text-primary">{formatSoles(quote.total)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
