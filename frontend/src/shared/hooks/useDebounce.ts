import { useEffect, useState } from 'react';

/**
 * Returns a value that lags `value` by `delayMs`. Useful for input that
 * triggers a network call (search, filter) — debounce the *value* rather
 * than the handler so the latest input always wins on rapid typing.
 *
 * Usage:
 *     const [query, setQuery] = useState('');
 *     const debouncedQuery = useDebounce(query, 250);
 *     useEffect(() => fetch(debouncedQuery), [debouncedQuery]);
 */
export function useDebounce<T>(value: T, delayMs = 250): T {
    const [debounced, setDebounced] = useState(value);

    useEffect(() => {
        const id = setTimeout(() => setDebounced(value), delayMs);
        return () => clearTimeout(id);
    }, [value, delayMs]);

    return debounced;
}
