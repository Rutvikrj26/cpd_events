# Demo Data Fixtures Plan

This document outlines the strategy for generating a comprehensive set of demo data for the CPD Events platform. The goal is to simulate a living, breathing application with diverse user personas, complex event configurations, and rich engagement history.

## 1. Core Personas (Accounts)

We will create a specific set of users to represent different roles in the ecosystem.

### Staff & Admin
*   **`admin@cpdevents.com`**: Superuser. Full access to Django admin and all platform features.

### Organizers
*   **`organizer.pro@example.com` (Dr. Sarah Chen)**
    *   **Plan**: Pro/LMS Tier.
    *   **Profile**: Medical Professional, "Director of CME at HealthTech Solutions".
    *   **Setup**: Stripe Connect "Enabled", Zoom Connected.
    *   **Assets**: Has custom certificate templates, badge templates, and extensive contact lists.
*   **`organizer.basic@example.com` (John Doe)**
    *   **Plan**: Basic/Attendee Tier (Free Organizer).
    *   **Profile**: "Community Coordinator".
    *   **Setup**: No Stripe (Free events only), No Zoom integration (Manual links).

### Instructors/Speakers
*   **`speaker.guest@example.com` (Prof. Alan Grant)**
    *   **Role**: Guest Speaker linked to specific sessions.
    *   **Bio**: Distinguished expert profile.

### Attendees (Learners)
*   **`attendee.engaged@example.com` (Alice Active)**
    *   **Profile**: High engagement.
    *   **Status**: Has earned certificates, badges, completes courses, gives feedback.
    *   **CPD**: Has specific CPD Requirements tracked (e.g., "Medical Board 2024").
*   **`attendee.casual@example.com` (Bob Basic)**
    *   **Profile**: Registers for free events, occasionally attends.
    *   **Status**: Some incomplete enrollments.
*   **`attendee.new@example.com` (Charlie New)**
    *   **Profile**: Just signed up, no history.
    *   **Status**: In onboarding flow.

---

## 2. Billing & Subscriptions

Simulate the SaaS aspect of the platform.

### Stripe Products & Prices
*   **Basic**: Free.
*   **Organizer**: $29/mo (Limits: 5 events/mo).
*   **LMS**: $49/mo (Includes Courses).
*   **Pro**: $99/mo (Unlimited, Teams).

### Subscriptions
*   **Pro Subscription**: Linked to `organizer.pro`. Status: `active`. Auto-renew enabled.
*   **Basic Subscription**: Linked to `organizer.basic`. Status: `active` (Free tier).
*   **Past Due Subscription**: Linked to a dummy user `churned@example.com` to demonstrate dunning UI.

### Financials
*   **Invoices**: Generate 6 months of paid invoices for `organizer.pro`.
*   **Payment Methods**: Valid Visa card attached to `organizer.pro`.

---

## 3. Assets (Badges & Certificates)

Templates required for event/course completion logic.

### Certificate Templates
*   **"HealthTech Standard Certificate"**: Owned by `organizer.pro`. Landscape, blue theme.
*   **"Generic Completion"**: Default system template.

### Badge Templates
*   **"Certified Expert"**: Gold badge image.
*   **"Early Adopter"**: Silver badge image.
*   **"Workshop Survivor"**: Bronze badge image.

---

## 4. Events Architecture

Showcase different event types and complexities.

### Event A: "Future of Medicine 2025" (The Flagship)
*   **Owner**: `organizer.pro`
*   **Type**: Hybrid Conference (Multi-session).
*   **Status**: `PUBLISHED` (Upcoming).
*   **Settings**: Paid ($199), CPD Enabled (10 Credits), Certificates Enabled.
*   **Sessions**:
    1.  *Keynote* (Live, Main Hall).
    2.  *Breakout A: Ethics* (Live, Room 101).
    3.  *Breakout B: Tech* (Recorded).
*   **Registrations**:
    *   `attendee.engaged`: Confirmed, Paid.
    *   `attendee.casual`: Waitlisted.
    *   50+ generated dummy registrations for stats density.

### Event B: "Weekly Health Webinar" (The Recurring)
*   **Owner**: `organizer.pro`
*   **Type**: Webinar (Single session).
*   **Status**: `COMPLETED` (Past).
*   **Settings**: Free, Zoom Integrated.
*   **Outcomes**:
    *   Attendance records populated (Join/Leave times).
    *   Certificates issued to eligible attendees.
    *   Feedback collected.

### Event C: "Community Meetup" (The Basic)
*   **Owner**: `organizer.basic`
*   **Type**: Social/Networking.
*   **Status**: `LIVE` (Currently happening).
*   **Settings**: Free, In-person location (No Zoom).

---

## 5. Learning (LMS)

Showcase self-paced and hybrid course capabilities.

### Course A: "Medical Ethics 101" (Self-Paced)
*   **Owner**: `organizer.pro`
*   **Format**: Online.
*   **Structure**:
    *   *Module 1: Intro* (Video Content).
    *   *Module 2: Case Studies* (PDF Reading).
    *   *Module 3: Assessment* (Quiz with 70% passing score).
*   **Enrollments**:
    *   `attendee.engaged`: Completed (Passed Quiz, Certificate Issued).
    *   `attendee.casual`: In Progress (Stuck on Module 2).

### Course B: "Advanced Surgery Tech" (Hybrid)
*   **Owner**: `organizer.pro`
*   **Format**: Hybrid (Requires Module completion + Live Session attendance).
*   **Price**: $499.
*   **Assignments**:
    *   *Final Paper*: File upload required. Rubric attached.

---

## 6. Marketing & Growth

### Promo Codes
*   **`EARLYBIRD25`**: 25% off. Active. Used by `attendee.engaged`.
*   **`COMMUNITY10`**: $10 off. Active.
*   **`EXPIRED50`**: 50% off. Expired last year.

### Contact Lists
*   **"Newsletter Subscribers"**: 200 contacts. Linked to `organizer.pro`.
*   **"VIP Doctors"**: 25 contacts. Tagged with `High Value`.

---

## 7. Engagement & Feedback

*   **Event Feedback**:
    *   Alice rates "Event B" 5/5 stars with comment "Excellent content!".
    *   Bob rates "Event B" 3/5 stars with comment "Audio issues".
*   **Zoom Logs**:
    *   Webhooks for "Event B" showing participant join/leave events.
    *   Cloud recording entry for "Event B".

---

## Implementation Plan

We will create separate fixture files (JSON) or a management command `create_demo_data` to generate this data programmatically. Using a management command is preferred to handle dynamic dates (e.g., ensuring "Upcoming" events are always in the future relative to when the script runs).

### Order of Operations
1.  **Users & Profiles**: Create base users.
2.  **Billing**: Setup products and attach subscriptions.
3.  **Core Assets**: Create templates, contact lists, promo codes.
4.  **Events**: Create events, sessions, and speakers.
5.  **Learning**: Create courses, modules, and content.
6.  **Engagement**: Generate registrations, enrollments, attendance records, and submissions.
7.  **Outcomes**: Issue certificates and badges based on the engagement data.
