"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface RhMonthPickerProps { value: string; max: string; onChange: (value: string) => void; }

const MONTHS = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

export function RhMonthPicker({ value, max, onChange }: RhMonthPickerProps) {
  const [year = "", month = ""] = value.split("-");
  const [maxYear, maxMonth] = max.split("-").map(Number);
  const years = Array.from({ length: maxYear - 2010 + 1 }, (_, index) => String(maxYear - index));
  const update = (nextYear: string, nextMonth: string) => {
    if (!nextYear || !nextMonth) return;
    onChange(`${nextYear}-${nextMonth.padStart(2, "0")}`);
  };

  return <div className="flex items-center gap-2">
    <Select value={year} onValueChange={(nextYear) => update(nextYear, month)}>
      <SelectTrigger className="h-7 min-w-fit text-xs"><SelectValue placeholder="Año" /></SelectTrigger>
      <SelectContent>{years.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent>
    </Select>
    <Select value={month} onValueChange={(nextMonth) => update(year, nextMonth)}>
      <SelectTrigger className="h-7 min-w-fit text-xs"><SelectValue placeholder="Mes" /></SelectTrigger>
      <SelectContent>{MONTHS.map((label, index) => {
        const item = String(index + 1).padStart(2, "0");
        return <SelectItem key={item} value={item} disabled={Number(year) === maxYear && index + 1 > maxMonth}>{label}</SelectItem>;
      })}</SelectContent>
    </Select>
  </div>;
}
