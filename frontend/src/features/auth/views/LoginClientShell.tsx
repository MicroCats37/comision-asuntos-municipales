"use client";

import { Eye, EyeOff, KeyRound, Loader2, Mail, User } from "lucide-react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { GenericForm } from "@/components/genericForm/GenericForm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useLogin } from "@/features/auth/hooks/useLogin";
import {
  type LoginDniFormData,
  LoginDniFormSchema,
  type LoginEmailFormData,
  LoginEmailFormSchema,
  type LoginUsernameFormData,
  LoginUsernameFormSchema,
} from "@/features/auth/schemas";
import { useAuthStore } from "@/features/auth/store/auth.store";
import { cn } from "@/lib/utils";

// =============================================================================
// SUB-FORM: Username Login
// =============================================================================
function UsernameLoginForm({ isLoading }: { isLoading: boolean }) {
  const loginMutation = useLogin();
  const router = useRouter();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [showPassword, setShowPassword] = useState(false);

  return (
    <GenericForm<LoginUsernameFormData>
      schema={LoginUsernameFormSchema}
      submitButtonText="Ingresar"
      isLoading={isLoading || loginMutation.isPending}
      onSubmit={async (data) => {
        try {
          const auth = await loginMutation.mutateAsync(data);
          setAuth(auth);
          toast.success("Bienvenido al sistema CAM");
          router.push("/liquidaciones");
        } catch (error) {
          toast.error(
            error instanceof Error
              ? error.message
              : "Error al iniciar sesión. Verifica tus credenciales.",
          );
        }
      }}
    >
      {({ methods, isSubmitting, submissionMessage }) => (
        <div className="space-y-6">
          {/* Error message */}
          {submissionMessage && submissionMessage.type === "error" && (
            <div className="p-4 rounded-2xl bg-destructive/10 border border-destructive/20 text-destructive text-xs font-bold uppercase tracking-widest animate-in fade-in slide-in-from-top-2 text-center">
              {submissionMessage.message}
            </div>
          )}

          {/* Username field */}
          <div className="space-y-3">
            <Label
              htmlFor="username"
              className="text-[10px] font-black text-primary uppercase tracking-[0.2em] ml-1 block"
            >
              Usuario
            </Label>
            <div className="relative group">
              <User
                className="absolute left-5 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground group-focus-within:text-primary transition-colors duration-300"
                aria-hidden="true"
              />
              <Input
                id="username"
                type="text"
                placeholder="Ej: juan.perez"
                autoComplete="username"
                className={cn(
                  "h-14 pl-13 pr-5 rounded-[1.5rem] border-border bg-card text-base font-bold placeholder:text-muted-foreground/60",
                  "focus:ring-[6px] focus:ring-primary/10 focus:border-primary transition-all",
                )}
                {...methods.register("username")}
              />
            </div>
            {methods.formState.errors.username && (
              <p className="text-[11px] font-bold text-destructive uppercase tracking-tight px-1 animate-in fade-in slide-in-from-top-1">
                {methods.formState.errors.username.message as string}
              </p>
            )}
          </div>

          {/* Password field */}
          <div className="space-y-3">
            <Label
              htmlFor="password"
              className="text-[10px] font-black text-primary uppercase tracking-[0.2em] ml-1 block"
            >
              Contraseña
            </Label>
            <div className="relative group">
              <KeyRound
                className="absolute left-5 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground group-focus-within:text-primary transition-colors duration-300"
                aria-hidden="true"
              />
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••••••"
                autoComplete="current-password"
                className={cn(
                  "h-14 pl-13 pr-14 rounded-[1.5rem] border-border bg-card text-base font-bold placeholder:text-muted-foreground/60",
                  "focus:ring-[6px] focus:ring-primary/10 focus:border-primary transition-all",
                )}
                {...methods.register("password")}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors p-1"
                aria-label={
                  showPassword ? "Ocultar contraseña" : "Mostrar contraseña"
                }
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5" aria-hidden="true" />
                ) : (
                  <Eye className="h-5 w-5" aria-hidden="true" />
                )}
              </button>
            </div>
            {methods.formState.errors.password && (
              <p className="text-[11px] font-bold text-destructive uppercase tracking-tight px-1 animate-in fade-in slide-in-from-top-1">
                {methods.formState.errors.password.message as string}
              </p>
            )}
          </div>

          {/* Submit button */}
          <Button
            type="submit"
            disabled={isSubmitting}
            className={cn(
              "w-full h-14 rounded-[1.5rem] bg-primary hover:bg-primary/90 text-primary-foreground font-black text-sm uppercase tracking-widest",
              "shadow-xl shadow-primary/10 btn-press-effect",
              "flex items-center justify-center gap-3",
            )}
          >
            {isSubmitting ? (
              <>
                <Loader2
                  className="w-5 h-5 animate-spin text-accent"
                  aria-hidden="true"
                />
                <span>Verificando...</span>
              </>
            ) : (
              "Ingresar"
            )}
          </Button>
        </div>
      )}
    </GenericForm>
  );
}

// =============================================================================
// SUB-FORM: DNI Login
// =============================================================================
function DniLoginForm({ isLoading }: { isLoading: boolean }) {
  const loginMutation = useLogin();
  const router = useRouter();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [showPassword, setShowPassword] = useState(false);

  return (
    <GenericForm<LoginDniFormData>
      schema={LoginDniFormSchema}
      submitButtonText="Ingresar"
      isLoading={isLoading || loginMutation.isPending}
      onSubmit={async (data) => {
        try {
          const auth = await loginMutation.mutateAsync(data);
          setAuth(auth);
          toast.success("Bienvenido al sistema CAM");
          router.push("/liquidaciones");
        } catch (error) {
          toast.error(
            error instanceof Error
              ? error.message
              : "Error al iniciar sesión. Verifica tus credenciales.",
          );
        }
      }}
    >
      {({ methods, isSubmitting, submissionMessage }) => (
        <div className="space-y-6">
          {/* Error message */}
          {submissionMessage && submissionMessage.type === "error" && (
            <div className="p-4 rounded-2xl bg-destructive/10 border border-destructive/20 text-destructive text-xs font-bold uppercase tracking-widest animate-in fade-in slide-in-from-top-2 text-center">
              {submissionMessage.message}
            </div>
          )}

          {/* DNI field */}
          <div className="space-y-3">
            <Label
              htmlFor="dni"
              className="text-[10px] font-black text-primary uppercase tracking-[0.2em] ml-1 block"
            >
              Documento Nacional de Identidad
            </Label>
            <div className="relative group">
              <User
                className="absolute left-5 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground group-focus-within:text-primary transition-colors duration-300"
                aria-hidden="true"
              />
              <Input
                id="dni"
                type="text"
                inputMode="numeric"
                placeholder="Ej: 12345678"
                autoComplete="off"
                className={cn(
                  "h-14 pl-13 pr-5 rounded-[1.5rem] border-border bg-card text-base font-bold placeholder:text-muted-foreground/60",
                  "focus:ring-[6px] focus:ring-primary/10 focus:border-primary transition-all",
                )}
                {...methods.register("dni")}
              />
            </div>
            {methods.formState.errors.dni && (
              <p className="text-[11px] font-bold text-destructive uppercase tracking-tight px-1 animate-in fade-in slide-in-from-top-1">
                {methods.formState.errors.dni.message as string}
              </p>
            )}
          </div>

          {/* Password field */}
          <div className="space-y-3">
            <Label
              htmlFor="password"
              className="text-[10px] font-black text-primary uppercase tracking-[0.2em] ml-1 block"
            >
              Contraseña
            </Label>
            <div className="relative group">
              <KeyRound
                className="absolute left-5 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground group-focus-within:text-primary transition-colors duration-300"
                aria-hidden="true"
              />
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••••••"
                autoComplete="current-password"
                className={cn(
                  "h-14 pl-13 pr-14 rounded-[1.5rem] border-border bg-card text-base font-bold placeholder:text-muted-foreground/60",
                  "focus:ring-[6px] focus:ring-primary/10 focus:border-primary transition-all",
                )}
                {...methods.register("password")}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors p-1"
                aria-label={
                  showPassword ? "Ocultar contraseña" : "Mostrar contraseña"
                }
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5" aria-hidden="true" />
                ) : (
                  <Eye className="h-5 w-5" aria-hidden="true" />
                )}
              </button>
            </div>
            {methods.formState.errors.password && (
              <p className="text-[11px] font-bold text-destructive uppercase tracking-tight px-1 animate-in fade-in slide-in-from-top-1">
                {methods.formState.errors.password.message as string}
              </p>
            )}
          </div>

          {/* Submit button */}
          <Button
            type="submit"
            disabled={isSubmitting}
            className={cn(
              "w-full h-14 rounded-[1.5rem] bg-primary hover:bg-primary/90 text-primary-foreground font-black text-sm uppercase tracking-widest",
              "shadow-xl shadow-primary/10 btn-press-effect",
              "flex items-center justify-center gap-3",
            )}
          >
            {isSubmitting ? (
              <>
                <Loader2
                  className="w-5 h-5 animate-spin text-accent"
                  aria-hidden="true"
                />
                <span>Verificando...</span>
              </>
            ) : (
              "Ingresar"
            )}
          </Button>
        </div>
      )}
    </GenericForm>
  );
}

// =============================================================================
// SUB-FORM: Email Login
// =============================================================================
function EmailLoginForm({ isLoading }: { isLoading: boolean }) {
  const loginMutation = useLogin();
  const router = useRouter();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [showPassword, setShowPassword] = useState(false);

  return (
    <GenericForm<LoginEmailFormData>
      schema={LoginEmailFormSchema}
      submitButtonText="Ingresar"
      isLoading={isLoading || loginMutation.isPending}
      onSubmit={async (data) => {
        try {
          const auth = await loginMutation.mutateAsync(data);
          setAuth(auth);
          toast.success("Bienvenido al sistema CAM");
          router.push("/liquidaciones");
        } catch (error) {
          toast.error(
            error instanceof Error
              ? error.message
              : "Error al iniciar sesión. Verifica tus credenciales.",
          );
        }
      }}
    >
      {({ methods, isSubmitting, submissionMessage }) => (
        <div className="space-y-6">
          {/* Error message */}
          {submissionMessage && submissionMessage.type === "error" && (
            <div className="p-4 rounded-2xl bg-destructive/10 border border-destructive/20 text-destructive text-xs font-bold uppercase tracking-widest animate-in fade-in slide-in-from-top-2 text-center">
              {submissionMessage.message}
            </div>
          )}

          {/* Email field */}
          <div className="space-y-3">
            <Label
              htmlFor="email"
              className="text-[10px] font-black text-primary uppercase tracking-[0.2em] ml-1 block"
            >
              Correo Electrónico
            </Label>
            <div className="relative group">
              <Mail
                className="absolute left-5 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground group-focus-within:text-primary transition-colors duration-300"
                aria-hidden="true"
              />
              <Input
                id="email"
                type="email"
                inputMode="email"
                placeholder="Ej: juan.perez@email.com"
                autoComplete="email"
                className={cn(
                  "h-14 pl-13 pr-5 rounded-[1.5rem] border-border bg-card text-base font-bold placeholder:text-muted-foreground/60",
                  "focus:ring-[6px] focus:ring-primary/10 focus:border-primary transition-all",
                )}
                {...methods.register("email")}
              />
            </div>
            {methods.formState.errors.email && (
              <p className="text-[11px] font-bold text-destructive uppercase tracking-tight px-1 animate-in fade-in slide-in-from-top-1">
                {methods.formState.errors.email.message as string}
              </p>
            )}
          </div>

          {/* Password field */}
          <div className="space-y-3">
            <Label
              htmlFor="password"
              className="text-[10px] font-black text-primary uppercase tracking-[0.2em] ml-1 block"
            >
              Contraseña
            </Label>
            <div className="relative group">
              <KeyRound
                className="absolute left-5 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground group-focus-within:text-primary transition-colors duration-300"
                aria-hidden="true"
              />
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••••••"
                autoComplete="current-password"
                className={cn(
                  "h-14 pl-13 pr-14 rounded-[1.5rem] border-border bg-card text-base font-bold placeholder:text-muted-foreground/60",
                  "focus:ring-[6px] focus:ring-primary/10 focus:border-primary transition-all",
                )}
                {...methods.register("password")}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors p-1"
                aria-label={
                  showPassword ? "Ocultar contraseña" : "Mostrar contraseña"
                }
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5" aria-hidden="true" />
                ) : (
                  <Eye className="h-5 w-5" aria-hidden="true" />
                )}
              </button>
            </div>
            {methods.formState.errors.password && (
              <p className="text-[11px] font-bold text-destructive uppercase tracking-tight px-1 animate-in fade-in slide-in-from-top-1">
                {methods.formState.errors.password.message as string}
              </p>
            )}
          </div>

          {/* Submit button */}
          <Button
            type="submit"
            disabled={isSubmitting}
            className={cn(
              "w-full h-14 rounded-[1.5rem] bg-primary hover:bg-primary/90 text-primary-foreground font-black text-sm uppercase tracking-widest",
              "shadow-xl shadow-primary/10 btn-press-effect",
              "flex items-center justify-center gap-3",
            )}
          >
            {isSubmitting ? (
              <>
                <Loader2
                  className="w-5 h-5 animate-spin text-accent"
                  aria-hidden="true"
                />
                <span>Verificando...</span>
              </>
            ) : (
              "Ingresar"
            )}
          </Button>
        </div>
      )}
    </GenericForm>
  );
}

// =============================================================================
// AUTH CARD WRAPPER
// =============================================================================
interface AuthCardProps {
  children: React.ReactNode;
  className?: string;
}

function AuthCard({ children, className = "" }: AuthCardProps) {
  return (
    <div
      className={cn(
        "w-full bg-card/95 backdrop-blur-sm border border-white/20 rounded-[2rem]",
        "shadow-2xl shadow-black/20",
        "p-6 sm:p-8 md:p-10",
        "transition-all duration-500",
        className,
      )}
    >
      {children}
    </div>
  );
}

// =============================================================================
// CLIENT SHELL — CAM Corporate Login
// =============================================================================
export function LoginClientShell() {
  const [activeTab, setActiveTab] = useState<"username" | "dni" | "email">(
    "dni",
  );

  return (
    <div className="min-h-screen w-full flex items-center justify-center login-animated-bg relative overflow-hidden p-4 sm:p-6">
      {/* Subtle overlay for depth — keeps text legible and adds sophistication */}
      <div className="absolute inset-0 bg-black/10 pointer-events-none" />

      <div className="w-full max-w-md relative z-10 space-y-6">
        {/* Form container — wrapped in AuthCard */}
        <div className="animate-in fade-in zoom-in-95 duration-500">
          <AuthCard>
            {/* CAM Branding Header — inside card */}
            <div className="text-center mb-10 animate-in fade-in slide-in-from-bottom-4 duration-700">
              <div className="inline-flex items-center justify-center h-28 w-28 rounded-full bg-primary/10 mb-4 border-4 border-primary/80 p-1">
                <Image
                  src="/images/logo.png"
                  alt="Logo CIP"
                  width={120}
                  height={120}
                  className="h-26 w-26 object-contain"
                  priority
                />
              </div>
              <h1 className="text-2xl sm:text-3xl font-black text-primary tracking-tighter leading-none mb-1">
                Sistema CAM
              </h1>
              <p className="text-muted-foreground font-medium text-xs sm:text-sm leading-relaxed">
                Comisión de Asuntos Municipales
              </p>
            </div>

            {/* Mode selector tabs — modern pill style */}
            <Tabs
              value={activeTab}
              onValueChange={(v) =>
                setActiveTab(v as "username" | "dni" | "email")
              }
            >
              <TabsList className="w-full bg-muted p-8 rounded-full border border-border/40 gap-2">
                <TabsTrigger
                  value="username"
                  className={cn(
                    "flex-1 rounded-[1.8rem] py-4 text-xs font-black uppercase tracking-wide transition-all duration-300 ease-out flex items-center justify-center gap-1.5",
                    "data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-md data-[state=active]:scale-[1.02]",
                    "data-[state=inactive]:text-muted-foreground data-[state=inactive]:hover:text-foreground data-[state=inactive]:hover:bg-muted-foreground/10",
                  )}
                >
                  <User className="w-4 h-4" aria-hidden="true" />
                  Usuario
                </TabsTrigger>
                <TabsTrigger
                  value="dni"
                  className={cn(
                    "flex-1 rounded-[1.8rem] py-4 text-xs font-black uppercase tracking-wide transition-all duration-300 ease-out flex items-center justify-center gap-1.5",
                    "data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-md data-[state=active]:scale-[1.02]",
                    "data-[state=inactive]:text-muted-foreground data-[state=inactive]:hover:text-foreground data-[state=inactive]:hover:bg-muted-foreground/10",
                  )}
                >
                  <User className="w-4 h-4" aria-hidden="true" />
                  DNI
                </TabsTrigger>
                <TabsTrigger
                  value="email"
                  className={cn(
                    "flex-1 rounded-[1.8rem] py-4 text-xs font-black uppercase tracking-wide transition-all duration-300 ease-out flex items-center justify-center gap-1.5",
                    "data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-md data-[state=active]:scale-[1.02]",
                    "data-[state=inactive]:text-muted-foreground data-[state=inactive]:hover:text-foreground data-[state=inactive]:hover:bg-muted-foreground/10",
                  )}
                >
                  <Mail className="w-4 h-4" aria-hidden="true" />
                  Email
                </TabsTrigger>
              </TabsList>
            </Tabs>

            {/* Form area — conditionally render based on active tab with animation */}
            <div
              key={activeTab}
              className="mt-8 animate-in fade-in slide-in-from-bottom-4 duration-500"
            >
              {activeTab === "username" ? (
                <UsernameLoginForm isLoading={false} />
              ) : activeTab === "dni" ? (
                <DniLoginForm isLoading={false} />
              ) : (
                <EmailLoginForm isLoading={false} />
              )}
            </div>
          </AuthCard>
        </div>

        {/* Footer */}
        <div className="text-center opacity-40 hover:opacity-100 transition-all duration-700">
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">
            CAM — Comisión de Asuntos Municipales
          </p>
        </div>
      </div>
    </div>
  );
}
