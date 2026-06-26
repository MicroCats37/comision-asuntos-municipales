# Modals: Worked Examples

## Example 1: Uncontrolled Composition (Preferred)

The simplest pattern using the compound component API:

```tsx
"use client";

import { Button } from "@/components/ui/button";
import { GenericModal } from "@/components/genericModal/GenericModal";

export function DeleteProductButton({ productId }: { productId: string }) {
  return (
    <GenericModal preventClose>
      <GenericModal.Trigger asChild>
        <Button variant="destructive">Delete Product</Button>
      </GenericModal.Trigger>

      <GenericModal.Content>
        <GenericModal.Header title="Delete Product" />
        <GenericModal.Body>
          <p>Are you sure you want to delete this product? This action cannot be undone.</p>
        </GenericModal.Body>
        <GenericModal.Footer>
          <GenericModal.Close asChild>
            <Button variant="outline">Cancel</Button>
          </GenericModal.Close>
          <Button variant="destructive" onClick={() => deleteProduct(productId)}>
            Delete
          </Button>
        </GenericModal.Footer>
      </GenericModal.Content>
    </GenericModal>
  );
}
```

## Example 2: Controlled with React 19 Ref

For async triggers (fetching data before opening):

```tsx
"use client";

import { useRef } from "react";
import { Button } from "@/components/ui/button";
import { GenericModal, type GenericModalRef } from "@/components/genericModal/GenericModal";

export function AsyncProductModal() {
  const modalRef = useRef<GenericModalRef>(null);

  const handleFetchAndOpen = async () => {
    // Simulate fetching
    await fetchProductData();
    modalRef.current?.open();
  };

  return (
    <>
      <Button onClick={handleFetchAndOpen}>View Product Details</Button>
      
      <GenericModal ref={modalRef}>
        <GenericModal.Content>
          <GenericModal.Header title="Product Details" />
          <GenericModal.Body>
            <p>Product content loaded asynchronously.</p>
          </GenericModal.Body>
        </GenericModal.Content>
      </GenericModal>
    </>
  );
}
```

## Example 3: No Header (Minimal Design)

For confirmation dialogs or minimal modals, omit the header:

```tsx
<GenericModal>
  <GenericModal.Trigger asChild>
    <Button>Continue</Button>
  </GenericModal.Trigger>

  <GenericModal.Content>
    {/* No GenericModal.Header — sr-only DialogTitle is auto-injected */}
    <GenericModal.Body>
      <p>Are you sure you want to continue?</p>
    </GenericModal.Body>
    <GenericModal.Footer>
      <GenericModal.Close asChild>
        <Button variant="outline">Cancel</Button>
      </GenericModal.Close>
      <Button>Confirm</Button>
    </GenericModal.Footer>
  </GenericModal.Content>
</GenericModal>
```

## Example 4: With Unsaved Changes Interceptor

Using `onBeforeClose` to prevent accidental data loss:

```tsx
<GenericModal
  preventClose
  onBeforeClose={async () => {
    if (hasUnsavedChanges) {
      const confirmed = window.confirm("You have unsaved changes. Leave anyway?");
      return confirmed;
    }
    return true;
  }}
>
  <GenericModal.Trigger asChild>
    <Button>Edit Profile</Button>
  </GenericModal.Trigger>

  <GenericModal.Content>
    <GenericModal.Header title="Edit Profile" />
    <GenericModal.Body>
      {/* Form with hasUnsavedChanges state */}
    </GenericModal.Body>
  </GenericModal.Content>
</GenericModal>
```

## Example 5: Deep State Injection

Using `useGenericModal` to close from deep inside the tree:

```tsx
"use client";

import { useGenericModal } from "@/components/genericModal/GenericModal";

// Inside a deeply nested form within the modal
function NestedFormSubmitButton() {
  const { close, forceClose } = useGenericModal();

  return (
    <Button
      onClick={async () => {
        await submitForm();
        close();  // Respects onBeforeClose interceptor
        // Or use forceClose() to bypass preventClose
      }}
    >
      Submit and Close
    </Button>
  );
}
```

## Example 6: Dynamic Width

Passing className to `GenericModal.Content` for wide forms:

```tsx
<GenericModal>
  <GenericModal.Trigger asChild>
    <Button>Create Product (Wide Form)</Button>
  </GenericModal.Trigger>

  <GenericModal.Content className="sm:min-w-3xl">
    <GenericModal.Header title="New Product" />
    <GenericModal.Body>
      {/* Product creation form — needs more width */}
      <div className="grid grid-cols-2 gap-4">
        {/* Many fields */}
      </div>
    </GenericModal.Body>
    <GenericModal.Footer>
      <GenericModal.Close asChild>
        <Button variant="outline">Cancel</Button>
      </GenericModal.Close>
      <Button>Create Product</Button>
    </GenericModal.Footer>
  </GenericModal.Content>
</GenericModal>
```

## Example 7: Controlled Open State

Using `open` and `onOpenChange` props for full control:

```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { GenericModal } from "@/components/genericModal/GenericModal";

export function ControlledModal() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setIsOpen(true)}>Open Modal</Button>
      
      <GenericModal open={isOpen} onOpenChange={setIsOpen}>
        <GenericModal.Content>
          <GenericModal.Header title="Controlled Modal" />
          <GenericModal.Body>
            <p>This modal is controlled by external state.</p>
          </GenericModal.Body>
          <GenericModal.Footer>
            <GenericModal.Close asChild>
              <Button variant="outline">Close</Button>
            </GenericModal.Close>
          </GenericModal.Footer>
        </GenericModal.Content>
      </GenericModal>
    </>
  );
}
```

## Example 8: CloseX Button

Using `GenericModal.CloseX` for a predefined close button:

```tsx
<GenericModal>
  <GenericModal.Trigger asChild>
    <Button>Open with CloseX</Button>
  </GenericModal.Trigger>

  <GenericModal.Content>
    {/* CloseX appears in top-right corner automatically */}
    <GenericModal.CloseX className="custom-close-class" />
    <GenericModal.Body>
      <p>This modal has a close button in the corner.</p>
    </GenericModal.Body>
  </GenericModal.Content>
</GenericModal>
```

## Example 9: Header with Description

Using both `title` and `description` props:

```tsx
<GenericModal>
  <GenericModal.Trigger asChild>
    <Button>View Details</Button>
  </GenericModal.Trigger>

  <GenericModal.Content>
    <GenericModal.Header 
      title="Confirm Action" 
      description="Please review the details below before proceeding."
    />
    <GenericModal.Body>
      {/* Content */}
    </GenericModal.Body>
  </GenericModal.Content>
</GenericModal>
```

---

## See Also
- [Spec: Modals](./SPEC.md) — full spec
- [Knowledge: React 19 Ref Pattern](../../knowledge/react-19/refs-simplified.md)
