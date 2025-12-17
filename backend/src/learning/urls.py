"""
URL routes for learning API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers

from .views import (
    EventModuleViewSet,
    ModuleContentViewSet,
    AssignmentViewSet,
    AttendeeSubmissionViewSet,
    OrganizerSubmissionsViewSet,
    MyLearningViewSet,
    ContentProgressView,
)

# Main router
router = DefaultRouter()
router.register(r'submissions', AttendeeSubmissionViewSet, basename='my-submission')
router.register(r'organizer/submissions', OrganizerSubmissionsViewSet, basename='organizer-submission')
router.register(r'learning', MyLearningViewSet, basename='my-learning')

urlpatterns = [
    # Learning routes
    path('', include(router.urls)),
    
    # Progress update
    path(
        'learning/progress/content/<uuid:content_uuid>/',
        ContentProgressView.as_view(),
        name='content-progress'
    ),
]

# Event-nested module routes (to be included in events/urls.py)
# /events/{event_uuid}/modules/
# /events/{event_uuid}/modules/{module_uuid}/contents/
# /events/{event_uuid}/modules/{module_uuid}/assignments/

event_module_patterns = [
    path(
        'events/<uuid:event_uuid>/modules/',
        EventModuleViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }),
        name='event-module-list'
    ),
    path(
        'events/<uuid:event_uuid>/modules/<uuid:uuid>/',
        EventModuleViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='event-module-detail'
    ),
    path(
        'events/<uuid:event_uuid>/modules/<uuid:uuid>/publish/',
        EventModuleViewSet.as_view({'post': 'publish'}),
        name='event-module-publish'
    ),
    path(
        'events/<uuid:event_uuid>/modules/<uuid:uuid>/unpublish/',
        EventModuleViewSet.as_view({'post': 'unpublish'}),
        name='event-module-unpublish'
    ),
    path(
        'events/<uuid:event_uuid>/modules/<uuid:module_uuid>/contents/',
        ModuleContentViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }),
        name='module-content-list'
    ),
    path(
        'events/<uuid:event_uuid>/modules/<uuid:module_uuid>/contents/<uuid:uuid>/',
        ModuleContentViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='module-content-detail'
    ),
    path(
        'events/<uuid:event_uuid>/modules/<uuid:module_uuid>/assignments/',
        AssignmentViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }),
        name='module-assignment-list'
    ),
    path(
        'events/<uuid:event_uuid>/modules/<uuid:module_uuid>/assignments/<uuid:uuid>/',
        AssignmentViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy'
        }),
        name='module-assignment-detail'
    ),
]

# Add event-nested patterns
urlpatterns += event_module_patterns
