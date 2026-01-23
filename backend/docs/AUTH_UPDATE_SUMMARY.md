# Backend Authentication Update - Events and Courses Endpoints

## Summary

Updated the backend to ensure that events and courses listing endpoints require attendee account authentication. These endpoints are no longer publicly accessible.

## Changes Made

### 1. Events Listing Endpoint (`/api/v1/events/`)

**File:** `backend/src/events/views.py`

**Changes:**
- Updated `EventViewSet` docstring to clearly indicate authentication requirements
- Maintained existing permission: `IsAuthenticated, IsOrganizerOrCourseManager`
- This endpoint was already properly secured and required authentication

**Behavior:**
- ✅ **Unauthenticated users**: Receive 401 Unauthorized
- ✅ **Authenticated attendees** (without organizer role): Can access but see empty results (they don't own any events)
- ✅ **Authenticated organizers**: Can access and see their own events

### 2. Courses Listing Endpoint (`/api/v1/courses/`)

**File:** `backend/src/learning/views.py`

**Changes:**
- Removed `IsAuthenticatedOrReadOnly` permission that allowed public access
- Updated to require `IsAuthenticated` for all actions (list, retrieve, create, update, delete)
- Updated `get_queryset()` to remove special handling for unauthenticated users
- Updated `get_permissions()` to consistently require authentication for all actions

**Before:**
```python
def get_permissions(self):
    if self.action in ["list", "retrieve"]:
        permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    else:
        permission_classes = [permissions.IsAuthenticated]
    return [permission() for permission in permission_classes]

def get_queryset(self):
    # ... other code ...
    # Public visibility logic for non-authenticated users
    if not user.is_authenticated:
        return queryset.filter(is_public=True, status=Course.Status.PUBLISHED)
    # ... rest of method ...
```

**After:**
```python
def get_permissions(self):
    # All actions require authentication
    return [permissions.IsAuthenticated()]

def get_queryset(self):
    # ... other code ...
    # Removed: if not user.is_authenticated block
    # Authenticated users can see public published courses or their own courses
    if self.action in ["list", "retrieve"]:
        return queryset.filter(models.Q(is_public=True, status=Course.Status.PUBLISHED) | models.Q(owner=user)).distinct()
    # ... rest of method ...
```

**Behavior:**
- ✅ **Unauthenticated users**: Receive 401 Unauthorized
- ✅ **Authenticated attendees**: Can see public published courses and any courses they own
- ✅ **Course owners**: Can see all their own courses (regardless of status) plus public published courses

### 3. Public Endpoints Remain Unchanged

**Public Event Discovery Endpoints** (still accessible without authentication):
- `GET /api/v1/public/events/` - List public events
- `GET /api/v1/public/events/{identifier}/` - View public event details

These endpoints remain publicly accessible for event discovery and registration purposes.

## Testing

### New Test Suite

Created comprehensive test suite in `backend/src/tests/test_auth_requirements.py` with 11 tests covering:

**Event Listing Authentication:**
1. ✅ Unauthenticated users cannot list events (401)
2. ✅ Unauthenticated users cannot retrieve event details (401)
3. ✅ Authenticated attendees with organizer role requirement
4. ✅ Authenticated organizers can list their events (200)

**Course Listing Authentication:**
5. ✅ Unauthenticated users cannot list courses (401)
6. ✅ Unauthenticated users cannot retrieve course details (401)
7. ✅ Authenticated attendees can see public published courses (200)
8. ✅ Authenticated attendees cannot see draft courses they don't own (200, filtered)
9. ✅ Course owners can see their own courses regardless of status (200)

**Public Endpoints:**
10. ✅ Public event list remains accessible without auth (200)
11. ✅ Public event detail remains accessible without auth (200)

### Test Results

All tests passing:
```
11 passed, 11 warnings in 7.94s
```

Existing test suites also pass:
- Events tests: 37 passed
- Learning tests: 19 passed

## API Endpoint Summary

### Protected Endpoints (Require Authentication)

| Endpoint | Method | Permission | Access |
|----------|--------|------------|--------|
| `/api/v1/events/` | GET | IsAuthenticated + IsOrganizerOrCourseManager | Event owners only |
| `/api/v1/events/` | POST | IsAuthenticated + CanCreateEvents | Event creators |
| `/api/v1/events/{uuid}/` | GET/PATCH/DELETE | IsAuthenticated + Ownership | Event owner |
| `/api/v1/courses/` | GET | IsAuthenticated | Public published + owned courses |
| `/api/v1/courses/` | POST | IsAuthenticated + CanCreateCourses | Course creators |
| `/api/v1/courses/{uuid}/` | GET/PATCH/DELETE | IsAuthenticated + Ownership | Course owner |

### Public Endpoints (No Authentication Required)

| Endpoint | Method | Access |
|----------|--------|--------|
| `/api/v1/public/events/` | GET | All users |
| `/api/v1/public/events/{identifier}/` | GET | All users |

## Security Benefits

1. **Data Privacy**: User data and private events/courses are not exposed to unauthenticated users
2. **Access Control**: Only authenticated users can discover available courses and events
3. **Consistent Security Model**: All management endpoints require authentication
4. **Separate Public Discovery**: Public event endpoints provide controlled access for discovery

## Migration Notes

### Frontend Impact

Frontend applications will need to:

1. **Ensure Authentication**: Users must be authenticated before accessing:
   - `/api/v1/events/` endpoint (for organizers)
   - `/api/v1/courses/` endpoint (for all users)

2. **Use Public Endpoints**: For public event discovery, use:
   - `/api/v1/public/events/` for listing public events
   - `/api/v1/public/events/{identifier}/` for public event details

3. **Handle 401 Responses**: Redirect to login if accessing protected endpoints without authentication

### Example Frontend Flow

**Before (courses were public):**
```javascript
// Could fetch courses without auth
fetch('/api/v1/courses/')
  .then(response => response.json())
```

**After (courses require auth):**
```javascript
// Must include authentication token
fetch('/api/v1/courses/', {
  headers: {
    'Authorization': `Bearer ${token}`
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

## Backward Compatibility

⚠️ **Breaking Change**: This is a breaking change for any clients accessing `/api/v1/courses/` without authentication.

**Mitigation:**
- Public event discovery remains available via `/api/v1/public/events/`
- Course discovery can be implemented via a similar public endpoint if needed
- All authenticated flows remain unchanged

## Recommendations

### Optional Future Enhancements

1. **Public Courses Endpoint**: Consider creating a `/api/v1/public/courses/` endpoint similar to public events for course discovery
2. **Rate Limiting**: Add rate limiting to prevent abuse of public endpoints
3. **Analytics**: Track usage of public vs. authenticated endpoints
4. **Documentation**: Update API documentation to reflect authentication requirements

## Files Modified

1. `backend/src/events/views.py` - Updated EventViewSet docstring
2. `backend/src/learning/views.py` - Secured CourseViewSet permissions
3. `backend/src/tests/test_auth_requirements.py` - New comprehensive test suite

## Verification Checklist

- [x] Unauthenticated users cannot access `/api/v1/events/`
- [x] Unauthenticated users cannot access `/api/v1/courses/`
- [x] Authenticated users can access courses based on visibility
- [x] Authenticated organizers can access their events
- [x] Public event endpoints remain accessible
- [x] All existing tests pass
- [x] New authentication tests pass
- [x] Documentation updated
