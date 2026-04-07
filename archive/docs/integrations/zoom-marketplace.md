# Accredit - Zoom Integration App Review

**Purpose**: Accredit automates CPD (Continuing Professional Development) event management with Zoom integration for virtual events, attendance tracking, and certificate issuance.

**Core Features**:
- Auto-create Zoom meetings when organizers schedule events
- Real-time attendance tracking via webhooks
- Automated certificate generation for qualified attendees
- Multi-session event support with per-session tracking

**OAuth Details**:
- Scopes: meeting:write, meeting:read, user:read, webinar:write, webinar:read
- Flow: Standard OAuth 2.0, encrypted token storage (Fernet/PostgreSQL)
- User connects via Settings > Integrations > "Connect Zoom"
- Automatic token refresh, user-initiated disconnect

**Webhooks Used**:
- participant_joined/left: Track attendance timestamps, calculate duration
- meeting.ended: Trigger certificate generation
- meeting.started: Send participant reminders
- Signature verification via ZOOM_WEBHOOK_SECRET
- Async processing (Google Cloud Tasks) for reliability

**Data Flow**:
Event created → Zoom meeting auto-generated → Join URL shared → Participant joins/leaves (webhooks track time) → Meeting ends → Certificates issued to attendees meeting threshold → Email with PDF + QR code

**Security**:
- Encrypted OAuth tokens at rest
- Webhook signature verification
- No recording/content access - attendance only
- PII: name/email (collected during registration)
- GDPR compliant, right to deletion
- Users disconnect anytime (tokens deleted)

**Tech**: Django 6 on Google Cloud Run, PostgreSQL, Cloud Tasks for webhooks, rate limiting with exponential backoff

**Testing**: Sign up → Connect Zoom → Create event (select "Online") → Meeting auto-created → Join/leave as participant → End meeting → Verify certificate

**Use Cases**: Professional associations (legal, medical, accounting) CPD tracking, corporate training certifications, educational completions

**Support**: support@accredit.store
