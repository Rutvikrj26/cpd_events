"""
URL routing for Organizations app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'organizations'

router = DefaultRouter()
router.register('', views.OrganizationViewSet, basename='organization')

urlpatterns = [
    # Accept invitation (public-ish, requires auth)
    path('accept-invite/<str:token>/', views.AcceptInvitationView.as_view(), name='accept-invite'),
    # Get user's pending invitations
    path('my-invitations/', views.MyInvitationsView.as_view(), name='my-invitations'),
    # Create organization from current organizer account
    path('create-from-account/', views.CreateOrgFromAccountView.as_view(), name='create-from-account'),
    # Router URLs (CRUD, members, etc.)
    path('', include(router.urls)),
]
