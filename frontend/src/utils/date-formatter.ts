import { format, formatDistanceToNow, isValid, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import type { Locale } from "react-day-picker";

type DateInput = Date | string | number | null | undefined;

interface FormatOptions {
  locale?: Locale;
  customFormat?: string;
}

function toDate(input: DateInput): Date | null {
  if (!input) return null;
  const date = typeof input === "string" ? parseISO(input) : new Date(input);
  return isValid(date) ? date : null;
}

/** Returns "12 de enero de 2025" */
export function formatDate(input: DateInput, options?: FormatOptions): string {
  const date = toDate(input);
  if (!date) return "";
  if (options?.customFormat)
    return format(date, options.customFormat, { locale: options.locale ?? es });
  return format(date, "PPP", { locale: options?.locale ?? es });
}

/** Returns "12 de enero de 2025, 14:30" */
export function formatDateTime(
  input: DateInput,
  options?: FormatOptions,
): string {
  const date = toDate(input);
  if (!date) return "";
  if (options?.customFormat)
    return format(date, options.customFormat, { locale: options.locale ?? es });
  return format(date, "PPp", { locale: options?.locale ?? es });
}

/** Returns "hace 2 horas" or "en 3 días" */
export function formatRelative(
  input: DateInput,
  options?: FormatOptions,
): string {
  const date = toDate(input);
  if (!date) return "";
  return formatDistanceToNow(date, {
    addSuffix: true,
    locale: options?.locale ?? es,
  });
}

/** Returns "12 ene" */
export function formatShort(input: DateInput, options?: FormatOptions): string {
  const date = toDate(input);
  if (!date) return "";
  if (options?.customFormat)
    return format(date, options.customFormat, {
      locale: options?.locale ?? es,
    });
  return format(date, "d MMM", { locale: options?.locale ?? es });
}
