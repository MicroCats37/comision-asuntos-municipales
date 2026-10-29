"use client";

import { Info, Settings2 } from "lucide-react";
import type { UseFormReturn } from "react-hook-form";
import { useWatch } from "react-hook-form";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  ESTRATEGIA_COTIZACION_DESCRIPCIONES,
  ESTRATEGIA_COTIZACION_LABELS,
  ESTRATEGIAS_COTIZACION_PO,
  type EstrategiaCotizacionPO,
} from "../../schemas/liquidacion-po-estrategia.schema";
import {
  campoProhibidoPorEstrategia,
  ESTRATEGIA_POR_DEFECTO,
  estrategiaUsaTotalExplicito,
} from "../../utils/estrategiaCotizacion";

interface EstrategiaCotizacionFieldProps {
  // biome-ignore lint/suspicious/noExplicitAny: UseFormReturn pattern matches the existing smart fields
  methods: UseFormReturn<any>;
  disabled?: boolean;
}

interface EstrategiaValorFieldProps {
  // biome-ignore lint/suspicious/noExplicitAny: UseFormReturn pattern matches the existing smart fields
  methods: UseFormReturn<any>;
  /** Valor declarado persistido (edición / revisión). */
  defaultValorDeclarado?: number;
  /** Total explícito persistido (edición / revisión). */
  defaultTotalExplicito?: number;
  disabled?: boolean;
}

/**
 * EstrategiaCotizacionField — selector accesible de la estrategia de
 * cotización del motor PO de Edificaciones.
 *
 * Solo existe para Edificaciones: Taludes, Impacto Vial, edge y legacy no
 * tienen estrategias (su contrato queda intacto).
 *
 * Al salir de TOTAL_EXPLICITO limpia `total_explicito`; al entrar conserva el
 * valor declarado porque sigue siendo información obligatoria de la obra.
 */
export function EstrategiaCotizacionField({
  methods,
  disabled = false,
}: EstrategiaCotizacionFieldProps) {
  const estrategia =
    (useWatch({
      control: methods.control,
      name: "estrategia_cotizacion",
    }) as EstrategiaCotizacionPO | undefined) ?? ESTRATEGIA_POR_DEFECTO;

  const handleSelect = (valor: string) => {
    const nueva = valor as EstrategiaCotizacionPO;
    methods.setValue("estrategia_cotizacion", nueva, {
      shouldValidate: false,
      shouldDirty: true,
    });

    const prohibido = campoProhibidoPorEstrategia(nueva);
    if (prohibido) {
      methods.setValue(prohibido, undefined, {
        shouldValidate: false,
        shouldDirty: true,
      });
    }
  };

  return (
    <div className="flex items-center gap-1.5">
      <Select
        value={estrategia}
        onValueChange={handleSelect}
        disabled={disabled}
      >
        <SelectTrigger
          id="estrategia-cotizacion"
          size="sm"
          className="h-7 max-w-64 rounded-full border-primary/25 bg-primary/10 px-2.5 text-xs font-medium text-primary"
          aria-label="Estrategia de cotización"
        >
          <Settings2 className="size-3" />
          <SelectValue />
        </SelectTrigger>
        <SelectContent align="end">
          {ESTRATEGIAS_COTIZACION_PO.map((valor) => (
            <SelectItem key={valor} value={valor}>
              {ESTRATEGIA_COTIZACION_LABELS[valor]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className="inline-flex size-6 shrink-0 items-center justify-center rounded-full text-primary/70 transition-colors hover:bg-primary/10 hover:text-primary"
              aria-label={`Información sobre ${ESTRATEGIA_COTIZACION_LABELS[estrategia]}`}
            >
              <Info className="size-3.5" />
            </button>
          </TooltipTrigger>
          <TooltipContent
            side="bottom"
            sideOffset={8}
            className="block w-72 max-w-[calc(100vw-2rem)] space-y-1.5 p-3"
          >
            <p className="text-xs font-semibold">
              {ESTRATEGIA_COTIZACION_LABELS[estrategia]}
            </p>
            <p className="text-xs leading-relaxed opacity-90">
              {ESTRATEGIA_COTIZACION_DESCRIPCIONES[estrategia]}
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}

/**
 * EstrategiaValorField — input monetario que corresponde a la estrategia
 * activa.
 *
 * - `NORMAL_SELECCIONADAS` y `TARIFA_HABILITADAS_PARTICIPANTES` → valor
 *   declarado del proyecto.
 * - `TOTAL_EXPLICITO` → valor informativo de la obra y total final autoritativo.
 */
export function EstrategiaValorField({
  methods,
  defaultValorDeclarado,
  defaultTotalExplicito,
  disabled = false,
}: EstrategiaValorFieldProps) {
  const estrategia =
    (useWatch({
      control: methods.control,
      name: "estrategia_cotizacion",
    }) as EstrategiaCotizacionPO | undefined) ?? ESTRATEGIA_POR_DEFECTO;

  if (estrategiaUsaTotalExplicito(estrategia)) {
    return (
      <>
        <MoneyInput
          name="valor_declarado"
          label="Valor de la obra (S/)"
          placeholder="S/ 0.00"
          control={methods.control}
          required
          disabled={disabled}
          defaultValue={defaultValorDeclarado ?? ""}
        />
        <MoneyInput
          name="total_explicito"
          label="Total final (S/)"
          placeholder="S/ 0.00"
          control={methods.control}
          required
          disabled={disabled}
          defaultValue={defaultTotalExplicito ?? ""}
        />
      </>
    );
  }

  return (
    <MoneyInput
      name="valor_declarado"
      label="Valor Declarado (S/)"
      placeholder="S/ 0.00"
      control={methods.control}
      required
      disabled={disabled}
      defaultValue={defaultValorDeclarado ?? ""}
    />
  );
}
