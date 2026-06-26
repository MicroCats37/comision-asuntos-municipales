# Arquitectura Orientada a la Optimización de IA (AI-Optimized Architecture)

> *Este documento no es un manual técnico estricto, sino un manifiesto de diseño. Explica el **POR QUÉ** detrás de nuestras decisiones arquitectónicas, la estructura de carpetas y el uso de herramientas como SDD y Engram. Su objetivo principal: **La optimización extrema de Tokens en el uso de Inteligencia Artificial.***

---

## 1. El Norte del Proyecto: Ahorro de Tokens y Claridad Cognitiva

A medida que el desarrollo de software se entrelaza con asistentes de IA avanzados (como Gemini, Claude o herramientas MCP), el recurso más valioso ya no es solo el tiempo de cómputo del servidor, sino el **Context Window (Ventana de Contexto)** y el costo por token de la IA.

Si una IA tiene que leer 5,000 líneas de código espagueti repartidas en un "cajón de sastre" como una carpeta `shared/` para entender cómo hacer un cambio, estamos desperdiciando tokens, introduciendo alucinaciones y ralentizando el desarrollo.

### Nuestra solución: Arquitectura de "Legos" y "Headless"
Hemos diseñado una arquitectura donde todo es **explícito, modular y predecible**:
- **Estructura Plana y Directa:** No hay un `shared/` opaco. Hay `hooks/`, `utils/`, `components/` y `features/`. La IA sabe exactamente dónde buscar, consumiendo la mínima cantidad de tokens posibles en comandos como `ls` o `cat`.
- **Componentes Compound (Headless):** Construimos componentes como `GenericModal` o `GenericSidebar` que no asumen la interfaz (UI), sino que proveen la lógica y la estructura. Esto significa menos props, menos código repetido y, por ende, menos tokens para que la IA lea y modifique.

---

## 2. El `.lab`: Un Sistema Vivo y Evolutivo

La carpeta `.lab` es nuestro "Cerebro Arquitectónico" (`LAB CORE DOCTRINE`). Es un ente en constante evolución. No buscamos tener la estructura perfecta desde el día uno, sino una estructura que sea **fácil de refactorizar**.

Si mañana descubrimos que indexar nuestras _skills_ o administrar nuestras especificaciones de otra manera ahorra un 20% de tokens en la lectura inicial de la IA, podemos mover las carpetas y actualizar el índice sin romper la aplicación. El `.lab` le dice a la IA cuáles son las reglas actuales ANTES de que empiece a programar.

---

## 3. Visión a Futuro: Los "Cascarones Universales" (Universal Shells)

Este proyecto (actualmente en Next.js) es solo el campo de pruebas. La meta final es crear un ecosistema de **Boilerplates (Cascarones)** ultra-optimizados para la IA, categorizados por el tamaño y la necesidad del proyecto. 

Cada "Cascarón" tendrá sus propias reglas estrictas, patrones de diseño limpios y *skills* específicas para que cualquier IA pueda arrancar a programar a velocidad de crucero gastando el mínimo de tokens:

### Nivel 1: Proyecto Mediano/Chico (MVP y Startups Rápido)
- **Stack:** Next.js (Frontend y Backend unificados).
- **Enfoque:** Reglas estrictas de separación entre Server Actions, API Routes y Server Components. UI basada en Radix/Shadcn. El cascarón actual que estamos puliendo.

### Nivel 2: Proyecto Mediano (Desacoplado)
- **Stack:** Frontend con React (TanStack Router/Query + Vite) + Backend nativo en Python (FastAPI o Django Ninja).
- **Enfoque:** APIs tipadas (OpenAPI generado automáticamente). La IA frontend solo lee contratos, la IA backend solo escribe endpoints. Máxima separación de responsabilidades.

### Nivel 3: Proyecto Mediano/Grande (Enterprise)
- **Stack:** Angular (Frontend) + NestJS (Backend).
- **Enfoque:** Arquitecturas fuertemente orientadas a objetos, inyección de dependencias estricta y monolitos modulares. Ideal para equipos grandes o IA orquestando múltiples submódulos.

### Nivel 4: Optimización Extrema / Embebido / Landing Pages
- **Stack:** Astro, SvelteKit, Qwik o SolidJS (Frontend) + Micro-backends ligeros como Elysia.js.
- **Enfoque:** Rendimiento absoluto, cero JavaScript innecesario. Cascarones pensados para escenarios hiper-específicos (IoT, marketing, paneles hiper-rápidos).

---

## 4. El Rol Crítico de Engram y SDD (Spec-Driven Development)

Para que esta visión de "múltiples lenguajes y frameworks" funcione sin quemar millones de tokens enseñándole a la IA desde cero cada vez, nos apoyamos en dos pilares:

1. **SDD Workflows:** En lugar de lanzar a la IA a escribir código ciegamente, usamos flujos de trabajo en `.lab/specs/`. La IA planifica, especifica y diseña *antes* de codificar. Leer un Markdown de 50 líneas escaneando la arquitectura cuesta una fracción de tokens que depurar un bug en 5 archivos interconectados.
2. **Engram (Memoria Persistente):** Utilizamos memoria para registrar descubrimientos de arquitectura, bugs resueltos y decisiones de patrones. La IA no tiene que re-aprender por qué elegimos Zustand sobre Redux, simplemente consulta su Engram.

---

## Conclusión

Todo lo que hacemos en este proyecto —la nomenclatura, la eliminación de carpetas ambiguas, los componentes Headless, la indexación del `.lab`— persigue un objetivo claro: **Crear el entorno de desarrollo más eficiente del mundo para la colaboración humano-IA.** 

Al estandarizar los patrones y crear "Cascarones" universales para diferentes stacks, estamos construyendo una fábrica de software donde el cuello de botella ya no es el costo de integrar a un desarrollador... ni el costo de los tokens de la IA.
