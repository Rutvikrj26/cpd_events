import React, { useState } from 'react';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Contact, deleteContact } from '@/api/contacts';

interface DeleteContactDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    contact: Contact | null;
    onSuccess?: () => void;
}

export function DeleteContactDialog({
    open,
    onOpenChange,
    contact,
    onSuccess
}: DeleteContactDialogProps) {
    const [loading, setLoading] = useState(false);

    if (!contact) return null;

    const handleDelete = async () => {
        setLoading(true);
        try {
            await deleteContact(contact.uuid);
            toast.success('Contact deleted successfully');
            onSuccess?.();
            onOpenChange(false);
        } catch (error) {
            console.error('Failed to delete contact:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <AlertDialog open={open} onOpenChange={onOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Delete Contact</AlertDialogTitle>
                    <AlertDialogDescription>
                        Are you sure you want to delete <strong>{contact.full_name}</strong> ({contact.email})?
                        This action cannot be undone.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel disabled={loading}>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                        onClick={handleDelete}
                        disabled={loading}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Delete
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
