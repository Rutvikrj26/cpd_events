import { ReactNode } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';

interface DashboardLayoutProps {
  children?: ReactNode;
  role?: 'attendee' | 'organizer' | 'admin';
}

export const DashboardLayout = ({ children, role }: DashboardLayoutProps) => {
  return (
    <div className="flex bg-slate-50 min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8 overflow-auto">
        {children || <Outlet />}
      </main>
    </div>
  );
};
