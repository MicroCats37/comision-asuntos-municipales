"use client";

import {
  AlertTriangle,
  BadgeCheck,
  CloudOff,
  Loader2,
  Search,
  UserSearch,
  X,
} from "lucide-react";
/**
 * ConsultarIngenieroButton — Botón + Modal reutilizable para consultar un
 * ingeniero habilitado por CIP.
 *
 * Endpoint: GET /ingenieros/habilitados/{cip}
 * Muestra CIP, nombres, apellidos, habilitado y capítulo.
 *
 * Sigue el contrato estándar del frontend: el servicio devuelve data|null y
 * propaga el error; el error-handler central (getErrorMessage) normaliza
 * errores de red (URL caída) y HTTP.
 *
 * Se usa en el header de las vistas de liquidaciones, junto al botón de
 * "Nueva Liquidación".
 */
import { useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getErrorMessage } from "@/errors";
import { useConsultarIngeniero } from "../../hooks/useConsultarIngeniero";

interface ConsultarIngenieroButtonProps {
  /** Estilo del botón que abre el modal (default relleno, outline opcional). */
  variant?: "default" | "outline";
  label?: string;
}

export function ConsultarIngenieroButton({
  variant = "outline",
  label = "Consultar Ingeniero",
}: ConsultarIngenieroButtonProps) {
  const [open, setOpen] = useState(false);
  const [cip, setCip] = useState("");
  const [searched, setSearched] = useState(false);

  const consulta = useConsultarIngeniero();
  const isConsulting = consulta.isPending;
  const isUnavailable = consulta.isError && !consulta.error?.response;

  const isCipValid = cip.trim().length === 6;

  const handleConsultar = () => {
    if (!isCipValid) return;
    setSearched(true);
    consulta.mutate(cip.trim());
  };

  const handleReset = () => {
    setCip("");
    setSearched(false);
    consulta.reset();
  };

  const errorMessage = consulta.isError ? getErrorMessage(consulta.error) : "";

  return (
    <>
      <Button
        type="button"
        variant={variant}
        className="gap-2 h-11 rounded-xl font-semibold shrink-0"
        onClick={() => setOpen(true)}
      >
        <UserSearch className="h-4 w-4" />
        {label}
      </Button>

      <GenericModal open={open} onOpenChange={setOpen} preventClose={false}>
        <GenericModal.Content size="md">
          <GenericModal.Header
            title=""
            className="bg-primary/[0.03] border-b border-border px-6 py-5"
          >
            <div className="flex items-center gap-3 w-full">
              <div className="p-2 bg-primary/10 rounded-xl border border-primary/20 shadow-sm shrink-0">
                <UserSearch className="h-5 w-5 text-primary" />
              </div>
              <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                  CIP
                </span>
                <h2 className="text-2xl font-black tracking-tight text-foreground leading-tight">
                  Consultar Ingeniero
                </h2>
                <p className="hidden sm:block text-sm text-muted-foreground leading-relaxed">
                  Consulta los datos de un ingeniero habilitado por su CIP
                </p>
              </div>
              <div className="w-9 shrink-0" aria-hidden="true" />
            </div>
          </GenericModal.Header>

          <GenericModal.Body className="space-y-6">
            {/* ── Búsqueda por CIP ── */}
            <div className="p-4 rounded-xl border border-border/60 bg-muted/10 space-y-3">
              <div className="space-y-2">
                <Label htmlFor="buscar-cip" className="text-sm font-semibold">
                  N° CIP
                </Label>
                <div className="flex gap-2">
                  <Input
                    id="buscar-cip"
                    placeholder="Ej. 123456"
                    inputMode="numeric"
                    value={cip}
                    onChange={(e) => {
                      setCip(e.target.value.replace(/\D/g, "").slice(0, 6));
                      setSearched(false);
                    }}
                    onKeyDown={(e) =>
                      e.key === "Enter" && isCipValid && handleConsultar()
                    }
                    className="w-full h-10 font-mono"
                  />
                  <Button
                    type="button"
                    variant="default"
                    onClick={handleConsultar}
                    disabled={!isCipValid || isConsulting}
                    className="h-10 shrink-0 gap-1.5 px-5"
                  >
                    {isConsulting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Search className="h-4 w-4" />
                    )}
                    Consultar
                  </Button>
                </div>
                {cip && !isCipValid && (
                  <p className="text-xs text-destructive">
                    El CIP debe tener 6 dígitos
                  </p>
                )}
              </div>
            </div>

            {/* ── Resultado ── */}
            <div className="border-t border-border/40 pt-5">
              {!searched ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/40 mb-3">
                    <Search className="h-5 w-5 text-muted-foreground/70" />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Ingresa un CIP y presiona Consultar
                  </p>
                  <p className="text-xs text-muted-foreground/60 mt-1">
                    CIP: 6 dígitos
                  </p>
                </div>
              ) : isConsulting ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              ) : isUnavailable ? (
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 mb-3">
                    <CloudOff className="h-6 w-6 text-destructive" />
                  </div>
                  <p className="text-destructive font-semibold">
                    Servicio no disponible
                  </p>
                  <p className="text-xs text-muted-foreground mt-1 max-w-[260px]">
                    {errorMessage ||
                      "No se pudo conectar con el servicio de consulta de ingenieros. Intenta más tarde."}
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-4 gap-1.5"
                    onClick={handleConsultar}
                    disabled={!isCipValid || isConsulting}
                  >
                    {isConsulting && (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    )}
                    Reintentar
                  </Button>
                </div>
              ) : consulta.isError ? (
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 mb-3">
                    <AlertTriangle className="h-6 w-6 text-destructive" />
                  </div>
                  <p className="text-destructive font-medium">
                    Error al consultar
                  </p>
                  <p className="text-xs text-muted-foreground mt-1 max-w-[260px]">
                    {errorMessage}
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-4 gap-1.5"
                    onClick={handleConsultar}
                    disabled={!isCipValid || isConsulting}
                  >
                    {isConsulting && (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    )}
                    Reintentar
                  </Button>
                </div>
              ) : !consulta.data ? (
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <p className="text-muted-foreground text-sm">
                    No se encontraron datos para el CIP {cip}
                  </p>
                </div>
              ) : (
                <div className="rounded-xl border bg-card p-5">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
                        <UserSearch className="h-5 w-5 text-primary" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-base font-bold text-foreground truncate">
                          {consulta.data.nombres} {consulta.data.apellidos}
                        </p>
                        <p className="text-xs text-muted-foreground font-mono">
                          CIP {consulta.data.cip}
                        </p>
                      </div>
                    </div>
                    <span
                      className={
                        consulta.data.habilitado
                          ? "inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 text-xs font-bold text-emerald-600"
                          : "inline-flex items-center gap-1 rounded-full bg-destructive/10 border border-destructive/20 px-2.5 py-1 text-xs font-bold text-destructive"
                      }
                    >
                      <BadgeCheck className="h-3.5 w-3.5" />
                      {consulta.data.habilitado
                        ? "Habilitado"
                        : "No habilitado"}
                    </span>
                  </div>
                  {consulta.data.capitulo && (
                    <div className="mt-4 pt-4 border-t border-border/40">
                      <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        Capítulo
                      </p>
                      <p className="text-sm text-foreground mt-1">
                        {consulta.data.capitulo}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </GenericModal.Body>

          <GenericModal.Footer className="px-6 py-4 bg-muted/30 border-t border-border">
            <div className="flex items-center justify-end gap-2">
              {searched && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleReset}
                  className="h-10 gap-1 text-xs text-muted-foreground"
                >
                  <X className="h-3 w-3" />
                  Limpiar
                </Button>
              )}
              <Button
                type="button"
                variant="outline"
                onClick={() => setOpen(false)}
                className="h-10 rounded-xl font-semibold"
              >
                Cerrar
              </Button>
            </div>
          </GenericModal.Footer>

          <GenericModal.CloseX />
        </GenericModal.Content>
      </GenericModal>
    </>
  );
}
