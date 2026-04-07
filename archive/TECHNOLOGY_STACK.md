# Technology Stack Overview

## Backend
- **Framework**: Django 6.x + Django REST Framework 3.15+
- **Auth**: JWT via djangorestframework-simplejwt 5.4+
- **Database**: PostgreSQL 15+ (Google Cloud SQL)
- **Storage**: Google Cloud Storage (3 buckets: media, certificates, CDN)
- **Payments**: Stripe API 8.x (Checkout, Billing, webhooks)
- **Video**: Zoom OAuth API (meetings, attendance webhooks)
- **Email**: Brevo via django-anymail 14.x
- **Async**: Google Cloud Tasks (certificates, emails, webhooks)
- **PDF**: ReportLab 4.x + Pillow 10.x
- **Docs**: drf-yasg (OpenAPI, Swagger UI)
- **Security**: cryptography 46.x, django-cors-headers
- **Server**: Gunicorn 21.x + WhiteNoise 6.x
- **Testing**: pytest 8.x, Factory Boy, Faker
- **Quality**: Black, Ruff, MyPy + django-stubs

## Frontend
- **Framework**: React 18.2 + TypeScript 5.2+
- **Build**: Vite 5.x (HMR, Rollup)
- **Routing**: React Router v6.20+
- **State**: TanStack Query 5.90+ + Context API
- **HTTP**: Axios 1.6+
- **Forms**: React Hook Form 7.68+ + Zod 4.2+
- **UI**: Radix UI (accessible components)
- **Styling**: Tailwind CSS 3.3+ + CVA 0.7+
- **Animation**: Framer Motion 12.23+
- **Payments**: Stripe.js 8.6+ + @stripe/react-stripe-js 5.4+
- **Rich Text**: React Quill 2.0
- **Dates**: date-fns 4.1 + react-day-picker 9.13
- **Maps**: @react-google-maps/api 2.20+
- **PDF**: react-pdf 10.2
- **Icons**: Lucide React 0.294
- **Notifications**: Sonner 2.0
- **JWT**: jwt-decode 4.0

## Infrastructure
- **IaC**: Terraform (Cloud Run, Cloud SQL, VPC, CDN)
- **CLI**: Custom Python CLI (deployment automation)
- **Containers**: Docker + Docker Compose
- **Compute**: Google Cloud Run (auto-scale 0-10)
- **CDN**: Cloud CDN + HTTPS Load Balancer
- **CI/CD**: GitHub Actions
- **Monitoring**: Cloud Logging, Monitoring, Trace
