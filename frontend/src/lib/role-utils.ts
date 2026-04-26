import { User } from "@/api/accounts/types";

type RoleFlags = {
    isAdmin: boolean;
    isOrganizer: boolean;
    isInstructor: boolean;
    isLearner: boolean;
};

/**
 * Derive role flags from user's group-based roles.
 *
 * The institutional role model has two content-creator roles:
 * - `organizer` for event management
 * - `instructor` for course + program management (incl. course-internal sessions)
 *
 * Admin inherits both. A user can be both `organizer` and `instructor`.
 */
export const getRoleFlags = (user?: User | null): RoleFlags => {
    const roles = new Set(user?.roles ?? []);
    const primaryRole = user?.primary_role;

    const isAdmin = primaryRole === "admin" || roles.has("admin");
    const isOrganizer = isAdmin || roles.has("organizer");
    const isInstructor = isAdmin || roles.has("instructor");
    const isLearner = !isOrganizer && !isInstructor && (roles.has("learner") || roles.size === 0);

    return {
        isAdmin,
        isOrganizer,
        isInstructor,
        isLearner,
    };
};

export type { RoleFlags };

/** Turn a role slug ("instructor") into a human label ("Instructor"). */
export const formatRoleLabel = (slug: string | null | undefined): string => {
    if (!slug) return '';
    return slug
        .replace(/[_-]+/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
};
