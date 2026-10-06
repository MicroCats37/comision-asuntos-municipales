import { api } from "@/lib/api";
import type { ApiResponse } from "@/types/api.types";
import type { LoginResponse, MeResponse } from "../schemas/auth.types";

/**
 * Login with username and password.
 */
export async function loginUsername(
  username: string,
  password: string,
): Promise<ApiResponse<LoginResponse>> {
  const { data } = await api.post("/auth/login/username", {
    username,
    password,
  });
  return data;
}

/**
 * Login with DNI and password.
 */
export async function loginDni(
  dni: string,
  password: string,
): Promise<ApiResponse<LoginResponse>> {
  const { data } = await api.post("/auth/login/dni", { dni, password });
  return data;
}

/**
 * Login with email and password.
 */
export async function loginEmail(
  email: string,
  password: string,
): Promise<ApiResponse<LoginResponse>> {
  const { data } = await api.post("/auth/login/email", { email, password });
  return data;
}

/**
 * Get current user info.
 */
export async function getMe(): Promise<ApiResponse<MeResponse>> {
  const { data } = await api.get("/auth/me/");
  return data;
}
