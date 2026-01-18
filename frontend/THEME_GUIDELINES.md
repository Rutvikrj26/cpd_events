# Theme Color Usage Guidelines

## Overview

This application uses a semantic, CSS variable-based theming system that supports both light and dark modes. All colors automatically adapt to the current theme without requiring hardcoded dark mode classes.

## Table of Contents

1. [Core Principles](#core-principles)
2. [Semantic Color System](#semantic-color-system)
3. [Usage Examples](#usage-examples)
4. [Component Patterns](#component-patterns)
5. [Migration Guide](#migration-guide)
6. [Common Pitfalls](#common-pitfalls)

---

## Core Principles

### ✅ DO

- **Use semantic color utilities** for state-based colors (success, info, warning, error)
- **Use CSS variables** for base theme colors (background, foreground, card, etc.)
- **Use consistent patterns** across similar components
- **Let Tailwind's dark mode handle transitions** automatically

### ❌ DON'T

- **Never hardcode dark mode color classes** like `dark:bg-green-950` for semantic states
- **Avoid mixing hardcoded colors** with semantic utilities
- **Don't use arbitrary color values** when semantic alternatives exist
- **Don't create one-off color classes** - extend the semantic system instead

---

## Semantic Color System

### Base Theme Colors (CSS Variables)

Located in `src/index.css` - these adapt automatically:

```css
/* Light & Dark mode handled automatically */
--background       /* Page background */
--foreground       /* Main text color */
--card            /* Card backgrounds */
--card-foreground /* Card text */
--muted           /* Muted backgrounds */
--muted-foreground /* Muted text */
--border          /* Border colors */
--input           /* Input borders */
--ring            /* Focus rings */
--primary         /* Primary brand color */
--primary-foreground
--secondary       /* Secondary brand color */
--secondary-foreground
--destructive     /* Destructive actions */
--destructive-foreground
```

**Usage:**
```tsx
<div className="bg-background text-foreground">
  <Card className="bg-card text-card-foreground border border-border">
    <p className="text-muted-foreground">Helper text</p>
  </Card>
</div>
```

---

### State Color Utilities

For success, info, warning, and error states:

#### Success (Green)

```tsx
/* Backgrounds */
.bg-success-subtle       /* Very light green bg - cards, alerts */
.bg-success-container    /* Medium green bg - icon containers */

/* Text */
.text-success           /* Primary success text */
.text-success-muted     /* Lighter success text */

/* Borders */
.border-success         /* Success border color */
.border-success-muted   /* Lighter success border */

/* Icons */
.icon-success           /* Success icon color */
.icon-container-success /* Success icon background + padding */
```

#### Info (Blue)

```tsx
.bg-info-subtle         /* Light blue background */
.bg-info-container      /* Medium blue background */
.text-info             /* Info text color */
.text-info-muted       /* Lighter info text */
.border-info           /* Info border */
.border-info-muted     /* Lighter info border */
.icon-info             /* Info icon color */
.icon-container-info   /* Info icon container */
```

#### Warning (Amber)

```tsx
.bg-warning-subtle         /* Light amber background */
.bg-warning-container      /* Medium amber background */
.text-warning             /* Warning text color */
.text-warning-muted       /* Lighter warning text */
.border-warning           /* Warning border */
.border-warning-muted     /* Lighter warning border */
.icon-warning             /* Warning icon color */
.icon-container-warning   /* Warning icon container */
```

#### Error (Red)

```tsx
.bg-error-subtle         /* Light red background */
.bg-error-container      /* Medium red background */
.text-error             /* Error text color */
.text-error-muted       /* Lighter error text */
.border-error           /* Error border */
.border-error-muted     /* Lighter error border */
.icon-error             /* Error icon color */
.icon-container-error   /* Error icon container */
```

#### Neutral

```tsx
.bg-neutral-card        /* Context-aware card bg (white/gray-800) */
```

---

## Usage Examples

### Success State Card

```tsx
<Card className="border-success bg-success-subtle">
  <CardHeader>
    <div className="flex items-center gap-3">
      <div className="icon-container-success">
        <CheckCircle className="h-5 w-5 icon-success" />
      </div>
      <div>
        <CardTitle className="text-success-muted">
          Operation Successful
        </CardTitle>
        <p className="text-sm text-success">
          Your changes have been saved.
        </p>
      </div>
    </div>
  </CardHeader>
</Card>
```

### Warning Alert

```tsx
<Alert className="bg-warning-subtle border-warning">
  <AlertTriangle className="h-4 w-4 icon-warning" />
  <AlertTitle className="text-warning">Warning</AlertTitle>
  <AlertDescription className="text-warning-muted">
    Please review before continuing.
  </AlertDescription>
</Alert>
```

### Error Message

```tsx
<div className="p-4 rounded-lg bg-error-subtle border border-error">
  <div className="flex items-start gap-2">
    <AlertCircle className="h-4 w-4 icon-error mt-0.5" />
    <div>
      <p className="font-medium text-error-muted">Error occurred</p>
      <p className="text-sm text-error">{errorMessage}</p>
    </div>
  </div>
</div>
```

### Info Banner

```tsx
<div className="bg-info-subtle border-info p-4 rounded-lg">
  <div className="flex items-center gap-3">
    <div className="icon-container-info">
      <Info className="h-5 w-5 icon-info" />
    </div>
    <p className="text-info">
      New features are available in this release.
    </p>
  </div>
</div>
```

---

## Component Patterns

### Status Indicators

```tsx
// Connection status
const StatusCard = ({ connected }: { connected: boolean }) => (
  <Card className={connected ? "border-success bg-success-subtle" : "border-warning bg-warning-subtle"}>
    <div className={connected ? "icon-container-success" : "icon-container-warning"}>
      <Icon className={connected ? "icon-success" : "icon-warning"} />
    </div>
  </Card>
);
```

### Form Validation

```tsx
// Input with success state
<Input 
  className="border-success focus-visible:ring-success" 
  isValid={true}
/>

// Success message
<div className="flex items-center gap-1.5 text-sm text-success mt-1">
  <CheckCircle2 className="h-4 w-4" />
  <span>Email is valid</span>
</div>

// Error message
<p className="text-sm text-error mt-1">
  {error}
</p>
```

### Icon Containers

```tsx
// Use the pre-built icon container classes
<div className="icon-container-success">
  <CheckCircle className="h-5 w-5 icon-success" />
</div>

// Instead of manual styling:
// ❌ DON'T: <div className="p-2 rounded-full bg-green-100 dark:bg-green-900/50">
```

---

## Migration Guide

### From Hardcoded to Semantic

**Before:**
```tsx
<Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20 dark:border-blue-900">
  <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/50">
    <Video className="h-5 w-5 text-blue-600 dark:text-blue-400" />
  </div>
  <p className="text-blue-700 dark:text-blue-300">Info message</p>
</Card>
```

**After:**
```tsx
<Card className="border-info bg-info-subtle">
  <div className="icon-container-info">
    <Video className="h-5 w-5 icon-info" />
  </div>
  <p className="text-info-muted">Info message</p>
</Card>
```

### Common Replacements

| Old (Hardcoded) | New (Semantic) |
|-----------------|----------------|
| `bg-green-50/50 dark:bg-green-950/20` | `bg-success-subtle` |
| `bg-green-100 dark:bg-green-900/50` | `bg-success-container` |
| `text-green-600 dark:text-green-400` | `text-success` |
| `text-green-700 dark:text-green-300` | `text-success-muted` |
| `border-green-200 dark:border-green-900` | `border-success` |
| `bg-blue-50/50 dark:bg-blue-950/20` | `bg-info-subtle` |
| `text-blue-600 dark:text-blue-400` | `text-info` |
| `bg-amber-50/50 dark:bg-amber-950/20` | `bg-warning-subtle` |
| `text-amber-700 dark:text-amber-300` | `text-warning` |
| `bg-red-50 dark:bg-red-950/30` | `bg-error-subtle` |
| `text-red-600 dark:text-red-400` | `text-error` |
| `bg-white dark:bg-gray-800` | `bg-neutral-card` |

---

## Common Pitfalls

### ❌ Mixing Hardcoded and Semantic

```tsx
// BAD: Mixed approach
<div className="bg-success-subtle border-blue-200 dark:border-blue-900">
  <Icon className="text-success" />
</div>

// GOOD: Consistent semantic classes
<div className="bg-success-subtle border-success">
  <Icon className="icon-success" />
</div>
```

### ❌ Inconsistent Color Shades

```tsx
// BAD: Using different shades for same semantic meaning
<div className="text-green-600">Success</div>
<div className="text-green-400">Also success</div>

// GOOD: Use semantic utilities
<div className="text-success">Success</div>
<div className="text-success">Also success</div>
```

### ❌ One-Off Custom Colors

```tsx
// BAD: Creating custom colors for states
<div className="bg-emerald-50 dark:bg-emerald-950/20">
  Custom success color
</div>

// GOOD: Extend the semantic system in index.css if needed
// Then use: <div className="bg-success-subtle">
```

---

## Special Cases

### Prose Content

For markdown/rich text, use the Tailwind Typography plugin:

```tsx
<div className="prose prose-slate dark:prose-invert max-w-none">
  {/* Markdown content */}
</div>
```

This is acceptable as it's a standard Tailwind pattern.

### Gradient Backgrounds

For decorative gradients that maintain the blue theme:

```tsx
<div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 border border-info">
  {/* Content */}
</div>
```

Use `border-info` for consistency, but gradients can remain as-is since they're decorative.

### Theme Toggle Icon

The mode toggle component intentionally uses rotation/scale transforms:

```tsx
<Sun className="dark:-rotate-90 dark:scale-0" />
<Moon className="dark:rotate-0 dark:scale-100" />
```

This is acceptable as it's for animation, not color.

---

## Testing Dark Mode

### Manual Testing

1. Toggle theme using the mode switcher (Sun/Moon icon)
2. Verify all semantic colors look appropriate
3. Check contrast ratios meet accessibility standards
4. Test focus states in both themes

### Automated Testing (Future)

See `theme-audit-49` for visual regression testing setup.

---

## Extending the System

If you need a new semantic state (e.g., "neutral-info"):

1. Add CSS variables to `src/index.css`:

```css
.dark {
  /* Add your new semantic color */
  --neutral-info: 200 20% 50%;
}
```

2. Create utility classes:

```css
@layer utilities {
  .bg-neutral-info-subtle {
    @apply bg-slate-50 dark:bg-slate-950/20;
  }
  
  .text-neutral-info {
    @apply text-slate-600 dark:text-slate-400;
  }
}
```

3. Document usage in this guide

---

## Resources

- **CSS Variables:** `src/index.css` (lines 6-113)
- **Semantic Utilities:** `src/index.css` (lines 207-309)
- **Theme Provider:** `src/components/theme-provider.tsx`
- **Mode Toggle:** `src/components/mode-toggle.tsx`

---

## Questions?

If you're unsure which class to use, ask yourself:

1. **Is this a semantic state?** → Use state utilities (`success`, `info`, `warning`, `error`)
2. **Is this base UI?** → Use CSS variables (`bg-card`, `text-foreground`, etc.)
3. **Is this decorative?** → Consider if it needs dark mode at all

When in doubt, prefer semantic utilities over hardcoded colors.

---

**Last Updated:** January 18, 2026  
**Maintained by:** Development Team
