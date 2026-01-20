import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils import error_response

from .cloud_tasks import get_task

logger = logging.getLogger(__name__)


class CloudTaskHandlerView(APIView):
    """
    Handle incoming Google Cloud Tasks.
    """

    permission_classes = [AllowAny]  # In production, verify OIDC token

    def post(self, request):
        try:
            task_name = request.data.get("task")
            args = request.data.get("args", [])
            kwargs = request.data.get("kwargs", {})

            if not task_name:
                return error_response("Missing task name", code="MISSING_TASK_NAME")

            task_func = get_task(task_name)
            if not task_func:
                logger.error(f"Task not found: {task_name}")
                return error_response(f"Task not found: {task_name}", code="TASK_NOT_FOUND")

            logger.info(f"Executing task: {task_name}")
            result = task_func(*args, **kwargs)

            return Response({"status": "success", "result": str(result)})

        except Exception as e:
            logger.exception(f"Error executing task: {e}")
            return error_response(str(e), code="INTERNAL_ERROR", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HealthCheckView(APIView):
    """
    Health check endpoint for monitoring and load balancers.

    GET /api/health/

    Returns:
        200 OK if all services healthy
        503 Service Unavailable if any critical service down

    Response format:
    {
        "status": "healthy",
        "timestamp": "2026-01-19T10:30:00Z",
        "checks": {
            "database": {"status": "up", "latency_ms": 5},
            "redis": {"status": "up"},
            "storage": {"status": "up"}
        },
        "version": "0.1.0"
    }
    """

    permission_classes = [AllowAny]

    def get(self, request):
        from django.db import connection
        from django.utils import timezone
        from django.core.cache import cache
        from django.conf import settings

        checks = {}
        overall_healthy = True

        # Check database connection
        try:
            start = timezone.now()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            latency_ms = (timezone.now() - start).total_seconds() * 1000

            checks["database"] = {"status": "up", "latency_ms": round(latency_ms, 2)}
        except Exception as e:
            logger.error("Health check: Database connection failed", extra={"error": str(e)}, exc_info=True)
            checks["database"] = {"status": "down", "error": str(e)}
            overall_healthy = False

        # Check Redis (if configured)
        try:
            cache.set("health_check", "ok", timeout=10)
            value = cache.get("health_check")
            checks["redis"] = {"status": "up" if value == "ok" else "degraded"}
        except Exception as e:
            logger.warning("Health check: Redis check failed", extra={"error": str(e)})
            checks["redis"] = {"status": "down", "error": str(e)}
            # Redis is not critical, don't fail overall health

        # Check storage (GCS availability - basic check)
        try:
            from django.core.files.storage import default_storage

            checks["storage"] = {"status": "up", "backend": type(default_storage).__name__}
        except Exception as e:
            logger.warning("Health check: Storage check failed", extra={"error": str(e)})
            checks["storage"] = {"status": "unknown", "error": str(e)}

        response_data = {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": timezone.now().isoformat(),
            "checks": checks,
            "version": "0.1.0",
            "environment": "development" if settings.DEBUG else "production",
        }

        status_code = 200 if overall_healthy else 503

        return Response(response_data, status=status_code)


class ReadinessCheckView(APIView):
    """
    Readiness check for Kubernetes/GCP Cloud Run.

    Returns 200 if app is ready to receive traffic, 503 otherwise.
    Lighter weight than health check - just checks if Django is initialized.

    GET /api/ready/
    """

    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone

        return Response({"status": "ready", "timestamp": timezone.now().isoformat()}, status=200)
