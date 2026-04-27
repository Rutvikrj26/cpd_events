import { useEffect } from 'react';
import { startSystemThemeListener } from '@/stores';

/**
 * Mount once at the app shell. Subscribes to OS-level theme changes so
 * the resolved theme follows `prefers-color-scheme` when the user has
 * picked "system". The actual DOM class write happens inside the store.
 */
export function ThemeBootstrap() {
    useEffect(() => {
        return startSystemThemeListener();
    }, []);
    return null;
}
