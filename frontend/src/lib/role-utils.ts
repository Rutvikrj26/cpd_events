import { Subscription } from "@/api/billing/types";
import { User } from "@/api/accounts/types";

type RoleFlags = {
    isAdmin: boolean;
    isOrganizer: boolean;
    isCourseManager: boolean;
    isAttendee: boolean;
};

export const getRoleFlags = (
    user?: User | null,
    subscription?: Subscription | null
): RoleFlags => {
    const roles = new Set<string>();
    const plan = subscription?.plan;

    if (plan === "organization") {
        roles.add("organizer");
        roles.add("course_manager");
    } else if (plan === "organizer") {
        roles.add("organizer");
    } else if (plan === "lms") {
        roles.add("course_manager");
    } else if (plan === "attendee") {
        roles.add("attendee");
    }

    if (!plan && user?.account_type) {
        roles.add(user.account_type);
    }

    if (user?.account_type === "admin") {
        roles.add("admin");
    }

    const isAdmin = roles.has("admin");
    const isOrganizer = isAdmin || roles.has("organizer");
    const isCourseManager = isAdmin || roles.has("course_manager");
    const isAttendee = roles.has("attendee") && !isOrganizer && !isCourseManager && !isAdmin;

    return {
        isAdmin,
        isOrganizer,
        isCourseManager,
        isAttendee,
    };
};
