import React, { useState, useEffect } from 'react';
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
    FileText,
    Video,
    Search,
    Users,
    TrendingUp
} from 'lucide-react';
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { ModeToggle } from "@/components/mode-toggle";
import { Subscription } from "@/api/billing/types";
import { getRoleFlags } from "@/lib/role-utils";
import { getCPDTransactionSummary } from "@/api/cpd";

type NavItemConfig = {
    routeKey: string;
    to: string;
    icon: React.ElementType;
    label: string;
    end?: boolean;
    attendeeOnly?: boolean;
    learnerOnly?: boolean;
    organizerOnly?: boolean;
    courseManagerOnly?: boolean;
    creatorOnly?: boolean;
    eventOnly?: boolean;
};

export const Sidebar = ({ subscription }: { subscription?: Subscription | null }) => {
    const { user, logout, hasRoute, hasFeature, manifest } = useAuth();
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [cpdBalance, setCpdBalance] = useState<number | null>(null);
    const { isOrganizer, isCourseManager, isAttendee } = getRoleFlags(user, subscription);
    const isLearner = isAttendee || isCourseManager;
    const isCreator = isOrganizer || isCourseManager;
    const plan = subscription?.plan;
    const isLmsPlan = plan === 'lms';
    
    const portalLabel = subscription?.plan === 'pro'
        ? 'Creator Portal'
        : isOrganizer
            ? 'Organizer Portal'
            : isCourseManager
                ? 'Course Manager Portal'
                : 'Attendee Portal';

    useEffect(() => {
        if (isAttendee) {
            getCPDTransactionSummary()
                .then(summary => setCpdBalance(summary.current_balance))
                .catch(() => setCpdBalance(null));
        }
    }, [isAttendee]);

    // Define nav items with route keys matching backend ROUTE_REGISTRY
    const navItems: NavItemConfig[] = [
        { routeKey: 'dashboard', to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
        
        // Browse/Discovery pages for attendees
        { routeKey: 'browse_events', to: '/events/browse', icon: Search, label: 'Browse Events', attendeeOnly: true, eventOnly: true },
        { routeKey: 'browse_courses', to: '/courses/browse', icon: Search, label: 'Browse Courses', attendeeOnly: true },
        
        // My Content pages
        { routeKey: 'registrations', to: '/registrations', icon: Calendar, label: 'My Events', attendeeOnly: true, eventOnly: true },
        { routeKey: 'my_courses', to: '/my-courses', icon: BookOpen, label: 'My Courses', attendeeOnly: true },
        { routeKey: 'certificates', to: '/certificates', icon: Award, label: 'My Certificates', attendeeOnly: true },
        { routeKey: 'badges', to: '/badges', icon: Award, label: 'My Badges', attendeeOnly: true },
        { routeKey: 'cpd_tracking', to: '/cpd', icon: TrendingUp, label: 'CPD Tracking', attendeeOnly: true },

        // Organizer Pages
        { routeKey: 'my_events', to: '/events', icon: Calendar, label: 'My Events', organizerOnly: true, eventOnly: true },
        { routeKey: 'creator_certificates', to: '/organizer/certificates', icon: Award, label: 'Certificates', creatorOnly: true },
        { routeKey: 'event_badges', to: '/organizer/badges', icon: Award, label: 'Badges', creatorOnly: true },
        { routeKey: 'zoom_meetings', to: '/organizer/zoom', icon: Video, label: 'Zoom Meetings', organizerOnly: true, eventOnly: true },
        { routeKey: 'contacts', to: '/organizer/contacts', icon: Users, label: 'Contacts', organizerOnly: true, eventOnly: true },
        { routeKey: 'subscriptions', to: '/billing', icon: CreditCard, label: 'Billing', creatorOnly: true },

        // Course Manager Specific
        { routeKey: 'courses', to: '/courses/manage', icon: FileText, label: 'Manage Courses', courseManagerOnly: true },
        { routeKey: 'course_certificates', to: '/courses/certificates', icon: Award, label: 'Course Certificates', courseManagerOnly: true },

        // --- SHARED ITEMS ---
        { routeKey: 'profile', to: '/settings', icon: UserCircle, label: 'Profile' },
    ];

    // Filter items based on role first, then listener to context
    const visibleItems = navItems.filter(item => {
        // Hide event-only features from LMS-only users (who should only see course features)
        // The role-based filtering below (attendeeOnly, organizerOnly) handles most access control
        if (isLmsPlan && item.eventOnly) return false;

        // 1. Role-based filtering (Security/UX)
        if (item.attendeeOnly && !isAttendee) return false;
        if (item.learnerOnly && !isLearner) return false;
        if (item.organizerOnly && !isOrganizer) return false;
        if (item.courseManagerOnly && !isCourseManager) return false;
        if (item.creatorOnly && !isCreator) return false;

        // 2. Manifest/Feature Flag filtering (Fine-grained control)
        if (manifest && manifest.routes.length > 0) {
            // Always accessible routes (truly universal)
            if (['dashboard', 'profile'].includes(item.routeKey)) return true;

            // Role-based filtering above (lines 176-180) is the primary filter
            // These routes are already filtered by attendeeOnly/organizerOnly/etc flags
            // The manifest check here is a secondary validation for edge cases
            const commonRoutes = ['my_events', 'browse_events', 'browse_courses', 'my_courses',
                                  'course_certificates', 'creator_certificates',
                                  'contacts', 'cpd_tracking', 'event_badges', 'badges'];
            if (commonRoutes.includes(item.routeKey)) {
                // Trust role-based filtering above, but verify with manifest if available
                return hasRoute(item.routeKey);
            }

            // Explicit feature checks for specific routes
            if (item.routeKey === 'certificates') return hasFeature('view_own_certificates');
            if (item.routeKey === 'browse_events') return hasFeature('browse_events');
            if (item.routeKey === 'subscriptions') return hasFeature('view_billing');

            // Default: check manifest for route key
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
            {!isCollapsed && (
                <span className="truncate flex-1">{item.label}</span>
            )}
            {/* Show CPD balance badge next to CPD Tracking link */}
            {!isCollapsed && item.routeKey === 'cpd_tracking' && cpdBalance !== null && (
                <Badge variant="secondary" className="ml-auto text-xs font-semibold">
                    {cpdBalance}
                </Badge>
            )}

            {/* Tooltip for collapsed state */}
            {isCollapsed && (
                <div className="absolute left-full ml-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 pointer-events-none border border-border">
                    {item.label}
                    {item.routeKey === 'cpd_tracking' && cpdBalance !== null && ` (${cpdBalance} credits)`}
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
