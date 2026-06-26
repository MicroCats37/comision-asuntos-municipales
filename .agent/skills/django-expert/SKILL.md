---
name: django-expert
description: Expert patterns for Django 5+ and Django REST Framework (DRF). Includes optimization, serialization strategies, and clean architecture for large apps.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Django & DRF Expert

> **Advanced patterns for scalable Codebases.**

---

## 🏗️ Clean Project Structure

### Where does business logic go?
❌ **Views**: Never. Views should only handle HTTP request/response.
❌ **Models**: Only for domain logic (e.g., `calculate_age()`). Avoid side effects here.
✅ **Services/Selectors**: Use a `services.py` for write operations (create, update) and `selectors.py` for read operations (filtering, complex queries).

### Recommended App Layout
```txt
users/
├── services.py   # CreateUser, UpdateUser
├── selectors.py  # GetActiveUsers, GetUserOr404
├── views.py      # Calls services/selectors
├── serializers.py
├── urls.py
└── models.py
```

---

## 🚀 Performance Rules (N+1 Killer)

### 1. Database Optimization (MANDATORY)
- Always check loops that access relationships.
- **ForeignKeys**: Use `select_related('related_model')`.
- **ManyToMany/Reverse FK**: Use `prefetch_related('related_model_set')`.
- **Only/Defer**: Use `.only('id', 'name')` for large models if you don't need all fields.

```python
# ❌ BAD: N+1 queries
queryset = Order.objects.all()
for order in queryset:
    print(order.user.email) # Boom! ID query per order

# ✅ GOOD: 1 query
queryset = Order.objects.select_related('user').all()
```

### 2. Validation First
- Use **Django REST Framework Serializers** for ALL data input/output.
- If validation is purely local and complex, consider **Pydantic** inside your service.

---

## 🐍 Coding Standards

### Type Hints (Python 3.10+)
Every function arguments and return types MUST be typed.

```python
from typing import Optional, List
from django.db.models import QuerySet

def get_active_orders(user_id: int) -> QuerySet[Order]:
    ...
```

### Async vs Sync
- Use `async def` views if you are doing:
  - External API calls (httpx).
  - Heavy file I/O.
- Use `def` (standard sync) for DB-heavy operations (Django ORM is mostly sync until very recent versions, and mixing them can cause thread issues).

---

## 🛡️ Security Best Practices
- Never disable CSRF globally (only on API endpoints via DRF standard auth).
- Always set `ALLOWED_HOSTS`.
- Use `django-environ` to manage secrets.
- Never commit `.env` files.
