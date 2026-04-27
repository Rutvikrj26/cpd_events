/**
 * Cross-cutting Zustand stores.
 *
 * Feature-scoped stores live in `features/{name}/store/`.
 */
export { useThemeStore, startSystemThemeListener } from './themeStore';
export type { Theme, ResolvedTheme } from './themeStore';
export { useUIStore, selectTopDialog } from './uiStore';
export type { DialogDescriptor } from './uiStore';
