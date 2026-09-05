"use client";

import { FilePenLine, FileText } from "lucide-react";
/**
 * HabilitacionUrbanaEditFormModal — Edit form for Habilitación Urbana (motor M2).
 * Reuses LiquidacionFormBodyBase (general) + Smart Fields M2 in edit mode.
 */
import { useCallback, useMemo, useState } from "react";
import { MoneyInput } from "@/components/genericForm/inputs/MoneyInput";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { notify } from "@/errors";
import { useEditarHabilitacionUrbana } from "../../hooks/useEditarHabilitacionUrbana";
import type { ContactoInline } from "../../schemas/liquidacion-form-base.schema";
import type { LiquidacionHabilitacionUrbanaListItem } from "../../schemas/liquidacion-habilitacion-urbana.schema";
import { ValoresActualesCard } from "../../components/liquidacion-ui";
import {
  type HabilitacionUrbanaFormData,
  habilitacionUrbanaFormSchema,
} from "../../schemas/liquidacion-habilitacion-urbana-form.schema";
import { ContactoFormModal } from "./ContactoFormModal";
import { CotizacionM2SmartField } from "./CotizacionM2SmartField";
import { LiquidacionFormBodyBase } from "./LiquidacionFormBodyBase";
import { TarifasM2SmartField } from "./TarifasM2SmartField";

interface HabilitacionUrbanaEditFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: LiquidacionHabilitacionUrbanaListItem;
  onSuccess?: () => void;
}

const toContactoInline = (
  contacto: LiquidacionHabilitacionUrbanaListItem["liquidacion_general"]["contacto"],
): ContactoInline | null => {
  if (!contacto?.nombres) return null;
  return {
    nombres: contacto.nombres,
    apellidos: contacto.apellidos ?? undefined,
    dni: contacto.dni ?? undefined,
    cargo: contacto.cargo ?? undefined,
    telefono: contacto.telefono ?? undefined,
    celular: contacto.celular ?? undefined,
    email: contacto.email ?? undefined,
  };
};

function buildInitialData(
  item: LiquidacionHabilitacionUrbanaListItem,
): HabilitacionUrbanaFormData {
  const { liquidacion_general: lg, liquidacion_tipo: lt } = item;
  return {
    denominacion: lg.denominacion_de_proyecto ?? "",
    municipalidad_id: lg.municipalidad?.id ?? "",
    expediente: lg.expediente ?? "",
    observacion: lg.observacion ?? "",
    retencion: lg.retencion ?? false,
    nombre_propietario: lg.proyecto.nombre_propietario,
    direccion: lg.proyecto.direccion,
    distrito_id: lg.proyecto.distrito?.id ?? "",
    urbanizacion: lg.proyecto.urbanizacion ?? undefined,
    entidad_tipo_documento:
      lg.proyecto.entidad?.tipo_documento === "DNI" ? "DNI" : "RUC",
    entidad_numero_documento: lg.proyecto.entidad?.numero_documento ?? "",
    entidad_razon_social: lg.proyecto.entidad?.razon_social ?? "",
    area_solicitada: lt.area_m2,
    tarifa_m2_id: lt.tarifa_aplicada_id,
  };
}

export function HabilitacionUrbanaEditFormModal({
  open,
  onOpenChange,
  item,
  onSuccess,
}: HabilitacionUrbanaEditFormModalProps) {
  const liquidacionId = item.liquidacion_general.id;
  const editarMutation = useEditarHabilitacionUrbana(liquidacionId);
  const [contacto, setContacto] = useState<ContactoInline | null>(() =>
    toContactoInline(item.liquidacion_general.contacto),
  );
  const [contactoModalOpen, setContactoModalOpen] = useState(false);

  const initialData = useMemo(() => buildInitialData(item), [item]);

  const handleContactoSaved = useCallback((saved: ContactoInline) => {
    setContacto(saved);
    setContactoModalOpen(false);
  }, []);

  const handleSubmit = useCallback(
    async (data: HabilitacionUrbanaFormData) => {
      try {
        await editarMutation.mutateAsync({
          ...data,
          contacto: contacto ?? undefined,
        });
        notify.success("Liquidación editada correctamente");
        onSuccess?.();
      } catch {
        // Error handled by mutation
      }
    },
    [editarMutation, contacto, onSuccess],
  );

  return (
    <>
      <AppFormModal<HabilitacionUrbanaFormData>
        open={open}
        onOpenChange={onOpenChange}
        title="Editar Liquidación — Habilitación Urbana"
        eyebrow="Habilitación Urbana"
        icon={<FilePenLine className="h-5 w-5 text-primary" />}
        primaryLabel="Guardar cambios"
        primaryLoadingLabel="Guardando..."
        primaryLoading={editarMutation.isPending}
        onPrimary={() => undefined}
        schema={habilitacionUrbanaFormSchema}
        initialData={initialData}
        onSubmit={handleSubmit}
      >
        {({ methods }) => (
          <LiquidacionFormBodyBase
            control={methods.control as never}
            methods={methods}
            contacto={contacto}
            onAddContacto={() => setContactoModalOpen(true)}
            onRemoveContacto={() => setContacto(null)}
            showUrbanizacion
            tramiteField={
              <MoneyInput
                name="area_solicitada"
                label="Área Solicitada (m²)"
                required
                control={methods.control}
                min={0}
                defaultValue={initialData.area_solicitada}
                className="w-full"
              />
              }
              valoresActualesSection={
                <ValoresActualesCard
                  subTotal={item.liquidacion_general.sub_total}
                  total={item.liquidacion_general.total}
                />
              }
              motorSection={
                <div className="space-y-3">
                <TarifasM2SmartField
                  methods={methods}
                  tipo="habilitacion-urbana"
                />
                <CotizacionM2SmartField
                  methods={methods}
                  tipo="habilitacion-urbana"
                  mode="edit"
                  liquidacionId={liquidacionId}
                />
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
