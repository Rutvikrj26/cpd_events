"""
Learning API views.
"""

from django.db import models
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import parsers, permissions, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import IsOrganizerOrCourseManager
from common.rbac import roles
from common.utils import error_response

from .models import (
    Assignment,
    AssignmentSubmission,
    ContentProgress,
    Course,
    CourseAnnouncement,
    CourseEnrollment,
    CourseModule,
    EventModule,
    ModuleContent,
    ModuleProgress,
    SubmissionReview,
)
from .serializers import (
    AssignmentCreateSerializer,
    AssignmentSerializer,
    AssignmentSubmissionCreateSerializer,
    AssignmentSubmissionSerializer,
    AssignmentSubmissionStaffSerializer,
    ContentProgressSerializer,
    ContentProgressUpdateSerializer,
    CourseAnnouncementSerializer,
    CourseCreateSerializer,
    CourseEnrollmentRosterSerializer,
    CourseEnrollmentSerializer,
    CourseListSerializer,
    CourseModuleSerializer,
    CourseSerializer,
    EventModuleCreateSerializer,
    EventModuleListSerializer,
    EventModuleSerializer,
    ModuleContentCreateSerializer,
    ModuleContentSerializer,
    ModuleProgressSerializer,
    SubmissionGradeSerializer,
)


@roles('organizer', 'course_manager', 'admin', route_name='event_modules')
class EventModuleViewSet(viewsets.ModelViewSet):
    """
    Event module management.

    GET /events/{event_uuid}/modules/ - List modules
    POST /events/{event_uuid}/modules/ - Create module
    GET /events/{event_uuid}/modules/{uuid}/ - Module detail
    PUT/PATCH /events/{event_uuid}/modules/{uuid}/ - Update module
    DELETE /events/{event_uuid}/modules/{uuid}/ - Delete module
    """

    permission_classes = [permissions.IsAuthenticated, IsOrganizerOrCourseManager]
    lookup_field = 'uuid'

    def get_queryset(self):
        from events.models import Event

        event_uuid = self.kwargs.get('event_uuid')
        event = get_object_or_404(Event, uuid=event_uuid, owner=self.request.user)
        return EventModule.objects.filter(event=event).prefetch_related('contents', 'assignments')

    def get_serializer_class(self):
        if self.action == 'list':
            return EventModuleListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return EventModuleCreateSerializer
        return EventModuleSerializer

    def perform_create(self, serializer):
        from events.models import Event

        event_uuid = self.kwargs.get('event_uuid')
        event = get_object_or_404(Event, uuid=event_uuid, owner=self.request.user)
        serializer.save(event=event)

    @swagger_auto_schema(
        operation_summary="Publish module",
        operation_description="Make this module visible to attendees.",
        responses={200: EventModuleSerializer},
    )
    @action(detail=True, methods=['post'])
    def publish(self, request, event_uuid=None, uuid=None):
        """Publish a module."""
        module = self.get_object()
        module.is_published = True
        module.save()
        return Response(EventModuleSerializer(module).data)

    @swagger_auto_schema(
        operation_summary="Unpublish module",
        operation_description="Hide this module from attendees.",
        responses={200: EventModuleSerializer},
    )
    @action(detail=True, methods=['post'])
    def unpublish(self, request, event_uuid=None, uuid=None):
        """Unpublish a module."""
        module = self.get_object()
        module.is_published = False
        module.save()
        return Response(EventModuleSerializer(module).data)


@roles('organizer', 'course_manager', 'admin', route_name='module_content')
class ModuleContentViewSet(viewsets.ModelViewSet):
    """
    Module content management.

    GET /events/{event_uuid}/modules/{module_uuid}/contents/ - List contents
    POST /events/{event_uuid}/modules/{module_uuid}/contents/ - Create content
    """

    permission_classes = [permissions.IsAuthenticated, IsOrganizerOrCourseManager]
    lookup_field = 'uuid'

    def get_queryset(self):
        from events.models import Event

        event_uuid = self.kwargs.get('event_uuid')
        module_uuid = self.kwargs.get('module_uuid')

        event = get_object_or_404(Event, uuid=event_uuid, owner=self.request.user)
        module = get_object_or_404(EventModule, uuid=module_uuid, event=event)
        return ModuleContent.objects.filter(module=module)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ModuleContentCreateSerializer
        return ModuleContentSerializer

    def perform_create(self, serializer):
        from events.models import Event

        event_uuid = self.kwargs.get('event_uuid')
        module_uuid = self.kwargs.get('module_uuid')

        event = get_object_or_404(Event, uuid=event_uuid, owner=self.request.user)
        module = get_object_or_404(EventModule, uuid=module_uuid, event=event)
        serializer.save(module=module)


@roles('organizer', 'course_manager', 'admin', route_name='assignments')
class AssignmentViewSet(viewsets.ModelViewSet):
    """
    Assignment management.

    GET /events/{event_uuid}/modules/{module_uuid}/assignments/ - List assignments
    POST /events/{event_uuid}/modules/{module_uuid}/assignments/ - Create assignment
    """

    permission_classes = [permissions.IsAuthenticated, IsOrganizerOrCourseManager]
    lookup_field = 'uuid'

    def get_queryset(self):
        from events.models import Event

        event_uuid = self.kwargs.get('event_uuid')
        module_uuid = self.kwargs.get('module_uuid')

        event = get_object_or_404(Event, uuid=event_uuid, owner=self.request.user)
        module = get_object_or_404(EventModule, uuid=module_uuid, event=event)
        return Assignment.objects.filter(module=module)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AssignmentCreateSerializer
        return AssignmentSerializer

    def perform_create(self, serializer):
        from events.models import Event

        event_uuid = self.kwargs.get('event_uuid')
        module_uuid = self.kwargs.get('module_uuid')

        event = get_object_or_404(Event, uuid=event_uuid, owner=self.request.user)
        module = get_object_or_404(EventModule, uuid=module_uuid, event=event)
        serializer.save(module=module)


@roles('attendee', 'organizer', 'course_manager', 'admin', route_name='attendee_submissions')
class AttendeeSubmissionViewSet(viewsets.ModelViewSet):
    """
    Attendee's assignment submissions.

    Allows attendees to submit and view their own submissions.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AssignmentSubmissionSerializer
    lookup_field = 'uuid'
    http_method_names = ['get', 'post', 'put', 'patch']

    def get_queryset(self):
        from django.db.models import Q

        from registrations.models import Registration

        registrations = Registration.objects.filter(user=self.request.user)
        return AssignmentSubmission.objects.filter(
            Q(registration__in=registrations) | Q(course_enrollment__user=self.request.user)
        ).select_related('assignment', 'registration', 'course_enrollment')

    def get_serializer_class(self):
        if self.action == 'create':
            return AssignmentSubmissionCreateSerializer
        return AssignmentSubmissionSerializer

    def create(self, request, *args, **kwargs):
        from learning.models import CourseEnrollment
        from registrations.models import Registration

        assignment_uuid = request.data.get('assignment')
        assignment = get_object_or_404(Assignment, uuid=assignment_uuid)

        # Determine context (Event vs Course)
        registration = None
        course_enrollment = None

        if assignment.module.event:
            # Event context
            registration = get_object_or_404(Registration, user=request.user, event=assignment.module.event)
            previous_submissions = AssignmentSubmission.objects.filter(assignment=assignment, registration=registration)
        else:
            # Course context
            # We need to find the enrollment. Since assignment -> module -> (maybe course module?)
            # But Module is EventModule.
            # If it's a course, we need to find the CourseEnrollment for the user that contains this module.
            # This is tricky because EventModule doesn't directly link to Course.
            # CourseModule links Course <-> EventModule.

            # Try to find a CourseEnrollment for this user that includes this module.
            # Course -> CourseModule -> EventModule
            enrollments = CourseEnrollment.objects.filter(
                user=request.user,
                course__modules__module=assignment.module,
                status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
            )
            if not enrollments.exists():
                return error_response('Not enrolled in the course for this assignment', code='NOT_ENROLLED')
            course_enrollment = enrollments.first()
            previous_submissions = AssignmentSubmission.objects.filter(
                assignment=assignment, course_enrollment=course_enrollment
            )

        # Check max attempts
        if assignment.max_attempts and previous_submissions.count() >= assignment.max_attempts:
            return error_response('Maximum attempts reached', code='MAX_ATTEMPTS_REACHED')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submission = serializer.save(
            assignment=assignment,
            registration=registration,
            course_enrollment=course_enrollment,
            attempt_number=previous_submissions.count() + 1,
        )

        return Response(AssignmentSubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Submit assignment",
        operation_description="Submit a draft assignment for grading.",
        responses={200: AssignmentSubmissionSerializer, 400: '{"error": "..."}'},
    )
    @action(detail=True, methods=['post'])
    def submit(self, request, uuid=None):
        """Submit the assignment."""
        submission = self.get_object()

        if submission.status == 'graded':
            return error_response('Submission already submitted', code='ALREADY_GRADED')

        submission.submit()
        return Response(AssignmentSubmissionSerializer(submission).data)


@roles('organizer', 'course_manager', 'admin', route_name='organizer_submissions')
class OrganizerSubmissionsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Organizer view of all submissions for their events.
    """

    permission_classes = [permissions.IsAuthenticated, IsOrganizerOrCourseManager]
    serializer_class = AssignmentSubmissionSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        return AssignmentSubmission.objects.filter(assignment__module__event__owner=self.request.user).select_related(
            'assignment', 'registration', 'registration__user'
        )

    @swagger_auto_schema(
        operation_summary="Grade submission",
        operation_description="Grade or return an assignment submission.",
        request_body=SubmissionGradeSerializer,
        responses={200: AssignmentSubmissionSerializer},
    )
    @action(detail=True, methods=['post'])
    def grade(self, request, uuid=None):
        """Grade a submission."""
        submission = self.get_object()
        serializer = SubmissionGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        action_type = data.get('action', 'grade')

        # Create review record
        review = SubmissionReview.objects.create(
            submission=submission,
            reviewer=request.user,
            action=action_type,
            from_status=submission.status,
            score=data.get('score'),
            feedback=data.get('feedback', ''),
            rubric_scores=data.get('rubric_scores', {}),
        )

        if action_type == 'grade':
            submission.grade(score=data['score'], feedback=data.get('feedback', ''), graded_by=request.user)
        elif action_type == 'return':
            submission.status = AssignmentSubmission.Status.NEEDS_REVISION
            submission.feedback = data.get('feedback', '')
            submission.save()
        elif action_type == 'approve':
            submission.status = AssignmentSubmission.Status.APPROVED
            submission.save()

        review.to_status = submission.status
        review.save()

        return Response(AssignmentSubmissionSerializer(submission).data)


@roles('attendee', 'organizer', 'course_manager', 'admin', route_name='my_learning')
class MyLearningViewSet(viewsets.GenericViewSet):
    """
    Attendee's learning dashboard.

    GET /users/me/learning/ - Overview of all learning
    GET /users/me/learning/{event_uuid}/ - Event-specific progress
    """

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """Get learning overview for all registered events."""
        from registrations.models import Registration

        registrations = Registration.objects.filter(user=request.user, status__in=['confirmed', 'attended']).select_related(
            'event'
        )

        dashboard_data = []
        for reg in registrations:
            event = reg.event
            modules = EventModule.objects.filter(event=event, is_published=True)

            module_progress = ModuleProgress.objects.filter(registration=reg, module__in=modules)

            completed = module_progress.filter(status='completed').count()
            total = modules.count()

            pending_assignments = AssignmentSubmission.objects.filter(
                registration=reg, status__in=['draft', 'needs_revision']
            ).count()

            cpd_earned = sum(mp.module.cpd_credits for mp in module_progress.filter(status='completed'))

            dashboard_data.append(
                {
                    'event_uuid': event.uuid,
                    'event_title': event.title,
                    'modules_total': total,
                    'modules_completed': completed,
                    'overall_progress': int((completed / total * 100) if total > 0 else 0),
                    'assignments_pending': pending_assignments,
                    'cpd_credits_earned': cpd_earned,
                    'modules': ModuleProgressSerializer(module_progress, many=True).data,
                }
            )

        return Response(dashboard_data)

    @swagger_auto_schema(
        operation_summary="Event learning progress",
        operation_description="Get detailed learning progress for a specific event.",
    )
    @action(detail=False, methods=['get'], url_path='(?P<event_uuid>[^/.]+)')
    def event_progress(self, request, event_uuid=None):
        """Get detailed progress for a specific event."""
        from events.models import Event
        from registrations.models import Registration

        event = get_object_or_404(Event, uuid=event_uuid)
        registration = get_object_or_404(Registration, user=request.user, event=event)

        modules = EventModule.objects.filter(event=event, is_published=True).prefetch_related('contents', 'assignments')

        module_data = []
        for module in modules:
            # Get module progress
            module_prog, _ = ModuleProgress.objects.get_or_create(
                registration=registration,
                module=module,
                defaults={'contents_total': module.contents.filter(is_required=True).count()},
            )

            # Get content progress
            content_prog = ContentProgress.objects.filter(registration=registration, content__module=module)

            # Get assignment submissions
            submissions = AssignmentSubmission.objects.filter(registration=registration, assignment__module=module)

            module_data.append(
                {
                    'module': EventModuleListSerializer(module).data,
                    'progress': ModuleProgressSerializer(module_prog).data,
                    'is_available': module.is_available_for_registration(registration),
                    'content_progress': ContentProgressSerializer(content_prog, many=True).data,
                    'submissions': AssignmentSubmissionSerializer(submissions, many=True).data,
                }
            )

        return Response({'event_uuid': event.uuid, 'event_title': event.title, 'modules': module_data})


@roles('attendee', 'organizer', 'course_manager', 'admin', route_name='content_progress')
class ContentProgressView(views.APIView):
    """
    Update content progress.

    POST /learning/progress/content/{content_uuid}/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, content_uuid):
        from learning.models import CourseEnrollment
        from registrations.models import Registration

        content = get_object_or_404(ModuleContent, uuid=content_uuid)

        # Determine context
        registration = None
        course_enrollment = None

        if content.module.event:
            # Event Context
            registration = get_object_or_404(Registration, user=request.user, event=content.module.event)
            # Verify progress query
            progress, created = ContentProgress.objects.get_or_create(registration=registration, content=content)
            module_prog, _ = ModuleProgress.objects.get_or_create(registration=registration, module=content.module)
        else:
            # Course Context
            enrollments = CourseEnrollment.objects.filter(
                user=request.user,
                course__modules__module=content.module,
                status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
            )
            if not enrollments.exists():
                return error_response('Not enrolled in course', code='NOT_ENROLLED')
            course_enrollment = enrollments.first()
            progress, created = ContentProgress.objects.get_or_create(course_enrollment=course_enrollment, content=content)
            module_prog, _ = ModuleProgress.objects.get_or_create(course_enrollment=course_enrollment, module=content.module)

        serializer = ContentProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if created:
            progress.start()

        if data.get('completed'):
            progress.complete()
        else:
            progress.update_progress(
                percent=data['progress_percent'], time_spent=data.get('time_spent', 0), position=data.get('position')
            )

        # Update module progress
        module_prog.update_from_content()
        module_prog.save()  # Ensure save

        if course_enrollment:
            course_enrollment.update_progress()

        return Response(ContentProgressSerializer(progress).data)


@roles('attendee', 'organizer', 'course_manager', 'admin', route_name='courses')
class CourseViewSet(viewsets.ModelViewSet):
    """
    Course management for organizations.
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        queryset = Course.objects.all()
        user = self.request.user

        # Filter by organization
        org_slug = self.request.query_params.get('org')
        if org_slug:
            queryset = queryset.filter(organization__slug=org_slug)

        # Filter by slug (for public view)
        slug = self.request.query_params.get('slug')
        if slug:
            queryset = queryset.filter(slug=slug)

        owned = self.request.query_params.get('owned')
        if owned and user.is_authenticated:
            queryset = queryset.filter(created_by=user)

        # Public visibility logic for non-authenticated users
        if not user.is_authenticated:
            return queryset.filter(is_public=True, status=Course.Status.PUBLISHED)

        if self.action in ['list', 'retrieve']:
            from organizations.models import OrganizationMembership

            memberships = OrganizationMembership.objects.filter(user=user, is_active=True)
            org_ids = memberships.filter(
                role__in=['admin', 'course_manager', 'organizer'],
            ).values_list('organization_id', flat=True)
            instructor_course_ids = memberships.filter(
                role='instructor',
                assigned_course__isnull=False,
            ).values_list('assigned_course_id', flat=True)

            return queryset.filter(
                models.Q(is_public=True, status=Course.Status.PUBLISHED)
                | models.Q(created_by=user)
                | models.Q(organization_id__in=org_ids)
                | models.Q(id__in=instructor_course_ids)
            ).distinct()

        return queryset.filter(
            models.Q(organization__memberships__user=user, organization__memberships__role__in=['admin', 'course_manager'])
            | models.Q(created_by=user)
        ).distinct()

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return CourseCreateSerializer
        return CourseSerializer

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied, ValidationError

        from organizations.models import Organization

        org_slug = self.request.data.get('organization_slug')
        organization = None

        if org_slug:
            try:
                org = Organization.objects.get(slug=org_slug)
            except Organization.DoesNotExist:
                raise ValidationError(f"Organization with slug '{org_slug}' not found")

            if not org.memberships.filter(
                user=self.request.user,
                role__in=['admin', 'course_manager'],
                is_active=True,
            ).exists():
                raise PermissionDenied("You do not have permission to create courses for this organization.")

            # Check organization subscription limits
            if hasattr(org, 'subscription'):
                org_subscription = org.subscription
                if not org_subscription.check_course_limit():
                    limit = org_subscription.config.get('courses_per_month')
                    raise PermissionDenied(
                        f"Organization has reached its course limit of {limit} courses this month. "
                        f"Please upgrade your plan to create more courses."
                    )

                # Increment organization course counter
                org_subscription.increment_courses()

            organization = org
        else:
            if self.request.user.account_type not in ['course_manager', 'admin']:
                raise PermissionDenied("Course manager account required to create courses.")

            subscription = getattr(self.request.user, 'subscription', None)
            if not subscription or not subscription.can_create_courses:
                raise PermissionDenied("Your subscription does not allow course creation.")

            subscription.increment_courses()

        serializer.save(organization=organization, created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, uuid=None):
        course = self.get_object()
        course.publish()
        return Response(CourseSerializer(course).data)

    @action(detail=True, methods=['get'], url_path='enrollments')
    def enrollments(self, request, uuid=None):
        """List enrollments for a course (staff/instructors)."""
        from rest_framework.exceptions import PermissionDenied

        course = self.get_object()
        if not (course.can_manage(request.user) or course.can_instruct(request.user)):
            raise PermissionDenied("You do not have access to this course's enrollments.")

        enrollments = CourseEnrollment.objects.filter(course=course).select_related('user').order_by('-enrolled_at')
        return Response(CourseEnrollmentRosterSerializer(enrollments, many=True).data)

    @action(detail=True, methods=['get'], url_path='progress')
    def progress(self, request, uuid=None):
        """Get detailed progress for a specific course enrollment."""
        from rest_framework.exceptions import PermissionDenied

        course = self.get_object()
        enrollment = CourseEnrollment.objects.filter(
            course=course,
            user=request.user,
            status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
        ).first()

        if not enrollment:
            raise PermissionDenied("You are not enrolled in this course.")

        modules = CourseModule.objects.filter(course=course).select_related('module').prefetch_related('module__contents')

        module_data = []
        for course_module in modules:
            module = course_module.module
            module_prog, _ = ModuleProgress.objects.get_or_create(
                course_enrollment=enrollment,
                module=module,
                defaults={'contents_total': module.contents.filter(is_required=True).count()},
            )
            content_prog = ContentProgress.objects.filter(course_enrollment=enrollment, content__module=module)

            module_data.append(
                {
                    'module': EventModuleListSerializer(module).data,
                    'progress': ModuleProgressSerializer(module_prog).data,
                    'is_available': module.is_available_for(request.user, course_enrollment=enrollment),
                    'content_progress': ContentProgressSerializer(content_prog, many=True).data,
                }
            )

        return Response(
            {
                'course_uuid': course.uuid,
                'course_title': course.title,
                'enrollment': CourseEnrollmentSerializer(enrollment).data,
                'modules': module_data,
            }
        )


@roles('attendee', 'organizer', 'course_manager', 'admin', route_name='course_enrollments')
class CourseEnrollmentViewSet(viewsets.ModelViewSet):
    """
    User enrollments in courses.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CourseEnrollmentSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        return CourseEnrollment.objects.filter(user=self.request.user).select_related('course')

    def perform_create(self, serializer):
        course_uuid = self.request.data.get('course_uuid')
        course = get_object_or_404(Course, uuid=course_uuid)

        if not course.is_free:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("This course requires payment. Please initiate checkout.")

        serializer.save(user=self.request.user, course=course)

    @swagger_auto_schema(
        operation_summary="Mark enrollment complete manually",
        operation_description="Mark a course enrollment as complete (instructor/manager override).",
        responses={200: CourseEnrollmentSerializer},
    )
    @action(detail=True, methods=['post'], url_path='mark-complete')
    def mark_complete(self, request, uuid=None):
        """
        Manually mark enrollment as complete (instructor/manager override).

        This allows course instructors or managers to mark a student's
        enrollment as complete regardless of quiz completion status.
        """
        from rest_framework.exceptions import PermissionDenied

        enrollment = self.get_object()
        course = enrollment.course

        # Check permission: must be course manager or instructor
        if not (course.can_manage(request.user) or course.can_instruct(request.user)):
            raise PermissionDenied("You do not have permission to mark this enrollment complete.")

        if enrollment.status == CourseEnrollment.Status.COMPLETED:
            return Response(
                {'detail': 'Enrollment is already completed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark complete manually
        enrollment.mark_complete_manually(completed_by=request.user)

        return Response(CourseEnrollmentSerializer(enrollment).data)

    @swagger_auto_schema(
        operation_summary="Checkout for paid course",
        operation_description="Create a Stripe checkout session for enrolling in a paid course.",
        responses={
            200: '{"session_id": "cs_xxx", "url": "https://checkout.stripe.com/..."}',
            400: '{"error": "..."}',
        },
    )
    @action(detail=False, methods=['post'], url_path='checkout')
    def checkout(self, request):
        """
        Create Stripe checkout session for paid course enrollment.

        Request body:
            course_uuid: UUID of the course to enroll in
            success_url: URL to redirect to on successful payment
            cancel_url: URL to redirect to if payment is cancelled
        """

        course_uuid = request.data.get('course_uuid')
        success_url = request.data.get('success_url')
        cancel_url = request.data.get('cancel_url')

        if not course_uuid:
            return Response(
                {'error': 'course_uuid is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not success_url or not cancel_url:
            return Response(
                {'error': 'success_url and cancel_url are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        course = get_object_or_404(Course, uuid=course_uuid)

        # Check if course is published
        if course.status != Course.Status.PUBLISHED:
            return Response(
                {'error': 'Course is not available for enrollment'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if already enrolled
        existing = CourseEnrollment.objects.filter(
            course=course,
            user=request.user,
            status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
        ).exists()

        if existing:
            return Response(
                {'error': 'You are already enrolled in this course'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if course is full
        if course.is_full:
            return Response(
                {'error': 'Course enrollment is full'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Free courses don't need checkout
        if course.is_free:
            # Just enroll directly
            enrollment = CourseEnrollment.objects.create(
                course=course,
                user=request.user,
                status=CourseEnrollment.Status.ACTIVE,
            )
            course.update_counts()
            return Response(
                {
                    'enrollment': CourseEnrollmentSerializer(enrollment).data,
                    'message': 'Enrolled in free course',
                },
                status=status.HTTP_201_CREATED,
            )

        # Create Stripe checkout session for paid course
        result = self._create_course_checkout_session(
            user=request.user,
            course=course,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        if result.get('success'):
            return Response(
                {
                    'session_id': result['session_id'],
                    'url': result['url'],
                }
            )
        else:
            return Response(
                {'error': result.get('error', 'Failed to create checkout session')},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def _create_course_checkout_session(self, user, course, success_url: str, cancel_url: str) -> dict:
        """
        Create Stripe checkout session for course enrollment.

        Uses Stripe Checkout with course-specific metadata for webhook handling.
        """
        import logging

        from django.conf import settings

        logger = logging.getLogger(__name__)

        try:
            import stripe

            stripe.api_key = settings.STRIPE_SECRET_KEY

            # Create or get Stripe customer
            from billing.services import stripe_service

            customer_id = stripe_service.create_customer(user)

            # Build line items
            # Use course's stripe_price_id if configured, otherwise create ad-hoc price
            if course.stripe_price_id:
                line_items = [
                    {
                        'price': course.stripe_price_id,
                        'quantity': 1,
                    }
                ]
            else:
                # Create ad-hoc price for one-time purchase
                line_items = [
                    {
                        'price_data': {
                            'currency': course.currency.lower(),
                            'product_data': {
                                'name': course.title,
                                'description': (
                                    course.short_description or course.description[:500] if course.description else None
                                ),
                            },
                            'unit_amount': course.price_cents,
                        },
                        'quantity': 1,
                    }
                ]

            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                mode='payment',  # One-time payment for course
                line_items=line_items,
                success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url,
                metadata={
                    'type': 'course_enrollment',
                    'course_uuid': str(course.uuid),
                    'course_title': course.title,
                    'user_id': str(user.id),
                    'user_email': user.email,
                },
                payment_intent_data={
                    'metadata': {
                        'type': 'course_enrollment',
                        'course_uuid': str(course.uuid),
                        'user_id': str(user.id),
                    },
                },
                # Transfer to course organization's connected account if applicable
                **(self._get_transfer_data(course) or {}),
            )

            logger.info(f"Created course checkout session {session.id} for course {course.uuid}")

            return {
                'success': True,
                'session_id': session.id,
                'url': session.url,
            }

        except Exception as e:
            logger.error(f"Course checkout session creation failed: {e}")
            return {
                'success': False,
                'error': str(e),
            }

    def _get_transfer_data(self, course) -> dict | None:
        """Get Stripe Connect transfer data for course payment."""
        if not course.organization:
            return None

        org = course.organization
        if not hasattr(org, 'subscription') or not org.subscription:
            return None

        connect_account_id = getattr(org.subscription, 'stripe_connect_account_id', None)
        if not connect_account_id:
            return None

        # Calculate platform fee (e.g., 10%)
        from django.conf import settings

        platform_fee_percent = getattr(settings, 'PLATFORM_FEE_PERCENT', 10)
        platform_fee = int(course.price_cents * platform_fee_percent / 100)

        return {
            'payment_intent_data': {
                'application_fee_amount': platform_fee,
                'transfer_data': {
                    'destination': connect_account_id,
                },
            },
        }


@roles('attendee', 'organizer', 'course_manager', 'instructor', 'admin', route_name='course_modules')
class CourseModuleViewSet(viewsets.ModelViewSet):
    """
    Manage modules within a course.

    Acts as a wrapper around EventModule creation but links to a Course.

    GET /courses/{course_uuid}/modules/
    POST /courses/{course_uuid}/modules/
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        course_uuid = self.kwargs.get('course_uuid')
        course = get_object_or_404(Course, uuid=course_uuid)

        # Staff and course managers can see full curriculum
        if course.can_manage(self.request.user) or course.can_instruct(self.request.user):
            return CourseModule.objects.filter(course=course).select_related('module').order_by('order')

        # Learners can only view published modules for enrolled courses
        enrolled = CourseEnrollment.objects.filter(
            user=self.request.user,
            course=course,
            status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
        ).exists()
        if enrolled:
            return (
                CourseModule.objects.filter(course=course, module__is_published=True).select_related('module').order_by('order')
            )

        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("You do not have access to this course.")

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            # Use EventModuleCreateSerializer effectively, but we need to handle the linking
            return EventModuleCreateSerializer
        return CourseModuleSerializer

    def perform_create(self, serializer):

        course_uuid = self.kwargs.get('course_uuid')
        course = get_object_or_404(Course, uuid=course_uuid)

        if not course.can_manage(self.request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this course.")

        # Create the EventModule (orphan)
        module = serializer.save(event=None)

        # Create the Link
        # Get next order
        last_item = CourseModule.objects.filter(course=course).order_by('-order').first()
        order = (last_item.order + 1) if last_item else 0

        CourseModule.objects.create(course=course, module=module, order=order)

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied

        course_uuid = self.kwargs.get('course_uuid')
        course = get_object_or_404(Course, uuid=course_uuid)
        if not course.can_manage(self.request.user):
            raise PermissionDenied("You do not have access to this course.")
        instance.delete()

    def perform_update(self, serializer):
        # We are updating the underlying EventModule
        # The viewset looks up CourseModule, but we want to update the linked module?
        # Actually standard ModelViewSet updates the queryset object (CourseModule).
        # We need to intercept this if we want to update the module title/desc.

        # BETTER APPROACH:
        # The frontend likely expects to edit module details.
        # If we return CourseModuleSerializer, it nests module.
        # So we should probably override get_object to return the EventModule?
        # OR, make CourseModuleSerializer writable?

        # Simpler: This viewset manages the LINKS (order, required status).
        # To edit content, use /modules/{uuid} directly?
        # But we want /courses/{uuid}/modules/{module_uuid} to feel like native editing.
        pass

    @action(detail=True, methods=['patch'])
    def update_content(self, request, course_uuid=None, uuid=None):
        """Update the underlying module content (title, desc, etc)."""
        course_link = self.get_object()  # This is CourseModule
        if not course_link.course.can_manage(self.request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this course.")
        module = course_link.module

        serializer = EventModuleCreateSerializer(module, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(CourseModuleSerializer(course_link).data)


@roles('attendee', 'organizer', 'course_manager', 'instructor', 'admin', route_name='course_module_content')
class CourseModuleContentViewSet(viewsets.ModelViewSet):
    """
    Content management for course modules.

    GET /courses/{course_uuid}/modules/{module_uuid}/contents/
    POST /courses/{course_uuid}/modules/{module_uuid}/contents/
    """

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    lookup_field = 'uuid'

    def get_queryset(self):
        course_uuid = self.kwargs.get('course_uuid')
        module_uuid = self.kwargs.get('module_uuid')
        course = get_object_or_404(Course, uuid=course_uuid)

        base_queryset = ModuleContent.objects.filter(
            module__uuid=module_uuid,
            module__course_links__course=course,
        )

        if course.can_manage(self.request.user) or course.can_instruct(self.request.user):
            return base_queryset.order_by('order')

        enrolled = CourseEnrollment.objects.filter(
            user=self.request.user,
            course=course,
            status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
        ).exists()
        if enrolled:
            return base_queryset.filter(
                module__is_published=True,
                is_published=True,
            ).order_by('order')

        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("You do not have access to this course.")

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ModuleContentCreateSerializer
        return ModuleContentSerializer

    def perform_create(self, serializer):
        course_uuid = self.kwargs.get('course_uuid')
        module_uuid = self.kwargs.get('module_uuid')

        # Verify access
        course = get_object_or_404(Course, uuid=course_uuid)
        if not course.can_manage(self.request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this course.")

        module = get_object_or_404(EventModule, uuid=module_uuid)
        # Ensure module links to this course to prevent cross-linking attacks
        if not CourseModule.objects.filter(course=course, module=module).exists():
            from rest_framework.exceptions import ValidationError

            raise ValidationError("Module does not belong to this course.")

        # Auto-calculate order if we are colliding or it's default 0
        current_data_order = serializer.validated_data.get('order', 0)

        # If order is 0 or exists, find the max and append
        if current_data_order == 0 or ModuleContent.objects.filter(module=module, order=current_data_order).exists():
            max_order = ModuleContent.objects.filter(module=module).aggregate(models.Max('order'))['order__max']
            next_order = (max_order or 0) + 1
            serializer.save(module=module, order=next_order)
        else:
            serializer.save(module=module)

    def perform_update(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        course_uuid = self.kwargs.get('course_uuid')
        course = get_object_or_404(Course, uuid=course_uuid)
        if not course.can_manage(self.request.user):
            raise PermissionDenied("You do not have access to this course.")
        serializer.save()

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied

        course_uuid = self.kwargs.get('course_uuid')
        course = get_object_or_404(Course, uuid=course_uuid)
        if not course.can_manage(self.request.user):
            raise PermissionDenied("You do not have access to this course.")
        instance.delete()


@roles('attendee', 'organizer', 'course_manager', 'instructor', 'admin', route_name='course_assignments')
class CourseAssignmentViewSet(viewsets.ModelViewSet):
    """
    Assignment management for course modules.

    GET /courses/{course_uuid}/modules/{module_uuid}/assignments/
    POST /courses/{course_uuid}/modules/{module_uuid}/assignments/
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def _get_course_and_module(self):
        course_uuid = self.kwargs.get('course_uuid')
        module_uuid = self.kwargs.get('module_uuid')
        course = get_object_or_404(Course, uuid=course_uuid)
        module = get_object_or_404(EventModule, uuid=module_uuid)

        if not CourseModule.objects.filter(course=course, module=module).exists():
            from rest_framework.exceptions import ValidationError

            raise ValidationError("Module does not belong to this course.")

        return course, module

    def get_queryset(self):
        course, module = self._get_course_and_module()

        if course.can_manage(self.request.user) or course.can_instruct(self.request.user):
            return Assignment.objects.filter(module=module)

        enrolled = CourseEnrollment.objects.filter(
            user=self.request.user,
            course=course,
            status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
        ).exists()
        if enrolled and module.is_published:
            return Assignment.objects.filter(module=module)

        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied("You do not have access to this course.")

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AssignmentCreateSerializer
        return AssignmentSerializer

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        course, module = self._get_course_and_module()
        if not (course.can_manage(self.request.user) or course.can_instruct(self.request.user)):
            raise PermissionDenied("You do not have access to this course.")
        serializer.save(module=module)

    def perform_update(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        course, _ = self._get_course_and_module()
        if not (course.can_manage(self.request.user) or course.can_instruct(self.request.user)):
            raise PermissionDenied("You do not have access to this course.")
        serializer.save()

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied

        course, _ = self._get_course_and_module()
        if not (course.can_manage(self.request.user) or course.can_instruct(self.request.user)):
            raise PermissionDenied("You do not have access to this course.")
        instance.delete()


@roles('organizer', 'course_manager', 'instructor', 'admin', route_name='course_submissions')
class CourseSubmissionsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Course staff view of submissions for a course.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AssignmentSubmissionStaffSerializer
    lookup_field = 'uuid'

    def get_course(self):
        course_uuid = self.kwargs.get('course_uuid')
        return get_object_or_404(Course, uuid=course_uuid)

    def get_queryset(self):
        course = self.get_course()
        if not (course.can_manage(self.request.user) or course.can_instruct(self.request.user)):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this course.")

        return AssignmentSubmission.objects.filter(course_enrollment__course=course).select_related(
            'assignment', 'course_enrollment__user'
        )

    @action(detail=True, methods=['post'])
    def grade(self, request, course_uuid=None, uuid=None):
        """Grade or return a submission."""
        submission = self.get_object()
        serializer = SubmissionGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        action_type = data.get('action', 'grade')

        review = SubmissionReview.objects.create(
            submission=submission,
            reviewer=request.user,
            action=action_type,
            from_status=submission.status,
            score=data.get('score'),
            feedback=data.get('feedback', ''),
            rubric_scores=data.get('rubric_scores', {}),
        )

        if action_type == 'grade':
            submission.grade(score=data['score'], feedback=data.get('feedback', ''), graded_by=request.user)
        elif action_type == 'return':
            submission.status = AssignmentSubmission.Status.NEEDS_REVISION
            submission.feedback = data.get('feedback', '')
            submission.save()
        elif action_type == 'approve':
            submission.status = AssignmentSubmission.Status.APPROVED
            submission.save()

        review.to_status = submission.status
        review.save()

        # Check if course should be completed after grading
        if submission.course_enrollment:
            submission.course_enrollment.check_completion()

        return Response(AssignmentSubmissionStaffSerializer(submission).data)


@roles('attendee', 'organizer', 'course_manager', 'instructor', 'admin', route_name='course_announcements')
class CourseAnnouncementViewSet(viewsets.ModelViewSet):
    """
    Announcements for a course.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CourseAnnouncementSerializer
    lookup_field = 'uuid'

    def get_course(self):
        course_uuid = self.kwargs.get('course_uuid')
        return get_object_or_404(Course, uuid=course_uuid)

    def _is_course_staff(self, course):
        return course.can_manage(self.request.user) or course.can_instruct(self.request.user)

    def get_queryset(self):
        course = self.get_course()
        queryset = CourseAnnouncement.objects.filter(course=course)

        if self._is_course_staff(course):
            return queryset

        enrolled = CourseEnrollment.objects.filter(
            user=self.request.user,
            course=course,
            status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
        ).exists()
        if not enrolled:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this course.")

        return queryset.filter(is_published=True)

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        course = self.get_course()
        if not self._is_course_staff(course):
            raise PermissionDenied("You do not have access to this course.")
        serializer.save(course=course, created_by=self.request.user)

    def perform_update(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        course = self.get_course()
        if not self._is_course_staff(course):
            raise PermissionDenied("You do not have access to this course.")
        serializer.save()

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied

        course = self.get_course()
        if not self._is_course_staff(course):
            raise PermissionDenied("You do not have access to this course.")
        instance.delete()
