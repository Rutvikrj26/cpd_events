"""
DRF Views for Organizations app.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Organization, OrganizationMembership, OrganizationSubscription
from .permissions import IsOrgAdmin, IsOrgManager, IsOrgOwner, get_user_organizations
from .serializers import (
    CreateOrgFromAccountSerializer,
    LinkOrganizerSerializer,
    OrganizationCreateSerializer,
    OrganizationDetailSerializer,
    OrganizationListSerializer,
    OrganizationMembershipInviteSerializer,
    OrganizationMembershipListSerializer,
    OrganizationMembershipUpdateSerializer,
    OrganizationUpdateSerializer,
)
from .services import OrganizationLinkingService


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Organization CRUD operations.

    list: List all organizations the user is a member of
    create: Create a new organization (user becomes owner)
    retrieve: Get organization details
    update: Update organization (admin+ required)
    destroy: Delete organization (owner only)
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return organizations user is a member of."""
        return get_user_organizations(self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return OrganizationListSerializer
        if self.action == 'create':
            return OrganizationCreateSerializer
        if self.action in ['update', 'partial_update']:
            return OrganizationUpdateSerializer
        return OrganizationDetailSerializer

    def get_object(self):
        """Get organization by UUID."""
        queryset = Organization.objects.filter(is_active=True)
        obj = get_object_or_404(queryset, uuid=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj

    def update(self, request, *args, **kwargs):
        """Update organization (admin+ required)."""
        organization = self.get_object()
        # Check admin permission
        if not organization.memberships.filter(
            user=request.user, role__in=['owner', 'admin'], is_active=True
        ).exists():
            return Response(
                {'detail': 'You do not have permission to update this organization.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete organization (owner only - soft delete)."""
        organization = self.get_object()
        # Check owner permission
        if not organization.memberships.filter(
            user=request.user, role='owner', is_active=True
        ).exists():
            return Response(
                {'detail': 'Only owners can delete organizations.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        organization.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """List organization members."""
        organization = self.get_object()
        memberships = organization.memberships.filter(is_active=True).select_related('user', 'invited_by')
        serializer = OrganizationMembershipListSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='members/invite')
    def invite_member(self, request, pk=None):
        """Invite a new member to the organization."""
        organization = self.get_object()

        # Check admin permission
        if not organization.memberships.filter(
            user=request.user, role__in=['owner', 'admin'], is_active=True
        ).exists():
            return Response(
                {'detail': 'You do not have permission to invite members.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OrganizationMembershipInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        role = serializer.validated_data['role']
        title = serializer.validated_data.get('title', '')

        # Check if user already a member
        from accounts.models import User

        try:
            user = User.objects.get(email__iexact=email)
            if organization.memberships.filter(user=user).exists():
                return Response(
                    {'detail': 'User is already a member of this organization.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except User.DoesNotExist:
            user = None

        # Check seat availability for organizer roles
        if role in ['owner', 'admin', 'manager']:
            if hasattr(organization, 'subscription') and not organization.subscription.can_add_organizer():
                return Response(
                    {'detail': 'No available organizer seats. Please upgrade your plan.'},
                    status=status.HTTP_402_PAYMENT_REQUIRED,
                )

        # Create pending membership
        membership = OrganizationMembership.objects.create(
            organization=organization,
            user=user,
            role=role,
            title=title,
            invited_by=request.user,
            invited_at=timezone.now(),
            invitation_email=email,
            is_active=False,  # Pending until accepted
        )
        membership.generate_invitation_token()

        # TODO: Send invitation email

        return Response(
            {
                'detail': f'Invitation sent to {email}',
                'invitation_token': membership.invitation_token,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['patch'], url_path='members/(?P<member_uuid>[^/.]+)')
    def update_member(self, request, pk=None, member_uuid=None):
        """Update a member's role or title."""
        organization = self.get_object()

        # Check admin permission
        if not organization.memberships.filter(
            user=request.user, role__in=['owner', 'admin'], is_active=True
        ).exists():
            return Response(
                {'detail': 'You do not have permission to update members.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        membership = get_object_or_404(
            organization.memberships.select_related('user'),
            user__uuid=member_uuid,
        )

        # Can't change your own role
        if membership.user == request.user:
            return Response(
                {'detail': 'You cannot change your own role.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OrganizationMembershipUpdateSerializer(membership, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Update subscription seat count
        if hasattr(organization, 'subscription'):
            organization.subscription.update_seat_usage()

        return Response(OrganizationMembershipListSerializer(membership).data)

    @action(detail=True, methods=['delete'], url_path='members/(?P<member_uuid>[^/.]+)/remove')
    def remove_member(self, request, pk=None, member_uuid=None):
        """Remove a member from the organization."""
        organization = self.get_object()

        # Check admin permission
        if not organization.memberships.filter(
            user=request.user, role__in=['owner', 'admin'], is_active=True
        ).exists():
            return Response(
                {'detail': 'You do not have permission to remove members.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        membership = get_object_or_404(
            organization.memberships.select_related('user'),
            user__uuid=member_uuid,
        )

        # Can't remove yourself
        if membership.user == request.user:
            return Response(
                {'detail': 'You cannot remove yourself. Leave the organization instead.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Can't remove the last owner
        if membership.role == 'owner':
            owner_count = organization.memberships.filter(role='owner', is_active=True).count()
            if owner_count <= 1:
                return Response(
                    {'detail': 'Cannot remove the last owner. Transfer ownership first.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        membership.deactivate()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='link-organizer')
    def link_organizer(self, request, pk=None):
        """Link an individual organizer's data to this organization."""
        organization = self.get_object()

        # Check admin permission
        if not organization.memberships.filter(
            user=request.user, role__in=['owner', 'admin'], is_active=True
        ).exists():
            return Response(
                {'detail': 'You do not have permission to link organizers.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = LinkOrganizerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Link current user's data if no email specified
        if not serializer.validated_data.get('organizer_email'):
            result = OrganizationLinkingService.link_organizer_to_org(
                user=request.user,
                organization=organization,
                role=serializer.validated_data['role'],
            )
            return Response({
                'detail': 'Your data has been linked to this organization.',
                'events_transferred': result['events_transferred'],
                'templates_transferred': result['templates_transferred'],
            })

        # TODO: Handle inviting other organizers

        return Response({'detail': 'Link invitation sent.'}, status=status.HTTP_201_CREATED)


class AcceptInvitationView(APIView):
    """Accept an organization invitation."""

    permission_classes = [IsAuthenticated]

    def post(self, request, token):
        """Accept invitation using token."""
        membership = get_object_or_404(
            OrganizationMembership.objects.select_related('organization'),
            invitation_token=token,
        )

        # Check if already accepted
        if membership.accepted_at:
            return Response(
                {'detail': 'This invitation has already been accepted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # If membership has no user, link to current user
        if membership.user is None:
            membership.user = request.user

        # Verify email matches
        elif membership.user != request.user:
            return Response(
                {'detail': 'This invitation was sent to a different email address.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Accept the invitation
        membership.accept_invitation()

        return Response({
            'detail': f'You have joined {membership.organization.name}.',
            'organization': OrganizationListSerializer(
                membership.organization,
                context={'request': request},
            ).data,
        })


class CreateOrgFromAccountView(APIView):
    """Create an organization from the current organizer's account."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Preview what data would be linked."""
        if not request.user.is_organizer:
            return Response(
                {'detail': 'Only organizers can create organizations.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        summary = OrganizationLinkingService.get_linkable_data_summary(request.user)
        return Response(summary)

    def post(self, request):
        """Create organization from current account."""
        if not request.user.is_organizer:
            return Response(
                {'detail': 'Only organizers can create organizations.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CreateOrgFromAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization = OrganizationLinkingService.create_org_from_organizer(
            user=request.user,
            name=serializer.validated_data.get('name'),
            slug=serializer.validated_data.get('slug'),
        )

        return Response(
            OrganizationDetailSerializer(organization, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )
