"""Promo Code API views.

Promo codes are redeemed at Stripe Checkout — we no longer expose a
validation endpoint. This module only exposes the organizer CRUD surface
for creating/listing codes; Stripe owns the redemption UX.
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.permissions import IsOrganizerOrAdmin
from common.rbac import roles

from .models import PromoCode
from .serializers import PromoCodeSerializer, PromoCodeUsageSerializer


@roles('organizer', 'admin', route_name='promo_codes')
class PromoCodeViewSet(viewsets.ModelViewSet):
    """Organizer CRUD for promo codes."""

    serializer_class = PromoCodeSerializer
    permission_classes = [IsAuthenticated, IsOrganizerOrAdmin]
    lookup_field = 'uuid'

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name="admin").exists():
            return PromoCode.objects.all().prefetch_related('events').distinct()
        queryset = PromoCode.objects.filter(owner=user)
        if hasattr(user, 'organization') and user.organization:
            queryset = queryset | PromoCode.objects.filter(organization=user.organization)
        return queryset.prefetch_related('events').distinct()

    @action(detail=True, methods=['get'])
    def usages(self, request, uuid=None):
        promo_code = self.get_object()
        usages = promo_code.usages.select_related(
            'registration', 'registration__event'
        ).order_by('-created_at')
        return Response(PromoCodeUsageSerializer(usages, many=True).data)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, uuid=None):
        promo_code = self.get_object()
        promo_code.is_active = not promo_code.is_active
        promo_code.save(update_fields=['is_active', 'updated_at'])
        return Response({
            'is_active': promo_code.is_active,
            'message': f"Promo code {'activated' if promo_code.is_active else 'deactivated'}.",
        })

    @action(detail=True, methods=['post'], url_path='sync-stripe')
    def sync_stripe(self, request, uuid=None):
        """Push this code's current definition to Stripe (admin action)."""
        from .services import sync_to_stripe, PromoCodeSyncError

        promo_code = self.get_object()
        try:
            sync_to_stripe(promo_code)
        except PromoCodeSyncError as exc:
            return Response({'error': str(exc)}, status=400)
        return Response({
            'stripe_coupon_id': promo_code.stripe_coupon_id,
            'stripe_promotion_code_id': promo_code.stripe_promotion_code_id,
        })
