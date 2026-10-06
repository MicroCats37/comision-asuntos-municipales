"use client";

import { format } from "date-fns";
import { es } from "date-fns/locale";
import { Calendar as CalendarIcon, CheckCircle2, Receipt } from "lucide-react";
import { useCallback, useId, useMemo } from "react";
import type { Control } from "react-hook-form";
import { useController } from "react-hook-form";
import type { z } from "zod";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { useCrearComprobante } from "@/features/liquidaciones/hooks";
import { cn } from "@/lib/utils";
import type { LiquidacionGeneralOutput } from "../../schemas/liquidacion-base.schema";
import {
  type CrearComprobanteInput,
  CrearComprobanteInputSchema,
  TIPO_COMPROBANTE_UI_ENUM,
} from "../../schemas/liquidacion-base.schema";
import { formatDate } from "../liquidacion-ui";

interface ComprobanteFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Full liquidacion data — used to derive active comprobante and show history */
  liquidacionGeneral: LiquidacionGeneralOutput;
  /** Called on successful creation/replacement */
  onSuccess?: (updated: LiquidacionGeneralOutput) => void;
}

/**
 * Returns the currently active comprobante, if any.
 */
function getActivoComprobante(
  comprobantes: LiquidacionGeneralOutput["comprobantes"],
) {
  return comprobantes.find((c) => c.activo) ?? null;
}

const defaultFormData: CrearComprobanteInput = {
  tipo_comprobante: "FACTURA",
  serie: "",
  numero: "",
  fecha_emision: "",
  motivo_reemplazo: "",
};

/** Individual text field component used inside the modal */
function CampoTexto({
  control,
  name,
  label,
  placeholder,
  type = "text",
  required,
}: {
  control: Control<CrearComprobanteInput>;
  name: "serie" | "numero" | "fecha_emision";
  label: string;
  placeholder?: string;
  type?: "text" | "date" | "number";
  required?: boolean;
}) {
  const { field, fieldState } = useController({
    name,
    control,
    defaultValue: "",
  });
  return (
    <div className="space-y-2">
      <Label htmlFor={name}>
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <Input
        id={name}
        type={type}
        placeholder={placeholder}
        {...field}
        className="w-full"
      />
      {fieldState.error && (
        <p className="text-xs text-destructive">{fieldState.error.message}</p>
      )}
    </div>
  );
}

/** Date picker using shadcn Calendar popover — returns YYYY-MM-DD string */
function DatePickerField({
  control,
  name,
  label,
  required,
}: {
  control: Control<CrearComprobanteInput>;
  name: "fecha_emision";
  label: string;
  required?: boolean;
}) {
  const id = useId();
  const { field, fieldState } = useController({
    name,
    control,
    defaultValue: "",
  });

  const selectedDate = field.value ? new Date(field.value) : undefined;

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            id={id}
            variant="outline"
            className={cn(
              "w-full justify-start text-left font-normal h-9 px-3 rounded-lg",
              !field.value && "text-muted-foreground",
            )}
          >
            <CalendarIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            {field.value
              ? format(selectedDate!, "PPP", { locale: es })
              : "Seleccionar..."}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={selectedDate}
            onSelect={(date) =>
              field.onChange(date ? format(date, "yyyy-MM-dd") : null)
            }
            locale={es}
            initialFocus
          />
        </PopoverContent>
      </Popover>
      {fieldState.error && (
        <p className="text-xs text-destructive">{fieldState.error.message}</p>
      )}
    </div>
  );
}

/** Comprobantes history list shown above the form */
function ComprobantesHistoryList({
  comprobantes,
}: {
  comprobantes: LiquidacionGeneralOutput["comprobantes"];
}) {
  if (comprobantes.length === 0) {
    return null;
  }
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Historial de comprobantes
      </h4>
      <div className="rounded-lg border border-border/50 bg-card divide-y divide-border/40">
        {comprobantes.map((c) => (
          <div
            key={c.id}
            className="flex items-center justify-between px-3 py-2"
          >
            <div className="flex items-center gap-2 min-w-0">
              {c.activo ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-success shrink-0" />
              ) : (
                <span className="h-3.5 w-3.5 rounded-full border border-muted-foreground/30 shrink-0" />
              )}
              <span className="text-xs font-medium truncate">
                {c.tipo_comprobante ?? "—"}
                {c.serie && c.numero
                  ? ` ${c.serie}-${c.numero}`
                  : c.serie
                    ? ` ${c.serie}`
                    : c.numero
                      ? ` ${c.numero}`
                      : ""}
              </span>
              {c.activo && (
                <span className="shrink-0 rounded-full bg-success/15 px-1.5 py-0.5 text-[9px] font-bold text-success uppercase tracking-wider">
                  Activo
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 shrink-0">
              {c.monto != null && (
                <span className="text-xs text-muted-foreground">
                  S/ {c.monto.toFixed(2)}
                </span>
              )}
              {c.fecha_emision && (
                <span className="text-[10px] text-muted-foreground">
                  {formatDate(c.fecha_emision)}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ComprobanteFormModal({
  open,
  onOpenChange,
  liquidacionGeneral,
  onSuccess,
}: ComprobanteFormModalProps) {
  const activo = getActivoComprobante(liquidacionGeneral.comprobantes);
  const isReplacement = activo !== null;

  const title = isReplacement
    ? "Reemplazar comprobante"
    : "Agregar comprobante";
  const description = isReplacement
    ? "El comprobante actual será desactivado. Complete el nuevo comprobante."
    : "Ingrese los datos del comprobante de la liquidación.";

  const crearMutation = useCrearComprobante({
    liquidacionId: liquidacionGeneral.id,
    onSuccess: (updated) => {
      onSuccess?.(updated);
    },
  });

  const handleSubmit = useCallback(
    async (data: CrearComprobanteInput) => {
      // Build payload — strip empty strings; monto is NOT sent from the frontend
      const payload: CrearComprobanteInput = {
        tipo_comprobante: data.tipo_comprobante,
        serie: data.serie || undefined,
        numero: data.numero || undefined,
        fecha_emision: data.fecha_emision || undefined,
        motivo_reemplazo: data.motivo_reemplazo || undefined,
      };
      await crearMutation.mutateAsync(payload);
      // AppFormModal closes the modal via handleFormSubmit wrapper
    },
    [crearMutation],
  );

  // Determine if motivo_reemplazo is required based on active comprobante
  const schema = useMemo(() => {
    if (isReplacement) {
      return CrearComprobanteInputSchema.safeExtend({
        motivo_reemplazo:
          CrearComprobanteInputSchema.shape.motivo_reemplazo.refine(
            (val) => val != null && val.trim().length > 0,
            {
              message:
                "El motivo de reemplazo es requerido cuando existe un comprobante activo",
            },
          ),
      });
    }
    return CrearComprobanteInputSchema;
  }, [isReplacement]);

  const formInitialData: CrearComprobanteInput = {
    tipo_comprobante: "FACTURA",
    serie: "",
    numero: "",
    fecha_emision: "",
    motivo_reemplazo: "",
  };

  return (
    <AppFormModal<CrearComprobanteInput>
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      description={description}
      eyebrow="Liquidación"
      icon={<Receipt className="h-5 w-5 text-primary" />}
      primaryLabel={isReplacement ? "Reemplazar" : "Agregar"}
      primaryLoadingLabel={isReplacement ? "Reemplazando..." : "Agregando..."}
      primaryLoading={crearMutation.isPending}
      primaryDisabled={false}
      onPrimary={() => undefined}
      schema={schema}
      initialData={formInitialData}
      onSubmit={handleSubmit}
      size="md"
    >
      {({ methods }) => (
        <div className="space-y-4">
          {/* Reemplazo warning */}
          {isReplacement && (
            <div className="rounded-lg border border-warning/20 bg-warning/5 p-3 flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-warning shrink-0 mt-0.5" />
              <div className="min-w-0">
                <p className="text-xs font-semibold text-warning">
                  Comprobante activo actual
                </p>
                <p className="text-xs text-warning mt-0.5 truncate">
                  {activo.tipo_comprobante}
                  {activo.serie && activo.numero
                    ? ` ${activo.serie}-${activo.numero}`
                    : ""}
                  {activo.monto != null
                    ? ` · S/ ${activo.monto.toFixed(2)}`
                    : ""}
                </p>
              </div>
            </div>
          )}

          {/* Historial */}
          <ComprobantesHistoryList
            comprobantes={liquidacionGeneral.comprobantes}
          />

          {/* Form fields */}
          <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
            <div className="flex items-center gap-2 border-b border-border/40 pb-2">
              <Receipt className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold uppercase tracking-wide">
                Datos del comprobante
              </h3>
            </div>

            {/* Tipo — required */}
            <div className="space-y-2">
              <Label htmlFor="tipo_comprobante">
                Tipo de comprobante
                <span className="text-destructive ml-1">*</span>
              </Label>
              <Select
                value={methods.watch("tipo_comprobante")}
                onValueChange={(val) =>
                  methods.setValue(
                    "tipo_comprobante",
                    val as (typeof TIPO_COMPROBANTE_UI_ENUM)[number],
                    {
                      shouldValidate: true,
                    },
                  )
                }
              >
                <SelectTrigger id="tipo_comprobante">
                  <SelectValue placeholder="Seleccione tipo" />
                </SelectTrigger>
                <SelectContent>
                  {TIPO_COMPROBANTE_UI_ENUM.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t.replace("_", " ")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {methods.formState.errors.tipo_comprobante && (
                <p className="text-xs text-destructive">
                  {methods.formState.errors.tipo_comprobante.message}
                </p>
              )}
            </div>

            {/* Serie + Número */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <CampoTexto
                control={methods.control}
                name="serie"
                label="Serie"
                placeholder="F001"
              />
              <CampoTexto
                control={methods.control}
                name="numero"
                label="Número"
                placeholder="00000123"
              />
            </div>

            {/* Fecha emisión */}
            <DatePickerField
              control={methods.control}
              name="fecha_emision"
              label="Fecha de emisión"
            />

            {/* Motivo reemplazo — conditionally required */}
            {isReplacement && (
              <div className="space-y-2">
                <Label htmlFor="motivo_reemplazo">
                  Motivo de reemplazo
                  <span className="text-destructive ml-1">*</span>
                </Label>
                <Input
                  id="motivo_reemplazo"
                  placeholder="Ej: Comprobante incorrecto, anulación por..."
                  value={methods.watch("motivo_reemplazo") ?? ""}
                  onChange={(e) =>
                    methods.setValue("motivo_reemplazo", e.target.value, {
                      shouldValidate: true,
                    })
                  }
                  onBlur={() => methods.trigger("motivo_reemplazo")}
                  className="w-full"
                />
                {methods.formState.errors.motivo_reemplazo && (
                  <p className="text-xs text-destructive">
                    {
                      methods.formState.errors.motivo_reemplazo
                        .message as string
                    }
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </AppFormModal>
  );
}
