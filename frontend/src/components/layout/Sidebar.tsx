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
    FileText
} from 'lucide-react';
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ModeToggle } from "@/components/mode-toggle";

export const Sidebar = () => {
    const { user, logout } = useAuth();
    const [isCollapsed, setIsCollapsed] = useState(false);
    const isOrganizer = user?.account_type === 'organizer' || user?.account_type === 'admin';

    const navItems = [
        { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
        { to: '/events', icon: Calendar, label: 'Events' },
        { to: '/registrations', icon: BookOpen, label: 'My Registrations', show: !isOrganizer },
        { to: '/certificates', icon: Award, label: 'Certificates', show: !isOrganizer },
        { to: '/organizer/certificates/templates', icon: FileText, label: 'Cert. Templates', show: isOrganizer },
        { to: '/billing', icon: CreditCard, label: 'Billing' },
        { to: '/profile', icon: UserCircle, label: 'Profile' },
        { to: '/settings', icon: Settings, label: 'Settings', show: false }, // Placeholder
    ];

    const toggleSidebar = () => setIsCollapsed(!isCollapsed);

    const NavItem = ({ item }: { item: any }) => (
        <NavLink
            to={item.to}
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
            <div className={cn("p-6 border-b border-border flex items-center", isCollapsed ? "justify-center p-4" : "justify-between")}>
                {!isCollapsed && (
                    <div className="overflow-hidden">
                        <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-teal-400 text-transparent bg-clip-text whitespace-nowrap">
                            CPD Events
                        </h1>
                        <p className="text-xs text-muted-foreground mt-1 truncate">{isOrganizer ? 'Organizer Portal' : 'Attendee Portal'}</p>
                    </div>
                )}
                {isCollapsed && <span className="font-bold text-primary text-xl">CPD</span>}
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
                {navItems.filter(item => item.show !== false).map((item) => (
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
