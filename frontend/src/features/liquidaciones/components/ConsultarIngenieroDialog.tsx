/**
 * Standalone dialog to consult engineer habilitado status by CIP.
 * Does NOT create proyectistas — read-only consult only.
 *
 * Key behavior (fixes ProyectistaFormModal bug):
 * - cipToQuery is reset when input is cleared or dialog closes
 * - Query is explicitly triggered by user action, not auto-enabled on digit count
 */

import {
  CheckCircle2,
  Loader2,
  Search,
  UserCheck,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useIngenieroHabilitado } from "../hooks/useIngenieroHabilitado";
import { ApiQueryError } from "@/hooks/callsApi/useApiQuery";
import { sanitizeCipInput, isValidCip } from "../utils/cip-utils";

interface ConsultarIngenieroDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ConsultarIngenieroDialog({
  open,
  onOpenChange,
}: ConsultarIngenieroDialogProps) {
  // Raw input as user types — never fed directly to the hook
  const [inputValue, setInputValue] = useState("");
  // CIP to actually query — only set when user clicks "Consultar"
  const [cipToQuery, setCipToQuery] = useState<string | null>(null);

  // Sanitize: digits only, max 6
  const digitsOnly = sanitizeCipInput(inputValue);
  const isValidLength = isValidCip(digitsOnly);

  // Query ingeniero habilitado when cipToQuery is set
  const {
    data: ingeniero,
    isFetching,
    isFetched,
    error,
  } = useIngenieroHabilitado(cipToQuery);

  const queryDone = isFetched && !isFetching;
  const ingenieroFound = queryDone && !error && ingeniero != null;
  const isHabilitado = ingenieroFound && ingeniero.habilitado;

  // Distinguish 404 (not found) from service errors (503/timeout/network)
  const is404Error = error instanceof ApiQueryError && error.status === 404;
  const isServiceError = error != null && !is404Error;
  const ingenieroNotFound = queryDone && (!ingeniero || error);

  // After terminal service error, clear cipToQuery so query doesn't stay enabled
  useEffect(() => {
    if (isServiceError && cipToQuery != null) {
      setCipToQuery(null);
    }
  }, [isServiceError, cipToQuery]);

  // When input is cleared externally, reset cipToQuery so no stale result shows
  useEffect(() => {
    if (inputValue === "" && cipToQuery !== null) {
      setCipToQuery(null);
    }
  }, [inputValue, cipToQuery]);

  // When dialog closes, reset all local state
  const handleClose = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) {
        setInputValue("");
        setCipToQuery(null);
      }
      onOpenChange(nextOpen);
    },
    [onOpenChange],
  );

  const handleConsultar = useCallback(() => {
    if (!isValidLength || isFetching) return;
    setCipToQuery(digitsOnly);
  }, [isValidLength, isFetching, digitsOnly]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Digits only, max 6
    const sanitized = e.target.value.replace(/\D/g, "").slice(0, 6);
    setInputValue(sanitized);
  };

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && isValidLength && !isFetching) {
      e.preventDefault();
      handleConsultar();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserCheck className="h-5 w-5 text-primary" />
            Consultar ingeniero habilitado
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* CIP Input */}
          <div className="space-y-2">
            <Label htmlFor="cip-consult">Código CIP</Label>
            <div className="flex gap-2">
              <Input
                id="cip-consult"
                type="text"
                inputMode="numeric"
                placeholder="Ingrese hasta 6 dígitos"
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={handleInputKeyDown}
                className="flex-1 h-11"
                autoComplete="off"
              />
              <Button
                variant="default"
                size="default"
                className="h-11 gap-2"
                onClick={handleConsultar}
                disabled={!isValidLength || isFetching}
              >
                {isFetching ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                Consultar
              </Button>
            </div>
          </div>

          {/* Idle — no query yet */}
          {!cipToQuery && !isFetching && (
            <p className="text-sm text-muted-foreground">
              Ingrese el CIP y presione Consultar para verificar el estado de
              habilitación.
            </p>
          )}

          {/* Loading */}
          {isFetching && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Buscando CIP...
            </div>
          )}

          {/* Error / Not Found */}
          {ingenieroNotFound && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20">
              <XCircle className="h-4 w-4 text-destructive shrink-0" />
              <span className="text-sm text-destructive">
                {isServiceError
                  ? "No se pudo consultar el servicio CIP. Intente nuevamente."
                  : "No se encontró ingeniero con este CIP"}
              </span>
            </div>
          )}

          {/* Engineer Found — show info */}
          {ingenieroFound && (
            <div className="space-y-3">
              {/* Habilitado badge */}
              {isHabilitado ? (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                  <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0" />
                  <span className="text-sm font-medium text-green-700">
                    Habilitado
                  </span>
                </div>
              ) : (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                  <XCircle className="h-4 w-4 text-destructive shrink-0" />
                  <span className="text-sm text-destructive font-medium">
                    NO habilitado
                  </span>
                </div>
              )}

              {/* Engineer Details */}
              <div className="grid grid-cols-2 gap-4 p-3 rounded-lg bg-muted/50">
                <div>
                  <p className="text-xs text-muted-foreground">Nombres</p>
                  <p className="text-sm font-medium">{ingeniero.nombres}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Apellidos</p>
                  <p className="text-sm font-medium">{ingeniero.apellidos}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">CIP</p>
                  <p className="text-sm font-medium">{ingeniero.cip}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Capítulo</p>
                  <p className="text-sm font-medium">
                    {ingeniero.capitulo || "N/A"}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
