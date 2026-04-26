import type { Assignment } from '@/api/courses/types';
import type { ContentWithProgress } from '../../hooks';

/** Active item in the player — either a content row or an assignment row. */
export type CourseItem =
    | { type: 'content'; item: ContentWithProgress; moduleUuid: string }
    | { type: 'assignment'; item: Assignment; moduleUuid: string };
