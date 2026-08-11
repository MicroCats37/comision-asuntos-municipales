"use client";

/**
 * MecanicaSuelosFormModal — Form delgado para Mecánica de Suelos (motor M2).
 * Reutiliza LiquidacionFormBodyBase (general) + Smart Fields M2.
 */
import { useCallback, useState } from "react";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { notify } from "@/errors";
import { FileText } from "lucide-react";
import { useCrearMecanicaSuelos } from "../../hooks/useCrearMecanicaSuelos";
import { mecanicaSuelosFormSchema, type MecanicaSuelosFormData } from "../../schemas/liquidacion-mecanica-suelos-form.schema";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";
import { LiquidacionFormBodyBase } from "./LiquidacionFormBodyBase";
import { TarifasM2SmartField } from "./TarifasM2SmartField";
import { CotizacionM2SmartField } from "./CotizacionM2SmartField";
import { ContactoFormModal } from "./ContactoFormModal";

interface MecanicaSuelosFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onCreated?: () => void;
}

export function MecanicaSuelosFormModal({
  open,
  onOpenChange,
  onSuccess,
  onCreated,
}: MecanicaSuelosFormModalProps) {
  const crearMutation = useCrearMecanicaSuelos();
  const [contacto, setContacto] = useState<ContactoInline | null>(null);
  const [contactoModalOpen, setContactoModalOpen] = useState(false);

  const handleContactoSaved = useCallback((saved: ContactoInline) => {
    setContacto(saved);
    setContactoModalOpen(false);
  }, []);

  const handleSubmit = useCallback(
    async (data: MecanicaSuelosFormData) => {
      try {
        await crearMutation.mutateAsync({ ...data, contacto: contacto ?? undefined });
        notify.success("Liquidación creada correctamente");
        setContacto(null);
        onSuccess?.();
        onCreated?.();
      } catch {
        // Error handled by mutation
      }
    },
    [crearMutation, contacto, onSuccess, onCreated],
  );

  return (
    <>
      <AppFormModal<MecanicaSuelosFormData>
        open={open}
        onOpenChange={onOpenChange}
        title="Nueva Liquidación — Mecánica de Suelos"
        eyebrow="Mecánica de Suelos"
        icon={<FileText className="h-5 w-5 text-primary" />}
        primaryLabel="Crear Liquidación"
        primaryLoadingLabel="Creando..."
        primaryLoading={crearMutation.isPending}
        onPrimary={() => undefined}
        schema={mecanicaSuelosFormSchema}
        initialData={{ area_solicitada: 0 }}
        onSubmit={handleSubmit}
      >
        {({ methods }) => (
          <LiquidacionFormBodyBase
            control={methods.control as never}
            methods={methods}
            contacto={contacto}
            onAddContacto={() => setContactoModalOpen(true)}
            onRemoveContacto={() => setContacto(null)}
            tramiteField={
              <div className="space-y-2">
                <Label htmlFor="area_solicitada">Área Solicitada (m²) <span className="text-destructive">*</span></Label>
                <Input
                  id="area_solicitada"
                  type="number"
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  className="w-full"
                  {...methods.register("area_solicitada", { valueAsNumber: true })}
                />
              </div>
            }
            motorSection={
              <div className="space-y-3">
                <TarifasM2SmartField methods={methods} tipo="mecanica-suelos" />
                <CotizacionM2SmartField methods={methods} tipo="mecanica-suelos" />
              </div>
            }
          />
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
