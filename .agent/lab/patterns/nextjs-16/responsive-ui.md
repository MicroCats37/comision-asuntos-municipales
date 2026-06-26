# Next.js 16: Responsive UI Utilities

## Context
Tailwind v4 @utility classes for responsive grids, flex wrap, and page section spacing — following mobile-first principles.

## Recipe

### Auto-fit Grid (no fixed columns)

```css
/* REQUIRED */
grid grid-auto-fill-sm gap-4

/* FORBIDDEN */
grid grid-cols-3  ← fixed, breaks on mobile
```

```tsx
// Card grid that fills available space
<div className="grid grid-auto-fill-sm gap-4">
  {items.map(item => <Card key={item.id} {...item} />)}
</div>

// Wider items (360px min)
<div className="grid grid-auto-fill-md gap-6">
  {features.map(f => <FeatureCard key={f.id} {...f} />)}
</div>
```

### Flex Wrap

```css
/* REQUIRED */
flex flex-wrap gap-3

/* FORBIDDEN */
flex gap-3  ← items overflow instead of wrapping
```

```tsx
// Toolbar/filter row that wraps on mobile
<div className="flex flex-wrap-gap">
  <SearchInput />
  <FilterDropdown />
  <SortSelect />
  <ExportButton />
</div>
```

### Standard Spacing Tokens

```css
page-section      ← standard content section
page-section-sm   ← compact section
```

```tsx
// Standard section with responsive padding
<section className="page-section">
  <h2>Section Title</h2>
  <p>Content...</p>
</section>
```

### Mobile-First Rule

Always write base styles for mobile, add responsive variants for larger screens:

```tsx
// ✅ CORRECT — mobile base, desktop enhanced
<div className="flex flex-col gap-2 md:flex-row md:gap-4">

// ❌ WRONG — desktop-first then override
<div className="md:flex-row flex flex-col gap-4 md:gap-2">
```

### Screen-Height Sections

```tsx
// Fills viewport minus header (~4rem)
<section className="min-h-[calc(100vh-4rem)]">
  <HeroContent />
</section>
```

## Why This Way

Auto-fill grids eliminate media queries for column count. Flex-wrap-gap prevents overflow. Page-section tokens establish vertical rhythm. Mobile-first ensures smallest screens work without needing JavaScript.

## See Also
- [Knowledge: Component Architecture](../../knowledge/nextjs-16/component-architecture.md)
- [Tailwind: Grid Auto Fill](https://tailwindcss.com/docs/grid-template-columns#auto-fill-and-auto-fit)
