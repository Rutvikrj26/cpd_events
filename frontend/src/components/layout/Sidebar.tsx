import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import {
    LayoutDashboard,
    Calendar,
    BookOpen,
    Award,
    LogOut,
    UserCircle,
    ChevronLeft,
    ChevronRight,
    FileText,
    GraduationCap,
    Users,
    TrendingUp,
    Video,
    Shield,
    Tag,
    Mic,
    BarChart3,
} from 'lucide-react';
import { cn } from "@/lib/utils";
import { ModeToggle } from "@/components/mode-toggle";
import { getRoleFlags } from "@/lib/role-utils";

type NavItemConfig = {
    routeKey: string;
    to: string;
    icon: React.ElementType;
    label: string;
    end?: boolean;
    learnerOnly?: boolean;
    organizerOnly?: boolean;
    instructorOnly?: boolean;
    // Visible to anyone who creates content (organizer or instructor).
    organizerOrInstructor?: boolean;
    adminOnly?: boolean;
};

export const Sidebar = () => {
    const { user, logout, hasRoute, hasFeature, manifest } = useAuth();
    const [isCollapsed, setIsCollapsed] = useState(false);
    const { isOrganizer, isInstructor, isLearner, isAdmin } = getRoleFlags(user);

    const institutionName = manifest?.deployment?.institution_name || 'Accredit';
    const portalLabel = isAdmin
        ? 'Admin Portal'
        : isOrganizer
            ? 'Organizer Portal'
            : isInstructor
                ? 'Instructor Portal'
                : 'Learner Portal';

    const navItems: NavItemConfig[] = [
        { routeKey: 'dashboard', to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },

        // Learner items
        { routeKey: 'registrations', to: '/registrations', icon: GraduationCap, label: 'My Learning', learnerOnly: true },
        { routeKey: 'accreditations', to: '/accreditations', icon: Award, label: 'My Accreditations', learnerOnly: true },
        { routeKey: 'my_programs', to: '/my-programs', icon: BookOpen, label: 'My Programs', learnerOnly: true },
        { routeKey: 'cpd_tracking', to: '/cpd', icon: TrendingUp, label: 'CPD Tracking', learnerOnly: true },

        // Organizer items (event management)
        { routeKey: 'manage_events', to: '/events', icon: Calendar, label: 'Manage Events', organizerOnly: true },
        { routeKey: 'video_rooms', to: '/organizer/video', icon: Video, label: 'Video Rooms', organizerOrInstructor: true },
        { routeKey: 'contacts', to: '/organizer/contacts', icon: Users, label: 'Contacts', organizerOnly: true },
        { routeKey: 'speakers', to: '/organizer/speakers', icon: Mic, label: 'Speakers', organizerOnly: true },
        { routeKey: 'promo_codes', to: '/organizer/promo-codes', icon: Tag, label: 'Promo Codes', organizerOnly: true },
        { routeKey: 'reports', to: '/organizer/reports', icon: BarChart3, label: 'Reports', organizerOrInstructor: true },

        // Instructor items (course management)
        { routeKey: 'courses', to: '/courses/manage', icon: FileText, label: 'Manage Courses', instructorOnly: true },
        { routeKey: 'programs', to: '/programs/manage', icon: BookOpen, label: 'Manage Programs', instructorOnly: true },

        // Shared creator items
        { routeKey: 'manage_accreditations', to: '/manage/accreditations', icon: Award, label: 'Accreditations', organizerOrInstructor: true },

        // Admin items
        { routeKey: 'admin_users', to: '/admin/users', icon: Shield, label: 'User Management', adminOnly: true },

        // Shared
        { routeKey: 'profile', to: '/settings', icon: UserCircle, label: 'Profile' },
    ];

    const visibleItems = navItems.filter(item => {
        // Role-based filtering
        if (item.learnerOnly && !isLearner) return false;
        if (item.organizerOnly && !isOrganizer) return false;
        if (item.instructorOnly && !isInstructor) return false;
        if (item.organizerOrInstructor && !(isOrganizer || isInstructor)) return false;
        if (item.adminOnly && !isAdmin) return false;

        // Feature flag filtering via manifest
        if (manifest && manifest.routes.length > 0) {
            // Items whose visibility is driven purely by role (no feature flag gate).
            // Keep the list tight — everything else must map to a named feature.
            const alwaysShow = ['dashboard', 'profile', 'cpd_tracking', 'courses', 'programs', 'accreditations', 'manage_accreditations', 'my_programs'];
            if (alwaysShow.includes(item.routeKey)) return true;

            // Map nav items to manifest features
            if (item.routeKey === 'registrations') return hasFeature('view_own_registrations');
            if (item.routeKey === 'manage_events') return hasFeature('create_events');
            if (item.routeKey === 'contacts') return hasFeature('manage_contacts');
            if (item.routeKey === 'video_rooms') return hasFeature('manage_video');
            if (item.routeKey === 'speakers') return hasFeature('create_events');
            if (item.routeKey === 'promo_codes') return hasFeature('create_events');
            // Reports page has Events/Courses/Programs tabs — show if the user
            // can see at least one of them.
            if (item.routeKey === 'reports') return hasFeature('create_events') || hasFeature('create_courses');
            if (item.routeKey === 'admin_users') return hasFeature('manage_users');

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
                                    {institutionName}
                                </h1>
                                <p className="text-xs text-muted-foreground mt-0.5 truncate">{portalLabel}</p>
                            </div>
                        )}
                    </NavLink>
                </div>
            </div>

            {/* Toggle Button */}
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

            {/* Footer */}
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
