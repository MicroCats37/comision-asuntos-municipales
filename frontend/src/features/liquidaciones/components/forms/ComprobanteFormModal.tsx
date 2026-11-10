"use client";

import { format } from "date-fns";
import { es } from "date-fns/locale";
import {
  Calendar as CalendarIcon,
  CheckCircle2,
  FilePenLine,
  Loader2,
  Receipt,
} from "lucide-react";
import { useCallback, useEffect, useId, useMemo, useState } from "react";
import type { Control, UseFormReturn } from "react-hook-form";
import { useController } from "react-hook-form";
import { z } from "zod";
import { GenericForm } from "@/components/genericForm/GenericForm";
import { GenericModal } from "@/components/genericModal/GenericModal";
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
import { useCrearComprobante, useEditarComprobante } from "@/features/liquidaciones/hooks";
import { cn } from "@/lib/utils";
import type { LiquidacionGeneralOutput } from "../../schemas/liquidacion-base.schema";
import {
  type CrearComprobanteInput,
  CrearComprobanteInputSchema,
  EditarComprobanteInputSchema,
  TIPO_COMPROBANTE_UI_ENUM,
} from "../../schemas/liquidacion-base.schema";
import { formatDate } from "../liquidacion-ui";

/**
 * Modo del FORMULARIO (no del modal).
 *
 * "crear" y "editar" no son dos modales distintos: son dos CONTENIDOS del
 * mismo formulario, dentro del mismo modal.
 */
type ModoFormularioComprobante = "crear" | "editar";

interface ComprobanteFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Full liquidacion data — used to derive active comprobante and show history */
  liquidacionGeneral: LiquidacionGeneralOutput;
  /** Called on successful creation/replacement/edition */
  onSuccess?: (updated: LiquidacionGeneralOutput) => void;
}

/**
 * Esquemas del FORMULARIO (no del API).
 *
 * Ambos modos comparten los mismos valores en memoria; lo que cambia es qué
 * campos se pintan y qué payload se envía. Por eso los dos esquemas declaran la
 * misma forma: cada uno es el esquema de su endpoint + el campo del otro modo
 * como opcional (para que el tipo del formulario sea único).
 *
 * `safeExtend` preserva las refinements del esquema base (el `superRefine` que
 * exige `serie` para FACTURA/BOLETA).
 */
const CREAR_FORM_SCHEMA = CrearComprobanteInputSchema;

const EDITAR_FORM_SCHEMA = EditarComprobanteInputSchema.safeExtend({
  motivo_reemplazo: z.string().optional(),
});

/** Valores del formulario — comunes a los dos modos. */
type ComprobanteFormValues = {
  tipo_comprobante: (typeof TIPO_COMPROBANTE_UI_ENUM)[number];
  serie?: string;
  numero?: string;
  fecha_emision?: string;
  motivo_reemplazo?: string;
};

/**
 * Returns the currently active comprobante, if any.
 */
function getActivoComprobante(
  comprobantes: LiquidacionGeneralOutput["comprobantes"],
) {
  return comprobantes.find((c) => c.activo) ?? null;
}

/** Individual text field component used inside the modal */
function CampoTexto({
  control,
  name,
  label,
  placeholder,
  type = "text",
  required,
}: {
  control: Control<ComprobanteFormValues>;
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
  control: Control<ComprobanteFormValues>;
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

/**
 * Campos del formulario de comprobante — comunes a los dos modos.
 *
 * El modo "crear" puede solicitar `motivo_reemplazo` si ya hay un comprobante activo.
 *
 * `monto` NO aparece en ningún modo: el backend lo preserva.
 *
 * `modoFormulario` NO es la prop `modo` del modal (que ya no existe): es el
 * contenido del formulario dentro del MISMO modal.
 */
function ComprobanteFormFields({
  methods,
  modoFormulario,
  mostrarMotivoReemplazo = true,
  motivoReemplazoRequerido = true,
}: {
  methods: UseFormReturn<ComprobanteFormValues>;
  modoFormulario: ModoFormularioComprobante;
  /**
   * Muestra el campo `motivo_reemplazo` (modo "crear").
   *
   * En el flujo "gestionar" el campo SÓLO aparece cuando hay un comprobante
   * activo (es decir, cuando la operación es un REEMPLAZO): en el alta en
   * blanco no hay nada que justificar.
   */
  mostrarMotivoReemplazo?: boolean;
  /** El `motivo_reemplazo` es obligatorio (sólo cuando hay comprobante activo). */
  motivoReemplazoRequerido?: boolean;
}) {
  return (
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

      {/* Motivo de reemplazo — sólo en modo crear/reemplazar */}
      {modoFormulario === "crear" && mostrarMotivoReemplazo && (
        <div className="space-y-2">
          <Label htmlFor="motivo_reemplazo">
            Motivo de reemplazo
            {motivoReemplazoRequerido && (
              <span className="text-destructive ml-1">*</span>
            )}
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
  );
}

/**
 * Vistas del flujo ÚNICO de gestión del comprobante.
 *
 * - "resumen": sólo lectura del comprobante vigente + historial + acciones.
 * - "crear":   alta (sin vigente) o REEMPLAZO (con vigente) — POST.
 * - "editar":  edición IN PLACE del comprobante vigente — PATCH.
 */
type VistaGestionarComprobante = "resumen" | "crear" | "editar";

/**
 * Resumen de SOLO LECTURA del comprobante vigente + historial.
 *
 * Es la PRIMERA vista del flujo "gestionar" cuando la liquidación YA tiene un
 * comprobante activo: el usuario ve el estado real antes de decidir. Las
 * acciones de esta vista cambian el CONTENIDO del MISMO modal (no abren otro
 * diálogo).
 */
function ComprobanteResumen({
  activo,
  comprobantes,
  onEditar,
  onReemplazar,
}: {
  activo: LiquidacionGeneralOutput["comprobantes"][number] | null;
  comprobantes: LiquidacionGeneralOutput["comprobantes"];
  onEditar: () => void;
  onReemplazar: () => void;
}) {
  const serieNumero =
    [activo?.serie, activo?.numero].filter(Boolean).join("-") || "—";

  return (
    <div className="space-y-4">
      {/* ── Comprobante vigente (sólo lectura) ── */}
      <div
        data-testid="comprobante-resumen"
        className="rounded-xl border border-border/50 bg-card p-4 space-y-3"
      >
        <div className="flex items-center gap-2 border-b border-border/40 pb-2">
          <CheckCircle2 className="h-4 w-4 text-success" />
          <h3 className="text-sm font-semibold uppercase tracking-wide">
            Comprobante vigente
          </h3>
        </div>

        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div className="min-w-0">
            <dt className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Tipo
            </dt>
            <dd className="font-medium truncate">
              {activo?.tipo_comprobante ?? "—"}
            </dd>
          </div>
          <div className="min-w-0">
            <dt className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Serie / Número
            </dt>
            <dd className="font-medium truncate">{serieNumero}</dd>
          </div>
          <div className="min-w-0">
            <dt className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Fecha de emisión
            </dt>
            <dd className="font-medium truncate">
              {activo?.fecha_emision ? formatDate(activo.fecha_emision) : "—"}
            </dd>
          </div>
          <div className="min-w-0">
            <dt className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              Monto
            </dt>
            <dd className="font-medium truncate">
              {activo?.monto != null ? `S/ ${activo.monto.toFixed(2)}` : "—"}
            </dd>
          </div>
        </dl>

        <p className="text-[11px] text-muted-foreground">
          El monto y el historial no se modifican al editar: la edición es in
          place sobre el comprobante vigente.
        </p>
      </div>

      {/* ── Historial (sólo lectura) ── */}
      <ComprobantesHistoryList comprobantes={comprobantes} />

      {/* ── Acciones de gestión (cambian el contenido del MISMO modal) ── */}
      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" onClick={onEditar}>
          <FilePenLine className="h-4 w-4" />
          Editar comprobante
        </Button>
        <Button type="button" variant="outline" onClick={onReemplazar}>
          <Receipt className="h-4 w-4" />
          Reemplazar comprobante
        </Button>
      </div>
    </div>
  );
}

/**
 * Flujo ÚNICO de gestión del comprobante.
 *
 * Un SOLO modal (un `GenericModal`) con tres vistas:
 *
 * 1. "resumen" — hay comprobante ACTIVO: sólo lectura del vigente + historial
 *    con las acciones "Editar comprobante" y "Reemplazar comprobante".
 * 2. "crear"   — alta (sin vigente) o REEMPLAZO (con vigente): POST al
 *    endpoint de comprobante.
 * 3. "editar"  — edición IN PLACE del comprobante ACTIVO: PATCH al recurso del
 *    comprobante (`monto` nunca viaja; el historial no crece).
 *
 * Cambiar de vista cambia el CONTENIDO del mismo modal: nunca se abre un
 * segundo diálogo ni se monta una segunda instancia del modal.
 */
function ComprobanteFormModalGestionar({
  open,
  onOpenChange,
  liquidacionGeneral,
  onSuccess,
}: ComprobanteFormModalProps) {
  const activo = getActivoComprobante(liquidacionGeneral.comprobantes);
  const activoId = activo?.id ?? null;

  const [vista, setVista] = useState<VistaGestionarComprobante>(
    activoId ? "resumen" : "crear",
  );

  /**
   * La vista se re-deriva del ESTADO REAL del comprobante vigente: si cambia
   * la liquidación objetivo, o el comprobante vigente aparece/desaparece (p.
   * ej. tras un alta), el flujo vuelve a su punto de partida.
   */
  useEffect(() => {
    setVista(activoId ? "resumen" : "crear");
  }, [liquidacionGeneral.id, activoId]);

  const formId = useId();

  const crearMutation = useCrearComprobante({
    liquidacionId: liquidacionGeneral.id,
    onSuccess: (updated) => {
      onSuccess?.(updated);
    },
  });

  const editarMutation = useEditarComprobante({
    liquidacionId: liquidacionGeneral.id,
    comprobanteId: activoId ?? "",
    onSuccess: (updated) => {
      onSuccess?.(updated);
    },
  });

  const isPending = crearMutation.isPending || editarMutation.isPending;

  /** El reemplazo sólo aplica cuando YA existe un comprobante vigente. */
  const esReemplazo = Boolean(activoId) && vista === "crear";

  const esquema = useMemo(() => {
    if (vista === "editar") return EDITAR_FORM_SCHEMA;
    if (!activoId) return CREAR_FORM_SCHEMA;
    return CREAR_FORM_SCHEMA.safeExtend({
      motivo_reemplazo: CREAR_FORM_SCHEMA.shape.motivo_reemplazo.refine(
        (val) => val != null && val.trim().length > 0,
        {
          message:
            "El motivo de reemplazo es requerido cuando existe un comprobante activo",
        },
      ),
    });
  }, [activoId, vista]);

  const initialData: ComprobanteFormValues =
    vista === "editar"
      ? {
          /**
           * Si el comprobante vigente tiene un tipo fuera del enum de UI (p.
           * ej. NOTA_CREDITO) se conserva el valor real: el Select no tendrá
           * una opción que lo represente y Zod bloqueará el guardado hasta
           * que el usuario elija un tipo válido — así el tipo NUNCA se cambia
           * en silencio.
           */
          tipo_comprobante: (activo?.tipo_comprobante ??
            "FACTURA") as ComprobanteFormValues["tipo_comprobante"],
           serie: activo?.serie ?? "",
           numero: activo?.numero ?? "",
           fecha_emision: activo?.fecha_emision ?? "",
        }
      : {
          tipo_comprobante: "FACTURA",
          serie: "",
          numero: "",
          fecha_emision: "",
          motivo_reemplazo: "",
        };

  const handleSubmit = useCallback(
    async (data: ComprobanteFormValues) => {
      try {
        if (vista === "editar") {
          // Sin comprobante vigente no hay nada que editar: no se emite PATCH.
          if (!activoId) return;
          // El payload lo construye el hook (`useEditarComprobante`): aquí sólo
          // se eligen los campos del formulario. `monto` no viaja nunca.
          await editarMutation.mutateAsync({
            tipo_comprobante: data.tipo_comprobante,
            serie: data.serie,
            numero: data.numero,
            fecha_emision: data.fecha_emision,
          });
        } else {
          // Alta o reemplazo: POST al endpoint de comprobante (`monto` no
          // viaja nunca: el backend lo preserva).
          const payload: CrearComprobanteInput = {
            tipo_comprobante: data.tipo_comprobante,
            serie: data.serie || undefined,
            numero: data.numero || undefined,
            fecha_emision: data.fecha_emision || undefined,
            motivo_reemplazo: data.motivo_reemplazo || undefined,
          };
          await crearMutation.mutateAsync(payload);
        }
        // Tras el guardado el modal se cierra (mismo comportamiento que el alta).
        onOpenChange(false);
      } catch {
        // El hook ya notificó el error (handleApiError + notify.error): el modal
        // permanece abierto para que el usuario corrija y reintente.
      }
    },
    [activoId, crearMutation, editarMutation, onOpenChange, vista],
  );

  const titulo =
    vista === "resumen"
      ? "Comprobante vigente"
      : vista === "editar"
        ? "Editar comprobante"
        : esReemplazo
          ? "Reemplazar comprobante"
          : "Agregar comprobante";

  const descripcion =
    vista === "resumen"
      ? "Revise el comprobante vigente y su historial. Puede editarlo o reemplazarlo."
      : vista === "editar"
        ? "Corrija los datos del comprobante vigente. El monto registrado y el historial no cambian."
        : esReemplazo
          ? "El comprobante actual será desactivado. Complete el nuevo comprobante."
          : "Ingrese los datos del comprobante de la liquidación.";

  const etiquetaPrimaria =
    vista === "editar"
      ? "Guardar cambios"
      : esReemplazo
        ? "Reemplazar"
        : "Agregar";

  return (
    <GenericModal
      open={open}
      onOpenChange={onOpenChange}
      preventClose={isPending}
    >
      <GenericModal.Content size="md">
        {/* ── Header ── */}
        <GenericModal.Header
          title=""
          className="bg-primary/[0.03] border-b border-border px-6 py-5 sm:px-8"
        >
          <div className="flex items-center gap-3 w-full">
            <div className="p-2 sm:p-2.5 bg-primary/10 rounded-xl sm:rounded-2xl border border-primary/20 shadow-sm shrink-0">
              <Receipt className="h-5 w-5 text-primary" />
            </div>
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                Liquidación
              </span>
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground leading-tight">
                {titulo}
              </h2>
              <p className="hidden sm:block max-w-prose text-pretty line-clamp-3 text-sm text-muted-foreground leading-relaxed">
                {descripcion}
              </p>
            </div>
          </div>
        </GenericModal.Header>

        {/* ── Body: el CONTENIDO cambia de vista, el modal es UNO ── */}
        <GenericModal.Body>
          {vista === "resumen" ? (
            <ComprobanteResumen
              activo={activo}
              comprobantes={liquidacionGeneral.comprobantes}
              onEditar={() => setVista("editar")}
              onReemplazar={() => setVista("crear")}
            />
          ) : (
            <GenericForm<ComprobanteFormValues>
              /* La `key` remonta el formulario al cambiar de vista: el form de
                 edición NUNCA hereda los valores del de alta/reemplazo. */
              key={`${vista}-${liquidacionGeneral.id}`}
              formId={formId}
              schema={esquema}
              initialData={initialData}
              onSubmit={handleSubmit}
              skipFooter
              isLoading={isPending}
              isDisabled={isPending}
            >
              {({ methods }) => (
                <div data-testid="comprobante-formulario" className="space-y-4">
                  {/* Aviso de reemplazo */}
                  {esReemplazo && (
                    <div className="rounded-lg border border-warning/20 bg-warning/5 p-3 flex items-start gap-2">
                      <CheckCircle2 className="h-4 w-4 text-warning shrink-0 mt-0.5" />
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-warning">
                          Comprobante activo actual
                        </p>
                        <p className="text-xs text-warning mt-0.5 truncate">
                          {activo?.tipo_comprobante}
                          {activo?.serie && activo?.numero
                            ? ` ${activo.serie}-${activo.numero}`
                            : ""}
                          {activo?.monto != null
                            ? ` · S/ ${activo.monto.toFixed(2)}`
                            : ""}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Historial (sólo lectura) */}
                  <ComprobantesHistoryList
                    comprobantes={liquidacionGeneral.comprobantes}
                  />

                  {/* Campos del formulario */}
                  <ComprobanteFormFields
                    methods={methods}
                    modoFormulario={vista === "editar" ? "editar" : "crear"}
                    mostrarMotivoReemplazo={esReemplazo}
                    motivoReemplazoRequerido={esReemplazo}
                  />
                </div>
              )}
            </GenericForm>
          )}
        </GenericModal.Body>

        {/* ── Footer: las acciones dependen de la vista ── */}
        <GenericModal.Footer className="px-6 py-4 sm:px-8 bg-muted/30 border-t border-border">
          {vista === "resumen" ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="flex-1 h-10 sm:h-11 rounded-xl font-semibold border-border/60 hover:bg-background transition-all duration-200 sm:max-w-[120px] text-muted-foreground hover:text-foreground"
            >
              Cerrar
            </Button>
          ) : (
            <>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  // Con comprobante vigente se vuelve al RESUMEN (mismo
                  // modal); sin él, se cierra el modal.
                  if (activoId) setVista("resumen");
                  else onOpenChange(false);
                }}
                className="flex-1 h-10 sm:h-11 rounded-xl font-semibold border border-border/60 hover:border-border hover:bg-background transition-all duration-200 sm:max-w-[120px] text-muted-foreground hover:text-foreground"
              >
                {activoId ? "Volver" : "Cancelar"}
              </Button>
              <Button
                type="submit"
                form={formId}
                disabled={isPending}
                className="flex-1 h-10 sm:h-12 rounded-xl sm:rounded-2xl font-bold shadow-lg shadow-primary/25 gap-2 sm:max-w-[160px] text-base transition-all duration-200 hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-0.5 active:translate-y-0 disabled:hover:translate-y-0 disabled:hover:shadow-lg"
              >
                {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                {!isPending && <CheckCircle2 className="h-4 w-4 sm:hidden" />}
                <span className="hidden sm:inline">
                  {isPending ? "Guardando..." : etiquetaPrimaria}
                </span>
              </Button>
            </>
          )}
        </GenericModal.Footer>

        <GenericModal.CloseX />
      </GenericModal.Content>
    </GenericModal>
  );
}

/**
 * Modal de comprobante — ÚNICA implementación pública.
 *
 * No hay prop `modo` ni selector de modo: el flujo se deriva del estado real
 * del comprobante vigente de la liquidación objetivo.
 *
 * - SIN comprobante vigente → vista de ALTA (POST).
 * - CON comprobante vigente  → vista de RESUMEN (sólo lectura + historial),
 *   desde la que se pasa a la EDICIÓN in-place (PATCH) o al REEMPLAZO (POST)
 *   cambiando el CONTENIDO de este MISMO modal.
 */
export function ComprobanteFormModal(props: ComprobanteFormModalProps) {
  return <ComprobanteFormModalGestionar {...props} />;
}
