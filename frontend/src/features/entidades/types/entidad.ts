/**
 * Tipos para Entidad — API contracts.
 */

export interface EntidadInstitucion {
  tipo_documento: "RUC";
  numero_documento: string;
  razon_social: string;
  nombre_comercial?: string;
  direccion?: string;
  distrito_id?: string;
}

export interface EntidadPersonaNatural {
  tipo_documento: "DNI";
  numero_documento: string;
  nombres: string;
  apellidos: string;
  direccion?: string;
  distrito_id?: string;
}

export type EntidadInput = EntidadInstitucion | EntidadPersonaNatural;

export interface EntidadResult {
  id: string;
  tipo_documento: string;
  numero_documento: string;
  razon_social?: string;
  nombres?: string;
  apellidos?: string;
  nombre_completo: string;
  direccion?: string;
  distrito_id?: string;
  activo: boolean;
  creado?: boolean; // Only present in upsert responses, not in buscar response
}
