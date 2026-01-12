import React, { useState } from 'react';
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
import { Switch } from '@/components/ui/switch';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { ContactList, CreateContactListParams, createContactList } from '@/api/contacts';

interface CreateListDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess?: (list: ContactList) => void;
}

export function CreateListDialog({
    open,
    onOpenChange,
    onSuccess
}: CreateListDialogProps) {
    const [loading, setLoading] = useState(false);
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');

    // Reset form when dialog opens
    React.useEffect(() => {
        if (open) {
            setName('');
            setDescription('');
        }
    }, [open]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!name.trim()) {
            toast.error('List name is required');
            return;
        }

        setLoading(true);
        try {
            const data: CreateContactListParams = {
                name: name.trim(),
                description: description.trim() || undefined,
            };
            const result = await createContactList(data);
            toast.success('Contact list created successfully');
            onSuccess?.(result);
            onOpenChange(false);
        } catch (error) {
            console.error('Failed to create list:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <form onSubmit={handleSubmit}>
                    <DialogHeader>
                        <DialogTitle>Create Contact List</DialogTitle>
                        <DialogDescription>
                            Create a new list to organize your contacts.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label htmlFor="name">List Name *</Label>
                            <Input
                                id="name"
                                placeholder="e.g., VIP Clients, 2024 Conference"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                required
                                disabled={loading}
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="description">Description</Label>
                            <Textarea
                                id="description"
                                placeholder="Optional description for this list..."
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                disabled={loading}
                                rows={2}
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
                            Create List
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
