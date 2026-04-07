import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from "@/components/ui/toaster";
import { Toaster as SonnerToaster } from "sonner";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/features/auth";
import { AuthenticatedRoot } from "@/components/auth/AuthenticatedRoot";


// Layouts
import { PublicLayout } from './components/layout/PublicLayout';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { AuthLayout } from './components/layout/AuthLayout';
import ScrollToTop from './components/layout/ScrollToTop';

// Public Pages (kept)
import { EventDiscovery } from './pages/public/EventDiscovery';
import { CourseDiscoveryPage } from './pages/public/CourseDiscoveryPage';
import { EventDetail } from './pages/public/EventDetail';
import { EventRegistration } from './pages/public/EventRegistration';
import { NotFoundPage } from './pages/public/NotFoundPage';
import { PublicCourseDetailPage } from './pages/courses/PublicCourseDetailPage';
import { TermsPage } from './pages/public/TermsPage';
import { PrivacyPage } from './pages/public/PrivacyPage';
import { CookiePolicyPage } from './pages/public/CookiePolicyPage';

// Auth Pages
import { LoginPage } from "@/pages/auth/LoginPage";
import { SignupPage } from "@/pages/auth/SignupPage";
import { VerifyEmailPage } from "@/pages/auth/VerifyEmailPage";
import { CheckEmailPage } from "@/pages/auth/CheckEmailPage";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "@/pages/auth/ResetPasswordPage";
import { OAuthCallbackPage } from "@/pages/auth/OAuthCallbackPage";
import { AcceptInvitationPage } from "@/pages/auth/AcceptInvitationPage";

// Dashboard Pages
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { EventsPage } from './pages/events/EventsPage';
import { EventCreatePage } from './pages/events/EventCreatePage';
import { EventDetailPage } from './pages/events/EventDetailPage';
import { MyRegistrationsPage } from './pages/registrations/MyRegistrationsPage';
import { CertificatesPage } from './pages/certificates/CertificatesPage';
import { CertificateVerify } from './pages/certificates/CertificateVerify';
import { CourseCertificatesPage } from './pages/certificates/CourseCertificatesPage';

// Shared Dashboard Pages
import { Notifications } from './pages/dashboard/Notifications';
import { ProfileSettings } from './pages/dashboard/ProfileSettings';

// Learner Pages
import { MyEvents } from './pages/dashboard/attendee/MyEvents';
import { CPDTracking } from './pages/dashboard/attendee/CPDTracking';
import { MyCoursesPage } from './pages/courses/MyCoursesPage';
import { CoursePlayerPage } from './pages/courses/CoursePlayerPage';

// Educator Pages
import { ContactsPage } from './pages/dashboard/organizer/ContactsPage';
import { ReportsPage } from './pages/dashboard/organizer/ReportsPage';
import { EventManagement } from './pages/dashboard/organizer/EventManagement';
import { OrganizerCertificatesPage } from './pages/dashboard/organizer/OrganizerCertificatesPage';
import { OrganizerBadgesPage } from './pages/dashboard/organizer/OrganizerBadgesPage';
import VideoManagement from './pages/dashboard/organizer/VideoManagement';
import { PublicBadgePage } from './pages/badges/PublicBadgePage';
import { MyBadgesPage } from './pages/badges/MyBadgesPage';

// Course Pages
import { CourseCatalogPage } from './pages/courses';
import OrgCoursesPage from './pages/organizations/courses/OrgCoursesPage';
import CreateCoursePage from './pages/organizations/courses/CreateCoursePage';
import { CourseManagementPage } from './pages/organizations/courses/CourseManagementPage';

// Admin Pages
import { UserManagementPage } from './pages/admin/UserManagementPage';

// Onboarding
import { OnboardingWizard } from './pages/onboarding';

import { ThemeProvider } from "@/components/theme-provider";
import { InstallPrompt } from "@/components/pwa/InstallPrompt";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
        <BrowserRouter>
          <ScrollToTop />
          <AuthProvider>
            <Routes>
              {/* Root: redirect to dashboard if authenticated, login if not */}
              <Route path="/" element={<AuthenticatedRoot />} />

              {/* Public event/course pages */}
              <Route path="/events/browse" element={
                <PublicLayout>
                  <EventDiscovery />
                </PublicLayout>
              } />

              <Route path="/courses/browse" element={
                <PublicLayout>
                  <CourseDiscoveryPage />
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

              <Route path="/courses/:slug" element={
                <PublicLayout>
                  <PublicCourseDetailPage />
                </PublicLayout>
              } />

              {/* Legal pages */}
              <Route path="/terms" element={
                <PublicLayout>
                  <TermsPage />
                </PublicLayout>
              } />

              <Route path="/privacy" element={
                <PublicLayout>
                  <PrivacyPage />
                </PublicLayout>
              } />

              <Route path="/cookies" element={
                <PublicLayout>
                  <CookiePolicyPage />
                </PublicLayout>
              } />

              {/* Public verification pages */}
              <Route path="/verify" element={<CertificateVerify />} />
              <Route path="/verify/:code" element={<CertificateVerify />} />
              <Route path="/badges/verify/:code" element={<PublicBadgePage />} />

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

              <Route path="/auth/verify-email" element={<VerifyEmailPage />} />
              <Route path="/auth/check-email" element={<CheckEmailPage />} />
              <Route path="/auth/accept-invitation" element={<AcceptInvitationPage />} />

              <Route path="/forgot-password" element={
                <AuthLayout>
                  <ForgotPasswordPage />
                </AuthLayout>
              } />

              <Route path="/auth/reset-password" element={
                <AuthLayout>
                  <ResetPasswordPage />
                </AuthLayout>
              } />

              <Route path="/auth/callback" element={<OAuthCallbackPage />} />

              {/* Protected Routes - Dashboard */}
              <Route element={<ProtectedRoute />}>

                {/* Onboarding */}
                <Route path="/onboarding" element={<OnboardingWizard />} />

                {/* Dashboard Layout */}
                <Route element={<DashboardLayout />}>
                  <Route path="/dashboard" element={<DashboardPage />} />

                  {/* Events */}
                  <Route path="/events" element={<EventsPage />} />
                  <Route path="/events/create" element={
                    <ProtectedRoute requiredFeature="create_events">
                      <EventCreatePage />
                    </ProtectedRoute>
                  } />
                  <Route path="/events/:uuid" element={<EventDetailPage />} />
                  <Route path="/events/:uuid/edit" element={
                    <ProtectedRoute requiredFeature="create_events">
                      <EventCreatePage />
                    </ProtectedRoute>
                  } />

                  {/* Learner pages */}
                  <Route path="/registrations" element={<MyRegistrationsPage />} />
                  <Route path="/certificates" element={<CertificatesPage />} />
                  <Route path="/my-events" element={<MyEvents />} />
                  <Route path="/courses" element={<CourseCatalogPage />} />
                  <Route path="/my-courses" element={<MyCoursesPage />} />
                  <Route path="/courses/certificates" element={<CourseCertificatesPage />} />
                  <Route path="/learn/:courseUuid" element={<CoursePlayerPage />} />
                  <Route path="/badges" element={<MyBadgesPage />} />
                  <Route path="/cpd" element={<CPDTracking />} />

                  {/* Course management */}
                  <Route path="/courses/manage" element={<OrgCoursesPage />} />
                  <Route path="/courses/manage/new" element={
                    <ProtectedRoute requiredFeature="create_courses">
                      <CreateCoursePage />
                    </ProtectedRoute>
                  } />
                  <Route path="/courses/manage/:courseSlug" element={<CourseManagementPage />} />

                  {/* Educator pages */}
                  <Route path="/organizer/contacts" element={<ContactsPage />} />
                  <Route path="/organizer/reports" element={<ReportsPage />} />
                  <Route path="/organizer/certificates" element={<OrganizerCertificatesPage />} />
                  <Route path="/organizer/events/:uuid/manage" element={<EventManagement />} />
                  <Route path="/organizer/badges" element={<OrganizerBadgesPage />} />
                  <Route path="/organizer/video" element={<VideoManagement />} />

                  {/* Admin pages */}
                  <Route path="/admin/users" element={
                    <ProtectedRoute requiredFeature="manage_users">
                      <UserManagementPage />
                    </ProtectedRoute>
                  } />

                  {/* Shared pages */}
                  <Route path="/notifications" element={<Notifications />} />
                  <Route path="/settings" element={<ProfileSettings />} />
                </Route>

                {/* Redirects for old routes */}
                <Route path="/organizer/events" element={<Navigate to="/events" replace />} />
                <Route path="/organizer/events/new" element={<Navigate to="/events/create" replace />} />
                <Route path="/organizer/settings" element={<Navigate to="/settings" replace />} />
                <Route path="/organizer/notifications" element={<Navigate to="/notifications" replace />} />
                <Route path="/profile" element={<Navigate to="/settings" replace />} />
                <Route path="/my-certificates" element={<Navigate to="/certificates" replace />} />
                <Route path="/billing" element={<Navigate to="/dashboard" replace />} />

              </Route>

              {/* Fallback */}
              <Route path="*" element={
                <PublicLayout>
                  <NotFoundPage />
                </PublicLayout>
              } />
            </Routes>
          </AuthProvider>
          <Toaster />
          <SonnerToaster position="top-right" richColors closeButton />
          <InstallPrompt />
        </BrowserRouter>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
