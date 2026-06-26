# Smart File Field Component

A reusable file upload component with `useController`, badge display, and generic file validation.

## Concept

Build a file input component that:
- Integrates with react-hook-form via `useController`
- Displays current file(s) with badges
- Supports generic file type/size validation
- Shows preview for images
- Handles multiple files when needed

## Implementation Pattern

```typescript
"use client";

import { useController, useWatch } from "react-hook-form";
import { Upload, X, FileText, Image as ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface SmartFileFieldProps {
  control: any;
  name: string;
  label: string;
  accept?: string;           // e.g., "image/*,.pdf"
  maxSizeMB?: number;        // Default: 5
  multiple?: boolean;        // Default: false
  helperText?: string;
  required?: boolean;
}

export const SmartFileField: FC<SmartFileFieldProps> = ({
  control,
  name,
  label,
  accept = "*",
  maxSizeMB = 5,
  multiple = false,
  helperText,
  required,
}) => {
  const {
    field: { onChange, value },
    fieldState: { error },
  } = useController({
    name,
    control,
    rules: {
      validate: {
        validateFile: (files) => {
          if (!files || (Array.isArray(files) && files.length === 0)) {
            return required ? "Este campo es requerido" : true;
          }
          
          const fileList = multiple ? files : [files];
          
          for (const file of fileList) {
            if (file.size > maxSizeMB * 1024 * 1024) {
              return `El archivo excede ${maxSizeMB}MB`;
            }
          }
          return true;
        },
      },
    },
  });

  const currentValue = useWatch({ control, name });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    
    if (multiple) {
      onChange(files);
    } else {
      onChange(files[0]);
    }
  };

  const removeFile = () => {
    onChange(multiple ? [] : null);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const isImage = (file: File) => file.type.startsWith("image/");

  const renderFileBadge = (file: File, index: number) => (
    <Badge key={index} variant="secondary" className="gap-1.5 pr-1">
      {isImage(file) ? (
        <ImageIcon className="w-3 h-3" />
      ) : (
        <FileText className="w-3 h-3" />
      )}
      <span className="truncate max-w-[150px]">{file.name}</span>
      <span className="text-muted-foreground text-xs">
        ({formatFileSize(file.size)})
      </span>
      <button
        type="button"
        onClick={removeFile}
        className="ml-1 hover:text-destructive"
      >
        <X className="w-3 h-3" />
      </button>
    </Badge>
  );

  return (
    <div className="space-y-2">
      <Label>
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      
      {/* Hidden file input */}
      <input
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={handleFileChange}
        className="hidden"
        id={name}
      />
      
      {/* Upload area */}
      <label
        htmlFor={name}
        className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer hover:bg-muted/50 transition-colors"
      >
        <Upload className="w-8 h-8 mb-2 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">
          Clic para subir {multiple ? "archivos" : "un archivo"}
        </span>
      </label>

      {/* Current file(s) display */}
      {currentValue && (
        <div className="flex flex-wrap gap-2">
          {multiple 
            ? Array.from(currentValue).map((file, i) => 
                renderFileBadge(file, i))
            : renderFileBadge(currentValue, 0)
          }
        </div>
      )}

      {/* Error message */}
      {error && (
        <p className="text-sm text-destructive">{error.message}</p>
      )}

      {/* Helper text */}
      {helperText && !error && (
        <p className="text-xs text-muted-foreground">{helperText}</p>
      )}
    </div>
  );
};
```

## Integration with GenericForm

To use in `GenericForm`, register as a custom field:

```typescript
const formConfig = {
  fields: [
    {
      name: "documento",
      type: "custom",
      label: "Documento de identidad",
    },
  ],
  customFields: {
    documento: (methods) => (
      <SmartFileField
        control={methods.control}
        name="documento"
        label="Documento de identidad"
        accept=".pdf,.jpg,.jpeg,.png"
        maxSizeMB={10}
      />
    ),
  },
};
```

## Validation Rules

The component supports:

| Rule | Description |
|------|-------------|
| `accept` | MIME types allowed (e.g., `"image/*"`, `".pdf,.doc"`) |
| `maxSizeMB` | Maximum file size in megabytes |
| `multiple` | Allow multiple files |
| `required` | Field cannot be empty |

## Extending with Preview

For image files, add preview functionality:

```typescript
const [preview, setPreview] = useState<string | null>(null);

// In handleFileChange for images:
if (isImage(file)) {
  const reader = new FileReader();
  reader.onload = () => setPreview(reader.result as string);
  reader.readAsDataURL(file);
}

// Display preview
{preview && (
  <img src={preview} alt="Preview" className="w-32 h-32 object-cover rounded" />
)}
```

## Best Practices

1. **Use `useController`** for proper react-hook-form integration
2. **Validate on both client and server** - client validation improves UX
3. **Provide clear file requirements** in helperText
4. **Handle removal** - always provide a way to clear the selected file
5. **Show file metadata** - name and size help users confirm their selection
