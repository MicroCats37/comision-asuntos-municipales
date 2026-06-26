# Tabs: Inputs & Outputs

## Component API

### GenericTabs Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `tabs` | `TabItem[]` | Yes | — | Array of tab definitions |
| `defaultTab` | `string` | No | First tab | Initial selected tab (local state only) |
| `syncUrl` | `boolean` | No | `false` | Sync tab state with URL |
| `paramName` | `string` | No | `"tab"` | URL query param name when syncUrl=true |
| `className` | `string` | No | `""` | CSS class for wrapper |

### TabItem Interface

```typescript
interface TabItem {
  value: string;
  label: string;
  content: ReactNode;
  disabled?: boolean;
}
```

**Rules:**
- `value` — unique identifier for the tab
- `label` — display text shown in tab trigger
- `content` — ReactNode rendered when tab is active
- `disabled` — optionally disables the tab

## Local State Mode

```tsx
<GenericTabs
  tabs={[
    { value: 'info', label: 'Información', content: <InfoTab /> },
    { value: 'history', label: 'Historial', content: <HistoryTab /> },
  ]}
  defaultTab="info"
/>
```

## URL-Synced Mode

```tsx
<Suspense fallback={<div>Loading...</div>}>
  <GenericTabs
    tabs={[...]}
    syncUrl
    paramName="seccion"
  />
</Suspense>
```

## Data Contracts

### Content Rendering

Content is a `ReactNode` — can be:
- A React component (`<InfoTab />`)
- Inline JSX (`<div><p>Content</p></div>`)
- A fragment (`<><p>Item 1</p><p>Item 2</p></>`)

### Data Fetching Pattern

**❌ DO NOT fetch data inside tab content directly:**

```tsx
// ❌ FORBIDDEN — causes waterfall
<TabItem
  value="users"
  label="Users"
  content={<UserList />} // UserList fetches inside!
/>
```

**✅ DO fetch data in parent, pass as prop:**

```tsx
// ✅ CORRECT — data fetched at parent level
const { data: users } = useQuery(...);

<TabItem
  value="users"
  label="Users"
  content={<UserList users={users} />}
/>
```

## See Also
- [Spec: Tabs](./SPEC.md) — full spec
