import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from "@/components/ui/toaster";
import { Toaster as SonnerToaster } from "sonner";
import { AuthProvider } from "@/contexts/AuthContext";
import { OrganizationProvider } from "@/contexts/OrganizationContext";
import { ProtectedRoute } from "@/features/auth";


// Layouts
import { PublicLayout } from './components/layout/PublicLayout';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { OrganizationLayout } from './components/layout/OrganizationLayout';
import { AuthLayout } from './components/layout/AuthLayout';
import ScrollToTop from './components/layout/ScrollToTop';

// Public Pages
import { LandingPage } from './pages/public/LandingPage';
import { EventDiscovery } from './pages/public/EventDiscovery';
import { CourseDiscoveryPage } from './pages/public/CourseDiscoveryPage';
import { EventDetail } from './pages/public/EventDetail';
import { EventRegistration } from './pages/public/EventRegistration';
import { PricingPage } from './pages/public/PricingPage';
import { ContactPage } from './pages/public/ContactPage';
import { NotFoundPage } from './pages/public/NotFoundPage';
import { OrganizationPublicProfilePage } from './pages/public/OrganizationPublicProfilePage';
import { OrganizationsDirectoryPage } from './pages/public/OrganizationsDirectoryPage';
import { PublicCourseDetailPage } from './pages/courses/PublicCourseDetailPage';
import { FeaturesPage } from './pages/public/FeaturesPage';
import { FAQPage } from './pages/public/FAQPage';
import { AboutPage } from './pages/public/AboutPage';
import { TermsPage } from './pages/public/TermsPage';
import { PrivacyPage } from './pages/public/PrivacyPage';
import { CookiePolicyPage } from './pages/public/CookiePolicyPage';

// Product Pages
import EventsProductPage from './pages/public/products/EventsProductPage';
import LMSProductPage from './pages/public/products/LMSProductPage';
import OrganizationsProductPage from './pages/public/products/OrganizationsProductPage';

// Auth Pages
import { LoginPage } from "@/pages/auth/LoginPage";
import { SignupPage } from "@/pages/auth/SignupPage";
import { VerifyEmailPage } from "@/pages/auth/VerifyEmailPage";
import { CheckEmailPage } from "@/pages/auth/CheckEmailPage";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "@/pages/auth/ResetPasswordPage";
import { OAuthCallbackPage } from "@/pages/auth/OAuthCallbackPage";
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { EventsPage } from './pages/events/EventsPage';
import { EventCreatePage } from './pages/events/EventCreatePage';
import { EventDetailPage } from './pages/events/EventDetailPage';
import { MyRegistrationsPage } from './pages/registrations/MyRegistrationsPage';
import { CertificatesPage } from './pages/certificates/CertificatesPage';
import { CertificateVerify } from './pages/certificates/CertificateVerify';
import { CourseCertificatesPage } from './pages/certificates/CourseCertificatesPage';
import { BillingPage } from './pages/billing/BillingPage';

// Shared Dashboard Pages
import { Notifications } from './pages/dashboard/Notifications';
import { ProfileSettings } from './pages/dashboard/ProfileSettings';

// Dashboard Pages - Attendee
import { AttendeeDashboard } from './pages/dashboard/attendee/AttendeeDashboard';
import { MyEvents } from './pages/dashboard/attendee/MyEvents';
import { CPDTracking } from './pages/dashboard/attendee/CPDTracking';
import { MyCoursesPage } from './pages/courses/MyCoursesPage';
import { CoursePlayerPage } from './pages/courses/CoursePlayerPage';

// Dashboard Pages - Organizer (non-duplicate pages only)
import { OrganizerDashboard } from './pages/dashboard/organizer/OrganizerDashboard';
import { ContactsPage } from './pages/dashboard/organizer/ContactsPage';
import { ReportsPage } from './pages/dashboard/organizer/ReportsPage';
import { EventManagement } from './pages/dashboard/organizer/EventManagement';
import { ZoomManagement } from './pages/dashboard/organizer/ZoomManagement';
import { OrganizerCertificatesPage } from './pages/dashboard/organizer/OrganizerCertificatesPage';
import { OrganizerBadgesPage } from './pages/dashboard/organizer/OrganizerBadgesPage';
import { PublicBadgePage } from './pages/badges/PublicBadgePage';
import { MyBadgesPage } from './pages/badges/MyBadgesPage';

// Organization Pages
import { OrganizationsListPage, CreateOrganizationPage, OrganizationDashboard, InstructorDashboard, OrgEventsPage, TeamManagementPage, OrganizationSettingsPage, OrgCoursesPage, CreateCoursePage, AcceptInvitationPage, OrganizationBillingPage, OrganizationOnboardingWizard } from './pages/organizations';
import { CourseManagementPage } from './pages/organizations/courses/CourseManagementPage';

// Course Pages
import { CourseCatalogPage } from './pages/courses';

// Integrations
import { ZoomCallbackPage } from './pages/integrations/ZoomCallbackPage';

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
            <OrganizationProvider>
              <Routes>
                {/* Public Routes */}
                <Route path="/" element={
                  <PublicLayout>
                    <LandingPage />
                  </PublicLayout>
                } />

                {/* Product Pages */}
                <Route path="/products/events" element={
                  <PublicLayout>
                    <EventsProductPage />
                  </PublicLayout>
                } />

                <Route path="/products/lms" element={
                  <PublicLayout>
                    <LMSProductPage />
                  </PublicLayout>
                } />

                <Route path="/products/organizations" element={
                  <PublicLayout>
                    <OrganizationsProductPage />
                  </PublicLayout>
                } />

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



                <Route path="/organizations/:slug/public" element={
                  <PublicLayout>
                    <OrganizationPublicProfilePage />
                  </PublicLayout>
                } />

                <Route path="/organizations/browse" element={
                  <PublicLayout>
                    <OrganizationsDirectoryPage />
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

                {/* New Feature Pages */}
                <Route path="/features" element={
                  <PublicLayout>
                    <FeaturesPage />
                  </PublicLayout>
                } />

                <Route path="/features/:feature" element={
                  <PublicLayout>
                    <FeaturesPage />
                  </PublicLayout>
                } />

                <Route path="/faq" element={
                  <PublicLayout>
                    <FAQPage />
                  </PublicLayout>
                } />

                <Route path="/about" element={
                  <PublicLayout>
                    <AboutPage />
                  </PublicLayout>
                } />

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

                {/* Public Certificate Verification */}
                <Route path="/verify" element={<CertificateVerify />} />
                <Route path="/verify/:code" element={<CertificateVerify />} />
                <Route path="/badges/verify/:code" element={<PublicBadgePage />} />

                {/* Public Courses */}
                <Route path="/courses/:slug" element={
                  <PublicLayout>
                    <PublicCourseDetailPage />
                  </PublicLayout>
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

                {/* Email Verification */}
                <Route path="/auth/verify-email" element={<VerifyEmailPage />} />
                <Route path="/auth/check-email" element={<CheckEmailPage />} />

                {/* Accept Organization Invitation - Public but requires auth */}
                <Route path="/accept-invite/:token" element={<AcceptInvitationPage />} />

                <Route path="/forgot-password" element={
                  <AuthLayout>
                    <ForgotPasswordPage />
                  </AuthLayout>
                } />

                <Route path="/reset-password" element={
                  <AuthLayout>
                    <ResetPasswordPage />
                  </AuthLayout>
                } />

                {/* OAuth Callback */}
                <Route path="/auth/callback" element={<OAuthCallbackPage />} />

                {/* Protected Routes - Unified Dashboard */}
                <Route element={<ProtectedRoute />}>

                  {/* Integrations */}
                  <Route path="/integrations/zoom/callback" element={<ZoomCallbackPage />} />

                  {/* Onboarding Wizard - Full Screen */}
                  <Route path="/onboarding" element={<OnboardingWizard />} />

                  {/* Main Dashboard Layout - all authenticated users */}
                  <Route element={<DashboardLayout />}>
                    {/* Dashboard - shows role-appropriate content */}
                    <Route path="/dashboard" element={<DashboardPage />} />

                    {/* Events - unified routes for both roles */}
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

                    {/* Attendee-specific pages */}
                    <Route path="/registrations" element={<MyRegistrationsPage />} />
                    <Route path="/certificates" element={<CertificatesPage />} />
                    <Route path="/my-events" element={<MyEvents />} />
                    <Route path="/courses" element={<CourseCatalogPage />} />
                    <Route path="/my-courses" element={<MyCoursesPage />} />
                    <Route path="/courses/certificates" element={<CourseCertificatesPage />} />
                    <Route path="/courses/manage" element={<OrgCoursesPage />} />
                    <Route path="/courses/manage/new" element={
                      <ProtectedRoute requiredFeature="create_courses">
                        <CreateCoursePage />
                      </ProtectedRoute>
                    } />
                    <Route path="/courses/manage/:courseSlug" element={<CourseManagementPage />} />
                    <Route path="/learn/:courseUuid" element={<CoursePlayerPage />} />
                    <Route path="/my-certificates" element={<Navigate to="/certificates" replace />} />
                    <Route path="/my-certificates/:id" element={<Navigate to="/certificates" replace />} />
                    <Route path="/badges" element={<MyBadgesPage />} />
                    <Route path="/cpd" element={<CPDTracking />} />

                    {/* Shared pages */}
                    <Route path="login" element={<LoginPage />} />
                    <Route path="signup" element={<SignupPage />} />
                    <Route path="forgot-password" element={<ForgotPasswordPage />} />
                    <Route path="/billing" element={
                      <ProtectedRoute requiredFeature="view_billing">
                        <BillingPage />
                      </ProtectedRoute>
                    } />
                    <Route path="/notifications" element={<Notifications />} />
                    <Route path="/settings" element={<ProfileSettings />} />

                    {/* Organizer-specific pages (non-event) */}
                    <Route path="/organizer/dashboard" element={<OrganizerDashboard />} />
                    <Route path="/organizer/contacts" element={<ContactsPage />} />
                    <Route path="/organizer/reports" element={<ReportsPage />} />

                    <Route path="/organizer/certificates" element={<OrganizerCertificatesPage />} />
                    <Route path="/organizer/events/:uuid/manage" element={<EventManagement />} />
                    <Route path="/organizer/badges" element={<OrganizerBadgesPage />} />
                    <Route path="/organizer/zoom" element={<ZoomManagement />} />

                    {/* Organization Routes */}
                    <Route path="/organizations" element={<OrganizationsListPage />} />
                    <Route path="/organizations/new" element={
                      <ProtectedRoute requiredFeature="can_create_organization">
                        <CreateOrganizationPage />
                      </ProtectedRoute>
                    } />

                    {/* Organization Onboarding - OUTSIDE OrganizationLayout */}
                    <Route path="/org/:slug/onboarding" element={<OrganizationOnboardingWizard />} />

                    <Route element={<OrganizationLayout />}>
                      <Route path="/org/:slug" element={<OrganizationDashboard />} />
                      <Route path="/org/:slug/instructor" element={<InstructorDashboard />} />
                      <Route path="/org/:slug/events" element={<OrgEventsPage />} />
                      <Route path="/org/:slug/team" element={<TeamManagementPage />} />
                      <Route path="/org/:slug/settings" element={<OrganizationSettingsPage />} />
                      <Route path="/org/:slug/billing" element={<OrganizationBillingPage />} />
                      <Route path="/org/:slug/courses" element={<OrgCoursesPage />} />
                      <Route path="/org/:slug/courses/new" element={
                        <ProtectedRoute requiredFeature="create_courses">
                          <CreateCoursePage />
                        </ProtectedRoute>
                      } />
                      <Route path="/org/:slug/courses/:courseSlug" element={<CourseManagementPage />} />
                      <Route path="/org/:slug/badges" element={<OrganizerBadgesPage />} />
                      <Route path="/org/:slug/certificates" element={<CourseCertificatesPage />} />
                    </Route>
                  </Route>

                  {/* Redirects for old organizer event routes */}
                  <Route path="/organizer/events" element={<Navigate to="/events" replace />} />
                  <Route path="/organizer/events/new" element={<Navigate to="/events/create" replace />} />
                  <Route path="/organizer/events/:id" element={<Navigate to="/events/:id" replace />} />
                  <Route path="/organizer/events/:id/edit" element={<Navigate to="/events/:id/edit" replace />} />
                  <Route path="/organizer/settings" element={<Navigate to="/settings" replace />} />
                  <Route path="/organizer/notifications" element={<Navigate to="/notifications" replace />} />
                  <Route path="/profile" element={<Navigate to="/settings" replace />} />

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
          <SonnerToaster position="top-right" richColors closeButton />
          <InstallPrompt />
        </BrowserRouter>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
