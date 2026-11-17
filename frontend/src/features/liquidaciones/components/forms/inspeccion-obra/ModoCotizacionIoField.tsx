"use client";

/**
 * ModoCotizacionIoField — selector accesible del MODO DE COTIZACIÓN del motor
 * IO (Inspección de Obra).
 *
 * Espeja el patrón de PO/Edificaciones (`EstrategiaCotizacionField`): el modo
 * es un discriminador TIPADO que vive en el FORM (RHF) y el SmartField de
 * tarifas lo lee para decidir qué panel muestra.
 *
 *  · `Normal`    → el SmartField muestra la cotización por valor completo
 *    (comportamiento vigente) y no toca la continuidad.
 *  · `Continuar` → el SmartField muestra, como panel activo, la referencia
 *    histórica, el crédito y la diferencia.
 *
 * El selector NO decide qué pasa con el bloque de continuidad: eso es del
 * dueño del SmartField, que le pasa `onModoChange` (slot) para componer el
 * ciclo de vida del bloque.
 */
import type { UseFormReturn } from "react-hook-form";
import { useWatch } from "react-hook-form";
import { cn } from "@/lib/utils";
import {
  esModoCotizacionValido,
  MODO_COTIZACION_IO_DESCRIPCIONES,
  MODO_COTIZACION_IO_LABELS,
  MODOS_COTIZACION_IO,
  type ModoCotizacionIO,
} from "../../../schemas/liquidacion-io-modo-cotizacion.schema";
import { MODO_COTIZACION_IO_POR_DEFECTO } from "../../../utils/modoCotizacionIo";

interface ModoCotizacionIoFieldProps {
  // biome-ignore lint/suspicious/noExplicitAny: UseFormReturn pattern matches the existing smart fields
  methods: UseFormReturn<any>;
  /**
   * Bloquea el selector. Se usa cuando el registro PERSISTIDO ya tiene
   * continuidad: la liquidación cobra la diferencia, así que el modo "Normal"
   * (valor completo) sería una vista falsa.
   */
  disabled?: boolean;
  /**
   * Slot de composición: el dueño del SmartField reacciona al cambio de modo
   * (p. ej. abrir o descartar el bloque de continuidad).
   */
  onModoChange?: (modo: ModoCotizacionIO) => void;
}

export function ModoCotizacionIoField({
  methods,
  disabled = false,
  onModoChange,
}: ModoCotizacionIoFieldProps) {
  const modo = useWatch({
    control: methods.control,
    name: "modo_cotizacion",
  }) as ModoCotizacionIO | undefined;

  const modoVigente = esModoCotizacionValido(modo)
    ? modo
    : MODO_COTIZACION_IO_POR_DEFECTO;

  const handleSelect = (valor: ModoCotizacionIO) => {
    methods.setValue("modo_cotizacion", valor, {
      shouldValidate: false,
      shouldDirty: true,
    });
    onModoChange?.(valor);
  };

  return (
    <div
      className="flex flex-row items-center gap-1 rounded-full border border-primary/25 bg-primary/10 p-0.5"
      role="radiogroup"
      aria-label="Modo de cotización"
      title={MODO_COTIZACION_IO_DESCRIPCIONES[modoVigente]}
    >
      {MODOS_COTIZACION_IO.map((valor) => {
        const seleccionado = modoVigente === valor;
        return (
          <label
            key={valor}
            className={cn(
              "cursor-pointer rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
              seleccionado
                ? "bg-primary text-primary-foreground"
                : "text-primary hover:bg-primary/10",
              disabled && "cursor-not-allowed opacity-60",
            )}
          >
            <span>{MODO_COTIZACION_IO_LABELS[valor]}</span>
            <input
              type="radio"
              name="modo_cotizacion_io"
              className="sr-only"
              checked={seleccionado}
              disabled={disabled}
              onChange={() => handleSelect(valor)}
            />
          </label>
        );
      })}
    </div>
  );
}
