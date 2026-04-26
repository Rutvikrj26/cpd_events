import React, { useEffect } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/shared/ui/dialog';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Textarea } from '@/shared/ui/textarea';
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@/shared/ui/form';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import type { Contact } from '@/api/contacts';
import {
    contactSchema,
    useCreateContact,
    useUpdateContact,
    type ContactFormValues,
} from '@/features/contacts';
import { useZodForm } from '@/shared/lib/forms';
// TAGGING-DISABLED: UI hidden while feature is deferred — backend still supports it.
// import { TagPicker } from './TagPicker';

interface ContactFormDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    /** If provided, dialog renders in edit mode. */
    contact?: Contact | null;
    /** Optional success callback. Mutations already invalidate the cache. */
    onSuccess?: (contact: Contact) => void;
}

const emptyValues: ContactFormValues = {
    email: '',
    full_name: '',
    professional_title: '',
    organization_name: '',
    phone: '',
    notes: '',
};

export function ContactFormDialog({
    open,
    onOpenChange,
    contact,
    onSuccess,
}: ContactFormDialogProps) {
    const isEdit = !!contact;
    const createContact = useCreateContact();
    const updateContact = useUpdateContact();

    const form = useZodForm(contactSchema, {
        defaultValues: emptyValues,
    });

    // Reset form when the dialog opens or the active contact changes.
    useEffect(() => {
        if (!open) return;
        if (contact) {
            form.reset({
                email: contact.email ?? '',
                full_name: contact.full_name ?? '',
                professional_title: contact.professional_title ?? '',
                organization_name: contact.organization_name ?? '',
                phone: contact.phone ?? '',
                notes: contact.notes ?? '',
            });
        } else {
            form.reset(emptyValues);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [open, contact]);

    const onSubmit = async (values: ContactFormValues) => {
        // Empty optional strings are normalized to undefined so the backend
        // treats them as unset rather than empty.
        const payload = {
            email: values.email,
            full_name: values.full_name.trim(),
            professional_title: values.professional_title?.trim() || undefined,
            organization_name: values.organization_name?.trim() || undefined,
            phone: values.phone?.trim() || undefined,
            notes: values.notes?.trim() || undefined,
        };

        try {
            let result: Contact;
            if (isEdit && contact) {
                result = await updateContact.mutateAsync({ uuid: contact.uuid, data: payload });
                toast.success('Contact updated successfully');
            } else {
                result = await createContact.mutateAsync(payload);
                toast.success('Contact added successfully');
            }
            onSuccess?.(result);
            onOpenChange(false);
        } catch (error) {
            console.error('Failed to save contact:', error);
        }
    };

    const loading =
        createContact.isPending ||
        updateContact.isPending ||
        form.formState.isSubmitting;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <Form {...form}>
                    {/* `noValidate` disables browser HTML5 validation so RHF +
                        Zod can own the error UX. Without this, `type="email"`
                        blocks the submit event before our resolver runs. */}
                    <form noValidate onSubmit={form.handleSubmit(onSubmit as any)}>
                        <DialogHeader>
                            <DialogTitle>
                                {isEdit ? 'Edit Contact' : 'Add New Contact'}
                            </DialogTitle>
                            <DialogDescription>
                                {isEdit
                                    ? 'Update the contact information below.'
                                    : 'Enter the contact details to add them to your contacts.'}
                            </DialogDescription>
                        </DialogHeader>

                        <div className="grid gap-4 py-4">
                            <FormField
                                control={form.control as any}
                                name="email"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Email *</FormLabel>
                                        <FormControl>
                                            <Input
                                                type="email"
                                                placeholder="contact@example.com"
                                                disabled={loading}
                                                {...field}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control as any}
                                name="full_name"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Full Name *</FormLabel>
                                        <FormControl>
                                            <Input
                                                placeholder="John Doe"
                                                disabled={loading}
                                                {...field}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <div className="grid grid-cols-2 gap-4">
                                <FormField
                                    control={form.control as any}
                                    name="professional_title"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Title</FormLabel>
                                            <FormControl>
                                                <Input
                                                    placeholder="Dr., MD, PhD..."
                                                    disabled={loading}
                                                    {...field}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                                <FormField
                                    control={form.control as any}
                                    name="phone"
                                    render={({ field }) => (
                                        <FormItem>
                                            <FormLabel>Phone</FormLabel>
                                            <FormControl>
                                                <Input
                                                    type="tel"
                                                    placeholder="+1 555-0123"
                                                    disabled={loading}
                                                    {...field}
                                                />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </div>

                            <FormField
                                control={form.control as any}
                                name="organization_name"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Organization</FormLabel>
                                        <FormControl>
                                            <Input
                                                placeholder="Company or institution"
                                                disabled={loading}
                                                {...field}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            {/* TAGGING-DISABLED: restore TagPicker block when re-enabling tag UI.
                            <div className="grid gap-2">
                                <Label>Tags</Label>
                                <TagPicker
                                    tags={availableTags}
                                    selectedUuids={tagUuids}
                                    onChange={setTagUuids}
                                    onTagsChange={setAvailableTags}
                                    disabled={loading}
                                />
                            </div>
                            */}

                            <FormField
                                control={form.control as any}
                                name="notes"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Notes</FormLabel>
                                        <FormControl>
                                            <Textarea
                                                placeholder="Private notes about this contact..."
                                                rows={3}
                                                disabled={loading}
                                                {...field}
                                            />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <DialogFooter>
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => onOpenChange(false)}
                                disabled={loading}
                            >
                                Cancel
                            </Button>
                            <Button type="submit" disabled={loading}>
                                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                {isEdit ? 'Save Changes' : 'Add Contact'}
                            </Button>
                        </DialogFooter>
                    </form>
                </Form>
            </DialogContent>
        </Dialog>
    );
}
