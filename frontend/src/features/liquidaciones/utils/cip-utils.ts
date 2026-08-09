/**
 * Pure utility helpers for CIP input sanitization and validation.
 * These functions have no React/UI dependencies and can be unit-tested directly.
 */

/**
 * Sanitize CIP input: remove non-digit characters and limit to 6 characters.
 */
export function sanitizeCipInput(value: string): string {
  return value.replace(/\D/g, "").slice(0, 6);
}

/**
 * Check if a sanitized CIP string is valid (exactly 6 digits).
 */
export function isValidCip(digits: string): boolean {
  return /^\d{6}$/.test(digits);
}
