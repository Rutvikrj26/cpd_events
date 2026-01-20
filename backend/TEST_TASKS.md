# Exhaustive Test Coverage Task List

## Phase 1: Quick Wins (Target: 78% coverage)

### Feedback Module - 0-19% → 80%+ (PRIORITY 1)

#### feedback/tests.py - Create comprehensive test suite
- [ ] Test feedback submission (authenticated user)
- [ ] Test feedback submission (unauthenticated - should fail)
- [ ] Test feedback retrieval by organizer
- [ ] Test feedback retrieval by non-organizer (should fail)
- [ ] Test feedback for specific event
- [ ] Test feedback with ratings
- [ ] Test feedback with comments
- [ ] Test feedback validation (missing fields)
- [ ] Test feedback update
- [ ] Test feedback deletion
- [ ] Test bulk feedback export
- [ ] Test feedback filtering by event
- [ ] Test feedback filtering by date range

#### feedback/views.py - 19% → 90%
- [ ] Test FeedbackViewSet create action
- [ ] Test FeedbackViewSet list action
- [ ] Test FeedbackViewSet retrieve action
- [ ] Test FeedbackViewSet update action
- [ ] Test FeedbackViewSet destroy action
- [ ] Test permission checks for all actions
- [ ] Test event-specific feedback queries
- [ ] Test pagination

#### feedback/serializers.py - 70% → 95%
- [ ] Test FeedbackSerializer validation
- [ ] Test required field validation
- [ ] Test rating range validation
- [ ] Test nested relationships

### integrations/tasks.py - 25% → 80%

#### Email Tasks
- [ ] Test send_email_task success
- [ ] Test send_email_task failure
- [ ] Test send_email_task retry logic
- [ ] Test batch email sending
- [ ] Test email template rendering

#### Zoom Tasks
- [ ] Test create_zoom_meeting_task success
- [ ] Test create_zoom_meeting_task failure
- [ ] Test update_zoom_meeting_task
- [ ] Test delete_zoom_meeting_task
- [ ] Test sync_zoom_attendance_task
- [ ] Test zoom_registrant_task
- [ ] Test zoom retry logic

#### General Task Tests
- [ ] Test task scheduling
- [ ] Test task error logging
- [ ] Test task timeout handling

### promo_codes/serializers.py - 55% → 90%

- [ ] Test PromoCodeSerializer validation
- [ ] Test discount_type validation
- [ ] Test discount_value validation
- [ ] Test usage_limit validation
- [ ] Test expiration date validation
- [ ] Test code uniqueness validation
- [ ] Test nested event/course relationships

## Phase 2: Core Functionality (Target: 82% coverage)

### learning/views.py - 45% → 80% (PRIORITY 2)

#### CourseViewSet Tests
- [ ] Test course list (authenticated)
- [ ] Test course list (unauthenticated)
- [ ] Test course retrieve (published)
- [ ] Test course retrieve (draft - owner only)
- [ ] Test course create (with LMS plan)
- [ ] Test course create (without LMS plan - should fail)
- [ ] Test course update (owner)
- [ ] Test course update (non-owner - should fail)
- [ ] Test course delete (owner)
- [ ] Test course delete (non-owner - should fail)
- [ ] Test course publish action
- [ ] Test course unpublish action
- [ ] Test course duplicate action
- [ ] Test course bulk delete
- [ ] Test course filtering by status
- [ ] Test course filtering by owner
- [ ] Test course search by title
- [ ] Test course ordering
- [ ] Test course pagination

#### CourseEnrollmentViewSet Tests (additional)
- [ ] Test enrollment list for user
- [ ] Test enrollment retrieve
- [ ] Test enrollment create for free course
- [ ] Test enrollment create for paid course (should fail)
- [ ] Test enrollment update status
- [ ] Test enrollment delete
- [ ] Test enrollment filtering

#### CourseModuleViewSet Tests
- [ ] Test module list for course
- [ ] Test module create (course owner)
- [ ] Test module create (non-owner - should fail)
- [ ] Test module update
- [ ] Test module delete
- [ ] Test module reordering
- [ ] Test module publish/unpublish

#### CourseModuleContentViewSet Tests
- [ ] Test content list for module
- [ ] Test content create (text)
- [ ] Test content create (video)
- [ ] Test content create (quiz)
- [ ] Test content create (file)
- [ ] Test content update
- [ ] Test content delete
- [ ] Test content reordering
- [ ] Test content file upload
- [ ] Test content permission checks

#### CourseAssignmentViewSet Tests
- [ ] Test assignment list
- [ ] Test assignment create
- [ ] Test assignment update
- [ ] Test assignment delete
- [ ] Test assignment submission
- [ ] Test assignment grading

#### CourseSubmissionsViewSet Tests
- [ ] Test submission list
- [ ] Test submission retrieve
- [ ] Test submission grade action
- [ ] Test submission filtering

#### CourseAnnouncementViewSet Tests
- [ ] Test announcement list
- [ ] Test announcement create
- [ ] Test announcement update
- [ ] Test announcement delete
- [ ] Test announcement permission checks

#### CourseSessionViewSet Tests (Hybrid Courses)
- [ ] Test session list
- [ ] Test session create
- [ ] Test session update
- [ ] Test session delete
- [ ] Test session publish
- [ ] Test session unpublish
- [ ] Test session sync_attendance action
- [ ] Test session unmatched_participants action
- [ ] Test session match_participant action
- [ ] Test Zoom integration for sessions

### promo_codes/views.py - 45% → 85%

- [ ] Test promo code validate action
- [ ] Test promo code apply to event registration
- [ ] Test promo code apply to course enrollment
- [ ] Test promo code usage limit enforcement
- [ ] Test promo code expiration check
- [ ] Test promo code for specific events only
- [ ] Test promo code percentage discount
- [ ] Test promo code fixed amount discount
- [ ] Test promo code permission checks
- [ ] Test invalid promo code handling
- [ ] Test already used promo code
- [ ] Test promo code admin views

### registrations/views.py - 63% → 85%

#### Additional Registration Tests
- [ ] Test bulk registration import
- [ ] Test bulk registration export (CSV)
- [ ] Test waitlist promotion
- [ ] Test waitlist manual add
- [ ] Test check-in action
- [ ] Test attendance tracking
- [ ] Test registration cancellation
- [ ] Test registration refund flow
- [ ] Test guest registration
- [ ] Test registration custom fields
- [ ] Test registration session selection (multi-session events)
- [ ] Test registration duplicate prevention
- [ ] Test registration capacity limits
- [ ] Test registration statistics endpoint
- [ ] Test QR code generation
- [ ] Test ticket download

## Phase 3: Background Jobs (Target: 85% coverage)

### learning/tasks.py - 42% → 85%

- [ ] Test send_enrollment_confirmation_task
- [ ] Test send_course_welcome_email_task
- [ ] Test generate_course_certificate_task
- [ ] Test send_course_completion_notification_task
- [ ] Test unlock_scheduled_content_task
- [ ] Test send_course_reminder_task
- [ ] Test process_bulk_enrollment_task
- [ ] Test sync_course_enrollment_with_zoom_task
- [ ] Test cleanup_expired_enrollments_task
- [ ] Test task retry logic
- [ ] Test task failure logging
- [ ] Test task success logging

### registrations/tasks.py - 64% → 90%

- [ ] Test send_registration_confirmation_task (additional cases)
- [ ] Test send_event_reminder_task
- [ ] Test process_zoom_registrant_task (additional cases)
- [ ] Test batch_create_zoom_registrants_task
- [ ] Test sync_attendance_from_zoom_task
- [ ] Test cleanup_abandoned_registrations_task
- [ ] Test send_certificate_email_task
- [ ] Test task error handling

## Phase 4: Polish & Edge Cases (Target: 88%+ coverage)

### events/views.py - 76% → 90%

- [ ] Test event bulk operations
- [ ] Test event complex filtering (date ranges, tags, categories)
- [ ] Test event CSV export
- [ ] Test event statistics endpoint
- [ ] Test event cloning with all related data
- [ ] Test event custom field handling
- [ ] Test event session management
- [ ] Test event capacity management
- [ ] Test event publishing workflow

### integrations/models.py - 76% → 90%

- [ ] Test ZoomIntegration model methods
- [ ] Test ZoomIntegration token refresh
- [ ] Test ZoomIntegration credential encryption
- [ ] Test EmailTemplate model methods
- [ ] Test template variable substitution
- [ ] Test integration status tracking

### registrations/models.py - 79% → 92%

- [ ] Test Registration model methods
- [ ] Test registration status transitions
- [ ] Test attendance calculation
- [ ] Test CPD credit calculation
- [ ] Test custom field handling
- [ ] Test payment processing
- [ ] Test refund processing

### learning/models.py - 80% → 92%

- [ ] Test Course model methods
- [ ] Test enrollment count updates
- [ ] Test course completion logic
- [ ] Test course progress calculation
- [ ] Test quiz grading logic
- [ ] Test certificate generation
- [ ] Test hybrid course logic

### learning/services.py - 66% → 95%

- [ ] Test CourseService.confirm_enrollment edge cases
- [ ] Test CourseService error handling
- [ ] Test StripeService integration
- [ ] Test ZoomService integration
- [ ] Test service retry logic

### Edge Cases & Integration Tests

- [ ] Test concurrent enrollment attempts
- [ ] Test race conditions in registration
- [ ] Test database transaction rollbacks
- [ ] Test cache invalidation
- [ ] Test file upload size limits
- [ ] Test SQL injection prevention
- [ ] Test XSS prevention
- [ ] Test CSRF protection
- [ ] Test rate limiting
- [ ] Test API throttling
- [ ] Test permission boundary cases
- [ ] Test data validation edge cases
- [ ] Test timezone handling
- [ ] Test internationalization
- [ ] Test error response formats
- [ ] Test API versioning

## Total Task Count

- **Phase 1**: ~60 tests
- **Phase 2**: ~100 tests
- **Phase 3**: ~30 tests
- **Phase 4**: ~70 tests

**Grand Total**: ~260 new tests to add

## Execution Order

1. Start with feedback module (easy, high impact)
2. Move to integrations/tasks.py (important background jobs)
3. Focus on learning/views.py (core functionality)
4. Add promo_codes tests (revenue critical)
5. Enhance registrations tests
6. Add background job tests
7. Polish with edge cases and integration tests
