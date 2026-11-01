import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface RhCipFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  onEnter?: () => void;
}

export const isValidRhCip = (value: string) => /^\d{6}$/.test(value);

export function RhCipField({
  id,
  label,
  value,
  onChange,
  onEnter,
}: RhCipFieldProps) {
  const hasValue = value.length > 0;
  const isValid = isValidRhCip(value);

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        value={value}
        inputMode="numeric"
        maxLength={6}
        onChange={(event) => onChange(event.target.value.replace(/\D/g, ""))}
        onKeyDown={(event) => {
          if (event.key === "Enter" && isValid) onEnter?.();
        }}
        placeholder="Ej. 123456"
        className="h-10 rounded-xl font-semibold"
        aria-describedby={`${id}-hint ${id}-error`}
        aria-invalid={hasValue && !isValid}
      />
      <p id={`${id}-hint`} className="text-xs text-muted-foreground">
        Ingresa los 6 dígitos del CIP.
      </p>
      {hasValue && !isValid && (
        <p id={`${id}-error`} className="text-xs text-destructive">
          El CIP debe tener exactamente 6 dígitos.
        </p>
      )}
    </div>
  );
}
