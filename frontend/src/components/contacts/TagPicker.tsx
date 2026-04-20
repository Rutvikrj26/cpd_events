import React, { useState } from 'react';
import {
    DropdownMenu,
    DropdownMenuCheckboxItem,
    DropdownMenuContent,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Plus, Tag as TagIcon, X } from 'lucide-react';
import { Tag, createTag } from '@/api/contacts';
import { toast } from 'sonner';

interface TagPickerProps {
    tags: Tag[];
    selectedUuids: string[];
    onChange: (uuids: string[]) => void;
    onTagsChange?: (tags: Tag[]) => void;
    disabled?: boolean;
}

export function TagPicker({ tags, selectedUuids, onChange, onTagsChange, disabled }: TagPickerProps) {
    const [newName, setNewName] = useState('');
    const [creating, setCreating] = useState(false);

    const selectedTags = tags.filter((t) => selectedUuids.includes(t.uuid));

    const toggle = (uuid: string, checked: boolean) => {
        onChange(checked ? [...selectedUuids, uuid] : selectedUuids.filter((id) => id !== uuid));
    };

    const remove = (uuid: string) => {
        onChange(selectedUuids.filter((id) => id !== uuid));
    };

    const createInline = async () => {
        const name = newName.trim();
        if (!name) return;
        if (tags.some((t) => t.name.toLowerCase() === name.toLowerCase())) {
            toast.error('Tag already exists');
            return;
        }
        setCreating(true);
        try {
            const created = await createTag({ name });
            onTagsChange?.([...tags, created]);
            onChange([...selectedUuids, created.uuid]);
            setNewName('');
        } catch (e) {
            toast.error('Failed to create tag');
        } finally {
            setCreating(false);
        }
    };

    return (
        <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2 min-h-[2rem] border rounded-md px-2 py-1.5 bg-background">
                {selectedTags.length === 0 && (
                    <span className="text-sm text-muted-foreground">No tags applied</span>
                )}
                {selectedTags.map((tag) => (
                    <Badge
                        key={tag.uuid}
                        variant="secondary"
                        className="gap-1"
                        style={{ borderLeft: `3px solid ${tag.color || '#888'}` }}
                    >
                        {tag.name}
                        {!disabled && (
                            <button
                                type="button"
                                onClick={() => remove(tag.uuid)}
                                className="ml-1 opacity-60 hover:opacity-100"
                                aria-label={`Remove ${tag.name}`}
                            >
                                <X className="h-3 w-3" />
                            </button>
                        )}
                    </Badge>
                ))}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button type="button" variant="ghost" size="sm" className="h-7" disabled={disabled}>
                            <TagIcon className="h-3 w-3 mr-1" />
                            {selectedTags.length > 0 ? 'Edit tags' : 'Add tags'}
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start" className="w-64">
                        <DropdownMenuLabel>Apply tags</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        {tags.length === 0 ? (
                            <div className="px-3 py-3 text-center text-xs text-muted-foreground">
                                No tags yet. Create one below.
                            </div>
                        ) : (
                            <div className="max-h-56 overflow-auto">
                                {tags.map((tag) => (
                                    <DropdownMenuCheckboxItem
                                        key={tag.uuid}
                                        checked={selectedUuids.includes(tag.uuid)}
                                        onCheckedChange={(c) => toggle(tag.uuid, c)}
                                        onSelect={(e) => e.preventDefault()}
                                    >
                                        <div className="flex items-center gap-2 flex-1">
                                            <span
                                                className="w-3 h-3 rounded-full shrink-0"
                                                style={{ backgroundColor: tag.color || '#888' }}
                                            />
                                            <span className="truncate">{tag.name}</span>
                                        </div>
                                    </DropdownMenuCheckboxItem>
                                ))}
                            </div>
                        )}
                        <DropdownMenuSeparator />
                        <div className="p-2 flex gap-1">
                            <Input
                                value={newName}
                                onChange={(e) => setNewName(e.target.value)}
                                placeholder="New tag name"
                                className="h-8 text-xs"
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        e.preventDefault();
                                        createInline();
                                    }
                                }}
                                disabled={creating}
                            />
                            <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                className="h-8 px-2"
                                onClick={createInline}
                                disabled={!newName.trim() || creating}
                            >
                                <Plus className="h-3 w-3" />
                            </Button>
                        </div>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </div>
    );
}
