/**
 * Form error utilities — translate DRF API errors into structured form errors.
 *
 * Industry-standard UX guidance (Carbon, PatternFly, GOV.UK, Stripe, Linear)
 * is that **field validation errors should render inline next to the input**,
 * not in a toast that floats away. Toasts are for transient, non-form events
 * (saved, copied, network failure). When the API returns
 * `{ error: { details: { speakers: ["..."], non_field_errors: ["..."] } } }`,
 * a form should:
 *
 *   1. push each field error into its form-state library (e.g. react-hook-form
 *      `setError(field, { type: 'server', message })`)
 *   2. render a summary banner at the top of the form for non-field errors
 *
 * `formErrorsFromApi(error)` returns the structure you need for both. It is
 * deliberately framework-agnostic — works with react-hook-form, formik, plain
 * `useState`, or anything else.
 *
 * Usage (react-hook-form)::
 *
 *     try {
 *       await updateEvent(uuid, data, { silent: true });   // <- opt out of toast
 *     } catch (err) {
 *       const { fieldErrors, formErrors } = formErrorsFromApi(err);
 *       Object.entries(fieldErrors).forEach(([field, message]) => {
 *         form.setError(field as any, { type: 'server', message });
 *       });
 *       if (formErrors.length > 0) {
 *         form.setError('root.serverError', { type: 'server', message: formErrors.join('\n') });
 *       }
 *     }
 *
 * Usage (plain state)::
 *
 *     const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
 *     // …
 *     setFieldErrors(formErrorsFromApi(err).fieldErrors);
 */

import axios from 'axios';
import { ApiErrorResponse } from '@/api/types';

export interface FormErrorBundle {
    /** Map of field name -> first error message. Use for inline errors. */
    fieldErrors: Record<string, string>;
    /** Non-field-level errors. Render in a summary banner above the form. */
    formErrors: string[];
}

const NON_FIELD_KEYS = new Set(['__all__', 'all', 'non_field_errors']);

/**
 * Parse an axios error from the DRF API into structured form errors.
 *
 * - Field errors: keyed by the original field name (snake_case).
 * - Form errors: pulled from `__all__` / `non_field_errors` / a top-level
 *   `message` if no `details` were given.
 *
 * Falls back to a single generic form error if the response can't be parsed.
 */
export function formErrorsFromApi(error: unknown): FormErrorBundle {
    const fieldErrors: Record<string, string> = {};
    const formErrors: string[] = [];

    if (axios.isAxiosError(error) && error.response?.data) {
        const data = error.response.data as ApiErrorResponse;

        if (data.error) {
            const { message, details } = data.error;

            if (details && typeof details === 'object') {
                for (const [field, value] of Object.entries(details)) {
                    const text = Array.isArray(value) ? value.join(', ') : String(value);
                    if (NON_FIELD_KEYS.has(field.toLowerCase())) {
                        formErrors.push(text);
                    } else if (!(field in fieldErrors)) {
                        // Keep the first error per field — RHF / inputs render one
                        // message at a time.
                        fieldErrors[field] = text;
                    }
                }
            } else if (message) {
                formErrors.push(message);
            }

            return { fieldErrors, formErrors };
        }
    }

    if (error instanceof Error && error.message) {
        formErrors.push(error.message);
    } else if (Object.keys(fieldErrors).length === 0 && formErrors.length === 0) {
        formErrors.push('An unexpected error occurred. Please try again.');
    }

    return { fieldErrors, formErrors };
}
