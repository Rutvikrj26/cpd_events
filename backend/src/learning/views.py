"""
Learning API views.
"""

import logging

from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiResponse,
    PolymorphicProxySerializer,
    extend_schema,
    inline_serializer,
)

# Bootstrap response shapes — explicit class refs so drf-spectacular's
# PolymorphicProxySerializer resolves them at schema-generation time.
from learning.bootstrap_serializers import (
    CoursePlayerGrantedSerializer,
    CoursePlayerPendingApprovalSerializer,
    CoursePlayerRedirectSerializer,
)
from rest_framework import generics, parsers, permissions, serializers, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from common.permissions import IsContentCreator
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
    CourseStaff,
    DiscussionFlag,
    DiscussionReply,
    DiscussionThread,
    EventModule,
    ModuleContent,
    ModuleProgress,
    Program,
    ProgramCourse,
    ProgramEnrollment,
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
    CourseMemberMiniSerializer,
    DiscussionFlagCreateSerializer,
    DiscussionFlagSerializer,
    DiscussionReplyCreateSerializer,
    DiscussionReplySerializer,
    DiscussionThreadCreateSerializer,
    DiscussionThreadDetailSerializer,
    DiscussionThreadListSerializer,
    DiscussionThreadUpdateSerializer,
    CourseCreateSerializer,
    CourseEnrollmentRosterSerializer,
    CourseEnrollmentSerializer,
    CourseListSerializer,
    CourseModuleSerializer,
    CourseSerializer,
    CourseStaffCreateSerializer,
    CourseStaffSerializer,
    EventModuleCreateSerializer,
    EventModuleListSerializer,
    EventModuleSerializer,
    ModuleContentCreateSerializer,
    ModuleContentSerializer,
    ModuleProgressSerializer,
    ProgramCourseEntrySerializer,
    ProgramCreateSerializer,
    ProgramEnrollmentRosterSerializer,
    ProgramEnrollmentSerializer,
    ProgramListSerializer,
    ProgramSerializer,
    SubmissionGradeSerializer,
)


@roles('organizer', 'instructor', 'admin', route_name='event_modules')
class EventModuleViewSet(viewsets.ModelViewSet):
    """
    Event module management.

    GET /events/{event_uuid}/modules/ - List modules
    POST /events/{event_uuid}/modules/ - Create module
    GET /events/{event_uuid}/modules/{uuid}/ - Module detail
    PUT/PATCH /events/{event_uuid}/modules/{uuid}/ - Update module
    DELETE /events/{event_uuid}/modules/{uuid}/ - Delete module
    """

    permission_classes = [permissions.IsAuthenticated, IsContentCreator]
    lookup_field = 'uuid'

    def _get_event(self):
        from events.models import Event

        event_uuid = self.kwargs.get('event_uuid')
        if self.request.user.groups.filter(name="admin").exists():
            return get_object_or_404(Event, uuid=event_uuid)
        return get_object_or_404(Event, uuid=event_uuid, owner=self.request.user)

    def get_queryset(self):
        event = self._get_event()
        return EventModule.objects.filter(event=event).prefetch_related('contents', 'assignments')

    def get_serializer_class(self):
        if self.action == 'list':
            return EventModuleListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return EventModuleCreateSerializer
        return EventModuleSerializer

    def perform_create(self, serializer):
        event = self._get_event()
        serializer.save(event=event)

    @action(detail=True, methods=['post'])
    def publish(self, request, event_uuid=None, uuid=None):
        """Publish a module."""
        module = self.get_object()
        module.is_published = True
        module.save()
        return Response(EventModuleSerializer(module).data)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, event_uuid=None, uuid=None):
        """Unpublish a module."""
        module = self.get_object()
        module.is_published = False
        module.save()
        return Response(EventModuleSerializer(module).data)


@roles('organizer', 'instructor', 'admin', route_name='module_content')
class ModuleContentViewSet(viewsets.ModelViewSet):
    """
    Module content management.

    GET /events/{event_uuid}/modules/{module_uuid}/contents/ - List contents
    POST /events/{event_uuid}/modules/{module_uuid}/contents/ - Create content
    """

    permission_classes = [permissions.IsAuthenticated, IsContentCreator]
    lookup_field = 'uuid'

    def _get_event_and_module(self):
        from events.models import Event

        event_uuid = self.kwargs.get('event_uuid')
        module_uuid = self.kwargs.get('module_uuid')

        if self.request.user.groups.filter(name="admin").exists():
            event = get_object_or_404(Event, uuid=event_uuid)
        else:
            event = get_object_or_404(Event, uuid=event_uuid, owner=self.request.user)
        module = get_object_or_404(EventModule, uuid=module_uuid, event=event)
        return event, module

    def get_queryset(self):
        _, module = self._get_event_and_module()
        return ModuleContent.objects.filter(module=module)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ModuleContentCreateSerializer
        return ModuleContentSerializer

    def perform_create(self, serializer):
        _, module = self._get_event_and_module()
        serializer.save(module=module)


def _get_event_for_user(user, event_uuid):
    """Helper: get event, allowing admin to access any event."""
    from events.models import Event

    if user.groups.filter(name="admin").exists():
        return get_object_or_404(Event, uuid=event_uuid)
    return get_object_or_404(Event, uuid=event_uuid, owner=user)


@roles('organizer', 'instructor', 'admin', route_name='assignments')
class AssignmentViewSet(viewsets.ModelViewSet):
    """
    Assignment management.

    GET /events/{event_uuid}/modules/{module_uuid}/assignments/ - List assignments
    POST /events/{event_uuid}/modules/{module_uuid}/assignments/ - Create assignment
    """

    permission_classes = [permissions.IsAuthenticated, IsContentCreator]
    lookup_field = 'uuid'

    def _get_module(self):
        event = _get_event_for_user(self.request.user, self.kwargs.get('event_uuid'))
        return get_object_or_404(EventModule, uuid=self.kwargs.get('module_uuid'), event=event)

    def get_queryset(self):
        module = self._get_module()
        return Assignment.objects.filter(module=module)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AssignmentCreateSerializer
        return AssignmentSerializer

    def perform_create(self, serializer):
        module = self._get_module()
        serializer.save(module=module)


@roles('learner', 'organizer', 'instructor', 'admin', route_name='attendee_submissions')
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

    @action(detail=True, methods=['post'])
    def submit(self, request, uuid=None):
        """Submit the assignment."""
        submission = self.get_object()

        if submission.status == 'graded':
            return error_response('Submission already submitted', code='ALREADY_GRADED')

        submission.submit()
        return Response(AssignmentSubmissionSerializer(submission).data)


@roles('organizer', 'instructor', 'admin', route_name='organizer_submissions')
class OrganizerSubmissionsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Organizer view of all submissions for their events.
    """

    permission_classes = [permissions.IsAuthenticated, IsContentCreator]
    serializer_class = AssignmentSubmissionSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        qs = AssignmentSubmission.objects.select_related('assignment', 'registration', 'registration__user')
        if self.request.user.groups.filter(name="admin").exists():
            return qs
        return qs.filter(assignment__module__event__owner=self.request.user)

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


@roles('learner', 'organizer', 'instructor', 'admin', route_name='my_learning')
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


@roles('learner', 'organizer', 'instructor', 'admin', route_name='content_progress')
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
            course_enrollment.start()
            progress, created = ContentProgress.objects.get_or_create(course_enrollment=course_enrollment, content=content)
            module_prog, _ = ModuleProgress.objects.get_or_create(course_enrollment=course_enrollment, module=content.module)

        serializer = ContentProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if created:
            progress.start()

        if data.get('completed'):
            progress.complete(time_spent=data.get('time_spent', 0), position=data.get('position'))
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


@roles('learner', 'organizer', 'instructor', 'admin', route_name='courses')
class CourseViewSet(viewsets.ModelViewSet):
    """
    Course management.
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        queryset = Course.objects.all()
        user = self.request.user

        # Filter by slug (for public view)
        slug = self.request.query_params.get('slug')
        if slug:
            queryset = queryset.filter(slug=slug)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search)
                | models.Q(short_description__icontains=search)
                | models.Q(description__icontains=search)
            )

        # Admin sees everything (regardless of owned param)
        if user.groups.filter(name="admin").exists():
            return queryset.distinct()

        # Public visibility logic for non-authenticated users
        if not user.is_authenticated:
            return queryset.filter(is_public=True, status=Course.Status.PUBLISHED)

        owned = self.request.query_params.get('owned')
        if owned:
            return queryset.filter(
                models.Q(created_by=user) | models.Q(staff_assignments__user=user)
            ).distinct()

        if self.action in ['list', 'retrieve', 'progress', 'player_bootstrap']:
            # Learner-facing read actions: visible if the course is public
            # AND published, OR if the learner has any relationship with it
            # (enrollment in any state — including pending/dropped — or
            # staffs/owns it). The relationship visibility matters for the
            # bootstrap so that pending/dropped enrollments still get a
            # response (we want the discriminated `pending_approval` /
            # `redirect_to_detail` shells to render, not a 404).
            return queryset.filter(
                models.Q(is_public=True, status=Course.Status.PUBLISHED)
                | models.Q(created_by=user)
                | models.Q(staff_assignments__user=user)
                | models.Q(enrollments__user=user)
            ).distinct()

        return queryset.filter(
            models.Q(created_by=user) | models.Q(staff_assignments__user=user)
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
        from rest_framework.exceptions import PermissionDenied

        if not self.request.user.has_perm("learning.can_create_course"):
            raise PermissionDenied("You do not have permission to create courses.")
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        from rest_framework.exceptions import PermissionDenied
        if not serializer.instance.can_manage(self.request.user):
            raise PermissionDenied("You do not have permission to update this course.")

        # Capture price/currency before save so we can audit any change.
        old = serializer.instance
        old_price_cents = old.price_cents
        old_currency = old.currency

        instance = serializer.save()

        if instance.price_cents != old_price_cents or instance.currency != old_currency:
            try:
                from accounts.audit import log_audit_event

                log_audit_event(
                    actor=self.request.user,
                    action='course.price_changed',
                    object_type='Course',
                    object_uuid=str(instance.uuid),
                    metadata={
                        'from_price_cents': old_price_cents,
                        'to_price_cents': instance.price_cents,
                        'from_currency': old_currency,
                        'to_currency': instance.currency,
                    },
                    request=self.request,
                )
            except Exception:
                logger.warning('audit log failed for course price change %s', instance.uuid, exc_info=True)

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied
        if not instance.can_manage(self.request.user):
            raise PermissionDenied("You do not have permission to delete this course.")
        instance.delete()

    @action(detail=True, methods=['post'])
    def publish(self, request, uuid=None):
        from rest_framework.exceptions import PermissionDenied
        course = self.get_object()
        if not course.can_manage(request.user):
            raise PermissionDenied("You do not have permission to publish this course.")
        course.publish()
        return Response(CourseSerializer(course).data)

    @action(detail=True, methods=['post'], url_path='invite')
    def invite(self, request, uuid=None):
        """Bulk-invite learners to this course by email or contact_uuid.

        See `accounts.services.create_invitations` for resolution rules.
        Gated by `course.can_manage` — owners + assigned staff + admins.
        """
        from rest_framework.exceptions import PermissionDenied
        from accounts.serializers import (
            InviteCreateSerializer,
            LearningInvitationSerializer,
        )
        from accounts.services import create_invitations
        from accounts.models import LearningInvitation

        course = self.get_object()
        if not course.can_manage(request.user):
            raise PermissionDenied("You do not have permission to invite learners to this course.")

        ser = InviteCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = create_invitations(
            inviter=request.user,
            target_type=LearningInvitation.TargetType.COURSE,
            target=course,
            invitees=ser.validated_data['invitees'],
            personal_message=ser.validated_data.get('personal_message', ''),
            comp=ser.validated_data.get('comp', False),
        )

        created_uuids = [r.invitation_uuid for r in result.created if r.invitation_uuid]
        refreshed_uuids = [r.invitation_uuid for r in result.refreshed if r.invitation_uuid]
        invitation_qs = LearningInvitation.objects.filter(
            uuid__in=created_uuids + refreshed_uuids,
        ).select_related('event', 'course', 'invited_by', 'contact')

        return Response({
            'invitations': LearningInvitationSerializer(invitation_qs, many=True).data,
            'created': [{'email': r.email, 'invitation_uuid': r.invitation_uuid} for r in result.created],
            'refreshed': [{'email': r.email, 'invitation_uuid': r.invitation_uuid} for r in result.refreshed],
            'skipped': [{'email': r.email, 'reason': r.status, 'detail': r.reason} for r in result.skipped],
        })

    @action(detail=True, methods=['get'], url_path='invitations')
    def invitations(self, request, uuid=None):
        """List invitations for a course (manage permission required)."""
        from rest_framework.exceptions import PermissionDenied
        from accounts.models import LearningInvitation
        from accounts.serializers import LearningInvitationSerializer

        course = self.get_object()
        if not course.can_manage(request.user):
            raise PermissionDenied("You do not have permission to view invitations for this course.")
        qs = (
            LearningInvitation.objects
            .filter(course=course)
            .select_related('invited_by', 'contact')
            .order_by('-created_at')
        )
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(LearningInvitationSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def reports(self, request):
        """Summary, trends, and recent activity for the requester's courses."""
        from datetime import datetime, timedelta

        from django.db.models import Count
        from django.db.models.functions import TruncDate
        from django.utils import timezone
        from rest_framework.exceptions import PermissionDenied

        user = request.user
        if not user.groups.filter(name__in=['instructor', 'admin']).exists():
            raise PermissionDenied('Course reports are limited to instructors and admins.')

        if user.groups.filter(name='admin').exists():
            courses = Course.objects.all()
        else:
            courses = Course.objects.filter(
                models.Q(created_by=user) | models.Q(staff_assignments__user=user)
            ).distinct()

        now = timezone.now()
        period = request.query_params.get('period', 'last-30-days')
        if period == 'last-7-days':
            start = now - timedelta(days=7)
        elif period == 'last-90-days':
            start = now - timedelta(days=90)
        elif period == 'this-year':
            start = timezone.make_aware(datetime(now.year, 1, 1))
        else:
            start = now - timedelta(days=30)

        enrollments = CourseEnrollment.objects.filter(
            course__in=courses,
            enrolled_at__gte=start,
            enrolled_at__lte=now,
        )

        total_enrollments = enrollments.count()
        completions_in_period = CourseEnrollment.objects.filter(
            course__in=courses,
            completed_at__gte=start,
            completed_at__lte=now,
        ).count()

        completion_rate = None
        if total_enrollments:
            completion_rate = round((completions_in_period / total_enrollments) * 100, 1)

        trends = []
        for row in (
            enrollments.annotate(day=TruncDate('enrolled_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        ):
            trends.append(
                {
                    'date': row['day'].isoformat() if row['day'] else None,
                    'count': row['count'],
                }
            )

        status_breakdown = [
            {'label': 'Active', 'count': enrollments.filter(status=CourseEnrollment.Status.ACTIVE).count()},
            {'label': 'Completed', 'count': enrollments.filter(status=CourseEnrollment.Status.COMPLETED).count()},
            {'label': 'Dropped', 'count': enrollments.filter(status=CourseEnrollment.Status.DROPPED).count()},
        ]

        recent_enrollments = [
            {
                'enrollment_uuid': str(e.uuid),
                'course_title': e.course.title if e.course else '',
                'user_name': getattr(e.user, 'full_name', None) or getattr(e.user, 'email', ''),
                'progress_percent': e.progress_percent,
                'status': e.status,
                'enrolled_at': e.enrolled_at.isoformat(),
            }
            for e in enrollments.select_related('course', 'user').order_by('-enrolled_at')[:5]
        ]

        top_courses = [
            {
                'uuid': str(c.uuid),
                'title': c.title,
                'enrollments': c.period_enrollments,
            }
            for c in courses.annotate(
                period_enrollments=Count(
                    'enrollments',
                    filter=models.Q(
                        enrollments__enrolled_at__gte=start,
                        enrollments__enrolled_at__lte=now,
                    ),
                )
            ).order_by('-period_enrollments')[:5]
            if c.period_enrollments
        ]

        # --- Revenue (CoursePurchase, course-scoped) ---------------------
        from django.db.models import Sum

        from billing.models import CoursePurchase

        purchases_in_period = CoursePurchase.objects.filter(
            course__in=courses,
            created_at__gte=start,
            created_at__lte=now,
        )
        completed = purchases_in_period.filter(status=CoursePurchase.Status.COMPLETED)
        refunded = purchases_in_period.filter(status=CoursePurchase.Status.REFUNDED)

        gross_cents = completed.aggregate(total=Sum('amount_cents'))['total'] or 0
        refund_cents = refunded.aggregate(total=Sum('amount_cents'))['total'] or 0
        net_cents = gross_cents - refund_cents

        recent_transactions = [
            {
                'purchase_uuid': str(p.uuid),
                'course_title': p.course.title if p.course else '',
                'user_name': getattr(p.user, 'full_name', None) or getattr(p.user, 'email', ''),
                'amount_cents': p.amount_cents,
                'currency': p.currency,
                'status': p.status,
                'created_at': p.created_at.isoformat() if p.created_at else None,
            }
            for p in purchases_in_period.select_related('course', 'user').order_by('-created_at')[:10]
        ]

        return Response(
            {
                'summary': {
                    'total_enrollments': total_enrollments,
                    'completions': completions_in_period,
                    'completion_rate': completion_rate,
                    'courses_published': courses.filter(status=Course.Status.PUBLISHED).count(),
                    'gross_revenue_cents': gross_cents,
                    'refunds_cents': refund_cents,
                    'net_revenue_cents': net_cents,
                    'purchase_count': completed.count(),
                    'refund_count': refunded.count(),
                },
                'trends': trends,
                'status_breakdown': status_breakdown,
                'recent_enrollments': recent_enrollments,
                'top_courses': top_courses,
                'recent_transactions': recent_transactions,
            }
        )

    @action(detail=True, methods=['get'], url_path='enrollments')
    def enrollments(self, request, uuid=None):
        """List enrollments for a course (staff/instructors)."""
        from rest_framework.exceptions import PermissionDenied

        course = self.get_object()
        if not (course.can_manage(request.user) or course.can_instruct(request.user)):
            raise PermissionDenied("You do not have access to this course's enrollments.")

        enrollments = CourseEnrollment.objects.filter(course=course).select_related('user').order_by('-enrolled_at')
        return Response(CourseEnrollmentRosterSerializer(enrollments, many=True).data)

    # Refund moved to the unified billing endpoint:
    # ``POST /api/v1/billing/purchases/{purchase_uuid}/refund/``.
    # See ``billing.views.RefundPurchaseView``.

    # The legacy /progress/ endpoint was replaced by the player_bootstrap
    # action below. The bootstrap returns one composite payload — course +
    # modules + module progress + sessions + announcements + the
    # discriminated access decision — eliminating the 6-fetch composition
    # the frontend used to do (and the racing 403s that came with it).

    @extend_schema(
        responses={
            200: PolymorphicProxySerializer(
                component_name='CoursePlayerBootstrap',
                serializers=[
                    CoursePlayerGrantedSerializer,
                    CoursePlayerPendingApprovalSerializer,
                    CoursePlayerRedirectSerializer,
                ],
                # The discriminator key lives at `access.kind` (nested), which
                # OpenAPI 3.0 cannot model with a single top-level field.
                # Spectacular emits a `oneOf` and the TS consumer
                # exhaustively narrows on `access.kind` at runtime.
                resource_type_field_name=None,
            ),
        },
        description=(
            'One fetch returns everything the course player needs to render '
            'its initial paint, plus a discriminated `access` field telling '
            'the client which shell to render: full player (granted), '
            'pending-approval banner (pending_approval), or a navigation '
            'hint to the catalog page (redirect_to_detail).'
        ),
    )
    @action(detail=True, methods=['get'], url_path='player-bootstrap')
    def player_bootstrap(self, request, uuid=None):
        """GET /api/v1/courses/{uuid}/player-bootstrap/

        The single fetch behind the course player. Returns one of three
        shapes (all HTTP 200), discriminated by ``access.kind``:

        - ``granted`` — full curriculum + progress + sessions + announcements.
        - ``pending_approval`` — slim shell payload (course title/image only).
        - ``redirect_to_detail`` — slug + reason; client navigates to the
          public catalog page where the right CTA already lives.

        See ``learning.view_states.derive_course_access`` for the access
        decision logic and ``learning.bootstrap_serializers`` for the wire
        shapes. This action replaces the legacy 6-fetch player-load
        sequence (course + enrollments + progress + modules + announcements
        + sessions) — none of those endpoints are called by the player
        anymore.
        """
        # Bootstrap serializers are imported only for the schema/codegen
        # path (referenced by `@extend_schema(responses=...)` above).
        # Composition at request time happens via dict-of-already-serialized
        # nested payloads — the outer serializer would otherwise try to
        # re-walk pre-serialized dicts as model instances and fail.
        from learning.serializers import (
            CourseAnnouncementSerializer,
            CourseModuleSerializer,
            CourseSerializer,
            LiveSessionSerializer,
        )
        from learning.view_states import (
            derive_course_access,
            derive_course_enrollment_view_state,
        )

        course = self.get_object()

        # The access decision is decoupled from "is the user enrolled in
        # any state?" — staff get granted access without an enrollment row,
        # and pending/dropped/expired enrollments are handled distinctly.
        enrollment = (
            CourseEnrollment.objects.filter(course=course, user=request.user)
            .order_by('-enrolled_at')
            .first()
        )
        access = derive_course_access(course, user=request.user, enrollment=enrollment)

        if access['kind'] == 'pending_approval':
            return Response({'access': access})

        if access['kind'] == 'redirect_to_detail':
            return Response({'access': access})

        # access.kind == 'granted' — compose the full player payload.
        # For staff_preview the enrollment may be null; handle below.
        granted_enrollment = enrollment if access['audience'] == 'learner' else None

        if granted_enrollment is not None:
            granted_enrollment.update_progress()
            granted_enrollment.refresh_from_db()

        modules_qs = (
            CourseModule.objects.filter(course=course)
            .select_related('module')
            .prefetch_related('module__contents')
            .order_by('order')
        )

        module_progress_payload = []
        for course_module in modules_qs:
            module = course_module.module
            if granted_enrollment is None:
                # Staff preview — synthesise a "fully available, zero
                # progress" snapshot so the client renders the same shell
                # without conditional branches.
                module_progress_payload.append({
                    'module_uuid': str(module.uuid),
                    'is_available': True,
                    'progress_status': 'not_started',
                    'progress_percent': 0,
                    'contents_completed': 0,
                    'contents_total': module.contents.filter(is_required=True).count(),
                    'completed_content_uuids': [],
                })
                continue
            mp, _ = ModuleProgress.objects.get_or_create(
                course_enrollment=granted_enrollment,
                module=module,
                defaults={'contents_total': module.contents.filter(is_required=True).count()},
            )
            completed_uuids = list(
                ContentProgress.objects
                .filter(course_enrollment=granted_enrollment, content__module=module, status='completed')
                .values_list('content__uuid', flat=True)
            )
            module_progress_payload.append({
                'module_uuid': str(module.uuid),
                'is_available': module.is_available_for(
                    request.user, course_enrollment=granted_enrollment,
                ),
                'progress_status': mp.status,
                'progress_percent': int(mp.progress_percent or 0),
                'contents_completed': mp.contents_completed,
                'contents_total': mp.contents_total,
                'completed_content_uuids': [str(u) for u in completed_uuids],
            })

        sessions_payload: list = []
        if course.format in (Course.CourseFormat.LIVE, Course.CourseFormat.HYBRID):
            from learning.models import CourseSession
            sessions_qs = (
                CourseSession.objects.filter(course=course, is_published=True)
                .exclude(status=CourseSession.Status.CANCELLED)
                .order_by('order', 'starts_at')
            )
            sessions_payload = LiveSessionSerializer(
                sessions_qs, many=True, context={'request': request},
            ).data

        announcements_qs = (
            CourseAnnouncement.objects.filter(course=course, is_published=True)
            .order_by('-created_at')
        )

        view_state = (
            derive_course_enrollment_view_state(granted_enrollment)
            if granted_enrollment is not None
            else None
        )

        payload = {
            'access': access,
            'course': CourseSerializer(course, context={'request': request}).data,
            'modules': CourseModuleSerializer(modules_qs, many=True).data,
            'module_progress': module_progress_payload,
            'sessions': sessions_payload,
            'announcements': CourseAnnouncementSerializer(announcements_qs, many=True).data,
            'view_state': view_state,
        }
        return Response(payload)


    @action(detail=True, methods=['get'])
    def attendance_stats(self, request, uuid=None):
        """Aggregate session attendance stats for hybrid courses."""
        from django.db.models import Count, Q

        from .models import CourseEnrollment, CourseSession

        course = self.get_object()

        # Determine if user can view stats (staff only)
        if not (course.can_manage(request.user) or course.can_instruct(request.user)):
             from rest_framework.exceptions import PermissionDenied
             raise PermissionDenied('Permission denied')

        sessions = CourseSession.objects.filter(course=course).annotate(
             attended_count=Count('attendance_records', filter=Q(attendance_records__is_eligible=True))
        ).order_by('starts_at')

        total_enrollments = CourseEnrollment.objects.filter(
             course=course,
             status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED]
        ).count()

        stats = []
        total_attendance_rate = 0

        for session in sessions:
             rate = round((session.attended_count / total_enrollments * 100), 1) if total_enrollments > 0 else 0
             total_attendance_rate += rate

             stats.append({
                  'uuid': session.uuid,
                  'title': session.title,
                  'start_time': session.starts_at,
                  'attended_count': session.attended_count,
                  'enrollment_count': total_enrollments,
                  'attendance_rate': rate
             })

        avg_rate = round(total_attendance_rate / len(sessions), 1) if sessions.exists() else 0

        return Response({
             'average_attendance_rate': avg_rate,
             'total_sessions': sessions.count(),
             'sessions': stats
        })


@roles('organizer', 'instructor', 'admin', route_name='course_staff')
class CourseStaffViewSet(viewsets.ModelViewSet):
    """
    Manage course staff assignments.

    Only admins and course owners can assign/remove staff.
    GET /courses/{course_uuid}/staff/
    POST /courses/{course_uuid}/staff/
    DELETE /courses/{course_uuid}/staff/{uuid}/
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CourseStaffSerializer
    lookup_field = 'uuid'
    http_method_names = ['get', 'post', 'delete']

    def get_queryset(self):
        course_uuid = self.kwargs.get('course_uuid')
        course = get_object_or_404(Course, uuid=course_uuid)
        if not course.can_manage(self.request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to manage course staff.")
        return CourseStaff.objects.filter(course=course).select_related('user')

    def create(self, request, course_uuid=None):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        course = get_object_or_404(Course, uuid=course_uuid)
        if not course.can_manage(request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to manage course staff.")

        serializer = CourseStaffCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = get_object_or_404(User, uuid=serializer.validated_data['user_uuid'])
        role = serializer.validated_data.get('role', 'instructor')

        staff, created = CourseStaff.objects.get_or_create(
            course=course, user=user, defaults={'role': role}
        )
        if not created:
            return Response({'detail': 'User is already assigned to this course.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CourseStaffSerializer(staff).data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        course = instance.course
        if not course.can_manage(self.request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to manage course staff.")
        instance.delete()


@roles('learner', 'organizer', 'instructor', 'admin', route_name='course_enrollments')
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
        from rest_framework.exceptions import PermissionDenied, ValidationError

        course_uuid = self.request.data.get('course_uuid')
        course = get_object_or_404(Course, uuid=course_uuid)

        if not course.is_free:
            raise PermissionDenied("This course requires payment. Please initiate checkout.")

        ok, code, message = course.check_enrollable()
        if not ok:
            raise ValidationError({'error': message, 'code': code})

        serializer.save(user=self.request.user, course=course)

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

    # Orphan checkout action removed — the canonical course-checkout
    # endpoint is ``POST /api/v1/courses/{uuid}/checkout/`` (see
    # ``learning.payment_views.CourseCheckoutView``).


@roles('learner', 'organizer', 'instructor', 'admin', route_name='course_modules')
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

        if not course.can_instruct(self.request.user):
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
        if not course.can_instruct(self.request.user):
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
        if not course_link.course.can_instruct(self.request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this course.")
        module = course_link.module

        serializer = EventModuleCreateSerializer(module, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(CourseModuleSerializer(course_link).data)


@roles('learner', 'organizer', 'instructor', 'admin', route_name='course_module_content')
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

        from rest_framework.exceptions import PermissionDenied

        enrollment = CourseEnrollment.objects.filter(
            user=self.request.user,
            course=course,
            status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
        ).first()
        if enrollment:
            # Enforce module-level gating
            module = get_object_or_404(EventModule, uuid=module_uuid)
            if not module.is_available_for(self.request.user, course_enrollment=enrollment):
                raise PermissionDenied("Complete the previous module first.")
            return base_queryset.filter(
                module__is_published=True,
                is_published=True,
            ).order_by('order')

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
        if not course.can_instruct(self.request.user):
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
        if not course.can_instruct(self.request.user):
            raise PermissionDenied("You do not have access to this course.")
        serializer.save()

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied

        course_uuid = self.kwargs.get('course_uuid')
        course = get_object_or_404(Course, uuid=course_uuid)
        if not course.can_instruct(self.request.user):
            raise PermissionDenied("You do not have access to this course.")
        instance.delete()


@roles('learner', 'organizer', 'instructor', 'admin', route_name='course_assignments')
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


@roles('organizer', 'instructor', 'admin', route_name='course_submissions')
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

        # Check if course should be completed after grading. Even when
        # completion criteria aren't met, refresh progress_percent so the
        # learner's bar reflects the new submission state. update_progress()
        # is a no-op once status=COMPLETED, so this is safe to call.
        if submission.course_enrollment:
            submission.course_enrollment.check_completion()
            submission.course_enrollment.refresh_from_db()
            if submission.course_enrollment.status == CourseEnrollment.Status.ACTIVE:
                submission.course_enrollment.update_progress()

        return Response(AssignmentSubmissionStaffSerializer(submission).data)


@roles('learner', 'organizer', 'instructor', 'admin', route_name='course_announcements')
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


@roles('learner', 'organizer', 'instructor', 'admin', route_name='program_announcements')
class ProgramAnnouncementViewSet(viewsets.ModelViewSet):
    """Announcements for a program. Re-uses the ``CourseAnnouncement`` table
    with the ``program`` FK populated (``course`` is NULL)."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CourseAnnouncementSerializer
    lookup_field = 'uuid'

    def get_program(self):
        program_uuid = self.kwargs.get('program_uuid')
        return get_object_or_404(Program, uuid=program_uuid)

    def _is_program_staff(self, program):
        return program.can_manage(self.request.user)

    def get_queryset(self):
        program = self.get_program()
        queryset = CourseAnnouncement.objects.filter(program=program)

        if self._is_program_staff(program):
            return queryset

        enrolled = ProgramEnrollment.objects.filter(
            user=self.request.user,
            program=program,
            status__in=[ProgramEnrollment.Status.ACTIVE, ProgramEnrollment.Status.COMPLETED],
        ).exists()
        if not enrolled:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this program.")

        return queryset.filter(is_published=True)

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        program = self.get_program()
        if not self._is_program_staff(program):
            raise PermissionDenied("You do not have access to this program.")
        serializer.save(program=program, created_by=self.request.user)

    def perform_update(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        program = self.get_program()
        if not self._is_program_staff(program):
            raise PermissionDenied("You do not have access to this program.")
        serializer.save()

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied

        program = self.get_program()
        if not self._is_program_staff(program):
            raise PermissionDenied("You do not have access to this program.")
        instance.delete()


@roles('organizer', 'instructor', 'admin', route_name='program_discussion')
class ProgramDiscussionView(generics.GenericAPIView):
    """Aggregated discussion view across a program's member courses.

    We intentionally don't fork the Discussion model for programs —
    learners discuss inside individual courses. This endpoint surfaces
    recent threads across every member course so an admin has one place
    to see what's active at the program level.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, program_uuid=None):
        from rest_framework.exceptions import PermissionDenied

        from learning.models import DiscussionThread
        from learning.serializers import DiscussionThreadListSerializer

        program = get_object_or_404(Program, uuid=program_uuid)
        if not program.can_manage(request.user):
            raise PermissionDenied("You do not have access to this program.")

        course_ids = list(
            program.program_courses.values_list('course_id', flat=True)
        )
        threads = (
            DiscussionThread.objects
            .filter(course_id__in=course_ids, deleted_at__isnull=True)
            .select_related('course', 'author')
            .order_by('-last_activity_at')[:50]
        )
        return Response(
            {
                'threads': DiscussionThreadListSerializer(threads, many=True).data,
                'member_course_count': len(course_ids),
            }
        )


@roles('learner', 'organizer', 'instructor', 'admin', route_name='course_sessions')
class CourseSessionViewSet(viewsets.ModelViewSet):
    """
    Live session management for hybrid courses.

    GET /courses/{course_uuid}/sessions/ - List sessions
    POST /courses/{course_uuid}/sessions/ - Create session
    GET /courses/{course_uuid}/sessions/{uuid}/ - Session detail
    PUT/PATCH /courses/{course_uuid}/sessions/{uuid}/ - Update session
    DELETE /courses/{course_uuid}/sessions/{uuid}/ - Delete session
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_course(self):
        course_uuid = self.kwargs.get('course_uuid')
        return get_object_or_404(Course, uuid=course_uuid)

    def _is_course_staff(self, course):
        return course.can_manage(self.request.user) or course.can_instruct(self.request.user)

    def get_queryset(self):
        from .models import CourseSession
        course = self.get_course()
        queryset = CourseSession.objects.filter(course=course)

        # Staff see all, learners see only published
        if self._is_course_staff(course):
            return queryset

        # Enrolled learners can see published sessions
        enrolled = CourseEnrollment.objects.filter(
            user=self.request.user,
            course=course,
            status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
        ).exists()

        if not enrolled:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have access to this course.")

        return queryset.filter(is_published=True)

    def get_serializer_class(self):
        from .serializers import (
            CourseSessionCreateSerializer,
            CourseSessionListSerializer,
            CourseSessionSerializer,
            LiveSessionSerializer,
        )

        if self.action == 'list':
            return CourseSessionListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return CourseSessionCreateSerializer
        if self.action == 'retrieve':
            # Learner-context shape with attendance / recording / join_url
            # already resolved against request.user. Powers the lobby.
            return LiveSessionSerializer
        return CourseSessionSerializer

    @action(detail=True, methods=['post', 'get'], url_path='recording-view')
    def recording_view(self, request, course_uuid=None, uuid=None):
        """Track recording playback. POST upserts the (enrollment, session)
        row; GET returns the caller's current row (or 204 if none yet).

        Body (POST): { watch_seconds: int, last_position_seconds?: int, completed?: bool }

        Watch_seconds is monotone — never decreases. Caller (frontend player)
        is expected to throttle to ~one POST per 15s of playback.

        Per D3 (docs/design/hybrid-course-experience.md): this endpoint NEVER
        flips CourseSessionAttendance.is_eligible — it's tracking only.
        """
        from .models import CourseEnrollment, CourseSessionRecordingView

        session = self.get_object()
        enrollment = CourseEnrollment.objects.filter(
            user=request.user, course=session.course,
        ).first()
        if not enrollment:
            return error_response(
                'You must be enrolled to track recording playback.',
                code='NOT_ENROLLED', status_code=403,
            )

        if request.method == 'GET':
            view = CourseSessionRecordingView.objects.filter(
                course_enrollment=enrollment, session=session,
            ).first()
            if not view:
                return Response(status=204)
            return Response({
                'watch_seconds': view.watch_seconds,
                'last_position_seconds': view.last_position_seconds,
                'completed_at': view.completed_at.isoformat() if view.completed_at else None,
            })

        watch_seconds = int(request.data.get('watch_seconds') or 0)
        last_position = int(request.data.get('last_position_seconds') or 0)
        mark_completed = bool(request.data.get('completed'))

        view, _ = CourseSessionRecordingView.objects.get_or_create(
            course_enrollment=enrollment, session=session,
        )
        # Monotone: never lower stored watch_seconds.
        if watch_seconds > view.watch_seconds:
            view.watch_seconds = watch_seconds
        view.last_position_seconds = last_position
        if mark_completed and not view.completed_at:
            view.completed_at = timezone.now()
        view.save()

        return Response({
            'watch_seconds': view.watch_seconds,
            'last_position_seconds': view.last_position_seconds,
            'completed_at': view.completed_at.isoformat() if view.completed_at else None,
        })

    @action(detail=True, methods=['post'])
    def sync_attendance(self, request, course_uuid=None, uuid=None):
        """Recalculate attendance statistics from webhook data."""
        from .tasks import sync_session_attendance

        session = self.get_object()
        task = sync_session_attendance.delay(session.id)
        # task might be a dict if CLOUD_TASKS_SYNC=True or in emulator mode
        task_id = getattr(task, 'id', None) or (task.get('id') if isinstance(task, dict) else None)
        # fallback to name if it's a CloudTasks response from create_task
        if not task_id and hasattr(task, 'name'):
            task_id = task.name

        return Response({'task_id': task_id, 'status': 'queued'})

    @action(detail=True, methods=['get'])
    def unmatched_participants(self, request, course_uuid=None, uuid=None):
        """Get video participants not matched to enrollment.

        Uses webhook logs data populated via LiveKit webhooks.
        """
        from conferencing.models import VideoRoom, VideoWebhookLog
        from django.contrib.contenttypes.models import ContentType

        from .models import CourseSessionAttendance
        from .serializers import UnmatchedParticipantSerializer

        session = self.get_object()
        course = session.course
        if not self._is_course_staff(course):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to perform this action.")

        # Find the video room for this session
        ct = ContentType.objects.get_for_model(session)
        video_room = VideoRoom.objects.filter(content_type=ct, object_id=session.id).first()
        if not video_room:
            return error_response('Session has no video room linked.', code='NO_VIDEO_ROOM', status_code=400)

        # 1. Get matched participant identities from attendance records
        matched_records = CourseSessionAttendance.objects.filter(session=session)
        matched_identities = set(r.participant_id for r in matched_records if r.participant_id)

        # 2. Get participant join events from webhook logs
        join_logs = VideoWebhookLog.objects.filter(
            room_name=video_room.room_name,
            event_type='participant_joined',
            processing_status='completed',
        ).order_by('-event_timestamp')

        # 3. Extract unmatched participants
        unmatched = []
        seen = set()

        for log in join_logs:
            participant = log.payload.get('participant', {})
            identity = participant.get('identity', '')
            name = participant.get('name', 'Unknown')

            if not identity or identity in matched_identities or identity in seen:
                continue

            seen.add(identity)
            unmatched.append({
                'user_id': identity,
                'user_name': name,
                'user_email': '',
                'join_time': log.event_timestamp.isoformat() if log.event_timestamp else None,
                'leave_time': None,
                'duration_minutes': 0,
            })

        serializer = UnmatchedParticipantSerializer(unmatched, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def match_participant(self, request, course_uuid=None, uuid=None):
        """Manually match a participant to an enrollment."""
        from .models import CourseEnrollment, CourseSessionAttendance
        from .serializers import MatchParticipantSerializer

        session = self.get_object()
        serializer = MatchParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        enrollment_uuid = data['enrollment_uuid']
        enrollment = get_object_or_404(CourseEnrollment, uuid=enrollment_uuid, course=session.course)

        # Create or update attendance record
        record, created = CourseSessionAttendance.objects.update_or_create(
             session=session,
             enrollment=enrollment,
             defaults={
                 'participant_email': data.get('participant_email', ''),
                 'join_time': data.get('join_time'),
                 'leave_time': data.get('leave_time'),
                 'attendance_minutes': data.get('attendance_minutes', 0),
                 'is_manual_override': True,
                 'override_reason': 'Manual reconciliation',
                 'override_by': request.user,
             }
        )
        record.calculate_eligibility()
        record.save(update_fields=['is_eligible', 'updated_at'])
        enrollment.update_progress()

        return Response({'status': 'matched'})

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        course = self.get_course()
        if not self._is_course_staff(course):
            raise PermissionDenied("You do not have permission to add sessions to this course.")
        serializer.save(course=course)

    def perform_update(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        course = self.get_course()
        if not self._is_course_staff(course):
            raise PermissionDenied("You do not have permission to update this session.")
        serializer.save()

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied

        course = self.get_course()
        if not self._is_course_staff(course):
            raise PermissionDenied("You do not have permission to delete this session.")
        instance.delete()

    @action(detail=True, methods=['post'])
    def publish(self, request, course_uuid=None, uuid=None):
        """Publish a session."""
        from rest_framework.exceptions import PermissionDenied

        from .serializers import CourseSessionSerializer

        session = self.get_object()
        course = self.get_course()

        if not self._is_course_staff(course):
            raise PermissionDenied("You do not have permission to publish this session.")

        session.is_published = True
        session.save()
        return Response(CourseSessionSerializer(session).data)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, course_uuid=None, uuid=None):
        """Unpublish a session."""
        from rest_framework.exceptions import PermissionDenied

        from .serializers import CourseSessionSerializer

        session = self.get_object()
        course = self.get_course()

        if not self._is_course_staff(course):
            raise PermissionDenied("You do not have permission to unpublish this session.")

        session.is_published = False
        session.save()
        return Response(CourseSessionSerializer(session).data)

    @action(detail=True, methods=['post'])
    def start(self, request, course_uuid=None, uuid=None):
        """Mark a session as live (kicks off recording if enabled)."""
        from rest_framework.exceptions import PermissionDenied

        from .serializers import CourseSessionSerializer

        session = self.get_object()
        if not self._is_course_staff(self.get_course()):
            raise PermissionDenied("You do not have permission to start this session.")
        try:
            session.start()
        except ValueError as exc:
            return error_response(str(exc), code='INVALID_TRANSITION', status_code=400)
        return Response(CourseSessionSerializer(session).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, course_uuid=None, uuid=None):
        """Mark a session as completed (stops recording if enabled)."""
        from rest_framework.exceptions import PermissionDenied

        from .serializers import CourseSessionSerializer

        session = self.get_object()
        if not self._is_course_staff(self.get_course()):
            raise PermissionDenied("You do not have permission to complete this session.")
        try:
            session.complete()
        except ValueError as exc:
            return error_response(str(exc), code='INVALID_TRANSITION', status_code=400)
        return Response(CourseSessionSerializer(session).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, course_uuid=None, uuid=None):
        """Cancel a session and notify enrolled learners."""
        from rest_framework.exceptions import PermissionDenied

        from .serializers import CourseSessionSerializer

        session = self.get_object()
        if not self._is_course_staff(self.get_course()):
            raise PermissionDenied("You do not have permission to cancel this session.")
        reason = request.data.get('reason', '')
        try:
            session.cancel(reason=reason, user=request.user)
        except ValueError as exc:
            return error_response(str(exc), code='INVALID_TRANSITION', status_code=400)
        from .tasks import notify_course_session_cancelled

        notify_course_session_cancelled.delay(session.id)
        return Response(CourseSessionSerializer(session).data)

    @action(detail=True, methods=['get'], url_path='calendar.ics')
    def calendar(self, request, course_uuid=None, uuid=None):
        """Return an .ics calendar invite for this session."""
        from django.http import HttpResponse

        from .services import build_session_ics

        session = self.get_object()
        ics = build_session_ics(session, user=request.user)
        response = HttpResponse(ics, content_type='text/calendar; charset=utf-8')
        response['Content-Disposition'] = (
            f'attachment; filename="course-session-{session.uuid}.ics"'
        )
        return response

    @action(detail=True, methods=['post'])
    def reschedule(self, request, course_uuid=None, uuid=None):
        """Move a session to a new start time / duration."""
        from rest_framework.exceptions import PermissionDenied

        from .serializers import CourseSessionSerializer

        session = self.get_object()
        if not self._is_course_staff(self.get_course()):
            raise PermissionDenied("You do not have permission to reschedule this session.")
        new_starts_at = request.data.get('starts_at')
        new_duration = request.data.get('duration_minutes')
        if not new_starts_at:
            return error_response('starts_at is required', code='MISSING_FIELD', status_code=400)
        from django.utils.dateparse import parse_datetime

        parsed = parse_datetime(new_starts_at)
        if parsed is None:
            return error_response('starts_at must be a valid datetime', code='INVALID_FORMAT', status_code=400)
        try:
            session.reschedule(new_starts_at=parsed, new_duration_minutes=new_duration)
        except ValueError as exc:
            return error_response(str(exc), code='INVALID_TRANSITION', status_code=400)
        return Response(CourseSessionSerializer(session).data)


# =============================================================================
# Programs
# =============================================================================


@roles('learner', 'organizer', 'instructor', 'admin', route_name='programs')
class ProgramViewSet(viewsets.ModelViewSet):
    """
    Program (course bundle) management.

    Mirrors CourseViewSet's public-vs-owner visibility pattern.
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        queryset = Program.objects.all()
        user = self.request.user

        slug = self.request.query_params.get('slug')
        if slug:
            queryset = queryset.filter(slug=slug)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search)
                | models.Q(short_description__icontains=search)
                | models.Q(description__icontains=search)
            )

        if user.is_authenticated and user.groups.filter(name='admin').exists():
            return queryset.distinct()

        if not user.is_authenticated:
            return queryset.filter(is_public=True, status=Program.Status.PUBLISHED)

        owned = self.request.query_params.get('owned')
        if owned:
            return queryset.filter(created_by=user).distinct()

        # ``enroll_free`` is a learner-facing action on any published public
        # program — not just programs the learner owns. Treat it like retrieve.
        if self.action in ['list', 'retrieve', 'enroll_free']:
            return queryset.filter(
                models.Q(is_public=True, status=Program.Status.PUBLISHED)
                | models.Q(created_by=user)
            ).distinct()

        return queryset.filter(created_by=user)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticatedOrReadOnly()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'list':
            return ProgramListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return ProgramCreateSerializer
        return ProgramSerializer

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        if not self.request.user.has_perm('learning.can_create_course'):
            raise PermissionDenied('You do not have permission to create programs.')
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        if not serializer.instance.can_manage(self.request.user):
            raise PermissionDenied('You do not have permission to update this program.')
        serializer.save()

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied

        if not instance.can_manage(self.request.user):
            raise PermissionDenied('You do not have permission to delete this program.')
        instance.delete()

    @action(detail=True, methods=['post'])
    def publish(self, request, uuid=None):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from rest_framework.exceptions import PermissionDenied

        program = self.get_object()
        if not program.can_manage(request.user):
            raise PermissionDenied('You do not have permission to publish this program.')
        try:
            program.publish()
        except DjangoValidationError as exc:
            return Response(
                exc.message_dict if hasattr(exc, 'message_dict') else {'detail': exc.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(ProgramSerializer(program).data)

    @action(detail=True, methods=['get'], url_path='analytics')
    def analytics(self, request, uuid=None):
        """Per-program analytics: enrollments, completions, revenue.

        Uses the same ``period`` shape as the cohort ``reports`` action but
        scoped to a single program. Revenue is drawn from
        ``CoursePurchase.program`` so it only exists once the program has
        been purchased since the schema landed; legacy Stripe Sessions are
        surfaced via /admin/billing/reconcile if missing.
        """
        from datetime import datetime, timedelta

        from django.db.models import Count, Sum
        from django.db.models.functions import TruncDate
        from django.utils import timezone
        from rest_framework.exceptions import PermissionDenied

        from billing.models import CoursePurchase

        program = self.get_object()
        if not program.can_manage(request.user):
            raise PermissionDenied("You do not have access to this program's analytics.")

        now = timezone.now()
        period = request.query_params.get('period', 'last-30-days')
        if period == 'last-7-days':
            start = now - timedelta(days=7)
        elif period == 'last-90-days':
            start = now - timedelta(days=90)
        elif period == 'this-year':
            start = timezone.make_aware(datetime(now.year, 1, 1))
        else:
            start = now - timedelta(days=30)

        enrollments = ProgramEnrollment.objects.filter(
            program=program, enrolled_at__gte=start, enrolled_at__lte=now,
        )
        total_enrollments = enrollments.count()
        completions = ProgramEnrollment.objects.filter(
            program=program, completed_at__gte=start, completed_at__lte=now,
        ).count()
        completion_rate = round((completions / total_enrollments) * 100, 1) if total_enrollments else None

        trends = [
            {'date': row['day'].isoformat() if row['day'] else None, 'count': row['count']}
            for row in (
                enrollments.annotate(day=TruncDate('enrolled_at'))
                .values('day').annotate(count=Count('id')).order_by('day')
            )
        ]

        status_breakdown = [
            {'label': 'Active', 'count': enrollments.filter(status=ProgramEnrollment.Status.ACTIVE).count()},
            {'label': 'Completed', 'count': enrollments.filter(status=ProgramEnrollment.Status.COMPLETED).count()},
            {'label': 'Dropped', 'count': enrollments.filter(status=ProgramEnrollment.Status.DROPPED).count()},
        ]

        purchases_in_period = CoursePurchase.objects.filter(
            program=program, created_at__gte=start, created_at__lte=now,
        )
        completed = purchases_in_period.filter(status=CoursePurchase.Status.COMPLETED)
        refunded = purchases_in_period.filter(status=CoursePurchase.Status.REFUNDED)
        gross_cents = completed.aggregate(total=Sum('amount_cents'))['total'] or 0
        refund_cents = refunded.aggregate(total=Sum('amount_cents'))['total'] or 0

        recent_transactions = [
            {
                'purchase_uuid': str(p.uuid),
                'user_name': getattr(p.user, 'full_name', None) or getattr(p.user, 'email', ''),
                'amount_cents': p.amount_cents,
                'currency': p.currency,
                'status': p.status,
                'created_at': p.created_at.isoformat() if p.created_at else None,
            }
            for p in purchases_in_period.select_related('user').order_by('-created_at')[:10]
        ]

        return Response(
            {
                'summary': {
                    'total_enrollments': total_enrollments,
                    'completions': completions,
                    'completion_rate': completion_rate,
                    'gross_revenue_cents': gross_cents,
                    'refunds_cents': refund_cents,
                    'net_revenue_cents': gross_cents - refund_cents,
                    'purchase_count': completed.count(),
                    'refund_count': refunded.count(),
                },
                'trends': trends,
                'status_breakdown': status_breakdown,
                'recent_transactions': recent_transactions,
            }
        )

    @action(detail=True, methods=['post'], url_path='sync-stripe')
    def sync_stripe(self, request, uuid=None):
        """Create or refresh the Stripe Product + Price for this program.

        Without this, checkout falls back to inline ``price_data`` every
        time — which works, but the price isn't reusable for promo codes
        or Stripe Dashboard reporting. Writing stripe_product_id /
        stripe_price_id lets Stripe reconcile purchases to a canonical
        product record.
        """
        from rest_framework.exceptions import PermissionDenied

        from billing.client import get_stripe

        program = self.get_object()
        if not program.can_manage(request.user):
            raise PermissionDenied('You do not have permission to sync this program.')

        if program.price_cents <= 0:
            return Response(
                {'error': {'code': 'NOT_PAID', 'message': 'Free programs do not need a Stripe product.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stripe = get_stripe()
        try:
            if not program.stripe_product_id:
                product = stripe.Product.create(
                    name=program.title,
                    description=(program.short_description or program.title)[:500],
                    metadata={'program_uuid': str(program.uuid)},
                    idempotency_key=f'program_product:{program.uuid}:v1',
                )
                program.stripe_product_id = product.id

            # Always create a new Price row if the price or currency shifts
            # (Stripe Prices are immutable — new values require a new Price).
            price = stripe.Price.create(
                currency=(program.currency or 'USD').lower(),
                unit_amount=program.price_cents,
                product=program.stripe_product_id,
                metadata={'program_uuid': str(program.uuid)},
            )
            program.stripe_price_id = price.id
            program.save(update_fields=['stripe_product_id', 'stripe_price_id', 'updated_at'])
        except Exception as exc:
            return Response(
                {'error': {'code': 'STRIPE_ERROR', 'message': str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(ProgramSerializer(program).data)

    @action(detail=True, methods=['post'])
    def archive(self, request, uuid=None):
        """Archive a program: hidden from discovery, blocks new enrollments.

        Existing ProgramEnrollments keep access. Admin can un-archive by
        calling ``publish`` again, which validates + flips the status back
        to PUBLISHED.
        """
        from rest_framework.exceptions import PermissionDenied

        program = self.get_object()
        if not program.can_manage(request.user):
            raise PermissionDenied('You do not have permission to archive this program.')
        program.archive()
        return Response(ProgramSerializer(program).data)

    @action(detail=True, methods=['post'], url_path='enroll')
    def enroll_free(self, request, uuid=None):
        """One-click enrollment for price-zero programs.

        Paid programs must go through Stripe Checkout. This is the single
        direct path for free bundles — creates the ProgramEnrollment,
        activates it (seeding member-course enrollments with provenance),
        and writes an audit entry.
        """
        program = self.get_object()
        if program.price_cents > 0:
            return Response(
                {'error': {'code': 'NOT_FREE', 'message': 'Paid programs require checkout.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if program.status != Program.Status.PUBLISHED:
            return Response(
                {'error': {'code': 'NOT_PUBLISHED', 'message': 'Program is not open for enrollment.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enrollment, created = ProgramEnrollment.objects.get_or_create(
            user=request.user, program=program
        )
        enrollment.activate()
        program.update_counts()

        if created:
            try:
                from accounts.audit import log_audit_event

                log_audit_event(
                    actor=request.user,
                    action='program_enrollment.created',
                    object_type='ProgramEnrollment',
                    object_uuid=str(enrollment.uuid),
                    metadata={'program_uuid': str(program.uuid), 'price_cents': 0},
                    request=request,
                )
            except Exception:
                logger.warning('audit log failed for free program enroll %s', enrollment.uuid, exc_info=True)

        return Response(ProgramEnrollmentSerializer(enrollment).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='enrollments')
    def enrollments(self, request, uuid=None):
        """Staff roster: every learner enrolled in this program with payment status."""
        from rest_framework.exceptions import PermissionDenied

        program = self.get_object()
        if not program.can_manage(request.user):
            raise PermissionDenied("You do not have access to this program's enrollments.")

        qs = (
            ProgramEnrollment.objects
            .filter(program=program)
            .select_related('user')
            .order_by('-enrolled_at')
        )
        return Response(ProgramEnrollmentRosterSerializer(qs, many=True).data)

    # Refund moved to the unified billing endpoint:
    # ``POST /api/v1/billing/purchases/{purchase_uuid}/refund/``.
    # See ``billing.views.RefundPurchaseView`` for cascade behaviour.

    @action(detail=False, methods=['get'])
    def reports(self, request):
        """Summary, trends, and recent activity for the requester's programs."""
        from datetime import datetime, timedelta

        from django.db.models import Count
        from django.db.models.functions import TruncDate
        from django.utils import timezone
        from rest_framework.exceptions import PermissionDenied

        user = request.user
        if not user.groups.filter(name__in=['instructor', 'admin']).exists():
            raise PermissionDenied('Program reports are limited to instructors and admins.')

        if user.groups.filter(name='admin').exists():
            programs = Program.objects.all()
        else:
            programs = Program.objects.filter(created_by=user).distinct()

        now = timezone.now()
        period = request.query_params.get('period', 'last-30-days')
        if period == 'last-7-days':
            start = now - timedelta(days=7)
        elif period == 'last-90-days':
            start = now - timedelta(days=90)
        elif period == 'this-year':
            start = timezone.make_aware(datetime(now.year, 1, 1))
        else:
            start = now - timedelta(days=30)

        enrollments = ProgramEnrollment.objects.filter(
            program__in=programs,
            enrolled_at__gte=start,
            enrolled_at__lte=now,
        )

        total_enrollments = enrollments.count()
        completions_in_period = ProgramEnrollment.objects.filter(
            program__in=programs,
            completed_at__gte=start,
            completed_at__lte=now,
        ).count()

        completion_rate = None
        if total_enrollments:
            completion_rate = round((completions_in_period / total_enrollments) * 100, 1)

        trends = []
        for row in (
            enrollments.annotate(day=TruncDate('enrolled_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        ):
            trends.append(
                {
                    'date': row['day'].isoformat() if row['day'] else None,
                    'count': row['count'],
                }
            )

        status_breakdown = [
            {'label': 'Active', 'count': enrollments.filter(status=ProgramEnrollment.Status.ACTIVE).count()},
            {'label': 'Completed', 'count': enrollments.filter(status=ProgramEnrollment.Status.COMPLETED).count()},
            {'label': 'Dropped', 'count': enrollments.filter(status=ProgramEnrollment.Status.DROPPED).count()},
        ]

        recent_enrollments = [
            {
                'enrollment_uuid': str(e.uuid),
                'program_title': e.program.title if e.program else '',
                'user_name': getattr(e.user, 'full_name', None) or getattr(e.user, 'email', ''),
                'status': e.status,
                'enrolled_at': e.enrolled_at.isoformat(),
            }
            for e in enrollments.select_related('program', 'user').order_by('-enrolled_at')[:5]
        ]

        top_programs = [
            {
                'uuid': str(p.uuid),
                'title': p.title,
                'enrollments': p.period_enrollments,
            }
            for p in programs.annotate(
                period_enrollments=Count(
                    'enrollments',
                    filter=models.Q(
                        enrollments__enrolled_at__gte=start,
                        enrollments__enrolled_at__lte=now,
                    ),
                )
            ).order_by('-period_enrollments')[:5]
            if p.period_enrollments
        ]

        return Response(
            {
                'summary': {
                    'total_enrollments': total_enrollments,
                    'completions': completions_in_period,
                    'completion_rate': completion_rate,
                    'programs_published': programs.filter(status=Program.Status.PUBLISHED).count(),
                },
                'trends': trends,
                'status_breakdown': status_breakdown,
                'recent_enrollments': recent_enrollments,
                'top_programs': top_programs,
            }
        )


@roles('learner', 'organizer', 'instructor', 'admin', route_name='program_courses')
class ProgramCourseViewSet(viewsets.ModelViewSet):
    """
    Manage the courses in a program (add, remove, reorder).

    GET /programs/{program_uuid}/courses/
    POST /programs/{program_uuid}/courses/   body: {course_uuid, order, is_required}
    PATCH /programs/{program_uuid}/courses/{uuid}/  body: {order, is_required}
    DELETE /programs/{program_uuid}/courses/{uuid}/
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProgramCourseEntrySerializer
    lookup_field = 'uuid'

    def _get_program(self):
        return get_object_or_404(Program, uuid=self.kwargs['program_uuid'])

    def get_queryset(self):
        return ProgramCourse.objects.filter(
            program__uuid=self.kwargs['program_uuid']
        ).select_related('course')

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        program = self._get_program()
        if not program.can_manage(self.request.user):
            raise PermissionDenied('You do not have permission to modify this program.')
        serializer.save(program=program)
        program.update_counts()

    def perform_update(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        program = self._get_program()
        if not program.can_manage(self.request.user):
            raise PermissionDenied('You do not have permission to modify this program.')
        serializer.save()

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied

        program = self._get_program()
        if not program.can_manage(self.request.user):
            raise PermissionDenied('You do not have permission to modify this program.')
        instance.delete()
        program.update_counts()


@roles('learner', 'organizer', 'instructor', 'admin', route_name='program_enrollments')
class ProgramEnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    """A learner's own program enrollments."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProgramEnrollmentSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        return ProgramEnrollment.objects.filter(user=self.request.user).select_related('program')


# =============================================================================
# Discussion Board
# =============================================================================


def _course_is_staff(course, user):
    if not user or not user.is_authenticated:
        return False
    return course.can_manage(user) or course.can_instruct(user)


def _course_is_enrollee(course, user):
    if not user or not user.is_authenticated:
        return False
    return CourseEnrollment.objects.filter(
        user=user,
        course=course,
        status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
    ).exists()


def _require_course_access(course, user):
    from rest_framework.exceptions import PermissionDenied

    if _course_is_staff(course, user) or _course_is_enrollee(course, user):
        return
    raise PermissionDenied('You do not have access to this course.')


def _require_course_staff(course, user):
    from rest_framework.exceptions import PermissionDenied

    if not _course_is_staff(course, user):
        raise PermissionDenied('Staff access required.')


def _apply_mentions(post, cleaned_html):
    """Parse mention UUIDs from sanitized HTML, resolve to allowed users, set M2M."""
    from accounts.models import User as UserModel
    from .sanitize import extract_mentions

    uuids = extract_mentions(cleaned_html)
    if not uuids:
        post.mentions.clear()
        return []
    course = post.thread.course if isinstance(post, DiscussionReply) else post.course
    allowed_ids = set(
        UserModel.objects.filter(uuid__in=uuids)
        .values_list('uuid', flat=True)
    )
    # Restrict mentions to users that are enrolled or staff on the course.
    enrolled_uuids = set(
        CourseEnrollment.objects.filter(
            course=course,
            user__uuid__in=allowed_ids,
            status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
        ).values_list('user__uuid', flat=True)
    )
    staff_uuids = set(
        CourseStaff.objects.filter(course=course, user__uuid__in=allowed_ids)
        .values_list('user__uuid', flat=True)
    )
    valid = enrolled_uuids | staff_uuids
    users = list(UserModel.objects.filter(uuid__in=valid))
    post.mentions.set(users)
    return users


@roles('learner', 'organizer', 'instructor', 'admin', route_name='course_discussions')
class DiscussionThreadViewSet(viewsets.ModelViewSet):
    """Threads on a course discussion board."""

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_course(self):
        return get_object_or_404(Course, uuid=self.kwargs.get('course_uuid'))

    def get_queryset(self):
        course = self.get_course()
        _require_course_access(course, self.request.user)
        manager = DiscussionThread.all_objects if _course_is_staff(course, self.request.user) else DiscussionThread.objects
        qs = manager.filter(course=course).select_related('author').prefetch_related('mentions')
        if not _course_is_staff(course, self.request.user):
            qs = qs.filter(is_hidden=False)
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return DiscussionThreadCreateSerializer
        if self.action in ('update', 'partial_update'):
            return DiscussionThreadUpdateSerializer
        if self.action == 'retrieve':
            return DiscussionThreadDetailSerializer
        return DiscussionThreadListSerializer

    def perform_create(self, serializer):
        course = self.get_course()
        _require_course_access(course, self.request.user)
        thread = serializer.save(course=course, author=self.request.user)
        mentioned = _apply_mentions(thread, thread.body_html)
        from .discussions_service import notify_mentions

        notify_mentions(thread, mentioned)

    def perform_update(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        thread = self.get_object()
        course = self.get_course()
        is_author = thread.author_id == self.request.user.id
        is_staff = _course_is_staff(course, self.request.user)
        if not (is_author or is_staff):
            raise PermissionDenied('Only the author or staff can edit this thread.')
        if thread.is_locked and not is_staff:
            raise PermissionDenied('Thread is locked.')
        thread = serializer.save()
        _apply_mentions(thread, thread.body_html)

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied

        course = self.get_course()
        is_author = instance.author_id == self.request.user.id
        is_staff = _course_is_staff(course, self.request.user)
        if not (is_author or is_staff):
            raise PermissionDenied('Only the author or staff can delete this thread.')
        instance.soft_delete()

    def _set_flag(self, field: str, value: bool):
        thread = self.get_object()
        _require_course_staff(self.get_course(), self.request.user)
        setattr(thread, field, value)
        thread.save(update_fields=[field, 'updated_at'])
        return Response(DiscussionThreadDetailSerializer(thread, context={'request': self.request}).data)

    @action(detail=True, methods=['post'])
    def pin(self, request, *args, **kwargs):
        return self._set_flag('is_pinned', True)

    @action(detail=True, methods=['post'])
    def unpin(self, request, *args, **kwargs):
        return self._set_flag('is_pinned', False)

    @action(detail=True, methods=['post'])
    def lock(self, request, *args, **kwargs):
        return self._set_flag('is_locked', True)

    @action(detail=True, methods=['post'])
    def unlock(self, request, *args, **kwargs):
        return self._set_flag('is_locked', False)

    @action(detail=True, methods=['post'])
    def hide(self, request, *args, **kwargs):
        return self._set_flag('is_hidden', True)

    @action(detail=True, methods=['post'])
    def unhide(self, request, *args, **kwargs):
        return self._set_flag('is_hidden', False)

    @action(detail=True, methods=['post'])
    def flag(self, request, *args, **kwargs):
        thread = self.get_object()
        _require_course_access(self.get_course(), self.request.user)
        serializer = DiscussionFlagCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        flag = serializer.save(thread=thread, reporter=self.request.user)
        return Response(DiscussionFlagSerializer(flag).data, status=status.HTTP_201_CREATED)


@roles('learner', 'organizer', 'instructor', 'admin', route_name='course_discussions')
class DiscussionReplyViewSet(viewsets.ModelViewSet):
    """Replies under a discussion thread."""

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'
    http_method_names = ['get', 'post', 'delete']

    def get_course(self):
        return get_object_or_404(Course, uuid=self.kwargs.get('course_uuid'))

    def get_thread(self):
        return get_object_or_404(
            DiscussionThread.all_objects,
            uuid=self.kwargs.get('thread_uuid'),
            course__uuid=self.kwargs.get('course_uuid'),
        )

    def get_queryset(self):
        course = self.get_course()
        _require_course_access(course, self.request.user)
        thread = self.get_thread()
        manager = DiscussionReply.all_objects if _course_is_staff(course, self.request.user) else DiscussionReply.objects
        qs = manager.filter(thread=thread).select_related('author').prefetch_related('mentions')
        if not _course_is_staff(course, self.request.user):
            qs = qs.filter(is_hidden=False)
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return DiscussionReplyCreateSerializer
        return DiscussionReplySerializer

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied

        course = self.get_course()
        _require_course_access(course, self.request.user)
        thread = self.get_thread()
        is_staff = _course_is_staff(course, self.request.user)
        if thread.is_locked and not is_staff:
            raise PermissionDenied('Thread is locked.')
        reply = serializer.save(thread=thread, author=self.request.user)
        mentioned = _apply_mentions(reply, reply.body_html)
        DiscussionThread.objects.filter(pk=thread.pk).update(
            reply_count=models.F('reply_count') + 1,
            last_activity_at=timezone.now(),
        )
        from .discussions_service import notify_new_reply, notify_mentions

        notify_new_reply(reply)
        notify_mentions(reply, mentioned)

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied

        course = self.get_course()
        is_author = instance.author_id == self.request.user.id
        is_staff = _course_is_staff(course, self.request.user)
        if not (is_author or is_staff):
            raise PermissionDenied('Only the author or staff can delete this reply.')
        instance.soft_delete()

    def _set_flag(self, field: str, value: bool):
        reply = self.get_object()
        _require_course_staff(self.get_course(), self.request.user)
        setattr(reply, field, value)
        reply.save(update_fields=[field, 'updated_at'])
        return Response(DiscussionReplySerializer(reply, context={'request': self.request}).data)

    @action(detail=True, methods=['post'])
    def hide(self, request, *args, **kwargs):
        return self._set_flag('is_hidden', True)

    @action(detail=True, methods=['post'])
    def unhide(self, request, *args, **kwargs):
        return self._set_flag('is_hidden', False)

    @action(detail=True, methods=['post'])
    def flag(self, request, *args, **kwargs):
        reply = self.get_object()
        _require_course_access(self.get_course(), self.request.user)
        serializer = DiscussionFlagCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        flag = serializer.save(reply=reply, reporter=self.request.user)
        return Response(DiscussionFlagSerializer(flag).data, status=status.HTTP_201_CREATED)


@roles('organizer', 'instructor', 'admin', route_name='course_discussion_flags')
class DiscussionFlagViewSet(viewsets.GenericViewSet):
    """Staff-only flag queue + resolve actions."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DiscussionFlagSerializer
    lookup_field = 'uuid'

    def get_course(self):
        return get_object_or_404(Course, uuid=self.kwargs.get('course_uuid'))

    def get_queryset(self):
        course = self.get_course()
        _require_course_staff(course, self.request.user)
        return DiscussionFlag.objects.filter(
            models.Q(thread__course=course) | models.Q(reply__thread__course=course)
        ).select_related('reporter', 'thread', 'reply', 'reply__thread').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        status_filter = request.query_params.get('status', DiscussionFlag.Status.OPEN)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(DiscussionFlagSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, *args, **kwargs):
        from django.utils import timezone as _tz
        from rest_framework.exceptions import ValidationError

        course = self.get_course()
        _require_course_staff(course, self.request.user)
        flag = get_object_or_404(self.get_queryset(), uuid=kwargs.get('uuid'))
        action_kind = request.data.get('action')
        if action_kind not in ('keep', 'hide'):
            raise ValidationError({'action': 'Must be "keep" or "hide".'})
        if action_kind == 'hide':
            target = flag.thread if flag.thread_id else flag.reply
            target.is_hidden = True
            target.save(update_fields=['is_hidden', 'updated_at'])
            flag.status = DiscussionFlag.Status.RESOLVED_HIDDEN
        else:
            flag.status = DiscussionFlag.Status.RESOLVED_KEPT
        flag.resolved_by = request.user
        flag.resolved_at = _tz.now()
        flag.save(update_fields=['status', 'resolved_by', 'resolved_at', 'updated_at'])
        from .discussions_service import notify_flag_resolved

        notify_flag_resolved(flag)
        return Response(DiscussionFlagSerializer(flag).data)


@roles('learner', 'organizer', 'instructor', 'admin', route_name='course_member_search')
class CourseMemberSearchView(views.APIView):
    """Search enrolled members + staff for @mention autocomplete."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_uuid):
        course = get_object_or_404(Course, uuid=course_uuid)
        _require_course_access(course, request.user)
        q = (request.query_params.get('q') or '').strip()
        from accounts.models import User as UserModel

        enrolled = UserModel.objects.filter(
            course_enrollments__course=course,
            course_enrollments__status__in=[
                CourseEnrollment.Status.ACTIVE,
                CourseEnrollment.Status.COMPLETED,
            ],
        )
        staff = UserModel.objects.filter(course_staff_assignments__course=course)
        qs = (enrolled | staff).distinct()
        if q:
            qs = qs.filter(
                models.Q(full_name__icontains=q) | models.Q(email__icontains=q)
            )
        qs = qs[:10]
        staff_ids = set(CourseStaff.objects.filter(course=course).values_list('user_id', flat=True))
        data = []
        for u in qs:
            data.append({
                'uuid': u.uuid,
                'full_name': u.full_name,
                'email': u.email,
                'role': 'staff' if u.id in staff_ids else 'learner',
            })
        return Response(CourseMemberMiniSerializer(data, many=True).data)
