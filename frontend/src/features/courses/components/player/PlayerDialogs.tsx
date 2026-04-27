import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from '@/shared/ui/dialog';
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
} from '@/shared/ui/card';
import { DiscussionPanel } from '@/components/courses/discussion/DiscussionPanel';
import type { CourseAnnouncement } from '@/api/courses/types';

interface PlayerDialogsProps {
    courseUuid: string;
    currentUserUuid?: string;
    announcements: CourseAnnouncement[];
    showAnnouncements: boolean;
    onAnnouncementsOpenChange: (open: boolean) => void;
    showDiscussion: boolean;
    onDiscussionOpenChange: (open: boolean) => void;
}

/**
 * PlayerDialogs — announcements + discussion modals.
 *
 * Pulled out of `<CoursePlayer>` to keep the orchestrator under its LOC
 * budget. Both dialogs are local-state driven; the alternative is the
 * shared `DialogHost` pattern but these are tightly scoped to this page.
 */
export function PlayerDialogs({
    courseUuid,
    currentUserUuid,
    announcements,
    showAnnouncements,
    onAnnouncementsOpenChange,
    showDiscussion,
    onDiscussionOpenChange,
}: PlayerDialogsProps) {
    return (
        <>
            <Dialog open={showAnnouncements} onOpenChange={onAnnouncementsOpenChange}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>Course Announcements</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 max-h-[60vh] overflow-y-auto">
                        {announcements.length === 0 ? (
                            <p className="text-sm text-muted-foreground">No announcements yet.</p>
                        ) : (
                            announcements.map((announcement) => (
                                <Card key={announcement.uuid}>
                                    <CardHeader className="pb-2">
                                        <CardTitle className="text-base">
                                            {announcement.title}
                                        </CardTitle>
                                        <p className="text-xs text-muted-foreground">
                                            {new Date(announcement.created_at).toLocaleDateString()}
                                            {announcement.created_by_name
                                                ? ` • ${announcement.created_by_name}`
                                                : ''}
                                        </p>
                                    </CardHeader>
                                    <CardContent className="pt-0 text-sm text-muted-foreground whitespace-pre-wrap">
                                        {announcement.body}
                                    </CardContent>
                                </Card>
                            ))
                        )}
                    </div>
                </DialogContent>
            </Dialog>

            <Dialog open={showDiscussion} onOpenChange={onDiscussionOpenChange}>
                <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>Discussion</DialogTitle>
                    </DialogHeader>
                    <DiscussionPanel
                        courseUuid={courseUuid}
                        currentUserUuid={currentUserUuid}
                        isStaff={false}
                    />
                </DialogContent>
            </Dialog>
        </>
    );
}
