# Hoja de Ruta: Reconstrucción del Frontend (components-app)

Al mover `components-app` a `components-app-deprecated`, hemos roto intencionalmente la aplicación para forzar una reconstrucción limpia. Esta es la hoja de ruta estricta (por niveles de dependencia) para volver a levantar la app pieza por pieza.

## Nivel 0: La Base Absoluta (Estado: ✅ LIMPIO)
- Los archivos `app/layout.tsx` y `app/page.tsx` (el home público) **no tienen dependencias** de `components-app`. 
- No hay que hacer nada aquí. El enrutador base de Next.js está intacto.

## Nivel 1: App Shell (Estado: 🚨 BLOQUEO CRÍTICO)
El archivo `app/(protected)/layout.tsx` (que envuelve TODA la aplicación privada) importa directamente `ProtectedSidebar`. Hasta que esto no exista, toda la app mostrará un error.

**Paso 1: Reconstruir el Sidebar**
- **Archivo:** `components-app/sidebar/ProtectedSidebar.tsx`
- **Dependencias:** `useAuthStore` (que decidimos reconstruir), componentes de UI genéricos (`Shadcn`) y hooks de móvil.
- **Acción:** Traer el diseño del deprecated, pero asegurándonos de que la lógica de navegación y los items del menú (Edificaciones, Taludes, etc.) estén bien estructurados.

## Nivel 2: Wrappers Core de Formularios (Prioridad: ALTA)
Estos son los componentes que 13, 8 y 6 archivos de `liquidaciones` respectivamente están pidiendo a gritos.

**Paso 2: Reconstruir FormSectionHeader**
- **Archivo:** `components-app/forms/FormSectionHeader.tsx`
- Simplemente un componente visual para dividir secciones. Muy rápido de hacer.

**Paso 3: Reconstruir AppFormModal**
- **Archivo:** `components-app/forms/AppFormModal.tsx`
- Este es el wrapper que une el `GenericModal` con el `GenericForm`. Es el núcleo de casi todos tus formularios (13 componentes lo usan).
- **Acción:** Reconstruirlo limpio, asegurando que expone correctamente los `customFields` para nuestra nueva arquitectura de Smart Fields.

**Paso 4: Reconstruir AppStepperFormModal**
- **Archivo:** `components-app/forms/AppStepperFormModal.tsx`
- Usado por los 6 tipos de liquidaciones para sus flujos de múltiples pasos. 
- **Acción:** Traer la lógica del stepper, pero asegurando que la validación y el estado se manejen limpiamente.

## Nivel 3: Features de Dominio (Prioridad: BAJA / A DEMANDA)
Componentes que estaban en la carpeta vieja pero que **NADIE** está importando actualmente en la app. No vamos a perder tiempo reconstruyéndolos hasta que una pantalla realmente los necesite:
- `ModalShell.tsx` (0 usos)
- `MultiPartFormStepper.tsx` (0 usos - componente masivo y complejo)
- `AppDataTable.tsx` (0 usos)
- `StatsArea.tsx` (0 usos - de hecho, parece tener textos hardcodeados de otro proyecto)

---

## Conclusión

El orden de trabajo obligatorio es:
1. Reconstruir `ProtectedSidebar` (Levanta la app).
2. Reconstruir `AppFormModal` y `FormSectionHeader` (Levanta los formularios simples).
3. Reconstruir `AppStepperFormModal` (Levanta los flujos de liquidación).
4. Proceder a aplicar el nuevo patrón de Smart Fields dentro de los dominios (`edificaciones`, etc.).