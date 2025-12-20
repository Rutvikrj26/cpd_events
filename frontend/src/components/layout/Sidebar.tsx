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
    Settings
} from 'lucide-react';
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export const Sidebar = () => {
    const { user, logout } = useAuth();
    const [isCollapsed, setIsCollapsed] = useState(false);
    const isOrganizer = user?.account_type === 'organizer' || user?.account_type === 'admin';

    const navItems = [
        { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
        { to: '/events', icon: Calendar, label: 'Events' },
        { to: '/registrations', icon: BookOpen, label: 'My Registrations', show: !isOrganizer },
        { to: '/certificates', icon: Award, label: 'Certificates', show: !isOrganizer },
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
                        ? 'bg-blue-600 text-white'
                        : 'text-slate-400 hover:bg-slate-800 hover:text-white',
                    isCollapsed ? "justify-center" : ""
                )
            }
        >
            <item.icon size={20} className="shrink-0" />
            {!isCollapsed && <span className="truncate">{item.label}</span>}

            {/* Tooltip for collapsed state */}
            {isCollapsed && (
                <div className="absolute left-full ml-2 px-2 py-1 bg-slate-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 pointer-events-none">
                    {item.label}
                </div>
            )}
        </NavLink>
    );

    return (
        <div
            className={cn(
                "h-screen bg-slate-900 text-white flex flex-col transition-all duration-300 ease-in-out border-r border-slate-800 relative",
                isCollapsed ? "w-20" : "w-64"
            )}
        >
            {/* Header */}
            <div className={cn("p-6 border-b border-slate-800 flex items-center", isCollapsed ? "justify-center p-4" : "justify-between")}>
                {!isCollapsed && (
                    <div className="overflow-hidden">
                        <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-teal-400 text-transparent bg-clip-text whitespace-nowrap">
                            CPD Events
                        </h1>
                        <p className="text-xs text-slate-400 mt-1 truncate">{isOrganizer ? 'Organizer Portal' : 'Attendee Portal'}</p>
                    </div>
                )}
                {isCollapsed && <span className="font-bold text-blue-500 text-xl">CPD</span>}
            </div>

            {/* Toggle Button - Absolute positioned overlapping the border */}
            <button
                onClick={toggleSidebar}
                className="absolute -right-3 top-10 bg-slate-800 border border-slate-700 text-slate-400 hover:text-white rounded-full p-1 shadow-md hover:bg-slate-700 transition-colors z-50"
            >
                {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>

            {/* Navigation */}
            <nav className="flex-1 p-3 space-y-2 overflow-y-auto overflow-x-hidden scrollbar-thin scrollbar-thumb-slate-700">
                {navItems.filter(item => item.show !== false).map((item) => (
                    <NavItem key={item.to} item={item} />
                ))}
            </nav>

            {/* Footer Actions */}
            <div className="p-3 border-t border-slate-800">
                <button
                    onClick={logout}
                    className={cn(
                        "flex items-center space-x-3 px-3 py-3 w-full text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors group relative",
                        isCollapsed ? "justify-center" : ""
                    )}
                >
                    <LogOut size={20} className="shrink-0" />
                    {!isCollapsed && <span>Sign Out</span>}
                    {isCollapsed && (
                        <div className="absolute left-full ml-2 px-2 py-1 bg-slate-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 pointer-events-none">
                            Sign Out
                        </div>
                    )}
                </button>
            </div>
        </div>
    );
};
