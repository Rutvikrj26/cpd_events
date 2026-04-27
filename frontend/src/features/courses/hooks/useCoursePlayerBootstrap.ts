/**
 * useCoursePlayerBootstrap — single fetch behind the course player.
 *
 * Replaces the 8-query orchestration the player used to do (course +
 * enrollments + progress + modules + announcements + sessions +
 * submissions + per-module-content) with one typed request against
 * `/api/v1/courses/{uuid}/player-bootstrap/`.
 *
 * The response is one of three discriminated shapes (see
 * `backend/src/learning/bootstrap_serializers.py`):
 *   - `granted` — full curriculum + progress; render the player.
 *   - `pending_approval` — slim shell payload; render PendingApprovalShell.
 *   - `redirect_to_detail` — slug + reason; navigate to /courses/{slug}.
 *
 * Consumers exhaustively switch on `data.access.kind` with TypeScript
 * narrowing — no boolean cascades, no race conditions, no toast spam
 * from per-resource 403s.
 */

import { useQuery } from '@tanstack/react-query';

import client from '@/api/client';
import type { components, paths } from '@/api/generated/schema';

// Source-of-truth types lifted from the generated OpenAPI schema. Editing
// the response shape on the backend changes these on the next
// `npm run generate-types` — there's no second place for them to drift.
export type CoursePlayerBootstrap = components['schemas']['CoursePlayerBootstrap'];
export type CoursePlayerGranted = components['schemas']['CoursePlayerGranted'];
export type CoursePlayerPendingApproval = components['schemas']['CoursePlayerPendingApproval'];
export type CoursePlayerRedirect = components['schemas']['CoursePlayerRedirect'];
export type CourseEnrollmentViewState = components['schemas']['_CourseEnrollmentViewState'];
export type ModuleProgressSlice = components['schemas']['_ModuleProgressSlice'];

// Discriminator narrowing helpers — preferred over `data.access.kind === 'x'`
// at call sites because they centralize the comparison.
export const isGranted = (data: CoursePlayerBootstrap): data is CoursePlayerGranted =>
    data.access.kind === 'granted';
export const isPendingApproval = (data: CoursePlayerBootstrap): data is CoursePlayerPendingApproval =>
    data.access.kind === 'pending_approval';
export const isRedirect = (data: CoursePlayerBootstrap): data is CoursePlayerRedirect =>
    data.access.kind === 'redirect_to_detail';

const PLAYER_BOOTSTRAP_PATH = '/api/v1/courses/{uuid}/player-bootstrap/' as const;
type Op = paths[typeof PLAYER_BOOTSTRAP_PATH]['get'];

async function fetchPlayerBootstrap(courseUuid: string): Promise<CoursePlayerBootstrap> {
    // The path in the generated schema includes the /api/v1/ prefix; the
    // axios client is configured with baseURL `/api/v1`, so we strip it.
    const url = `/courses/${courseUuid}/player-bootstrap/`;
    const response = await client.get<CoursePlayerBootstrap>(url);
    return response.data;
}

export function useCoursePlayerBootstrap(courseUuid: string | undefined) {
    return useQuery<CoursePlayerBootstrap>({
        queryKey: ['courses', 'player-bootstrap', courseUuid],
        queryFn: () => fetchPlayerBootstrap(courseUuid!),
        enabled: Boolean(courseUuid),
        // The bootstrap is a first-paint snapshot. Mutations on individual
        // resources (mark complete, post discussion) invalidate their own
        // narrow keys; this key is only refreshed on view-state-changing
        // mutations (enroll, drop, complete, refund, instructor-approve).
        staleTime: 1000 * 60,
        retry: false,
    });
}

// Convenience for components that need the granted-only data. Throws at
// runtime if called against a non-granted response — meant for code that
// runs inside an `isGranted(data)` branch already.
export function assertGranted(data: CoursePlayerBootstrap): CoursePlayerGranted {
    if (!isGranted(data)) {
        throw new Error(`Expected granted bootstrap, got access.kind=${data.access.kind}`);
    }
    return data;
}
