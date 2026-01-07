import React from 'react';
import {
    DropdownMenu,
    DropdownMenuCheckboxItem,
    DropdownMenuContent,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Filter, Tag as TagIcon } from 'lucide-react';
import { Tag } from '@/api/contacts';
import { Badge } from '@/components/ui/badge';

interface TagFilterProps {
    tags: Tag[];
    selectedTagUuids: string[];
    onTagsChange: (uuids: string[]) => void;
    loading?: boolean;
}

export function TagFilter({
    tags,
    selectedTagUuids,
    onTagsChange,
    loading = false
}: TagFilterProps) {
    const handleTagToggle = (uuid: string, checked: boolean) => {
        if (checked) {
            onTagsChange([...selectedTagUuids, uuid]);
        } else {
            onTagsChange(selectedTagUuids.filter(id => id !== uuid));
        }
    };

    const handleClear = () => {
        onTagsChange([]);
    };

    const selectedCount = selectedTagUuids.length;

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" disabled={loading}>
                    <Filter className="h-4 w-4 mr-2" />
                    Filter
                    {selectedCount > 0 && (
                        <Badge variant="secondary" className="ml-2 h-5 px-1.5">
                            {selectedCount}
                        </Badge>
                    )}
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel className="flex items-center justify-between">
                    <span>Filter by Tags</span>
                    {selectedCount > 0 && (
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
                            onClick={handleClear}
                        >
                            Clear all
                        </Button>
                    )}
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                {tags.length === 0 ? (
                    <div className="px-2 py-4 text-center text-sm text-muted-foreground">
                        <TagIcon className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p>No tags yet</p>
                    </div>
                ) : (
                    tags.map((tag) => (
                        <DropdownMenuCheckboxItem
                            key={tag.uuid}
                            checked={selectedTagUuids.includes(tag.uuid)}
                            onCheckedChange={(checked) => handleTagToggle(tag.uuid, checked)}
                        >
                            <div className="flex items-center gap-2">
                                <div
                                    className="w-3 h-3 rounded-full"
                                    style={{ backgroundColor: tag.color || '#888' }}
                                />
                                <span>{tag.name}</span>
                                <span className="text-xs text-muted-foreground ml-auto">
                                    {tag.contact_count}
                                </span>
                            </div>
                        </DropdownMenuCheckboxItem>
                    ))
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
