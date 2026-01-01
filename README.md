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

## 📊 Pricing Tiers

| Plan | Price | Events/Month | Attendees | Certificates | Best For |
|------|-------|--------------|-----------|--------------|----------|
| **Attendee** | Free | - | - | - | Event participants |
| **Starter** | $49/mo | 10 | 100 | 100 | Solo professionals |
| **Professional** | $99/mo | 30 | 500 | 500 | Established trainers ⭐ |
| **Premium** | $199/mo | Unlimited | 2,000 | Unlimited | Power users |
| **Team** | $299/mo | Unlimited | Unlimited | Unlimited | Organizations (5 seats) |

**Trial**: 14-day free trial on all paid plans
**Annual Discount**: Save 17% with annual billing

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

**Detailed guide**: See [`docs/pricing-implementation/QUICK_START.md`](docs/pricing-implementation/QUICK_START.md)

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
    └── pricing-implementation/
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
- **[Quick Start Guide](docs/pricing-implementation/QUICK_START.md)** - Get running in 15 minutes
- **[Implementation Summary](docs/pricing-implementation/IMPLEMENTATION_SUMMARY.md)** - Complete overview
- **[CLI Commands](docs/CLI_COMMAND_TREE.md)** - All available commands

### Pricing & Billing
- **[Pricing Implementation](docs/pricing-implementation/PRICING_IMPLEMENTATION.md)** - Complete setup guide
- **[Stripe Admin Management](docs/pricing-implementation/STRIPE_ADMIN_SETUP.md)** - Manage pricing via Django Admin ⭐ NEW
- **[Stripe Setup](docs/pricing-implementation/STRIPE_SETUP_NEW_PRICING.md)** - Stripe configuration
- **[Upgrade/Downgrade](docs/pricing-implementation/UPGRADE_FIX_SUMMARY.md)** - Subscription management
- **[Workflow Audit](docs/pricing-implementation/UPGRADE_WORKFLOW_AUDIT.md)** - Technical deep dive
- **[Stripe Admin & Promo Codes](docs/pricing-implementation/STRIPE_ADMIN_AND_PROMO_CODES.md)** - Advanced features

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
- Multi-tier pricing with usage limits
- 14-day free trial (no credit card required)
- Stripe integration for payments
- Automatic proration on upgrades
- Team plans with per-seat billing

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

### Current Version (v2.0) ✅
- ✅ Multi-tier pricing with 5 tiers
- ✅ Subscription upgrade/downgrade
- ✅ Certificate limit enforcement
- ✅ 14-day trial period
- ✅ Annual billing with discount

### Upcoming (v2.1)
- [ ] Proration preview before upgrade
- [ ] Plan comparison modal
- [ ] Upgrade analytics dashboard
- [ ] Smart upgrade prompts at limits

### Future (v3.0)
- [ ] Mobile app (React Native)
- [ ] Advanced analytics & reporting
- [ ] White-label capabilities
- [ ] API marketplace
- [ ] Third-party integrations (MS Teams, etc.)

---

## 📝 Recent Updates

### December 29, 2025 - v2.0 Release

**New Pricing Structure** 🎯
- Implemented 5-tier pricing (Attendee, Starter, Professional, Premium, Team)
- Added annual billing with 17% discount
- Changed trial period from 30 to 14 days
- Research-backed pricing aligned with market

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
- Read [Quick Start](docs/pricing-implementation/QUICK_START.md)
- Review [Implementation Summary](docs/pricing-implementation/IMPLEMENTATION_SUMMARY.md)

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

[Get Started](docs/pricing-implementation/QUICK_START.md) • [Documentation](docs/) • [Report Bug](../../issues)

</div>
