// Build avatar initials from a person's name, stripping common honorifics so
// "Dr. Michael Torres" produces "MT" rather than "DT" (QA finding F-19).
// Also exports `splitFullName` which uses the same honorific-stripping logic
// to feed first_name / last_name form prefills correctly (F-33).
//
// Display-name shape we normalise from:
//
//     "[Honorific] Firstname [Middle] Lastname[, Postnom1, Postnom2, ...]"
//
// Two stripping rules, applied in order:
//
//   1. Anything after the first comma is post-nominal credentials —
//      "MD, FRCPC", "RN, MN", "PhD", "MPH" — and is dropped wholesale.
//      We do NOT enumerate medical/professional credentials by name; the
//      comma is the structural signal authors use everywhere this matters.
//   2. From the remaining tokens, drop any honorific prefix (Dr., Prof.,
//      Mr., etc.) — a small enumerable set with no domain-specific tail.

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

/** Drop comma-delimited post-nominals AND any honorific prefix tokens. */
function stripHonorifics(name: string): string {
    // Step 1 — keep only the segment before the first comma. Everything
    // after is post-nominals by convention (Western display-name syntax),
    // which is more reliable than maintaining a list of every credential
    // a user might append (RN, MN, MD, FRCPC, MPH, FACS, CNCC(C), …).
    const beforeComma = name.split(',', 1)[0] ?? '';
    // Step 2 — strip the small enumerable set of honorific prefixes.
    return beforeComma
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

/**
 * Split a full name into { first, last } parts, stripping honorifics.
 * "Dr. Michael Torres" → { first: "Michael", last: "Torres" }
 * "Cher" → { first: "Cher", last: "" }
 */
export function splitFullName(fullName: string | undefined | null): { first: string; last: string } {
    if (!fullName) return { first: '', last: '' };
    const tokens = stripHonorifics(fullName).split(/\s+/).filter(Boolean);
    if (tokens.length === 0) return { first: '', last: '' };
    if (tokens.length === 1) return { first: tokens[0], last: '' };
    return { first: tokens[0], last: tokens.slice(1).join(' ') };
}
