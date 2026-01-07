import React, { useState } from 'react';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Plus, Users, Share2 } from 'lucide-react';
import { ContactList } from '@/api/contacts';
import { Badge } from '@/components/ui/badge';

interface ListSelectorProps {
    lists: ContactList[];
    currentList: ContactList | null;
    onListChange: (list: ContactList) => void;
    onCreateList: () => void;
    loading?: boolean;
}

export function ListSelector({
    lists,
    currentList,
    onListChange,
    onCreateList,
    loading = false
}: ListSelectorProps) {
    const handleValueChange = (uuid: string) => {
        const list = lists.find(l => l.uuid === uuid);
        if (list) {
            onListChange(list);
        }
    };

    return (
        <div className="flex items-center gap-2">
            <Select
                value={currentList?.uuid || ''}
                onValueChange={handleValueChange}
                disabled={loading}
            >
                <SelectTrigger className="w-[220px]">
                    <SelectValue placeholder="Select a list">
                        {currentList && (
                            <div className="flex items-center gap-2">
                                <Users className="h-4 w-4 text-muted-foreground" />
                                <span className="truncate">{currentList.name}</span>
                                {currentList.is_shared && (
                                    <Share2 className="h-3 w-3 text-primary" />
                                )}
                            </div>
                        )}
                    </SelectValue>
                </SelectTrigger>
                <SelectContent>
                    {lists.map((list) => (
                        <SelectItem key={list.uuid} value={list.uuid}>
                            <div className="flex items-center gap-2">
                                <span>{list.name}</span>
                                <span className="text-xs text-muted-foreground">
                                    ({list.contact_count})
                                </span>
                                {list.is_shared && (
                                    <Badge variant="outline" className="text-xs px-1 py-0">
                                        Shared
                                    </Badge>
                                )}
                                {list.is_default && (
                                    <Badge variant="secondary" className="text-xs px-1 py-0">
                                        Default
                                    </Badge>
                                )}
                            </div>
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
            <Button
                variant="outline"
                size="icon"
                onClick={onCreateList}
                title="Create new list"
            >
                <Plus className="h-4 w-4" />
            </Button>
        </div>
    );
}
