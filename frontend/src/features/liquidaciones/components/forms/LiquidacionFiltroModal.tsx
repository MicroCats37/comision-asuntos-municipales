"use client";

import { format } from "date-fns";
import { es } from "date-fns/locale";
import {
  Building2,
  Calendar as CalendarIcon,
  Filter,
  Hash,
  IdCard,
  MapPin,
  User,
  UserRound,
} from "lucide-react";
/**
 * LiquidacionFiltroModal — Modal de filtros para listas de liquidaciones.
 * Usa AppFormModal como shell.
 *
 * Filtros del backend (comunes a los 6 tipos):
 *   entidad_id, propietario, fecha_desde, fecha_hasta, numero,
 *   razon_social, creado_por, numero_revisiones
 */
import { useCallback } from "react";
import { z } from "zod";
import { GenericInput } from "@/components/genericForm/GenericInput";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { useDistritos } from "../../hooks/useDistritos";
import type { LiquidacionFiltros } from "../../hooks/useLiquidacionList";
import { useMunicipalidades } from "../../hooks/useMunicipalidades";

const filtroSchema = z.object({
  entidad_id: z.string().optional(),
  distrito_id: z.string().optional(),
  propietario: z.string().optional(),
  fecha_desde: z.string().optional(),
  fecha_hasta: z.string().optional(),
  numero: z.string().optional(),
  razon_social: z.string().optional(),
  creado_por: z.string().optional(),
  numero_revisiones: z.string().optional(),
  direccion: z.string().optional(),
});

type FiltroFormData = z.infer<typeof filtroSchema>;

interface LiquidacionFiltroModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialFiltros?: LiquidacionFiltros;
  onApply: (filtros: LiquidacionFiltros) => void;
}

function CampoTexto({
  name,
  label,
  placeholder,
  register,
  icon: Icon,
}: {
  name: keyof FiltroFormData;
  label: string;
  placeholder?: string;
  register: any;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={name}>{label}</Label>
      <div className="relative">
        {Icon && (
          <Icon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        )}
        <Input
          id={name}
          placeholder={placeholder}
          className={Icon ? "pl-10 w-full" : "w-full"}
          {...register(name)}
        />
      </div>
    </div>
  );
}

function CampoFecha({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            className="w-full h-10 justify-start text-left font-normal pl-9 relative"
          >
            <CalendarIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            {value ? (
              format(new Date(value), "PPP", { locale: es })
            ) : (
              <span className="text-muted-foreground">Seleccionar...</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={value ? new Date(value) : undefined}
            onSelect={(date) =>
              onChange(date ? format(date, "yyyy-MM-dd") : "")
            }
            locale={es}
            initialFocus
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}

export function LiquidacionFiltroModal({
  open,
  onOpenChange,
  initialFiltros,
  onApply,
}: LiquidacionFiltroModalProps) {
  const { data: municipalidades, isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();
  const { data: distritos, isLoading: isLoadingDistritos } = useDistritos();

  const initialData: FiltroFormData = {
    entidad_id: initialFiltros?.entidad_id ?? "",
    distrito_id: initialFiltros?.distrito_id ?? "",
    propietario: initialFiltros?.propietario ?? "",
    fecha_desde: initialFiltros?.fecha_desde ?? "",
    fecha_hasta: initialFiltros?.fecha_hasta ?? "",
    numero: initialFiltros?.numero ? String(initialFiltros.numero) : "",
    razon_social: initialFiltros?.razon_social ?? "",
    creado_por: initialFiltros?.creado_por ?? "",
    numero_revisiones: initialFiltros?.numero_revisiones
      ? String(initialFiltros.numero_revisiones)
      : "",
    direccion: initialFiltros?.direccion ?? "",
  };

  const handleSubmit = useCallback(
    async (data: FiltroFormData) => {
      const filtros: LiquidacionFiltros = {};
      if (data.entidad_id) filtros.entidad_id = data.entidad_id;
      if (data.distrito_id) filtros.distrito_id = data.distrito_id;
      if (data.propietario) filtros.propietario = data.propietario;
      if (data.fecha_desde) filtros.fecha_desde = data.fecha_desde;
      if (data.fecha_hasta) filtros.fecha_hasta = data.fecha_hasta;
      if (data.numero) filtros.numero = Number(data.numero);
      if (data.razon_social) filtros.razon_social = data.razon_social;
      if (data.creado_por) filtros.creado_por = data.creado_por;
      if (data.numero_revisiones)
        filtros.numero_revisiones = Number(data.numero_revisiones);
      if (data.direccion) filtros.direccion = data.direccion;
      onApply(filtros);
    },
    [onApply],
  );

  return (
    <AppFormModal<FiltroFormData>
      open={open}
      onOpenChange={onOpenChange}
      title="Filtrar Liquidaciones"
      description="Filtra la lista por municipalidad, distrito, propietario, fechas y otros datos."
      eyebrow="Liquidación"
      icon={<Filter className="h-5 w-5 text-primary" />}
      primaryLabel="Aplicar Filtros"
      primaryLoadingLabel="Aplicando..."
      primaryLoading={false}
      primaryDisabled={false}
      onPrimary={() => undefined}
      schema={filtroSchema}
      initialData={initialData}
      onSubmit={handleSubmit}
      size="lg"
    >
      {({ methods }) => (
        <div className="space-y-4">
          {/* Fila 1: Municipalidad + Distrito */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <GenericInput
              field={{
                name: "entidad_id",
                label: "Municipalidad",
                type: "searchable-select",
                containerClassName: "col-span-1",
                className: "[&_button]:w-full",
                placeholder: isLoadingMunicipalidades
                  ? "Cargando..."
                  : "Buscar municipalidad",
                icon: Building2,
                isLoading: isLoadingMunicipalidades,
                options: (municipalidades || []).map((municipalidad) => ({
                  value: municipalidad.id,
                  label: `${
                    municipalidad.codigo ? `${municipalidad.codigo} - ` : ""
                  }${municipalidad.nombre}`,
                })),
              }}
              register={methods.register as never}
              control={methods.control as never}
              errors={methods.formState.errors}
            />
            <GenericInput
              field={{
                name: "distrito_id",
                label: "Distrito",
                type: "searchable-select",
                containerClassName: "col-span-1",
                className: "[&_button]:w-full",
                placeholder: isLoadingDistritos
                  ? "Cargando..."
                  : "Buscar distrito",
                icon: MapPin,
                isLoading: isLoadingDistritos,
                options: (distritos || []).map((distrito) => ({
                  value: distrito.id,
                  label: `${distrito.nombre} - ${distrito.provinciaNombre}`,
                })),
              }}
              register={methods.register as never}
              control={methods.control as never}
              errors={methods.formState.errors}
            />
          </div>

          {/* Fila 2: Propietario + Dirección */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <CampoTexto
              name="propietario"
              label="Propietario"
              placeholder="Nombre del propietario"
              register={methods.register}
              icon={User}
            />
            <CampoTexto
              name="direccion"
              label="Dirección"
              placeholder="Dirección del proyecto"
              register={methods.register}
              icon={MapPin}
            />
          </div>

          {/* Fila 3: Fechas */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <CampoFecha
              label="Fecha Desde"
              value={methods.watch("fecha_desde") || ""}
              onChange={(v) => methods.setValue("fecha_desde", v)}
            />
            <CampoFecha
              label="Fecha Hasta"
              value={methods.watch("fecha_hasta") || ""}
              onChange={(v) => methods.setValue("fecha_hasta", v)}
            />
          </div>

          {/* Fila 4: Razón Social + Número */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <CampoTexto
              name="razon_social"
              label="Razón Social"
              placeholder="Razón social de la entidad"
              register={methods.register}
              icon={Building2}
            />
            <CampoTexto
              name="numero"
              label="Número"
              placeholder="Número de liquidación"
              register={methods.register}
              icon={Hash}
            />
          </div>

          {/* Fila 5: Creado por + N° Revisiones */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <CampoTexto
              name="creado_por"
              label="Creado Por"
              placeholder="Username del creador"
              register={methods.register}
              icon={UserRound}
            />
            <CampoTexto
              name="numero_revisiones"
              label="N° Revisiones"
              placeholder="Número de revisión exacto"
              register={methods.register}
              icon={IdCard}
            />
          </div>
        </div>
      )}
    </AppFormModal>
  );
}
