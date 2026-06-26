# Axios: Cancelación (AbortController)

## Qué es
Mecanismo para detener una petición HTTP en curso. Esencial para evitar fugas de memoria o estados inconsistentes cuando el usuario navega fuera de una vista rápidamente.

## Reglas de Oro
- ✅ HACER: Usar `AbortController`, el estándar moderno soportado por Axios v0.22+.
- ✅ HACER: Limpiar las peticiones en el desmontaje de componentes (useEffect cleanup).
- ❌ NO HACER: Ignorar los errores de cancelación; hay que diferenciar un "AbortError" de un error real de red.

## Código Canónico

```typescript
import api from './api';

const controller = new AbortController();

api.get('/data', {
  signal: controller.signal
}).catch(error => {
  if (axios.isCancel(error)) {
    console.log('Petición cancelada:', error.message);
  } else {
    // manejar otro tipo de errores
  }
});

// Para cancelar:
controller.abort();
```

## Gotchas
- Una vez que llamas a `abort()`, el controlador no se puede reutilizar. Debes crear uno nuevo para la siguiente petición.
- `axios.isCancel(error)` es el método seguro para detectar si el catch fue por una cancelación manual.

## Integración con Nuestro Stack
Se integra naturalmente con el ciclo de vida de **React** y el sistema de cancelación de **TanStack Query**, que maneja gran parte de esto automáticamente si le pasamos la señal.
