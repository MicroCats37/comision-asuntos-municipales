# Comandos Docker

## Levantar base de datos

```bash
docker compose -p cam-db -f docker-compose.db.yml up -d
```

## Levantar aplicacion

```bash
docker compose -p cam-app -f docker-compose.app.yml up -d --build
```

## Ver estado

```bash
docker compose -p cam-db -f docker-compose.db.yml ps
docker compose -p cam-app -f docker-compose.app.yml ps
```

## Ver logs

```bash
docker compose -p cam-db -f docker-compose.db.yml logs -f db
docker compose -p cam-app -f docker-compose.app.yml logs -f backend
docker compose -p cam-app -f docker-compose.app.yml logs -f proxy
```

## Detener aplicacion

```bash
docker compose -p cam-app -f docker-compose.app.yml down
```

## Detener base de datos

```bash
docker compose -p cam-db -f docker-compose.db.yml down
```

## Restaurar ambos servicios

```bash
docker compose -p cam-db -f docker-compose.db.yml up -d
docker compose -p cam-app -f docker-compose.app.yml up -d --build
```

## Cargar dump PostgreSQL

```bash
docker cp cam_db.dump cam_db:/tmp/cam_db.dump && \
docker exec cam_db sh -c 'pg_restore --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB" /tmp/cam_db.dump' && \
docker exec cam_db rm -f /tmp/cam_db.dump
```

## Crear backup PostgreSQL

Ejecutar desde el servidor, en el directorio donde se desea guardar el dump:

```bash
TS=$(date +%Y%m%d_%H%M%S) && \
docker exec cam_db sh -c 'pg_dump -Fc -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
> "cam_db_backup_${TS}.dump" && \
ls -lh "cam_db_backup_${TS}.dump"
```

El comando solo genera un dump en formato custom; no modifica la base de datos.

## Descargar un backup del servidor

Desde la computadora local, descarga el dump ubicado en `Downloads` del servidor:

```bash
scp "cam-05@172.16.4.228:C:/Users/cam-05/Downloads/cam_db_backup_20261110_194630.dump" .
```
