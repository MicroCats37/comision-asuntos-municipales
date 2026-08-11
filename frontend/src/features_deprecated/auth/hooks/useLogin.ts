"use client";

import { useMutation } from "@tanstack/react-query";
import { deleteCookie, setCookie } from "cookies-next";
import { api } from "@/lib/api";
import { AUTH_COOKIES } from "@/lib/auth";
import type { ApiResponse } from "@/types/api.types";
import type {
  LoginDniFormData,
  LoginEmailFormData,
  LoginResponse,
  LoginUsernameFormData,
  MeResponse,
} from "../schemas";

export type LoginUsernamePayload = LoginUsernameFormData;
export type LoginDniPayload = LoginDniFormData;
export type LoginEmailPayload = LoginEmailFormData;
export type LoginPayload =
  | LoginUsernamePayload
  | LoginDniPayload
  | LoginEmailPayload;

/**
 * Client-side login flow:
 * 1. POST /auth/login/{type} with credentials → get access_token + refresh_token + expires_at + user
 * 2. Set cookies for tokens and user session
 *
 * Supports three login modes: username, dni, email
 */
export function useLogin() {
  return useMutation<MeResponse, Error, LoginPayload>({
    mutationFn: async (data) => {
      // Determine which login type based on which key is present (discriminated union)
      if ("username" in data) {
        return loginWithUsername(data.username, data.password);
      } else if ("dni" in data) {
        return loginWithDni(data.dni, data.password);
      } else if ("email" in data) {
        return loginWithEmail(data.email, data.password);
      } else {
        throw new Error("Identificador no proporcionado");
      }
    },
  });
}

async function loginWithUsername(
  username: string,
  password: string,
): Promise<MeResponse> {
  const loginResponse = await api.post<ApiResponse<LoginResponse>>(
    "/auth/login/username",
    { username, password },
  );

  if (!loginResponse.data?.success || !loginResponse.data?.data) {
    throw new Error(loginResponse.data?.error?.message ?? "Login failed");
  }

  return persistAuthAndReturnUser(loginResponse.data.data);
}

async function loginWithDni(
  dni: string,
  password: string,
): Promise<MeResponse> {
  const loginResponse = await api.post<ApiResponse<LoginResponse>>(
    "/auth/login/dni",
    { dni, password },
  );

  if (!loginResponse.data?.success || !loginResponse.data?.data) {
    throw new Error(loginResponse.data?.error?.message ?? "Login failed");
  }

  return persistAuthAndReturnUser(loginResponse.data.data);
}

async function loginWithEmail(
  email: string,
  password: string,
): Promise<MeResponse> {
  const loginResponse = await api.post<ApiResponse<LoginResponse>>(
    "/auth/login/email",
    { email, password },
  );

  if (!loginResponse.data?.success || !loginResponse.data?.data) {
    throw new Error(loginResponse.data?.error?.message ?? "Login failed");
  }

  return persistAuthAndReturnUser(loginResponse.data.data);
}

function persistAuthAndReturnUser(loginData: LoginResponse): MeResponse {
  const { access_token, refresh_token, expires_at, user } = loginData;

  // Set cookies client-side using cookies-next
  const cookieOptions = {
    path: "/",
    secure: process.env.NEXT_PUBLIC_COOKIE_SECURE === "true",
    sameSite: "lax" as const,
    maxAge: 7 * 24 * 60 * 60, // 7 days in seconds
    httpOnly: false, // client-side cookies — httpOnly no funciona desde cliente
  };

  setCookie(AUTH_COOKIES.ACCESS_TOKEN, access_token, cookieOptions);
  setCookie(AUTH_COOKIES.REFRESH_TOKEN, refresh_token, cookieOptions);
  setCookie(AUTH_COOKIES.EXPIRES_AT, expires_at, cookieOptions);
  setCookie(AUTH_COOKIES.USER_SESSION, JSON.stringify(user), cookieOptions);

  return user;
}

/**
 * Client-side logout: clear auth cookies and localStorage state.
 */
export function useLogout() {
  return useMutation<void, Error, void>({
    mutationFn: async () => {
      deleteCookie(AUTH_COOKIES.ACCESS_TOKEN);
      deleteCookie(AUTH_COOKIES.REFRESH_TOKEN);
      deleteCookie(AUTH_COOKIES.EXPIRES_AT);
      deleteCookie(AUTH_COOKIES.USER_SESSION);
    },
  });
}
