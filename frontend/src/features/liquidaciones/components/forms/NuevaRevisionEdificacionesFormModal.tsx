"use client";

/**
 * NuevaRevisionEdificacionesFormModal — Form LIVIANO para nueva revisión de Edificaciones.
 *
 * Schema propio reducido (NO usa el form general):
 *  - Se hereda de la previa: valor_declarado, municipalidad_id, proyecto
 *  - Se edita: expediente, observacion, retencion, contacto, tarifas (preseleccionada una)
 *
 * Endpoint: POST /liquidaciones/edificaciones/nueva-revision
 */
import { useCallback, useEffect, useState } from "react";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { FileText, RefreshCw } from "lucide-react";
import { notify } from "@/errors";
import { useQuery } from "@tanstack/react-query";
import { useController } from "react-hook-form";
import api from "@/lib/api";
import { useCrearNuevaRevisionEdificaciones } from "../../hooks/useCrearNuevaRevisionEdificaciones";
import {
  nuevaRevisionEdificacionesFormSchema,
  type NuevaRevisionEdificacionesFormData,
} from "../../schemas/liquidacion-nueva-revision-form.schema";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";
import { CotizacionPorcentajeSmartField } from "./CotizacionPorcentajeSmartField";
import { ContactoFormModal } from "./ContactoFormModal";
import { CircleCheck, Star } from "lucide-react";

interface TarifaVigente {
  id: string;
  especialidad: string;
  porcentaje_liquidacion: number;
}

interface NuevaRevisionEdificacionesFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Liquidación previa (base) — se hereda valor_declarado, municipalidad, proyecto */
  liquidacionPreviaId: string;
  onSuccess?: () => void;
}

const formatPercent = (value: number): string => `${(value * 100).toFixed(2)}%`;

/** Selector de tarifas — seleccionable con UNA preseleccionada por defecto */
function TarifasNuevaRevisionSelector({ methods }: { methods: any }) {
  const { field } = useController({ name: "tarifas_ids", control: methods.control, defaultValue: [] });
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const { data: tarifas, isLoading } = useQuery<TarifaVigente[]>({
    queryKey: ["liquidaciones", "edificaciones", "tarifas-vigentes"],
    queryFn: async () => {
      const { data } = await api.get("/liquidaciones/edificaciones/tarifas/vigentes");
      return data.data?.tarifas || [];
    },
  });

  // Preseleccionar la PRIMERA tarifa vigente por defecto
  useEffect(() => {
    if (tarifas && tarifas.length > 0 && selectedIds.length === 0) {
      const firstId = tarifas[0].id;
      setSelectedIds([firstId]);
      methods.setValue("tarifas_ids", [firstId], { shouldValidate: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tarifas]);

  const handleToggle = (id: string) => {
    setSelectedIds((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      methods.setValue("tarifas_ids", next, { shouldValidate: true });
      return next;
    });
  };

  if (isLoading) {
    return <div className="h-24 rounded-xl border bg-card animate-pulse" />;
  }

  if (!tarifas || tarifas.length === 0) {
    return <p className="text-sm text-muted-foreground">No hay tarifas vigentes</p>;
  }

  return (
    <div className="space-y-2">
      <Label>Tarifas Vigentes <span className="text-destructive">*</span></Label>
      <div className="flex flex-col gap-2">
        {tarifas.map((tarifa) => {
          const isSelected = selectedIds.includes(tarifa.id);
          return (
            <button
              key={tarifa.id}
              type="button"
              onClick={() => handleToggle(tarifa.id)}
              className={[
                "rounded-lg border bg-background px-3 py-2 transition-all duration-200 text-left w-full flex items-center justify-between gap-3 cursor-pointer",
                isSelected
                  ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                  : "border-border hover:border-primary/40",
              ].join(" ")}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <div
                  className={[
                    "flex items-center justify-center rounded-md border shrink-0 p-1",
                    isSelected ? "bg-primary text-primary-foreground border-primary" : "bg-muted text-muted-foreground border-border",
                  ].join(" ")}
                >
                  {isSelected ? <CircleCheck className="h-4 w-4" /> : <Star className="h-4 w-4" />}
                </div>
                <span className="text-sm font-medium truncate">{tarifa.especialidad}</span>
              </div>
              <span className="text-xs font-semibold">{formatPercent(tarifa.porcentaje_liquidacion)}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function NuevaRevisionEdificacionesFormModal({
  open,
  onOpenChange,
  liquidacionPreviaId,
  onSuccess,
}: NuevaRevisionEdificacionesFormModalProps) {
  const crearMutation = useCrearNuevaRevisionEdificaciones();
  const [contacto, setContacto] = useState<ContactoInline | null>(null);
  const [contactoModalOpen, setContactoModalOpen] = useState(false);

  const handleContactoSaved = useCallback((saved: ContactoInline) => {
    setContacto(saved);
    setContactoModalOpen(false);
  }, []);

  const handleSubmit = useCallback(
    async (data: NuevaRevisionEdificacionesFormData) => {
      try {
        await crearMutation.mutateAsync({ ...data, liquidacion_previa_id: liquidacionPreviaId, contacto: contacto ?? undefined });
        notify.success("Nueva revisión creada correctamente");
        setContacto(null);
        onSuccess?.();
      } catch {
        // Error handled by mutation
      }
    },
    [crearMutation, liquidacionPreviaId, contacto, onSuccess],
  );

  return (
    <>
      <AppFormModal<NuevaRevisionEdificacionesFormData>
        open={open}
        onOpenChange={onOpenChange}
        title="Nueva Revisión"
        description="Crea una nueva revisión sobre la liquidación seleccionada"
        eyebrow="Edificaciones"
        icon={<RefreshCw className="h-5 w-5 text-primary" />}
        primaryLabel="Crear Revisión"
        primaryLoadingLabel="Creando..."
        primaryLoading={crearMutation.isPending}
        onPrimary={() => undefined}
        schema={nuevaRevisionEdificacionesFormSchema}
        initialData={{ liquidacion_previa_id: liquidacionPreviaId, expediente: "", retencion: false, tarifas_ids: [] }}
        onSubmit={handleSubmit}
        size="lg"
      >
        {({ methods }) => (
          <div className="space-y-4">
            {/* Datos editables */}
            <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
              <div className="flex items-center gap-2 border-b border-border/40 pb-2">
                <FileText className="h-4 w-4 text-primary" />
                <h3 className="text-sm font-semibold uppercase tracking-wide">Datos de la Revisión</h3>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="expediente">Expediente <span className="text-destructive">*</span></Label>
                  <Input id="expediente" placeholder="Número de expediente" className="w-full" {...methods.register("expediente")} />
                </div>
                <div className="space-y-2">
                  <Label>Retención</Label>
                  <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-background px-3 py-2.5">
                    <Checkbox
                      id="retencion"
                      checked={!!methods.watch("retencion")}
                      onCheckedChange={(checked) => methods.setValue("retencion", !!checked)}
                    />
                    <Label htmlFor="retencion" className="text-sm font-medium cursor-pointer">¿Tiene retención?</Label>
                  </div>
                </div>
                <div className="sm:col-span-2 space-y-2">
                  <Label htmlFor="observacion">Observación</Label>
                  <Textarea id="observacion" placeholder="Observaciones (opcional)" rows={2} {...methods.register("observacion")} />
                </div>
              </div>
            </div>

            {/* Tarifas — preseleccionada una */}
            <TarifasNuevaRevisionSelector methods={methods} />

            {/* Cotización preview */}
            <CotizacionPorcentajeSmartField methods={methods} />

            {/* Contacto (opcional, reutiliza el modal existente) */}
            <div className="rounded-xl border border-border/50 bg-card p-4">
              <div className="flex items-center justify-between">
                <Label>Contacto Principal</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setContactoModalOpen(true)}
                  className="h-8 gap-1 text-xs"
                >
                  {contacto ? "Editar" : "Agregar"}
                </Button>
              </div>
              {contacto ? (
                <p className="text-sm mt-2">
                  {contacto.nombres} {contacto.apellidos}
                  {contacto.email ? ` · ${contacto.email}` : ""}
                </p>
              ) : (
                <p className="text-xs text-muted-foreground/70 italic mt-2">Sin contacto registrado</p>
              )}
            </div>
          </div>
        )}
      </AppFormModal>

      <ContactoFormModal
        open={contactoModalOpen}
        onOpenChange={setContactoModalOpen}
        onSaved={handleContactoSaved}
        initialData={contacto ?? undefined}
      />
    </>
  );
}
