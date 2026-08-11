/**
 * Tipos para Contacto inline en liquidaciones edificaciones.
 */

export interface ContactoInline {
  /** Local identifier for editing (NOT sent to backend) */
  localId?: string;
  nombres: string;
  apellidos: string;
  dni?: string;
  telefono?: string;
  celular?: string;
  email?: string;
  cargo?: string;
  direccion?: string;
  descripcion?: string;
  principal?: boolean;
}
