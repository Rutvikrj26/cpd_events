import { useEffect } from 'react';

const SUFFIX = ' · Accredit';

/**
 * Set the document <title> for the current route. Restores the previous
 * title on unmount so navigating away from a route that calls this hook
 * doesn't leave a stale tab title behind.
 *
 * Usage:
 *     useDocumentTitle('Login');                  // → "Login · Accredit"
 *     useDocumentTitle(`${course.title} – Edit`); // → "Course X – Edit · Accredit"
 *     useDocumentTitle(null);                     // → "Accredit"
 */
export function useDocumentTitle(title: string | null | undefined) {
    useEffect(() => {
        const previous = document.title;
        if (title) {
            document.title = `${title}${SUFFIX}`;
        } else {
            document.title = 'Accredit';
        }
        return () => {
            document.title = previous;
        };
    }, [title]);
}
