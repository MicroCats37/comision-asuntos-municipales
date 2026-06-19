/**
 * Auth types for CAM (Centro de Atención al Mutuario)
 * Endpoints: login username, login dni, login email
 */

// ── Login Mode ────────────────────────────────────────────────────────────────

/** Discriminated union for login mode */
export type LoginMode = "username" | "dni" | "email";

// ── Login Response ───────────────────────────────────────────────────────────

export interface LoginTokens {
  access_token: string;
  refresh_token: string;
  expires_at: string;
}

/**
 * User info returned from login and /auth/me/ endpoint.
 */
export interface MeResponse {
  id: number;
  nombre: string;
  apellido: string;
}

/**
 * Respuesta de login del backend: access_token + refresh_token + expires_at + user
 */
export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  expires_at: string;
  user: MeResponse;
}
