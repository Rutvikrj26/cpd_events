import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import {
    LayoutDashboard,
    Calendar,
    BookOpen,
    Award,
    CreditCard,
    LogOut,
    UserCircle,
    ChevronLeft,
    ChevronRight,
    Settings,
    FileText,
    Video,
    Search,
    Users,
    TrendingUp
} from 'lucide-react';
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ModeToggle } from "@/components/mode-toggle";
import { OrganizationSwitcher } from "@/components/organizations/OrganizationSwitcher";
import { useOrganization } from "@/contexts/OrganizationContext";
import { Subscription } from "@/api/billing/types";
import { getRoleFlags } from "@/lib/role-utils";

type NavItemConfig = {
    routeKey: string;
    to: string;
    icon: React.ElementType;
    label: string;
    end?: boolean;
    hideInOrg?: boolean;
    requiresOrg?: boolean;
    attendeeOnly?: boolean;
    learnerOnly?: boolean;
    organizerOnly?: boolean;
    courseManagerOnly?: boolean;
    creatorOnly?: boolean;
    eventOnly?: boolean;
    orgRoles?: Array<'admin' | 'organizer' | 'course_manager' | 'instructor'>;
};

export const Sidebar = ({ subscription }: { subscription?: Subscription | null }) => {
    const { user, logout, hasRoute, hasFeature, manifest } = useAuth();
    const [isCollapsed, setIsCollapsed] = useState(false);
    const { isOrganizer, isCourseManager, isAttendee } = getRoleFlags(user, subscription);
    const isLearner = isAttendee || isCourseManager;
    const isCreator = isOrganizer || isCourseManager;
    const plan = subscription?.plan;
    const isLmsPlan = plan === 'lms';
    const { currentOrg, organizations } = useOrganization();
    const orgRole = currentOrg?.user_role || null;
    const portalLabel = orgRole === 'instructor'
        ? 'Instructor Portal'
        : subscription?.plan === 'organization'
            ? 'Organization Portal'
            : isOrganizer
                ? 'Organizer Portal'
                : isCourseManager
                    ? 'Course Manager Portal'
                    : 'Attendee Portal';

    // Define nav items with route keys matching backend ROUTE_REGISTRY
    const navItems: NavItemConfig[] = [
        { routeKey: 'dashboard', to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', hideInOrg: true },
        { routeKey: 'browse_events', to: '/events', icon: Search, label: 'Browse Events', attendeeOnly: true, hideInOrg: true, eventOnly: true },
        { routeKey: 'browse_courses', to: '/courses', icon: BookOpen, label: 'Browse Courses', attendeeOnly: true, hideInOrg: true },
        { routeKey: 'my_events', to: '/events', icon: Calendar, label: 'My Events', organizerOnly: true, hideInOrg: true, eventOnly: true },
        { routeKey: 'registrations', to: '/registrations', icon: BookOpen, label: 'My Registrations', attendeeOnly: true, hideInOrg: true, eventOnly: true },
        { routeKey: 'certificates', to: '/certificates', icon: Award, label: 'My Certificates', attendeeOnly: true, hideInOrg: true },
        { routeKey: 'badges', to: '/badges', icon: Award, label: 'My Badges', attendeeOnly: true, hideInOrg: true },
        { routeKey: 'cpd_tracking', to: '/cpd', icon: TrendingUp, label: 'CPD Tracking', attendeeOnly: true, hideInOrg: true },

        // Organizer Specific (Personal Context)
        { routeKey: 'event_certificates', to: '/organizer/certificates', icon: Award, label: 'Certificates', organizerOnly: true, hideInOrg: true, eventOnly: true },
        { routeKey: 'creator_certificates', to: '/organizer/certificates', icon: Award, label: 'Certificates', creatorOnly: true, hideInOrg: true },
        { routeKey: 'event_badges', to: '/organizer/badges', icon: Award, label: 'Badges', creatorOnly: true, hideInOrg: true },
        { routeKey: 'zoom_meetings', to: '/organizer/zoom', icon: Video, label: 'Zoom Meetings', organizerOnly: true, hideInOrg: true, eventOnly: true },
        { routeKey: 'contacts', to: '/organizer/contacts', icon: Users, label: 'Contacts', organizerOnly: true, hideInOrg: true, eventOnly: true },
        // NOTE: "Organizations" link is removed as it's replaced by the Context Switcher
        { routeKey: 'subscriptions', to: '/billing', icon: CreditCard, label: 'Billing', creatorOnly: true, hideInOrg: true },

        // Course Manager Specific (Personal Context)
        { routeKey: 'courses', to: '/courses/manage', icon: FileText, label: 'Manage Courses', courseManagerOnly: true, hideInOrg: true },
        { routeKey: 'course_certificates', to: '/courses/certificates', icon: Award, label: 'Course Certificates', courseManagerOnly: true, hideInOrg: true },

        // --- ORGANIZATION CONTEXT ITEMS ---
        {
            routeKey: 'org_instructor',
            to: currentOrg ? `/org/${currentOrg.slug}/instructor` : '#',
            icon: LayoutDashboard,
            label: 'Instructor Home',
            requiresOrg: true,
            orgRoles: ['instructor'],
        },
        {
            routeKey: 'org_dashboard',
            to: currentOrg ? `/org/${currentOrg.slug}` : '#',
            icon: LayoutDashboard,
            label: 'Overview',
            requiresOrg: true,
            orgRoles: ['admin', 'organizer', 'course_manager'],
        },
        {
            routeKey: 'org_events',
            to: currentOrg ? `/org/${currentOrg.slug}/events` : '#',
            icon: Calendar,
            label: 'Events',
            requiresOrg: true,
            orgRoles: ['admin', 'organizer'],
        },
        {
            routeKey: 'org_courses',
            to: currentOrg ? `/org/${currentOrg.slug}/courses` : '#',
            icon: BookOpen,
            label: 'Courses',
            requiresOrg: true,
            orgRoles: ['admin', 'course_manager'],
        },
        {
            routeKey: 'org_badges',
            to: currentOrg ? `/org/${currentOrg.slug}/badges` : '#',
            icon: Award,
            label: 'Badges',
            requiresOrg: true,
            orgRoles: ['admin', 'course_manager'],
        },
        {
            routeKey: 'org_certificates',
            to: currentOrg ? `/org/${currentOrg.slug}/certificates` : '#',
            icon: Award,
            label: 'Certificates',
            requiresOrg: true,
            orgRoles: ['admin', 'course_manager'],
        },
        {
            routeKey: 'org_team',
            to: currentOrg ? `/org/${currentOrg.slug}/team` : '#',
            icon: Users,
            label: 'Team & Subscription',
            requiresOrg: true,
            orgRoles: ['admin', 'course_manager'],
        },
        {
            routeKey: 'org_settings',
            to: currentOrg ? `/org/${currentOrg.slug}/settings` : '#',
            icon: Settings,
            label: 'Settings',
            requiresOrg: true,
            orgRoles: ['admin'],
        },

        // --- SHARED ITEMS ---
        { routeKey: 'profile', to: '/settings', icon: UserCircle, label: 'Profile' },
    ];

    // Filter items based on role first, then listener to context
    const visibleItems = navItems.filter(item => {
        if (isLmsPlan && item.eventOnly) return false;

        // 1. Role-based filtering (Security/UX)
        if (item.attendeeOnly && !isAttendee) return false;
        if (item.learnerOnly && !isLearner) return false;
        if (item.organizerOnly && !isOrganizer) return false;
        if (item.courseManagerOnly && !isCourseManager) return false;
        if (item.creatorOnly && !isCreator) return false;

        // 2. Context-based filtering (Personal vs Org)
        if (currentOrg) {
            // We are in Organization Context
            if (item.hideInOrg) return false;
            if (item.orgRoles && (!orgRole || !item.orgRoles.includes(orgRole))) return false;
            // requiresOrg items are allowed (and shared items)
        } else {
            // We are in Personal Context
            if (item.requiresOrg) return false;
        }

        // 3. Manifest/Feature Flag filtering (Fine-grained control)
        if (manifest && manifest.routes.length > 0) {
            // Always allow basic shared routes and new org routes (assuming they are allowed if we are in the org)
            // TODO: Ideally check robust permissions for org routes, but checking 'requiresOrg' existence is a proxy for now
            if (['dashboard', 'profile', 'my_events', 'browse_events', 'browse_courses', 'course_certificates', 'creator_certificates', 'contacts', 'cpd_tracking', 'event_badges', 'badges'].includes(item.routeKey)) return true;
            if (item.requiresOrg) return true; // Assume if they are in the org, they can see the links (page will protect)

            if (item.routeKey === 'certificates') return hasFeature('view_own_certificates');
            if (item.routeKey === 'browse_events') return hasFeature('browse_events');

            // Check specific route keys
            if (item.routeKey.startsWith('org_')) return true; // Allow new org routes for now

            return hasRoute(item.routeKey);
        }

        return true;
    });

    const toggleSidebar = () => setIsCollapsed(!isCollapsed);

    const NavItem = ({ item }: { item: NavItemConfig }) => (
        <NavLink
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
                cn(
                    "flex items-center space-x-3 px-3 py-3 rounded-lg transition-all duration-200 group relative",
                    isActive
                        ? 'bg-accent text-foreground font-medium'
                        : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                    isCollapsed ? "justify-center" : ""
                )
            }
        >
            <item.icon size={20} className="shrink-0" />
            {!isCollapsed && <span className="truncate">{item.label}</span>}

            {/* Tooltip for collapsed state */}
            {isCollapsed && (
                <div className="absolute left-full ml-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 pointer-events-none border border-border">
                    {item.label}
                </div>
            )}
        </NavLink>
    );

    return (
        <div
            className={cn(
                "h-full bg-card text-card-foreground flex flex-col transition-all duration-300 ease-in-out border-r border-border relative shrink-0",
                isCollapsed ? "w-20" : "w-64"
            )}
        >
            {/* Header */}
            <div className={cn("p-6 border-b border-border flex flex-col gap-3", isCollapsed ? "p-4 items-center" : "")}>
                <div className={cn("flex items-center", isCollapsed ? "justify-center" : "justify-between")}>
                    <NavLink to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                        <div className={cn(
                            "flex items-center justify-center rounded-lg bg-white border border-border/50 overflow-hidden shadow-sm",
                            isCollapsed ? "h-9 w-9" : "h-8 w-8"
                        )}>
                            <img src="/letter-a.png" alt="Logo" className="h-full w-full object-contain p-1" />
                        </div>
                        {!isCollapsed && (
                            <div className="overflow-hidden">
                                <h1 className="text-xl font-bold gradient-text whitespace-nowrap font-outfit tracking-wide">
                                    Accredit
                                </h1>
                                <p className="text-xs text-muted-foreground mt-0.5 truncate">{portalLabel}</p>
                            </div>
                        )}
                    </NavLink>
                </div>

                {/* Organization Switcher - Available for any org member */}
                {organizations && organizations.length > 0 && (
                    <OrganizationSwitcher variant={isCollapsed ? "compact" : "default"} />
                )}
            </div>

            {/* Toggle Button - Absolute positioned overlapping the border */}
            <button
                onClick={toggleSidebar}
                className="absolute -right-3 top-10 bg-card border border-border text-muted-foreground hover:text-foreground rounded-full p-1 shadow-md hover:bg-accent transition-colors z-50"
                aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
                {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>

            {/* Navigation */}
            <nav className="flex-1 p-3 space-y-2 overflow-y-auto overflow-x-hidden scrollbar-thin scrollbar-thumb-muted">
                {visibleItems.map((item) => (
                    <NavItem key={item.to} item={item} />
                ))}
            </nav>

            {/* Footer Actions */}
            <div className="p-3 border-t border-border flex flex-col gap-2">
                <div className={cn("flex items-center", isCollapsed ? "justify-center" : "justify-between px-3")}>
                    {!isCollapsed && <span className="text-sm text-muted-foreground">Theme</span>}
                    <ModeToggle />
                </div>
                <button
                    onClick={logout}
                    className={cn(
                        "flex items-center space-x-3 px-3 py-3 w-full text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors group relative",
                        isCollapsed ? "justify-center" : ""
                    )}
                >
                    <LogOut size={20} className="shrink-0" />
                    {!isCollapsed && <span>Sign Out</span>}
                    {isCollapsed && (
                        <div className="absolute left-full ml-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 pointer-events-none border border-border">
                            Sign Out
                        </div>
                    )}
                </button>
            </div>
        </div>
    );
};
