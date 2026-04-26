import { useParams } from 'react-router-dom';
import { CoursePlayer } from '@/features/courses';
import { useAuth } from '@/features/auth';

/**
 * CoursePlayerPage — thin route shell.
 *
 * The actual player UI lives in `features/courses/components/player/`.
 * This page just resolves the route param, the auth user, and forwards
 * both into the orchestrator.
 */
export function CoursePlayerPage() {
    const { courseUuid } = useParams<{ courseUuid: string }>();
    const { user } = useAuth();

    if (!courseUuid) return null;

    return <CoursePlayer courseUuid={courseUuid} currentUserUuid={user?.uuid} />;
}

export default CoursePlayerPage;
