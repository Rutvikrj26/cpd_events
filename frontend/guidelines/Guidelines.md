# System Guidelines

## Core Philosophy

Build interfaces that feel calm, confident, and invisible. The best UI gets out of the user's way. Every element should earn its place—when in doubt, remove it.

## Technical Stack

- React with functional components and hooks
- Tailwind CSS for styling (use design tokens via Tailwind config, not arbitrary values)
- Component library agnostic—wrap third-party components in project abstractions when used

---

## Layout & Structure

- Use semantic HTML: `<main>`, `<section>`, `<nav>`, `<article>`, `<aside>`, `<header>`, `<footer>`
- Flexbox for 1D alignment, CSS Grid for 2D layouts. Avoid absolute positioning except for overlays/tooltips/dropdowns
- Page max-width: 1280px centered with responsive horizontal padding (`px-4 sm:px-6 lg:px-8`)
- Establish clear content zones: navigation, main content area, and contextual sidebars when needed

## Spacing & Rhythm

- Use Tailwind's default spacing scale consistently—don't mix arbitrary values
- Spacing hierarchy: tight within components (2-3), moderate between related elements (4-6), generous between sections (8-16)
- Let content breathe. Generous whitespace signals quality. When layouts feel cramped, add space before adding decoration
- Vertical rhythm: maintain consistent gaps between stacked elements using `space-y-*` or `gap-*`

## Typography

- Restrained type scale: Use 3-4 sizes maximum per page (e.g., `text-sm`, `text-base`, `text-lg`, `text-xl`)
- Hierarchy through weight and color, not just size. Muted secondary text (`text-gray-500`) creates depth
- Body text: `text-base` (16px) minimum, `leading-relaxed` for readability
- Headings: Meaningful hierarchy (`<h1>` → `<h2>` → `<h3>`), never skip levels

## Color & Visual Treatment

- Minimal palette: One primary accent color, neutral grays, semantic colors (success/warning/error)
- Backgrounds: Prefer subtle (`gray-50`, `white`) over bold. Let content be the hero
- Borders: Use sparingly and subtly (`border-gray-200`). Not every container needs a border
- Shadows: Restrained. Small shadows (`shadow-sm`) for elevation hints, larger only for modals/dropdowns
- No gradients unless specifically requested. Flat, solid colors read as more professional

## Visual Hierarchy

- One primary action per view—it should be immediately obvious what to do next
- Progressive disclosure: Show essential information first, details on demand
- Group related items visually; separate unrelated items with space, not lines
- Use size, weight, and color contrast to guide the eye—not decoration

---

## Component Patterns

### Buttons

| Intent      | Treatment                 | Tailwind Example                                      |
| ----------- | ------------------------- | ----------------------------------------------------- |
| Primary     | Solid fill, primary color | `bg-blue-600 text-white hover:bg-blue-700`            |
| Secondary   | Outlined or muted fill    | `border border-gray-300 hover:bg-gray-50`             |
| Ghost       | Text only, minimal        | `text-gray-600 hover:text-gray-900 hover:bg-gray-100` |
| Destructive | Red/danger, use sparingly | `bg-red-600 text-white hover:bg-red-700`              |

- Verb-first labels: "Save changes", "Create project", "Send invite"
- Minimum height: `h-9` (36px) for comfortable click targets
- Consistent padding: `px-4 py-2` for standard, `px-3 py-1.5` for compact
- Loading state: Disable + show spinner, preserve button width

### Forms

- Labels above inputs, always visible (no placeholder-only labels)
- Consistent input sizing: `h-10` height, `px-3` padding, `rounded-md` corners
- Focus states: Clear ring (`focus:ring-2 focus:ring-blue-500 focus:ring-offset-2`)
- Error states: Red border + error message below input in `text-sm text-red-600`
- Group related fields logically; use `<fieldset>` and `<legend>` for field groups
- Action buttons at form bottom: Primary on right, secondary/cancel on left

### Cards

- Consistent internal padding: `p-4` or `p-6`
- Subtle container treatment: `bg-white rounded-lg border border-gray-200` or `shadow-sm`
- If clickable, entire card is the target with hover state (`hover:shadow-md` or `hover:border-gray-300`)
- Content hierarchy: Title → metadata/status → body → actions

### Page Layouts

- Standard page structure:

```
  Header/Nav (sticky if needed)
  └── Main content area (centered, max-width)
      ├── Page header (title, description, primary action)
      ├── Filters/controls (if applicable)
      ├── Content (tables, cards, forms)
      └── Pagination/load more (if applicable)
```

- Page titles: `text-2xl font-semibold` with optional `text-gray-500` subtitle below
- Page-level actions (Create, Export) in page header, aligned right

### Tables

- Header: `text-left text-sm font-medium text-gray-500 uppercase tracking-wide`
- Rows: Subtle dividers (`divide-y divide-gray-200`), hover state for interactive rows
- Cells: Appropriate alignment (text left, numbers right)
- Empty state: Centered message with icon, helpful guidance, and action if applicable

### Empty, Loading, and Error States

Every data-driven component needs three states:

- **Empty**: Friendly illustration/icon + clear message + action to populate ("No projects yet. Create your first project.")
- **Loading**: Skeleton or spinner, maintain layout dimensions to prevent shift
- **Error**: Clear message + retry action. Never just fail silently

---

## Interaction & Feedback

- Hover states on all interactive elements—immediate visual feedback
- Focus states visible and clear for keyboard navigation
- Transitions: Subtle and fast (`transition-colors duration-150`). No bouncy animations
- Confirm destructive actions. State consequences clearly ("This will permanently delete 12 files.")

## Responsive Behavior

- Mobile-first: Default styles for mobile, use `sm:`, `md:`, `lg:` for larger screens
- Breakpoint strategy: `sm` (640px), `md` (768px), `lg` (1024px), `xl` (1280px)
- Stack horizontally-arranged elements vertically on mobile
- Touch targets: Minimum 44x44px on mobile
- Hide non-essential elements on mobile; don't just shrink everything

## Accessibility Baseline

- Logical heading hierarchy, never skip levels
- All images: meaningful `alt` text or `alt=""` for decorative
- Form inputs: Always associated `<label>` elements
- Interactive elements: Keyboard accessible, visible focus states
- Color contrast: 4.5:1 minimum for text
- ARIA only when semantic HTML is insufficient

---

## Code Quality

- Components: Single responsibility, under 150 lines. Extract early and often
- Naming: Descriptive and consistent (`UserProfileCard`, not `Card2` or `ProfileThing`)
- Props: Minimal surface area. Prefer composition over configuration
- Styles: Use Tailwind classes directly; extract to `@apply` only for highly reused patterns
- State: Lift only when necessary. Local state is fine for local concerns
- Comments: Explain _why_, not _what_

## File Organization

```
components/
├── ui/           # Primitives (Button, Input, Card, Modal)
├── forms/        # Form-specific components (FormField, SearchInput)
├── layout/       # Page structure (PageHeader, Sidebar, Container)
└── [feature]/    # Feature-specific components
```

---

## Anti-Patterns to Avoid

- Decorative elements that don't serve function (random icons, excessive dividers)
- Inconsistent spacing—pick values from the scale and stick to them
- Multiple competing calls to action on one screen
- Deeply nested div soup—flatten structure, use semantic elements
- Arbitrary Tailwind values (`w-[347px]`)—use the scale or configure tokens
- Walls of text—break up with hierarchy, whitespace, or progressive disclosure
- Disabled buttons without explanation—tell users why they can't proceed

