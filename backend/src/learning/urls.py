"""
URL routes for learning API.
"""
app_name = 'learning'
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .payment_views import CourseCheckoutView
from .views import (
    AssignmentViewSet,
    AttendeeSubmissionViewSet,
    ContentProgressView,
    CourseAnnouncementViewSet,
    CourseAssignmentViewSet,
    CourseEnrollmentViewSet,
    CourseModuleContentViewSet,
    CourseModuleViewSet,
    CourseSubmissionsViewSet,
    CourseViewSet,
    EventModuleViewSet,
    ModuleContentViewSet,
    MyLearningViewSet,
    OrganizerSubmissionsViewSet,
)

# Main router
router = DefaultRouter()
router.register(r'submissions', AttendeeSubmissionViewSet, basename='my-submission')
router.register(r'organizer/submissions', OrganizerSubmissionsViewSet, basename='organizer-submission')
router.register(r'learning', MyLearningViewSet, basename='my-learning')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'enrollments', CourseEnrollmentViewSet, basename='course-enrollment')

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
    # Progress update
    path('learning/progress/content/<uuid:content_uuid>/', ContentProgressView.as_view(), name='content-progress'),
    # Payments
    path('courses/<uuid:uuid>/checkout/', CourseCheckoutView.as_view(), name='course-checkout'),
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
