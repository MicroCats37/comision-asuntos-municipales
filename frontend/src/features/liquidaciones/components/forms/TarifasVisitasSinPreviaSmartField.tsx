"use client";

import { useMutation } from "@tanstack/react-query";
import { Calculator, HardHat, Link2, Loader2 } from "lucide-react";
/**
 * TarifasVisitasSinPreviaSmartField — Smart field de IO sin liquidación previa.
 *
 * Incluye dentro del mismo card-wrapper:
 *  · Selector de MODO DE COTIZACIÓN (Normal / Continuar) — discriminador tipado
 *  · Selector de categoría (1/2/3/4) — radio group
 *  · Botón "Inspector Asignado" — abre seleccionarInspectorModal via callback
 *  · Tarifa informativa
 *  · Cotización auto-debounceada (400ms)
 *  · PANEL DEL MODO ACTIVO: la cotización por valor completo (Normal) o el
 *    panel de continuidad (Continuar: referencia histórica, crédito y diferencia)
 *
 * Es el DUEÑO de la composición de los modos de IO (patrón PO/Edificaciones):
 * un solo formulario, un solo SmartField y UNA sola llamada de cotización. El
 * modo se lee del form (`modo_cotizacion`) y el panel activo se compone aquí.
 *
 * Lee del form vía `useWatch`:
 *  - `cantidad_visitas` (vive en Datos del Trámite via IncrementerInput)
 *  - `categoria`, `tarifa_visitas_id`
 *  - `modo_cotizacion` (modo de cotización) y `continuidad` (bloque)
 *
 * NO persiste en form: solo lee. La categoría se escribe via `methods.setValue`
 * cuando el usuario hace click en un chip.
 *
 * Endpoint: POST /liquidaciones/inspeccion-obra/cotizar
 */
import { useEffect, useMemo, useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import { useWatch } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/errors";
import { useDebounce } from "@/hooks/system/useDebounce";
import { useLatestRequestGuard } from "@/hooks/system/useLatestRequestGuard";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatCurrencyTrimmed } from "@/utils/number-formatter";
import { useTarifasVigentesVisitas } from "../../hooks/useTarifasVigentes";
import type { LiquidacionInspeccionObraListItem } from "../../schemas/liquidacion-inspeccion-obra.schema";
import {
  type CotizacionVisitasOutput,
  construirCotizacionVisitasEdicionPayload,
  construirCotizacionVisitasPayload,
  parseCotizacionVisitasOutput,
} from "../../schemas/liquidacion-io-cotizacion.schema";
import {
  MODO_COTIZACION_IO_CONTINUAR,
  type ModoCotizacionIO,
} from "../../schemas/liquidacion-io-modo-cotizacion.schema";
import type { ContinuidadVisitasOut } from "../../schemas/liquidacion-visitas.schema";
import type { ContinuidadVisitasFormData } from "../../schemas/liquidacion-visitas-form.schema";
import { MODO_COTIZACION_IO_POR_DEFECTO } from "../../utils/modoCotizacionIo";
import {
  ContinuidadVisitasPanel,
  deriveContinuidadDefaults,
} from "./inspeccion-obra/ContinuidadVisitasPanel";
import { ModoCotizacionIoField } from "./inspeccion-obra/ModoCotizacionIoField";

interface TarifasVisitasSinPreviaSmartFieldProps {
  // biome-ignore lint/suspicious/noExplicitAny: Pattern matches existing smart fields (CotizacionM2SmartField, CotizacionPorcentajeSmartField).
  methods: UseFormReturn<any>;
  /** Inspector ya seleccionado (nombre para mostrar en el botón) */
  inspectorNombre?: string;
  /** Callback al hacer click en el botón "Inspector Asignado" */
  onOpenInspector: () => void;
  fecha?: string;
  hideInspector?: boolean;
  legacy?: boolean;
  /**
   * Modo del formulario:
   *  · "create" (default): la cotización usa `/cotizar` (valores vigentes).
   *  · "edit": la cotización usa `/{id}/cotizar-edicion`, que resuelve los
   *    valores HISTÓRICOS de `fecha_registro` — los mismos con los que el
   *    PATCH reprecia B (Explorer D6). Con la cotización vigente, el preview
   *    del panel de continuidad mentiría respecto de lo que persistirá el
   *    servidor.
   */
  mode?: "create" | "edit";
  /** ID de la liquidación — requerido en `mode="edit"` para usar /cotizar-edicion */
  liquidacionId?: string;
  /**
   * Capacidad del motor: el selector de MODO DE COTIZACIÓN (Normal / Continuar)
   * solo se monta si el formulario lo admite.
   *
   * IO lo admite en `create` y `edit`; en `legacy` y `relacionada` la
   * continuidad no existe (el backend no la admite) y el SmartField se comporta
   * exactamente como antes: cotización por valor completo, sin selector.
   */
  soportaModoContinuidad?: boolean;
  /**
   * Liquidación previa (A) desde la que se inició el "Continuar".
   *
   * Es el origen de los defaults del bloque de continuidad cuando se entra en
   * el modo "Continuar" (sin el registro persistido, la referencia histórica
   * no se reprecia: se toma tal cual).
   */
  continuidadPrevia?: LiquidacionInspeccionObraListItem | null;
  /**
   * Registro de continuidad PERSISTIDO de la IO (`liquidacion_tipo.continuidad`).
   * Solo en `mode="edit"`: snapshot histórico congelado (referencia a A, crédito
   * histórico y valor completo guardado).
   */
  continuidadPersistida?: ContinuidadVisitasOut | null;
  onOpenReferencia?: () => void;
}

const toNumber = (value: unknown): number => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};
const formatSoles = (value: unknown): string =>
  formatCurrencyTrimmed(toNumber(value), 2);

const normalizeCategoria = (cat: string): string => {
  if (["C1", "C2", "C3", "C4"].includes(cat)) return cat.slice(1);
  return cat;
};

/**
 * El builder del cuerpo de cotización (mode-aware) vive en el módulo de
 * schemas: `liquidacion-io-cotizacion.schema.ts`.
 *
 * `/cotizar` espera el wrapper `liquidacion_especifica` y `/cotizar-edicion`
 * el wrapper `liquidacion_tipo` (NO `liquidacion_especifica`), que resuelve los
 * valores históricos de `fecha_registro` desde el propio registro.
 */
export function TarifasVisitasSinPreviaSmartField({
  methods,
  inspectorNombre,
  onOpenInspector,
  fecha,
  hideInspector = false,
  legacy = false,
  mode = "create",
  liquidacionId,
  soportaModoContinuidad = false,
  continuidadPrevia = null,
  continuidadPersistida = null,
  onOpenReferencia,
}: TarifasVisitasSinPreviaSmartFieldProps) {
  const [quote, setQuote] = useState<CotizacionVisitasOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestGuard = useLatestRequestGuard();
  const fechaRegistro = useWatch({
    control: methods.control,
    name: "fecha_registro",
  }) as string | undefined;
  const fechaEfectiva = fecha ?? fechaRegistro;
  // En edición la cotización va por `/cotizar-edicion`: el servidor resuelve
  // los valores históricos de `fecha_registro` del propio registro (Explorer
  // D6). `fechaEfectiva` sigue sirviendo para LISTAR las tarifas históricas
  // vigentes a esa fecha.
  const esEdicion = mode === "edit" && Boolean(liquidacionId);

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

  // ── Modo de cotización (Normal / Continuar) ────────────────────────────
  // El modo es un discriminador TIPADO que vive en el form (patrón PO). Este
  // SmartField es su dueño: decide qué panel es el activo y compone el ciclo
  // de vida del bloque de continuidad.
  const modoCotizacion = useWatch({
    control: methods.control,
    name: "modo_cotizacion",
  }) as ModoCotizacionIO | undefined;
  const modoVigente = modoCotizacion ?? MODO_COTIZACION_IO_POR_DEFECTO;
  const esModoContinuar = modoVigente === MODO_COTIZACION_IO_CONTINUAR;
  // El panel de continuidad solo existe si el formulario admite el modo
  // "Continuar" (en `legacy` y `relacionada` la continuidad no existe).
  const muestraPanelContinuidad = soportaModoContinuidad && esModoContinuar;

  const continuidad = useWatch({
    control: methods.control,
    name: "continuidad",
  }) as ContinuidadVisitasFormData | undefined;

  /**
   * Con continuidad PERSISTIDA la liquidación cobra la diferencia: el modo
   * "Normal" (valor completo) sería una vista falsa. El selector queda
   * bloqueado y la continuidad solo se apaga con la confirmación explícita del
   * panel (que es una operación, no un cambio de vista).
   */
  const modoBloqueado = Boolean(continuidadPersistida);

  /**
   * Ciclo de vida del bloque de continuidad ante un cambio de MODO.
   *
   *  · Entrar en "Continuar" abre el bloque (con los defaults de la previa A
   *    si la hay; si no, ingreso manual). No es una operación: el discriminador
   *    `modo` (activar/mantener/desactivar) lo fija el panel al editar.
   *  · Volver a "Normal" descarta el bloque: la operación de continuidad no
   *    viaja y el servidor conserva el crédito congelado. Si el registro
   *    PERSISTIDO tiene continuidad, el selector está bloqueado y el bloque
   *    nunca se descarta.
   */
  const handleModoCotizacionChange = (siguiente: ModoCotizacionIO) => {
    if (siguiente === MODO_COTIZACION_IO_CONTINUAR) {
      if (continuidad) return;
      const base: ContinuidadVisitasFormData = continuidadPrevia
        ? deriveContinuidadDefaults(continuidadPrevia)
        : {
            visitas_previas_pendientes: 0,
            // Sin total informado: el servidor no puede validar las pendientes
            // contra nada. El usuario lo informa (ingreso manual de la previa).
            visitas_previas_totales: undefined,
            observacion: "",
          };
      methods.setValue("continuidad", base as never, {
        shouldDirty: true,
        shouldValidate: true,
      });
      return;
    }

    if (continuidadPersistida) return;
    methods.setValue("continuidad", undefined as never, {
      shouldDirty: true,
      shouldValidate: true,
    });
  };

  /**
   * BRUTO declarado por el usuario (IGV incluido). Es la ENTRADA del crédito:
   * el servidor lo valida y deriva el par (crédito neto, crédito bruto).
   *
   * El cliente NO calcula el crédito: solo declara el bruto y muestra las
   * cifras que devuelve el servidor (DD-7).
   */
  const totalPagadoPrevia = toNumber(
    continuidad?.total_pagado_previa ?? undefined,
  );
  const hayTotalPagadoPrevia = totalPagadoPrevia > 0;

  // La cotización vigente (la UNAICA llamada de cotización) alimenta el panel
  // del modo activo: el bloque `continuidad` que devuelve el SERVIDOR se
  // refleja sin repetir la petición al backend.
  const cotizacionContinuidad = quote?.continuidad ?? null;

  // Tarifas para mostrar info de la categoría seleccionada
  const { data: tarifasData, isLoading: isTarifasLoading } =
    useTarifasVigentesVisitas("inspeccion-obra", {
      fecha: fechaEfectiva,
      enabled: !legacy || Boolean(fechaEfectiva),
    });
  const tarifas = useMemo(
    () => tarifasData?.tarifas ?? [],
    [tarifasData?.tarifas],
  );

  // Categorías únicas (orden estable: 1, 2, 3, 4)
  const categorias = useMemo(
    () =>
      Array.from(
        new Set(tarifas.map((t) => normalizeCategoria(t.categoria))),
      ).sort(),
    [tarifas],
  );

  // Auto-seleccionar primera categoría si no hay
  useEffect(() => {
    if (tarifas.length > 0 && !categoria && categorias[0]) {
      methods.setValue("categoria", categorias[0] as never, {
        shouldValidate: false,
      });
    }
  }, [tarifas, categoria, categorias, methods]);

  // Tarifas que coinciden con la categoría seleccionada
  const tarifasDeCategoria = useMemo(
    () => tarifas.filter((t) => normalizeCategoria(t.categoria) === categoria),
    [tarifas, categoria],
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
  }, [categoria, tarifasDeCategoria, tarifaVisitasId, methods]);

  const tarifaSeleccionada = tarifas.find((t) => t.id === tarifaVisitasId);

  const cotizacionMutation = useMutation({
    mutationFn: async (payload: {
      requestId: number;
      modo_cotizacion: ModoCotizacionIO;
      cantidad_visitas: number;
      tarifa_visitas_id: string;
      total_pagado_previa?: number;
      endpoint: string;
      esEdicion: boolean;
    }): Promise<CotizacionVisitasOutput> => {
      const entrada = {
        modo: payload.modo_cotizacion,
        cantidad_visitas: payload.cantidad_visitas,
        tarifa_visitas_id: payload.tarifa_visitas_id,
        total_pagado_previa: payload.total_pagado_previa,
      };
      // El wrapper NO cambia: `/cotizar` usa `liquidacion_especifica` y
      // `/cotizar-edicion` usa `liquidacion_tipo`.
      const body = payload.esEdicion
        ? construirCotizacionVisitasEdicionPayload(entrada)
        : construirCotizacionVisitasPayload(entrada);
      const { data } = await api.post(payload.endpoint, body);
      // La respuesta se tipa con el ESPEJO Zod del contrato del backend: es lo
      // que impide que las claves nuevas (`modo_cotizacion`, `continuidad`)
      // sean eliminadas por Zod (riesgo R9 del Explorer).
      return parseCotizacionVisitasOutput(data.data);
    },
    onSuccess: (result, variables) => {
      if (!requestGuard.isLatest(variables.requestId)) return;
      setQuote(result);
      setError(null);
    },
    onError: (err, variables) => {
      if (!requestGuard.isLatest(variables.requestId)) return;
      setQuote(null);
      setError(getErrorMessage(err) || "Error al calcular cotización");
    },
  });

  const cantidadVisitas = toNumber(cantidadVisitasForm);
  const categoriaNorm = categoria ? normalizeCategoria(categoria) : "";
  const debouncedCantidad = useDebounce(cantidadVisitas, 400);
  // El bruto declarado entra en el MISMO debounce que la cantidad de visitas
  // (400 ms): cambiar el bruto re-cotiza, pero no en cada tecla.
  const debouncedTotalPagadoPrevia = useDebounce(totalPagadoPrevia, 400);

  useEffect(() => {
    // En el modo CONTINUAR la cotización EXIGE el bruto declarado: sin él, el
    // backend rechaza el payload (422). El cliente no inventa el dato: espera
    // a que el usuario lo declare.
    const requiereBruto = muestraPanelContinuidad && !hayTotalPagadoPrevia;

    if (
      !debouncedCantidad ||
      debouncedCantidad <= 0 ||
      !tarifaVisitasId ||
      (legacy && !fechaEfectiva) ||
      !categoriaNorm ||
      requiereBruto
    ) {
      requestGuard.invalidate();
      setQuote(null);
      setError(null);
      return;
    }
    const requestId = requestGuard.begin();
    // El endpoint se resuelve AQUÍ (y no dentro de `mutationFn`) para que la
    // dependencia sea explícita: si el registro llega después del montaje,
    // `esEdicion`/`liquidacionId` cambian y el efecto vuelve a cotizar con la
    // vía de edición (valores históricos de `fecha_registro`).
    const endpoint = esEdicion
      ? `/liquidaciones/inspeccion-obra/${liquidacionId}/cotizar-edicion`
      : fechaEfectiva
        ? `/liquidaciones/inspeccion-obra/cotizar?fecha=${encodeURIComponent(fechaEfectiva)}`
        : "/liquidaciones/inspeccion-obra/cotizar";
    cotizacionMutation.mutate({
      requestId,
      modo_cotizacion: modoVigente,
      cantidad_visitas: debouncedCantidad,
      tarifa_visitas_id: tarifaVisitasId,
      ...(muestraPanelContinuidad && hayTotalPagadoPrevia
        ? { total_pagado_previa: debouncedTotalPagadoPrevia }
        : {}),
      endpoint,
      esEdicion,
    });
    return () => requestGuard.invalidate();
  }, [
    debouncedCantidad,
    debouncedTotalPagadoPrevia,
    tarifaVisitasId,
    categoriaNorm,
    fechaEfectiva,
    legacy,
    esEdicion,
    liquidacionId,
    modoVigente,
    muestraPanelContinuidad,
    hayTotalPagadoPrevia,
    cotizacionMutation.mutate,
    requestGuard,
  ]);

  const isCalculating = cotizacionMutation.isPending;

  return (
    <div className="space-y-4 rounded-xl border border-primary/20 bg-primary/[0.03] p-4 shadow-sm">
      <input type="hidden" {...methods.register("categoria")} />
      <input type="hidden" {...methods.register("tarifa_visitas_id")} />
      <input type="hidden" {...methods.register("inspector_id")} />
      <input type="hidden" {...methods.register("inspector_operacion_id")} />
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Calculator className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
            Cálculo de Visitas
          </h3>
          {isCalculating && (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
          )}
        </div>
        <div className="flex items-center gap-2">
          {onOpenReferencia && esModoContinuar && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onOpenReferencia}
              className="gap-1"
            >
              <Link2 className="h-3.5 w-3.5" />
              Referencia IO
            </Button>
          )}
          {soportaModoContinuidad && (
            <ModoCotizacionIoField
              methods={methods}
              disabled={modoBloqueado}
              onModoChange={handleModoCotizacionChange}
            />
          )}
        </div>
      </div>

      {!hideInspector && (
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
            className="w-full gap-1"
          >
            <HardHat className="h-3 w-3" />
            {inspectorNombre
              ? `Inspector: ${inspectorNombre}`
              : "Seleccionar inspector"}
          </Button>
          {methods.formState.errors.inspector_operacion_id?.message && (
            <p className="text-xs font-medium text-destructive">
              {String(methods.formState.errors.inspector_operacion_id.message)}
            </p>
          )}
        </div>
      )}

      {/* Selector de categoría */}
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
                      shouldValidate: false,
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

      {/*
       * PANEL DEL MODO ACTIVO.
       *
       *  · Normal   → la cotización por valor completo (comportamiento vigente).
       *  · Continuar → el panel de continuidad (referencia histórica, crédito
       *    y diferencia) DENTRO del SmartField: no hay una tarjeta aparte en el
       *    modal.
       *
       * La UNAICA llamada de cotización alimenta los dos paneles.
       */}
      {muestraPanelContinuidad ? (
        <ContinuidadVisitasPanel
          methods={methods}
          mode={mode === "edit" ? "edit" : "create"}
          previa={continuidadPrevia}
          continuidadPersistida={continuidadPersistida}
          cotizacion={cotizacionContinuidad}
        />
      ) : (
        quote && (
          <div className="space-y-2 rounded-lg border border-border bg-card p-3">
            <div className="grid grid-cols-2 gap-1 text-sm">
              <span className="text-muted-foreground">Costo por visita:</span>
              <span className="font-medium text-right">
                {formatSoles(
                  quote.datos?.tarifa?.costo_por_visita ??
                    tarifaSeleccionada?.costo_por_visita,
                )}
              </span>
              <span className="text-muted-foreground">Categoría:</span>
              <span className="font-medium text-right">
                {categoriaNorm ? `Categoría ${categoriaNorm}` : "—"}
              </span>
              <span className="text-muted-foreground">
                Cantidad de visitas:
              </span>
              <span className="font-medium text-right tabular-nums">
                {quote.datos?.entrada?.datos?.cantidad_visitas ??
                  cantidadVisitas}
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
        )
      )}
    </div>
  );
}
