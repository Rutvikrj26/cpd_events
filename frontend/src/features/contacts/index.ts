/**
 * features/contacts — public surface.
 */
export {
    contactKeys,
    useContacts,
    useCreateContact,
    useUpdateContact,
    useDeleteContact,
    useTags,
    useCreateTag,
    useUpdateTag,
    useDeleteTag,
} from './hooks';
export { contactSchema } from './schemas/contact';
export type { ContactFormValues } from './schemas/contact';
