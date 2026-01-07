import React, { useState, useEffect } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import {
    Contact,
    CreateContactParams,
    UpdateContactParams,
    createContact,
    updateContact
} from '@/api/contacts';

interface ContactFormDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    contact?: Contact | null;  // If provided, edit mode
    onSuccess?: (contact: Contact) => void;
}

export function ContactFormDialog({
    open,
    onOpenChange,
    contact,
    onSuccess
}: ContactFormDialogProps) {
    const isEdit = !!contact;
    const [loading, setLoading] = useState(false);

    // Form state
    const [email, setEmail] = useState('');
    const [fullName, setFullName] = useState('');
    const [professionalTitle, setProfessionalTitle] = useState('');
    const [organizationName, setOrganizationName] = useState('');
    const [phone, setPhone] = useState('');
    const [notes, setNotes] = useState('');

    // Reset form when contact changes or dialog opens
    useEffect(() => {
        if (open) {
            if (contact) {
                setEmail(contact.email);
                setFullName(contact.full_name);
                setProfessionalTitle(contact.professional_title || '');
                setOrganizationName(contact.organization_name || '');
                setPhone(contact.phone || '');
                setNotes(contact.notes || '');
            } else {
                // Reset for new contact
                setEmail('');
                setFullName('');
                setProfessionalTitle('');
                setOrganizationName('');
                setPhone('');
                setNotes('');
            }
        }
    }, [open, contact]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!email.trim() || !fullName.trim()) {
            toast.error('Email and name are required');
            return;
        }

        setLoading(true);
        try {
            let result: Contact;

            if (isEdit && contact) {
                const data: UpdateContactParams = {
                    email: email.trim(),
                    full_name: fullName.trim(),
                    professional_title: professionalTitle.trim() || undefined,
                    organization_name: organizationName.trim() || undefined,
                    phone: phone.trim() || undefined,
                    notes: notes.trim() || undefined,
                };
                result = await updateContact(contact.uuid, data);
                toast.success('Contact updated successfully');
            } else {
                const data: CreateContactParams = {
                    email: email.trim(),
                    full_name: fullName.trim(),
                    professional_title: professionalTitle.trim() || undefined,
                    organization_name: organizationName.trim() || undefined,
                    phone: phone.trim() || undefined,
                    notes: notes.trim() || undefined,
                };
                result = await createContact(data);
                toast.success('Contact added successfully');
            }

            onSuccess?.(result);
            onOpenChange(false);
        } catch (error) {
            console.error('Failed to save contact:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <form onSubmit={handleSubmit}>
                    <DialogHeader>
                        <DialogTitle>
                            {isEdit ? 'Edit Contact' : 'Add New Contact'}
                        </DialogTitle>
                        <DialogDescription>
                            {isEdit
                                ? 'Update the contact information below.'
                                : 'Enter the contact details to add them to your contacts.'
                            }
                        </DialogDescription>
                    </DialogHeader>

                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label htmlFor="email">Email *</Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="contact@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                disabled={loading}
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="fullName">Full Name *</Label>
                            <Input
                                id="fullName"
                                placeholder="John Doe"
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                required
                                disabled={loading}
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="grid gap-2">
                                <Label htmlFor="title">Title</Label>
                                <Input
                                    id="title"
                                    placeholder="Dr., MD, PhD..."
                                    value={professionalTitle}
                                    onChange={(e) => setProfessionalTitle(e.target.value)}
                                    disabled={loading}
                                />
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="phone">Phone</Label>
                                <Input
                                    id="phone"
                                    type="tel"
                                    placeholder="+1 555-0123"
                                    value={phone}
                                    onChange={(e) => setPhone(e.target.value)}
                                    disabled={loading}
                                />
                            </div>
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="org">Organization</Label>
                            <Input
                                id="org"
                                placeholder="Company or institution"
                                value={organizationName}
                                onChange={(e) => setOrganizationName(e.target.value)}
                                disabled={loading}
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="notes">Notes</Label>
                            <Textarea
                                id="notes"
                                placeholder="Private notes about this contact..."
                                value={notes}
                                onChange={(e) => setNotes(e.target.value)}
                                disabled={loading}
                                rows={3}
                            />
                        </div>
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
            </DialogContent>
        </Dialog>
    );
}
