import React from 'react';
import { Pin, PinOff, Lock, Unlock, EyeOff, Eye, Trash2, MoreVertical } from 'lucide-react';
import { Button } from '@/shared/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/shared/ui/dropdown-menu';
import { DiscussionThreadList } from '@/api/courses';

interface ThreadActionsMenuProps {
    thread: Pick<DiscussionThreadList, 'is_pinned' | 'is_locked' | 'is_hidden'>;
    onPin: () => void;
    onUnpin: () => void;
    onLock: () => void;
    onUnlock: () => void;
    onHide: () => void;
    onUnhide: () => void;
    onDelete?: () => void;
}

export function ThreadActionsMenu({
    thread,
    onPin,
    onUnpin,
    onLock,
    onUnlock,
    onHide,
    onUnhide,
    onDelete,
}: ThreadActionsMenuProps) {
    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                    <MoreVertical className="h-4 w-4" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
                {thread.is_pinned ? (
                    <DropdownMenuItem onClick={onUnpin}>
                        <PinOff className="mr-2 h-4 w-4" />
                        Unpin
                    </DropdownMenuItem>
                ) : (
                    <DropdownMenuItem onClick={onPin}>
                        <Pin className="mr-2 h-4 w-4" />
                        Pin
                    </DropdownMenuItem>
                )}
                {thread.is_locked ? (
                    <DropdownMenuItem onClick={onUnlock}>
                        <Unlock className="mr-2 h-4 w-4" />
                        Unlock replies
                    </DropdownMenuItem>
                ) : (
                    <DropdownMenuItem onClick={onLock}>
                        <Lock className="mr-2 h-4 w-4" />
                        Lock replies
                    </DropdownMenuItem>
                )}
                {thread.is_hidden ? (
                    <DropdownMenuItem onClick={onUnhide}>
                        <Eye className="mr-2 h-4 w-4" />
                        Unhide
                    </DropdownMenuItem>
                ) : (
                    <DropdownMenuItem onClick={onHide}>
                        <EyeOff className="mr-2 h-4 w-4" />
                        Hide
                    </DropdownMenuItem>
                )}
                {onDelete && (
                    <>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={onDelete} className="text-red-600">
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                        </DropdownMenuItem>
                    </>
                )}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
