"""
Learning API views.
"""

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from common.utils import error_response
from drf_yasg.utils import swagger_auto_schema

from common.permissions import IsOrganizer

from .models import (
    Assignment,
    AssignmentSubmission,
    ContentProgress,
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
