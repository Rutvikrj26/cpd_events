from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from badges.models import BadgeTemplate, IssuedBadge
from badges.serializers import BadgeTemplateSerializer, IssuedBadgeSerializer
from badges.services import badge_service
from registrations.models import Registration

class BadgeTemplateViewSet(viewsets.ModelViewSet):
    """
    CRUD for Badge Templates.
    """
    serializer_class = BadgeTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        return BadgeTemplate.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """Generate a preview of the badge template."""
        template = self.get_object()
        # Mock data for preview
        dummy_data = {
            'attendee_name': request.user.full_name,
            'event_title': 'Sample Event',
            'issued_date': '2025-01-01'
        }
        
        image_bytes = badge_service._render_image(template, dummy_data)
        if not image_bytes:
            return Response({'error': 'Failed to generate preview'}, status=400)
            
        import base64
        b64 = base64.b64encode(image_bytes).decode('utf-8')
        return Response({'preview_base64': f"data:image/png;base64,{b64}"})


class IssuedBadgeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnly view for issued badges (My Badges).
    """
    serializer_class = IssuedBadgeSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        # Badges earned by the user
        queryset = IssuedBadge.objects.filter(status='active')
        
        if self.request.query_params.get('issued_by_me') == 'true':
            return queryset.filter(issued_by=self.request.user)
            
        return queryset.filter(recipient=self.request.user)

    @action(detail=False, methods=['get'])
    def public(self, request):
        """Public verification endpoint (handled separately strictly speaking, but handy here)."""
        code = request.query_params.get('code')
        if not code:
            return Response({'error': 'Code required'}, status=400)
        
        badge = IssuedBadge.objects.filter(verification_code=code, status='active').first() or \
                IssuedBadge.objects.filter(short_code=code, status='active').first()
                
        if not badge:
            return Response({'error': 'Invalid badge'}, status=404)
            
        return Response(IssuedBadgeSerializer(badge).data)
