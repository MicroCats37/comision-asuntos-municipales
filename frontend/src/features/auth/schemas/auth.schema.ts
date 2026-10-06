import { z } from "zod";
import type { LoginMode } from "./auth.types";

// ── Login Schemas (CAM only — username, DNI, email) ──────────────────────────

/**
 * LoginUsernameFormSchema — requires username + password.
 * Use for username login flow.
 */
export const LoginUsernameFormSchema = z.object({
  username: z.string().min(3, "Usuario debe tener al menos 3 caracteres"),
  password: z.string().min(5, "Contraseña debe tener al menos 6 caracteres"),
});

export type LoginUsernameFormData = z.infer<typeof LoginUsernameFormSchema>;

/**
 * LoginDniFormSchema — requires dni + password only.
 * Use for DNI-only login flow.
 */
export const LoginDniFormSchema = z.object({
  dni: z.string().min(8, "DNI debe tener al menos 8 caracteres"),
  password: z.string().min(5, "Contraseña debe tener al menos 6 caracteres"),
});

export type LoginDniFormData = z.infer<typeof LoginDniFormSchema>;

/**
 * LoginEmailFormSchema — requires email + password only.
 * Use for email login flow.
 */
export const LoginEmailFormSchema = z.object({
  email: z.string().email("Email inválido"),
  password: z.string().min(5, "Contraseña debe tener al menos 6 caracteres"),
});

export type LoginEmailFormData = z.infer<typeof LoginEmailFormSchema>;

export type { LoginMode };
