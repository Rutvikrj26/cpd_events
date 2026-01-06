# CPD Events Platform - Architecture

## High-Level Infrastructure Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    INTERNET                                          │
└─────────────────────────────────────┬───────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              CLOUD LOAD BALANCER                                     │
│                        (HTTPS, SSL Certificates, CDN)                                │
└───────────────┬─────────────────────────────────────────────┬───────────────────────┘
                │                                             │
                ▼                                             ▼
┌───────────────────────────────────┐       ┌────────────────────────────────────────┐
│         FIREBASE HOSTING          │       │            CLOUD RUN                    │
│         (Web Frontend)            │       │         (Django API)                    │
│                                   │       │                                         │
│  • Next.js/React SPA              │       │  • REST API endpoints                   │
│  • Static assets                  │       │  • WebSocket connections                │
│  • CDN-cached                     │       │  • Task handler endpoints               │
│                                   │       │  • Auto-scaling (0 to N)                │
└───────────────────────────────────┘       └──────────────┬──────────────────────────┘
                                                           │
                    ┌──────────────────────────────────────┼──────────────────────────────────────┐
                    │                                      │                                      │
                    ▼                                      ▼                                      ▼
┌───────────────────────────────┐       ┌───────────────────────────────┐       ┌───────────────────────────────┐
│        CLOUD SQL              │       │       CLOUD STORAGE           │       │       CLOUD TASKS             │
│       (PostgreSQL)            │       │         (GCS)                 │       │      (Task Queue)             │
│                               │       │                               │       │                               │
│  • Primary database           │       │  • Certificate PDFs           │       │  • Async job processing       │
│  • Private IP (VPC)           │       │  • Event recordings           │       │  • GDPR exports               │
│  • Automated backups          │       │  • User uploads               │       │  • Email sending              │
│  • Read replicas (prod)       │       │  • Signed URLs                │       │  • Certificate generation     │
│                               │       │                               │       │  • Rate limiting              │
└───────────────────────────────┘       └───────────────────────────────┘       └───────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SUPPORTING SERVICES                                     │
├───────────────────────────┬───────────────────────────┬─────────────────────────────┤
│                           │                           │                             │
│     SECRET MANAGER        │    CLOUD SCHEDULER        │     CLOUD LOGGING           │
│                           │                           │                             │
│  • Database credentials   │  • Scheduled tasks        │  • Application logs         │
│  • API keys               │  • Daily reports          │  • Error tracking           │
│  • JWT secrets            │  • Cleanup jobs           │  • Audit trails             │
│  • Zoom credentials       │  • Certificate expiry     │  • Metrics                  │
│                           │    checks                 │                             │
└───────────────────────────┴───────────────────────────┴─────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL INTEGRATIONS                                   │
├───────────────────────────────────┬─────────────────────────────────────────────────┤
│                                   │                                                 │
│            ZOOM API               │              EMAIL SERVICE                      │
│                                   │           (SMTP provider: Brevo/Mailgun)        │
│  • Meeting creation               │                                                 │
│  • Webhook events                 │  • Transactional emails                         │
│  • Attendance data                │  • Event reminders                              │
│  • Recording access               │  • Certificate delivery                         │
│                                   │                                                 │
└───────────────────────────────────┴─────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### 1. User Registration & Event Signup

```
User                   Frontend              API (Cloud Run)           Database
 │                        │                        │                      │
 ├──── Sign Up ──────────►│                        │                      │
 │                        ├──── POST /auth/signup──►│                      │
 │                        │                        ├─── Create User ──────►│
 │                        │                        │◄── User Created ──────┤
 │                        │                        │                      │
 │                        │                        ├─── Link Guest Regs ──►│
 │                        │◄─── JWT Token ─────────┤                      │
 │◄─── Logged In ─────────┤                        │                      │
 │                        │                        │                      │
 ├─── Register Event ────►│                        │                      │
 │                        ├─ POST /events/{id}/register ─►│               │
 │                        │                        ├── Create Registration─►│
 │                        │◄── Registration ───────┤                      │
 │◄── Confirmation ───────┤                        │                      │
```

### 2. Async Task Processing (GDPR Export)

```
User                   API (Cloud Run)         Cloud Tasks           Task Handler
 │                        │                        │                      │
 ├─ Request Data Export ─►│                        │                      │
 │                        ├── Enqueue Task ───────►│                      │
 │                        │                        │                      │
 │◄── "Processing" ───────┤                        │                      │
 │                        │                        ├── HTTP POST ─────────►│
 │                        │                        │                      │
 │                        │                        │    ┌─ Generate Export │
 │                        │                        │    │  Upload to GCS   │
 │                        │                        │    │  Send Email      │
 │                        │                        │    └──────────────────│
 │                        │                        │                      │
 │◄───── Email with download link ─────────────────┼──────────────────────┤
```

### 3. Certificate Issuance

```
Organizer              API (Cloud Run)           Cloud Tasks          GCS
    │                        │                        │                │
    ├─ Issue Certificates ──►│                        │                │
    │                        ├── For each eligible:   │                │
    │                        │   Enqueue PDF task ───►│                │
    │◄── "Processing X certs"┤                        │                │
    │                        │                        ├── Generate PDF──►│ (upload)
    │                        │                        ├── Update DB      │
    │                        │                        ├── Send Email     │
    │                        │                        │                │
```

---

## Environment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                 GCP PROJECT: cpd-events                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│   ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐       │
│   │     DEVELOPMENT     │   │       STAGING       │   │     PRODUCTION      │       │
│   │                     │   │                     │   │                     │       │
│   │ Cloud Run (1 inst)  │   │ Cloud Run (1-3)     │   │ Cloud Run (2-10)    │       │
│   │ Cloud SQL (small)   │   │ Cloud SQL (small)   │   │ Cloud SQL (HA)      │       │
│   │ Cloud Tasks (dev)   │   │ Cloud Tasks (stg)   │   │ Cloud Tasks (prod)  │       │
│   │ GCS (dev bucket)    │   │ GCS (stg bucket)    │   │ GCS (prod bucket)   │       │
│   │                     │   │                     │   │                     │       │
│   │ api-dev.cpdevents   │   │ api-stg.cpdevents   │   │ api.cpdevents.com   │       │
│   └─────────────────────┘   └─────────────────────┘   └─────────────────────┘       │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SECURITY LAYERS                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  1. NETWORK LAYER                                                                    │
│     ├── Cloud Armor (DDoS protection, WAF rules)                                     │
│     ├── VPC with private subnets                                                     │
│     └── Cloud SQL private IP (no public access)                                      │
│                                                                                      │
│  2. AUTHENTICATION                                                                   │
│     ├── JWT tokens (short-lived access, refresh rotation)                            │
│     ├── Rate limiting on auth endpoints                                              │
│     └── Password hashing (bcrypt/argon2)                                             │
│                                                                                      │
│  3. AUTHORIZATION                                                                    │
│     ├── Role-based access (attendee, organizer, admin)                               │
│     ├── Object-level permissions (event ownership)                                   │
│     └── Internal endpoints protected by Cloud Tasks auth                             │
│                                                                                      │
│  4. DATA PROTECTION                                                                  │
│     ├── Encryption at rest (Cloud SQL, GCS)                                          │
│     ├── Encryption in transit (TLS 1.3)                                              │
│     ├── Signed URLs for file access                                                  │
│     └── PII encryption (email, phone with app-level encryption)                      │
│                                                                                      │
│  5. SECRETS MANAGEMENT                                                               │
│     ├── All secrets in Secret Manager                                                │
│     ├── IAM-based access control                                                     │
│     └── Automatic rotation where supported                                           │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Cost Estimation (Monthly)

| Service | Dev | Staging | Production |
|---------|-----|---------|------------|
| Cloud Run | ~$5 | ~$20 | ~$100-300 |
| Cloud SQL | ~$10 | ~$30 | ~$150-300 |
| Cloud Storage | ~$1 | ~$5 | ~$20-50 |
| Cloud Tasks | ~$0 | ~$0 | ~$5-20 |
| Cloud Load Balancer | ~$20 | ~$20 | ~$20 |
| Secret Manager | ~$0 | ~$0 | ~$1 |
| **Total** | **~$36** | **~$75** | **~$300-700** |

*Estimates based on moderate usage. Production scales with traffic.*
