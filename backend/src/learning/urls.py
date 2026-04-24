"""
URL routes for learning API.
"""
app_name = 'learning'
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .payment_views import CourseCheckoutView, ProgramCheckoutView
from .views import (
    AssignmentViewSet,
    AttendeeSubmissionViewSet,
    ContentProgressView,
    CourseAnnouncementViewSet,
    ProgramAnnouncementViewSet,
    ProgramDiscussionView,
    CourseAssignmentViewSet,
    CourseEnrollmentViewSet,
    CourseMemberSearchView,
    CourseModuleContentViewSet,
    CourseModuleViewSet,
    CourseSessionViewSet,
    CourseStaffViewSet,
    CourseSubmissionsViewSet,
    CourseViewSet,
    DiscussionFlagViewSet,
    DiscussionReplyViewSet,
    DiscussionThreadViewSet,
    EventModuleViewSet,
    ModuleContentViewSet,
    MyLearningViewSet,
    OrganizerSubmissionsViewSet,
    ProgramCourseViewSet,
    ProgramEnrollmentViewSet,
    ProgramViewSet,
)

# Main router
router = DefaultRouter()
router.register(r'submissions', AttendeeSubmissionViewSet, basename='my-submission')
router.register(r'organizer/submissions', OrganizerSubmissionsViewSet, basename='organizer-submission')
router.register(r'learning', MyLearningViewSet, basename='my-learning')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'enrollments', CourseEnrollmentViewSet, basename='course-enrollment')
router.register(r'programs', ProgramViewSet, basename='program')
router.register(r'program-enrollments', ProgramEnrollmentViewSet, basename='program-enrollment')

urlpatterns = [
    # Learning routes
    path('', include(router.urls)),
    # Course Modules (Custom implementation since it's a wrapper)
    path(
        'courses/<uuid:course_uuid>/modules/',
        CourseModuleViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='course-module-list',
    ),
    path(
        'courses/<uuid:course_uuid>/modules/<uuid:uuid>/',
        CourseModuleViewSet.as_view({'get': 'retrieve', 'delete': 'destroy', 'patch': 'update_content'}),
        name='course-module-detail',
    ),
    # Reuse valid content routes but mapped under course structure for consistency?
    # Actually, we can reuse the ViewSets if they are generic enough.
    # ModuleContentViewSet expects 'module_uuid'.
    path(
        'courses/<uuid:course_uuid>/modules/<uuid:module_uuid>/contents/',
        CourseModuleContentViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='course-module-content-list',
    ),
    path(
        'courses/<uuid:course_uuid>/modules/<uuid:module_uuid>/contents/<uuid:uuid>/',
        CourseModuleContentViewSet.as_view(
            {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}
        ),
        name='course-module-content-detail',
    ),
    path(
        'courses/<uuid:course_uuid>/modules/<uuid:module_uuid>/assignments/',
        CourseAssignmentViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='course-module-assignment-list',
    ),
    path(
        'courses/<uuid:course_uuid>/modules/<uuid:module_uuid>/assignments/<uuid:uuid>/',
        CourseAssignmentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='course-module-assignment-detail',
    ),
    path(
        'courses/<uuid:course_uuid>/submissions/',
        CourseSubmissionsViewSet.as_view({'get': 'list'}),
        name='course-submission-list',
    ),
    path(
        'courses/<uuid:course_uuid>/submissions/<uuid:uuid>/',
        CourseSubmissionsViewSet.as_view({'get': 'retrieve'}),
        name='course-submission-detail',
    ),
    path(
        'courses/<uuid:course_uuid>/submissions/<uuid:uuid>/grade/',
        CourseSubmissionsViewSet.as_view({'post': 'grade'}),
        name='course-submission-grade',
    ),
    path(
        'courses/<uuid:course_uuid>/announcements/',
        CourseAnnouncementViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='course-announcement-list',
    ),
    path(
        'courses/<uuid:course_uuid>/announcements/<uuid:uuid>/',
        CourseAnnouncementViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='course-announcement-detail',
    ),
    # Program announcements — share the CourseAnnouncement table via the program FK.
    path(
        'programs/<uuid:program_uuid>/announcements/',
        ProgramAnnouncementViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='program-announcement-list',
    ),
    path(
        'programs/<uuid:program_uuid>/announcements/<uuid:uuid>/',
        ProgramAnnouncementViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='program-announcement-detail',
    ),
    # Aggregated discussion view across a program's member courses.
    path(
        'programs/<uuid:program_uuid>/discussion/',
        ProgramDiscussionView.as_view(),
        name='program-discussion',
    ),
    # Course Staff
    path(
        'courses/<uuid:course_uuid>/staff/',
        CourseStaffViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='course-staff-list',
    ),
    path(
        'courses/<uuid:course_uuid>/staff/<uuid:uuid>/',
        CourseStaffViewSet.as_view({'delete': 'destroy'}),
        name='course-staff-detail',
    ),
    # Course Sessions (for hybrid courses)
    path(
        'courses/<uuid:course_uuid>/sessions/',
        CourseSessionViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='course-session-list',
    ),
    path(
        'courses/<uuid:course_uuid>/sessions/<uuid:uuid>/',
        CourseSessionViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='course-session-detail',
    ),
    path(
        'courses/<uuid:course_uuid>/sessions/<uuid:uuid>/publish/',
        CourseSessionViewSet.as_view({'post': 'publish'}),
        name='course-session-publish',
    ),
    path(
        'courses/<uuid:course_uuid>/sessions/<uuid:uuid>/unpublish/',
        CourseSessionViewSet.as_view({'post': 'unpublish'}),
        name='course-session-unpublish',
    ),
    path(
        'courses/<uuid:course_uuid>/sessions/<uuid:uuid>/sync_attendance/',
        CourseSessionViewSet.as_view({'post': 'sync_attendance'}),
        name='course-session-sync-attendance',
    ),
    path(
        'courses/<uuid:course_uuid>/sessions/<uuid:uuid>/unmatched_participants/',
        CourseSessionViewSet.as_view({'get': 'unmatched_participants'}),
        name='course-session-unmatched-participants',
    ),
    path(
        'courses/<uuid:course_uuid>/sessions/<uuid:uuid>/match_participant/',
        CourseSessionViewSet.as_view({'post': 'match_participant'}),
        name='course-session-match-participant',
    ),
    # Discussions
    path(
        'courses/<uuid:course_uuid>/discussions/',
        DiscussionThreadViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='course-discussion-list',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/flags/',
        DiscussionFlagViewSet.as_view({'get': 'list'}),
        name='course-discussion-flag-list',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/flags/<uuid:uuid>/resolve/',
        DiscussionFlagViewSet.as_view({'post': 'resolve'}),
        name='course-discussion-flag-resolve',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/<uuid:uuid>/',
        DiscussionThreadViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='course-discussion-detail',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/<uuid:uuid>/pin/',
        DiscussionThreadViewSet.as_view({'post': 'pin'}),
        name='course-discussion-pin',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/<uuid:uuid>/unpin/',
        DiscussionThreadViewSet.as_view({'post': 'unpin'}),
        name='course-discussion-unpin',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/<uuid:uuid>/lock/',
        DiscussionThreadViewSet.as_view({'post': 'lock'}),
        name='course-discussion-lock',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/<uuid:uuid>/unlock/',
        DiscussionThreadViewSet.as_view({'post': 'unlock'}),
        name='course-discussion-unlock',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/<uuid:uuid>/hide/',
        DiscussionThreadViewSet.as_view({'post': 'hide'}),
        name='course-discussion-hide',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/<uuid:uuid>/unhide/',
        DiscussionThreadViewSet.as_view({'post': 'unhide'}),
        name='course-discussion-unhide',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/<uuid:uuid>/flag/',
        DiscussionThreadViewSet.as_view({'post': 'flag'}),
        name='course-discussion-flag',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/<uuid:thread_uuid>/replies/',
        DiscussionReplyViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='course-discussion-reply-list',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/<uuid:thread_uuid>/replies/<uuid:uuid>/',
        DiscussionReplyViewSet.as_view({'delete': 'destroy'}),
        name='course-discussion-reply-detail',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/<uuid:thread_uuid>/replies/<uuid:uuid>/hide/',
        DiscussionReplyViewSet.as_view({'post': 'hide'}),
        name='course-discussion-reply-hide',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/<uuid:thread_uuid>/replies/<uuid:uuid>/unhide/',
        DiscussionReplyViewSet.as_view({'post': 'unhide'}),
        name='course-discussion-reply-unhide',
    ),
    path(
        'courses/<uuid:course_uuid>/discussions/<uuid:thread_uuid>/replies/<uuid:uuid>/flag/',
        DiscussionReplyViewSet.as_view({'post': 'flag'}),
        name='course-discussion-reply-flag',
    ),
    path(
        'courses/<uuid:course_uuid>/members/search/',
        CourseMemberSearchView.as_view(),
        name='course-member-search',
    ),
    # Progress update
    path('learning/progress/content/<uuid:content_uuid>/', ContentProgressView.as_view(), name='content-progress'),
    # Payments
    path('courses/<uuid:uuid>/checkout/', CourseCheckoutView.as_view(), name='course-checkout'),
    # Programs — member-course management (nested)
    path(
        'programs/<uuid:program_uuid>/courses/',
        ProgramCourseViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='program-course-list',
    ),
    path(
        'programs/<uuid:program_uuid>/courses/<uuid:uuid>/',
        ProgramCourseViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy'}),
        name='program-course-detail',
    ),
    path('programs/<uuid:uuid>/checkout/', ProgramCheckoutView.as_view(), name='program-checkout'),
]


# Event-nested module routes (to be included in events/urls.py)
# /events/{event_uuid}/modules/
# /events/{event_uuid}/modules/{module_uuid}/contents/
# /events/{event_uuid}/modules/{module_uuid}/assignments/

event_module_patterns = [
    path(
        'events/<uuid:event_uuid>/modules/',
        EventModuleViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='event-module-list',
    ),
    path(
        'events/<uuid:event_uuid>/modules/<uuid:uuid>/',
        EventModuleViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='event-module-detail',
    ),
    path(
        'events/<uuid:event_uuid>/modules/<uuid:uuid>/publish/',
        EventModuleViewSet.as_view({'post': 'publish'}),
        name='event-module-publish',
    ),
    path(
        'events/<uuid:event_uuid>/modules/<uuid:uuid>/unpublish/',
        EventModuleViewSet.as_view({'post': 'unpublish'}),
        name='event-module-unpublish',
    ),
    path(
        'events/<uuid:event_uuid>/modules/<uuid:module_uuid>/contents/',
        ModuleContentViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='module-content-list',
    ),
    path(
        'events/<uuid:event_uuid>/modules/<uuid:module_uuid>/contents/<uuid:uuid>/',
        ModuleContentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='module-content-detail',
    ),
    path(
        'events/<uuid:event_uuid>/modules/<uuid:module_uuid>/assignments/',
        AssignmentViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='module-assignment-list',
    ),
    path(
        'events/<uuid:event_uuid>/modules/<uuid:module_uuid>/assignments/<uuid:uuid>/',
        AssignmentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}),
        name='module-assignment-detail',
    ),
]

# Add event-nested patterns
urlpatterns += event_module_patterns
