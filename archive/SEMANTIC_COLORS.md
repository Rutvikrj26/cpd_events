# Semantic Color System

This project uses a **semantic color system** to ensure consistent theming and dark mode support. Instead of hardcoded Tailwind color classes (like `bg-blue-500` or `text-gray-600`), we use semantic class names that adapt to the current theme.

## Why Semantic Colors?

1. **Dark Mode Support**: Theme-aware colors automatically adapt to light/dark mode
2. **Consistency**: Ensures colors convey meaning (success, error, warning, etc.) across the app
3. **Maintainability**: Changing theme colors only requires updating CSS variables, not every component
4. **Accessibility**: Semantic colors are designed to meet contrast requirements in both themes

## Available Semantic Classes

All semantic color classes are defined in `/frontend/src/index.css` (lines 207-351).

### Success States (Green)
Use for positive actions, completed states, and success messages.

```tsx
// Backgrounds
className="bg-success-subtle"        // Light green background
className="bg-success-container"     // Icon/badge containers
className="bg-success"               // Solid success background

// Text
className="text-success"             // Success text color
className="icon-success"             // Success icon color

// Borders
className="border-success"           // Success borders
```

**Examples:**
- ✅ Completed task indicators
- ✅ Success notifications
- ✅ "Published" status badges
- ✅ Positive confirmation messages

### Error/Destructive States (Red)
Use for errors, destructive actions, and critical warnings.

```tsx
// Backgrounds
className="bg-error-subtle"          // Light red background
className="bg-destructive/10"        // Alternative light background
className="bg-destructive"           // Solid error background

// Text
className="text-error"               // Error text
className="text-destructive"         // Destructive action text

// Borders
className="border-error"             // Error borders
className="border-destructive"       // Destructive borders
```

**Examples:**
- ❌ Error messages
- ❌ Delete buttons
- ❌ Failed status indicators
- ❌ Validation errors

### Warning States (Amber/Orange)
Use for warnings, cautions, and pending states.

```tsx
// Backgrounds
className="bg-warning-subtle"        // Light amber background

// Text
className="text-warning"             // Warning text color

// Borders
className="border-warning"           // Warning borders
```

**Examples:**
- ⚠️ Warning messages
- ⚠️ Pending approvals
- ⚠️ "Needs attention" states
- ⚠️ Caution indicators

### Info States (Blue)
Use for informational content, primary actions, and neutral emphasis.

```tsx
// Backgrounds
className="bg-info-subtle"           // Light blue background

// Text
className="text-info"                // Info text color

// Borders
className="border-info"              // Info borders
```

**Examples:**
- ℹ️ Informational alerts
- ℹ️ Help text
- ℹ️ "Submitted" status
- ℹ️ Secondary CTAs

### Primary/Accent Colors
Use for primary actions, links, and brand emphasis.

```tsx
// Backgrounds
className="bg-primary"               // Primary background
className="bg-primary/10"            // Light primary background (10% opacity)

// Text
className="text-primary"             // Primary text/accent color

// Borders
className="border-primary"           // Primary borders
```

**Examples:**
- 🔵 Primary buttons (use `<Button>` default variant instead)
- 🔵 Active tabs
- 🔵 Links
- 🔵 Selected states

### Neutral/Muted States
Use for backgrounds, secondary text, and subtle UI elements.

```tsx
// Backgrounds
className="bg-background"            // Main page background
className="bg-card"                  // Card backgrounds
className="bg-muted"                 // Muted background
className="bg-muted/30"              // 30% opacity muted
className="bg-muted/20"              // 20% opacity muted

// Text
className="text-foreground"          // Primary text color
className="text-muted-foreground"    // Secondary/muted text

// Borders
className="border-border"            // Standard borders
```

**Examples:**
- 🔘 Page backgrounds
- 🔘 Secondary text
- 🔘 Disabled states
- 🔘 Subtle separators

## Common Replacements

### Before (Hardcoded) → After (Semantic)

```tsx
// ❌ DON'T: Hardcoded colors
className="bg-gray-50"               → className="bg-muted/30"
className="text-gray-400"            → className="text-muted-foreground"
className="text-gray-600"            → className="text-muted-foreground"
className="border-gray-300"          → className="border-border"

// Success (green)
className="bg-green-50"              → className="bg-success-subtle"
className="text-green-600"           → className="text-success"
className="border-green-200"         → className="border-success"

// Error (red)
className="bg-red-50"                → className="bg-error-subtle"
className="text-red-600"             → className="text-error" or "text-destructive"
className="bg-red-600"               → className="bg-destructive"

// Warning (amber/orange)
className="bg-amber-50"              → className="bg-warning-subtle"
className="text-amber-600"           → className="text-warning"
className="border-amber-200"         → className="border-warning"

// Info (blue)
className="bg-blue-50"               → className="bg-info-subtle"
className="text-blue-600"            → className="text-info"
className="border-blue-200"          → className="border-info"

// Primary/Accent (blue/purple)
className="bg-blue-600"              → Use <Button> default variant or className="bg-primary"
className="text-purple-600"          → className="text-primary"
```

## Buttons

For buttons, prefer using the built-in variants instead of custom colors:

```tsx
// ✅ DO: Use Button variants
<Button>Primary Action</Button>                          // Primary style
<Button variant="outline">Secondary</Button>             // Outline style
<Button variant="destructive">Delete</Button>            // Destructive/error
<Button variant="ghost">Subtle</Button>                  // Ghost/subtle

// ❌ DON'T: Custom button colors
<Button className="bg-blue-600">Action</Button>         // Use default variant instead
<Button className="bg-red-600">Delete</Button>          // Use variant="destructive"
```

## Status Badges

```tsx
// Success
<Badge className="text-success bg-success-subtle border-success">
  Approved
</Badge>

// Warning
<Badge className="text-warning bg-warning-subtle border-warning">
  Pending
</Badge>

// Error
<Badge variant="destructive">
  Failed
</Badge>

// Info
<Badge className="text-info bg-info-subtle border-info">
  In Review
</Badge>
```

## Special Cases

### When to Use Hardcoded Colors

There are rare exceptions where hardcoded colors are acceptable:

1. **Dark mode variants**: `dark:text-gray-100` - These are intentional
2. **Brand logos**: When displaying external logos that require specific colors
3. **Decorative gradients**: `from-blue-950/30` - Pure decoration, not semantic
4. **Typography plugin**: `prose dark:prose-invert` - Tailwind plugin standard

### Loading Spinners

```tsx
// ✅ DO
<Loader2 className="animate-spin text-primary" />
<Loader2 className="animate-spin text-muted-foreground" />

// ❌ DON'T
<Loader2 className="animate-spin text-blue-600" />
```

### Icons

```tsx
// ✅ DO
<CheckCircle className="h-4 w-4 text-success" />
<XCircle className="h-4 w-4 text-destructive" />
<AlertTriangle className="h-4 w-4 text-warning" />
<Info className="h-4 w-4 text-info" />
<User className="h-4 w-4 text-muted-foreground" />

// ❌ DON'T
<CheckCircle className="h-4 w-4 text-green-500" />
<XCircle className="h-4 w-4 text-red-500" />
```

## ESLint Rule

This project includes a custom ESLint rule `local/no-hardcoded-colors` that warns when hardcoded color classes are used. The rule will suggest semantic alternatives.

To run the linter:
```bash
npm run lint
```

## Testing in Dark Mode

To verify your changes work in both themes:

1. Open the app in your browser
2. Toggle dark mode (usually in settings or via system preferences)
3. Verify all colors look appropriate and maintain proper contrast

## Questions?

If you're unsure which semantic class to use:
1. Check this guide for examples
2. Look at similar components in the codebase
3. Check `/frontend/src/index.css` for available classes
4. Ask the team in PR reviews

## Related Files

- `/frontend/src/index.css` - Semantic color definitions (lines 207-351)
- `/frontend/eslint-local-rules.cjs` - ESLint rule for enforcement
- `/frontend/eslint.config.js` - ESLint configuration
