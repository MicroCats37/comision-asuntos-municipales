# Guía de Schemas HTTP con Ejemplos de JSON (Request / Response)

Este documento contiene la especificación de clases Ninja (`BaseSchema`) junto con sus respectivos ejemplos de payloads JSON de entrada y salida para cada uno de los 3 endpoints de Habilitación Urbana.

---

## 1. GET `/api/liquidaciones/habilitacion-urbana/tarifas/vigentes`

### Request (GET)
*No tiene request body.*

### Response JSON (200 OK)
```json
{
  "tarifa_vigente": {
    "datos": {
      "id": "2b6a5a7b-3d44-42ea-8228-403d1544a020",
      "costo_por_m2": 0.20
    }
  },
  "derecho_vigente": {
    "datos": {
      "id": "e8913bfa-76ef-46c1-a201-100234500010",
      "derecho_minimo": 1000.00,
      "derecho_maximo": 10000.00
    }
  }
}
```

### Python Ninja Schemas (`presentation/schemas/tarifa_hu_vigentes_schemas.py`)
```python
from core.types import BaseSchema
import uuid

class TarifaVigenteDatos(BaseSchema):
    id: uuid.UUID
    costo_por_m2: float

class TarifaVigenteWrapper(BaseSchema):
    datos: TarifaVigenteDatos

class DerechoVigenteDatos(BaseSchema):
    id: uuid.UUID
    derecho_minimo: float
    derecho_maximo: float

class DerechoVigenteWrapper(BaseSchema):
    datos: DerechoVigenteDatos

class TarifasVigentesOutput(BaseSchema):
    tarifa_vigente: TarifaVigenteWrapper
    derecho_vigente: DerechoVigenteWrapper
```

---

## 2. POST `/api/liquidaciones/habilitacion-urbana/cotizar`

### Request JSON Body
```json
{
  "liquidacion_especifica": {
    "datos": {
      "area_solicitada": 200.00
    },
    "tarifa": {
      "tarifa_m2_id": "2b6a5a7b-3d44-42ea-8228-403d1544a020"
    }
  }
}
```

### Response JSON (200 OK)
```json
{
  "datos": {
    "entrada": {
      "area_solicitada": 200.00
    },
    "tarifa": {
      "id": "2b6a5a7b-3d44-42ea-8228-403d1544a020",
      "costo_por_m2": 0.20
    },
    "derecho": {
      "id": "e8913bfa-76ef-46c1-a201-100234500010",
      "derecho_minimo": 1000.00,
      "derecho_maximo": 10000.00
    },
    "variables_financieras": {
      "igv": null,
      "uit": null
    }
  },
  "calculo": {
    "monto_bruto": 40.00,
    "subtotal": 40.00,
    "total": 1000.00
  }
}
```

### Python Ninja Schemas (`presentation/schemas/liquidacion_hu_cotizar_schemas.py`)
```python
from core.types import BaseSchema
from typing import Optional
import uuid

# --- Request ---
class CotizarEspecificaDatosIn(BaseSchema):
    area_solicitada: float

class CotizarEspecificaTarifaIn(BaseSchema):
    tarifa_m2_id: uuid.UUID

class LiquidacionEspecificaCotizarIn(BaseSchema):
    datos: CotizarEspecificaDatosIn
    tarifa: CotizarEspecificaTarifaIn

class CotizarInputSchema(BaseSchema):
    liquidacion_especifica: LiquidacionEspecificaCotizarIn

# --- Response ---
class CotizarTarifaOut(BaseSchema):
    id: uuid.UUID
    costo_por_m2: float

class CotizarDerechoOut(BaseSchema):
    id: uuid.UUID
    derecho_minimo: float
    derecho_maximo: float

class VariablesFinancierasNulasOut(BaseSchema):
    igv: Optional[dict] = None
    uit: Optional[dict] = None

class CotizarDatosOutputSchema(BaseSchema):
    entrada: CotizarEspecificaDatosIn
    tarifa: CotizarTarifaOut
    derecho: CotizarDerechoOut
    variables_financieras: VariablesFinancierasNulasOut

class CotizarCalculoOutputSchema(BaseSchema):
    monto_bruto: float
    subtotal: float
    total: float

class CotizarOutputSchema(BaseSchema):
    datos: CotizarDatosOutputSchema
    calculo: CotizarCalculoOutputSchema
```

---

## 3. POST `/api/liquidaciones/habilitacion-urbana/primera-revision`

### Request JSON Body
```json
{
  "liquidacion_general": {
    "municipalidad_id": "file_c_3A_Users_Usuario_Desktop_Aplicaciones_CIP_CAM",
    "expediente": "EXP-2026-001",
    "observacion": "Primera revisión",
    "proyecto": {
      "denominacion": "Condominio Los Pinos",
      "nombre_propietario": "Constructora XYZ S.A.C.",
      "direccion": "Av. Principal 123",
      "distrito_id": "787c8940-da57-314d-84ad-a40e99d8669b",
      "entidad": {
        "tipo_documento": "RUC",
        "numero_documento": "20123456789",
        "razon_social": "Constructora XYZ S.A.C."
      }
    }
  },
  "liquidacion_especifica": {
    "datos": {
      "area_solicitada": 500.00
    },
    "tarifa": {
      "tarifa_m2_id": "2b6a5a7b-3d44-42ea-8228-403d1544a020"
    }
  }
}
```

### Response JSON (200 OK)
```json
{
  "liquidacion_general": {
    "id": "b4dbb91d-68c5-4d90-a02f-ce687ed5b79f",
    "municipalidad_id": "file_c_3A_Users_Usuario_Desktop_Aplicaciones_CIP_CAM",
    "usuario_creador": {
      "id": "e1bd99c9-ef48-493b-93bc-9a6efb9794a5"
    },
    "fecha_registro": "2026-08-06T10:00:00Z",
    "expediente": "EXP-2026-001",
    "observacion": "Primera revisión",
    "numero_revision": 1,
    "sub_total": 100.00,
    "total": 118.00,
    "igv_id": "93faf260-f277-403d-b015-99a8a234d341",
    "uit_id": "baeb6266-bef8-4d55-975d-6840cae8f901",
    "derecho_id": "e8913bfa-76ef-46c1-a201-100234500010",
    "proyecto": {
      "id": "9b80b3b1-44b6-437e-939f-c0b348e46307",
      "denominacion": "Condominio Los Pinos",
      "nombre_propietario": "Constructora XYZ S.A.C.",
      "direccion": "Av. Principal 123",
      "distrito_id": "787c8940-da57-314d-84ad-a40e99d8669b",
      "entidad": {
        "razon_social": "Constructora XYZ S.A.C.",
        "tipo_documento": "RUC",
        "numero_documento": "20123456789"
      }
    }
  },
  "liquidacion_tipo": {
    "id": "79d8d7ef-940a-4a95-9b2c-481c0ab3456f",
    "numero": 1
  },
  "liquidacion_especifica": {
    "id": "325d9292-46f1-42cf-8bb3-3c903760e939",
    "area_m2": 500.00,
    "costo_por_m2": 0.20,
    "derecho_minimo": 1000.00,
    "derecho_maximo": 10000.00,
    "tarifa_aplicada_id": "2b6a5a7b-3d44-42ea-8228-403d1544a020",
    "derecho_aplicado_id": "e8913bfa-76ef-46c1-a201-100234500010"
  }
}
```

### Python Ninja Schemas (`presentation/schemas/liquidacion_habilitacion_urbana_schemas.py`)
```python
from core.types import BaseSchema
from typing import Optional
import uuid

# --- Request ---
class ProyectoCotizar(BaseSchema):
    denominacion: str
    nombre_propietario: str
    direccion: str
    distrito_id: uuid.UUID
    entidad: EntidadInline

class LiquidacionGeneralRevisionIn(BaseSchema):
    municipalidad_id: uuid.UUID
    expediente: str
    observacion: Optional[str] = None
    proyecto: ProyectoCotizar

class LiquidacionEspecificaRevisionIn(BaseSchema):
    datos: CotizarEspecificaDatosIn
    tarifa: CotizarEspecificaTarifaIn

class LiquidacionHabilitacionUrbanaInput(BaseSchema):
    liquidacion_general: LiquidacionGeneralRevisionIn
    liquidacion_especifica: LiquidacionEspecificaRevisionIn

# --- Response ---
class UsuarioCreadorOutput(BaseSchema):
    id: uuid.UUID

class ProyectoOutput(BaseSchema):
    id: uuid.UUID
    denominacion: str
    nombre_propietario: str
    direccion: str
    distrito_id: uuid.UUID
    entidad: EntidadInline

class LiquidacionGeneralOutput(BaseSchema):
    id: uuid.UUID
    municipalidad_id: uuid.UUID
    usuario_creador: UsuarioCreadorOutput
    fecha_registro: str
    expediente: str
    observacion: Optional[str] = None
    numero_revision: int
    sub_total: float
    total: float
    igv_id: uuid.UUID
    uit_id: uuid.UUID
    derecho_id: uuid.UUID
    proyecto: ProyectoOutput

class LiquidacionTipoOutput(BaseSchema):
    id: uuid.UUID
    numero: int

class LiquidacionEspecificaOutput(BaseSchema):
    id: uuid.UUID
    area_m2: float
    costo_por_m2: float
    derecho_minimo: float
    derecho_maximo: float
    tarifa_aplicada_id: uuid.UUID
    derecho_aplicado_id: uuid.UUID

class LiquidacionHabilitacionUrbanaOutput(BaseSchema):
    liquidacion_general: LiquidacionGeneralOutput
    liquidacion_tipo: LiquidacionTipoOutput
    liquidacion_especifica: LiquidacionEspecificaOutput
```
