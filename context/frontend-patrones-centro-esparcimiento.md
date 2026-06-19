# Patrones Frontend - Centro de Esparcimiento

## Resumen Ejecutivo

Este documento registra los patrones observados en el proyecto frontend de referencia (`centro-de-esparcimiento`) para servir como contrato y guía de implementación en el proyecto CAM.

---

## 1. Stack Tecnológico

### Framework y Runtime
- **Framework**: Next.js 16.2.1 (App Router)
- **Runtime**: React 19.2.4
- **Language**: TypeScript 5
- **Package Manager**: npm

### Librerías Principales

| Categoría | Librería | Versión |
|-----------|----------|---------|
| UI Components | shadcn + radix-ui | 4.x / 1.4.x |
| Formularios | react-hook-form + zod | 7.72 / 4.3 |
| Validación | @hookform/resolvers | 5.2 |
| Estado Global | zustand | 5.0 |
| Fetching | axios + @tanstack/react-query | 1.14 / 5.95 |
| UI Utils | class-variance-authority, clsx, tailwind-merge | 0.7 / 2.1 / 3.5 |
| Carousel | embla-carousel-react | 8.6 |
| Drag & Drop | @dnd-kit/core + sortable | 6.3 / 10.0 |
| Notifications | sonner (toasts) | 2.0 |
| Auth | cookies-next + JWT manual | 6.1 |
| Dates | date-fns | 4.1 |

### Estructura de App/Router

```
src/app/
├── (protected)/           # Rutas protegidas por auth
│   ├── admin/            # Dashboard admin
│   │   ├── bungalows/   # Admin bungalows + tarifas
│   │   ├── entradas/
│   │   ├── usuarios/
│   │   └── layout.tsx   # Server Component - check admin role
│   ├── cliente/          # Dashboard cliente
│   ├── dashboard/
│   └── layout.tsx        # Server Component - check auth + wrap sidebar
├── api/auth/             # Route handlers (refresh, logout)
│   ├── refresh/route.ts  # 'use server' - proxy refresh token
│   └── logout/route.ts
└── login/
```

---

## 2. Patrón Admin Bungalows

### Ubicación de Archivos

```
src/app/(protected)/admin/bungalows/page.tsx  → importa BungalowsView
src/features/bungalows/
├── views/BungalowsView.tsx           # Page component (state management)
├── components/
│   ├── BungalowFormModal.tsx        # Create/Edit modal
│   ├── BungalowGalleryEditor.tsx    # Image gallery modal
│   ├── BungalowCardGrid.tsx         # Card grid display
│   └── BungalowFilters.tsx           # Search/filter controls
├── hooks/useBungalows.ts            # React Query hooks
├── hooks/useBungalowMutations.ts    # Mutations (create/update/delete)
├── schemas/bungalow.schema.ts       # Zod schemas + types
└── services/                        # API calls (optional layer)
```

### Flujo de Datos

1. **Page Component** (`BungalowsView.tsx`):
   - Gestiona estado de modales (`formState`, `galleryOpen`)
   - Contiene lógica de discriminated union para modal create/edit
   - Pasa datos a componentes hijos
   - NO hace fetching directo - usa hooks

2. **Hooks** (`useBungalows.ts`):
   - React Query para fetching/caching
   - `useBungalowsCompletos()` - lista con imágenes
   - `useBungalowMutations` - create, update, delete

3. **Modal Components**:
   - Reciben datos y callbacks como props
   - Manejan提交 lógica interna
   - Llaman a `onOpenChange(false)` en éxito

### Discriminated Union State Pattern

```typescript
// BungalowsView.tsx - Líneas 21-24
type BungalowFormState =
  | { mode: "closed" }
  | { mode: "create" }
  | { mode: "edit"; bungalowId: string };

// El estado 'mode' es la fuente de verdad, nunca derivado de datos
// Esto previene el "flicker" del modal edit→create durante animación de cierre
```

---

## 3. Problema: Modal Dentro de Modal (Nested Modals)

### Dónde Ocurre

El problema existe en `TarifaMatrixEditorModal` y sus secciones:

```
TarifaMatrixEditorModal (modal padre)
├── NocheCard
│   └── TarifaNocheSectionEditor (modal hijo)
│       └── AppFormModal → GenericModal → Radix Dialog
├── DiasCard
│   ├── TarifaDiasSectionEditor (modal hijo)
│   ├── TarifaPrecioCapacidadSectionEditor (modal hijo)
│   └── TarifaOverrideBungalowSectionEditor (modal hijo)
```

**Archivos afectados:**
- `src/features/bungalows/tarifas/components/TarifaMatrixEditorModal.tsx`
- `src/features/bungalows/tarifas/components/TarifaNocheSectionEditor.tsx`
- `src/features/bungalows/tarifas/components/TarifaDiasSectionEditor.tsx`
- `src/features/bungalows/tarifas/components/TarifaPrecioCapacidadSectionEditor.tsx`
- `src/features/bungalows/tarifas/components/TarifaOverrideBungalowSectionEditor.tsx`

### Componentes Involucrados

1. **`AppFormModal`** (`src/components-app/forms/AppFormModal.tsx`):
   - Envuelve `GenericModal`
   - Props: `open`, `onOpenChange`, `preventClose`, etc.

2. **`GenericModal`** (`src/components/genericModal/GenericModal.tsx`):
   - Usa Radix UI `Dialog`
   - Compound components: `Content`, `Header`, `Body`, `Footer`, `CloseX`
   - Context interno `GenericModalContext` para comunicación deep

3. **Radix UI `Dialog`**:
   - Maneja overlay, content, focus trap, accessibility
   - `onOpenChange` se dispara en escape/overlay click

### Por Qué Cierre Hijo Puede Cerrar Padre

**CAUSA RAÍZ**: Cada `GenericModal` crea su propio `Dialog` de Radix. Cuando hay múltiples Dialogs abiertos:

1. El Dialog hijo tiene `open=true` y se rendered encima del padre
2. El overlay del Dialog hijo está activo
3. El overlay del Dialog padre sigue activo (nunca se "pausó")
4. **El problema**: Si hay un bug en el cierre del hijo o si el hijo no previene el cierre adecuado, el evento puede "bubble up" o el focus trap puede interferir

**En la implementación actual:**
- `GenericModal` (línea 121): `<Dialog open={isOpen} onOpenChange={handleOpenChange}>`
- `handleClose` (línea 75-87) tiene interceptor `onBeforeClose`
- `preventClose` (línea 66) puede bloquear cierre pero no afecta al padre

**El flujo problemático:**
```
Hijo cierra → onOpenChange(false) → setState en hijo → re-render
                                              ↓
                                    ¿El estado del padre se afecta?
```

En teoría no debería afectar... pero el problema real es probablemente que:
1. El overlay del hijo tiene `onPointerDownOutside` que previene cierre accidental
2. PERO: al cerrar el hijo, el foco vuelve al trigger del padre
3. Si el trigger del padre ya no existe (ej: cambió de estado), puede causar comportamiento inesperado

### Patrón Genérico Recomendado

**OPCIÓN 1: Contained Inline Editors (RECOMENDADO)**
- NO usar modales dentro de modales
- Usar "inline editing" o "expandable rows"
- El modal padre tiene una sección colapsable que abre el editor dentro del mismo modal

```typescript
// BAD: Nested modals
<ModalParent open={parentOpen} onOpenChange={setParentOpen}>
  <NocheCard>
    <Button onClick={() => setEditorOpen(true)}>Editar</Button>
    <ModalChild open={editorOpen} onOpenChange={setEditorOpen} />
  </NocheCard>
</ModalParent>

// GOOD: Inline expansion
<ModalParent open={parentOpen} onOpenChange={setParentOpen}>
  <NocheCard>
    {expanded ? (
      <InlineNocheEditor onSave={handleSave} onCancel={() => setExpanded(false)} />
    ) : (
      <Button onClick={() => setExpanded(true)}>Editar</Button>
    )}
  </NocheCard>
</ModalParent>
```

**OPCIÓN 2: Stepper/Wizard dentro del mismo modal**
- Si necesitas flujo de múltiples pasos, maneja estados internos

**OPCIÓN 3: Dialog anidado con disableOutsideEvents**
- Radix Dialog tiene `disableOutsideEvents` y `onInteractOutside`
- Pero esto no previene completamente el problema de cierre

### Solución Implementada en el Frontend Referencia

**NO USAN modales anidados directamente** - pero hay un近似:

En `TarifaMatrixEditorModal`, los section editors (`TarifaNocheSectionEditor`, etc.) SON modales separados que se renderizan dentro del modal padre. Esto funciona porque:

1. El modal padre (`TarifaMatrixEditorModal`) es `AppFormModal` → `GenericModal`
2. Los modales hijos (`TarifaNocheSectionEditor`) son `AppFormModal` → `GenericModal`
3. **CUALQUIER modales hijos heredan el stacking context de Radix**
4. El problema no se ha "solucionado", solo no se reporta como bug todavía

**Recomendación para CAM**: Implementar inline editing pattern en vez de modales anidados.

---

## 4. Patrones de Componentes/Formularios

### Separación Page/Container/Components

```
View (page component)     → Estado local + callbacks + render
├── Filters              → Componente presentación
├── CardGrid             → Componente presentación
├── FormModal            → Lógica de formulario + UI
│   └── GenericForm      → Librería de formulario genérica
└── GalleryEditor        → Componente con lógica específica
```

### Form Library Stack

- **react-hook-form**: Manejo de form state
- **zod**: Esquemas de validación
- **@hookform/resolvers**: Integración zod + rhf
- **GenericForm** (`src/components/genericForm/GenericForm.tsx`): Wrapper reutilizable

### Componentes UI Principales

| Componente | Ubicación | Descripción |
|------------|-----------|-------------|
| `GenericModal` | `@/components/genericModal/GenericModal` | Modal compound con Context |
| `AppFormModal` | `@/components-app/forms/AppFormModal` | FormModal wrapper con GenericModal |
| `GenericForm` | `@/components/genericForm/GenericForm` | Form builder genérico |
| `AppDataTable` | `@/components-app/tables/AppDataTable` | Tabla con sorting/pagination |
| `Button` | `@/components/ui/button` | shadcn Button |
| `Input` | `@/components/ui/input` | shadcn Input |
| `Label` | `@/components/ui/label` | shadcn Label |
| `Carousel` | `@/components/ui/carousel` | embla carousel wrapper |

### GenericForm Props

```typescript
interface GenericFormProps<T extends FieldValues> {
  formId?: string;
  schema: ZodType<T>;
  initialData?: DefaultValues<T>;
  fields?: FormField[];                    // Definición declarativa
  formSections?: FormSection[];            // Secciones agrupadas
  customFields?: Record<string, (methods) => ReactNode>; // Custom render
  onSubmit: (data: T) => unknown;
  isLoading?: boolean;
  isDisabled?: boolean;
  showErrorsAsToasts?: boolean;
  onFieldChange?: (fieldName: string, value: unknown) => void;
  skipFooter?: boolean;                    // Para usar en modales
  children?: (props: FormChildrenProps<T>) => ReactNode; // Render prop
}
```

### Manejo de Errores/Loading/Toasts

**Errores:**
- `handleApiError` (`src/errors/index.ts`) - utility centralizado
- Errores de formulario se muestran inline
- Errores de mutations se muestran como toasts (sonner)

**Loading:**
- `isPending` en mutations para deshabilitar inputs
- Skeleton loaders en grids/cards
- Spinner en botones (primaryLoading)

**Toasts:**
```typescript
import { toast } from "sonner";
toast.success("Bungalow creado");
toast.error("Error al crear bungalow");
```

---

## 5. Patrón Auth Frontend

### NO usa Server Actions ('use server') para login

El proyecto usa una estrategia híbrida:

1. **Route Handlers** (`/api/auth/*`) con `'use server'`:
   - `POST /api/auth/refresh` - Refresca access token via refresh cookie
   - `POST /api/auth/logout` - Limpia cookies

2. **Cliente directo a backend**:
   - Login (`useLogin` hook) → llama `POST /auth/login` directamente
   - No usa server action para login

### Flujo de Auth

```
1. Login Page
   └── useLogin() mutation
       ├── POST /auth/login { cip, password }  → access_token + refresh_token
       ├── GET /auth/me { Bearer token }     → user data
       └── cookies-next: setCookie()          → guarda tokens client-side

2. API Calls (axios interceptor)
   └── api.interceptors.request
       ├── Lee token de cookie
       ├── Si expira pronto → POST /api/auth/refresh
       └── Añade Authorization header

3. Protected Routes (Server Components)
   └── (protected)/layout.tsx
       └── getUserSession() (lib/auth/actions.ts - 'use server')
           └── Lee USER_SESSION cookie
           └── Si no existe → redirect("/login")

4. Admin Protection
   └── admin/layout.tsx
       └── getUserSession() + isAdmin(user)
```

### Archivos de Auth

```
src/features/auth/
├── services/auth.service.ts      # Funciones API (login, getMe, etc.)
├── store/auth.store.ts          # Zustand stores (user, registro, recuperar)
├── hooks/useLogin.ts            # Mutation hook - login flow
├── hooks/useLogout.ts          # Mutation hook - logout
├── schemas/auth.types.ts       # Tipos TypeScript
├── schemas/auth.schema.ts      # Zod schemas
└── views/
    ├── LoginView.tsx           # Componente de login
    ├── LoginClientShell.tsx    # Shell con branding
    └── ...

src/lib/auth/
├── actions.ts                  # 'use server' - setAuthCookies, getUserSession, etc.
├── cookies.ts                  # Constantes de cookies + opciones
├── roles.ts                    # isAdmin, isCliente, hasRole
└── index.ts                   # Exports

src/app/api/auth/
├── refresh/route.ts           # 'use server' - proxy refresh
└── logout/route.ts            # 'use server' - logout
```

### Tipos de Auth

```typescript
interface MeResponse {
  id: number;
  cip: string;
  nombre: string;
  apellido: string;
  roles: string[];  // ['ADMIN'], ['CLIENTE'], etc.
}

interface BackendLoginResponse {
  access_token: string;
  refresh_token: string;
  expires_at: string;
}
```

### Cookies Auth

```typescript
// src/lib/auth/cookies.ts
export const AUTH_COOKIES = {
  ACCESS_TOKEN: "auth_access_token",
  REFRESH_TOKEN: "auth_refresh_token",
  EXPIRES_AT: "auth_expires_at",     // Client-readable expiry
  USER_SESSION: "auth_user_session",  // JSON user data
};

// Todas non-httpOnly para acceso desde cliente
// httpOnly=true solo en route handlers server-side
```

### Protección de Rutas Admin

```typescript
// src/app/(protected)/admin/layout.tsx
export default async function AdminLayout({ children }) {
  const user = await getUserSession(); // 'use server' - lee cookies server-side

  if (!user) {
    redirect("/login");
  }

  if (!isAdmin(user)) {
    redirect("/cliente/inicio");
  }

  return <>{children}</>;
}
```

---

## 6. Componentes Reutilizables Detectados

### Componentes de App (components-app/)

```
src/components-app/
├── forms/
│   ├── AppFormModal.tsx      # Modal con formulario integrado
│   └── ModalShell.tsx        # Shell para modales custom
├── tables/
│   └── AppDataTable.tsx      # Tabla con TanStack Table
├── pages/
│   ├── StatsArea.tsx         # Área de estadísticas
│   ├── RichEmptyState.tsx    # Estado vacío fancy
│   └── MemberCardSkeleton.tsx
└── backgrounds/
    └── CampestreBackground.tsx
```

### Componentes UI (shadcn)

```
src/components/ui/
├── button.tsx
├── input.tsx
├── label.tsx
├── dialog.tsx           # Radix Dialog wrapper
├── sheet.tsx           # Radix Sheet (slide-over)
├── dropdown-menu.tsx
├── select.tsx
├── calendar.tsx         # react-day-picker
├── carousel.tsx         # embla wrapper
├── scroll-area.tsx      # Radix ScrollArea
└── ...
```

### Componentes Genéricos

```
src/components/genericModal/
├── GenericModal.tsx         # Modal compound components
└── GenericModal.types.ts    # Tipos TypeScript

src/components/genericForm/
├── GenericForm.tsx          # Form builder
└── GenericInput.tsx         # Input field components
```

---

## 7. Recomendaciones para Contrato Frontend CAM

### Estructura de Carpetas Sugerida

```
src/
├── app/                    # Next.js App Router
│   ├── (protected)/       # Rutas protegidas
│   │   ├── admin/        # Admin pages
│   │   └── cliente/      # Cliente pages
│   ├── api/              # Route handlers si needed
│   └── login/            # Login page
├── components/
│   ├── ui/               # shadcn components
│   ├── genericModal/     # Modal system
│   ├── genericForm/      # Form system
│   └── app/              # App-level components
├── features/             # Feature modules
│   ├── auth/
│   ├── bungalows/
│   └── ...
├── hooks/                # Custom hooks
├── lib/                  # Utilities
│   ├── api.ts           # Axios instance + interceptors
│   ├── auth/            # Auth utilities
│   └── utils.ts         # cn() and helpers
├── schemas/             # Zod schemas
└── types/               # TypeScript types
```

### Patrones a Seguir

1. **Discriminated Union para Modal State**:
   ```typescript
   type ModalState =
     | { mode: "closed" }
     | { mode: "create" }
     | { mode: "edit"; id: string };
   ```

2. **Persisted Selected ID**:
   ```typescript
   const [selectedId, setSelectedId] = useState<string | null>(null);
   // Mantener ID cuando mode="closed" para evitar flicker en animación
   ```

3. **Explicit Mode Prop en Modals**:
   ```typescript
   interface FormModalProps {
     mode: "create" | "edit";  // NO derivar de data
     data?: SomeData;
   }
   ```

4. **NO Modales Anidados** - Usar inline editing o steppers

5. **Server Components para Auth Check**:
   ```typescript
   // layout.tsx
   export default async function ProtectedLayout({ children }) {
     const user = await getUserSession();
     if (!user) redirect("/login");
     return <>{children}</>;
   }
   ```

6. **Axios con Interceptores para Auth**:
   - Request: leer token de cookie, refrescar si expira
   - Response: 401 → refresh → retry

7. **React Query para Server State**:
   - Queries para fetching
   - Mutations para create/update/delete
   - Invalidación selectiva post-mutation

8. **Zustand para Client State**:
   - Auth store (user, isAuthenticated)
   - Form wizards multi-step
   - UI state (sidebar open, etc.)

---

## 8. Pendientes / Preguntas

1. **Modal Anidado**: Confirmar si el bug reportado realmente ocurre en el frontend referencia o es un problema específico de CAM. El patrón actual de TarifaMatrixEditorModal SÍ tiene modales anidados.

2. **Server Actions**: El frontend referencia NO usa 'use server' para login. Solo usa server actions para `getUserSession`, `setAuthCookies`, `clearAuthCookies`. ¿Cuál es la estrategia deseada para CAM?

3. **shadcn**: ¿CAM usa o planea usar shadcn? Los componentes actuales de CAM parecen ser custom. El patrón shadcn requiere CLI (`npx shadcn@latest add button`) y usa `components.json`.

4. **GenericForm vs react-hook-form directo**: El frontend referencia tiene un `GenericForm` wrapper. ¿Es deseable en CAM o prefieren forms directos con r/hf?

5. **Data Fetching**: ¿CAM usa React Query, axios directo, o swr? El patrón referencia usa @tanstack/react-query + axios.

6. **Auth Storage**: El frontend referencia guarda user en cookie (non-httpOnly). ¿Es aceptable o se prefiere httpOnly + server-side only?

---

## Anexo: Rutas Principales

| Ruta | Descripción |
|------|-------------|
| `/admin/bungalows` | Admin bungalows (grid + create/edit modal) |
| `/admin/bungalows/tarifas` | Tarifas planas |
| `/admin/bungalows/tarifas-bungalow` | Tarifas estructuradas (CON nested modals) |
| `/admin/entradas` | Admin entradas |
| `/admin/usuarios/...` | Admin usuarios |
| `/cliente/reservar-bungalow` | Reservar bungalow (wizard) |
| `/login` | Login page |
