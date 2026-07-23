// genericForm/inputs/registry.ts
// Registro central de todos los inputs disponibles

import { FormattedNumberInput } from "./FormattedNumberInput";
import { InputCheckbox } from "./InputCheckbox";
import { InputDatePicker } from "./InputDatePicker";
import { InputFormattedNumber } from "./InputFormattedNumber";
import { InputHidden } from "./InputHidden";
import { InputImage } from "./InputImage";
import { InputNumber } from "./InputNumber";
import { InputPassword } from "./InputPassword";
import { InputRadio } from "./InputRadio";
import { InputSearchableSelect } from "./InputSearchableSelect";
import { InputSelect } from "./InputSelect";
// Inputs básicos
import { InputText } from "./InputText";
import { InputTextarea } from "./InputTextarea";
import type { InputComponent } from "./types";

/**
 * Registry de inputs disponibles.
 * Para agregar un nuevo tipo de input:
 * 1. Crear el componente en esta carpeta (InputXxx.tsx)
 * 2. Importarlo aquí
 * 3. Agregarlo al objeto inputRegistry
 *
 * El tipo (key) debe coincidir con field.type en la configuración del formulario.
 */
export const inputRegistry: Record<string, InputComponent> = {
  // Básicos
  text: InputText,
  number: InputNumber,
  textarea: InputTextarea,
  password: InputPassword,

  // Selección
  select: InputSelect,
  "searchable-select": InputSearchableSelect,
  radio: InputRadio,
  checkbox: InputCheckbox,

  // Oculto
  hidden: InputHidden,

  // Avanzados (requieren dependencias adicionales)
  date: InputDatePicker,
  image: InputImage,

  // Formatted
  "formatted-number": InputFormattedNumber,
};

/**
 * Obtiene el componente de input del registry.
 * Si no existe, retorna InputText como fallback.
 */
export const getInputComponent = (type: string): InputComponent => {
  const component = inputRegistry[type];

  if (!component) {
    console.warn(
      `Input type "${type}" not found in registry. Using InputText as fallback.`,
    );
    return InputText;
  }

  return component;
};

/**
 * Registra un nuevo tipo de input en runtime.
 * Útil para plugins o inputs personalizados a nivel de app.
 */
export const registerInput = (
  type: string,
  component: InputComponent,
): void => {
  if (inputRegistry[type]) {
    console.warn(
      `Input type "${type}" already exists and will be overwritten.`,
    );
  }
  inputRegistry[type] = component;
};
