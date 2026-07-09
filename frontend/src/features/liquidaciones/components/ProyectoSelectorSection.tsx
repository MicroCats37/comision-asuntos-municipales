"use client";

import { AlertCircle, Building2, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ProyectoSelectorSectionProps } from "../types/liquidacion-edificaciones-form.types";

export function ProyectoSelectorSection({
  proyecto,
  onOpenProyectoModal,
}: ProyectoSelectorSectionProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground uppercase tracking-wide">
          Proyecto
        </h3>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onOpenProyectoModal}
          className="gap-2 h-9 rounded-lg"
        >
          <Search className="h-4 w-4" />
          {proyecto ? "Cambiar" : "Seleccionar"}
        </Button>
      </div>

      {proyecto ? (
        <div className="p-4 rounded-xl border border-border bg-card">
          <div className="space-y-2">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-semibold text-foreground">
                  {proyecto.denominacion}
                </p>
                <p className="text-sm text-muted-foreground">
                  {proyecto.public_id}
                </p>
              </div>
              <Badge variant="outline" className="ml-2">
                {proyecto.public_id}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {proyecto.direccion || "Sin dirección"}
              {proyecto.distrito && ` - ${proyecto.distrito}`}
            </p>

            {/* Entidad */}
            {proyecto.entidad && (
              <div className="flex items-center gap-2 mt-2 text-sm">
                <Building2 className="h-4 w-4 text-muted-foreground" />
                <span>{proyecto.entidad.nombre}</span>
                {proyecto.entidad.tipo && (
                  <span className="text-xs text-muted-foreground">
                    ({proyecto.entidad.tipo})
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center p-8 rounded-xl border border-dashed border-border">
          <div className="text-center">
            <AlertCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              No hay proyecto seleccionado
            </p>
            <Button
              type="button"
              variant="link"
              size="sm"
              onClick={onOpenProyectoModal}
              className="mt-1"
            >
              Seleccionar o crear proyecto
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
