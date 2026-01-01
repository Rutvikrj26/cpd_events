import { ReactNode, useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TrialStatusBanner } from '@/components/billing/TrialStatusBanner';
import { useAuth } from '@/contexts/AuthContext';
import { getSubscription } from '@/api/billing';
import { Subscription } from '@/api/billing/types';

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

  const isOrganizer = user?.account_type === 'organizer';

  useEffect(() => {
    if (isOrganizer) {
      getSubscription()
        .then(setSubscription)
        .catch((error) => {
          setSubscription(null);
          // Silent fail is acceptable - banner just won't show
          // User can still access billing page directly if needed
          if (process.env.NODE_ENV === "development") {
            console.warn("Failed to fetch subscription:", error);
          }
        });
    }
  }, [isOrganizer]);

  return (
    <div className="flex h-screen bg-muted/30 overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="p-4 md:p-6 lg:p-8 min-h-full">
          {/* Global trial/subscription banner for organizers */}
          {isOrganizer && subscription && (
            <div className="mb-6">
              <TrialStatusBanner subscription={subscription} />
            </div>
          )}
          {children || <Outlet />}
        </div>
      </main>
    </div>
  );
};
