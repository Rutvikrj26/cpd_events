# CPD Events Platform - Backend

Django REST Framework-based backend API for the CPD Events platform, providing comprehensive event management, user registration, certificate generation, and learning management system capabilities.

## API Architecture

The backend is built using Django REST Framework (DRF) and follows RESTful API design principles with the following key characteristics:

- **Modular Architecture**: Organized into Django apps by domain (accounts, events, registrations, etc.)
- **Token Authentication**: JWT-based authentication for API access
- **Permission System**: Role-based access control (RBAC)
- **Async Processing**: Background tasks handled via Cloud Tasks
- **API Versioning**: Support for multiple API versions

## Module Structure

The backend is organized into Django apps, each handling a specific domain:

### Core Apps

#### `accounts/`
User management and authentication
- User model (extends Django User)
- Organization management
- User profiles and preferences
- Role-based permissions
- Multi-organization support

**Key Models**: `User`, `Organization`, `OrganizationMembership`, `UserProfile`

#### `events/`
Event and course management
- Event creation and management
- Course catalog
- Multi-session/hybrid events
- Attendance tracking
- Zoom integration

**Key Models**: `Event`, `Course`, `Session`, `Attendance`, `ZoomMeeting`

#### `registrations/`
Event registration and enrollment
- Registration processing
- Payment integration (Stripe)
- Cancellation and refunds
- Waitlist management
- Registration status tracking

**Key Models**: `Registration`, `Payment`, `Refund`, `Waitlist`

#### `certificates/`
Certificate generation and verification
- Automated certificate creation
- PDF generation
- Certificate verification
- Badge integration
- Email delivery

**Key Models**: `Certificate`, `CertificateTemplate`, `Badge`

#### `contacts/`
Contact and communication management
- Contact database
- Email campaigns
- Communication history
- Subscriber management

**Key Models**: `Contact`, `EmailCampaign`, `CommunicationLog`

#### `learning/`
Learning management system features
- Course progress tracking
- Learning paths
- Assessments and quizzes
- Completion tracking
- CPD credit management

**Key Models**: `Enrollment`, `Progress`, `Assessment`, `CPDCredit`

#### `integrations/`
Third-party integrations
- Zoom API integration
- Stripe payment processing
- Email service providers
- Webhook handling

**Key Models**: `ZoomWebhook`, `StripeWebhook`, `Integration`

### Supporting Apps

#### `core/`
Shared utilities and base classes
- Base models and managers
- Common utilities
- Shared constants
- Custom exceptions

#### `services/`
Business logic layer
- Service classes for complex operations
- Email service
- Payment processing service
- Certificate generation service
- Notification service

## Database Models

### Key Relationships

```
User (1) ----< (N) OrganizationMembership (N) >---- (1) Organization
User (1) ----< (N) Registration (N) >---- (1) Event
Registration (1) ----< (1) Payment
Registration (1) ----< (1) Certificate
Event (1) ----< (N) Session (for multi-session events)
User (1) ----< (N) Enrollment (N) >---- (1) Course
Enrollment (1) ----< (N) Progress
```

### Database Schema
See [docs/api/data-models.md](../docs/api/data-models.md) for complete data model specifications.

## Authentication & Authorization

### Authentication Methods
- **Token Authentication**: JWT tokens for API access
- **Session Authentication**: Django sessions for admin panel
- **OAuth**: Social login integration (Google, Microsoft)

### Permission Levels
- **SuperAdmin**: Full system access
- **OrgAdmin**: Organization-level management
- **OrgStaff**: Limited organization operations
- **User**: Standard user access
- **Anonymous**: Public access to certain endpoints

### Role-Based Access Control
Permissions are managed through Django's built-in permission system with custom permission classes for API endpoints.

## Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis (for caching)
- Docker (optional)

### Local Development

#### 1. Virtual Environment Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 3. Environment Configuration
Create a `.env` file in the backend directory:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=cpd_events
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

# Zoom
ZOOM_CLIENT_ID=your-zoom-client-id
ZOOM_CLIENT_SECRET=your-zoom-client-secret

# Cloud Tasks (for local dev, can be disabled)
CLOUD_TASKS_ENABLED=False
```

#### 4. Database Setup
```bash
# Create database
createdb cpd_events

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load initial data (optional)
python manage.py loaddata initial_data.json
```

#### 5. Run Development Server
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

### Docker Development

```bash
# From the cli/ directory
docker-compose up

# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser
```

## Testing Approach

### Unit Tests
Test individual models, serializers, and utility functions.

```bash
# Run all tests
python manage.py test

# Run tests for specific app
python manage.py test accounts

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Integration Tests
Test API endpoints and business logic interactions.

### Test Coverage
Aim for >80% code coverage across the backend.

## API Endpoints

### Key Endpoint Groups

#### Authentication (`/api/auth/`)
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/register/` - User registration
- `POST /api/auth/password-reset/` - Password reset

#### Events (`/api/events/`)
- `GET /api/events/` - List events
- `GET /api/events/{id}/` - Event details
- `POST /api/events/` - Create event (admin)
- `PATCH /api/events/{id}/` - Update event (admin)
- `DELETE /api/events/{id}/` - Delete event (admin)

#### Registrations (`/api/registrations/`)
- `GET /api/registrations/` - List user registrations
- `POST /api/registrations/` - Create registration
- `GET /api/registrations/{id}/` - Registration details
- `POST /api/registrations/{id}/cancel/` - Cancel registration

#### Certificates (`/api/certificates/`)
- `GET /api/certificates/` - List user certificates
- `GET /api/certificates/{id}/` - Certificate details
- `GET /api/certificates/{id}/download/` - Download PDF
- `GET /api/certificates/verify/{code}/` - Verify certificate

#### Courses (`/api/courses/`)
- `GET /api/courses/` - List courses
- `GET /api/courses/{id}/` - Course details
- `POST /api/courses/{id}/enroll/` - Enroll in course

See [docs/api/](../docs/api/) for complete API documentation.

## Background Tasks

Asynchronous tasks are handled using Google Cloud Tasks:

### Task Types
- **Email Delivery**: Send transactional emails
- **Certificate Generation**: Generate PDFs asynchronously
- **Payment Processing**: Handle payment webhooks
- **Zoom Sync**: Sync attendance from Zoom
- **Notifications**: Send push notifications

### Task Management
Tasks are created in the service layer and processed by Cloud Tasks workers.

## Services Layer

Business logic is encapsulated in service classes located in the `services/` app:

### Key Services
- `EmailService`: Email sending and templates
- `PaymentService`: Stripe integration
- `CertificateService`: Certificate generation
- `ZoomService`: Zoom API integration
- `NotificationService`: User notifications

### Service Usage Example
```python
from services.email_service import EmailService

# Send registration confirmation
EmailService.send_registration_confirmation(registration)
```

## Configuration

### Settings Structure
```
backend/settings/
├── base.py         # Base settings
├── development.py  # Development overrides
├── production.py   # Production configuration
└── testing.py      # Test configuration
```

### Environment-Specific Settings
Load settings based on `DJANGO_ENV` environment variable:
- `development` - Local development
- `production` - Production deployment
- `testing` - Test environment

## Deployment

### Production Deployment

The backend is deployed to Google Cloud Run:

```bash
# Using the accredit CLI
accredit cloud backend build --env prod
accredit cloud backend deploy --env prod

# Manual deployment
gcloud builds submit --tag gcr.io/PROJECT_ID/cpd-backend:latest
gcloud run deploy cpd-events-prod --image gcr.io/PROJECT_ID/cpd-backend:latest
```

See [docs/deployment/](../docs/deployment/) for detailed deployment instructions.

### Database Migrations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Production migrations via Cloud Run
gcloud run jobs execute migrate-db --region=us-central1
```

## Monitoring & Logging

### Logging
- Django logging to Cloud Logging
- Structured logging for better searchability
- Error tracking with Sentry (optional)

### Monitoring
- Cloud Monitoring for metrics
- API response times
- Database query performance
- Task queue health

## Documentation

### Related Documentation
- [API Specifications](../docs/api/) - Complete API documentation
- [Data Models](../docs/api/data-models.md) - Database schema
- [Architecture Overview](../docs/architecture/overview.md) - System architecture
- [Backend Gaps](../docs/gaps/backend-gaps.md) - Known gaps and improvements
- [Setup Guide](../docs/setup/) - Environment setup

## Contributing

When adding new features:
1. Create a new branch from `main`
2. Write tests for new functionality
3. Follow Django best practices
4. Update API documentation
5. Run tests and ensure they pass
6. Submit a pull request

### Code Style
- Follow PEP 8 style guide
- Use Black for code formatting
- Use isort for import sorting
- Run linting with flake8

```bash
# Format code
black .
isort .

# Lint
flake8
```

## Technology Stack

- **Framework**: Django 5.0
- **API**: Django REST Framework 3.14
- **Database**: PostgreSQL 15
- **Cache**: Redis
- **Task Queue**: Google Cloud Tasks
- **Storage**: Google Cloud Storage
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Payment**: Stripe
- **Video**: Zoom API
- **PDF Generation**: ReportLab

See [TECHNOLOGY_STACK.md](../TECHNOLOGY_STACK.md) for complete technology overview.

## Troubleshooting

### Common Issues

#### Database Connection Errors
- Ensure PostgreSQL is running
- Check database credentials in `.env`
- Verify database exists: `psql -l`

#### Migration Conflicts
- Resolve migration conflicts manually
- Use `python manage.py migrate --fake` cautiously

#### Import Errors
- Ensure virtual environment is activated
- Reinstall requirements: `pip install -r requirements.txt`

#### Cloud Tasks Local Development
- Set `CLOUD_TASKS_ENABLED=False` for local dev
- Use synchronous task execution in development

## Support

For questions or issues:
- Check [docs/](../docs/) for documentation
- Review [ARCHITECTURE.md](../ARCHITECTURE.md) for system overview
- See [gaps/backend-gaps.md](../docs/gaps/backend-gaps.md) for known issues
