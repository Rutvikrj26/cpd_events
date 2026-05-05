import { ReactNode } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';

interface DashboardLayoutProps {
  children?: ReactNode;
}

export const DashboardLayout = ({ children }: DashboardLayoutProps) => {
  return (
    <div className="flex h-screen bg-muted/30 overflow-hidden">
      <Sidebar />
      {/* `relative` is intentional: forms inside (e.g. CreateCoursePage)
          render react-hook-form's Switch with an absolutely-positioned
          input. Without a positioned ancestor, the input's containing
          block resolves to <html>, which pushes document scrollHeight
          past the viewport and lets the user scroll the whole page —
          even when <main>'s own overflow-y-auto already paginates the
          content. Anchoring abs-positioned descendants here keeps all
          scroll inside this main element. */}
      <main className="relative flex-1 overflow-y-auto">
        <div className="p-4 md:p-6 lg:p-8 min-h-full">
          {children || <Outlet />}
        </div>
      </main>
    </div>
  );
};
