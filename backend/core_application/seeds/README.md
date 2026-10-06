# Seeds: Delegados y Colegiados Reales

Este directorio contiene los datos semilla para datos reales basados en los documentos oficiales de las Comisiones Técnicas Calificadoras de Proyectos de Edificación.

## Estructura

```
seeds/
├── delegados_reales.json    # Municipalidades, delegados y asignaciones
├── colegiados_reales.json   # PerfilIngeniero/Capitulo materializado (sin endpoint)
└── README.md                # Este archivo
```

## Seeds Disponibles

### 1. `delegados_reales.json`

Contiene las municipalidades, delegados y asignaciones municipalidad-delegado.

**Fuente de Datos:**
- `docs/desarrollo/delegados-sanitaria.md` → Ingeniería Sanitaria
- `docs/desarrollo/delegados-habilitacion-urbana.md` → Habilitación Urbana
- `docs/desarrollo/delegados-civil.md` → Ingeniería Civil
- `docs/desarrollo/delegados-electrica-mecanica.md` → Ingeniería Eléctrica y Mecánica Eléctrica

**Formato:**
```json
{
  "version": "1.0",
  "periodo": "SEPTIEMBRE 2025 A AGOSTO 2026",
  "fuente": "docs/desarrollo/",
  "municipalidades": [
    {
      "nombre": "CERCADO DE LIMA",
      "codigo": "MUN0001",
      "provincia": null,
      "distrito": null
    }
  ],
  "delegados": [
    {
      "cip": "006502",
      "nombre": "ALBINAGORTA",
      "paterno": "JARAMILLO",
      "materno": "JORGE ALBERTO",
      "nombre_completo": "ALBINAGORTA JARAMILLO JORGE ALBERTO",
      "especialidad": "Ingeniería Sanitaria",
      "tipo": "titular"
    }
  ],
  "asignaciones": [
    {
      "cip": "006502",
      "municipalidad_codigo": "MUN0001",
      "especialidad": "Ingeniería Sanitaria",
      "tipo": "titular"
    }
  ]
}
```

### 2. `colegiados_reales.json`

Contiene los datos materializados de `PerfilIngeniero` y `Capitulo` para cada CIPreferenciado en `delegados_reales.json`. Este seed evita tener que consultar el endpoint CIP cada vez.

**Formato:**
```json
{
  "version": "1.0",
  "source": "Endpoint CIP materializado desde load_delegados_reales",
  "count": 60,
  "colegiados": [
    {
      "cip": "006502",
      "dni": "06650249",
      "nombres": "JORGE ALBERTO",
      "apellido_paterno": "ALBINAGORTA",
      "apellido_materno": "JARAMILLO",
      "fecha_nacimiento": "1944-07-24",
      "genero": "M",
      "correo_personal": "jajconstruccionesysalud@gmail.com",
      "correo_institucional": "jalbinagorta@ciplima.org.pe",
      "direccion": "EDIF.LAS BEGONIAS DPTO.504   RESD.SAN FELIPE",
      "ubigeo": "150113",
      "codigo_especialidad": "01",
      "capitulo": {
        "registro_id": "09",
        "abreviacion": "SANITARIA",
        "nombre": "INGENIERIA SANITARIA E HIGIENE Y SEGURIDAD INDUSTRIAL",
        "grupo_envio_intitucional": "institucionales_cisaehsi@ciplima.org.pe"
      }
    }
  ]
}
```

## Comando de Carga

### Uso Básico

```bash
# Carga normal (usa endpoint como fallback)
python manage.py load_delegados_reales --settings=config.settings.development

# Dry-run (valida sin escribir)
python manage.py load_delegados_reales --dry-run --settings=config.settings.development

# Skip endpoint (usa solo seeds locales, sin consultar API)
python manage.py load_delegados_reales --skip-endpoint --settings=config.settings.development
```

### Comandos de Verificación

```bash
# Dry-run usando solo seeds locales (sin endpoint)
uv run python manage.py load_delegados_reales --dry-run --skip-endpoint --settings=config.settings.development

# Carga real usando solo seeds locales (sin endpoint)
uv run python manage.py load_delegados_reales --skip-endpoint --settings=config.settings.development

# Refrescar desde endpoint (actualiza PerfilIngeniero desde API)
uv run python manage.py load_delegados_reales --settings=config.settings.development
```

### Opciones

| Opción | Descripción |
|--------|-------------|
| `--dry-run` | Valida parsing y estructura sin escribir a la base de datos |
| `--skip-endpoint` | Omite consulta al endpoint de Colegio, usa solo datos del seed |
| `--seed-path` | Ruta alternativa al archivo seed JSON de delegados |
| `--colegiados-seed-path` | Ruta alternativa al archivo seed JSON de colegiados |

### Prioridad de Carga

El comando usa la siguiente prioridad para crear/actualizar `PerfilIngeniero`:

1. **Seed local `colegiados_reales.json`** - Si el CIP existe en el seed materializado
2. **Endpoint CIP** - Si no está en seed y `--skip-endpoint` no está activado
3. **Fallback seed `delegados_reales.json`** - Solo nombres básicos (nombre, paterno, materno)

### Proceso de Carga

1. **Carga Seeds** - Lee `delegados_reales.json` y `colegiados_reales.json`
2. **Crea Especialidades** - Asegura que existan: Ingeniería Sanitaria, Ingeniería Civil, Habilitación Urbana, Ingeniería Eléctrica y Mecánica Eléctrica
3. **Crea Municipalidades** - Por cada municipalidad en el seed:
   - Usa código pre-generado desde el seed
   - Crea/actualiza con `update_or_create`
4. **Crea Delegados** - Por cada delegado en el seed:
   - Normaliza CIP a 6 dígitos
   - Consulta `colegiados_reales.json` primero, luego endpoint (si no es `--skip-endpoint`)
   - Crea/actualiza `PerfilIngeniero` con datos completos
   - Crea/actualiza `Delegado` con tipo y especialidad
5. **Crea Asignaciones** - Por cada asignación en el seed:
   - Vincula delegado a municipalidad

### Endpoint

El comando puede consultar el endpoint del CIP para obtener datos actualizados del colegiado:

```
GET http://172.16.93.83:9001/api/v1/colegiado/{cip}
```

Si `--skip-endpoint` está activado, usa solo los datos de los seeds locales.

## Regenerar Seeds desde Documentos

Para regenerar el archivo `delegados_reales.json` desde los documentos fuente:

```bash
cd /ruta/al/proyecto
python scripts/parse_delegados_docs.py
```

Para exportar los `PerfilIngeniero` cargados a `colegiados_reales.json`:

```bash
cd backend
uv run python ../scripts/export_colegiados_seed.py
```

## Notas

- **CIP Normalizado**: Siempre se almacena con 6 dígitos y ceros iniciales (ej: `006502`)
- **Banco Nulo**: El campo `banco` en `Delegado` permanece `null`
- **Idempotencia**: Usa `update_or_create` - seguro ejecutar múltiples veces
- **No conecta Entidad**: Las municipalidades no se conectan a `Entidad`
- **Municipalidades con coma**: Algunas filas tienen múltiples municipalidades separadas por coma - se dividen automáticamente
- **Seed materializado**: `colegiados_reales.json` evita consultas repetitivas al endpoint CIP