# Arquitectura de Smart Fields y Desacoplamiento de UI

Este documento sirve como estándar de ingeniería para el equipo respecto a cómo manejar formularios dinámicos y acoplar componentes complejos (Smart Fields) dentro de la arquitectura de la aplicación, manteniendo una separación estricta entre la interfaz de usuario (UI) y la lógica de validación/estado.

---

## 1. Arquitectura Central (Core Architecture)

El sistema de formularios está construido sobre tres pilares interconectados: **Zod** (validación), **React Hook Form** (estado y rendimiento) y nuestros **Wrappers Declarativos** (UI).

### A. `GenericForm.tsx` (El Orquestador)
Este es el componente de nivel superior. No renderiza inputs directamente, sino que actúa como el cerebro del formulario:
- **Gestión de Estado Centralizada:** Inicializa `useForm` integrando el esquema de Zod (`zodResolver`).
- **Ciclo de Vida de los Datos:** Maneja valores por defecto (`initialData`), procesa y parsea los datos antes de enviarlos (ej. cast de strings a numbers o booleans) y normaliza payloads usando `buildUpdatePayload`.
- **Gestión de Interfaz de Nivel Alto:** Dibuja las secciones (`formSections` o agrupaciones simples mediante `GhostWrapper` o `CardWrapper`) y expone los `methods` para casos de delegación manual (`customFields` o el patrón render prop en `children`).

### B. `GenericInput.tsx` (El Despachador)
Es el puente entre el cerebro (`GenericForm`) y los inputs individuales:
- **Resolución de Componentes:** Infiere qué input instanciar basado en la propiedad `type` de la configuración llamando a `getInputComponent(field.type)`.
- **Estandarización Visual (`FieldWrapper`):** Envuelve incondicionalmente todos los inputs (excepto los de tipo "hidden" o "custom") con el `DefaultFieldWrapper`. Esto es vital porque centraliza el renderizado del `<Label>`, el texto de descripción, los asteriscos de campos requeridos y, lo más importante, **los mensajes de error**.

### C. `registry.ts` y `types.ts` (El Ecosistema)
Define el contrato de los componentes. Para que un componente exista en el ecosistema automático, debe mapearse en `inputRegistry`.

---

## 2. El Patrón "Smart Field"

En arquitecturas tradicionales, un componente complejo (como un uploader de archivos o un buscador asíncrono) tiende a mezclar reglas de validación, manejo de errores y lógica de negocio. 

El **Patrón Smart Field** requiere que un input actúe **únicamente como un adaptador bidireccional** entre la UI compleja y el estado subyacente de `react-hook-form`.

**¿Qué hace "Smart" a un campo bajo esta arquitectura?**
1. **Agnosticismo de Validación:** No contiene lógica de validación interna. No usa comprobaciones como `if (!file) throw Error`. Deja que el `GenericForm` bloquee el envío basándose enteramente en Zod.
2. **Conexión mediante `useController`:** Los componentes complejos que no pueden funcionar con un simple `register` de HTML utilizan el `control` inyectado para sincronizarse.
3. **Inyección de Errores Delegada:** Sabe que el `DefaultFieldWrapper` de `GenericInput` ya renderizará el texto de error de Zod bajo él, por lo que ignora su propio renderizado de errores si recibe la prop `hideErrorMessage`.

---

## 3. Guía Paso a Paso: Creación de un Nuevo Smart Component

Supongamos que necesitamos crear un campo generalizado para subir archivos (`SmartFileField`).

### Paso 1: Crear o Importar la UI Pura (Dumb Component)
Crea o utiliza un componente de diseño que no sepa nada del formulario (ej. un `<FileDropzone />` de tu librería UI). Este solo debe recibir `value` y `onChange`.

### Paso 2: Crear la Capa Adaptadora
Crea un archivo nuevo en `frontend/src/components/genericForm/inputs/InputFile.tsx`.

```tsx
import { useController } from "react-hook-form";
import type { InputComponentProps } from "./types";
import { FileDropzone } from "@/components/ui/file-dropzone"; 

export const InputFile: React.FC<InputComponentProps> = ({
  field,
  control,
  id,
  hideErrorMessage, // Provisto por GenericInput
  error
}) => {
  // Conexión principal con React Hook Form usando el "control"
  const { field: rhfField } = useController({
    name: field.name,
    control,
  });

  return (
    <FileDropzone 
      id={id}
      file={rhfField.value} 
      onFileChange={rhfField.onChange} // Inyecta el archivo de vuelta al formulario
      onBlur={rhfField.onBlur}
      disabled={field.disabled}
      placeholder={field.placeholder}
      // Delegamos la interfaz de error visual al componente si tiene un flag visual, 
      // pero evitamos imprimir el texto del error porque el Wrapper ya lo hace.
      hasError={!!error}
    />
  );
};
```

### Paso 3: Ampliar las Capacidades (Opcional)
Si tu campo `InputFile` necesita parámetros especiales (por ejemplo, `maxSizeMb` o `allowedFormats`), deberás agregar esas propiedades opcionales a la interfaz `FieldConfig` en `types.ts` para mantener el tipado estricto.

---

## 4. Integración: ¿Registro Global vs. Custom Fields?

Una vez creado tu Smart Component, ¿cómo lo conectas al `GenericForm`? Tienes dos enfoques arquitectónicos:

### Enfoque A: Registro Global (`registry.ts`)
*Cuándo usar:* Cuando el Smart Field es genérico (fecha, archivo, número de teléfono, editor de texto) y se utilizará en múltiples lugares de la aplicación.
1. Añade tu nuevo tipo al string union `FieldType` en `GenericInput.tsx` (ej. `"file"`).
2. Entra a `registry.ts`, importa tu componente y añádelo al objeto:
   ```ts
   export const inputRegistry: Record<string, InputComponent> = {
     // ...
     file: InputFile, 
   };
   ```
3. Utilízalo directamente en cualquier configuración: `{ type: "file", name: "avatar", label: "Tu Foto" }`.

### Enfoque B: Inyección Externa (`customFields`)
*Cuándo usar:* Cuando el Smart Field es una entidad de dominio hiper-específica y acoplada que solo existe para un módulo (ej. `SelectorDeEntidadesGubernamentales`). No contamines el registro global con componentes de dominio.
1. Configura el campo con `type: "custom"`. Esto le dice a `GenericInput` que ignore la inyección estandarizada.
2. Intercepta el render en el orquestador:
   ```tsx
   <GenericForm
     schema={schema}
     fields={[{ name: "gobernacionId", type: "custom", label: "Entidad" }]}
     customFields={{
       gobernacionId: (methods) => (
         // methods nos da acceso full a watch, control y setValue
         <MyDomainSpecificSelector control={methods.control} />
       )
     }}
   />
   ```
*Nota importante:* Al usar `customFields`, el componente renderizado salta el `DefaultFieldWrapper`. Si deseas labels y errores, deberás incluir la estructura de grid y tipografía tú mismo dentro de la función de render.

---

## 5. Mejores Prácticas y Reglas Duras

1. **La Verdad Reside en Zod:** Nunca hardcodees en tu `InputXxx.tsx` validaciones como `maxLength = 20`. Tu componente se debe limitar a pasar datos. Zod evaluará si es válido y retornará el error.
2. **Cuidado con el Ciclo de Renderizado:** Usar `watch()` indiscriminadamente dentro de un Smart Component global o dentro del `GenericForm` causará renders de toda la pantalla en cada tecleo. Los Smart Components deben depender de `useController` o `useWatch` localmente solo para el dato específico que les interesa.
3. **No Duplicar Errores:** `GenericInput` fue diseñado para aislar los mensajes de error. Tu Smart Component debe aceptar la prop `hideErrorMessage` y **no** renderizar párrafos de error si el Wrapper ya lo está haciendo (por defecto). Solo debe aplicar clases visuales de error (ej. bordes rojos).
4. **Serialización Pre-Envío:** Si tu Smart Component produce datos complejos (como una instancia `File`, un array de objetos o fechas primitivas de JS), debes asegurarte de que la limpieza en el método `handleFormSubmit` en `GenericForm.tsx` (donde se itera sobre los keys y se aplican conversiones de tipo basándose en `fieldConfig.type`) esté configurada para respetar y no destruir el formato que tu API espera.
