import { z } from 'zod';

/**
 * Cross-feature primitive Zod schemas. Compose into feature schemas
 * rather than redefining (e.g. `z.object({ user_uuid: uuid, … })`).
 */

/** RFC-4122 UUID. */
export const uuid = z.string().uuid('Invalid identifier');

/** Backend slug — lowercase, alphanumeric, dashes. */
export const slug = z
    .string()
    .min(1)
    .max(160)
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'Use lowercase letters, numbers, and dashes only');

/** Trimmed non-empty string. */
export const nonEmpty = (label = 'Field') =>
    z
        .string()
        .trim()
        .min(1, `${label} is required`);

/** Email — Zod's built-in plus a normalization. */
export const email = z.string().trim().toLowerCase().email('Enter a valid email');

/** ISO datetime string. */
export const isoDateTime = z.string().datetime({ offset: true });

/** Currency in cents — non-negative integer. */
export const cents = z.number().int().min(0);

/** Pagination params (mirrors api/types.ts shape). */
export const paginationParams = z.object({
    page: z.number().int().min(1).default(1),
    page_size: z.number().int().min(1).max(100).default(20),
});

export type PaginationParams = z.infer<typeof paginationParams>;
