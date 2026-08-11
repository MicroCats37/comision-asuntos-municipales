/**
 * Tipos para Revisiones Vigentes — API contracts.
 */

export interface EspecialidadBasica {
  id: string;
  nombre: string;
}

export interface RevisionVigente {
  id: string;
  especialidades: EspecialidadBasica[];
  tarifa_id: string;
  porcentaje_liquidacion: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number;
  habilitada: boolean;
}

export interface RevisionesVigentesResponse {
  revisiones: RevisionVigente[];
}
