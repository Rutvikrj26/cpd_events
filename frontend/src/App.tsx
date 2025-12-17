import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from "@/components/ui/toaster";
import { AuthProvider } from "@/contexts/AuthContext";
import ProtectedRoute from "@/components/layout/ProtectedRoute";


// Layouts
import { PublicLayout } from './components/layout/PublicLayout';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { AuthLayout } from './components/layout/AuthLayout';

// Public Pages
import { LandingPage } from './pages/public/LandingPage';
import { EventDiscovery } from './pages/public/EventDiscovery';
import { EventDetail } from './pages/public/EventDetail';

// Auth Pages
import { LoginPage } from './pages/auth/LoginPage';
import { SignupPage } from './pages/auth/SignupPage';
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { EventsPage } from './pages/events/EventsPage';
import { EventCreatePage } from './pages/events/EventCreatePage';
import { EventDetailPage } from './pages/events/EventDetailPage';
import { MyRegistrationsPage } from './pages/registrations/MyRegistrationsPage';
import { CertificatesPage } from './pages/certificates/CertificatesPage';
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

// Dashboard Pages - Organizer
import { OrganizerDashboard } from './pages/dashboard/organizer/OrganizerDashboard';
import { EventsList } from './pages/dashboard/organizer/EventsList';
import { CreateEvent } from './pages/dashboard/organizer/CreateEvent';
import { EventManagement } from './pages/dashboard/organizer/EventManagement';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
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

          <Route path="/pricing" element={
            <PublicLayout>
              <div className="container py-20 text-center">
                <h1 className="text-3xl font-bold">Pricing Page</h1>
                <p className="text-gray-500 mt-4">Coming soon...</p>
              </div>
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

          {/* Protected Routes - Attendee */}
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/events" element={<EventsPage />} />
            <Route path="/events/create" element={<EventCreatePage />} />
            <Route path="/events/:uuid" element={<EventDetailPage />} />
            <Route path="/registrations" element={<MyRegistrationsPage />} />
            <Route path="/certificates" element={<CertificatesPage />} />
            <Route path="/billing" element={<BillingPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/notifications" element={
              <DashboardLayout role="attendee">
                <Notifications />
              </DashboardLayout>
            } />

            <Route path="/settings" element={
              <DashboardLayout role="attendee">
                <ProfileSettings />
              </DashboardLayout>
            } />

            <Route path="/dashboard" element={
              <DashboardLayout role="attendee">
                <AttendeeDashboard />
              </DashboardLayout>
            } />

            <Route path="/events" element={
              <DashboardLayout role="attendee">
                <MyEvents />
              </DashboardLayout>
            } />

            <Route path="/certificates" element={
              <DashboardLayout role="attendee">
                <CertificatesList />
              </DashboardLayout>
            } />

            <Route path="/certificates/:id" element={
              <DashboardLayout role="attendee">
                <CertificateDetail />
              </DashboardLayout>
            } />

            <Route path="/cpd" element={
              <DashboardLayout role="attendee">
                <CPDTracking />
              </DashboardLayout>
            } />

            {/* Organizer Routes - could be separated into another role-protected route later */}
            <Route path="/organizer/dashboard" element={
              <DashboardLayout role="organizer">
                <OrganizerDashboard />
              </DashboardLayout>
            } />

            <Route path="/organizer/events" element={
              <DashboardLayout role="organizer">
                <EventsList />
              </DashboardLayout>
            } />

            <Route path="/organizer/events/new" element={
              <DashboardLayout role="organizer">
                <CreateEvent />
              </DashboardLayout>
            } />

            <Route path="/organizer/events/:id" element={
              <DashboardLayout role="organizer">
                <EventManagement />
              </DashboardLayout>
            } />

            <Route path="/organizer/events/:id/edit" element={
              <DashboardLayout role="organizer">
                <CreateEvent />
              </DashboardLayout>
            } />

            <Route path="/organizer/contacts" element={
              <DashboardLayout role="organizer">
                <div className="text-center py-10">Contacts Manager (Coming Soon)</div>
              </DashboardLayout>
            } />

            <Route path="/organizer/reports" element={
              <DashboardLayout role="organizer">
                <div className="text-center py-10">Reports (Coming Soon)</div>
              </DashboardLayout>
            } />

            <Route path="/organizer/settings" element={
              <DashboardLayout role="organizer">
                <ProfileSettings />
              </DashboardLayout>
            } />
            <Route path="/organizer/notifications" element={
              <DashboardLayout role="organizer">
                <Notifications />
              </DashboardLayout>
            } />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
      <Toaster />
    </BrowserRouter >
  );
}
