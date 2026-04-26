/**
 * features/dashboard — composable role-aware dashboards.
 *
 * The dashboard pages in `pages/dashboard/{role}/` should be < 100 LOC
 * thin shells that compose these components + hooks.
 */
export {
    HeroBand,
    MiniStat,
    SectionHeader,
    DashboardSkeleton,
} from './components';
export type {
    HeroBandProps,
    HeroAction,
    MiniStatProps,
    MiniStatTone,
    SectionHeaderProps,
} from './components';

export {
    useAttendeeDashboard,
    useInstructorDashboard,
    useOrganizerDashboard,
    dashboardKeys,
} from './hooks';
export type {
    AttendeeDashboardData,
    InstructorDashboardData,
    OrganizerDashboardData,
    ResumeCandidate,
} from './hooks';
