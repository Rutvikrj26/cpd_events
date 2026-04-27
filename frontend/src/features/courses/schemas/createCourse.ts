import { z } from 'zod';
import { nonEmpty, slug, uuid } from '@/shared/schemas/primitives';

/**
 * Form schema for the "Create course" page.
 *
 * Captures every field the page surfaces: identity, pricing, format,
 * completion criteria, and certificate/badge templates. The schema is
 * authoritative — handlers should not duplicate trim/required checks.
 *
 * Refinement: when format is 'live' or 'hybrid' the page enforces
 * "at least one session" against external state (the SessionScheduler),
 * so that constraint is checked imperatively in the page rather than here.
 */
export const courseFormatEnum = z.enum(['online', 'live', 'hybrid']);
export type CourseFormat = z.infer<typeof courseFormatEnum>;

export const completionCriteriaEnum = z.enum([
    'modules_only',
    'sessions_only',
    'both',
    'either',
    'min_sessions',
]);
export type CompletionCriteria = z.infer<typeof completionCriteriaEnum>;

export const createCourseSchema = z.object({
    title: nonEmpty('Title').refine(
        (val) => val.trim().length >= 3,
        'Title must be at least 3 characters',
    ),
    slug,
    short_description: z
        .string()
        .max(300, 'Short description limited to 300 characters')
        .optional(),
    description: z.string().optional(),

    cpd_credits: z.coerce.number().min(0).default(0),
    is_public: z.boolean().default(true),
    price_cents: z.coerce.number().int().min(0).default(0),
    enrollment_open: z.boolean().default(true),
    estimated_hours: z.coerce.number().min(0).optional(),

    format: courseFormatEnum.default('online'),
    hybrid_completion_criteria: completionCriteriaEnum.optional(),
    min_sessions_required: z.coerce.number().int().min(1).default(1),

    live_session_start: z.string().optional(),
    live_session_end: z.string().optional(),
    live_session_timezone: z.string().default('UTC'),

    certificates_enabled: z.boolean().default(false),
    certificate_template: uuid.nullable().optional(),
    auto_issue_certificates: z.boolean().default(true),
    badges_enabled: z.boolean().default(false),
    badge_template: uuid.nullable().optional(),
    auto_issue_badges: z.boolean().default(true),
});

export type CreateCourseFormValues = z.infer<typeof createCourseSchema>;
