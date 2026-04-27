import { useForm, type UseFormProps, type UseFormReturn } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import type { z } from 'zod';

/**
 * useZodForm — react-hook-form + Zod, wired together.
 *
 * Removes the boilerplate of `useForm({ resolver: zodResolver(schema) })`
 * and gets type-safe values inferred from the schema.
 *
 * Usage:
 *     const schema = z.object({ email: z.string().email() });
 *     const form = useZodForm(schema, { defaultValues: { email: '' } });
 *     <form onSubmit={form.handleSubmit(onSubmit)} />
 */
export function useZodForm<TSchema extends z.ZodType<any, any, any>>(
    schema: TSchema,
    options?: Omit<UseFormProps<z.infer<TSchema>>, 'resolver'>
): UseFormReturn<z.infer<TSchema>> {
    return useForm<z.infer<TSchema>>({
        ...options,
        resolver: zodResolver(schema) as any,
    });
}
