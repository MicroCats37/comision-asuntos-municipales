# TypeScript: Template Literal Types

## Qué es
Permite construir tipos basados en strings usando la misma sintaxis que los template strings de JavaScript, permitiendo validaciones de texto muy potentes.

## Reglas de Oro
- ✅ HACER: Usar para tipar rutas dinámicas (`/api/${string}`).
- ✅ HACER: Usar para generar combinaciones de clases de CSS o tokens de diseño (ej. `spacing-${1 | 2 | 4}`).
- ❌ NO HACER: Crear millones de combinaciones que estresen el servidor de tipos de TypeScript.

## Código Canónico

```typescript
// 1. Tipado de rutas API
type ApiVersion = 'v1' | 'v2';
type Endpoint = 'users' | 'products';

type ApiPath = `/api/${ApiVersion}/${Endpoint}`;

const validPath: ApiPath = '/api/v1/users'; // OK
// const invalidPath: ApiPath = '/api/v3/orders'; // Error

// 2. Combinación de colores de UI
type Color = 'blue' | 'red' | 'green';
type Intensity = '500' | '700';

type UIColor = `${Color}-${Intensity}`;

const primary: UIColor = 'blue-500';
```

## Gotchas
- El exceso de combinaciones en Template Literals puede ralentizar drásticamente el VS Code.
- No soporta expresiones complejas, solo uniones de literales.

## Integración con Nuestro Stack
Lo utilizaremos para blindar el **Enrutamiento de Next.js** y asegurar que los componentes de UI solo reciban variantes de diseño válidas definidas en nuestro sistema de diseño.
