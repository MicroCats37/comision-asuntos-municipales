"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import { useCotizacionPrimeraRevision } from "../../hooks/useCotizacion";
import { useLiquidacionStepperUIStore } from "../../store";
import type { RevisionVigente } from "../../types/revisiones-vigentes";
import type { VariablesFinancieras } from "../../types/liquidacion-edificaciones";
import { CotizacionSection } from "../CotizacionSection";

interface Step4CotizacionProps {
  methods: UseFormReturn<FieldValues>;
  isActive: boolean;
  variablesFinancieras?: VariablesFinancieras;
  isLoadingVariables?: boolean;
  revisionesVigentes?: RevisionVigente[];
}

export function Step4Cotizacion({
  methods,
  isActive,
  variablesFinancieras,
  isLoadingVariables,
  revisionesVigentes,
}: Step4CotizacionProps) {
  const {
    cotizacion,
    setCotizacionQuote,
    setCotizacionCalculating,
    setCotizacionError,
    selectedRevisionIds,
    selectedTarifasIds,
    setSelectedTarifasId,
  } = useLiquidacionStepperUIStore();

  const cotizacionMutation = useCotizacionPrimeraRevision();
  const { watch } = methods;

  const watchedValues = watch([
    "valor_proyecto",
    "valor_base_calculo",
    "tipo_tramite",
  ]);
  const [valorProyecto, valorBaseCalculo, tipoTramite] =
    watchedValues;

  const hasValidValorBase = Number(valorBaseCalculo) > 0;
  const hasVariablesFinancieras = !!variablesFinancieras;

  const selectedTarifaId = useMemo(() => {
    if (!revisionesVigentes || selectedRevisionIds.length === 0) return null;
    const firstRevision = revisionesVigentes.find(
      (rev) => rev.id === selectedRevisionIds[0],
    );
    return firstRevision?.id || null;
  }, [revisionesVigentes, selectedRevisionIds]);

  // Sincronizar tarifa seleccionada con el store cuando cambia
  useEffect(() => {
    if (selectedTarifaId && selectedRevisionIds.length === 1) {
      setSelectedTarifasId(selectedTarifaId);
    }
  }, [selectedTarifaId, selectedRevisionIds.length, setSelectedTarifasId]);

  const hasTarifa = selectedTarifasIds.length === 1;

  const valorBase =
    valorBaseCalculo && Number(valorBaseCalculo) > 0
      ? Number(valorBaseCalculo)
      : Number(valorProyecto);

  const hasAllDependencies =
    hasValidValorBase &&
    hasVariablesFinancieras &&
    hasTarifa;

  const hasAutoCalculated = useRef(false);

  // ── Stable refs for latest values used in the cotizacion callback ──
  const latestRef = useRef({
    hasValidValorBase,
    hasTarifa,
    selectedTarifasIds,
    tipoTramite,
    valorProyecto,
    valorBase,
  });
  latestRef.current = {
    hasValidValorBase,
    hasTarifa,
    selectedTarifasIds,
    tipoTramite,
    valorProyecto,
    valorBase,
  };

  const runCotizacion = useCallback(async () => {
    const latest = latestRef.current;
    if (
      !latest.hasValidValorBase ||
      !latest.hasTarifa ||
      latest.selectedTarifasIds.length === 0
    )
      return;

    setCotizacionCalculating(true);
    setCotizacionError(null);

    try {
      const result = await cotizacionMutation.mutateAsync({
        tipo_tramite: latest.tipoTramite as string,
        valor_proyecto: Number(latest.valorProyecto),
        valor_base_calculo: latest.valorBase,
        tarifas_ids: latest.selectedTarifasIds,
      });
      setCotizacionQuote(result);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error al calcular la cotización";
      setCotizacionError(msg);
    } finally {
      setCotizacionCalculating(false);
    }
  }, [
    cotizacionMutation,
    setCotizacionCalculating,
    setCotizacionError,
    setCotizacionQuote,
  ]);

  // Auto-calculate when entering step 4 with valid dependencies
  // Only runs once per entry (hasAutoCalculated flag).
  // Manual recalculation available via the "Calcular cotización" button.
  useEffect(() => {
    if (!isActive) {
      hasAutoCalculated.current = false;
      return;
    }

    if (
      hasAllDependencies &&
      !hasAutoCalculated.current &&
      !cotizacion.isCalculating
    ) {
      hasAutoCalculated.current = true;
      runCotizacion();
    }
  }, [isActive, hasAllDependencies, cotizacion.isCalculating, runCotizacion]);

  if (!isActive) return null;

  return (
    <div className="space-y-4 min-w-0 max-w-full">
      {/* Cotización Section */}
      <CotizacionSection
        quote={cotizacion.quote}
        isLoading={cotizacion.isCalculating}
        onCotizar={runCotizacion}
        hasErrors={!!cotizacion.lastError}
        hasValidValorBase={hasValidValorBase}
        variablesFinancieras={variablesFinancieras}
        isLoadingVariables={isLoadingVariables}
      />

      {/* Dependency warnings */}
      {!hasAllDependencies && !cotizacion.isCalculating && (
        <div className="flex gap-2 text-xs text-muted-foreground">
          {!hasValidValorBase && (
            <span>• Ingresa un valor de proyecto válido</span>
          )}
          {!hasTarifa && <span>• Selecciona exactamente una revisión/tarifa</span>}
          {!hasVariablesFinancieras && (
            <span>• Variables financieras no disponibles</span>
          )}
        </div>
      )}
    </div>
  );
}
