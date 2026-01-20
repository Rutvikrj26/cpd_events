# Test Coverage Improvement Plan

## Current Status
- **Overall Coverage**: 73% (18,185 statements, 4,973 uncovered)
- **Tests Passing**: 495 passed, 1 skipped
- **Tests Runtime**: ~8-15 seconds

## Priority Areas (Sorted by Impact)

### 🔴 CRITICAL - Low Coverage (<50%)

#### 1. learning/views.py - 45% (801 statements, 443 uncovered)
**Impact**: Core LMS functionality
**Priority**: HIGH
**Tasks**:
- [ ] Test CourseViewSet CRUD operations (create, update, delete, publish)
- [ ] Test CourseViewSet actions (duplicate, bulk operations)
- [ ] Test CourseEnrollmentViewSet edge cases
- [ ] Test CourseModuleViewSet operations
- [ ] Test CourseSessionViewSet (hybrid course sessions)
- [ ] Test CourseAnnouncementViewSet
- [ ] Test file upload/download operations
- [ ] Test permission checks across all views
- [ ] Test error handling for invalid data

**Estimated Tests to Add**: 40-50 tests
**Estimated Coverage Increase**: +30-35%

#### 2. integrations/tasks.py - 25% (110 statements, 82 uncovered)
**Impact**: Background jobs, async operations
**Priority**: HIGH
**Tasks**:
- [ ] Test email sending tasks (success and failure cases)
- [ ] Test Zoom integration tasks
- [ ] Test retry logic
- [ ] Test task scheduling
- [ ] Mock external API calls
- [ ] Test error handling and logging

**Estimated Tests to Add**: 15-20 tests
**Estimated Coverage Increase**: +50%

#### 3. learning/tasks.py - 42% (102 statements, 59 uncovered)
**Impact**: Background learning operations
**Priority**: MEDIUM
**Tasks**:
- [ ] Test enrollment notification tasks
- [ ] Test certificate generation tasks
- [ ] Test course completion tasks
- [ ] Test scheduled content unlock tasks
- [ ] Test reminder tasks

**Estimated Tests to Add**: 12-15 tests
**Estimated Coverage Increase**: +40%

#### 4. promo_codes/views.py - 45% (49 statements, 27 uncovered)
**Impact**: Revenue (promo code functionality)
**Priority**: MEDIUM
**Tasks**:
- [ ] Test promo code validation
- [ ] Test promo code application
- [ ] Test usage limit enforcement
- [ ] Test expiration logic
- [ ] Test permission checks

**Estimated Tests to Add**: 10-12 tests
**Estimated Coverage Increase**: +40%

#### 5. feedback/views.py - 19% (62 statements, 50 uncovered)
**Impact**: User engagement/feedback
**Priority**: LOW (but easy win)
**Tasks**:
- [ ] Test feedback submission
- [ ] Test feedback retrieval
- [ ] Test feedback moderation (if applicable)
- [ ] Test permission checks

**Estimated Tests to Add**: 8-10 tests
**Estimated Coverage Increase**: +60%

#### 6. feedback/tests.py - 0% (24 statements, 24 uncovered)
**Impact**: No tests exist
**Priority**: LOW
**Tasks**:
- [ ] Create initial test file structure
- [ ] Add basic CRUD tests
- [ ] Add permission tests

**Estimated Tests to Add**: 10-15 tests
**Estimated Coverage Increase**: 100% (from 0%)

### 🟡 MEDIUM - Moderate Coverage (50-70%)

#### 7. promo_codes/serializers.py - 55% (73 statements, 33 uncovered)
**Priority**: MEDIUM
**Tasks**:
- [ ] Test serializer validation rules
- [ ] Test custom field validation
- [ ] Test nested serializers

**Estimated Tests to Add**: 8-10 tests
**Estimated Coverage Increase**: +30%

#### 8. registrations/tasks.py - 64% (86 statements, 31 uncovered)
**Priority**: MEDIUM
**Tasks**:
- [ ] Test registration confirmation tasks
- [ ] Test reminder tasks
- [ ] Test Zoom registrant tasks
- [ ] Test error handling

**Estimated Tests to Add**: 8-10 tests
**Estimated Coverage Increase**: +25%

#### 9. registrations/views.py - 63% (388 statements, 143 uncovered)
**Priority**: MEDIUM
**Tasks**:
- [ ] Test bulk registration operations
- [ ] Test waitlist management
- [ ] Test check-in/attendance tracking
- [ ] Test CSV export
- [ ] Test guest registration flows

**Estimated Tests to Add**: 20-25 tests
**Estimated Coverage Increase**: +25%

#### 10. learning/services.py - 66% (62 statements, 21 uncovered)
**Priority**: MEDIUM
**Tasks**:
- [ ] Test CourseService methods
- [ ] Test enrollment confirmation logic
- [ ] Test edge cases and error handling

**Estimated Tests to Add**: 6-8 tests
**Estimated Coverage Increase**: +25%

### 🟢 LOW - Good Coverage (>70%)

These modules have good coverage but can be improved:

#### 11. events/views.py - 76% (381 statements, 90 uncovered)
- Add edge case tests
- Test bulk operations
- Test complex filtering

#### 12. integrations/models.py - 76% (265 statements, 63 uncovered)
- Test model methods
- Test property calculations
- Test model validation

#### 13. registrations/models.py - 79% (258 statements, 53 uncovered)
- Test model methods
- Test complex business logic
- Test signal handlers

#### 14. learning/models.py - 80% (729 statements, 148 uncovered)
- Test model methods and properties
- Test complex relationships
- Test business logic in models

## Implementation Strategy

### Phase 1: Quick Wins (Week 1)
**Goal**: Increase overall coverage to 78%
1. Fix feedback module (0% → 80%) - Easy win
2. Add missing task tests (integrations/tasks.py)
3. Add missing serializer validation tests

**Expected Impact**: +5% overall coverage

### Phase 2: Core Functionality (Weeks 2-3)
**Goal**: Increase overall coverage to 82%
1. learning/views.py coverage improvements
2. promo_codes/views.py coverage improvements
3. registrations/views.py edge cases

**Expected Impact**: +4% overall coverage

### Phase 3: Background Jobs (Week 4)
**Goal**: Increase overall coverage to 85%
1. learning/tasks.py coverage
2. registrations/tasks.py coverage
3. Integration task coverage

**Expected Impact**: +3% overall coverage

### Phase 4: Polish & Edge Cases (Week 5)
**Goal**: Increase overall coverage to 88%+
1. Add edge case tests across all modules
2. Test error handling
3. Test permission checks
4. Add integration tests

**Expected Impact**: +3% overall coverage

## Testing Best Practices

### Guidelines for New Tests
1. **Follow AAA Pattern**: Arrange, Act, Assert
2. **Use Fixtures**: Leverage existing conftest.py fixtures
3. **Mock External Services**: Always mock Stripe, Zoom, email services
4. **Test Edge Cases**: Don't just test happy paths
5. **Test Permissions**: Verify authorization for all endpoints
6. **Test Validation**: Check serializer/form validation
7. **Keep Tests Fast**: Use in-memory SQLite, avoid unnecessary I/O
8. **Descriptive Names**: Use clear test method names
9. **One Assertion Per Test**: When possible, keep tests focused
10. **Add Docstrings**: Explain what complex tests do

### Common Patterns to Test
- ✅ CRUD operations (Create, Read, Update, Delete)
- ✅ Permission checks (authenticated, unauthenticated, different roles)
- ✅ Validation (invalid data, missing fields, edge cases)
- ✅ Edge cases (empty lists, null values, max limits)
- ✅ Error handling (exceptions, API errors, timeouts)
- ✅ Business logic (complex calculations, state transitions)
- ✅ Bulk operations (batch creates, updates, deletes)
- ✅ Filtering and search
- ✅ Pagination
- ✅ File uploads/downloads

## Progress Tracking

Update this section as you complete tasks:

- [ ] Phase 1: Quick Wins (Target: 78%)
- [ ] Phase 2: Core Functionality (Target: 82%)
- [ ] Phase 3: Background Jobs (Target: 85%)
- [ ] Phase 4: Polish & Edge Cases (Target: 88%+)

## Useful Commands

```bash
# Run tests with coverage
.venv/bin/pytest --cov=src --cov-report=term-missing

# Run tests for specific module
.venv/bin/pytest src/learning/tests/ --cov=src/learning

# Run tests with coverage HTML report
.venv/bin/pytest --cov=src --cov-report=html
# Then open htmlcov/index.html

# Run specific test
.venv/bin/pytest src/learning/tests/test_views.py::TestCourseViewSet::test_create_course -v

# Run tests matching pattern
.venv/bin/pytest -k "test_create" -v
```

## Notes

- Current test suite runs in ~8-15 seconds, which is excellent
- Keep tests fast by using in-memory database and mocking external services
- Consider adding integration tests for critical user flows
- Monitor test execution time as you add more tests
- Aim for 90%+ coverage on critical modules (billing, registrations, learning)
- Some uncovered lines may be defensive code (error handlers) that are hard to test
