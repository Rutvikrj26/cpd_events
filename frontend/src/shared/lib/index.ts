/**
 * Shared library helpers.
 *
 * Pure utilities only — anything that needs React state or DOM lives in
 * `shared/hooks/` instead.
 */
export { useZodForm } from './forms';
export { lazyNamed } from './lazyNamed';
// Re-export the existing legacy `cn` helper so feature code can import
// from a single canonical location (shared/lib) going forward. The
// underlying file stays at @/lib/utils until P1's component migration
// settles to keep the diff small.
export { cn } from '@/lib/utils';
