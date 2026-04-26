import { Lock } from 'lucide-react';

interface LockedModuleNoticeProps {
    /** Title of the locked content/assignment, displayed above the notice. */
    title?: string;
}

/**
 * LockedModuleNotice — empty state shown in the main content area when the
 * learner clicks (or auto-lands on) a content item inside a module that
 * isn't yet unlocked. Pure presentational; the lock decision happens
 * upstream via `moduleAvailability`.
 */
export function LockedModuleNotice({ title }: LockedModuleNoticeProps) {
    return (
        <div className="flex flex-col items-center justify-center h-full text-center p-12">
            <div className="h-20 w-20 rounded-full bg-muted flex items-center justify-center mb-6">
                <Lock className="h-10 w-10 text-muted-foreground" />
            </div>
            {title && <h3 className="text-xl font-semibold">{title}</h3>}
            <p className="text-muted-foreground mt-2 max-w-md">
                Complete the previous module to unlock this content.
            </p>
        </div>
    );
}
