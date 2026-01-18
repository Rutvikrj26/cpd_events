# API Documentation

This directory contains complete REST API specifications for the CPD Events platform.

## Files

- [drf-endpoints-part1.md](drf-endpoints-part1.md) - Django REST Framework API endpoints (Part 1)
- [drf-endpoints-part2.md](drf-endpoints-part2.md) - Django REST Framework API endpoints (Part 2)
- [api-review.md](api-review.md) - API specification review and analysis
- [data-models.md](data-models.md) - Database models and relationships

## API Overview

The CPD Events API is built with Django REST Framework and provides endpoints for:

- **Authentication**: User login, registration, password reset
- **Events**: Event management, listing, and details
- **Registrations**: Event registration and payment processing
- **Certificates**: Certificate generation and verification
- **Courses**: Learning management and course enrollment
- **Contacts**: Contact management and communication

## Quick Start

### Authentication
All API requests (except public endpoints) require authentication via JWT tokens.

### Base URL
- Development: `http://localhost:8000/api/`
- Production: `https://api.yourdomain.com/api/`

### Common Headers
```
Authorization: Bearer <token>
Content-Type: application/json
```

## Documentation Structure

### Part 1 - Core Endpoints
[drf-endpoints-part1.md](drf-endpoints-part1.md) covers:
- Authentication endpoints
- User management
- Event endpoints
- Registration endpoints

### Part 2 - Additional Endpoints
[drf-endpoints-part2.md](drf-endpoints-part2.md) covers:
- Certificate endpoints
- Course endpoints
- Contact endpoints
- Integration endpoints

### Data Models
[data-models.md](data-models.md) provides:
- Database schema
- Model relationships
- Field specifications
- Validation rules

### API Review
[api-review.md](api-review.md) contains:
- API design analysis
- Best practices review
- Improvement recommendations

## Related Documentation

- [Backend README](../../backend/README.md) - Backend implementation details
- [Features Documentation](../features/) - Feature-specific documentation
- [Architecture Overview](../architecture/overview.md) - System architecture
