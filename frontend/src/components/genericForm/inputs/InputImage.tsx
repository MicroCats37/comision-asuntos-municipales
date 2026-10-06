// genericForm/inputs/InputImage.tsx
"use client";

import { ExternalLink, ImageIcon, Upload, X } from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { useController } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { resolveImageUrl } from "@/lib/utils";
import type { InputComponentProps } from "./types";

/**
 * Input para imágenes con previsualización.
 * Maneja archivos individuales.
 */
export const InputImage: React.FC<InputComponentProps> = ({
  field,
  control,
  error,
  id,
}) => {
  const {
    field: { onChange, value: hookValue },
  } = useController({ name: field.name, control });

  const internalId = id || `image-upload-${field.name}`;

  const [preview, setPreview] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  // Intentar cargar previsualización inicial si hay un valor (URL)
  useEffect(() => {
    const initialValue = field.defaultValue;
    if (initialValue && typeof initialValue === "string") {
      setPreview(resolveImageUrl(initialValue));
    }
  }, [field.defaultValue]);

  // Sincronizar previsualización si el valor cambia externamente o es un File
  useEffect(() => {
    if (hookValue instanceof File) {
      setFileName(hookValue.name);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result as string);
      };
      reader.readAsDataURL(hookValue);
    } else if (typeof hookValue === "string") {
      // Si es una URL o ruta
      setPreview(resolveImageUrl(hookValue));
      setFileName(hookValue.split("/").pop() || null);
    } else if (!hookValue) {
      setPreview(null);
      setFileName(null);
    }
  }, [hookValue]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onChange(file); // Actualizar Hook Form con el ARCHIVO (no FileList)
    }
  };

  const clearImage = () => {
    onChange(null);
    // Resetear el valor en el input si es posible
    const input = document.getElementById(internalId) as HTMLInputElement;
    if (input) input.value = "";
  };

  return (
    <div className="space-y-4">
      <div
        className={`relative group border-2 border-dashed rounded-2xl overflow-hidden transition-all flex flex-col items-center justify-center min-h-[160px] bg-muted/5 ${
          error
            ? "border-destructive/50"
            : "border-muted-foreground/20 hover:border-primary/50"
        }`}
      >
        {preview ? (
          <div className="relative w-full h-full min-h-[160px]">
            <img
              src={preview}
              alt="Preview"
              className="w-full h-full object-cover max-h-[300px]"
            />
            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="rounded-xl"
                onClick={() => window.open(preview, "_blank")}
                title="Ver imagen original"
              >
                <ExternalLink className="w-4 h-4 mr-2" />
                Ver
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="rounded-xl"
                onClick={() => document.getElementById(internalId)?.click()}
              >
                <Upload className="w-4 h-4 mr-2" />
                Cambiar
              </Button>
              <Button
                type="button"
                variant="destructive"
                size="sm"
                className="rounded-xl"
                onClick={clearImage}
              >
                <X className="w-4 h-4 mr-2" />
                Quitar
              </Button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            className="w-full h-full p-8 flex flex-col items-center justify-center gap-3 text-muted-foreground hover:text-primary transition-colors"
            onClick={() => document.getElementById(internalId)?.click()}
          >
            <div className="p-4 bg-primary/5 rounded-full group-hover:bg-primary/10 transition-colors">
              <ImageIcon className="w-8 h-8" />
            </div>
            <div className="text-center">
              <p className="font-semibold text-sm">
                Haga clic para subir una imagen
              </p>
              <p className="text-xs opacity-70 mt-1">
                PNG, JPG o WEBP (Máx. 5MB)
              </p>
            </div>
          </button>
        )}

        <input
          id={internalId}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleFileChange}
        />
      </div>

      {fileName && !error && (
        <p className="text-[10px] font-mono text-muted-foreground bg-muted/30 px-2 py-1 rounded truncate">
          Archivo: {fileName}
        </p>
      )}
    </div>
  );
};
