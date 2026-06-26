# TypeScript: satisfies & as const

## Qué es
`as const` convierte un objeto en un literal inmutable. `satisfies` valida que un objeto cumpla un tipo sin "ensanchar" (widening) sus propiedades, preservando la información específica.

## Reglas de Oro
- ✅ HACER: Usar `as const` para arrays de opciones o configuraciones de temas que nunca cambian.
- ✅ HACER: Usar `satisfies` para validar objetos dinámicos pero mantener la inferencia de sus valores exactos.
- ❌ NO HACER: Usar `as const` en datos que vienen de una API o que el usuario puede modificar.

## Código Canónico

```typescript
// 1. satisfies: Valida pero mantiene los valores literales
type Theme = Record<string, string>;

const myTheme = {
  primary: '#0070f3',
  secondary: '#ff0000',
} satisfies Theme;

// myTheme.primary sigue siendo '#0070f3', no solo 'string'
// Esto permite al IDE sugerir los colores exactos.

// 2. as const: Inmutabilidad total
const ROUTES = {
  HOME: '/',
  DASHBOARD: '/admin',
} as const;

// ROUTES.HOME es solo '/' y es readonly.
```

## Gotchas
- `satisfies` solo está disponible a partir de **TypeScript 4.9+**.
- No confundir `satisfies` con una declaración de tipo (: Type). La declaración ensancha el tipo, `satisfies` no.

## Integración con Nuestro Stack
Vital para definir las **Configuraciones de Tailwind** y las **Enums constantes** de nuestro ecosistema para que la IA tenga autocompletes exactos.
