"use client";

import { useMutation } from "@tanstack/react-query";
import { setCookie } from "cookies-next";
import { getErrorMessage } from "@/errors";
import { api } from "@/lib/api";
import {
  AUTH_COOKIES,
  accessTokenCookieOptions,
  expiresAtCookieOptions,
  refreshTokenCookieOptions,
  userSessionCookieOptions,
} from "@/lib/auth";
import { clearAuthSessionAndRedirect } from "@/lib/auth/session-client";
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

/**
 * Fallback used when the backend does not describe why the login failed.
 */
const LOGIN_ERROR_FALLBACK = "Credenciales inválidas";

/**
 * Posts the credentials and normalizes any failure into a human-readable
 * message (the raw Axios text like "Request failed with status code 401" must
 * never reach the UI).
 */
async function requestLogin(
  url: string,
  payload: Record<string, unknown>,
): Promise<ApiResponse<LoginResponse>> {
  try {
    const response = await api.post<ApiResponse<LoginResponse>>(url, payload);
    return response.data;
  } catch (error) {
    throw new Error(getErrorMessage(error) || LOGIN_ERROR_FALLBACK);
  }
}

async function loginWithUsername(
  username: string,
  password: string,
): Promise<MeResponse> {
  const loginResponse = await requestLogin("/auth/login/username", {
    username,
    password,
  });

  if (!loginResponse?.success || !loginResponse?.data) {
    throw new Error(loginResponse?.error?.message ?? LOGIN_ERROR_FALLBACK);
  }

  return persistAuthAndReturnUser(loginResponse.data);
}

async function loginWithDni(
  dni: string,
  password: string,
): Promise<MeResponse> {
  const loginResponse = await requestLogin("/auth/login/dni", {
    dni,
    password,
  });

  if (!loginResponse?.success || !loginResponse?.data) {
    throw new Error(loginResponse?.error?.message ?? LOGIN_ERROR_FALLBACK);
  }

  return persistAuthAndReturnUser(loginResponse.data);
}

async function loginWithEmail(
  email: string,
  password: string,
): Promise<MeResponse> {
  const loginResponse = await requestLogin("/auth/login/email", {
    email,
    password,
  });

  if (!loginResponse?.success || !loginResponse?.data) {
    throw new Error(loginResponse?.error?.message ?? LOGIN_ERROR_FALLBACK);
  }

  return persistAuthAndReturnUser(loginResponse.data);
}

function persistAuthAndReturnUser(loginData: LoginResponse): MeResponse {
  const { access_token, refresh_token, expires_at, user } = loginData;

  setCookie(AUTH_COOKIES.ACCESS_TOKEN, access_token, accessTokenCookieOptions);
  setCookie(
    AUTH_COOKIES.REFRESH_TOKEN,
    refresh_token,
    refreshTokenCookieOptions,
  );
  setCookie(AUTH_COOKIES.EXPIRES_AT, expires_at, expiresAtCookieOptions);
  setCookie(
    AUTH_COOKIES.USER_SESSION,
    JSON.stringify(user),
    userSessionCookieOptions,
  );

  return user;
}

/**
 * Client-side logout: clear auth cookies and localStorage state.
 */
export function useLogout() {
  return useMutation<void, Error, void>({
    mutationFn: async () => {
      await clearAuthSessionAndRedirect();
    },
  });
}
