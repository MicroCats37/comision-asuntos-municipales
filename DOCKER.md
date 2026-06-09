# Docker Commands - CAM Project

Este documento describe los comandos Docker para el proyecto CAM usando `uv` para Python.

## Prerequisites

1. Copiar el archivo de ejemplo de variables de entorno:

```bash
cp .env.example .env
```

2. Editar `.env` y configurar los valores apropiados:
   - `SECRET_KEY`: Generar una clave secreta segura para producción
   - `POSTGRES_PASSWORD`: Contraseña segura para PostgreSQL
   - `ALLOWED_HOSTS`: Agregar los dominios/hosts permitidos

## Quick Start

### Construir e iniciar todos los servicios

```bash
docker compose up --build
```

### Iniciar servicios en segundo plano

```bash
docker compose up --build -d
```

### Ver logs de todos los servicios

```bash
docker compose logs
```

### Ver logs de un servicio específico

```bash
docker compose logs backend
docker compose logs db
```

## Service Management

### Iniciar servicios

```bash
docker compose up -d
```

### Detener servicios

```bash
docker compose down
```

### Detener y eliminar volúmenes (RESETEA la base de datos)

```bash
docker compose down -v
```

### Reiniciar un servicio

```bash
docker compose restart backend
docker compose restart db
```

## Database Operations

### Abrir shell de PostgreSQL

```bash
docker compose exec db psql -U cam_user -d cam_db
```

### Ejecutar migraciones

```bash
docker compose exec backend uv run python manage.py migrate
```

### Crear migraciones (después de cambios en modelos)

```bash
docker compose exec backend uv run python manage.py makemigrations
```

### Resetear la base de datos (⚠️ Elimina todos los datos)

```bash
docker compose down -v
docker compose up -d
docker compose exec backend uv run python manage.py migrate
```

## Static Files & Admin

### Recolectar archivos estáticos

```bash
docker compose exec backend uv run python manage.py collectstatic --noinput
```

### Ver archivos estáticos en el contenedor

```bash
docker compose exec backend ls -la /app/staticfiles
```

## Superuser & Admin

### Crear superusuario

```bash
docker compose exec backend uv run python manage.py createsuperuser
```

### Crear admin con datos de prueba

```bash
docker compose exec backend uv run python manage.py shell <<EOF
from usuarios.models import Usuario
if not Usuario.objects.filter(username='admin').exists():
    Usuario.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Admin created')
else:
    print('Admin already exists')
EOF
```

## Development

### Modo desarrollo (con reload)

Activar modo development con volumes montados:

```bash
docker compose up --build -d
docker compose exec backend uv run python manage.py runserver 0.0.0.0:8000
```

### Ver código en el contenedor

Los volúmenes montan el código fuente, así que cualquier cambio en tu IDE se refleja inmediatamente.

### Logs en tiempo real

```bash
docker compose logs -f
docker compose logs -f backend
```

### Entrar al contenedor como appuser

```bash
docker compose exec backend /bin/bash
```

## Troubleshooting

### Admin CSS no carga (WhiteNoise)

Si el admin de Django no tiene estilos CSS:

1. Verificar que `STATIC_ROOT` está configurado en settings:

```python
STATIC_ROOT = BASE_DIR / "staticfiles"
```

2. Ejecutar `collectstatic`:

```bash
docker compose exec backend uv run python manage.py collectstatic --noinput
```

3. Verificar que WhiteNoise middleware está en orden correcto en `MIDDLEWARE`:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # ← Después de SecurityMiddleware
    ...
]
```

4. Verificar que `STORAGES` tiene la configuración correcta:

```python
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

5. Rebuild del contenedor si persisten los problemas:

```bash
docker compose down
docker compose build --no-cache backend
docker compose up -d
docker compose exec backend uv run python manage.py collectstatic --noinput
```

### Problemas de conexión a la base de datos

1. Verificar que PostgreSQL está corriendo:

```bash
docker compose ps
```

2. Ver logs de PostgreSQL:

```bash
docker compose logs db
```

3. Verificar variables de entorno en `.env`:

```bash
POSTGRES_DB=cam_db
POSTGRES_USER=cam_user
POSTGRES_PASSWORD=your_password
DB_HOST=db
```

4. Testear conexión desde el contenedor backend:

```bash
docker compose exec backend uv run python manage.py dbshell
```

### Verificar estado de Django

```bash
docker compose exec backend uv run python manage.py check
```

### Verificar configuración de Docker

```bash
docker compose config
```

### Resetear todo y empezar de nuevo

```bash
docker compose down -v --rmi local
docker compose build --no-cache backend
docker compose up -d
docker compose exec backend uv run python manage.py migrate
docker compose exec backend uv run python manage.py collectstatic --noinput
```

## Production Notes

Para un despliegue de producción considerar:

1. Usar gunicorn en producción (ya configurado en entrypoint.sh)

2. Configurar Nginx como reverse proxy

3. Usar volúmenes externos para static files

4. Configurar backup automático de PostgreSQL

5. Implementar HTTPS con Let's Encrypt

## Clean Up

### Eliminar todos los contenedores, volúmenes e imágenes no usadas

```bash
docker compose down -v --rmi local
```

### Eliminar imágenes BuildKit cache

```bash
docker builder prune -f
```

## Environment Variables

El archivo `.env` en la raíz del proyecto es usado por docker-compose.yml para configurar los servicios.

Variables necesarias para Docker:

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL)
USE_SQLITE=False
POSTGRES_DB=cam_db
POSTGRES_USER=cam_user
POSTGRES_PASSWORD=changeme
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Alternative (django-environ compatible)
DB_NAME=cam_db
DB_USER=cam_user
DB_PASSWORD=changeme
DB_HOST=db
DB_PORT=5432

# Backend Port
BACKEND_PORT=8000

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```
