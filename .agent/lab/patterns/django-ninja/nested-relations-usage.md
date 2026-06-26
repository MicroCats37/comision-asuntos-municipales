# M2M vs Batch Pattern: Choosing the Right Service

## Overview

When handling related entities in Django Ninja services, two distinct patterns emerge depending on the complexity of the relationship:

| Scenario | Pattern | Schema | Use When |
|----------|---------|--------|----------|
| Simple ID linking/unlinking | **M2M** | `M2MDiffSchema` | Adding/removing tags, roles, categories |
| Complex nested CRUD | **Batch** | `BatchItemSchema` | Creating/updating/deleting entities with rich payloads, files, documents |

---

## M2M Pattern (`M2MDiffSchema`)

### When to Use

- You need to **link or unlink existing records** by their IDs
- The relationship is a simple **Many-to-Many** (e.g., a post can have many tags, a user can have many roles)
- You're **not creating, updating, or deleting** the related entities themselves
- Only the **ID** of the related entity matters

### Examples

**Tag Assignment:**
```python
# Schema
class TagDiffSchema(M2MDiffSchema):
    """Schema for adding/removing tags from a post."""
    add_tags: List[int] = []  # Tag IDs to ADD
    remove_tags: List[int] = []  # Tag IDs to REMOVE

# Service
class PostService:
    def update_post_tags(self, post_id: int, diff: TagDiffSchema) -> Post:
        post = self.repo.get(post_id)
        
        if diff.remove_tags:
            post.tags.remove(*diff.remove_tags)
        if diff.add_tags:
            post.tags.add(*diff.add_tags)
        
        return post
```

**Role Assignment:**
```python
class UserRoleDiffSchema(M2MDiffSchema):
    add_roles: List[int] = []
    remove_roles: List[int] = []

class UserService:
    def update_user_roles(self, user_id: int, diff: UserRoleDiffSchema) -> User:
        user = self.repo.get(user_id)
        
        if diff.remove_roles:
            user.roles.remove(*diff.remove_roles)
        if diff.add_roles:
            user.roles.add(*diff.add_roles)
        
        return user
```

### Key Characteristics

- **Input**: List of IDs (integers)
- **Operation**: `add()` / `remove()` on M2M manager
- **No entity creation**: Only links existing records
- **Stateless diff**: The schema captures intent (add/remove) not full state

---

## Batch Pattern (`BatchItemSchema`)

### When to Use

- You need to **CREATE, UPDATE, or DELETE** complete related entities
- The related entities have **nested objects, files, or rich payloads**
- You're managing **complex documents** with multiple fields
- The operation involves **business logic** beyond simple ID linking

### Examples

**Document Management:**
```python
# Schema
class DocumentItemSchema(BatchItemSchema):
    id: Optional[int] = None  # None = create new, present = update
    title: str
    content: str
    attachments: List[AttachmentSchema] = []
    
class DocumentBatchSchema(Schema):
    items: List[DocumentItemSchema]
    delete_ids: List[int] = []  # IDs to permanently delete

# Service
class DocumentService:
    def process_document_batch(self, parent_id: int, batch: DocumentBatchSchema) -> List[Document]:
        parent = self.parent_repo.get(parent_id)
        results = []
        
        # Delete marked items
        if batch.delete_ids:
            self.doc_repo.delete_batch(batch.delete_ids)
        
        # Create/Update items
        for item in batch.items:
            if item.id is None:
                # CREATE new document
                doc = self.doc_repo.create({**item.dict(), "parent_id": parent_id})
            else:
                # UPDATE existing document
                doc = self.doc_repo.update(item.id, item.dict())
            
            # Handle nested attachments (files, etc.)
            if item.attachments:
                self._sync_attachments(doc.id, item.attachments)
            
            results.append(doc)
        
        return results
```

**Line Items with Nested Data:**
```python
class InvoiceItemSchema(BatchItemSchema):
    id: Optional[int] = None
    description: str
    quantity: int
    unit_price: Decimal
    tax_components: List[TaxComponentSchema] = []
    metadata: Dict[str, Any] = {}

class InvoiceBatchSchema(Schema):
    items: List[InvoiceItemSchema]
    replace_all: bool = False  # If True, delete all existing and recreate

class InvoiceService:
    def process_invoice_items(self, invoice_id: int, batch: InvoiceBatchSchema) -> Invoice:
        invoice = self.repo.get(invoice_id)
        
        if batch.replace_all:
            self.item_repo.delete_by_invoice(invoice_id)
        
        for item in batch.items:
            if item.id is None:
                self.item_repo.create({**item.dict(), "invoice_id": invoice_id})
            else:
                self.item_repo.update(item.id, item.dict())
        
        return invoice
```

### Key Characteristics

- **Input**: Full entity schemas with optional ID (for updates)
- **Operations**: CREATE, UPDATE, DELETE on complete entities
- **Nested objects**: Handles files, documents, complex payloads
- **Full state or diff**: Can replace all or selectively update

---

## Decision Matrix

```
START
  │
  ▼
Is the operation ONLY adding/removing links to EXISTING entities?
  │
  ├── YES ──► Use M2MDiffSchema (M2M Pattern)
  │
  └── NO ──► Are you creating/updating/deleting complete entities
              with nested data, files, or rich payloads?
              │
              ├── YES ──► Use BatchItemSchema (Batch Pattern)
              │
              └── NO ──► Consider if a simple CRUD operation or
                         a different pattern is more appropriate
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Using Batch for simple tag assignment | Overengineering, bloated payloads | Use M2MDiffSchema |
| Using M2MDiffSchema to "update" nested entities | M2M only handles IDs, not full entities | Use BatchItemSchema |
| Creating IDs in M2MDiffSchema | M2M assumes entities already exist | Use BatchItemSchema with create logic |

---

## See Also
- [Knowledge: Services](./services.md) — Service layer fundamentals
- [Pattern: Schema Validation](./schema-validation-usage.md) — Input/output schema patterns
