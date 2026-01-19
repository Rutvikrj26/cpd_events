"""
Promo Code API views.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from common.permissions import CanCreateEvents
from events.models import Event

from .models import PromoCode
from .serializers import (
    PromoCodeSerializer,
    PromoCodeUsageSerializer,
    ValidatePromoCodeSerializer,
)
from .services import (
    PromoCodeError,
    PromoCodeNotFoundError,
    promo_code_service,
)


class PromoCodeViewSet(viewsets.ModelViewSet):
    """
    API endpoints for managing promo codes (organizer).

    list: GET /promo-codes/
    create: POST /promo-codes/
    retrieve: GET /promo-codes/{uuid}/
    update: PUT /promo-codes/{uuid}/
    partial_update: PATCH /promo-codes/{uuid}/
    destroy: DELETE /promo-codes/{uuid}/
    """

    serializer_class = PromoCodeSerializer
    permission_classes = [IsAuthenticated, CanCreateEvents]
    lookup_field = "uuid"

    def get_queryset(self):
        """Filter to codes owned by current user."""
        user = self.request.user
        return PromoCode.objects.filter(owner=user).prefetch_related("events").distinct()

    @action(detail=True, methods=["get"])
    def usages(self, request, uuid=None):
        """
        Get usage records for a promo code.

        GET /promo-codes/{uuid}/usages/
        """
        promo_code = self.get_object()
        usages = promo_code.usages.select_related("registration", "registration__event").order_by("-created_at")

        serializer = PromoCodeUsageSerializer(usages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, uuid=None):
        """
        Toggle promo code active status.

        POST /promo-codes/{uuid}/toggle-active/
        """
        promo_code = self.get_object()
        promo_code.is_active = not promo_code.is_active
        promo_code.save(update_fields=["is_active", "updated_at"])

        return Response(
            {
                "is_active": promo_code.is_active,
                "message": f"Promo code {'activated' if promo_code.is_active else 'deactivated'}.",
            }
        )


class PublicPromoCodeViewSet(viewsets.ViewSet):
    """
    Public API for validating promo codes during registration.
    """

    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"])
    def validate(self, request):
        """
        Validate a promo code and return discount preview.

        POST /public/promo-codes/validate/

        Request body:
        {
            "code": "SAVE20",
            "event_uuid": "...",
            "email": "user@example.com"
        }

        Response (success):
        {
            "valid": true,
            "code": "SAVE20",
            "discount_type": "percentage",
            "discount_value": "20.00",
            "discount_display": "20% off",
            "original_price": "50.00",
            "discount_amount": "10.00",
            "final_price": "40.00",
            "promo_code_uuid": "..."
        }

        Response (error):
        {
            "valid": false,
            "error": "This promo code has expired."
        }
        """
        serializer = ValidatePromoCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]
        event_uuid = serializer.validated_data["event_uuid"]
        email = serializer.validated_data["email"]

        # Get event
        try:
            event = Event.objects.get(uuid=event_uuid, deleted_at__isnull=True)
        except Event.DoesNotExist:
            return Response({"valid": False, "error": "Event not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get current user if authenticated
        user = request.user if request.user.is_authenticated else None

        try:
            result = promo_code_service.validate_and_preview(code=code, event=event, email=email, user=user)
            return Response(result)

        except PromoCodeNotFoundError as e:
            return Response({"valid": False, "error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except PromoCodeError as e:
            return Response({"valid": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
