/**
 * Tipos para Proyectista — API contracts.
 */

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
