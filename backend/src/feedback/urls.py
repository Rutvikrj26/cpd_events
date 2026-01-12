from rest_framework.routers import DefaultRouter

from .views import EventFeedbackViewSet

router = DefaultRouter()
router.register(r'', EventFeedbackViewSet)

urlpatterns = router.urls
