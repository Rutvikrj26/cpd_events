/**
 * User-aware date and time formatting helpers.
 *
 * Use these instead of bare `toLocaleDateString()` so that every datetime
 * shown in the UI honours the signed-in user's timezone and locale.
 * For unauthenticated surfaces, a sensible default falls back to
 * en-CA + the browser's local timezone.
 */

interface UserLike {
    timezone?: string | null;
    locale?: string | null;
}

const DEFAULT_LOCALE = "en-CA";

function effectiveLocale(user?: UserLike | null): string {
    return user?.locale || DEFAULT_LOCALE;
}

function effectiveTimezone(user?: UserLike | null): string | undefined {
    // undefined → Intl uses the user-agent default; explicit values override.
    return user?.timezone || undefined;
}

export function formatDate(
    value: string | number | Date | null | undefined,
    user?: UserLike | null,
    options: Intl.DateTimeFormatOptions = { year: "numeric", month: "short", day: "numeric" },
): string {
    if (value === null || value === undefined || value === "") return "";
    const d = value instanceof Date ? value : new Date(value);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleDateString(effectiveLocale(user), {
        ...options,
        timeZone: effectiveTimezone(user),
    });
}

export function formatTime(
    value: string | number | Date | null | undefined,
    user?: UserLike | null,
    options: Intl.DateTimeFormatOptions = { hour: "numeric", minute: "2-digit" },
): string {
    if (value === null || value === undefined || value === "") return "";
    const d = value instanceof Date ? value : new Date(value);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString(effectiveLocale(user), {
        ...options,
        timeZone: effectiveTimezone(user),
    });
}

export function formatDateTime(
    value: string | number | Date | null | undefined,
    user?: UserLike | null,
    options: Intl.DateTimeFormatOptions = {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
    },
): string {
    if (value === null || value === undefined || value === "") return "";
    const d = value instanceof Date ? value : new Date(value);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleString(effectiveLocale(user), {
        ...options,
        timeZone: effectiveTimezone(user),
    });
}

/**
 * ISO timestamp safe for `<time datetime="...">` and tooltip absolute display.
 */
export function toAbsoluteISO(value: string | number | Date | null | undefined): string {
    if (value === null || value === undefined || value === "") return "";
    const d = value instanceof Date ? value : new Date(value);
    if (isNaN(d.getTime())) return "";
    return d.toISOString();
}
