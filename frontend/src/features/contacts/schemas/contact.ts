import { z } from 'zod';
import { email, nonEmpty } from '@/shared/schemas/primitives';

/**
 * Form schema for creating / editing a contact.
 *
 * Both create and edit dialogs share these fields. Optional fields are
 * stored as plain strings in the form (empty = absent) and lifted to
 * `undefined` at submit time so the backend treats them as unset.
 */
export const contactSchema = z.object({
    email,
    full_name: nonEmpty('Full name'),
    professional_title: z.string().optional().default(''),
    organization_name: z.string().optional().default(''),
    phone: z.string().optional().default(''),
    notes: z.string().optional().default(''),
});

export type ContactFormValues = z.infer<typeof contactSchema>;
