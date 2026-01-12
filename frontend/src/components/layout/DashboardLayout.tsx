import { ReactNode, useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TrialStatusBanner } from '@/components/billing/TrialStatusBanner';
import { useAuth } from '@/contexts/AuthContext';
import { getSubscription } from '@/api/billing';
import { Subscription } from '@/api/billing/types';
import { getRoleFlags } from '@/lib/role-utils';

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
  const { user } = useAuth();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const isDev = import.meta.env.DEV;

  const { isOrganizer, isCourseManager } = getRoleFlags(user, subscription);
  const isCreator = isOrganizer || isCourseManager;

  useEffect(() => {
    if (!user) return;
    getSubscription()
      .then(setSubscription)
      .catch((error) => {
        setSubscription(null);
        // Silent fail is acceptable - banner just won't show
        // User can still access billing page directly if needed
        if (isDev) {
          console.warn("Failed to fetch subscription:", error);
        }
      });
  }, [user]);

  return (
    <div className="flex h-screen bg-muted/30 overflow-hidden">
      <Sidebar subscription={subscription} />
      <main className="flex-1 overflow-y-auto">
        <div className="p-4 md:p-6 lg:p-8 min-h-full">
          {/* Global trial/subscription banner for organizers */}
          {isCreator && subscription && (
            <div className="mb-6">
              <TrialStatusBanner subscription={subscription} />
            </div>
          )}
          {children || <Outlet context={{ subscription }} />}
        </div>
      </main>
    </div>
  );
};
