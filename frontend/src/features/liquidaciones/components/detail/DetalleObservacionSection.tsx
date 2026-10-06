"use client";

import { AlertCircle } from "lucide-react";
import { DetalleSection } from "./DetalleSection";

interface Props {
  observacion: string | null | undefined;
}

export function DetalleObservacionSection({ observacion }: Props) {
  if (!observacion || !observacion.trim()) return null;

  return (
    <DetalleSection
      title="Observacion"
      icon={AlertCircle}
      className="lg:col-span-12"
    >
      <div className="flex items-start gap-2.5 px-1 py-1">
        <AlertCircle className="h-4 w-4 text-warning shrink-0 mt-0.5" />
        <p className="text-sm text-foreground/90 leading-relaxed [text-wrap:pretty]">
          {observacion}
        </p>
      </div>
    </DetalleSection>
  );
}
