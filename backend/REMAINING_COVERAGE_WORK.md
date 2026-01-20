# Remaining Test Coverage Work

## Current Status (After Phase 1)
- **Overall Coverage**: 73%
- **Tests Passing**: 536
- **Recently Completed**:
  - ✅ feedback module (20 tests, 60-95% coverage)
  - ✅ events/tasks.py (21 tests, 83% coverage)
  - ✅ Fixed 5 failing tests
  - ✅ Fixed 3 bugs

## Remaining High-Priority Modules

### 1. integrations/tasks.py - Currently 25% → Target 80%
**Lines**: 110 total, 82 uncovered
**Estimated Tests**: 15-18 tests
**Impact**: HIGH - Critical background job infrastructure

**Functions to Test**:
- `process_zoom_webhook` - webhook processing with retries
- `cleanup_old_logs` - data retention cleanup
- `retry_failed_webhooks` - automatic retry logic
- `send_email` - email sending with EmailLog
- `retry_failed_emails` - email retry logic
- `send_email_batch` - bulk email sending
- `sync_zoom_recordings` - Zoom recording sync

**Test Coverage Needed**:
- Success cases for all tasks
- Failure handling and error logging
- Retry logic and attempt limits
- Database operations (create, update, delete)
- External API mocking (Zoom, email services)
- Edge cases (missing data, invalid IDs)

### 2. promo_codes/views.py - Currently 45% → Target 85%
**Lines**: 49 total, 27 uncovered
**Estimated Tests**: 10-12 tests
**Impact**: MEDIUM - Revenue critical

**Functions to Test**:
- Promo code validation
- Apply to event registration
- Apply to course enrollment
- Usage limit enforcement
- Expiration checking
- Discount calculation (percentage & fixed)
- Permission checks

**Test Coverage Needed**:
- Valid promo code application
- Invalid/expired promo codes
- Usage limit exceeded
- Already used codes
- Permission checks (owner vs non-owner)
- Edge cases (zero discount, 100% discount)

### 3. learning/views.py - Currently 45% → Target 75%
**Lines**: 805 total, 439 uncovered ⚠️ LARGEST MODULE
**Estimated Tests**: 40-50 tests
**Impact**: VERY HIGH - Core LMS functionality

**ViewSets to Test**:
- `CourseViewSet` (CRUD, publish, duplicate, filtering)
- `CourseModuleViewSet` (module management)
- `CourseModuleContentViewSet` (content CRUD, file uploads)
- `CourseAssignmentViewSet` (assignment management)
- `CourseSubmissionsViewSet` (submission grading)
- `CourseAnnouncementViewSet` (announcements)
- `CourseSessionViewSet` (hybrid course sessions, Zoom sync)

**Test Coverage Needed**:
- CRUD operations for all viewsets
- Permission checks (owner, instructor, student)
- File upload/download operations
- Zoom integration for sessions
- Attendance tracking
- Progress calculations
- Edge cases and validation

### 4. registrations/views.py - Currently 63% → Target 85%
**Lines**: 388 total, 143 uncovered
**Estimated Tests**: 20-25 tests
**Impact**: MEDIUM - Already decent coverage

**Functions to Test**:
- Bulk registration import/export
- Waitlist management
- Check-in operations
- QR code generation
- Ticket downloads
- Registration statistics
- Custom field handling

**Test Coverage Needed**:
- Bulk operations (CSV import/export)
- Waitlist promotion logic
- Check-in validation
- Permission checks
- Edge cases (capacity limits, duplicates)

### 5. learning/tasks.py - Currently 53% → Target 90%
**Lines**: 102 total, 48 uncovered
**Estimated Tests**: 12-15 tests
**Impact**: HIGH - Background jobs for LMS

**Functions to Test**:
- `send_enrollment_confirmation_task`
- `send_course_welcome_email_task`
- `generate_course_certificate_task`
- `send_course_completion_notification_task`
- `unlock_scheduled_content_task`
- `send_course_reminder_task`
- `process_bulk_enrollment_task`
- `sync_course_enrollment_with_zoom_task`

**Test Coverage Needed**:
- Success cases for all tasks
- Email sending with proper context
- Certificate generation
- Content unlocking logic
- Zoom synchronization
- Error handling

### 6. promo_codes/serializers.py - Currently 55% → Target 90%
**Lines**: 73 total, 33 uncovered
**Estimated Tests**: 7-10 tests
**Impact**: MEDIUM

**Functions to Test**:
- PromoCode serializer validation
- Discount type validation
- Discount value ranges
- Usage limit validation
- Expiration date validation
- Code uniqueness
- Nested relationships

**Test Coverage Needed**:
- Valid data serialization
- Invalid data rejection
- Edge cases (boundary values)
- Custom validation methods

## Implementation Strategy

### Phase 2: Quick Coverage Wins (Next)
Focus on high-impact, relatively easy modules:
1. integrations/tasks.py (15-18 tests) → +55% coverage
2. promo_codes/views.py (10-12 tests) → +40% coverage
3. promo_codes/serializers.py (7-10 tests) → +35% coverage

**Expected Impact**: +3-4% overall coverage

### Phase 3: Large Modules
Tackle the biggest modules:
1. learning/views.py (40-50 tests) → +30% coverage ⚠️ BIGGEST
2. registrations/views.py (20-25 tests) → +22% coverage
3. learning/tasks.py (12-15 tests) → +37% coverage

**Expected Impact**: +4-5% overall coverage

### Phase 4: Polish & Final Pass
- Run comprehensive coverage report
- Identify any remaining gaps
- Add edge case tests
- Aim for 83-85% overall coverage

## Testing Patterns to Follow

### Task Testing Pattern
```python
@pytest.mark.django_db
class TestTaskName:
    @patch('module.external_service')
    def test_success_case(self, mock_service, fixtures):
        # Setup
        mock_service.method.return_value = {'success': True}

        # Execute
        result = task_function(arg)

        # Assert
        assert result is True
        mock_service.method.assert_called_once()
        # Verify database changes

    def test_handles_missing_data(self):
        # Test with nonexistent ID
        result = task_function(99999)
        assert result is False

    @patch('module.external_service')
    def test_handles_failure(self, mock_service):
        # Test failure handling
        mock_service.method.side_effect = Exception("Error")
        result = task_function(id)
        # Verify error logged and handled gracefully
```

### ViewSet Testing Pattern
```python
@pytest.mark.django_db
class TestViewSetName:
    def test_list(self, auth_client, fixtures):
        response = auth_client.get(url)
        assert response.status_code == 200
        assert len(response.data['results']) > 0

    def test_create(self, auth_client, data):
        response = auth_client.post(url, data)
        assert response.status_code == 201
        # Verify database

    def test_permission_denied(self, other_client):
        response = other_client.post(url, data)
        assert response.status_code == 403
```

## Key Mocking Targets

External services that must be mocked:
- `stripe.checkout.Session.create`
- `stripe.Webhook.construct_event`
- `zoom_service.create_meeting`
- `zoom_service.get_access_token`
- `email_service.send_email`
- `attendance_matcher.match_attendance`
- `requests.get` / `requests.post` (for Zoom API)

## Success Criteria

- [ ] Overall coverage reaches 83-85%
- [ ] All critical paths tested
- [ ] No failing tests
- [ ] Test suite runs in <30 seconds
- [ ] All high-priority modules above 80% coverage

## Next Steps

1. **Immediate**: Create consolidated test files for remaining modules (Option B)
2. **Short-term**: Run full coverage report and identify specific gaps
3. **Medium-term**: Add integration tests for critical user flows
4. **Long-term**: Maintain coverage as new features are added

## Notes

- Current test suite is well-structured with good fixtures
- Mock patterns are consistent and reusable
- Coverage measurement is accurate
- No flaky tests observed
- Test execution is fast (<30s for 536 tests)

## Resources

- Test fixtures: `backend/src/conftest.py`
- Factories: `backend/src/factories.py`
- Coverage reports: Run `pytest --cov=src --cov-report=html`
- Test patterns: See existing test files in `src/*/tests/`
