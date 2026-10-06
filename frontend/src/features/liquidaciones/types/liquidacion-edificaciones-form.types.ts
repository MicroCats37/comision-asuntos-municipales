/**
 * Tipos para el formulario de Liquidación Edificaciones.
 * Re-exportado para compatibilidad con componentes de entidades.
 */
import type { EntidadResult } from "@/features/entidades/types/entidad";

export interface InstitucionFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: (entidad: EntidadResult) => void;
}

export interface PersonaNaturalFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: (entidad: EntidadResult) => void;
}
