# CPD Events - User Workflows Documentation

This document contains Mermaid diagrams for all user workflows implemented in the frontend application.

## Table of Contents
1. [Authentication & Signup Workflows](#1-authentication--signup-workflows)
2. [Onboarding Workflow](#2-onboarding-workflow)
3. [Event Creation Workflow](#3-event-creation-workflow)
4. [Event Registration Workflow](#4-event-registration-workflow)
5. [Promo Code Workflow](#5-promo-code-workflow)
6. [Organizer Dashboard Workflows](#6-organizer-dashboard-workflows)
7. [Attendee Dashboard Workflows](#7-attendee-dashboard-workflows)
8. [Feedback Collection Workflow](#8-feedback-collection-workflow)
9. [Billing & Subscription Workflow](#9-billing--subscription-workflow)
10. [Subscription Cancellation with Retention](#10-subscription-cancellation-with-retention)
11. [Profile & Settings Workflows](#11-profile--settings-workflows)
12. [Organization Management Workflow](#12-organization-management-workflow)
13. [Zoom Integration Workflow](#13-zoom-integration-workflow)
14. [Certificate Verification Workflow](#14-certificate-verification-workflow)
15. [Event Duplication Workflow](#15-event-duplication-workflow)
16. [Complete Application Flow](#16-complete-application-flow)

---

## 1. Authentication & Signup Workflows

### Login Flow
```mermaid
flowchart TD
    A["/login"] --> B{Authentication Method}
    B -->|Email/Password| C[Enter Credentials]
    B -->|Zoom OAuth| D[Redirect to Zoom]

    C --> E{Valid Credentials?}
    E -->|Yes| F[Store Auth Token]
    E -->|No| G[Show Error Toast]
    G --> C

    D --> H["/auth/callback"]
    H --> F

    F --> I{User Role?}
    I -->|Organizer| J["/organizer/dashboard"]
    I -->|Attendee| K["/dashboard"]
```

### Signup Flow
```mermaid
flowchart TD
    A["/signup"] --> B[Select Account Type]
    B -->|Attendee| C[Attendee Registration Form]
    B -->|Organizer| D[Organizer Registration Form]

    C --> E[Enter: Email, Name, Password]
    D --> F[Enter: Email, Name, Password]
    F --> G[Auto-enroll 30-day Professional Trial]

    E --> H[Accept Terms & Conditions]
    G --> H

    H --> I{Form Valid?}
    I -->|No| J[Show Validation Errors]
    J --> E

    I -->|Yes| K[Submit Registration]
    K --> L[Send Confirmation Email]
    L --> M[Redirect to "/login" with Success Message]

    subgraph "URL Parameters"
        N["?plan=pro|professional|starter"]
        O["?role=organizer"]
    end
```

### Password Recovery Flow
```mermaid
flowchart TD
    A["/login"] --> B["Click 'Forgot Password?'"]
    B --> C["/forgot-password"]

    C --> D["Enter Email Address"]
    D --> E["Submit Request"]
    E --> F["resetPassword API"]

    F --> G{Email Exists?}
    G -->|Yes| H["Send Reset Email"]
    G -->|No| I["Show generic 'Check email' message"]

    H --> J["Success Message"]
    J --> K["'Check your email' instruction"]

    I --> J

    subgraph "Email Link Flow"
        L["User clicks link in email"]
        L --> M["/reset-password?token=xxx"]
        M --> N["ResetPasswordPage"]
        N --> O["Enter New Password"]
        O --> P["Confirm Password"]
        P --> Q{Passwords Match?}
        Q -->|No| R["Show validation error"]
        R --> O
        Q -->|Yes| S["Submit"]
        S --> T["confirmPasswordReset API"]
        T --> U{Token Valid?}
        U -->|Yes| V["Success Message"]
        V --> W["Redirect to /login"]
        U -->|No| X["Token expired/invalid error"]
        X --> Y["'Request new link' option"]
        Y --> C
    end
```

---

## 2. Onboarding Workflow

```mermaid
flowchart TD
    A[Organizer Signup Complete] --> B{Onboarding Completed?}
    B -->|No| C["/onboarding"]
    B -->|Yes| D["/organizer/dashboard"]

    C --> E["Step 1: Welcome"]
    E --> F["Display Trial Status: 30 days"]
    F --> G["Show Feature Limits"]
    G --> H[Click "Let's Get Started"]

    H --> I["Step 2: Profile Setup"]
    I --> J["Enter Full Name"]
    J --> K["Enter Organization Name"]
    K --> L[Click Next]

    L --> M["Step 3: Zoom Integration"]
    M --> N{Connect Zoom?}
    N -->|Yes| O["Redirect to Zoom OAuth"]
    O --> P["Store onboarding_redirect in sessionStorage"]
    P --> Q["Zoom Authorization"]
    Q --> R["Return to Onboarding Step 3"]
    N -->|Skip| S[Click Next/Skip]
    R --> S

    S --> T["Step 4: Billing Details"]
    T --> U["Display Plan: $30/mo"]
    U --> V["Show Trial Countdown"]
    V --> W{Add Payment Method?}
    W -->|Yes| X["Open PaymentMethodModal"]
    X --> Y["Enter Card Details via Stripe"]
    Y --> Z[Card Saved]
    W -->|Skip| AA[Click Skip]
    Z --> AA

    AA --> AB["Step 5: Complete"]
    AB --> AC["You're All Set!"]
    AC --> AD["Call refreshManifest()"]
    AD --> AE{Choose Action}
    AE -->|Create Event| AF["/events/create"]
    AE -->|Explore| AG["/dashboard"]
```

---

## 3. Event Creation Workflow

```mermaid
flowchart TD
    A["/events/create"] --> B["EventWizard Component"]

    B --> C["Step 1: Basic Info"]
    C --> C1["Event Title (required)"]
    C1 --> C2["Event Description (rich text)"]
    C2 --> C3["Event Type: webinar|workshop|course|conference"]
    C3 --> C4["Featured Image Upload"]
    C4 --> D[Next]

    D --> E["Step 2: Schedule"]
    E --> E1["Start Date & Time"]
    E1 --> E2["End Date & Time"]
    E2 --> E3["Timezone Selection"]
    E3 --> E4{Multi-Session?}
    E4 -->|Yes| E5["SessionEditor: Add/Edit Sessions"]
    E4 -->|No| F[Next]
    E5 --> F

    F --> G["Step 3: Details"]
    G --> G1["Format: Online|In-person|Hybrid"]
    G1 --> G2["Location (if applicable)"]
    G2 --> G3["CPD Credits: Value + Type"]
    G3 --> G4["Registration Deadline"]
    G4 --> G5["Max Attendees"]
    G5 --> G6["Learning Objectives"]
    G6 --> G7["Speakers Selection"]
    G7 --> G8["Custom Registration Fields"]
    G8 --> H[Next]

    H --> I["Step 4: Settings"]
    I --> I1["Registration Enabled Toggle"]
    I1 --> I2["Certificate Generation Toggle"]
    I2 --> I3["Certificate Template Selection"]
    I3 --> I4{Free Event?}
    I4 -->|No| I5["Set Price & Currency"]
    I4 -->|Yes| I6["Zoom Integration Options"]
    I5 --> I6
    I6 --> I7["Attendance Tracking Settings"]
    I7 --> J[Next]

    J --> K["Step 5: Review"]
    K --> K1["Summary of All Data"]
    K1 --> K2["Edit Buttons per Section"]
    K2 --> L{Submit}

    L --> M["Validate All Steps"]
    M --> N["Create Event via API"]
    N --> O["Upload Featured Image"]
    O --> P{Multi-Session?}
    P -->|Yes| Q["Create Sessions"]
    P -->|No| R["Success Toast"]
    Q --> R
    R --> S["Redirect to /events"]
```

### Edit Event Flow
```mermaid
flowchart TD
    A["/events/:uuid/edit"] --> B["Load Event Data"]
    B --> C["Pre-populate EventWizard"]
    C --> D["User Makes Changes"]
    D --> E{Submit}
    E --> F["updateEvent(uuid, data)"]
    F --> G["Handle Sessions"]
    G --> G1["Delete Removed Sessions"]
    G1 --> G2["Create New Sessions"]
    G2 --> G3["Update Existing Sessions"]
    G3 --> H["Success Toast"]
    H --> I["Redirect to /events"]
```

---

## 4. Event Registration Workflow

```mermaid
flowchart TD
    A["/events/:id/register"] --> B["Display Event Summary"]

    B --> C["Step 1: Registration Form"]
    C --> D["First Name (required)"]
    D --> E["Last Name (required)"]
    E --> F["Email (required)"]
    F --> G["Professional Title (optional)"]
    G --> H["Organization (optional)"]

    H --> I{Event is Paid?}
    I -->|Yes| I1["Show Promo Code Input"]
    I1 --> I2["Enter code + Apply button"]
    I2 --> I3{Code Valid?}
    I3 -->|Yes| I4["Show discount applied"]
    I3 -->|No| I5["Show error message"]
    I4 --> J
    I5 --> I2
    I -->|No| J

    J --> K["Custom Fields from Event"]

    K --> L{User Authenticated?}
    L -->|No| M["Show 'Create Account' Checkbox"]
    M --> N{Checkbox Checked?}
    N -->|Yes| O["Show Password Field"]
    N -->|No| P[Continue]
    O --> P
    L -->|Yes| P

    P --> Q["Submit Registration"]
    Q --> R["registerForEvent API Call"]
    R --> R1["Include promo_code if applied"]

    R1 --> S{requires_payment?}
    S -->|No - Free or 100% Discount| T["Step 3: Success"]
    S -->|Yes - Paid Event| U["Step 2: Payment"]

    U --> V["Display Stripe PaymentForm"]
    V --> V1["Show discounted amount if promo applied"]
    V1 --> W["Enter Card Details"]
    W --> X["Process Payment"]
    X --> Y{Payment Successful?}
    Y -->|Yes| Z["handlePaymentSuccess()"]
    Y -->|No| AA["Show Error, Retry"]
    AA --> W

    Z --> AB{Create Account Requested?}
    AB -->|Yes| AC["Create User Account"]
    AB -->|No| T
    AC --> T

    T --> AD["Green Checkmark"]
    AD --> AE["'You're Registered!' Message"]
    AE --> AF["Check Email for Confirmation"]
    AF --> AG{User Choice}
    AG -->|View Event| AH["/events/:slug"]
    AG -->|Browse More| AI["/events/browse"]
```

---

## 5. Promo Code Workflow

### Attendee: Applying Promo Code During Registration
```mermaid
flowchart TD
    A["/events/:id/register"] --> B{Event is Paid?}
    B -->|No - Free| C["No Promo Code Field"]
    B -->|Yes - Paid| D["Show Promo Code Input"]

    D --> E["Enter Promo Code"]
    E --> F["Click 'Apply' Button"]
    F --> G["validatePromoCode API"]

    G --> H{Code Valid?}
    H -->|No| I["Show Error Message"]
    I --> I1["Invalid code"]
    I --> I2["Code expired"]
    I --> I3["Code exhausted"]
    I --> I4["Already used"]
    I --> I5["Min order not met"]
    I --> E

    H -->|Yes| J["Show Applied State"]
    J --> J1["Green checkmark"]
    J --> J2["Code name + discount display"]
    J --> J3["Remove button"]

    J --> K["Update Price Card"]
    K --> K1["Show 'Your Price' label"]
    K --> K2["Display discounted price"]
    K --> K3["Show original price strikethrough"]
    K --> K4["Show savings amount"]

    J3 --> L["Click Remove"]
    L --> M["Reset to original price"]
    M --> D

    K --> N["Submit Registration"]
    N --> O["Include promo_code in request"]
    O --> P{Final Price = $0?}
    P -->|Yes| Q["Skip Payment Step"]
    Q --> R["Registration Complete"]
    P -->|No| S["Proceed to Payment"]
    S --> T["Pay Discounted Amount"]
    T --> R
```

### Organizer: Managing Promo Codes
```mermaid
flowchart TD
    A["/organizer/promo-codes"] --> B["Promo Codes List"]
    B --> B1["Code name"]
    B --> B2["Discount display"]
    B --> B3["Status badge"]
    B --> B4["Usage count"]
    B --> B5["Actions menu"]

    B --> C["'Create Promo Code' Button"]
    C --> D["PromoCodeForm Modal"]

    D --> E["Code Details"]
    E --> E1["Code string (auto-uppercase)"]
    E --> E2["Description (internal)"]

    D --> F["Discount Settings"]
    F --> F1["Type: Percentage | Fixed Amount"]
    F --> F2["Value (e.g., 20 or $10)"]
    F --> F3["Max discount cap (optional)"]

    D --> G["Validity Settings"]
    G --> G1["Active toggle"]
    G --> G2["Valid from date"]
    G --> G3["Valid until date"]

    D --> H["Usage Limits"]
    H --> H1["Max total uses"]
    H --> H2["Max uses per user"]
    H --> H3["Minimum order amount"]
    H --> H4["First-time buyers only"]

    D --> I["Event Selection"]
    I --> J{Apply to?}
    J -->|All Events| K["Leave events empty"]
    J -->|Specific Events| L["Select events from list"]

    K --> M["Save Promo Code"]
    L --> M
    M --> N["createPromoCode API"]
    N --> O["Success Toast"]
    O --> B

    B5 --> P["View Usage"]
    P --> Q["getPromoCodeUsages API"]
    Q --> R["Usage Table"]
    R --> R1["User email"]
    R --> R2["Event title"]
    R --> R3["Original price"]
    R --> R4["Discount amount"]
    R --> R5["Final price"]
    R --> R6["Date used"]

    B5 --> S["Toggle Active"]
    S --> T["togglePromoCodeActive API"]
    T --> U["Update status badge"]

    B5 --> V["Edit"]
    V --> D

    B5 --> W["Delete"]
    W --> X["Confirmation Dialog"]
    X --> Y["deletePromoCode API"]
```

---

## 6. Organizer Dashboard Workflows

### Main Dashboard
```mermaid
flowchart TD
    A["/organizer/dashboard"] --> B["Page Header"]
    B --> C["'Create New Event' Button"]

    B --> D["Stats Grid"]
    D --> D1["Total Events"]
    D --> D2["Active Events"]
    D --> D3["Total Registrations"]
    D --> D4["Certificates Issued"]

    B --> E["Recent Activity Table"]
    E --> E1["Event Name"]
    E --> E2["Date"]
    E --> E3["Status Badge"]
    E --> E4["Registration Count"]
    E --> E5["Actions Menu"]
    E5 --> E6["Manage Event"]
    E5 --> E7["Edit Event"]

    B --> F["Zoom Integration Card"]
    F --> G{Zoom Connected?}
    G -->|Yes| H["Show Connected Email"]
    H --> I["'Disconnect' Button"]
    G -->|No| J["'Connect Zoom Account' Button"]
```

### Event Management
```mermaid
flowchart TD
    A["/organizer/events/:uuid/manage"] --> B["Event Header"]
    B --> B1["Title & Status Badge"]
    B --> B2["Dates, Format, Timezone"]
    B --> B3["Edit Event Button"]
    B --> B4["Publish/Unpublish Toggle"]

    A --> C["Attendees Tab"]
    C --> C1["Search by Name/Email"]
    C1 --> C2["Filter by Status"]
    C2 --> C3["Attendees Table"]

    C3 --> D["Per Attendee Row"]
    D --> D1["Name, Email"]
    D --> D2["Status Badge"]
    D --> D3["Attendance Checkbox"]
    D --> D4["Actions Menu"]
    D4 --> D5["Edit Attendance"]
    D4 --> D6["Email Attendee"]
    D4 --> D7["View Certificate"]

    C --> E["Bulk Actions"]
    E --> E1["Select All"]
    E --> E2["Issue Certificates"]
    E --> E3["Export Attendee List"]
    E --> E4["Send Email Campaign"]

    E2 --> F["Certificate Issuance"]
    F --> F1["Confirmation Dialog"]
    F1 --> F2["issueCertificates API"]
    F2 --> F3["Success Toast with Count"]

    D3 --> G["Attendance Tracking"]
    G --> G1["Toggle Check-in"]
    G1 --> G2["checkInAttendee API"]
    G2 --> G3["Optimistic UI Update"]

    D5 --> H["EditAttendanceDialog"]
    H --> H1["Attendance Percentage"]
    H --> H2["Notes"]
```

---

## 6. Attendee Dashboard Workflows

### Main Dashboard
```mermaid
flowchart TD
    A["/dashboard (Attendee)"] --> B["Welcome Header"]
    B --> B1["'Welcome back, [Name]!'"]
    B --> B2["'Browse Events' Button"]
    B --> B3["'View Profile' Button"]

    A --> C["Stats Grid"]
    C --> C1["Total CPD Credits"]
    C --> C2["Certificates Earned"]
    C --> C3["Upcoming Events"]
    C --> C4["Total Learning Hours"]

    A --> D["Your Upcoming Events"]
    D --> E{Has Events?}
    E -->|Yes| F["Event Cards"]
    F --> F1["Date Badge"]
    F --> F2["Event Title, Type"]
    F --> F3["CPD Credits"]
    F --> F4{Zoom Available?}
    F4 -->|Yes| F5["'Join Session' Button"]
    F4 -->|No| F6["'View Details' Button"]

    E -->|No| G["Empty State"]
    G --> G1["'Browse Events' Button"]

    A --> H["Sidebar"]
    H --> I["'Host Your Own Events' Card"]
    I --> J["'Become an Organizer' Button"]
```

### My Registrations
```mermaid
flowchart TD
    A["/registrations"] --> B["Registrations Table"]
    B --> C["Columns"]
    C --> C1["Event Name"]
    C --> C2["Date Registered"]
    C --> C3["Status Badge"]
    C --> C4["Payment Status Badge"]
    C --> C5["Actions"]

    C5 --> D["'View Event' Link"]

    C4 --> E{Payment Status}
    E -->|Pending| F["'Pay Now' Button"]
    E -->|Failed| G["'Retry Payment' Button"]
    E -->|Paid| H["No Action Needed"]

    A --> I["'Missing Events?' Card"]
    I --> J["'Find & Link My Events' Button"]
    J --> K["linkRegistrations API"]
    K --> L["Show Count of Linked Events"]
```

### My Certificates
```mermaid
flowchart TD
    A["/certificates"] --> B["Search Bar"]
    B --> C["Certificate Count Badge"]
    C --> D["Certificates Table"]

    D --> E["Columns"]
    E --> E1["Event Name"]
    E --> E2["Date Issued"]
    E --> E3["CPD Credits"]
    E --> E4["Status"]
    E --> E5["Actions"]

    E5 --> F["'Download' - Opens PDF"]
    E5 --> G["'View' - Opens /verify/:code"]
    E5 --> H["'Share' - Copy Link + Toast"]

    D --> I["Click Certificate Row"]
    I --> J["/my-certificates/:id"]
    J --> K["Full Certificate Display"]
    K --> K1["Verification Details"]
    K --> K2["Download/Share Options"]
```

---

## 8. Feedback Collection Workflow

### Attendee: Leaving Feedback
```mermaid
flowchart TD
    A["/registrations"] --> B["My Registrations Table"]
    B --> C{Event Status?}

    C -->|Upcoming| D["No Feedback Option"]
    C -->|Past/Completed| E["'Leave Feedback' Button"]

    E --> F{Already Submitted?}
    F -->|Yes| G["Button disabled: 'Feedback Submitted'"]
    F -->|No| H["Open FeedbackModal"]

    H --> I["FeedbackForm Component"]
    I --> J["Overall Rating (1-5 stars)"]
    J --> K["Content Quality Rating (1-5 stars)"]
    K --> L["Speaker Rating (1-5 stars)"]
    L --> M["Comments (optional textarea)"]
    M --> N["Anonymous Toggle"]

    N --> O["Submit Feedback"]
    O --> P["createFeedback API"]
    P --> Q{Success?}
    Q -->|Yes| R["Success Toast"]
    R --> S["Close Modal"]
    S --> T["Update button to 'Feedback Submitted'"]
    Q -->|No| U["Error Toast"]
    U --> I

    subgraph "Star Rating Component"
        V["Hover State"]
        V --> V1["Stars highlight on hover"]
        V --> V2["Click to select rating"]
        V --> V3["Sizes: sm, md, lg"]
        V --> V4["Readonly mode for display"]
    end
```

### Organizer: Viewing Event Feedback
```mermaid
flowchart TD
    A["/organizer/events/:uuid/manage"] --> B["Event Management Page"]
    B --> C["Tabs: Attendees | Feedback | Settings"]

    C --> D["Feedback Tab"]
    D --> E["FeedbackSummary Component"]

    E --> F["Aggregate Stats"]
    F --> F1["Average Overall Rating"]
    F --> F2["Average Content Quality"]
    F --> F3["Average Speaker Rating"]
    F --> F4["Total Responses Count"]

    E --> G["Rating Distribution Chart"]
    G --> G1["5 stars: X%"]
    G --> G2["4 stars: X%"]
    G --> G3["3 stars: X%"]
    G --> G4["2 stars: X%"]
    G --> G5["1 star: X%"]

    D --> H["Individual Feedback Cards"]
    H --> I["FeedbackCard Component"]
    I --> I1["Attendee Name (or 'Anonymous')"]
    I --> I2["Date Submitted"]
    I --> I3["Ratings Grid (3 categories)"]
    I --> I4["Comments (if provided)"]

    D --> J["Empty State"]
    J --> K["'No feedback yet' message"]
    K --> L["Encourage sharing event"]
```

---

## 9. Billing & Subscription Workflow

```mermaid
flowchart TD
    A["/billing"] --> B["Current Subscription Card"]
    B --> B1["Plan Name + Icon"]
    B --> B2["'Active' Badge"]
    B --> B3{Canceling?}
    B3 -->|Yes| B4["'Cancels {date}' in Red"]
    B --> B5["'Change Plan' Button"]
    B --> B6["'Manage in Stripe' Link"]

    B5 --> C["Plan Change Dialog"]
    C --> D["Plan Grid"]
    D --> D1["Attendee ($0)"]
    D --> D2["Organizer ($30/mo)"]
    D --> D3["Organization (Custom)"]

    D1 --> E{Current Plan?}
    D2 --> E
    D3 --> E
    E -->|Yes| F["'Current Plan' Label"]
    E -->|No - Higher| G["'Upgrade' Button"]
    E -->|No - Lower| H["'Downgrade' Button"]
    E -->|Enterprise| I["'Contact Sales' Button"]

    G --> J["handleUpgrade(planId)"]
    J --> K["createCheckoutSession API"]
    K --> L["Redirect to Stripe Checkout"]
    L --> M{Checkout Result}
    M -->|Success| N["/billing?checkout=success"]
    N --> O["Success Alert + Toast"]
    M -->|Canceled| P["/billing?checkout=canceled"]
    P --> Q["Info Toast: 'Checkout was canceled'"]

    A --> R["Usage Stats (Organizer Only)"]
    R --> R1["Events Created / Limit"]
    R --> R2["Certificates Issued / Limit"]
    R --> R3["Subscription Status"]
    R --> R4["Renewal Date"]

    A --> S["Plan Management"]
    S --> S1{Plan Status}
    S1 -->|Canceling| S2["'Reactivate' Button"]
    S1 -->|Active Organizer| S3["'Cancel Subscription' Button"]
    S3 --> S4["Confirmation Dialog"]

    A --> T["Payment History"]
    T --> T1["Date, Amount, Status, PDF Download"]
```

---

## 8. Profile & Settings Workflows

### Profile Page
```mermaid
flowchart TD
    A["/profile"] --> B["Account Information"]
    B --> B1["Email (read-only)"]
    B --> B2["Full Name (editable)"]
    B --> B3["'Save Changes' Button"]

    A --> C["Payment Methods"]
    C --> D{Has Methods?}
    D -->|Yes| E["Payment Methods List"]
    E --> E1["Card Brand"]
    E --> E2["Last 4 Digits"]
    E --> E3["Expiry Date"]
    E --> E4["Default Badge"]
    E --> E5{Expired?}
    E5 -->|Yes| E6["Expired Badge"]
    E --> E7["Delete Button"]
    E --> E8["'Add' Button"]

    D -->|No| F["Empty State"]
    F --> F1["'Add Payment Method' Button"]

    E8 --> G["PaymentMethodModal"]
    F1 --> G
    G --> H["Stripe Payment Form"]
    H --> I["Card Saved"]
    I --> J["Reload Billing Data"]

    A --> K["Subscription Status"]
    K --> K1["Plan Name"]
    K --> K2["Status Badge"]
    K --> K3{Trialing?}
    K3 -->|Yes| K4["Trial Countdown"]
    K3 -->|Yes| K5{Payment Method Set?}
    K5 -->|Yes| K6["'Billing set up' Message"]
    K5 -->|No| K7["'Add billing' Warning"]
```

---

## 10. Subscription Cancellation with Retention

```mermaid
flowchart TD
    A["/billing"] --> B["'Cancel Subscription' Button"]
    B --> C["Open CancellationModal"]

    C --> D["Step 1: Reason Selection"]
    D --> E["Select Cancellation Reason"]
    E --> E1["Too expensive"]
    E --> E2["Not using it enough"]
    E --> E3["Missing features"]
    E --> E4["Switching to competitor"]
    E --> E5["Technical issues"]
    E --> E6["Other"]

    E --> F["Optional: Additional feedback textarea"]
    F --> G["Click 'Continue'"]

    G --> H["Step 2: Retention Offer"]
    H --> I["'Before you go...' message"]
    I --> J["Retention Options Grid"]

    J --> K["Option 1: 50% Off"]
    K --> K1["3 months at half price"]
    K --> K2["'Apply Discount' button"]

    J --> L["Option 2: Pause Subscription"]
    L --> L1["Pause for 1-3 months"]
    L --> L2["'Pause Instead' button"]

    J --> M["Option 3: Free Onboarding"]
    M --> M1["1-on-1 setup call"]
    M --> M2["'Schedule Call' button"]

    K2 --> N["Apply retention offer"]
    L2 --> N
    M2 --> N
    N --> O["Close modal with success"]

    J --> P["'No thanks, continue canceling'"]
    P --> Q["Step 3: Confirm Cancellation"]

    Q --> R["What You'll Lose Section"]
    R --> R1["Event creation capability"]
    R --> R2["Registration management"]
    R --> R3["Certificate issuance"]
    R --> R4["Zoom integration"]

    Q --> S["Access Until Date"]
    S --> T["Billing period end date"]

    Q --> U["'Cancel My Subscription' Button"]
    U --> V["cancelSubscription API"]
    V --> W{Success?}
    W -->|Yes| X["Step 4: Confirmation"]
    W -->|No| Y["Error Toast"]

    X --> Z["Sad emoji illustration"]
    Z --> AA["'We're sorry to see you go'"]
    AA --> AB["Optional: Exit survey"]
    AB --> AC["'Close' button"]
    AC --> AD["Refresh billing page"]
    AD --> AE["Show 'Cancels on {date}' badge"]
```

---

## 11. Profile & Settings Workflows

### Profile Page
```mermaid
flowchart TD
    A["/profile"] --> B["Account Information"]
    B --> B1["Email (read-only)"]
    B --> B2["Full Name (editable)"]
    B --> B3["'Save Changes' Button"]

    A --> C["Change Password Section"]
    C --> C1["Current Password"]
    C --> C2["New Password"]
    C --> C3["Confirm New Password"]
    C --> C4["'Update Password' Button"]
    C4 --> C5["changePassword API"]
    C5 --> C6{Success?}
    C6 -->|Yes| C7["Success Toast"]
    C6 -->|No| C8["Error Toast"]

    A --> D["Email Notification Preferences"]
    D --> D1["Event Reminders Toggle"]
    D --> D2["Registration Confirmations Toggle"]
    D --> D3["Certificate Notifications Toggle"]
    D --> D4["Marketing Emails Toggle"]
    D --> D5["'Save Preferences' Button"]
```

### Payment Methods
```mermaid
flowchart TD
    A["/profile"] --> B["Payment Methods"]
    B --> C{Has Methods?}
    C -->|Yes| D["Payment Methods List"]
    D --> D1["Card Brand"]
    D --> D2["Last 4 Digits"]
    D --> D3["Expiry Date"]
    D --> D4["Default Badge"]
    D --> D5{Expired?}
    D5 -->|Yes| D6["Expired Badge"]
    D --> D7["Delete Button"]
    D --> D8["'Add' Button"]

    C -->|No| E["Empty State"]
    E --> E1["'Add Payment Method' Button"]

    D8 --> F["PaymentMethodModal"]
    E1 --> F
    F --> G["Stripe Payment Form"]
    G --> H["Card Saved"]
    H --> I["Reload Billing Data"]

    A --> J["Subscription Status"]
    J --> J1["Plan Name"]
    J --> J2["Status Badge"]
    J --> J3{Trialing?}
    J3 -->|Yes| J4["Trial Countdown"]
    J3 -->|Yes| J5{Payment Method Set?}
    J5 -->|Yes| J6["'Billing set up' Message"]
    J5 -->|No| J7["'Add billing' Warning"]
```

---

## 12. Organization Management Workflow

### Organization Creation
```mermaid
flowchart TD
    A["/organizations"] --> B["Organizations List"]
    B --> C["'Create Organization' Button"]
    C --> D["/organizations/new"]

    D --> E{URL Params?}
    E -->|"?from=account"| F["Upgrade Mode"]
    E -->|None| G["Fresh Creation Mode"]

    F --> H["Show Transfer Notice"]
    H --> H1["X Events"]
    H --> H2["Y Certificate Templates"]
    H --> I["getLinkableDataPreview API"]

    G --> J["Organization Form"]
    F --> J
    J --> J1["Organization Name (required)"]
    J --> J2["Description (rich text)"]
    J --> J3["Website URL"]
    J --> J4["Contact Email"]

    J --> K{Upgrade Mode?}
    K -->|Yes| L["createOrgFromAccount API"]
    L --> L1["transfer_data: true"]
    K -->|No| M["createOrganization API"]

    L1 --> N["Success Screen"]
    M --> N
    N --> N1["Green Checkmark"]
    N --> N2["'Organization Created!'"]
    N --> O["Redirect to /org/:slug"]
```

### Organization Dashboard
```mermaid
flowchart TD
    A["/org/:slug"] --> B["Organization Overview"]
    B --> B1["Org Name & Logo"]
    B --> B2["Members Count"]
    B --> B3["Events List"]
    B --> B4["Invitation Link"]
    B --> B5["Settings Button"]

    B5 --> C["/org/:slug/settings"]
    C --> C1["Organization Name"]
    C --> C2["Description"]
    C --> C3["Logo Upload"]
    C --> C4["Website URL"]
    C --> C5["Contact Info"]
    C --> C6["Stripe Connect Integration"]
    C --> C7["Billing Settings"]

    A --> D["Team Management Link"]
    D --> E["/org/:slug/team"]
    E --> E1["Team Members List"]
    E --> E2["Roles: Admin, Manager, Organizer"]
    E --> E3["Add Member by Email"]
    E --> E4["Remove Member"]
    E --> E5["Update Member Role"]

    A --> F["Courses Link"]
    F --> G["/org/:slug/courses"]
    G --> G1["Courses List"]
    G --> G2["'Create Course' Button"]
    G2 --> H["/org/:slug/courses/new"]
    H --> H1["Course Form"]
    H --> H2["Curriculum Builder"]
    H --> H3["Lessons/Modules Editor"]
```

---

## 13. Zoom Integration Workflow

```mermaid
flowchart TD
    A["Organizer Dashboard or Onboarding"] --> B["'Connect Zoom Account' Button"]
    B --> C["initiateZoomOAuth API"]
    C --> D["Get OAuth URL"]
    D --> E["Redirect to Zoom Login"]
    E --> F["User Authorizes App"]
    F --> G["/zoom/callback"]
    G --> H["Backend Creates ZoomIntegration"]

    H --> I{Check sessionStorage}
    I -->|"onboarding_redirect" exists| J["Return to Onboarding Step 3"]
    I -->|None| K["Redirect to /organizer/dashboard"]

    K --> L["Zoom Card Updated"]
    L --> L1["Connected Email Shown"]
    L --> L2["Animated Pulse Indicator"]
    L --> L3["'Disconnect' Button"]
    L --> L4["Meeting Count"]

    L3 --> M["disconnectZoom API"]
    M --> N["Status Reset to Disconnected"]

    subgraph "Auto-Meeting Creation"
        O["Event Creation - Step 4"]
        O --> P["'Auto-create Zoom' Checkbox"]
        P --> Q{Zoom Connected?}
        Q -->|Yes| R["Meeting Created on Save"]
        R --> S["zoom_join_url Stored"]
    end

    subgraph "Attendee Join"
        T["Attendee Dashboard"]
        T --> U["'Join Session' Button"]
        U --> V{Can Join?}
        V -->|Yes| W["Open zoom_join_url"]
        V -->|No - Not Started| X["Button Disabled"]
        V -->|No - No URL| X
    end
```

---

## 14. Certificate Verification Workflow

```mermaid
flowchart TD
    A["Public URL: /verify/:code"] --> B["No Auth Required"]
    B --> C["Fetch Certificate by Short Code"]
    C --> D{Certificate Found?}

    D -->|Yes| E["Display Certificate Details"]
    E --> E1["Recipient Name"]
    E --> E2["Event Title"]
    E --> E3["Date Issued"]
    E --> E4["CPD Credits"]
    E --> E5["Organizer Name"]
    E --> E6["Verification Status: ✓ Valid"]
    E --> E7["QR Code (optional)"]
    E --> F["'Download PDF' Button"]

    D -->|No| G["Certificate Not Found Error"]
```

---

## 15. Event Duplication Workflow

```mermaid
flowchart TD
    A["/events"] --> B["Events List Page"]
    B --> C["Event Row"]
    C --> D["Actions Dropdown Menu"]

    D --> E["View"]
    E --> F["/events/:slug"]

    D --> G["Edit"]
    G --> H["/events/:uuid/edit"]

    D --> I["Duplicate"]
    I --> J["Show Loading Spinner"]
    J --> K["duplicateEvent API"]

    K --> L{Success?}
    L -->|Yes| M["Success Toast: 'Event duplicated!'"]
    M --> N["Navigate to /events/:newUuid/edit"]
    N --> O["Pre-populated Event Wizard"]
    O --> O1["Title: 'Copy of [Original]'"]
    O --> O2["All settings copied"]
    O --> O3["Dates cleared (user must set)"]
    O --> O4["Status: Draft"]

    L -->|No| P["Error Toast"]
    P --> B

    D --> Q["Delete"]
    Q --> R["Open Confirmation Dialog"]
    R --> S["'Are you sure?' message"]
    S --> S1["Event title displayed"]
    S --> S2["Warning about registrations"]

    R --> T{User Choice}
    T -->|Cancel| U["Close Dialog"]
    T -->|Confirm Delete| V["deleteEvent API"]
    V --> W{Success?}
    W -->|Yes| X["Success Toast"]
    X --> Y["Remove from list"]
    W -->|No| Z["Error Toast"]
```

---

## 16. Complete Application Flow

```mermaid
flowchart TD
    subgraph "Public Access"
        A[Landing Page "/"] --> B[Event Discovery "/events/browse"]
        B --> C[Event Detail "/events/:id"]
        C --> D[Event Registration "/events/:id/register"]
        A --> E[Pricing "/pricing"]
        A --> F[Features "/features"]
        A --> G[Certificate Verify "/verify/:code"]
    end

    subgraph "Authentication"
        H[Login "/login"] --> I{Auth Success?}
        I -->|Yes| J{User Role?}
        I -->|No| H

        K[Signup "/signup"] --> L{Account Type?}
        L -->|Attendee| M[Create Attendee Account]
        L -->|Organizer| N[Create Organizer + Trial]
        M --> H
        N --> H
    end

    subgraph "Organizer Flow"
        J -->|Organizer| O{Onboarding Complete?}
        O -->|No| P[Onboarding Wizard]
        P --> Q[Organizer Dashboard]
        O -->|Yes| Q

        Q --> R[Create Event]
        Q --> S[Manage Events]
        Q --> T[Contacts]
        Q --> U[Reports]
        Q --> V[Certificates]
        Q --> W[Zoom Integration]
        Q --> X[Billing]
        Q --> Y[Organization Management]
    end

    subgraph "Attendee Flow"
        J -->|Attendee| Z[Attendee Dashboard]
        Z --> AA[My Registrations]
        Z --> AB[My Certificates]
        Z --> AC[CPD Tracking]
        Z --> AD[My Events]
        Z --> AE[Browse Events]
        Z --> AF[Profile]
    end

    subgraph "Shared"
        Q --> AG[Profile/Settings]
        Z --> AG
    end
```

---

## Navigation Structure

```mermaid
flowchart LR
    subgraph "Public Layout"
        A[Public Navigation]
        A --> A1[Home]
        A --> A2[Events]
        A --> A3[Pricing]
        A --> A4[Features]
        A --> A5[Login/Signup]
    end

    subgraph "Dashboard Layout - Organizer"
        B[Sidebar]
        B --> B1[Dashboard]
        B --> B2[Events]
        B --> B3[Contacts]
        B --> B4[Certificates]
        B --> B5[Reports]
        B --> B6[Billing]
        B --> B7[Settings]
        B --> B8[Organization]
    end

    subgraph "Dashboard Layout - Attendee"
        C[Sidebar]
        C --> C1[Dashboard]
        C --> C2[My Events]
        C --> C3[My Courses]
        C --> C4[CPD Tracking]
        C --> C5[Certificates]
        C --> C6[Registrations]
        C --> C7[Profile]
    end
```

---

## Route Protection

```mermaid
flowchart TD
    A[User Requests Route] --> B{Route Type?}

    B -->|Public| C[Allow Access]
    C --> D[Render with PublicLayout]

    B -->|Auth Pages| E{Already Logged In?}
    E -->|Yes| F[Redirect to Dashboard]
    E -->|No| G[Render with AuthLayout]

    B -->|Protected| H{Authenticated?}
    H -->|No| I[Redirect to Login]
    H -->|Yes| J{Role Check?}
    J -->|Pass| K[Render with DashboardLayout]
    J -->|Fail| L[Redirect to Appropriate Dashboard]

    subgraph "Public Routes"
        M1["/"]
        M2["/events/browse"]
        M3["/events/:id"]
        M4["/pricing"]
        M5["/verify/:code"]
    end

    subgraph "Auth Routes"
        N1["/login"]
        N2["/signup"]
        N3["/forgot-password"]
    end

    subgraph "Protected Routes"
        O1["/dashboard"]
        O2["/organizer/*"]
        O3["/events/create"]
        O4["/billing"]
        O5["/profile"]
    end
```
