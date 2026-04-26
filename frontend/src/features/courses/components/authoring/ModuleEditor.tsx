import React, { useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/shared/ui/dialog';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Plus } from 'lucide-react';
import { toast } from 'sonner';
import { useCreateModule } from '../../hooks';

interface ModuleEditorProps {
    courseUuid: string;
    onCreated: () => void;
}

/**
 * ModuleEditor — "Add Module" dialog that opens from the CurriculumBuilder header.
 * Inline name editing per-module is handled directly in ModuleList/ModuleItem.
 */
export function ModuleEditor({ courseUuid, onCreated }: ModuleEditorProps) {
    const [open, setOpen] = useState(false);
    const [title, setTitle] = useState('');
    const { mutate: createModule, isPending } = useCreateModule(courseUuid);

    const handleCreate = () => {
        if (!title.trim()) return;
        createModule(
            { title: title.trim() },
            {
                onSuccess: () => {
                    toast.success('Module created');
                    setTitle('');
                    setOpen(false);
                    onCreated();
                },
                onError: () => toast.error('Failed to create module'),
            },
        );
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button>
                    <Plus className="mr-2 h-4 w-4" /> Add Module
                </Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Add New Module</DialogTitle>
                    <DialogDescription>
                        Create a new section for your course curriculum.
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                    <div className="space-y-2">
                        <Label htmlFor="module-title">Module Title</Label>
                        <Input
                            id="module-title"
                            placeholder="e.g., Introduction to CPD"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                        />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => setOpen(false)} disabled={isPending}>
                        Cancel
                    </Button>
                    <Button onClick={handleCreate} disabled={isPending || !title.trim()}>
                        Create Module
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
