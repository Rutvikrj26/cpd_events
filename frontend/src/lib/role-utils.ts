import { User } from "@/api/accounts/types";

type RoleFlags = {
    isAdmin: boolean;
    isEducator: boolean;
    isCourseManager: boolean;
    isInstructor: boolean;
    isLearner: boolean;
    isCreator: boolean;
};

/**
 * Derive role flags from user's group-based roles.
 * No longer depends on subscription plans.
 */
export const getRoleFlags = (user?: User | null): RoleFlags => {
    const roles = new Set(user?.roles ?? []);
    const primaryRole = user?.primary_role;

    const isAdmin = primaryRole === "admin" || roles.has("admin");
    const isEducator = isAdmin || roles.has("educator");
    const isCourseManager = isAdmin || roles.has("course_manager");
    const isInstructor = roles.has("instructor") && !isAdmin;
    const isCreator = isEducator || isCourseManager;
    const isLearner = !isCreator && !isInstructor && (roles.has("learner") || roles.size === 0);

    return {
        isAdmin,
        isEducator,
        isCourseManager,
        isInstructor,
        isLearner,
        isCreator,
    };
};

// Backward compat aliases
export type { RoleFlags };

/** Turn a role slug ("course_manager") into a human label ("Course Manager"). */
export const formatRoleLabel = (slug: string | null | undefined): string => {
    if (!slug) return '';
    return slug
        .replace(/[_-]+/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
};
