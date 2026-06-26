# Hexagonal Architecture Flow — Django Ninja

## Overview
Hexagonal Architecture (Ports & Adapters) organizes Django Ninja applications into distinct layers with strict dependency rules. The architecture ensures business logic remains independent of infrastructure and HTTP concerns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         APPLICATION                                  │
│                                                                      │
│  ┌─────────────────┐                              ┌───────────────┐  │
│  │   PRESENTATION  │                              │     CORE      │  │
│  │                 │                              │               │  │
│  │  Controllers    │                              │  Exceptions   │  │
│  │  Routers        │                              │  Config       │  │
│  │  Dependencies   │                              │  Pagination   │  │
│  └────────┬────────┘                              └───────────────┘  │
│           │                                                           │
│           │ calls                                                     │
│           ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │                         DOMAIN                               │     │
│  │                                                              │     │
│  │   Services ───────────► Selectors ◄───────────── Repos    │     │
│  │   (business logic)     (query port)       (persistence    │     │
│  │                         (interface)        port)           │     │
│  │                                                              │     │
│  │   Models    Schemas    Exceptions                           │     │
│  │   (entities)(validation)                                     │     │
│  │                                                              │     │
│  └─────────────────────────────────────────────────────────────┘     │
│           ▲                                                           │
│           │ implements                                                │
│           │                                                           │
│  ┌────────┴────────┐                              ┌───────────────┐  │
│  │  INFRASTRUCTURE  │                              │   EXTERNAL     │  │
│  │                  │                              │                 │  │
│  │  RepositoryImpl  │─────── uses ────────────►    │  Django ORM    │  │
│  │  SelectorImpl    │                              │  SQLAlchemy     │  │
│  │  ServicesImpl    │                              │  Email/SMS     │  │
│  └──────────────────┘                              └───────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Request Flow

### 1. HTTP Request Arrives

```
Client → presentation/urls.py → api.register_controllers()
```

### 2. Controller Receives Request

```python
# presentation/controllers.py
@api_controller("/requests", tags=["requests"])
class RequestController:
    @inject
    def __init__(self, request_service: RequestService):
        self.request_service = request_service  # Domain service injected
    
    @route.get("/{request_id}", response=RequestOut)
    def get_request(self, request_id: int) -> RequestOut:
        # Thin orchestration — delegates to domain service
        return self.request_service.get_by_id(request_id)
```

### 3. Domain Service Executes Business Logic

```python
# domain/services.py
class RequestService:
    def __init__(self, repository: RequestRepository, selector: RequestSelector):
        self.repository = repository  # Port interface
        self.selector = selector      # Port interface
    
    def get_by_id(self, request_id: int) -> Request:
        # Pure business logic — no infrastructure imports
        request = self.selector.by_id(request_id)  # Query via port
        if not request:
            raise RequestNotFoundError(f"Request {request_id} not found")
        
        # Business rule validation
        self._validate_can_view(request, current_user)
        
        return request
```

### 4. Infrastructure Implements Port Interfaces

```python
# infrastructure/selectors.py
class RequestSelectorImpl(RequestSelector):
    """Concrete implementation of the selector port."""
    
    def __init__(self, db: Session):  # Infrastructure detail
        self.db = db
    
    def by_id(self, request_id: int) -> Request | None:
        # Direct ORM query — infrastructure concern
        model = self.db.get(RequestModel, request_id)
        return self._to_domain(model) if model else None
```

```python
# infrastructure/repositories.py
class RequestRepositoryImpl(RequestRepository):
    """Concrete implementation of the repository port."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def add(self, entity: Request) -> Request:
        model = self._to_model(entity)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._to_domain(model)
```

## Dependency Rule

```
presentation → domain ← infrastructure
```

| Rule | Description |
|------|-------------|
| **Domain** | Depends on nothing in the application. Contains pure business logic. |
| **Infrastructure** | Implements domain interfaces (ports). Depends on domain only. |
| **Presentation** | Implements HTTP concerns. Depends on domain services. |

### ❌ FORBIDDEN Dependencies
- `domain` → `infrastructure` (business logic would know about persistence)
- `domain` → `presentation` (business logic would know about HTTP)
- `infrastructure` → `presentation` (persistence would know about HTTP)

## Dependency Injection Setup

```python
# presentation/dependencies.py
from injector import Module, provider, Injector
from myapp.domain.repositories import RequestRepository
from myapp.domain.selectors import RequestSelector
from myapp.domain.services import RequestService
from myapp.infrastructure.repositories import RequestRepositoryImpl
from myapp.infrastructure.selectors import RequestSelectorImpl

injector = Injector([AppModule()])

class AppModule(Module):
    """Binds domain interfaces to infrastructure implementations."""
    
    @provider
    def provide_request_repository(self, db: Session) -> RequestRepository:
        return RequestRepositoryImpl(db)
    
    @provider
    def provide_request_selector(self, db: Session) -> RequestSelector:
        return RequestSelectorImpl(db)
    
    @provider
    def provide_request_service(
        self,
        repository: RequestRepository,
        selector: RequestSelector
    ) -> RequestService:
        return RequestService(repository=repository, selector=selector)
```

## Example: Complete Request Lifecycle

```python
# 1. Client POST /api/v1/requests
# 2. Router maps to controller method
# 3. Controller receives data
@route.post("/", response=RequestOut, status_code=201)
def create_request(self, data: RequestCreateIn) -> RequestOut:
    request = self.request_service.create(data)  # Delegates to domain
    return RequestOut.model_validate(request)

# 4. Domain service validates and orchestrates
def create(self, data: RequestCreateIn) -> Request:
    # Business rule: Check for duplicates
    existing = self.selector.by_requester_and_title(
        data.requester_id, data.title
    )
    if existing:
        raise DuplicateRequestError("Request already exists")
    
    # Create domain entity
    request = Request(
        title=data.title,
        description=data.description,
        requester_id=data.requester_id,
        status=RequestStatus.PENDING
    )
    
    # Persist via port
    return self.repository.add(request)

# 5. Infrastructure persists the entity
def add(self, entity: Request) -> Request:
    model = RequestModel(...entity.model_dump()...)
    self.db.add(model)
    self.db.commit()
    self.db.refresh(model)
    return self._to_domain(model)

# 6. Response flows back through layers
#    RequestOut ← Request ← repository.add() ← domain service
#    ← controller ← HTTP response
```

## Testing Benefits

| Layer | What to Test | How |
|-------|--------------|-----|
| **Domain** | Business logic, rules, validations | Unit test with mock ports |
| **Infrastructure** | ORM queries, persistence | Integration test with real DB |
| **Presentation** | HTTP mapping, response formatting | Integration test with TestClient |

### Example: Testing Domain Service

```python
# tests/domain/test_request_service.py
def test_create_request_success():
    # Arrange — mock the ports
    mock_repo = Mock(spec=RequestRepository)
    mock_selector = Mock(spec=RequestSelector)
    mock_selector.by_requester_and_title.return_value = None
    
    service = RequestService(repository=mock_repo, selector=mock_selector)
    
    # Act
    result = service.create(RequestCreateIn(...))
    
    # Assert
    assert result.status == RequestStatus.PENDING
    mock_repo.add.assert_called_once()
```

## See Also
- [Spec: Project Structure](../../specs/django-ninja/project-structure/SPEC.md)
- [Services Documentation](./services.md)
- [Selectors Documentation](./selectors.md)
- [Pattern: DI Service Usage](../../patterns/django-ninja/di-service-usage.md)
