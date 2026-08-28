"use client";

import { Loader2, Search } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import type { Control, FieldErrors } from "react-hook-form";
import { useController } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { notify } from "@/errors";
import {
  type DocumentoConsultaData,
  useDocumentoLookup,
} from "@/features/entidades/hooks/useConsultaExterna";

const TIPO_DOCUMENTO_OPTIONS = [
  { value: "RUC", label: "RUC" },
  { value: "DNI", label: "DNI" },
] as const;

interface EntidadLookupFieldProps {
  control: Control<any>;
  errors: FieldErrors<any>;
  onFieldChange?: (field: string, value: string) => void;
  razonSocialSideSlot?: ReactNode;
  /** Configurable field names so multiple liquidation modules can share this component. */
  fieldNames?: {
    tipoDocumento: string;
    numeroDocumento: string;
    razonSocial: string;
    nombrePropietario?: string;
  };
}

interface LookupState {
  tipo_documento: "RUC" | "DNI";
  numero_documento: string;
}

/**
 * Smart Entity Field — unified lookup for SUNAT/RENIEC.
 *
 * Single clean flow (no duplicated inputs):
 *   1. Select DNI or RUC via RadioGroup
 *   2. Type document number
 *   3. Click "Buscar" → queries SUNAT or RENIEC
 *   4. Auto-fills Razón Social / Nombre Completo
 *
 * RHF fields managed: entidad_tipo_documento, entidad_numero_documento, entidad_razon_social.
 * Lookup state (tipo_documento + numero_documento) is local — not tied to RHF until search succeeds.
 */
export function EntidadLookupField({
  control,
  errors,
  onFieldChange,
  razonSocialSideSlot,
  fieldNames: fieldNamesConfig,
}: EntidadLookupFieldProps) {
  // Default field names — Edificaciones uses these exact names
  const fn = fieldNamesConfig ?? {
    tipoDocumento: "entidad_tipo_documento",
    numeroDocumento: "entidad_numero_documento",
    razonSocial: "entidad_razon_social",
    nombrePropietario: "nombre_propietario",
  };
  // ── Local search UI state (independent from RHF until lookup completes) ────
  const [lookupState, setLookupState] = useState<LookupState>({
    tipo_documento: "DNI",
    numero_documento: "",
  });

  // ── Consulta externa de documento (DNI o RUC) ─────────────────────────────
  const documentoLookup = useDocumentoLookup();
  const isConsulting = documentoLookup.isPending;

  // ── RHF controllers (useController for each form field) ──────────────────
  const tipoDocCtrl = useController({
    name: fn.tipoDocumento,
    control,
    defaultValue: "DNI",
    rules: { required: "Tipo de documento es requerido" },
  });
  const numDocCtrl = useController({
    name: fn.numeroDocumento,
    control,
    defaultValue: "",
    rules: { required: "Número de documento es requerido" },
  });
  const razonSocialCtrl = useController({
    name: fn.razonSocial,
    control,
    defaultValue: "",
    rules: { required: "Razón social o nombre completo es requerido" },
  });
  // Optional: sync nombre_propietario with razon_social when lookup succeeds
  const nombrePropietarioCtrl = fn.nombrePropietario
    ? useController({ name: fn.nombrePropietario, control, defaultValue: "" })
    : null;

  // ── Sync flag: prevents circular RHF ↔ lookupState updates ───────────────
  // When true, the sync effect skips updating lookupState to avoid loops
  const isInternalUpdate = useRef(false);

  // ── Sync RHF → lookupState for externally-restored values (e.g. Step1Proyecto) ──
  useEffect(() => {
    // Skip if this change originated from inside this component (avoid echo)
    if (isInternalUpdate.current) {
      isInternalUpdate.current = false;
      return;
    }

    // Sync tipo_documento when RHF value changes externally
    if (
      tipoDocCtrl.field.value !== undefined &&
      tipoDocCtrl.field.value !== lookupState.tipo_documento
    ) {
      isInternalUpdate.current = true;
      setLookupState((s) => ({
        ...s,
        tipo_documento: tipoDocCtrl.field.value,
        numero_documento: "", // Reset number when type changes externally
      }));
      return;
    }

    // Sync numero_documento when RHF value changes externally (type unchanged)
    if (
      numDocCtrl.field.value !== undefined &&
      numDocCtrl.field.value !== lookupState.numero_documento
    ) {
      isInternalUpdate.current = true;
      setLookupState((s) => ({
        ...s,
        numero_documento: numDocCtrl.field.value,
      }));
    }
  }, [
    tipoDocCtrl.field.value,
    numDocCtrl.field.value,
    lookupState.tipo_documento,
    lookupState.numero_documento,
  ]);

  const isLookupValid =
    lookupState.numero_documento.trim().length ===
    (lookupState.tipo_documento === "DNI" ? 8 : 11);

  // ── Update all 3 RHF fields atomically after successful lookup ────────────

  const setAllFields = (
    tipoDoc: "RUC" | "DNI",
    numDoc: string,
    razonSocial: string,
  ) => {
    tipoDocCtrl.field.onChange(tipoDoc);
    numDocCtrl.field.onChange(numDoc);
    razonSocialCtrl.field.onChange(razonSocial);
    // Auto-fill propietario with the same razon_social / nombre_completo
    if (nombrePropietarioCtrl) {
      nombrePropietarioCtrl.field.onChange(razonSocial);
    }

    onFieldChange?.(fn.tipoDocumento, tipoDoc);
    onFieldChange?.(fn.numeroDocumento, numDoc);
    onFieldChange?.(fn.razonSocial, razonSocial);
    if (fn.nombrePropietario) {
      onFieldChange?.(fn.nombrePropietario, razonSocial);
    }
  };

  const handleLookup = async () => {
    const num = lookupState.numero_documento.trim();
    if (!num) {
      notify.error("Ingresa el número de documento a consultar");
      return;
    }

    const expectedLen = lookupState.tipo_documento === "DNI" ? 8 : 11;
    if (num.length !== expectedLen) {
      notify.error(
        lookupState.tipo_documento === "DNI"
          ? "El DNI debe tener 8 dígitos"
          : "El RUC debe tener 11 dígitos",
      );
      return;
    }

    try {
      // Consulta externa genérica: GET /entidades/consulta/{documento} devuelve
      // { tipo_documento, numero_documento, razon_social } — tanto DNI como RUC.
      const result = await documentoLookup.mutateAsync(num);
      if (result) {
        const data = result as DocumentoConsultaData;
        const tipoDoc = lookupState.tipo_documento;
        setAllFields(tipoDoc, num, data.razon_social || "");
        notify.success("Datos del documento cargados");
      }
    } catch {
      // Error handled by mutation hooks
    }
  };

  return (
    <div className="space-y-3 pt-2 border-t border-border/60">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
        Datos de la Entidad
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="space-y-3 min-w-0">
          {/* ── Tipo de Documento (único RadioGroup, no duplicado) ────────────── */}
          <div>
            <Label className="text-primary font-semibold text-sm">
              Tipo de Documento
            </Label>
            <RadioGroup
              value={lookupState.tipo_documento}
              onValueChange={(val) => {
                const tipo = val as "DNI" | "RUC";
                isInternalUpdate.current = true;
                setLookupState({ tipo_documento: tipo, numero_documento: "" });
                tipoDocCtrl.field.onChange(val);
                onFieldChange?.(fn.tipoDocumento, val);
              }}
              className="flex gap-4 mt-2"
            >
              {TIPO_DOCUMENTO_OPTIONS.map((opt) => (
                <div key={opt.value} className="flex items-center space-x-2">
                  <RadioGroupItem
                    value={opt.value}
                    id={`entidad-tipo-${opt.value}`}
                  />
                  <Label
                    htmlFor={`entidad-tipo-${opt.value}`}
                    className="text-sm font-normal cursor-pointer"
                  >
                    {opt.label}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </div>

          {/* ── Número de Documento + Buscar (único input, no duplicado) ──────── */}
          <div className="space-y-2 min-w-0">
            <Label
              htmlFor="entidad-numero"
              className="text-primary font-semibold text-sm"
            >
              Número de Documento
            </Label>
            <div className="flex gap-2 min-w-0">
              <input
                id="entidad-numero"
                type="text"
                value={lookupState.numero_documento}
                onChange={(e) => {
                  const val = e.target.value;
                  if (!/^\d*$/.test(val)) return;
                  const maxLen = lookupState.tipo_documento === "DNI" ? 8 : 11;
                  if (val.length > maxLen) return;
                  setLookupState((s) => ({ ...s, numero_documento: val }));
                  numDocCtrl.field.onChange(val);
                  onFieldChange?.(fn.numeroDocumento, val);
                }}
                placeholder={
                  lookupState.tipo_documento === "DNI"
                    ? "Ej: 87654321"
                    : "Ej: 20456789012"
                }
                className="min-w-0 flex-1 h-10 rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              />
              <Button
                type="button"
                size="default"
                onClick={handleLookup}
                disabled={isConsulting || !isLookupValid}
                className="h-10 rounded-xl gap-2 shrink-0"
              >
                {isConsulting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
                Buscar
              </Button>
            </div>
            {numDocCtrl.fieldState.error && (
              <p className="text-sm text-destructive font-medium">
                {numDocCtrl.fieldState.error.message}
              </p>
            )}
          </div>
        </div>

        <div className="space-y-3 min-w-0">
          {/* ── Razón Social / Nombre Completo (auto-fill desde búsqueda) ─────── */}
          <div className="space-y-2 min-w-0">
            <Label
              htmlFor="entidad-razon"
              className="text-primary font-semibold text-sm"
            >
              {lookupState.tipo_documento === "RUC"
                ? "Razón Social"
                : "Nombre Completo"}
            </Label>
            <input
              id="entidad-razon"
              type="text"
              value={razonSocialCtrl.field.value || ""}
              onChange={razonSocialCtrl.field.onChange}
              onBlur={razonSocialCtrl.field.onBlur}
              ref={razonSocialCtrl.field.ref}
              name={razonSocialCtrl.field.name}
              placeholder={
                lookupState.tipo_documento === "RUC"
                  ? "Nombre de la empresa"
                  : "Nombres y apellidos"
              }
              className="flex h-10 w-full rounded-xl border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
            {razonSocialCtrl.fieldState.error && (
              <p className="text-sm text-destructive font-medium">
                {razonSocialCtrl.fieldState.error.message}
              </p>
            )}
          </div>
          {razonSocialSideSlot}
        </div>
      </div>
    </div>
  );
}
