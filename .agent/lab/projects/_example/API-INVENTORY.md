# API Inventory (The "WHERE")

This document maps the project's features to existing backend endpoints.

## Base Configuration
- **Base URL**: `/api/v1/`
- **Auth Strategy**: `Bearer Token`

## Endpoint Map

| Method | Path | Request (Zod/Schema) | Response (JSON) | Role |
|--------|------|----------------------|-----------------|------|
| `GET` | `/resource/` | `paginationSchema` | `ApiResponse<Resource[]>` | List Resources |
| `POST` | `/resource/` | `createResourceSchema` | `ApiResponse<Resource>` | Create Resource |

## Integration Notes
- [Note 1: e.g., File uploads must use multipart/form-data]
- [Note 2: e.g., Filters use URL search params]
