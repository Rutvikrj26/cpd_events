"""
Learning API views.
"""

from django.shortcuts import get_object_or_404
from django.db import models
from rest_framework import permissions, status, views, viewsets, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from common.utils import error_response
from drf_yasg.utils import swagger_auto_schema

from common.permissions import IsOrganizer

from .models import (
    Assignment,
    AssignmentSubmission,
    ContentProgress,
    Course,
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
    ContentProgressSerializer,
    ContentProgressUpdateSerializer,
    CourseCreateSerializer,
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


class EventModuleViewSet(viewsets.ModelViewSet):
    """
    Event module management.

    GET /events/{event_uuid}/modules/ - List modules
    POST /events/{event_uuid}/modules/ - Create module
    GET /events/{event_uuid}/modules/{uuid}/ - Module detail
    PUT/PATCH /events/{event_uuid}/modules/{uuid}/ - Update module
    DELETE /events/{event_uuid}/modules/{uuid}/ - Delete module
    """

    permission_classes = [permissions.IsAuthenticated, IsOrganizer]
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


class ModuleContentViewSet(viewsets.ModelViewSet):
    """
    Module content management.

    GET /events/{event_uuid}/modules/{module_uuid}/contents/ - List contents
    POST /events/{event_uuid}/modules/{module_uuid}/contents/ - Create content
    """

    permission_classes = [permissions.IsAuthenticated, IsOrganizer]
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


class AssignmentViewSet(viewsets.ModelViewSet):
    """
    Assignment management.

    GET /events/{event_uuid}/modules/{module_uuid}/assignments/ - List assignments
    POST /events/{event_uuid}/modules/{module_uuid}/assignments/ - Create assignment
    """

    permission_classes = [permissions.IsAuthenticated, IsOrganizer]
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
        from registrations.models import Registration

        registrations = Registration.objects.filter(user=self.request.user)
        return AssignmentSubmission.objects.filter(registration__in=registrations).select_related('assignment', 'registration')

    def get_serializer_class(self):
        if self.action == 'create':
            return AssignmentSubmissionCreateSerializer
        return AssignmentSubmissionSerializer

    def create(self, request, *args, **kwargs):
        from registrations.models import Registration

        assignment_uuid = request.data.get('assignment')
        assignment = get_object_or_404(Assignment, uuid=assignment_uuid)

        # Find registration for this event
        registration = get_object_or_404(Registration, user=request.user, event=assignment.module.event)

        # Check attempt limits
        previous_submissions = AssignmentSubmission.objects.filter(assignment=assignment, registration=registration)
        # Check max attempts
        if assignment.max_attempts and previous_submissions.count() >= assignment.max_attempts:
            return error_response('Maximum attempts reached', code='MAX_ATTEMPTS_REACHED')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submission = serializer.save(assignment=assignment, registration=registration, attempt_number=previous_submissions.count() + 1)

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


class OrganizerSubmissionsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Organizer view of all submissions for their events.
    """

    permission_classes = [permissions.IsAuthenticated, IsOrganizer]
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


class ContentProgressView(views.APIView):
    """
    Update content progress.

    POST /learning/progress/content/{content_uuid}/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, content_uuid):
        from registrations.models import Registration

        content = get_object_or_404(ModuleContent, uuid=content_uuid)

        # Find registration
        registration = get_object_or_404(Registration, user=request.user, event=content.module.event)

        serializer = ContentProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        progress, created = ContentProgress.objects.get_or_create(registration=registration, content=content)

        if created:
            progress.start()

        data = serializer.validated_data

        if data.get('completed'):
            progress.complete()
        else:
            progress.update_progress(
                percent=data['progress_percent'], time_spent=data.get('time_spent', 0), position=data.get('position')
            )

        # Update module progress
        module_prog, _ = ModuleProgress.objects.get_or_create(registration=registration, module=content.module)
        module_prog.update_from_content()

        return Response(ContentProgressSerializer(progress).data)

class CourseViewSet(viewsets.ModelViewSet):
    """
    Course management for organizations.
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        queryset = Course.objects.all()
        
        # Filter by organization
        org_slug = self.request.query_params.get('org')
        if org_slug:
            queryset = queryset.filter(organization__slug=org_slug)
            
        # Filter by slug (for public view)
        slug = self.request.query_params.get('slug')
        if slug:
            queryset = queryset.filter(slug=slug)

        # Public visibility logic for non-authenticated users
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_public=True)
            
        return queryset

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
        from organizations.models import Organization
        from rest_framework.exceptions import ValidationError, PermissionDenied

        org_slug = self.request.data.get('organization_slug')
        if not org_slug:
            raise ValidationError("Courses must belong to an organization. Please provide 'organization_slug'.")

        try:
            org = Organization.objects.get(slug=org_slug)

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

            serializer.save(organization=org, created_by=self.request.user)

        except Organization.DoesNotExist:
            raise ValidationError(f"Organization with slug '{org_slug}' not found")

    @action(detail=True, methods=['post'])
    def publish(self, request, uuid=None):
        course = self.get_object()
        course.publish()
        return Response(CourseSerializer(course).data)


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
        serializer.save(user=self.request.user, course=course)


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
        # Return CourseModules, but user might expect EventModule data structure?
        # The design is: Course -> CourseModule -> EventModule
        # Let's return the nested EventModule structure via serializer
        return CourseModule.objects.filter(course__uuid=course_uuid, course__organization__memberships__user=self.request.user).select_related('module').order_by('order')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
             # Use EventModuleCreateSerializer effectively, but we need to handle the linking
             return EventModuleCreateSerializer
        return CourseModuleSerializer

    def perform_create(self, serializer):
        from events.models import Event
        
        course_uuid = self.kwargs.get('course_uuid')
        course = get_object_or_404(Course, uuid=course_uuid)
        
        # Verify permissions (basic check, ideally use proper permission class)
        if not course.organization.memberships.filter(user=self.request.user).exists():
             raise permissions.PermissionDenied("You do not have access to this course.")

        # Create the EventModule (orphan)
        module = serializer.save(event=None)
        
        # Create the Link
        # Get next order
        last_item = CourseModule.objects.filter(course=course).order_by('-order').first()
        order = (last_item.order + 1) if last_item else 0
        
        CourseModule.objects.create(course=course, module=module, order=order)

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
        course_link = self.get_object() # This is CourseModule
        module = course_link.module
        
        serializer = EventModuleCreateSerializer(module, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(CourseModuleSerializer(course_link).data)


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
        
        course_uuid = self.kwargs.get('course_uuid')
        module_uuid = self.kwargs.get('module_uuid')
        
        print(f"DEBUG: CourseModuleContentViewSet.get_queryset course={course_uuid} module={module_uuid} user={self.request.user}")

        # Ensure user has access to the course organization
        return ModuleContent.objects.filter(
            module__uuid=module_uuid,
            module__course_links__course__uuid=course_uuid,
            module__course_links__course__organization__memberships__user=self.request.user
        ).order_by('order')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ModuleContentCreateSerializer
        return ModuleContentSerializer

    def perform_create(self, serializer):
        course_uuid = self.kwargs.get('course_uuid')
        module_uuid = self.kwargs.get('module_uuid')
        
        # Verify access
        course = get_object_or_404(Course, uuid=course_uuid)
        if not course.organization.memberships.filter(user=self.request.user).exists():
             raise permissions.PermissionDenied("You do not have access to this course.")
             
        module = get_object_or_404(EventModule, uuid=module_uuid)
        # Ensure module links to this course to prevent cross-linking attacks
        # Ensure module links to this course to prevent cross-linking attacks
        if not CourseModule.objects.filter(course=course, module=module).exists():
            raise serializers.ValidationError("Module does not belong to this course.")

        # Auto-calculate order if we are colliding or it's default 0
        current_data_order = serializer.validated_data.get('order', 0)
        
        # If order is 0 or exists, find the max and append
        if current_data_order == 0 or ModuleContent.objects.filter(module=module, order=current_data_order).exists():
            max_order = ModuleContent.objects.filter(module=module).aggregate(models.Max('order'))['order__max']
            next_order = (max_order or 0) + 1
            serializer.save(module=module, order=next_order)
        else:
            serializer.save(module=module)
