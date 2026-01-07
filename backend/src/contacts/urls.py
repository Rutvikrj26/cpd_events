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
router.register(r'contacts', views.ContactViewSet, basename='contact')
router.register(r'tags', views.TagViewSet, basename='tag')

urlpatterns = [
    path('', include(router.urls)),
]
