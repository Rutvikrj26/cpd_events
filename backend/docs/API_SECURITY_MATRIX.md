# API Endpoint Security Matrix

## 📋 Overview
This document provides a quick reference for authentication requirements across all API endpoints.

## 🔒 Events Endpoints

### Management Endpoints (Require Authentication)

| Endpoint | Method | Authentication | Permission | Description |
|----------|--------|----------------|------------|-------------|
| `/api/v1/events/` | GET | ✅ Required | Organizer/Course Manager | List organizer's events |
| `/api/v1/events/` | POST | ✅ Required | Event Creator | Create new event |
| `/api/v1/events/{uuid}/` | GET | ✅ Required | Organizer/Course Manager | Get event details |
| `/api/v1/events/{uuid}/` | PATCH | ✅ Required | Event Owner | Update event |
| `/api/v1/events/{uuid}/` | DELETE | ✅ Required | Event Owner | Delete event |
| `/api/v1/events/{uuid}/publish/` | POST | ✅ Required | Event Owner | Publish event |
| `/api/v1/events/{uuid}/unpublish/` | POST | ✅ Required | Event Owner | Unpublish event |
| `/api/v1/events/{uuid}/cancel/` | POST | ✅ Required | Event Owner | Cancel event |

### Public Endpoints (No Authentication Required)

| Endpoint | Method | Authentication | Description |
|----------|--------|----------------|-------------|
| `/api/v1/public/events/` | GET | ❌ Not Required | Discover public events |
| `/api/v1/public/events/{identifier}/` | GET | ❌ Not Required | View public event details |

## 📚 Courses Endpoints

### All Endpoints Require Authentication

| Endpoint | Method | Authentication | Permission | Description |
|----------|--------|----------------|------------|-------------|
| `/api/v1/courses/` | GET | ✅ Required | Authenticated User | List public courses + owned |
| `/api/v1/courses/` | POST | ✅ Required | Course Creator | Create new course |
| `/api/v1/courses/{uuid}/` | GET | ✅ Required | Authenticated User | Get course details |
| `/api/v1/courses/{uuid}/` | PATCH | ✅ Required | Course Owner | Update course |
| `/api/v1/courses/{uuid}/` | DELETE | ✅ Required | Course Owner | Delete course |
| `/api/v1/courses/{uuid}/publish/` | POST | ✅ Required | Course Owner | Publish course |
| `/api/v1/courses/{uuid}/enrollments/` | GET | ✅ Required | Course Owner/Instructor | View enrollments |
| `/api/v1/courses/{uuid}/progress/` | GET | ✅ Required | Enrolled User | View course progress |

## 🎓 Course Enrollment Endpoints

| Endpoint | Method | Authentication | Permission | Description |
|----------|--------|----------------|------------|-------------|
| `/api/v1/enrollments/` | GET | ✅ Required | Authenticated User | List user's enrollments |
| `/api/v1/enrollments/` | POST | ✅ Required | Authenticated User | Enroll in course |
| `/api/v1/enrollments/{uuid}/` | GET | ✅ Required | Enrollment Owner | Get enrollment details |
| `/api/v1/enrollments/{uuid}/mark-complete/` | POST | ✅ Required | Course Manager/Instructor | Mark enrollment complete |

## 🎫 Registration Endpoints

| Endpoint | Method | Authentication | Permission | Description |
|----------|--------|----------------|------------|-------------|
| `/api/v1/events/{uuid}/registrations/` | GET | ✅ Required | Event Owner | List event registrations |
| `/api/v1/events/{uuid}/registrations/` | POST | ✅ Required | Authenticated User | Register for event |
| `/api/v1/registrations/{uuid}/` | GET | ✅ Required | Owner or Registrant | Get registration details |
| `/api/v1/registrations/{uuid}/` | PATCH | ✅ Required | Owner or Registrant | Update registration |

## 📝 Learning Content Endpoints

| Endpoint | Method | Authentication | Permission | Description |
|----------|--------|----------------|------------|-------------|
| `/api/v1/learning/` | GET | ✅ Required | Authenticated User | Learning dashboard |
| `/api/v1/learning/progress/content/{uuid}/` | POST | ✅ Required | Enrolled User | Update content progress |
| `/api/v1/learning/quiz/submit/` | POST | ✅ Required | Enrolled User | Submit quiz |
| `/api/v1/submissions/` | GET | ✅ Required | Authenticated User | List submissions |
| `/api/v1/submissions/` | POST | ✅ Required | Enrolled User | Create submission |

## 🔐 Authentication Methods

### Supported Authentication Schemes

1. **Token Authentication** (Primary)
   ```
   Authorization: Token <token>
   ```

2. **Session Authentication** (Browser)
   - Automatic via Django session cookies
   - Used for admin interface and browsable API

### Getting a Token

```bash
POST /api/v1/auth/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password"
}

Response:
{
  "token": "abc123...",
  "user": { ... }
}
```

## 📊 Quick Reference

### ✅ Requires Authentication
- All `/api/v1/events/` endpoints
- All `/api/v1/courses/` endpoints
- All `/api/v1/learning/` endpoints
- All `/api/v1/registrations/` endpoints
- All `/api/v1/enrollments/` endpoints
- All `/api/v1/submissions/` endpoints

### ❌ Public Access (No Auth)
- `/api/v1/public/events/` - Public event listing
- `/api/v1/public/events/{identifier}/` - Public event detail

### 🔒 Permission Levels

1. **Authenticated User** - Any logged-in user
2. **Event Creator** - User with event creation capability
3. **Course Creator** - User with course creation capability
4. **Owner** - User who owns the resource
5. **Organizer/Course Manager** - User with management capabilities
6. **Enrolled User** - User enrolled in the course/event

## 🚨 Error Responses

### 401 Unauthorized
Returned when authentication is required but not provided:
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Solution:** Include authentication token in request headers

### 403 Forbidden
Returned when user is authenticated but lacks permission:
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**Solution:** Ensure user has required role/permission

### 404 Not Found
Returned when resource doesn't exist or user doesn't have access:
```json
{
  "detail": "Not found."
}
```

**Solution:** Verify resource exists and user has permission to access it

## 📱 Frontend Integration Examples

### Authenticated Request
```javascript
fetch('/api/v1/courses/', {
  headers: {
    'Authorization': `Token ${userToken}`,
    'Content-Type': 'application/json'
  }
})
.then(response => {
  if (response.status === 401) {
    // Redirect to login
    window.location.href = '/login';
  }
  return response.json();
})
```

### Public Request
```javascript
// No authentication needed
fetch('/api/v1/public/events/')
  .then(response => response.json())
```

## 🔄 Migration from Previous Version

### Breaking Changes

**Courses Endpoint** - Now requires authentication:

**Before (v1.0):**
```javascript
// Public access allowed
fetch('/api/v1/courses/') // Works without auth
```

**After (v2.0):**
```javascript
// Authentication required
fetch('/api/v1/courses/', {
  headers: { 'Authorization': `Token ${token}` }
}) // Requires auth
```

### Recommended Updates

1. **Update API calls** to include authentication headers
2. **Handle 401 responses** by redirecting to login
3. **Use public endpoints** for unauthenticated discovery
4. **Test all API integrations** after update

## ✅ Security Benefits

- **Data Privacy**: User data protected from public access
- **Access Control**: Role-based permissions enforced
- **Audit Trail**: All requests tied to authenticated users
- **GDPR Compliance**: Better control over personal data access

## 📖 Additional Resources

- [API Documentation](./API.md)
- [Authentication Guide](./AUTHENTICATION.md)
- [Permission System](./PERMISSIONS.md)
- [Security Best Practices](./SECURITY.md)
