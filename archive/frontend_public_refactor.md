# Frontend Public-Facing Refactor Plan

## Executive Summary
This document outlines a strategic refactor of the public-facing frontend to align the user experience with the platform's legal identity as a **Marketplace**. Currently, the UI positions Accredit primarily as a SaaS tool for organizers, neglecting the Attendee experience and creating a disconnect with the Terms of Service.

## 1. Navigation & Discovery (High Priority)
**Goal:** Make the "Marketplace" visible and accessible to users.

### 1.1 Update Main Navigation (`PublicLayout.tsx`)
- **Action:** Add a top-level "Browse" or "Find Training" link to the navbar.
- **Target:** Link to `/events` (mapped to `EventDiscovery` component).
- **Placement:** Between "Products" and "Pricing".
- **Rationale:** Users cannot buy what they cannot find. A marketplace requires a storefront.

### 1.2 Hero Section Dual-CTA (`LandingPage.tsx`)
- **Action:** Update the Hero section to address both audiences.
- **Current:** "Get Started Free" (Organizer focused).
- **New:** 
  - Primary: "Get Started Free" (for Organizers).
  - Secondary: "Browse Events" or "Verify Certificate" (for Attendees).

## 2. Authentication & Onboarding (High Priority)
**Goal:** Reduce friction and fix broken entry paths.

### 2.1 Restore Social Login (`SignupPage.tsx`)
- **Action:** Uncomment and enable the Google Sign-In button.
- **Task:** Verify `initiateGoogleSignIn` integration with the backend.
- **Rationale:** Password-only signup is a high-friction barrier for attendees who just want to register for a webinar.

### 2.2 Unified Signup Flow
- **Action:** Ensure the signup flow handles both "Organizer" and "Attendee" intents gracefully.
- **Task:** Verify `role` query parameter handling ensures users land in the correct dashboard view after signup.

## 3. Landing Page & Copy Overhaul (Medium Priority)
**Goal:** Communicate value to the *entire* ecosystem (Organizers + Attendees).

### 3.1 Add "For Professionals" Section (`LandingPage.tsx`)
- **Action:** Add a new section highlighting Attendee benefits.
- **Key Points:**
  - "One-click registration"
  - "Centralized CPD Wallet/Passport"
  - "Verifiable Digital Certificates"
  - "Permanent Learning Record"

### 3.2 Review Claims vs. Legal
- **Action:** Audit the "99.9% Uptime Guarantee" claim.
- **Fix:** Change to "Designed for high reliability" or "Enterprise-grade infrastructure" unless a specific SLA exists in the Enterprise contract.

## 4. Pricing & Packaging (Medium Priority)
**Goal:** Clarify options and remove artificial barriers.

### 4.1 Clarify "Hybrid" Needs (`PricingPage.tsx`)
- **Problem:** Users think they must choose between "Events" OR "Courses".
- **Action:** Add a "Bundle" or "Pro" tier visual representation (even if it maps to the Organization plan on the backend) to show that users can have both.

### 4.2 Organization Plan Transparency
- **Action:** Replace "Contact Sales" with "Starting at $X/mo" or "Custom pricing for teams".
- **Rationale:** "Contact Sales" is a barrier for mid-sized teams who might self-serve if they knew the ballpark cost.

## 5. Visual Trust (Low Priority)
**Goal:** Show the product, don't just tell.

### 5.1 Replace Wireframes (`FeaturesPage.tsx`)
- **Action:** Replace code-drawn "Visual Components" (e.g., `EventManagementVisual`) with high-fidelity screenshots of the actual application dashboard.
- **Rationale:** Abstract wireframes lower perceived value. Real screenshots prove the software exists and is polished.

## Implementation Roadmap

### Phase 1: The Marketplace Fix (Immediate)
- [ ] Update `PublicLayout.tsx` navigation.
- [ ] Uncomment Google Auth in `SignupPage.tsx`.

### Phase 2: The Attendee Value (Next Sprint)
- [ ] Rewrite `LandingPage.tsx` Hero section.
- [ ] Add "For Professionals" section to Landing Page.

### Phase 3: Visual & Pricing Polish (Future)
- [ ] Update `PricingPage.tsx` structure.
- [ ] Capture and implement dashboard screenshots for `FeaturesPage.tsx`.
