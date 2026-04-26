import { z } from 'zod';
import { nonEmpty, slug } from '@/shared/schemas/primitives';

/**
 * Form schema for the "Create program" page.
 *
 * Validation rules:
 * - title: required, trimmed, non-empty.
 * - slug: required, must match the standard backend slug shape.
 * - short_description: optional, capped at 300 chars (matches API constraint).
 * - description: optional free text.
 * - price_cents: non-negative integer (0 = free).
 * - currency: 3-letter ISO code, uppercased.
 * - is_public: switch.
 */
export const createProgramSchema = z.object({
    title: nonEmpty('Title'),
    slug,
    short_description: z
        .string()
        .max(300, 'Short description limited to 300 characters')
        .optional(),
    description: z.string().optional(),
    price_cents: z.coerce.number().int().min(0).default(0),
    currency: z
        .string()
        .trim()
        .toUpperCase()
        .length(3, 'Use a 3-letter currency code')
        .default('USD'),
    is_public: z.boolean().default(true),
});

export type CreateProgramFormValues = z.infer<typeof createProgramSchema>;
