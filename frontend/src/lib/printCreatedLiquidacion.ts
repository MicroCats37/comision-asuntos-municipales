"use client";

/**
 * Production helper for post-create PDF printing.
 *
 * Uses the same printLiquidacionDocument renderer as the card/list PDF button,
 * with the created response adapted to LiquidacionCardBase.
 *
 * NO refetch - uses the created response directly.
 */
import type { LiquidacionCardBase } from "../features/liquidaciones/types/liquidacion-general";

export type PrintFn = (item: LiquidacionCardBase) => Promise<void>;
export type ToCardBaseFn<T> = (created: T) => LiquidacionCardBase;

/**
 * Prints a newly created liquidacion using the card/list renderer path.
 *
 * @param created - The raw created response from the API
 * @param toCardBase - Adapter function to convert created response to LiquidacionCardBase
 * @param printFn - The print function (defaults to printLiquidacionDocument)
 *
 * Usage:
 *   printCreatedLiquidacion(created, HUToCardBase, printLiquidacionDocument)
 *   printCreatedLiquidacion(created, MSToCardBase, printLiquidacionDocument)
 *   printCreatedLiquidacion(created, IVToCardBase, printLiquidacionDocument)
 *   printCreatedLiquidacion(created, TaludesToCardBase, printLiquidacionDocument)
 */
export async function printCreatedLiquidacion<T>(
  created: T,
  toCardBase: ToCardBaseFn<T>,
  printFn: PrintFn,
): Promise<void> {
  const cardBase = toCardBase(created);
  await printFn(cardBase);
}
