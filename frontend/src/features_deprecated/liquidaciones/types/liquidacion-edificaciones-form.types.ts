/**
 * Tipos para el formulario de Liquidación Edificaciones.
 */
import type { EntidadResult } from "@/features/entidades/types/entidad";
import type { ContactoInline } from "./contacto";
import type {
  TipoTramiteEdificaciones,
  VariablesFinancieras,
} from "./liquidacion-edificaciones";
import type { ProyectistaInline, ProyectistaResult } from "./proyectista";
import type { RevisionVigente } from "./revisiones-vigentes";

// ── Entidad Simple (matches backend ProyectoSerializer response) ─────────────

export interface EntidadSimple {
  id: string | null;
  tipo: string | null;
  nombre: string | null;
}

// ── Entidad Inline for proyecto_inline ─────────────────────────────────────

export interface EntidadInlineSubmit {
  tipo_documento: string;
  numero_documento: string;
  razon_social: string;
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
  expediente: string;
  valor_base_calculo: number;
  observacion: string;
  revisiones_ids: string[];
  proyectistas: ProyectistaInline[];
  contactos: ContactoInline[];
  delegados_ids: string[];
  proyecto?: ProyectoResumen;
}

// ── Form Schema Type ────────────────────────────────────────────────────────

// Proyecto Inline para crear proyecto al vuelo
export interface ProyectoInlineSubmit {
  denominacion: string;
  direccion?: string;
  distrito_id?: string;
  nombre_propietario: string;
  entidad: EntidadInlineSubmit;
}

export interface LiquidacionEdificacionSubmitData {
  // XOR: uno de los dos es requerido
  proyecto_public_id?: string;
  proyecto_inline?: ProyectoInlineSubmit;
  municipalidad_id: string;
  tipo_tramite: TipoTramiteEdificaciones;
  valor_proyecto: number;
  expediente?: string;
  valor_base_calculo?: number;
  observacion?: string;
  revisiones_ids: string[];
  proyectistas: ProyectistaInline[];
  contactos: ContactoInline[];
  // delegadas_ids fue eliminado del payload de creación
  // tarifas_ids es opcional para compatibilidad con formularios deprecated
  tarifas_ids?: string[];
}

// ── Props Interfaces ────────────────────────────────────────────────────────

export interface VariablesFinancierasCardProps {
  variables?: VariablesFinancieras;
  isLoading?: boolean;
}

export interface RevisionesVigentesTableProps {
  revisiones: RevisionVigente[];
  selectedId: string | null;
  onSelectRevision: (id: string) => void;
  isLoading?: boolean;
  lockedIds?: string[];
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
  onSaved: (proyectista: ProyectistaInline) => void;
  /** Available especialidades from revisiones vigentes */
  especialidadOptions?: Array<{ label: string; value: string }>;
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

export interface ContactoFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: (contacto: ContactoInline) => void;
  /** Initial data to pre-fill the form (for edit mode) */
  initialData?: ContactoInline;
}
