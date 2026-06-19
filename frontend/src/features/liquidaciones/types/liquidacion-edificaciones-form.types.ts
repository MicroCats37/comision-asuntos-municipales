/**
 * Tipos para el formulario de Liquidación Edificaciones.
 */
import type { EntidadResult } from "@/features/entidades/types/entidad";
import type { ProyectistaResult } from "./proyectista";
import type { RevisionVigente } from "./revisiones-vigentes";
import type { TipoTramiteEdificaciones, VariablesFinancieras } from "./liquidacion-edificaciones";

// ── Entidad Simple (matches backend ProyectoSerializer response) ─────────────

export interface EntidadSimple {
  id: string | null;
  tipo: string | null;
  nombre: string | null;
}

// ── Proyecto ────────────────────────────────────────────────────────────────

export interface ProyectoResumen {
  id: string;
  public_id: string;
  denominacion: string;
  direccion: string;
  distrito?: string;
  distrito_id?: string;
  entidad?: EntidadSimple;
}

// ── Form State ──────────────────────────────────────────────────────────────

export interface LiquidacionEdificacionFormState {
  municipalidad_id: string;
  tipo_tramite: TipoTramiteEdificaciones | "";
  valor_proyecto: number;
  observacion: string;
  revisiones_ids: string[];
  proyectistas_ids: string[];
  proyecto?: ProyectoResumen;
}

// ── Form Schema Type ────────────────────────────────────────────────────────

export interface LiquidacionEdificacionSubmitData {
  proyecto_public_id: string;
  municipalidad_id: string;
  tipo_tramite: TipoTramiteEdificaciones;
  valor_proyecto: number;
  observacion?: string;
  revisiones_ids: string[];
  proyectistas_ids: string[];
}

// ── Props Interfaces ────────────────────────────────────────────────────────

export interface VariablesFinancierasCardProps {
  variables?: VariablesFinancieras;
  isLoading?: boolean;
}

export interface RevisionesVigentesTableProps {
  revisiones: RevisionVigente[];
  selectedIds: string[];
  onToggleRevision: (id: string) => void;
  isLoading?: boolean;
}

export interface ProyectoSelectorSectionProps {
  proyecto?: ProyectoResumen;
  onOpenProyectoModal: () => void;
}

export interface LiquidacionEdificacionFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

// ── Child Modal Props ───────────────────────────────────────────────────────

export interface ProyectoFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: (proyecto: ProyectoResumen) => void;
}

export interface ProyectistaFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: (proyectista: ProyectistaResult) => void;
}

export interface EntidadFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: (entidad: EntidadResult) => void;
}

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
