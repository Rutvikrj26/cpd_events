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
    Building2,
    Search
} from 'lucide-react';
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ModeToggle } from "@/components/mode-toggle";
import { OrganizationSwitcher } from "@/components/organizations/OrganizationSwitcher";
import { useOrganization } from "@/contexts/OrganizationContext";

export const Sidebar = () => {
    const { user, logout, hasRoute, hasFeature, manifest } = useAuth();
    const [isCollapsed, setIsCollapsed] = useState(false);
    const isOrganizer = user?.account_type === 'organizer' || user?.account_type === 'admin';

    const { currentOrg } = useOrganization();

    // Define nav items with route keys matching backend ROUTE_REGISTRY
    const navItems = [
        { routeKey: 'dashboard', to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
        { routeKey: 'browse_events', to: '/events', icon: Search, label: 'Browse Events', attendeeOnly: true },
        { routeKey: 'my_events', to: '/events', icon: Calendar, label: 'My Events', organizerOnly: true },
        // Dynamic Org Courses Link - visible only when context is set (handled in filter)
        {
            routeKey: 'org_courses',
            to: currentOrg ? `/org/${currentOrg.slug}/courses` : '/courses',
            icon: BookOpen,
            label: 'Courses',
            organizerOnly: true,
            requiresOrg: true
        },
        { routeKey: 'registrations', to: '/registrations', icon: BookOpen, label: 'My Registrations', attendeeOnly: true },
        { routeKey: 'certificates', to: '/certificates', icon: Award, label: 'My Certificates', attendeeOnly: true },
        { routeKey: 'org_certificates', to: '/organizer/certificates', icon: Award, label: 'Certificates', organizerOnly: true, end: true },
        // { routeKey: 'cert_templates', to: '/organizer/certificates/templates', icon: FileText, label: 'Cert. Templates', organizerOnly: true }, // REMOVED

        { routeKey: 'zoom', to: '/organizer/zoom', icon: Video, label: 'Zoom Meetings', organizerOnly: true },
        { routeKey: 'organizations', to: '/organizations', icon: Building2, label: 'Organizations', organizerOnly: true },
        { routeKey: 'billing', to: '/billing', icon: CreditCard, label: 'Billing', organizerOnly: true },
        { routeKey: 'profile', to: '/profile', icon: UserCircle, label: 'Profile' },
    ];

    // Filter items based on role first, then optionally use manifest for fine-grained control
    const visibleItems = navItems.filter(item => {
        // FIRST: Apply role-based filtering - this always takes precedence
        // Hide attendee-only items for organizers
        if (item.attendeeOnly && isOrganizer) {
            return false;
        }
        // Hide organizer-only items for attendees
        if (item.organizerOnly && !isOrganizer) {
            return false;
        }

        // Hide items requiring org context if none selected
        if (item.requiresOrg && !currentOrg) {
            return false;
        }

        // SECOND: If manifest is loaded, use it for additional fine-grained control
        if (manifest && manifest.routes.length > 0) {
            // Items always visible (not in RBAC registry)
            if (['dashboard', 'profile'].includes(item.routeKey)) {
                return true;
            }
            // Organizer items not in manifest (frontend-only routes)
            if (['org_certificates', 'cert_templates', 'zoom', 'billing', 'organizations'].includes(item.routeKey)) {
                return isOrganizer;
            }
            // Use feature flag for certificates since it's not a distinct backend view
            if (item.routeKey === 'certificates') {
                return hasFeature('view_own_certificates');
            }
            return hasRoute(item.routeKey);
        }

        // Fallback: no manifest loaded, default to true (role filtering already applied)
        return true;
    });

    const toggleSidebar = () => setIsCollapsed(!isCollapsed);

    const NavItem = ({ item }: { item: any }) => (
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
                "h-screen bg-card text-card-foreground flex flex-col transition-all duration-300 ease-in-out border-r border-border relative",
                isCollapsed ? "w-20" : "w-64"
            )}
        >
            {/* Header */}
            <div className={cn("p-6 border-b border-border flex flex-col gap-3", isCollapsed ? "p-4 items-center" : "")}>
                <div className={cn("flex items-center", isCollapsed ? "justify-center" : "justify-between")}>
                    <NavLink to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                        {!isCollapsed && (
                            <div className="overflow-hidden">
                                <h1 className="text-xl font-bold gradient-text whitespace-nowrap">
                                    Accredit
                                </h1>
                                <p className="text-xs text-muted-foreground mt-1 truncate">{isOrganizer ? 'Organizer Portal' : 'Attendee Portal'}</p>
                            </div>
                        )}
                        {isCollapsed && <span className="font-bold text-primary text-xl">A</span>}
                    </NavLink>
                </div>

                {/* Organization Switcher - Only for organizers */}
                {isOrganizer && !isCollapsed && (
                    <OrganizationSwitcher />
                )}
                {isOrganizer && isCollapsed && (
                    <OrganizationSwitcher variant="compact" />
                )}
            </div>

            {/* Toggle Button - Absolute positioned overlapping the border */}
            <button
                onClick={toggleSidebar}
                className="absolute -right-3 top-10 bg-card border border-border text-muted-foreground hover:text-foreground rounded-full p-1 shadow-md hover:bg-accent transition-colors z-50"
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
