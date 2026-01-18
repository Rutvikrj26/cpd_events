# Hardcoded Colors Comprehensive Audit

**Date:** January 2026  
**Total Issues Found:** ~600+ hardcoded color instances

## Executive Summary

A comprehensive scan of the frontend codebase revealed **600+ hardcoded color utilities** that need to be replaced with theme-aware semantic classes. These hardcoded colors break dark mode functionality and create maintenance issues.

## Impact Analysis

### Files by Issue Count (Top 20)

| Rank | File | Instances | Priority |
|------|------|-----------|----------|
| 1 | `pages/public/EventDetail.tsx` | 42 | HIGH |
| 2 | `pages/public/EventRegistration.tsx` | 35 | HIGH |
| 3 | `pages/organizations/courses/manage/CurriculumTab.tsx` | 28 | HIGH |
| 4 | `pages/dashboard/organizer/EventManagement.tsx` | 18 | HIGH |
| 5 | `components/certificates/CertificateTemplatesList.tsx` | 14 | HIGH |
| 6 | `pages/dashboard/attendee/CertificateDetail.tsx` | 12 | MEDIUM |
| 7 | `components/events/wizard/steps/StepSettings.tsx` | 12 | MEDIUM |
| 8 | `pages/registrations/MyRegistrationsPage.tsx` | 9 | MEDIUM |
| 9 | `pages/organizations/TeamManagementPage.tsx` | 9 | MEDIUM |
| 10 | `components/badges/BadgeTemplatesList.tsx` | 9 | MEDIUM |
| 11 | `components/badges/BadgeDesigner.tsx` | 9 | MEDIUM |
| 12 | `pages/organizations/AcceptInvitationPage.tsx` | 8 | LOW |
| 13 | `components/certificates/FieldPositionEditor.tsx` | 8 | LOW |
| 14 | `components/custom/QuizBuilder.tsx` | 7 | LOW |
| 15-20 | Various files | 5-6 each | LOW |

## Breakdown by Category

### Background Colors
- `bg-white`: 26 instances
- `bg-gray-*`: 29 instances
- `bg-slate-*`: 5 instances
- `bg-red-*`: 25 instances (ERROR states)
- `bg-green-*`: 42 instances (SUCCESS states)
- `bg-blue-*`: 39 instances (INFO states)
- `bg-amber-*`: 26 instances (WARNING states)
- `bg-yellow-*`: 11 instances (WARNING states)

**Total Background Issues:** ~200

### Text Colors
- `text-white`: 37 instances
- `text-gray-*`: 53 instances
- `text-slate-*`: 13 instances
- `text-red-*`: 32 instances (ERROR states)
- `text-green-*`: 62 instances (SUCCESS states)
- `text-blue-*`: 61 instances (INFO states)
- `text-amber-*`: 45 instances (WARNING states)
- `text-yellow-*`: 16 instances (WARNING states)

**Total Text Issues:** ~320

### Border Colors
- `border-gray-*`: 17 instances
- `border-slate-*`: 10 instances
- `border-red-*`: 8 instances (ERROR states)
- `border-green-*`: 19 instances (SUCCESS states)
- `border-blue-*`: 19 instances (INFO states)

**Total Border Issues:** ~80

## Common Pattern Replacements

### 1. Success/Green States
**Current (Bad):**
```tsx
<div className="bg-green-50 border border-green-200">
  <CheckCircle className="text-green-600" />
  <p className="text-green-700">Success!</p>
</div>
```

**Fixed (Good):**
```tsx
<div className="bg-success-subtle border border-success">
  <CheckCircle className="text-success" />
  <p className="text-success">Success!</p>
</div>
```

### 2. Error/Red States
**Current (Bad):**
```tsx
<div className="bg-red-50 border border-red-200">
  <AlertCircle className="text-red-600" />
  <p className="text-red-700">Error occurred</p>
</div>
```

**Fixed (Good):**
```tsx
<div className="bg-error-subtle border border-error">
  <AlertCircle className="text-error" />
  <p className="text-error">Error occurred</p>
</div>
```

### 3. Warning/Amber States
**Current (Bad):**
```tsx
<div className="bg-amber-50 border border-amber-200">
  <AlertTriangle className="text-amber-600" />
  <p className="text-amber-700">Warning!</p>
</div>
```

**Fixed (Good):**
```tsx
<div className="bg-warning-subtle border border-warning">
  <AlertTriangle className="text-warning" />
  <p className="text-warning">Warning!</p>
</div>
```

### 4. Info/Blue States
**Current (Bad):**
```tsx
<div className="bg-blue-50 border border-blue-200">
  <Info className="text-blue-600" />
  <p className="text-blue-700">Information</p>
</div>
```

**Fixed (Good):**
```tsx
<div className="bg-info-subtle border border-info">
  <Info className="text-info" />
  <p className="text-info">Information</p>
</div>
```

### 5. Neutral/Gray States
**Current (Bad):**
```tsx
<div className="bg-gray-50">
  <p className="text-gray-400">Disabled</p>
  <span className="text-gray-600">Secondary text</span>
</div>
```

**Fixed (Good):**
```tsx
<div className="bg-muted/30">
  <p className="text-muted-foreground">Disabled</p>
  <span className="text-muted-foreground">Secondary text</span>
</div>
```

### 6. White Backgrounds
**Current (Bad):**
```tsx
<Dialog>
  <DialogContent className="bg-white">
    <div className="bg-white border-gray-200">
      Content
    </div>
  </DialogContent>
</Dialog>
```

**Fixed (Good):**
```tsx
<Dialog>
  <DialogContent className="bg-card">
    <div className="bg-card border-border">
      Content
    </div>
  </DialogContent>
</Dialog>
```

## Special Cases

### ReactQuill Editors
**Files Affected:** 6 files
- `CertificateTemplatesList.tsx`
- `BadgeTemplatesList.tsx`
- `SessionEditor.tsx`
- `CreateCoursePage.tsx`
- `CurriculumTab.tsx`
- `CreateOrganizationPage.tsx`

**Issue:** All have `className="bg-white mb-4"` and placeholder text is invisible in dark mode.

**Solution:**
1. Remove `bg-white` from ReactQuill components
2. Add global Quill CSS to `index.css`:

```css
/* Quill Editor Theme Support */
.ql-container {
  @apply bg-background border-border;
}

.ql-editor {
  @apply text-foreground;
}

.ql-editor.ql-blank::before {
  @apply text-muted-foreground;
  font-style: italic;
}

.ql-toolbar {
  @apply bg-muted/30 border-border;
}

.ql-stroke {
  @apply stroke-foreground;
}

.ql-fill {
  @apply fill-foreground;
}

.ql-picker-label {
  @apply text-foreground;
}
```

### Upload/File Drop Zones
**Pattern:**
```tsx
// Bad
className={`border-2 border-dashed ${
  hasFile 
    ? 'border-green-400 bg-green-50' 
    : 'border-gray-300 hover:border-blue-400'
}`}

// Good
className={`border-2 border-dashed ${
  hasFile 
    ? 'border-success bg-success-subtle' 
    : 'border-border hover:border-primary'
}`}
```

### Status Badges
```tsx
// Bad
const getStatusColor = (status) => {
  if (status === 'live') return 'bg-red-500 text-white';
  if (status === 'upcoming') return 'bg-yellow-500 text-yellow-950';
  if (status === 'completed') return 'bg-green-500 text-white';
  return 'bg-gray-500 text-white';
};

// Good
const getStatusColor = (status) => {
  if (status === 'live') return 'bg-destructive text-destructive-foreground';
  if (status === 'upcoming') return 'bg-warning text-foreground';
  if (status === 'completed') return 'bg-success text-white';
  return 'bg-muted text-muted-foreground';
};
```

### Loading Spinners
```tsx
// Bad
<Loader2 className="text-blue-600 animate-spin" />

// Good
<Loader2 className="text-primary animate-spin" />
```

## Implementation Plan

### Phase 1: Critical Fixes (Immediate)
1. ✅ Add ReactQuill dark mode CSS to `index.css`
2. Fix `EventDetail.tsx` (42 instances)
3. Fix `EventRegistration.tsx` (35 instances)
4. Fix `CurriculumTab.tsx` (28 instances)

### Phase 2: High Priority (This Sprint)
5. Fix `EventManagement.tsx` (18 instances)
6. Fix `CertificateTemplatesList.tsx` (14 instances)
7. Fix all 6 ReactQuill component files

### Phase 3: Medium Priority (Next Sprint)
8. Fix dashboard components (12-9 instances each)
9. Fix badge and certificate designers
10. Fix team management pages

### Phase 4: Cleanup (Future)
11. Fix remaining low-priority files
12. Add linting rules to prevent hardcoded colors
13. Update developer guidelines

## Prevention

### ESLint Rule Recommendation
Add to `.eslintrc`:
```json
{
  "rules": {
    "no-restricted-syntax": [
      "error",
      {
        "selector": "Literal[value=/bg-(white|gray|slate|red|green|blue|amber|yellow)-/]",
        "message": "Use semantic theme classes instead of hardcoded colors"
      }
    ]
  }
}
```

### Pre-commit Hook
```bash
#!/bin/bash
# Check for hardcoded colors in staged files
if git diff --cached --name-only | grep -E '\.(tsx|ts)$' | xargs grep -E 'bg-(white|gray|slate)-[0-9]|text-(gray|slate)-[0-9]' ; then
  echo "❌ Found hardcoded colors. Please use semantic theme classes."
  exit 1
fi
```

## Progress Tracking

- [x] Initial audit complete
- [x] Semantic utility classes created
- [x] Documentation written
- [ ] Phase 1 fixes (0/3 files)
- [ ] Phase 2 fixes (0/3 files)
- [ ] Phase 3 fixes (0/6 files)
- [ ] Phase 4 fixes (0/remaining files)
- [ ] ESLint rules added
- [ ] Pre-commit hook added

## Resources

- Theme Guidelines: `/frontend/THEME_GUIDELINES.md`
- Semantic Classes: `/frontend/src/index.css` (lines 207-309)
- Audit Report: `/frontend/THEME_AUDIT_REPORT.md`
