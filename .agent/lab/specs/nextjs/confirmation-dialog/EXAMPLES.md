# Confirmation Dialog: Worked Examples

## Example 1: Basic Destructive Confirmation

Delete an item after user confirms:

```tsx
"use client";

import { useConfirmationDialog } from "@/components/confirmationDialog/useConfirmationDialog";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";

export function DeleteUserButton({ userId, onDeleted }: { userId: number; onDeleted: () => void }) {
  const { confirm, Dialog } = useConfirmationDialog();

  const handleDelete = async (id: number) => {
    const ok = await confirm({
      title: "¿Eliminar usuario?",
      description: "Esta acción no se puede deshacer.",
      confirmLabel: "Eliminar",
      variant: "danger",
    });

    if (ok) {
      await deleteUser(id);
      onDeleted();
    }
  };

  return (
    <>
      <Button variant="destructive" size="sm" onClick={() => handleDelete(userId)}>
        <Trash2 className="h-4 w-4" />
      </Button>
      {Dialog}
    </>
  );
}
```

## Example 2: Confirmation with Custom Labels

Using custom button labels for a specific context:

```tsx
"use client";

import { useConfirmationDialog } from "@/components/confirmationDialog/useConfirmationDialog";
import { Button } from "@/components/ui/button";

export function RevokeAccessButton({ roleId }: { roleId: number }) {
  const { confirm, Dialog } = useConfirmationDialog();

  const handleRevoke = async (id: number) => {
    const confirmed = await confirm({
      title: "Revocar acceso",
      description: "El usuario perderá inmediatamente todos los permisos asociados.",
      confirmLabel: "Revocar acceso",
      cancelLabel: "Mantener",
      variant: "danger",
    });

    if (confirmed) {
      await revokeRole(id);
    }
  };

  return (
    <>
      <Button variant="outline" onClick={() => handleRevoke(roleId)}>
        Revocar
      </Button>
      {Dialog}
    </>
  );
}
```

## Example 3: Non-Destructive Confirmation

Using the default variant for reversible actions:

```tsx
"use client";

import { useConfirmationDialog } from "@/components/confirmationDialog/useConfirmationDialog";
import { Button } from "@/components/ui/button";
import { Archive } from "lucide-react";

export function ArchiveButton({ documentId }: { documentId: number }) {
  const { confirm, Dialog } = useConfirmationDialog();

  const handleArchive = async (id: number) => {
    const ok = await confirm({
      title: "¿Archivar documento?",
      description: "El documento se moverá al archivo.",
      confirmLabel: "Archivar",
      variant: "default",
    });

    if (ok) {
      await archiveDocument(id);
    }
  };

  return (
    <>
      <Button variant="secondary" onClick={() => handleArchive(documentId)}>
        <Archive className="h-4 w-4 mr-2" />
        Archivar
      </Button>
      {Dialog}
    </>
  );
}
```

## Example 4: Multiple Confirmation Buttons

Multiple items each with their own confirmation:

```tsx
"use client";

import { useConfirmationDialog } from "@/components/confirmationDialog/useConfirmationDialog";
import { Button } from "@/components/ui/button";

interface Item {
  id: number;
  name: string;
}

export function ItemList({ items }: { items: Item[] }) {
  const { confirm, Dialog } = useConfirmationDialog();

  const handleDelete = async (item: Item) => {
    const ok = await confirm({
      title: `¿Eliminar "${item.name}"?`,
      description: "Esta acción no se puede deshacer.",
      variant: "danger",
    });

    if (ok) {
      await deleteItem(item.id);
    }
  };

  return (
    <div>
      {items.map((item) => (
        <div key={item.id}>
          <span>{item.name}</span>
          <Button variant="destructive" size="sm" onClick={() => handleDelete(item)}>
            Eliminar
          </Button>
        </div>
      ))}
      {Dialog}
    </div>
  );
}
```

## See Also
- [Spec: Confirmation Dialog](./SPEC.md) — full spec
- [IO: Confirmation Dialog](./IO.md) — component API
- [Spec: GenericModal](../modals/SPEC.md) — modal compound components