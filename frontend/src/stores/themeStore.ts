import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Theme store — replaces the legacy ThemeProvider context.
 *
 * Single source of truth for theme. Persists `theme` choice to localStorage,
 * subscribes to `prefers-color-scheme` when theme is "system", and toggles
 * the `dark` / `light` class on `<html>`.
 *
 * Usage:
 *     const theme = useThemeStore(s => s.theme);
 *     const setTheme = useThemeStore(s => s.setTheme);
 */

export type Theme = 'dark' | 'light' | 'system';
export type ResolvedTheme = 'dark' | 'light';

interface ThemeState {
    /** User's selected theme (may be 'system'). */
    theme: Theme;
    /** Concrete theme actually applied to the DOM. */
    resolved: ResolvedTheme;
    setTheme: (theme: Theme) => void;
    /** Called by the bootstrap effect — re-evaluates 'system' against the OS pref. */
    refreshSystem: () => void;
}

const STORAGE_KEY = 'accredit-theme';
const LEGACY_KEY = 'vite-ui-theme'; // ThemeProvider's old localStorage key

function resolveSystem(): ResolvedTheme {
    if (typeof window === 'undefined') return 'light';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/**
 * Migrate from the legacy raw-string key to the Zustand-persist JSON shape.
 * Runs once at module load. Idempotent (only migrates when legacy exists
 * and new is missing).
 */
function migrateLegacyTheme(): void {
    if (typeof window === 'undefined') return;
    try {
        if (window.localStorage.getItem(STORAGE_KEY)) return; // already migrated
        const legacy = window.localStorage.getItem(LEGACY_KEY);
        if (!legacy) return;
        if (legacy !== 'light' && legacy !== 'dark' && legacy !== 'system') return;
        // Match Zustand persist's wrapper shape so the seed survives rehydration.
        window.localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({ state: { theme: legacy }, version: 0 })
        );
        window.localStorage.removeItem(LEGACY_KEY);
    } catch {
        // Quota / access errors — fall through; user keeps default 'system'.
    }
}

migrateLegacyTheme();

function applyToDom(resolved: ResolvedTheme) {
    if (typeof document === 'undefined') return;
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(resolved);
}

export const useThemeStore = create<ThemeState>()(
    persist(
        (set, get) => ({
            theme: 'system',
            resolved: resolveSystem(),
            setTheme: (theme) => {
                const resolved: ResolvedTheme = theme === 'system' ? resolveSystem() : theme;
                applyToDom(resolved);
                set({ theme, resolved });
            },
            refreshSystem: () => {
                if (get().theme !== 'system') return;
                const resolved = resolveSystem();
                if (resolved !== get().resolved) {
                    applyToDom(resolved);
                    set({ resolved });
                }
            },
        }),
        {
            name: STORAGE_KEY,
            // Only persist the user's explicit choice; resolved is recomputed.
            partialize: (state) => ({ theme: state.theme }),
            onRehydrateStorage: () => (state) => {
                if (!state) return;
                const resolved: ResolvedTheme = state.theme === 'system' ? resolveSystem() : state.theme;
                applyToDom(resolved);
                state.resolved = resolved;
            },
        }
    )
);

/**
 * Subscribe to OS-level theme changes once. Call from the app shell.
 */
export function startSystemThemeListener(): () => void {
    if (typeof window === 'undefined') return () => undefined;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => useThemeStore.getState().refreshSystem();
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
}
