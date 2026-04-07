import { User } from "@/api/accounts/types";

type RoleFlags = {
    isAdmin: boolean;
    isEducator: boolean;
    isCourseManager: boolean;
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
    const isCreator = isEducator || isCourseManager;
    const isLearner = !isCreator && (roles.has("learner") || roles.size === 0);

    return {
        isAdmin,
        isEducator,
        isCourseManager,
        isLearner,
        isCreator,
    };
};

// Backward compat aliases
export type { RoleFlags };
