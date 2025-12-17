import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from common.utils import error_response
from rest_framework.views import APIView

from .cloud_tasks import get_task

logger = logging.getLogger(__name__)


class CloudTaskHandlerView(APIView):
    """
    Handle incoming Google Cloud Tasks.
    """

    permission_classes = [AllowAny]  # In production, verify OIDC token

    def post(self, request):
        try:
            task_name = request.data.get('task')
            args = request.data.get('args', [])
            kwargs = request.data.get('kwargs', {})

            if not task_name:
                return error_response('Missing task name', code='MISSING_TASK_NAME')

            task_func = get_task(task_name)
            if not task_func:
                logger.error(f"Task not found: {task_name}")
                return error_response(f"Task not found: {task_name}", code='TASK_NOT_FOUND')

            logger.info(f"Executing task: {task_name}")
            result = task_func(*args, **kwargs)

            return Response({'status': 'success', 'result': str(result)})

        except Exception as e:
            logger.exception(f"Error executing task: {e}")
            return error_response(str(e), code='INTERNAL_ERROR', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
