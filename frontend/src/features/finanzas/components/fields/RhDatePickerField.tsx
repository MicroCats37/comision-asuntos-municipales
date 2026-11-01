import { format } from "date-fns";
import { es } from "date-fns/locale";
import { Calendar as CalendarIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

interface RhDatePickerFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}

/** Uses the same shadcn Calendar popover pattern as Legacy liquidation forms. */
export function RhDatePickerField({
  id,
  label,
  value,
  onChange,
}: RhDatePickerFieldProps) {
  const selectedDate = value ? new Date(value) : undefined;

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            id={id}
            variant="outline"
            className="relative h-10 w-full justify-start rounded-xl pl-9 text-left font-normal"
          >
            <CalendarIcon className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            {selectedDate ? (
              format(selectedDate, "PPP", { locale: es })
            ) : (
              <span className="text-muted-foreground">Seleccionar...</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={selectedDate}
            onSelect={(date) =>
              onChange(date ? format(date, "yyyy-MM-dd") : "")
            }
            locale={es}
            initialFocus
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}
