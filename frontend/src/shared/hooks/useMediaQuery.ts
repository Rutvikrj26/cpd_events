import { useEffect, useState } from 'react';

/**
 * useMediaQuery — subscribes to a CSS media query and returns its current
 * match state. Returns false during SSR.
 *
 * Usage:
 *     const isDesktop = useMediaQuery('(min-width: 1024px)');
 *     const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');
 */
export function useMediaQuery(query: string): boolean {
    const [matches, setMatches] = useState(() => {
        if (typeof window === 'undefined') return false;
        return window.matchMedia(query).matches;
    });

    useEffect(() => {
        if (typeof window === 'undefined') return;
        const mq = window.matchMedia(query);
        const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
        // Sync immediately in case the query result changed between init and mount.
        setMatches(mq.matches);
        mq.addEventListener('change', handler);
        return () => mq.removeEventListener('change', handler);
    }, [query]);

    return matches;
}
