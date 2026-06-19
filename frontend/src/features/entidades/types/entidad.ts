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

// ── SUNAT/RENIEC Lookup Response Types ─────────────────────────────────────────

export interface InstitucionSunatResponse {
  ruc: string;
  razon_social: string;
  nombre_comercial?: string;
  estado: string;
  tipo_contribuyente?: string;
  direccion?: string;
  departamento?: string;
  provincia?: string;
  distrito?: string;
}

export interface PersonaReniecResponse {
  dni: string;
  nombres: string;
  apellidos: string;
  nombre_completo: string;
  genero?: string;
  fecha_nacimiento?: string;
  direccion?: string;
  ubigeo?: string;
}
