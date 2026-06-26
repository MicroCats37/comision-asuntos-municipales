/**
 * Tipos para Proyectista — API contracts.
 */

/**
 * Ingeniero habilitado response from GET /ingenieros/habilitados/{cip}
 */
export interface IngenieroHabilitado {
  cip: string;
  nombres: string;
  apellidos: string;
  habilitado: boolean;
  capitulo: string | null;
}

/**
 * Inline proyectista for form state and submit.
 * Display fields (nombres, apellidos, habilitado, capitulo) are for UI only.
 * Submit payload only includes cip, especialidad_id, and optional descripcion.
 */
export interface ProyectistaInline {
  cip: string;
  especialidad_id: string;
  descripcion?: string;
  // Display fields (UI only, not sent to backend)
  nombres?: string;
  apellidos?: string;
  habilitado?: boolean;
  capitulo?: string | null;
}

export interface ProyectistaInput {
  nombres: string;
  apellidos: string;
  cip?: string;
  dni?: string;
  cap?: string;
}

export interface ProyectistaResult {
  id: string;
  nombres: string;
  apellidos: string;
  cip?: string;
  dni?: string;
  cap?: string;
  creado: boolean;
}
