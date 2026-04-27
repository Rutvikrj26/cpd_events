import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster as SonnerToaster } from "sonner";
import { ProtectedRoute, BrandTheme } from "@/features/auth";
import { AuthenticatedRoot } from "@/components/auth/AuthenticatedRoot";
import { lazyNamed } from "@/shared/lib";
import { Loader2 } from "lucide-react";

/** Generic suspense fallback while a route chunk loads. */
function RouteFallback() {
    return (
        <div className="flex h-screen w-full items-center justify-center" role="status" aria-label="Loading">
            <Loader2 className="h-8 w-8 animate-spin text-primary" strokeWidth={1.75} />
        </div>
    );
}

// Layouts (eagerly imported — needed on initial render)
import { DashboardLayout } from './components/layout/DashboardLayout';
import { AuthLayout } from './components/layout/AuthLayout';
import { PublicLayout } from './components/layout/PublicLayout';
import ScrollToTop from './components/layout/ScrollToTop';

import { ThemeBootstrap } from "@/app/providers/ThemeBootstrap";
import { DialogHost } from "@/app/providers/DialogHost";
import { InstallPrompt } from "@/components/pwa/InstallPrompt";
import { ErrorBoundary } from "@/components/ErrorBoundary";

/* ------------------------------------------------------------------ */
/* Lazy-loaded pages (P2 — every route imports its chunk on demand).  */
/* Auth + 404 stay eager because they're tiny and on the cold-load   */
/* path. Everything else splits into its own chunk.                  */
/* ------------------------------------------------------------------ */

// Auth (eager — fast cold-start)
import { LoginPage } from "@/pages/auth/LoginPage";
import { SignupPage } from "@/pages/auth/SignupPage";
import { VerifyEmailPage } from "@/pages/auth/VerifyEmailPage";
import { CheckEmailPage } from "@/pages/auth/CheckEmailPage";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "@/pages/auth/ResetPasswordPage";
import { AcceptInvitationPage } from "@/pages/auth/AcceptInvitationPage";
import { ConfirmEmailChangePage } from "@/pages/auth/ConfirmEmailChangePage";
import { NotFoundPage } from './pages/NotFoundPage';

// Legal (lazy)
const TermsPage = lazyNamed(() => import('./pages/public/TermsPage'), 'TermsPage');
const PrivacyPage = lazyNamed(() => import('./pages/public/PrivacyPage'), 'PrivacyPage');
const CookiePolicyPage = lazyNamed(() => import('./pages/public/CookiePolicyPage'), 'CookiePolicyPage');

// Public / Discovery (lazy)
const EventDetail = lazyNamed(() => import('./pages/public/EventDetail'), 'EventDetail');
const EventDiscovery = lazyNamed(() => import('./pages/public/EventDiscovery'), 'EventDiscovery');
const EventRegistration = lazyNamed(() => import('./pages/public/EventRegistration'), 'EventRegistration');
const EventLobbyPage = lazyNamed(() => import('./pages/events/EventLobbyPage'), 'EventLobbyPage');
const EventRecordingPage = lazyNamed(() => import('./pages/events/EventRecordingPage'), 'EventRecordingPage');
const CourseSessionLobbyPage = lazyNamed(() => import('./pages/courses/CourseSessionLobbyPage'), 'CourseSessionLobbyPage');
const CourseSessionRecordingPage = lazyNamed(() => import('./pages/courses/CourseSessionRecordingPage'), 'CourseSessionRecordingPage');
const CheckoutCancel = lazyNamed(() => import('./pages/public/CheckoutReturn'), 'CheckoutCancel');
const CheckoutSuccess = lazyNamed(() => import('./pages/public/CheckoutReturn'), 'CheckoutSuccess');
const PublicCourseDetailPage = lazyNamed(() => import('./pages/courses/PublicCourseDetailPage'), 'PublicCourseDetailPage');
const ProgramDiscoveryPage = lazyNamed(() => import('./pages/public/ProgramDiscoveryPage'), 'ProgramDiscoveryPage');
const PublicProgramDetailPage = lazyNamed(() => import('./pages/programs/PublicProgramDetailPage'), 'PublicProgramDetailPage');
const PublicBadgePage = lazyNamed(() => import('./pages/badges/PublicBadgePage'), 'PublicBadgePage');
const CertificateVerify = lazyNamed(() => import('./pages/certificates/CertificateVerify'), 'CertificateVerify');

// Dashboard / Learner (lazy — heavy)
const DashboardPage = lazyNamed(() => import('./pages/dashboard/DashboardPage'), 'DashboardPage');
const EventsPage = lazyNamed(() => import('./pages/events/EventsPage'), 'EventsPage');
const EventCreatePage = lazyNamed(() => import('./pages/events/EventCreatePage'), 'EventCreatePage');
const EventDetailPage = lazyNamed(() => import('./pages/events/EventDetailPage'), 'EventDetailPage');
const MyLearningPage = lazyNamed(() => import('./pages/registrations/MyRegistrationsPage'), 'MyLearningPage');
const CertificatesPage = lazyNamed(() => import('./pages/certificates/CertificatesPage'), 'CertificatesPage');
const Notifications = lazyNamed(() => import('./pages/dashboard/Notifications'), 'Notifications');
const ProfileSettings = lazyNamed(() => import('./pages/dashboard/ProfileSettings'), 'ProfileSettings');
const MyEvents = lazyNamed(() => import('./pages/dashboard/attendee/MyEvents'), 'MyEvents');
const CPDTracking = lazyNamed(() => import('./pages/dashboard/attendee/CPDTracking'), 'CPDTracking');
const CoursePlayerPage = lazyNamed(() => import('./pages/courses/CoursePlayerPage'), 'CoursePlayerPage');
const MyBadgesPage = lazyNamed(() => import('./pages/badges/MyBadgesPage'), 'MyBadgesPage');
const MyAccreditationsPage = lazyNamed(() => import('./pages/accreditations/MyAccreditationsPage'), 'MyAccreditationsPage');
const MyProgramsPage = lazyNamed(() => import('./pages/programs/MyProgramsPage'), 'MyProgramsPage');

// Organizer (lazy — heavy)
const ContactsPage = lazyNamed(() => import('./pages/dashboard/organizer/ContactsPage'), 'ContactsPage');
const ReportsPage = lazyNamed(() => import('./pages/dashboard/organizer/ReportsPage'), 'ReportsPage');
const EventManagement = lazyNamed(() => import('./pages/dashboard/organizer/EventManagement'), 'EventManagement');
const OrganizerAccreditationsPage = lazyNamed(() => import('./pages/dashboard/organizer/OrganizerAccreditationsPage'), 'OrganizerAccreditationsPage');
const PromoCodesPage = lazy(() => import('./pages/dashboard/organizer/PromoCodesPage'));
const SpeakersPage = lazy(() => import('./pages/dashboard/organizer/SpeakersPage'));

// Course management (lazy — heavy)
const CourseCatalogPage = lazyNamed(() => import('./pages/courses'), 'CourseCatalogPage');
const OrgCoursesPage = lazy(() => import('./pages/organizations/courses/OrgCoursesPage'));
const CreateCoursePage = lazy(() => import('./pages/organizations/courses/CreateCoursePage'));
const CourseManagementPage = lazyNamed(() => import('./pages/organizations/courses/CourseManagementPage'), 'CourseManagementPage');
const OrgProgramsPage = lazy(() => import('./pages/organizations/programs/OrgProgramsPage'));
const CreateProgramPage = lazy(() => import('./pages/organizations/programs/CreateProgramPage'));
const ProgramManagementPage = lazy(() => import('./pages/organizations/programs/ProgramManagementPage'));

// Admin (lazy)
const UserManagementPage = lazyNamed(() => import('./pages/admin/UserManagementPage'), 'UserManagementPage');
const AdminUserDetailPage = lazyNamed(() => import('./pages/admin/AdminUserDetailPage'), 'AdminUserDetailPage');
const BillingAdminPage = lazyNamed(() => import('./pages/admin/BillingAdminPage'), 'BillingAdminPage');

// Onboarding (lazy)
const OnboardingWizard = lazyNamed(() => import('./pages/onboarding'), 'OnboardingWizard');

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeBootstrap />
      <BrowserRouter>
          <ScrollToTop />
          <BrandTheme />
            <Suspense fallback={<RouteFallback />}>
            <Routes>
              {/* Root: redirect to dashboard if authenticated, login if not */}
              <Route path="/" element={<AuthenticatedRoot />} />

              {/* Legal pages — wrapped in PublicLayout (not AuthLayout) so
                  the prose column gets a real reading width instead of the
                  ~448px sign-in card box. (QA F-35) */}
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
                    <ProtectedRoute requiredFeature="configure_billing">
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
            </Suspense>
          <SonnerToaster position="top-right" richColors closeButton duration={5000} />
          <InstallPrompt />
          <DialogHost />
        </BrowserRouter>
    </ErrorBoundary>
  );
}
