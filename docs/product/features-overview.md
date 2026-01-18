Accredit Product Feature Overview
This document provides a holistic overview of the features implemented in the Accredit platform, categorized by functional area.

1. Organization & Team Management
Multi-Tenant Architecture

Organizations: Central hubs for managing events, courses, and team members.
Roles & Permissions:
Admin: Full control (organizer + course manager capabilities), manages billing/subscriptions. 1 included in $199/mo base plan.
Organizer: Can manage events and contacts. Requires organizer subscription ($129/seat if org-paid, or self-paid).
Course Manager: Can create and manage all courses ($129/seat).
Instructor: Can manage only assigned course (Unlimited/Free).
Team Collaboration: Invite members via email, manage seat assignments.
Branding: Custom logos, colors, and domains (slugs) for organization portals.
2. Event Management
Lifecycle Management

Creation Wizard: Step-by-step flow for details, schedule, and ticketing.
Sessions: Support for multi-session events (days/times).
Virtual / Hybrid:
Zoom Integration: Native support for Meetings and Webinars.
Automated Sync: Webhooks track meeting start/end and participant attendance.
Cloud Recordings: Auto-ingest Zoom recordings, manage visibility, and access control (Registrants only, Public, etc.).
Feedback: Post-event 5-star surveys (Content, Speaker, Overall) with anonymous option.
3. Learning Management System (LMS)
Course Delivery

Formats: Self-paced (Online) and Hybrid (Live Sessions).
Modules: Structured learning paths with release schedules:
Immediate, Scheduled Date, Days after Registration, or Prerequisite-based.
Content Types: Video, Documents (PDFs), Rich Text, Quizzes, External Links.
Progress Tracking:
granular video playback tracking (last position).
Module completion status.
Course-level progress bars.
Assessment & Grading

Assignments:
Submission types: Text, File Upload, URL, Mixed.
Rubric-based grading.
Workflow: Draft -> Submitted -> In Review -> Graded/Returned.
Quizzes: Auto-graded assessments with passing score thresholds.
4. Certificates & Compliance
Accreditation Engine

Template Builder:
Drag-and-drop field positioning (Name, Date, Title, etc.).
Custom background uploads (PDF/Image).
Size & Orientation control.
Issuance:
Automated: Triggered on Event attendance or Course completion.
Manual: Admin issuance override.
Verification:
generic public verification page (/verify/{code}).
QR Codes on certificates.
Immutable historical snapshots of attendee data at time of issuance.
CPD/CNE Tracking:
Track credit hours and types (e.g., "Clinical", "Ethics").
Compliance reporting via Feedback surveys.
5. Commerce & Billing
Monetization

Stripe Connect:
Payouts to organizers for paid events/courses.
Split payments functionality.
Subscriptions:
Organization-level SaaS billing (Free, Organization tier).
Per-seat billing logic for additional Organizers.
Ticketing:
Paid vs Free events.
Promotion Codes (Percentage or Fixed amount discounts).
Inventory management (Max capacity).
6. CRM & Communications
Attendee Management

Contacts: Centralized database of attendees across all events.
Lists & Tags: Segment users for targeted communication.
History: View full engagement history (Registrations, Certificates, Emails).
Email Engine

Transactional: Automated emails for Verification, Reset Password, Confirmations.
Engagement: Event reminders, Certificate delivery.
Tracking: Logs for Sent, Delivered, Opened, Clicked statuses.
7. Integrations
Zoom: Deep two-way sync (Webhooks, Recordings, Attendance).
Stripe: Payments, subscriptions, and Connect express onboarding.
Files: Cloud storage for resources and generated PDFs.