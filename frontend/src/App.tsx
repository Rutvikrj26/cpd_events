import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from "@/components/ui/toaster";
import { AuthProvider } from "@/contexts/AuthContext";
import { OrganizationProvider } from "@/contexts/OrganizationContext";
import { ProtectedRoute } from "@/features/auth";


// Layouts
import { PublicLayout } from './components/layout/PublicLayout';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { AuthLayout } from './components/layout/AuthLayout';
import ScrollToTop from './components/layout/ScrollToTop';

// Public Pages
import { LandingPage } from './pages/public/LandingPage';
import { EventDiscovery } from './pages/public/EventDiscovery';
import { EventDetail } from './pages/public/EventDetail';
import { EventRegistration } from './pages/public/EventRegistration';
import { PricingPage } from './pages/public/PricingPage';
import { ContactPage } from './pages/public/ContactPage';
import { NotFoundPage } from './pages/public/NotFoundPage';
import { PublicCourseDetailPage } from './pages/courses/PublicCourseDetailPage';

// Auth Pages
import { LoginPage } from './pages/auth/LoginPage';
import { SignupPage } from './pages/auth/SignupPage';
import { ForgotPasswordPage } from './pages/auth/ForgotPasswordPage';
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { EventsPage } from './pages/events/EventsPage';
import { EventCreatePage } from './pages/events/EventCreatePage';
import { EventDetailPage } from './pages/events/EventDetailPage';
import { MyRegistrationsPage } from './pages/registrations/MyRegistrationsPage';
import { CertificatesPage } from './pages/certificates/CertificatesPage';
import { CertificateVerify } from './pages/certificates/CertificateVerify';
import { BillingPage } from './pages/billing/BillingPage';
import { ProfilePage } from './pages/profile/ProfilePage';

// Shared Dashboard Pages
import { Notifications } from './pages/dashboard/Notifications';
import { ProfileSettings } from './pages/dashboard/ProfileSettings';

// Dashboard Pages - Attendee
import { AttendeeDashboard } from './pages/dashboard/attendee/AttendeeDashboard';
import { MyEvents } from './pages/dashboard/attendee/MyEvents';
import { CertificateDetail } from './pages/dashboard/attendee/CertificateDetail';
import { CertificatesList } from './pages/dashboard/attendee/CertificatesList';
import { CPDTracking } from './pages/dashboard/attendee/CPDTracking';
import { MyCoursesPage } from './pages/courses/MyCoursesPage';

// Dashboard Pages - Organizer (non-duplicate pages only)
import { OrganizerDashboard } from './pages/dashboard/organizer/OrganizerDashboard';
import { ContactsPage } from './pages/dashboard/organizer/ContactsPage';
import { ReportsPage } from './pages/dashboard/organizer/ReportsPage';
import { EventManagement } from './pages/dashboard/organizer/EventManagement';
import { CertificateTemplatesPage } from './pages/dashboard/organizer/CertificateTemplatesPage';
import { ZoomManagement } from './pages/dashboard/organizer/ZoomManagement';
import { OrganizerCertificatesPage } from './pages/dashboard/organizer/OrganizerCertificatesPage';

// Organization Pages
import { OrganizationsListPage, CreateOrganizationPage, OrganizationDashboard, TeamManagementPage, OrganizationSettingsPage, OrgCoursesPage, CreateCoursePage } from './pages/organizations';
import { CourseManagementPage } from './pages/organizations/courses/CourseManagementPage';

// Integrations
import { ZoomCallbackPage } from './pages/integrations/ZoomCallbackPage';

import { ThemeProvider } from "@/components/theme-provider";

export default function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
      <BrowserRouter>
        <ScrollToTop />
        <AuthProvider>
          <OrganizationProvider>
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={
                <PublicLayout>
                  <LandingPage />
                </PublicLayout>
              } />

              <Route path="/events/browse" element={
                <PublicLayout>
                  <EventDiscovery />
                </PublicLayout>
              } />

              <Route path="/events/:id" element={
                <PublicLayout>
                  <EventDetail />
                </PublicLayout>
              } />

              <Route path="/events/:id/register" element={
                <PublicLayout>
                  <EventRegistration />
                </PublicLayout>
              } />

              <Route path="/pricing" element={
                <PublicLayout>
                  <PricingPage />
                </PublicLayout>
              } />

              <Route path="/contact" element={
                <PublicLayout>
                  <ContactPage />
                </PublicLayout>
              } />

              {/* Public Certificate Verification */}
              <Route path="/verify/:code" element={<CertificateVerify />} />

              {/* Public Courses */}
              <Route path="/courses/:slug" element={
                <PublicLayout>
                  <PublicCourseDetailPage />
                </PublicLayout>
              } />

              <Route path="/forgot-password" element={
                <AuthLayout>
                  <ForgotPasswordPage />
                </AuthLayout>
              } />

              {/* Auth Routes */}
              <Route path="/login" element={
                <AuthLayout>
                  <LoginPage />
                </AuthLayout>
              } />

              <Route path="/signup" element={
                <AuthLayout>
                  <SignupPage />
                </AuthLayout>
              } />

              {/* Protected Routes - Unified Dashboard */}
              <Route element={<ProtectedRoute />}>

                {/* Integrations */}
                <Route path="/zoom/callback" element={<ZoomCallbackPage />} />

                {/* Main Dashboard Layout - all authenticated users */}
                <Route element={<DashboardLayout />}>
                  {/* Dashboard - shows role-appropriate content */}
                  <Route path="/dashboard" element={<DashboardPage />} />

                  {/* Events - unified routes for both roles */}
                  <Route path="/events" element={<EventsPage />} />
                  <Route path="/events/create" element={<EventCreatePage />} />
                  <Route path="/events/:uuid" element={<EventDetailPage />} />
                  <Route path="/events/:uuid/edit" element={<EventCreatePage />} />

                  {/* Attendee-specific pages */}
                  <Route path="/registrations" element={<MyRegistrationsPage />} />
                  <Route path="/certificates" element={<CertificatesPage />} />
                  <Route path="/my-events" element={<MyEvents />} />
                  <Route path="/my-courses" element={<MyCoursesPage />} />
                  <Route path="/my-certificates" element={<CertificatesList />} />
                  <Route path="/my-certificates/:id" element={<CertificateDetail />} />
                  <Route path="/cpd" element={<CPDTracking />} />

                  {/* Shared pages */}
                  <Route path="/billing" element={<BillingPage />} />
                  <Route path="/profile" element={<ProfilePage />} />
                  <Route path="/notifications" element={<Notifications />} />
                  <Route path="/settings" element={<ProfileSettings />} />

                  {/* Organizer-specific pages (non-event) */}
                  <Route path="/organizer/dashboard" element={<OrganizerDashboard />} />
                  <Route path="/organizer/contacts" element={<ContactsPage />} />
                  <Route path="/organizer/reports" element={<ReportsPage />} />
                  <Route path="/organizer/certificates/templates" element={<CertificateTemplatesPage />} />
                  <Route path="/organizer/certificates" element={<OrganizerCertificatesPage />} />
                  <Route path="/organizer/events/:uuid/manage" element={<EventManagement />} />
                  <Route path="/organizer/zoom" element={<ZoomManagement />} />

                  {/* Organization Routes */}
                  <Route path="/organizations" element={<OrganizationsListPage />} />
                  <Route path="/organizations/new" element={<CreateOrganizationPage />} />
                  <Route path="/org/:slug" element={<OrganizationDashboard />} />
                  <Route path="/org/:slug/team" element={<TeamManagementPage />} />
                  <Route path="/org/:slug/settings" element={<OrganizationSettingsPage />} />
                  <Route path="/org/:slug/courses" element={<OrgCoursesPage />} />
                  <Route path="/org/:slug/courses/new" element={<CreateCoursePage />} />
                  <Route path="/org/:slug/courses/:courseSlug" element={<CourseManagementPage />} />
                </Route>

                {/* Redirects for old organizer event routes */}
                <Route path="/organizer/events" element={<Navigate to="/events" replace />} />
                <Route path="/organizer/events/new" element={<Navigate to="/events/create" replace />} />
                <Route path="/organizer/events/:id" element={<Navigate to="/events/:id" replace />} />
                <Route path="/organizer/events/:id/edit" element={<Navigate to="/events/:id/edit" replace />} />
                <Route path="/organizer/settings" element={<Navigate to="/settings" replace />} />
                <Route path="/organizer/notifications" element={<Navigate to="/notifications" replace />} />

              </Route>

              {/* Fallback */}
              <Route path="*" element={
                <PublicLayout>
                  <NotFoundPage />
                </PublicLayout>
              } />
            </Routes>
          </OrganizationProvider>
        </AuthProvider>
        <Toaster />
      </BrowserRouter>
    </ThemeProvider>
  );
}

