"use client";

import {
  Check,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  type LucideIcon,
  ShieldCheck,
  User,
} from "lucide-react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { GenericForm } from "@/components/genericForm/GenericForm";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLogin } from "@/features/auth/hooks/useLogin";
import {
  type LoginUsernameFormData,
  LoginUsernameFormSchema,
} from "@/features/auth/schemas";
import { useAuthStore } from "@/features/auth/store/auth.store";
import { cn } from "@/lib/utils";

/** Modules surfaced under the card as institutional highlights. */
const BRAND_HIGHLIGHTS = ["Liquidaciones", "Operativa", "Finanzas"];

// =============================================================================
// SHARED PIECES
// =============================================================================

/** Shared class for every credential input. */
const INPUT_BASE =
  "h-13 rounded-[1.25rem] border-border bg-card text-sm font-bold placeholder:text-muted-foreground/60 shadow-[inset_0_1px_2px_oklch(0_0_0_/_0.04)] transition-all duration-200 hover:border-primary/40 focus:border-primary focus:bg-card focus:ring-[5px] focus:ring-primary/20";

/** Label + icon + input slot + inline error. */
function LoginField({
  id,
  label,
  icon: Icon,
  error,
  trailing,
  children,
}: {
  id: string;
  label: string;
  icon: LucideIcon;
  error?: string;
  trailing?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <Label
        htmlFor={id}
        className="ml-1 flex items-center gap-2 text-[10px] font-black tracking-[0.2em] text-primary uppercase"
      >
        <span className="h-1 w-1 rounded-full bg-accent" aria-hidden="true" />
        {label}
      </Label>
      <div className="group relative">
        <Icon
          className="absolute top-1/2 left-4 h-4.5 w-4.5 -translate-y-1/2 text-muted-foreground transition-colors duration-300 group-focus-within:text-primary"
          aria-hidden="true"
        />
        {children}
        {trailing}
      </div>
      {error && (
        <p className="animate-in fade-in slide-in-from-top-1 px-1 text-[11px] font-bold tracking-tight text-destructive uppercase">
          {error}
        </p>
      )}
    </div>
  );
}

/** Eye toggle for the password input. */
function PasswordToggle({
  visible,
  onToggle,
}: {
  visible: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="absolute top-1/2 right-4 -translate-y-1/2 cursor-pointer rounded-full p-1 text-muted-foreground transition-colors duration-200 hover:bg-primary/5 hover:text-primary"
      aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
    >
      {visible ? (
        <EyeOff className="h-4.5 w-4.5" aria-hidden="true" />
      ) : (
        <Eye className="h-4.5 w-4.5" aria-hidden="true" />
      )}
    </button>
  );
}

/** Server-side error banner. */
function FormError({ message }: { message?: string | null }) {
  if (!message) return null;

  return (
    <div className="animate-in fade-in slide-in-from-top-2 rounded-xl border border-destructive/20 bg-destructive/10 p-3 text-center text-xs font-bold tracking-widest text-destructive uppercase">
      {message}
    </div>
  );
}

/** Wine gradient submit button. */
function SubmitButton({ isSubmitting }: { isSubmitting: boolean }) {
  return (
    <Button
      type="submit"
      disabled={isSubmitting}
      className={cn(
        "flex h-13 w-full cursor-pointer items-center justify-center gap-3 rounded-[1.25rem] font-black text-sm tracking-widest text-primary-foreground uppercase",
        "btn-wine-gradient-hover",
      )}
    >
      {isSubmitting ? (
        <>
          <Loader2
            className="h-5 w-5 animate-spin text-accent"
            aria-hidden="true"
          />
          <span>Verificando...</span>
        </>
      ) : (
        "Ingresar"
      )}
    </Button>
  );
}

// =============================================================================
// LOGIN FORM — username + password
// =============================================================================

function UsernameLoginForm({
  showPassword,
  onTogglePassword,
}: {
  showPassword: boolean;
  onTogglePassword: () => void;
}) {
  const loginMutation = useLogin();
  const router = useRouter();
  const setAuth = useAuthStore((state) => state.setAuth);

  return (
    <GenericForm<LoginUsernameFormData>
      schema={LoginUsernameFormSchema}
      submitButtonText="Ingresar"
      isLoading={loginMutation.isPending}
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
          throw error;
        }
      }}
    >
      {({ methods, isSubmitting, submissionMessage }) => (
        <div className="space-y-4">
          <FormError
            message={
              submissionMessage?.type === "error"
                ? submissionMessage.message
                : null
            }
          />

          <LoginField
            id="username"
            label="Usuario"
            icon={User}
            error={
              methods.formState.errors.username?.message as string | undefined
            }
          >
            <Input
              id="username"
              type="text"
              placeholder="Ej: juan.perez"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              className={cn(INPUT_BASE, "pr-4 pl-11")}
              {...methods.register("username")}
            />
          </LoginField>

          <LoginField
            id="password"
            label="Contraseña"
            icon={KeyRound}
            error={
              methods.formState.errors.password?.message as string | undefined
            }
            trailing={
              <PasswordToggle
                visible={showPassword}
                onToggle={onTogglePassword}
              />
            }
          >
            <Input
              id="password"
              type={showPassword ? "text" : "password"}
              placeholder="••••••••••••"
              autoComplete="current-password"
              className={cn(INPUT_BASE, "pr-11 pl-11")}
              {...methods.register("password")}
            />
          </LoginField>

          <SubmitButton isSubmitting={isSubmitting} />
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
        "relative w-full overflow-hidden rounded-[1.75rem] border border-primary/[0.08] bg-gradient-to-b from-card to-card/95 p-6 backdrop-blur-sm sm:p-8",
        "shadow-[0_8px_32px_-4px_oklch(0.25_0.16_22_/_0.12),0_2px_8px_-2px_oklch(0.25_0.16_22_/_0.08)]",
        "ring-1 ring-inset ring-primary/[0.06]",
        "transition-all duration-300 ease-out",
        "hover:scale-[1.01] hover:shadow-[0_16px_48px_-8px_oklch(0.3_0.16_22_/_0.18),0_4px_12px_-4px_oklch(0.25_0.16_22_/_0.1)]",
        className,
      )}
    >
      {/* Wine → gold hairline accent */}
      <div
        className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-primary via-accent to-primary"
        aria-hidden="true"
      />
      {children}
    </div>
  );
}

// =============================================================================
// CLIENT SHELL — CAM Corporate Login
// Full animated wine background + centered card. Everything fits the viewport
// height — the page never scrolls.
// =============================================================================

export function LoginClientShell() {
  const [showPassword, setShowPassword] = useState(false);

  const onTogglePassword = () => setShowPassword((previous) => !previous);

  return (
    <div className="login-animated-bg relative flex min-h-dvh w-full items-center justify-center overflow-hidden p-4 sm:p-6">
      {/* Subtle overlay for depth — keeps the card legible over the gradient */}
      <div className="pointer-events-none absolute inset-0 bg-black/10" />

      <div className="relative z-10 flex w-full max-w-md flex-col items-center">
        {/* Institutional signature — stated once, at the top */}
        <div className="mb-4 text-center animate-in fade-in slide-in-from-top-4 duration-700">
          <p className="text-xs font-black tracking-[0.22em] text-white/85 uppercase">
            Colegio de Ingenieros del Perú
          </p>
          <p className="text-[9px] font-semibold tracking-[0.22em] text-white/55 uppercase">
            Consejo Nacional
          </p>
        </div>

        {/* Login card — centered */}
        <div className="w-full animate-in fade-in zoom-in-95 duration-500">
          <AuthCard>
            {/* Brand lockup — the CIP logo lives inside the card */}
            <div className="flex flex-col items-center text-center">
              <div className="mb-3 flex h-20 w-20 items-center justify-center rounded-full border border-accent/30 bg-accent/10 p-1.5 shadow-md shadow-accent/15 ring-1 ring-accent/20">
                <Image
                  src="/images/logo.png"
                  alt="CIP"
                  width={72}
                  height={72}
                  className="h-16 w-16 object-contain"
                  priority
                />
              </div>
              <h1 className="text-lg font-black tracking-tight text-foreground">
                Comisión de Asuntos Municipales
              </h1>
              <p className="mt-0.5 text-[9px] font-semibold tracking-[0.18em] text-muted-foreground uppercase">
                Sistema CAM
              </p>
            </div>

            {/* Form header */}
            <div className="mt-5 mb-5">
              <div
                className="mb-4 h-px bg-gradient-to-r from-transparent via-primary/25 to-transparent"
                aria-hidden="true"
              />
              <div className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-primary/15 bg-primary/8 px-2.5 py-1 text-[9px] font-black tracking-[0.2em] text-primary uppercase">
                <ShieldCheck className="h-3 w-3" aria-hidden="true" />
                Acceso institucional
              </div>
              <h2 className="text-xl font-black tracking-tight text-foreground">
                Iniciar Sesión
              </h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Ingresa tus credenciales para acceder al sistema CAM
              </p>
            </div>

            <UsernameLoginForm
              showPassword={showPassword}
              onTogglePassword={onTogglePassword}
            />
          </AuthCard>
        </div>

        {/* Module highlights */}
        <div className="mt-4 flex flex-wrap justify-center gap-2 animate-in fade-in delay-300 duration-700">
          {BRAND_HIGHLIGHTS.map((highlight) => (
            <div
              key={highlight}
              className="flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-[10px] font-semibold text-white/80 backdrop-blur-sm"
            >
              <Check
                className="h-2.5 w-2.5 shrink-0 text-accent"
                strokeWidth={3}
                aria-hidden="true"
              />
              {highlight}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
