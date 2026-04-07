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
    Search,
    Users,
    TrendingUp,
    Video,
    Shield,
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
    educatorOnly?: boolean;
    courseManagerOnly?: boolean;
    creatorOnly?: boolean;
    adminOnly?: boolean;
};

export const Sidebar = () => {
    const { user, logout, hasRoute, hasFeature, manifest } = useAuth();
    const [isCollapsed, setIsCollapsed] = useState(false);
    const { isEducator, isCourseManager, isLearner, isCreator, isAdmin } = getRoleFlags(user);

    const institutionName = manifest?.deployment?.institution_name || 'Accredit';
    const portalLabel = isAdmin
        ? 'Admin Portal'
        : isEducator
            ? 'Educator Portal'
            : isCourseManager
                ? 'Course Manager Portal'
                : 'Learner Portal';

    const navItems: NavItemConfig[] = [
        { routeKey: 'dashboard', to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },

        // Learner items
        { routeKey: 'browse_events', to: '/events', icon: Search, label: 'Browse Events', learnerOnly: true },
        { routeKey: 'browse_courses', to: '/courses', icon: BookOpen, label: 'Browse Courses', learnerOnly: true },
        { routeKey: 'registrations', to: '/registrations', icon: BookOpen, label: 'My Registrations', learnerOnly: true },
        { routeKey: 'certificates', to: '/certificates', icon: Award, label: 'My Certificates', learnerOnly: true },
        { routeKey: 'badges', to: '/badges', icon: Award, label: 'My Badges', learnerOnly: true },
        { routeKey: 'cpd_tracking', to: '/cpd', icon: TrendingUp, label: 'CPD Tracking', learnerOnly: true },

        // Educator items
        { routeKey: 'my_events', to: '/events', icon: Calendar, label: 'My Events', educatorOnly: true },
        { routeKey: 'creator_certificates', to: '/organizer/certificates', icon: Award, label: 'Certificates', creatorOnly: true },
        { routeKey: 'event_badges', to: '/organizer/badges', icon: Award, label: 'Badges', creatorOnly: true },
        { routeKey: 'video_rooms', to: '/organizer/video', icon: Video, label: 'Video Rooms', creatorOnly: true },
        { routeKey: 'contacts', to: '/organizer/contacts', icon: Users, label: 'Contacts', educatorOnly: true },

        // Course Manager items
        { routeKey: 'courses', to: '/courses/manage', icon: FileText, label: 'Manage Courses', courseManagerOnly: true },
        { routeKey: 'course_certificates', to: '/courses/certificates', icon: Award, label: 'Course Certificates', courseManagerOnly: true },

        // Admin items
        { routeKey: 'admin_users', to: '/admin/users', icon: Shield, label: 'User Management', adminOnly: true },

        // Shared
        { routeKey: 'profile', to: '/settings', icon: UserCircle, label: 'Profile' },
    ];

    const visibleItems = navItems.filter(item => {
        // Role-based filtering
        if (item.learnerOnly && !isLearner) return false;
        if (item.educatorOnly && !isEducator) return false;
        if (item.courseManagerOnly && !isCourseManager) return false;
        if (item.creatorOnly && !isCreator) return false;
        if (item.adminOnly && !isAdmin) return false;

        // Feature flag filtering via manifest
        if (manifest && manifest.routes.length > 0) {
            // Items that don't need feature checks (basic navigation)
            const alwaysShow = ['dashboard', 'profile', 'browse_events', 'browse_courses', 'cpd_tracking', 'badges'];
            if (alwaysShow.includes(item.routeKey)) return true;

            // Map nav items to manifest features
            if (item.routeKey === 'certificates') return hasFeature('view_own_certificates');
            if (item.routeKey === 'registrations') return hasFeature('view_own_registrations');
            if (item.routeKey === 'my_events') return hasFeature('create_events');
            if (item.routeKey === 'contacts') return hasFeature('manage_contacts');
            if (item.routeKey === 'creator_certificates') return hasFeature('manage_certificates');
            if (item.routeKey === 'event_badges') return hasFeature('manage_badges');
            if (item.routeKey === 'video_rooms') return hasFeature('manage_video');
            if (item.routeKey === 'courses') return hasFeature('create_courses');
            if (item.routeKey === 'course_certificates') return hasFeature('create_courses');
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
