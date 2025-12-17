"""
Contacts app URL routing.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'contacts'

# Main routers
router = DefaultRouter()
router.register(r'contact-lists', views.ContactListViewSet, basename='contact-list')
router.register(r'tags', views.TagViewSet, basename='tag')

# Nested contacts router
contact_router = DefaultRouter()
contact_router.register(r'contacts', views.ListContactViewSet, basename='list-contact')

urlpatterns = [
    # Main contact list and tag API
    path('', include(router.urls)),
    # Nested: /contact-lists/{list_uuid}/contacts/
    path('contact-lists/<uuid:list_uuid>/', include(contact_router.urls)),
]
