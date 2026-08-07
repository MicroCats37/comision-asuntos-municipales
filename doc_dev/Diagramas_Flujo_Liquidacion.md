# Diagramas de Flujo y Secuencia: Módulo de Liquidaciones

Los siguientes diagramas detallan el flujo de datos y el comportamiento de las capas (Controller, Orchestrator, Flujo, Core y Presenter) para los procesos de **Cotizar** y **Crear (Primera Revisión)** en especialidades basadas en M2 (Habilitación Urbana y Mecánica de Suelos).

---

## 1. Flujo de Cotización (`POST /cotizar`)

Este diagrama muestra el flujo simplificado donde no hay persistencia en base de datos. Solo se ejecutan validaciones y la fórmula del cálculo M2.

```mermaid
sequenceDiagram
    autonumber
    actor Cliente as Cliente (HTTP)
    participant Ctrl as LiquidacionHuCotizarController
    participant Orch as LiquidacionHuCotizarOrchestrator
    participant Core as TarifaCoreService
    participant Pres as LiquidacionHuCotizarPresenter

    Cliente->>Ctrl: POST /habilitacion-urbana/cotizar (Payload)
    Note over Ctrl: Valida JSON de entrada (Schemas)
    Ctrl->>Orch: cotizar_proceso(area_solicitada, tarifa_id)
    Note over Orch: Valida que area > 0
    Orch->>Core: calcular_cotizacion_m2(tipo, area, tarifa_id)
    Note over Core: Obtiene Tarifa y Derecho vigentes
    Note over Core: Aplica fórmula: área * costo_m2
    Note over Core: Aplica clamps (min/max de Derecho)
    Core-->>Orch: DTO CotizacionM2Result
    Orch-->>Ctrl: DTO CotizacionM2Result
    Ctrl->>Pres: present(Result)
    Note over Pres: Mapea DTO a Schemas HTTP (Variables fin. = Null)
    Pres-->>Ctrl: Schema CotizarOutputSchema
    Ctrl-->>Cliente: Response 200 OK (JSON)
```

---

## 2. Flujo de Creación de Liquidación (`POST /primera-revision`)

Este diagrama muestra cómo se **reutiliza el mismo Core Service de cálculo** para asegurar que los montos guardados coincidan exactamente con la cotización, garantizando el guardado atómico mediante `@transaction.atomic`.

```mermaid
sequenceDiagram
    autonumber
    actor Cliente as Cliente (HTTP)
    participant Ctrl as LiquidacionHURevisionController
    participant Orch as LiquidacionHURevisionOrchestrator
    participant Flujo as LiquidacionHURevisionFlujo (Atomic)
    participant Core as TarifaCoreService
    participant Model as Django ORM (Base de Datos)
    participant Pres as LiquidacionHUPresenter

    Cliente->>Ctrl: POST /habilitacion-urbana/primera-revision (Payload)
    Ctrl->>Orch: crear_revision(payload)
    Orch->>Flujo: ejecutar_creacion_revision(payload)
    
    Note over Flujo: Inicia @transaction.atomic()
    
    Flujo->>Core: calcular_cotizacion_m2(tipo, area, tarifa_id)
    Note over Core: Reutiliza el cálculo idéntico de cotización
    Core-->>Flujo: DTO CotizacionM2Result
    
    Flujo->>Model: 1. Crear LiquidacionGeneral (sub_total, total)
    Flujo->>Model: 2. Crear LiquidacionHabilitacionUrbana (AutoNumero)
    Flujo->>Model: 3. Crear LiquidacionPorMetroCuadrado (costo_m2, derecho_min, tarifa_aplicada_id, derecho_aplicado_id)
    
    Note over Flujo: Commits Transaction
    
    Flujo-->>Orch: DTO LiquidacionM2Result
    Orch-->>Ctrl: DTO LiquidacionM2Result
    Ctrl->>Pres: present(Result)
    Pres-->>Ctrl: Schema RevisionOutputSchema
    Ctrl-->>Cliente: Response 200 OK (JSON)
```
