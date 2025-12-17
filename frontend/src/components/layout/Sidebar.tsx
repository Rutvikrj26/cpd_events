import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import {
    LayoutDashboard,
    Calendar,
    BookOpen,
    Award,
    CreditCard,
    LogOut,
    UserCircle
} from 'lucide-react';

export const Sidebar = () => {
    const { user, logout } = useAuth();
    const isOrganizer = user?.account_type === 'organizer' || user?.account_type === 'admin';

    const navItems = [
        { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
        { to: '/events', icon: Calendar, label: 'Events' },
        { to: '/registrations', icon: BookOpen, label: 'My Registrations', show: !isOrganizer },
        { to: '/certificates', icon: Award, label: 'Certificates', show: !isOrganizer },
        { to: '/billing', icon: CreditCard, label: 'Billing' },
        { to: '/profile', icon: UserCircle, label: 'Profile' },
    ];

    return (
        <div className="h-screen w-64 bg-slate-900 text-white flex flex-col">
            <div className="p-6 border-b border-slate-800">
                <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-teal-400 text-transparent bg-clip-text">
                    CPD Events
                </h1>
                <p className="text-xs text-slate-400 mt-1">{isOrganizer ? 'Organizer Portal' : 'Attendee Portal'}</p>
            </div>

            <nav className="flex-1 p-4 space-y-2">
                {navItems.filter(item => item.show !== false).map((item) => (
                    <NavLink
                        key={item.to}
                        to={item.to}
                        className={({ isActive }) =>
                            `flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${isActive
                                ? 'bg-blue-600 text-white'
                                : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                            }`
                        }
                    >
                        <item.icon size={20} />
                        <span>{item.label}</span>
                    </NavLink>
                ))}
            </nav>

            <div className="p-4 border-t border-slate-800">
                <button
                    onClick={logout}
                    className="flex items-center space-x-3 px-4 py-3 w-full text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                >
                    <LogOut size={20} />
                    <span>Sign Out</span>
                </button>
            </div>
        </div>
    );
};
