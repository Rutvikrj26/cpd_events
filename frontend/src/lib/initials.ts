// Build avatar initials from a person's name, stripping common honorifics so
// "Dr. Michael Torres" produces "MT" rather than "DT" (QA finding F-19).

const HONORIFICS = new Set([
    'dr', 'dr.',
    'prof', 'prof.', 'professor',
    'mr', 'mr.',
    'mrs', 'mrs.',
    'ms', 'ms.',
    'mx', 'mx.',
    'rev', 'rev.', 'reverend',
    'sr', 'sr.', 'sister',
    'fr', 'fr.', 'father',
    'hon', 'hon.', 'honourable',
    'sir',
]);

function stripHonorifics(name: string): string {
    return name
        .split(/\s+/)
        .filter((token) => token && !HONORIFICS.has(token.toLowerCase()))
        .join(' ');
}

/**
 * Return a 1-2 character avatar initial from a person's name.
 * Accepts either a single full-name string or first/last parts.
 */
export function getInitials(...parts: Array<string | undefined | null>): string {
    const cleaned = parts
        .filter((p): p is string => Boolean(p))
        .map(stripHonorifics)
        .filter(Boolean)
        .join(' ')
        .trim();

    if (!cleaned) return '?';

    const tokens = cleaned.split(/\s+/);
    if (tokens.length === 1) {
        return tokens[0].slice(0, 2).toUpperCase();
    }
    return (tokens[0][0] + tokens[tokens.length - 1][0]).toUpperCase();
}
