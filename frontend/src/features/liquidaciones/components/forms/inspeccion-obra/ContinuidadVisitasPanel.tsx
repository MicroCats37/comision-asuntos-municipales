"use client";

/**
 * ContinuidadVisitasPanel — PANEL del modo de cotización "Continuar" (IO).
 *
 * Antes era `ContinuidadVisitasSection`: una tarjeta independiente que el modal
 * montaba aparte del SmartField de tarifas. Ahora es el PANEL ACTIVO del modo
 * "Continuar" y se renderiza DENTRO de `TarifasVisitasSinPreviaSmartField`
 * (patrón PO/Edificaciones): un solo formulario, un solo SmartField, una sola
 * llamada de cotización.
 *
 * Reglas del contrato (io-continuity-visitas-impacto / io-continuity-visitas-ui
 * / io-continuity-server-quote):
 *  · La continuidad es OPCIONAL: sin el modo "Continuar", la IO es normal y su
 *    `sub_total` es el valor completo del trabajo (comportamiento vigente).
 *  · `B.cantidad_visitas` contiene SOLO las visitas nuevas del inspector de B.
 *  · La liquidación nueva (B) cobra la DIFERENCIA: valor completo − crédito.
 *  · NO existe endpoint de candidatas de continuidad: la previa se referencia
 *    desde el listado/detalle de IO existente o se ingresa manual.
 *  · El panel NO hace aritmética monetaria (DD-7): el único dato que DECLARA
 *    el usuario es el BRUTO pagado en la IO previa (`total_pagado_previa`) y
 *    todas las cifras mostradas (valor completo, crédito, diferencia) son las
 *    que devuelve el SERVIDOR en el bloque `continuidad` de la cotización.
 *  · El límite del crédito NO se valida en el cliente: es el invariante IV-5
 *    del servidor (400).
 *
 * En EDICIÓN la referencia a la liquidación previa (A) y su tarifa histórica
 * son METADATO HISTÓRICO: se muestran en solo lectura y la UI nunca las
 * reprecia. Lo editable es el registro de continuidad: el bruto declarado, las
 * visitas pendientes, el total de visitas (solo cuando no hay A referenciada) y
 * la observación.
 *
 * El panel NO decide si la continuidad está encendida: eso es del modo de
 * cotización (el selector del SmartField). Aquí solo se declara el
 * discriminador de la OPERACIÓN (`activar` / `mantener` / `desactivar`).
 */
import { AlertTriangle, Link2, Link2Off } from "lucide-react";
import { useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import { useWatch } from "react-hook-form";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { Button } from "@/components/ui/button";
import { formatCurrencyTrimmed } from "@/utils/number-formatter";
import type { LiquidacionInspeccionObraListItem } from "../../../schemas/liquidacion-inspeccion-obra.schema";
import type { CotizacionVisitasContinuidadOut } from "../../../schemas/liquidacion-io-cotizacion.schema";
import type { ContinuidadVisitasOut } from "../../../schemas/liquidacion-visitas.schema";
import type {
  ContinuidadVisitasFormData,
  ModoContinuidadVisitas,
  VisitasFormData,
} from "../../../schemas/liquidacion-visitas-form.schema";

/**
 * Bloque `continuidad` de la cotización del SERVIDOR (las cifras
 * autoritativas). El panel las RENDERIZA: no las recalcula.
 */
export type CotizacionContinuidad = CotizacionVisitasContinuidadOut;

interface ContinuidadVisitasPanelProps {
  methods: UseFormReturn<VisitasFormData>;
  /** Liquidación previa (A) desde la que se inició el "Continuar". */
  previa?: LiquidacionInspeccionObraListItem | null;
  /**
   * Bloque `continuidad` de la cotización vigente (la calcula el SmartField de
   * tarifas con el servidor). `null` mientras no llegue o cuando el modo no
   * admite continuidad.
   */
  cotizacion?: CotizacionContinuidad | null;
  /**
   * Modo del formulario:
   *  · `create` (default): la continuidad se activa desde cero.
   *  · `edit`: la continuidad se rehidrata del registro persistido y puede
   *    mantenerse o desactivarse (y activarse si no existía).
   */
  mode?: "create" | "edit";
  /**
   * Registro de continuidad PERSISTIDO de la IO (`liquidacion_tipo.continuidad`).
   * Solo en `mode="edit"`: es el snapshot histórico congelado (referencia a A,
   * crédito histórico y valor completo guardado).
   */
  continuidadPersistida?: ContinuidadVisitasOut | null;
}

function toNumber(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

/** Formatea un importe del servidor; `undefined` se muestra como "—". */
function formatMonto(value: number | undefined | null): string {
  if (value === undefined || value === null) return "—";
  return formatCurrencyTrimmed(value, 2);
}

/**
 * BRUTO cobrado en la liquidación previa (Σ de los comprobantes ACTIVOS).
 *
 * Es el ÚNICO cálculo de dinero del cliente y NO es una cifra de resultado:
 * es la SUGERENCIA de prefill del bruto DECLARADO (`total_pagado_previa`),
 * que el usuario confirma. La cifra autoritativa del crédito la deriva el
 * servidor (DD-7).
 */
export function totalCobradoPrevia(
  previa: LiquidacionInspeccionObraListItem,
): number | undefined {
  const total = (previa.liquidacion_general.comprobantes ?? [])
    .filter((comprobante) => comprobante.activo)
    .reduce((total, comprobante) => total + toNumber(comprobante.monto), 0);
  return total > 0 ? total : undefined;
}

/**
 * La previa es una referencia opcional: su BRUTO cobrado se propone como el
 * bruto declarado del crédito y el usuario puede ajustarlo antes de crear la
 * IO nueva.
 */
export function deriveContinuidadDefaults(
  previa: LiquidacionInspeccionObraListItem,
): ContinuidadVisitasFormData {
  return {
    liquidacion_previa_id: previa.liquidacion_general.id,
    total_pagado_previa: totalCobradoPrevia(previa),
  };
}

/**
 * Rehidrata el bloque de continuidad del formulario desde el registro
 * PERSISTIDO de la IO (`liquidacion_tipo.continuidad`).
 *
 * NO es lo mismo que `deriveContinuidadDefaults` (que deriva de la previa A
 * para la creación): aquí la referencia histórica ya existe y está congelada,
 * y sus valores NO se reprecian.
 *
 * El BRUTO vigente del crédito (`total_credito`, derivado por el servidor) se
 * propone como el bruto DECLARADO: al re-declararlo, el servidor lo vuelve a
 * derivar con el MISMO IGV histórico de la cotización de edición.
 *
 * `modo` NO se rehidrata a propósito: la operación de continuidad solo viaja
 * si el usuario interactúa con el panel (Explorer §7.7). Un bloque
 * rehidratado sin `modo` produce un PATCH idéntico al vigente.
 */
export function deriveContinuidadEditDefaults(
  continuidad: ContinuidadVisitasOut,
): ContinuidadVisitasFormData {
  const totalCredito = toNumber(continuidad.total_credito);
  return {
    liquidacion_previa_id: continuidad.liquidacion_previa_id ?? undefined,
    visitas_previas_totales: continuidad.visitas_previas_totales ?? undefined,
    visitas_previas_pendientes: continuidad.visitas_previas_pendientes ?? 0,
    categoria_previa: continuidad.categoria_previa ?? undefined,
    total_pagado_previa: totalCredito > 0 ? totalCredito : undefined,
    subtotal_credito: toNumber(continuidad.subtotal_credito),
    observacion: continuidad.observacion ?? "",
  };
}

export function ContinuidadVisitasPanel({
  methods,
  previa,
  cotizacion,
  mode = "create",
  continuidadPersistida = null,
}: ContinuidadVisitasPanelProps) {
  const isEdit = mode === "edit";
  const continuidad = useWatch({
    control: methods.control,
    name: "continuidad",
  }) as ContinuidadVisitasFormData | undefined;

  // Confirmación explícita del apagado: `desactivar` NUNCA viaja sin que el
  // usuario confirme el efecto comercial (el crédito se elimina y B pasa a
  // cobrar el valor completo del trabajo).
  const [confirmandoDesactivacion, setConfirmandoDesactivacion] =
    useState(false);
  // Modo vigente antes de pedir el apagado: permite volver al estado previo
  // ("sin tocar" o "mantener") si el usuario se arrepiente.
  const [modoAntesDeDesactivar, setModoAntesDeDesactivar] = useState<
    ModoContinuidadVisitas | undefined
  >(undefined);

  const hayRegistroPersistido = Boolean(continuidadPersistida);
  const modo = isEdit ? continuidad?.modo : undefined;
  const pendienteDesactivar = modo === "desactivar";
  // Modo que corresponde a EDITAR el registro de continuidad. Si no existe
  // registro persistido, la única operación posible es `activar`.
  const modoOperacion: ModoContinuidadVisitas = hayRegistroPersistido
    ? "mantener"
    : "activar";

  const update = (patch: Partial<ContinuidadVisitasFormData>) => {
    methods.setValue(
      "continuidad",
      {
        ...(continuidad ?? {}),
        // En edición, editar el bloque ES la operación de continuidad: el
        // `modo` marca que el PATCH debe llevar el bloque.
        ...(isEdit ? { modo: modoOperacion } : {}),
        ...patch,
      } as never,
      { shouldDirty: true, shouldValidate: true },
    );
  };

  // ── Apagado de la continuidad (exige confirmación explícita) ──────────────
  const handleSolicitarDesactivacion = () => {
    setModoAntesDeDesactivar(continuidad?.modo);
    setConfirmandoDesactivacion(true);
  };

  const handleConfirmarDesactivacion = () => {
    methods.setValue(
      "continuidad",
      { ...(continuidad ?? {}), modo: "desactivar" } as never,
      { shouldDirty: true, shouldValidate: true },
    );
    setConfirmandoDesactivacion(false);
  };

  const handleCancelarDesactivacion = () => {
    setConfirmandoDesactivacion(false);
  };

  const handleRevertirDesactivacion = () => {
    const restaurado = { ...(continuidad ?? {}) } as ContinuidadVisitasFormData;
    if (modoAntesDeDesactivar) {
      restaurado.modo = modoAntesDeDesactivar;
    } else {
      delete restaurado.modo;
    }
    methods.setValue("continuidad", restaurado as never, {
      shouldDirty: true,
      shouldValidate: true,
    });
  };

  // ── Resumen: valor completo | crédito | total a cobrar ──────────────────
  // TODAS estas cifras son del SERVIDOR: el bloque `continuidad` de la
  // cotización (autoritativo) o, cuando la cotización aún no ha llegado, el
  // registro de continuidad persistido (también derivado por el servidor).
  // El cliente NO calcula ninguna diferencia.
  const valorCompletoNeto =
    cotizacion?.valor_completo_neto ?? continuidadPersistida?.monto_acumulado;
  const valorCompletoBruto =
    cotizacion?.valor_completo_bruto ?? continuidadPersistida?.total_acumulado;
  const creditoNeto =
    cotizacion?.credito_neto ?? continuidadPersistida?.subtotal_credito;
  const creditoBruto =
    cotizacion?.credito_bruto ?? continuidadPersistida?.total_credito;
  const diferenciaNeto = cotizacion?.diferencia_neto;
  const diferenciaBruto = cotizacion?.diferencia_bruto;

  const totalCobrado = previa ? totalCobradoPrevia(previa) : undefined;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Link2 className="h-4 w-4 text-primary" />
          <h4 className="text-sm font-semibold uppercase tracking-wide">
            Continuidad de visitas
          </h4>
        </div>
        {isEdit && hayRegistroPersistido && !pendienteDesactivar && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleSolicitarDesactivacion}
          >
            Desactivar continuidad
          </Button>
        )}
      </div>

      {/* Confirmación explícita del apagado */}
      {confirmandoDesactivacion && (
        <div
          role="alert"
          className="space-y-3 rounded-lg border border-destructive/40 bg-destructive/5 p-3"
        >
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
            <div className="space-y-1">
              <p className="text-sm font-semibold text-destructive">
                Desactivar la continuidad de visitas
              </p>
              <p className="text-xs text-muted-foreground">
                Al desactivar la continuidad se elimina el crédito de la previa
                y la liquidación pasa a cobrar el valor completo del trabajo (no
                la diferencia).
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={handleConfirmarDesactivacion}
            >
              Confirmar desactivación
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCancelarDesactivacion}
            >
              Cancelar
            </Button>
          </div>
        </div>
      )}

      {/* Apagado pendiente de confirmar al guardar */}
      {pendienteDesactivar && (
        <div
          role="alert"
          className="space-y-3 rounded-lg border border-destructive/40 bg-destructive/5 p-3"
        >
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
            <div className="space-y-1">
              <p className="text-sm font-semibold text-destructive">
                La continuidad se desactivará al guardar
              </p>
              <p className="text-xs text-muted-foreground">
                Se elimina el crédito de la previa y la liquidación pasará a
                cobrar el valor completo del trabajo (no la diferencia).
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleRevertirDesactivacion}
          >
            Mantener continuidad
          </Button>
        </div>
      )}

      {/* Referencia a la liquidación previa */}
      {isEdit && hayRegistroPersistido ? (
        <div className="rounded-lg border border-border/50 bg-muted/20 p-3 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Liquidación previa (referencia histórica)
            </span>
            <span className="text-xs text-muted-foreground">Solo lectura</span>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            <span className="text-muted-foreground">Previa:</span>
            <span className="text-right font-medium break-all">
              {continuidadPersistida?.liquidacion_previa_id ??
                "Ingreso manual (previa fuera de CAM)"}
            </span>
            <span className="text-muted-foreground">Categoría previa:</span>
            <span className="text-right font-medium">
              {continuidadPersistida?.categoria_previa ?? "—"}
            </span>
            <span className="text-muted-foreground">
              Visitas totales de la previa:
            </span>
            <span className="text-right font-medium tabular-nums">
              {continuidadPersistida?.visitas_previas_totales ?? "—"}
            </span>
            <span className="text-muted-foreground">
              Crédito histórico (neto):
            </span>
            <span className="text-right font-medium tabular-nums">
              {formatMonto(continuidadPersistida?.subtotal_credito)}
            </span>
            <span className="text-muted-foreground">
              Crédito histórico (con IGV):
            </span>
            <span className="text-right font-medium tabular-nums">
              {formatMonto(continuidadPersistida?.total_credito)}
            </span>
            <span className="text-muted-foreground">
              Valor completo de B (guardado):
            </span>
            <span className="text-right font-medium tabular-nums">
              {formatMonto(continuidadPersistida?.monto_acumulado)}
            </span>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-border/50 bg-muted/20 p-3 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Liquidación previa
            </span>
            {continuidad?.liquidacion_previa_id ? (
              <Button
                type="button"
                variant="ghost"
                size="xs"
                className="h-6 gap-1 px-2 text-xs"
                onClick={() =>
                  update({
                    liquidacion_previa_id: undefined,
                    categoria_previa: undefined,
                  })
                }
              >
                <Link2Off className="h-3 w-3" />
                Quitar referencia
              </Button>
            ) : null}
          </div>
          {previa && continuidad?.liquidacion_previa_id ? (
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <span className="text-muted-foreground">Expediente:</span>
              <span className="text-right font-medium">
                {previa.liquidacion_general.expediente || "—"}
              </span>
              <span className="text-muted-foreground">Categoría previa:</span>
              <span className="text-right font-medium">
                {continuidad.categoria_previa ??
                  previa.liquidacion_tipo.categoria ??
                  "—"}
              </span>
              <span className="text-muted-foreground">Tarifa (% UIT):</span>
              <span className="text-right font-medium tabular-nums">
                {previa.liquidacion_tipo.porcentaje_uit != null
                  ? `${toNumber(previa.liquidacion_tipo.porcentaje_uit)}%`
                  : "—"}
              </span>
              <span className="text-muted-foreground">
                Visitas de la previa:
              </span>
              <span className="text-right font-medium tabular-nums">
                {previa.liquidacion_tipo.cantidad_visitas ?? 0}
              </span>
              <span className="text-muted-foreground">
                Total cobrado (sugerencia):
              </span>
              <span className="text-right font-medium tabular-nums">
                {formatMonto(totalCobrado)}
              </span>
              <span className="text-muted-foreground">
                Valor completo previa:
              </span>
              <span className="text-right font-medium tabular-nums">
                {formatCurrencyTrimmed(
                  toNumber(
                    previa.liquidacion_tipo.continuidad?.monto_acumulado ??
                      previa.liquidacion_general.sub_total,
                  ),
                  2,
                )}
              </span>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">
              Opcional: selecciona una IO anterior para consultar sus datos.
            </p>
          )}
        </div>
      )}

      {/*
       * El único dato que el usuario DECLARA: el BRUTO pagado en la IO previa
       * (IGV incluido). El servidor lo valida y deriva el par (crédito neto,
       * crédito bruto) con el IGV efectivo de la ruta.
       */}
      <MoneyInput
        name="continuidad.total_pagado_previa"
        label="Total pagado en la liquidación previa (con IGV)"
        control={methods.control}
        error={methods.formState.errors.continuidad?.total_pagado_previa}
        onValueChange={(value) => {
          if (isEdit) {
            // MoneyInput writes through RHF first. Preserve that fresh value
            // while marking the continuity transition for the PATCH.
            update({
              modo: modoOperacion,
              total_pagado_previa: value,
            });
          }
          void methods.trigger("continuidad.total_pagado_previa");
        }}
      />

      {/* Resumen del cobro: valor completo | crédito | total a cobrar */}
      <div className="space-y-1.5 rounded-lg border border-border bg-muted/20 p-3 text-sm">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Valor completo (B):</span>
          <span className="font-medium tabular-nums">
            {formatMonto(valorCompletoNeto)}
          </span>
        </div>
        <div className="flex justify-between text-[11px] text-muted-foreground">
          <span>Valor completo con IGV:</span>
          <span className="tabular-nums">
            {formatMonto(valorCompletoBruto)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Crédito de la previa:</span>
          <span className="font-medium tabular-nums text-destructive">
            − {formatMonto(creditoNeto)}
          </span>
        </div>
        <div className="flex justify-between text-[11px] text-muted-foreground">
          <span>Crédito con IGV:</span>
          <span className="tabular-nums">− {formatMonto(creditoBruto)}</span>
        </div>
        <div className="flex justify-between border-t border-border pt-1.5 font-semibold">
          <span>Total a cobrar:</span>
          <span className="text-primary tabular-nums">
            {formatMonto(diferenciaBruto)}
          </span>
        </div>
        <div className="flex justify-between text-[11px] text-muted-foreground">
          <span>Total a cobrar (neto):</span>
          <span className="tabular-nums">{formatMonto(diferenciaNeto)}</span>
        </div>
        <p className="text-[11px] text-muted-foreground">
          El valor completo, el crédito y la diferencia los calcula y valida el
          servidor: aquí solo se muestran sus cifras.
        </p>
      </div>

      {isEdit ? (
        hayRegistroPersistido ? (
          <p className="text-[11px] text-muted-foreground">
            Al guardar se recalculan el valor completo de B y la diferencia. La
            referencia a la liquidación previa y su tarifa histórica no se
            modifican.
          </p>
        ) : (
          <p className="text-[11px] text-muted-foreground">
            Al guardar se creará el registro de continuidad y la liquidación
            pasará a cobrar la diferencia entre el valor completo del trabajo y
            el crédito de la previa.
          </p>
        )
      ) : (
        <p className="text-[11px] text-muted-foreground">
          La continuidad es opcional: vuelve al modo Normal para que la
          liquidación cobre el valor completo del trabajo.
        </p>
      )}
    </div>
  );
}
