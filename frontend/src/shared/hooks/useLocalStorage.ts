import { useCallback, useEffect, useState } from 'react';

/**
 * useLocalStorage — typed, SSR-safe, cross-tab-aware.
 *
 * - Initial value is read from localStorage if present, otherwise `initial`.
 * - Updates write through to localStorage (JSON-serialized).
 * - The `storage` event listener keeps multiple tabs in sync.
 *
 * Usage:
 *     const [draft, setDraft, removeDraft] = useLocalStorage<Draft>('event-draft', emptyDraft);
 */
export function useLocalStorage<T>(
    key: string,
    initial: T
): [T, (value: T | ((prev: T) => T)) => void, () => void] {
    const read = useCallback((): T => {
        if (typeof window === 'undefined') return initial;
        try {
            const raw = window.localStorage.getItem(key);
            return raw === null ? initial : (JSON.parse(raw) as T);
        } catch {
            return initial;
        }
    }, [key, initial]);

    const [value, setValue] = useState<T>(read);

    const setStoredValue = useCallback(
        (next: T | ((prev: T) => T)) => {
            setValue(prev => {
                const resolved = typeof next === 'function' ? (next as (p: T) => T)(prev) : next;
                try {
                    window.localStorage.setItem(key, JSON.stringify(resolved));
                } catch {
                    // Quota or privacy mode — fall back to in-memory only.
                }
                return resolved;
            });
        },
        [key]
    );

    const remove = useCallback(() => {
        try {
            window.localStorage.removeItem(key);
        } catch {
            // ignore
        }
        setValue(initial);
    }, [key, initial]);

    useEffect(() => {
        if (typeof window === 'undefined') return;
        const handler = (e: StorageEvent) => {
            if (e.key !== key) return;
            try {
                setValue(e.newValue === null ? initial : (JSON.parse(e.newValue) as T));
            } catch {
                // ignore malformed
            }
        };
        window.addEventListener('storage', handler);
        return () => window.removeEventListener('storage', handler);
    }, [key, initial]);

    return [value, setStoredValue, remove];
}
