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
