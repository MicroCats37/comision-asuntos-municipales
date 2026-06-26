# Date Formatter — Usage Examples

## Basic Usage

### Table Column with Formatted Date

```tsx
// In a data table showing users
<UserTable
  data={users}
  columns={[
    { key: 'name', label: 'Nombre' },
    { 
      key: 'createdAt', 
      label: 'Fecha de creación',
      render: (value) => formatDate(value) // "12 de enero de 2025"
    },
  ]}
/>
```

### "Last updated X ago" Relative Format

```tsx
// In a detail view header
<Card>
  <CardHeader>
    <CardTitle>{item.name}</CardTitle>
    <CardDescription>
      Actualizado {formatRelative(item.updatedAt)}
      {/* "Actualizado hace 2 horas" */}
    </CardDescription>
  </CardHeader>
</Card>
```

### Form Field with Short Date

```tsx
// In a form display mode
<FormField label="Fecha de nacimiento">
  <Input value={formatShort(profile.birthDate)} readOnly />
  {/* "12 ene" */}
</FormField>
```

### Form Field with Date and Time

```tsx
// In an audit log entry
<AuditEntry>
  <span>{formatDateTime(log.createdAt)}</span>
  {/* "12 de enero de 2025, 14:30" */}
</AuditEntry>
```

---

## Custom Format Override

### Custom Date Format

```tsx
// When you need ISO format for API payload display
<Input
  value={formatDate(lastSync, { customFormat: 'yyyy-MM-dd' })}
  readOnly
/>
// "2025-01-12"
```

### Custom DateTime Format

```tsx
// 24-hour format with seconds
<time dateTime={formatDateTime(lastSync, { customFormat: 'dd/MM/yyyy HH:mm:ss' })}>
  {formatDateTime(lastSync)}
</time>
```

---

## Locale Override

### English Locale

```tsx
import { enUS } from 'date-fns/locale'

// For international audiences
<span>{formatDate(event.date, { locale: enUS })}</span>
```

---

## Edge Cases

### Null/Undefined Handling

```tsx
// Safe to call with potentially null values
<span>{formatDate(user.lastLogin ?? undefined)}</span>
{/* Returns "" if undefined, proper date if valid */}
```

### Invalid Date String

```tsx
// Invalid strings return empty string — no crashes
formatDate('not-a-date') // ""
formatDate('') // ""
formatDate(NaN) // ""
```

---

## Common Patterns

### Relative Time for Recent Items

```tsx
// Show relative time for items < 7 days old, otherwise full date
function formatSmartDate(date: DateInput): string {
  const parsed = toDate(date)
  if (!parsed) return ''
  
  const daysDiff = differenceInDays(new Date(), parsed)
  if (daysDiff < 7) {
    return formatRelative(date)
  }
  return formatDate(date)
}
```

### Timestamp Display

```tsx
// In activity feeds
<li key={activity.id}>
  <ActivityIcon />
  <span>{activity.description}</span>
  <span className="text-muted-foreground">
    {formatRelative(activity.timestamp)}
  </span>
</li>
```
