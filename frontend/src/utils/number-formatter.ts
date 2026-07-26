/**
 * Number formatting utilities for liquidation UI display.
 *
 * - trimTrailingZeros: removes insignificant trailing zeros from decimal numbers.
 * - formatDecimalPercent: converts a decimal fraction to a trimmed percentage string.
 *
 * These are intended for card/list/paginated UI display only.
 * Do NOT use in PDF or legal print output — those should use fixed formatting.
 */

/**
 * Remove insignificant trailing zeros from a decimal number.
 *
 * @param value  - Number or numeric string to format.
 * @param maxDecimals - Optional cap on decimal places (default 6).
 * @returns Formatted string without trailing zeros (e.g. "5", "5.001", "5.5").
 *
 * @example
 * trimTrailingZeros(5.000)   // "5"
 * trimTrailingZeros(2.0000)  // "2"
 * trimTrailingZeros(5.001)   // "5.001"
 * trimTrailingZeros(5.5000)  // "5.5"
 * trimTrailingZeros(0.0500)  // "0.05"
 * trimTrailingZeros(0.05001) // "0.05001"
 */
export function trimTrailingZeros(
  value: number | string,
  maxDecimals: number = 6,
): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(num)) return String(value);

  const fixed = num.toFixed(maxDecimals);
  // Strip trailing zeros after the decimal point
  return fixed.replace(/\.(\d*?)0+$/, (match, decimals) =>
    decimals ? `.${decimals}` : "",
  );
}

/**
 * Convert a decimal fraction to a trimmed percentage string.
 *
 * @param value - Decimal fraction (e.g. 0.05 for 5%) or null/undefined.
 * @param maxDecimals - Optional cap on decimal places (default 4).
 * @returns Percentage string with trailing zeros removed, or "—" for null/undefined.
 *
 * @example
 * formatDecimalPercent(0.05)    // "5"
 * formatDecimalPercent(0.0500)   // "5"
 * formatDecimalPercent(0.051)    // "5.1"
 * formatDecimalPercent(0.055)    // "5.5"
 * formatDecimalPercent(0.0555)  // "5.55"
 * formatDecimalPercent(0.05555) // "5.555"
 * formatDecimalPercent(null)    // "—"
 */
export function formatDecimalPercent(
  value: number | null | undefined,
  maxDecimals: number = 4,
): string {
  if (value == null) return "—";
  return `${trimTrailingZeros(value * 100, maxDecimals)}%`;
}

/**
 * Format a currency value as a trimmed string prefixed with "S/ ".
 *
 * Unlike formatCurrency helpers in some cards, this one trims trailing zeros
 * for cleaner display in list/card UI. Use a dedicated fixed-format helper
 * for PDF/legal output where consistent decimal places are required.
 *
 * @param value - Numeric value or null/undefined.
 * @param maxDecimals - Optional cap on decimal places (default 4).
 * @returns "S/ {value}" with trailing zeros removed, or "—" for null/undefined.
 *
 * @example
 * formatCurrencyTrimmed(5.000)   // "S/ 5"
 * formatCurrencyTrimmed(5.5000)  // "S/ 5.5"
 * formatCurrencyTrimmed(5.001)   // "S/ 5.001"
 * formatCurrencyTrimmed(null)    // "—"
 */
export function formatCurrencyTrimmed(
  value: number | null | undefined,
  maxDecimals: number = 4,
): string {
  if (value == null) return "—";
  return `S/ ${trimTrailingZeros(value, maxDecimals)}`;
}
