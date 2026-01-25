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

// Public Pages
import { LandingPage } from './pages/public/LandingPage';
import { EventDetail } from './pages/public/EventDetail';
import { EventRegistration } from './pages/public/EventRegistration';
import { PricingPage } from './pages/public/PricingPage';
import { ContactPage } from './pages/public/ContactPage';
import { NotFoundPage } from './pages/public/NotFoundPage';
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

// Organization Pages - REMOVED

// Course Pages
import { CourseManagementPage } from './pages/courses/management/CourseManagementPage';
import CourseManagerPage from './pages/courses/management/CourseManagerPage';
import CreateCoursePage from './pages/courses/management/CreateCoursePage';

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
              <Routes>
                {/* Public Routes */}
                <Route path="/" element={
                  <PublicLayout>
                    <AuthenticatedRoot />
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

                <Route path="/forgot-password" element={
                  <AuthLayout>
                    <ForgotPasswordPage />
                  </AuthLayout>
                } />

                {/* Password Reset - matches backend /auth/reset-password */}
                <Route path="/auth/reset-password" element={
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

                     {/* Events - organizer only for management */}
                     <Route path="/events" element={
                       <ProtectedRoute requiredFeature="create_events">
                         <EventsPage />
                       </ProtectedRoute>
                     } />
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
                     <Route path="/my-courses" element={<MyCoursesPage />} />

                    <Route path="/courses/certificates" element={<CourseCertificatesPage />} />
                    <Route path="/courses/manage" element={
                      <ProtectedRoute requiredFeature="create_courses">
                        <CourseManagerPage />
                      </ProtectedRoute>
                    } />
                    <Route path="/courses/manage/new" element={
                      <ProtectedRoute requiredFeature="create_courses">
                        <CreateCoursePage />
                      </ProtectedRoute>
                    } />
                    <Route path="/courses/manage/:courseSlug" element={
                      <ProtectedRoute requiredFeature="create_courses">
                        <CourseManagementPage />
                      </ProtectedRoute>
                    } />
                    <Route path="/learn/:courseUuid" element={<CoursePlayerPage />} />
                    <Route path="/courses/:courseSlug/learn" element={<CoursePlayerPage />} />
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
                    <Route path="/organizer/dashboard" element={
                      <ProtectedRoute requiredFeature="create_events">
                        <OrganizerDashboard />
                      </ProtectedRoute>
                    } />
                    <Route path="/organizer/contacts" element={
                      <ProtectedRoute requiredFeature="create_events">
                        <ContactsPage />
                      </ProtectedRoute>
                    } />
                    <Route path="/organizer/reports" element={
                      <ProtectedRoute requiredFeature="create_events">
                        <ReportsPage />
                      </ProtectedRoute>
                    } />
                    <Route path="/organizer/certificates" element={
                      <ProtectedRoute requiredFeature="create_events">
                        <OrganizerCertificatesPage />
                      </ProtectedRoute>
                    } />
                    <Route path="/organizer/events/:uuid/manage" element={
                      <ProtectedRoute requiredFeature="create_events">
                        <EventManagement />
                      </ProtectedRoute>
                    } />
                    <Route path="/organizer/badges" element={
                      <ProtectedRoute requiredFeature="create_events">
                        <OrganizerBadgesPage />
                      </ProtectedRoute>
                    } />
                    <Route path="/organizer/zoom" element={
                      <ProtectedRoute requiredFeature="create_events">
                        <ZoomManagement />
                      </ProtectedRoute>
                    } />

                    {/* Redirects for old organizer event routes */}
                    <Route path="/organizer/events" element={<Navigate to="/events" replace />} />
                    <Route path="/organizer/events/new" element={<Navigate to="/events/create" replace />} />
                    <Route path="/organizer/events/:id" element={<Navigate to="/events/:id" replace />} />
                    <Route path="/organizer/events/:id/edit" element={<Navigate to="/events/:id/edit" replace />} />
                    <Route path="/organizer/settings" element={<Navigate to="/settings" replace />} />
                    <Route path="/organizer/notifications" element={<Navigate to="/notifications" replace />} />
                    <Route path="/profile" element={<Navigate to="/settings" replace />} />

                  </Route>

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
