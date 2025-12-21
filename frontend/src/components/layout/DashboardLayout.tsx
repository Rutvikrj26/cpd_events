import { ReactNode } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';

interface DashboardLayoutProps {
  children?: ReactNode;
  /**
   * Role hint for layout customization (future use).
   * Currently unused - Sidebar reads account_type from AuthContext.
   * Keep for potential future role-based layout features.
   */
  role?: 'attendee' | 'organizer' | 'admin';
}

export const DashboardLayout = ({ children, role }: DashboardLayoutProps) => {
  return (
    <div className="flex bg-muted/30 min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8 overflow-auto">
        {children || <Outlet />}
      </main>
    </div>
  );
};
