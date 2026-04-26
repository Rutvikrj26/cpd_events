/**
 * features/public — surface for unauthenticated marketing pages.
 *
 * Most public pages are static prose (terms, privacy, FAQ) and don't
 * need their own hooks. Discovery pages (events, courses, programs)
 * use `usePublicEvents`, `usePublicCourses`, `usePublicPrograms` from
 * their respective features instead — events live with events, etc.
 *
 * Re-export the public catalog hooks here as a convenience for the
 * landing-page experience that pulls from all three.
 */
export { usePublicEvents } from '@/features/events';
export { usePublicCourses } from '@/features/courses';
export { usePublicPrograms } from '@/features/programs';
