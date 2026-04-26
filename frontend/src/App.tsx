import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from "@/components/ui/toaster";
import { Toaster as SonnerToaster } from "sonner";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/features/auth";
import { AuthenticatedRoot } from "@/components/auth/AuthenticatedRoot";


// Layouts
import { DashboardLayout } from './components/layout/DashboardLayout';
import { AuthLayout } from './components/layout/AuthLayout';
import ScrollToTop from './components/layout/ScrollToTop';

// Legal Pages
import { NotFoundPage } from './pages/NotFoundPage';
import { TermsPage } from './pages/public/TermsPage';
import { PrivacyPage } from './pages/public/PrivacyPage';
import { CookiePolicyPage } from './pages/public/CookiePolicyPage';
import { PublicLayout } from './components/layout/PublicLayout';

// Learner browsing (reused from public pages, now behind auth)
import { EventDetail } from './pages/public/EventDetail';
import { EventDiscovery } from './pages/public/EventDiscovery';
import { EventRegistration } from './pages/public/EventRegistration';
import { EventLobbyPage } from './pages/events/EventLobbyPage';
import { EventRecordingPage } from './pages/events/EventRecordingPage';
import { CourseSessionLobbyPage } from './pages/courses/CourseSessionLobbyPage';
import { CourseSessionRecordingPage } from './pages/courses/CourseSessionRecordingPage';
import { CheckoutCancel, CheckoutSuccess } from './pages/public/CheckoutReturn';
import { PublicCourseDetailPage } from './pages/courses/PublicCourseDetailPage';
import { ProgramDiscoveryPage } from './pages/public/ProgramDiscoveryPage';
import { PublicProgramDetailPage } from './pages/programs/PublicProgramDetailPage';

// Auth Pages
import { LoginPage } from "@/pages/auth/LoginPage";
import { SignupPage } from "@/pages/auth/SignupPage";
import { VerifyEmailPage } from "@/pages/auth/VerifyEmailPage";
import { CheckEmailPage } from "@/pages/auth/CheckEmailPage";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "@/pages/auth/ResetPasswordPage";
import { AcceptInvitationPage } from "@/pages/auth/AcceptInvitationPage";
import { ConfirmEmailChangePage } from "@/pages/auth/ConfirmEmailChangePage";

// Dashboard Pages
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { EventsPage } from './pages/events/EventsPage';
import { EventCreatePage } from './pages/events/EventCreatePage';
import { EventDetailPage } from './pages/events/EventDetailPage';
import { MyLearningPage } from './pages/registrations/MyRegistrationsPage';
import { CertificatesPage } from './pages/certificates/CertificatesPage';
import { CertificateVerify } from './pages/certificates/CertificateVerify';

// Shared Dashboard Pages
import { Notifications } from './pages/dashboard/Notifications';
import { ProfileSettings } from './pages/dashboard/ProfileSettings';

// Learner Pages
import { MyEvents } from './pages/dashboard/attendee/MyEvents';
import { CPDTracking } from './pages/dashboard/attendee/CPDTracking';
import { CoursePlayerPage } from './pages/courses/CoursePlayerPage';

// Organizer Pages
import { ContactsPage } from './pages/dashboard/organizer/ContactsPage';
// TAGGING-DISABLED: restore TagLibraryPage import when re-enabling tag UI.
// import { TagLibraryPage } from './pages/dashboard/organizer/TagLibraryPage';
import { ReportsPage } from './pages/dashboard/organizer/ReportsPage';
import { EventManagement } from './pages/dashboard/organizer/EventManagement';
import { OrganizerAccreditationsPage } from './pages/dashboard/organizer/OrganizerAccreditationsPage';
import PromoCodesPage from './pages/dashboard/organizer/PromoCodesPage';
import SpeakersPage from './pages/dashboard/organizer/SpeakersPage';
import { PublicBadgePage } from './pages/badges/PublicBadgePage';
import { MyBadgesPage } from './pages/badges/MyBadgesPage';
import { MyAccreditationsPage } from './pages/accreditations/MyAccreditationsPage';
import { MyProgramsPage } from './pages/programs/MyProgramsPage';

// Course Pages
import { CourseCatalogPage } from './pages/courses';
import OrgCoursesPage from './pages/organizations/courses/OrgCoursesPage';
import CreateCoursePage from './pages/organizations/courses/CreateCoursePage';
import { CourseManagementPage } from './pages/organizations/courses/CourseManagementPage';
import OrgProgramsPage from './pages/organizations/programs/OrgProgramsPage';
import CreateProgramPage from './pages/organizations/programs/CreateProgramPage';
import ProgramManagementPage from './pages/organizations/programs/ProgramManagementPage';

// Admin Pages
import { UserManagementPage } from './pages/admin/UserManagementPage';
import { AdminUserDetailPage } from './pages/admin/AdminUserDetailPage';
import { BillingAdminPage } from './pages/admin/BillingAdminPage';

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

              {/* Legal pages */}
              <Route path="/terms" element={
                <AuthLayout>
                  <TermsPage />
                </AuthLayout>
              } />

              <Route path="/privacy" element={
                <AuthLayout>
                  <PrivacyPage />
                </AuthLayout>
              } />

              <Route path="/cookies" element={
                <AuthLayout>
                  <CookiePolicyPage />
                </AuthLayout>
              } />

              {/* Public verification pages */}
              <Route path="/verify" element={<CertificateVerify />} />
              <Route path="/verify/:code" element={<CertificateVerify />} />
              <Route path="/badges/verify/:code" element={<PublicBadgePage />} />

              {/* Public event, course & program pages */}
              <Route path="/discover/events" element={<EventDiscovery />} />
              <Route path="/discover/courses" element={<CourseCatalogPage />} />
              <Route path="/events/:id/details" element={<EventDetail />} />
              <Route path="/events/:id/register" element={<EventRegistration />} />
              {/* Guest pre-event lobby (no auth required) — landed on from
                  the join URL we embed in reminder/confirmation emails. */}
              <Route path="/r/:registrationUuid/lobby" element={<EventLobbyPage />} />
              <Route path="/courses/:slug" element={<PublicCourseDetailPage />} />
              <Route path="/programs" element={<ProgramDiscoveryPage />} />
              <Route path="/programs/:slug" element={<PublicProgramDetailPage />} />

              {/* Stripe Checkout return */}
              <Route path="/checkout/success" element={<CheckoutSuccess />} />
              <Route path="/checkout/cancel" element={<CheckoutCancel />} />

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

              <Route path="/auth/callback" element={<Navigate to="/login" replace />} />
              <Route path="/auth/confirm-email-change" element={<ConfirmEmailChangePage />} />

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
                  {/* Pre-event lobby (auth) and post-event recording playback. */}
                  <Route path="/events/:id/lobby" element={<EventLobbyPage />} />
                  <Route path="/events/:id/recording" element={<EventRecordingPage />} />
                  <Route path="/events/:id/recording/:recordingUuid" element={<EventRecordingPage />} />
                  {/* Symmetric routes for course-session lobby / recording. */}
                  <Route path="/courses/:slug/sessions/:sessionUuid/lobby" element={<CourseSessionLobbyPage />} />
                  <Route path="/courses/:slug/sessions/:sessionUuid/recording" element={<CourseSessionRecordingPage />} />
                  <Route path="/events/:uuid/edit" element={
                    <ProtectedRoute requiredFeature="create_events">
                      <EventCreatePage />
                    </ProtectedRoute>
                  } />

                  {/* Learner pages */}
                  <Route path="/registrations" element={<MyLearningPage />} />
                  <Route path="/accreditations" element={<MyAccreditationsPage />} />
                  <Route path="/my-programs" element={<MyProgramsPage />} />
                  <Route path="/certificates" element={<CertificatesPage />} />
                  <Route path="/my-events" element={<MyEvents />} />
                  <Route path="/courses" element={<CourseCatalogPage />} />
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

                  {/* Program management */}
                  <Route path="/programs/manage" element={<OrgProgramsPage />} />
                  <Route path="/programs/manage/new" element={
                    <ProtectedRoute requiredFeature="create_courses">
                      <CreateProgramPage />
                    </ProtectedRoute>
                  } />
                  <Route path="/programs/manage/:programSlug" element={<ProgramManagementPage />} />

                  {/* Organizer pages */}
                  <Route path="/organizer/contacts" element={
                    <ProtectedRoute requiredFeature="manage_contacts">
                      <ContactsPage />
                    </ProtectedRoute>
                  } />
                  {/* TAGGING-DISABLED: restore /organizer/contacts/tags route when re-enabling.
                  <Route path="/organizer/contacts/tags" element={
                    <ProtectedRoute requiredFeature="manage_contacts">
                      <TagLibraryPage />
                    </ProtectedRoute>
                  } />
                  */}
                  {/* Reports page gates its own Events/Courses/Programs tabs based on role;
                      drop the requiredFeature so instructors without create_events can load it. */}
                  <Route path="/organizer/reports" element={<ReportsPage />} />
                  <Route path="/manage/accreditations" element={<OrganizerAccreditationsPage />} />
                  <Route path="/organizer/events/:uuid/manage" element={
                    <ProtectedRoute requiredFeature="create_events">
                      <EventManagement />
                    </ProtectedRoute>
                  } />
                  <Route path="/organizer/video" element={<Navigate to="/settings" replace />} />
                  <Route path="/organizer/promo-codes" element={
                    <ProtectedRoute requiredFeature="create_events">
                      <PromoCodesPage />
                    </ProtectedRoute>
                  } />
                  <Route path="/organizer/speakers" element={
                    <ProtectedRoute requiredFeature="create_events">
                      <SpeakersPage />
                    </ProtectedRoute>
                  } />

                  {/* Admin pages */}
                  <Route path="/admin/users" element={
                    <ProtectedRoute requiredFeature="manage_users">
                      <UserManagementPage />
                    </ProtectedRoute>
                  } />
                  <Route path="/admin/users/:uuid" element={
                    <ProtectedRoute requiredFeature="manage_users">
                      <AdminUserDetailPage />
                    </ProtectedRoute>
                  } />
                  <Route path="/admin/billing" element={
                    <ProtectedRoute>
                      <BillingAdminPage />
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

              </Route>

              {/* Fallback — show a real 404 page that preserves auth state */}
              <Route path="*" element={<NotFoundPage />} />
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
