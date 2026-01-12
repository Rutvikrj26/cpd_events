# CPD Events Platform (Accredit)

> A comprehensive SaaS platform for managing Continuing Professional Development (CPD) events with integrated certificate issuance, payment processing, and learning management.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-18.2+-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.2+-blue.svg)](https://www.typescriptlang.org/)

---

## 🎯 Overview

**CPD Events** is a production-ready SaaS platform that enables organizations to:
- Create and manage virtual/hybrid CPD events
- Automatically track attendance via Zoom integration
- Issue verifiable digital certificates
- Manage subscriptions and payments via Stripe
- Deliver self-paced courses with full LMS capabilities

### Key Features

- ✅ **Multi-format events**: Online (Zoom), in-person, hybrid
- ✅ **Automatic attendance tracking**: Real-time via Zoom webhooks
- ✅ **Certificate management**: PDF generation with custom templates
- ✅ **Flexible billing**: Multi-tier subscriptions with 14-day trial
- ✅ **Learning Management**: Courses, modules, assignments, grading
- ✅ **Team collaboration**: Organizations with role-based access
- ✅ **Guest registration**: Attendees can participate without accounts

---

## 📊 Pricing & Plans

Pricing is configured in Django Admin (Stripe Products/Prices) and reflected on the public pricing page.

### Current Plans

**Individual Plans:**
- **Attendee** (Free) - Attend events and courses
- **Organizer** (Paid) - Create events, 30/month limit, 500 max attendees
- **LMS** (Paid) - Create courses, 30/month limit

**Organization Plan:**
- **Organization** ($199/month base)
  - Includes 1 Admin (full organizer + course manager capabilities)
  - Unlimited events and courses
  - Additional seats: $129/month per seat
  - Unlimited Course Instructors (free)

Trials (default 30 days), limits, and pricing are all managed in the database per plan.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (or use Docker)
- Stripe account (for payments)
- Zoom account (for virtual events)

### Option 1: Docker (Recommended)

```bash
# Install CLI tool
cd cli
pipx install -e .

# Start all services with Docker
accredit docker up --build -d

# Initialize environment (migrations, buckets)
accredit docker init

# View logs
accredit docker logs -f

# Access application
open http://localhost:8000      # Backend
open http://localhost:5173      # Frontend
```

### Option 2: Local Development

```bash
# Install CLI tool
cd cli
pipx install -e .

# Setup and start local servers
accredit local setup    # Installs dependencies
accredit local up       # Starts backend + frontend

# Access application
open http://localhost:8000      # Backend
open http://localhost:5173      # Frontend
```

**Detailed guide**: See [`docs/ADMIN_PANEL_GUIDE.md`](docs/ADMIN_PANEL_GUIDE.md)

---

## 📁 Project Structure

```
cpd_events/
├── backend/              # Django REST API
│   ├── src/
│   │   ├── accounts/     # User authentication & profiles
│   │   ├── billing/      # Stripe subscriptions & payments
│   │   ├── certificates/ # Certificate generation & management
│   │   ├── events/       # Event creation & management
│   │   ├── registrations/# Registration & attendance tracking
│   │   ├── learning/     # LMS (courses, modules, assignments)
│   │   ├── organizations/# Multi-tenant organizations
│   │   ├── integrations/ # Zoom, email, webhooks
│   │   ├── feedback/     # Event feedback & surveys
│   │   └── promo_codes/  # Discount codes
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/             # React + TypeScript SPA
│   ├── src/
│   │   ├── api/          # API client layer
│   │   ├── components/   # Reusable components
│   │   ├── pages/        # Page components
│   │   └── lib/          # Utilities
│   └── package.json
│
├── cli/                  # Deployment CLI tool ⭐
│   ├── accredit/         # CLI commands
│   │   └── commands/     # Local, Docker, Cloud
│   ├── docker-compose.yml
│   └── pyproject.toml
│
├── infra/                # Infrastructure as Code
│   └── gcp/              # Terraform for Google Cloud
│
└── docs/                 # Documentation
    └── legacy/           # Archived pricing docs
```

---

## 🛠️ Technology Stack

### Backend
- **Framework**: Django 4.x + Django REST Framework
- **Database**: PostgreSQL (production) / SQLite (development)
- **Authentication**: JWT tokens via djangorestframework-simplejwt
- **Payments**: Stripe (Subscriptions + Connect)
- **Integrations**: Zoom OAuth, webhooks
- **Cloud**: Google Cloud Platform (Cloud Run, Cloud SQL, Cloud Storage)
- **Tasks**: GCP Cloud Tasks (async processing)

### Frontend
- **Framework**: React 18 + TypeScript
- **Build**: Vite
- **Routing**: React Router v6
- **State**: TanStack Query (React Query) + Context API
- **UI**: Radix UI + Tailwind CSS
- **Forms**: React Hook Form + Zod validation
- **Payments**: Stripe.js + Stripe Elements

### DevOps
- **Containerization**: Docker + Docker Compose
- **IaC**: Terraform
- **CLI**: Custom Python CLI tool (`accredit`)

---

## 📚 Documentation

### Getting Started
- **[Environment Setup](docs/ENV_SETUP_SUMMARY.md)** - Configuration guide
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Local + cloud workflows
- **[CLI Commands](docs/CLI_COMMAND_TREE.md)** - All available commands

### Pricing & Billing
- **[Admin Pricing Guide](docs/ADMIN_PANEL_GUIDE.md)** - Manage plans, pricing, and trials

### Infrastructure & Deployment
- **[Infrastructure Summary](docs/INFRASTRUCTURE_SUMMARY.md)** - GCP architecture
- **[Docker Setup](docs/DOCKER_CHANGES_SUMMARY.md)** - Container setup
- **[Environment Setup](docs/ENV_SETUP_SUMMARY.md)** - Configuration guide

---

## 🎨 Key Features Deep Dive

### Event Management
- Create single or multi-session events
- Support for online (Zoom), in-person, and hybrid formats
- Custom registration forms with validation
- Capacity management with automatic waitlist
- Event duplication and templates

### Attendance Tracking
- **Automatic**: Zoom webhooks capture join/leave events
- **Manual**: In-person check-in for hybrid events
- **Smart matching**: Email-based attendee matching
- **Eligibility calculation**: Automatic certificate eligibility

### Certificate System
- Custom PDF templates with versioning
- Automatic generation on eligibility
- QR codes for verification
- Public verification portal
- Email delivery with tracking

### Billing & Subscriptions
- Multi-plan pricing with usage limits
- Trials configured per plan
- Stripe integration for payments
- Automatic proration on upgrades
- Organization plans with per-seat billing

---

## 🔧 CLI Commands

### Docker Commands
```bash
accredit docker up -d              # Start all services
accredit docker init               # Initialize (migrations, buckets)
accredit docker logs -f            # View logs
accredit docker down               # Stop services
accredit docker ps                 # List running containers
```

### Local Development
```bash
accredit local setup               # Install dependencies
accredit local up                  # Start backend + frontend
accredit local logs                # View logs
accredit local down                # Stop servers
```

### Cloud Deployment (GCP)
```bash
accredit cloud infra apply --env prod    # Deploy infrastructure
accredit cloud backend deploy --env prod # Deploy backend
accredit cloud frontend deploy --env prod # Deploy frontend
```

**Full CLI reference**: [`docs/CLI_COMMAND_TREE.md`](docs/CLI_COMMAND_TREE.md)

---

## 🧪 Testing

### Backend Tests
```bash
cd backend
python manage.py test
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Test Subscription Flow
```bash
# Use Stripe test cards
Card: 4242 4242 4242 4242
Exp: Any future date
CVC: Any 3 digits
```

---

## 🚢 Deployment

### Development
```bash
accredit docker up --build -d
accredit docker init
```

### Production (Google Cloud)
```bash
# Deploy infrastructure
accredit cloud infra apply --env prod

# Deploy application
accredit cloud backend deploy --env prod
accredit cloud frontend deploy --env prod
```

See [`cli/DEPLOYMENT.md`](cli/DEPLOYMENT.md) for detailed deployment guide.

---

## 📊 Monitoring & Analytics

### Key Metrics
- Trial-to-paid conversion rate
- Plan distribution (which tiers are popular)
- Upgrade/downgrade patterns
- Event creation trends
- Certificate issuance volume

### Recommended Tools
- **Errors**: Sentry
- **Infrastructure**: Google Cloud Monitoring
- **Analytics**: Google Analytics / Mixpanel
- **Payments**: Stripe Dashboard

---

## 🔒 Security

- JWT-based authentication with refresh tokens
- Encrypted OAuth tokens (Fernet encryption)
- Stripe webhook signature validation
- Zoom webhook signature validation
- CORS configuration
- Rate limiting on auth endpoints
- GDPR-compliant user anonymization

---

## 🗺️ Roadmap

### Current Version (v2.1) ✅
- ✅ Multi-tier pricing (Attendee, Organizer, LMS, Organization)
- ✅ Subscription upgrade/downgrade
- ✅ Database-driven plan limits and pricing
- ✅ Configurable trial periods
- ✅ Annual billing support
- ✅ Organization team management with role-based access
- ✅ Full LMS with courses, modules, assignments

### Upcoming (v2.2)
- [ ] Refund processing automation
- [ ] Payout reconciliation dashboard
- [ ] Payment retry logic
- [ ] Trial expiration automation
- [ ] Enhanced email notifications

### Future (v3.0)
- [ ] Mobile app (React Native)
- [ ] Advanced analytics & reporting
- [ ] White-label capabilities
- [ ] API marketplace
- [ ] Third-party integrations (MS Teams, etc.)

---

## 📝 Recent Updates

### January 2026 - v2.1 Release

**Pricing Structure** 🎯
- 4-tier pricing: Attendee (Free), Organizer, LMS, Organization
- Organization plan: $199/month base + $129/seat for additional organizers/course managers
- Configurable trial periods (default 30 days)
- Database-driven pricing via Stripe Products
- Annual billing support with Stripe integration

**Critical Bug Fixes** 🐛
- Fixed broken subscription upgrade/downgrade workflow
- Added proper Stripe subscription update methods
- Implemented certificate limit enforcement
- Added proration support for upgrades

**Documentation** 📚
- Created 6 comprehensive implementation guides
- Added quick start guide (15 minutes)
- Documented complete upgrade workflow
- Added Stripe setup instructions

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push and open a Pull Request

**Code Style**: Black (Python), Prettier (TypeScript)

---

## 📞 Support

### Documentation
- Check [`docs/`](docs/) for detailed guides
- Read the [Admin Pricing Guide](docs/ADMIN_PANEL_GUIDE.md)
- Review [Environment Setup](docs/ENV_SETUP_SUMMARY.md)

### Issues
- GitHub Issues: Report bugs or request features
- GitHub Discussions: Ask questions

---

## 📈 Performance

- API response time: <200ms (p95)
- Page load time: <2s (Lighthouse score >90)
- Concurrent users: 1000+ (with auto-scaling)
- Database: Optimized with indexes and caching

---

## 🌟 Acknowledgments

- Built with [Django](https://www.djangoproject.com/) and [React](https://reactjs.org/)
- UI from [Radix UI](https://www.radix-ui.com/) and [shadcn/ui](https://ui.shadcn.com/)
- Icons from [Lucide](https://lucide.dev/)
- Powered by [Stripe](https://stripe.com/) and [Zoom](https://zoom.us/)

---

<div align="center">

**Built with ❤️ for the CPD community**

[Get Started](docs/ENV_SETUP_SUMMARY.md) • [Documentation](docs/) • [Report Bug](../../issues)

</div>
