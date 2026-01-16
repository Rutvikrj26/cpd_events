"""
DRF Views for Organizations app.
"""

import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import log_audit_event
from billing.services import stripe_service
from common.rbac import roles
from events.models import Event
from events.serializers import EventListSerializer
from integrations.services import email_service
from learning.models import Course
from learning.serializers import CourseListSerializer

from .models import Organization, OrganizationMembership
from .permissions import get_user_organizations
from .serializers import (
    CreateOrgFromAccountSerializer,
    LinkOrganizerSerializer,
    OrganizationCreateSerializer,
    OrganizationDetailSerializer,
    OrganizationListSerializer,
    OrganizationMembershipInviteSerializer,
    OrganizationMembershipListSerializer,
    OrganizationMembershipUpdateSerializer,
    OrganizationPublicSerializer,
    OrganizationUpdateSerializer,
)
from .services import OrganizationLinkingService

logger = logging.getLogger(__name__)


@roles('organizer', 'admin', route_name='organizations', plans=['organization'])
class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Organization CRUD operations.

    list: List all organizations the user is a member of
    create: Create a new organization (user becomes admin)
    retrieve: Get organization details
    update: Update organization (admin+ required)
    destroy: Delete organization (admin only)
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
        # Use get_queryset to ensure user permission (must be a member)
        queryset = self.get_queryset()
        obj = get_object_or_404(queryset, uuid=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj

    def update(self, request, *args, **kwargs):
        """Update organization (admin+ required)."""
        organization = self.get_object()
        # Check admin permission
        if not organization.memberships.filter(user=request.user, role__in=['admin'], is_active=True).exists():
            return Response(
                {'detail': 'You do not have permission to update this organization.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete organization (admin only - soft delete)."""
        organization = self.get_object()
        # Check admin permission
        if not organization.memberships.filter(user=request.user, role='admin', is_active=True).exists():
            return Response(
                {'detail': 'Only admins can delete organizations.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        organization.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='onboarding/complete')
    def complete_onboarding(self, request, pk=None):
        """Mark organization onboarding as complete."""
        organization = self.get_object()

        # Verify user is admin
        if not organization.memberships.filter(user=request.user, role='admin', is_active=True).exists():
            return Response(
                {'detail': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not organization.onboarding_completed:
            organization.onboarding_completed = True
            organization.onboarding_completed_at = timezone.now()
            organization.save(update_fields=['onboarding_completed', 'onboarding_completed_at', 'updated_at'])

        return Response({
            'message': 'Onboarding completed.',
            'onboarding_completed': organization.onboarding_completed,
        })

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """List organization members (active and pending)."""
        organization = self.get_object()
        # Include active members and those with pending invitations (non-empty token)
        from django.db.models import Q

        memberships = organization.memberships.filter(
            Q(is_active=True) | (Q(invitation_token__isnull=False) & ~Q(invitation_token='') & Q(accepted_at__isnull=True))
        ).select_related('user', 'invited_by')
        serializer = OrganizationMembershipListSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='events')
    def events(self, request, pk=None):
        """List all events for this organization (admin oversight)."""
        organization = self.get_object()

        if not organization.memberships.filter(user=request.user, role='admin', is_active=True).exists():
            return Response(
                {'detail': 'You do not have permission to view organization events.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = (
            Event.objects.filter(
                organization=organization,
                deleted_at__isnull=True,
            )
            .select_related('owner', 'certificate_template')
            .order_by('-created_at')
        )

        page = self.paginate_queryset(queryset)
        serializer = EventListSerializer(
            page if page is not None else queryset,
            many=True,
            context={'request': request},
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='courses')
    def courses(self, request, pk=None):
        """List all courses for this organization (admin oversight)."""
        organization = self.get_object()

        if not organization.memberships.filter(user=request.user, role='admin', is_active=True).exists():
            return Response(
                {'detail': 'You do not have permission to view organization courses.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = (
            Course.objects.filter(
                organization=organization,
            )
            .select_related('organization', 'created_by')
            .order_by('-created_at')
        )

        page = self.paginate_queryset(queryset)
        serializer = CourseListSerializer(
            page if page is not None else queryset,
            many=True,
            context={'request': request},
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='members/lookup')
    def lookup_user(self, request, pk=None):
        """Lookup a user by email before inviting."""
        # Use get_object to verify user has access to this org
        self.get_object()

        email = request.query_params.get('email')
        if not email:
            return Response({'detail': 'Email parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        from accounts.models import User

        user = User.objects.filter(email__iexact=email).first()

        if user:
            return Response(
                {
                    'found': True,
                    'user': {
                        'email': user.email,
                        'full_name': user.full_name,
                        # Optional: avatar_url
                    },
                }
            )

        return Response({'found': False})

    @action(detail=True, methods=['post'], url_path='members/invite')
    def invite_member(self, request, pk=None):
        """Invite a new member to the organization."""
        organization = self.get_object()

        # Check permissions
        try:
            requester_membership = organization.memberships.get(user=request.user, is_active=True)
        except OrganizationMembership.DoesNotExist:
            return Response(
                {'detail': 'You are not a member of this organization.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        allowed_roles = ['admin', 'course_manager']
        if requester_membership.role not in allowed_roles:
            return Response(
                {'detail': 'You do not have permission to invite members.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = OrganizationMembershipInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        role = serializer.validated_data['role']
        title = serializer.validated_data.get('title', '')
        billing_payer = serializer.validated_data.get('billing_payer')  # For organizer role
        assigned_course_uuid = serializer.validated_data.get('assigned_course_uuid')
        assigned_course = None

        if assigned_course_uuid:
            from learning.models import Course

            assigned_course = Course.objects.filter(
                uuid=assigned_course_uuid,
                organization=organization,
            ).first()
            if not assigned_course:
                return Response(
                    {'detail': 'Assigned course not found for this organization.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Course Manager restriction: Can only invite instructors
        if requester_membership.role == 'course_manager':
            if role != OrganizationMembership.Role.INSTRUCTOR:
                return Response(
                    {'detail': 'Course Managers can only invite Instructors.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Check if user already a member
        from accounts.models import User

        try:
            user = User.objects.get(email__iexact=email)
            existing_membership = organization.memberships.filter(user=user).first()

            if existing_membership:
                if existing_membership.is_active:
                    return Response(
                        {'detail': 'User is already a member of this organization.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                # If pending or inactive, we can proceed to re-invite/reactivate
        except User.DoesNotExist:
            user = None
            existing_membership = None
            # Check if there is a pending invitation for this email (without user linked yet)
            # Note: Current model has unique constraint on (organization, user), but if user is None,
            # we rely on invitation_email or we need to check if user=None is allowed for unique constraint.
            # Django unique_together doesn't enforce uniqueness for NULLs usually.
            # Let's check for existing pending invite by email
            existing_membership = organization.memberships.filter(invitation_email=email, user__isnull=True).first()

        # Check seat availability for org-paid billable roles (organizer + course_manager)
        payer = billing_payer or 'organization'
        uses_org_seat = role in OrganizationMembership.BILLABLE_ROLES and (
            role != OrganizationMembership.Role.ORGANIZER or payer == 'organization'
        )

        if uses_org_seat:
            # If valid existing membership exists, we skip check (re-invite)
            is_reinvite = False
            if existing_membership and existing_membership.role == role:
                if role == OrganizationMembership.Role.ORGANIZER:
                    if existing_membership.organizer_billing_payer == 'organization':
                        is_reinvite = True
                else:
                    is_reinvite = True

            if not is_reinvite and hasattr(organization, 'subscription'):
                # Count occupied org-paid billable seats (active + pending invites)
                from django.db.models import Q

                occupied_seats = (
                    organization.memberships.filter(
                        Q(role=OrganizationMembership.Role.ORGANIZER, organizer_billing_payer='organization')
                        | Q(role=OrganizationMembership.Role.COURSE_MANAGER)
                    )
                    .filter(Q(is_active=True) | Q(invitation_token__isnull=False))
                    .count()
                )

                if occupied_seats >= organization.subscription.total_seats:
                    config = organization.subscription.config
                    return Response(
                        {
                            'error': {
                                'code': 'SEAT_LIMIT_REACHED',
                                'message': 'This organization has used all available seats.',
                                'details': {'seat_price_cents': config.get('seat_price_cents', 12900), 'action': 'buy_seat'},
                            }
                        },
                        status=status.HTTP_402_PAYMENT_REQUIRED,
                    )

        # Check role-specific constraints
        if role == OrganizationMembership.Role.ADMIN:
            # Check if organization already has an admin
            existing_admin = (
                organization.memberships.filter(role=OrganizationMembership.Role.ADMIN, is_active=True)
                .exclude(pk=existing_membership.pk if existing_membership else None)
                .exists()
            )

            if existing_admin:
                return Response(
                    {'detail': 'Organization already has an admin. Only one admin per organization is allowed.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Determine billing payer default based on role
        if role == OrganizationMembership.Role.ORGANIZER:
            billing_payer = billing_payer or 'organization'
        else:
            billing_payer = None

        # Create or update membership
        if existing_membership:
            membership = existing_membership
            membership.role = role
            membership.title = title
            membership.invited_by = request.user
            membership.invited_at = timezone.now()
            membership.invitation_email = email
            # If reactivating, or just updating role of pending member
            if membership.user:
                # If user exists, we keep it inactive until accepted if it was inactive
                # But if we are re-inviting, we assume it's pending again?
                # Actually if existing_membership is active, we errored out earlier.
                # So this is for pending/inactive.
                membership.is_active = False

            # If user is None (pending invite), it stays None until acceptance.

            # Set organizer billing info
            if role == OrganizationMembership.Role.ORGANIZER:
                membership.organizer_billing_payer = billing_payer

            if assigned_course_uuid is not None:
                membership.assigned_course = assigned_course
            membership.save()
            membership.generate_invitation_token()
        else:
            membership_data = {
                'organization': organization,
                'user': user,  # Can be None
                'role': role,
                'title': title,
                'invited_by': request.user,
                'invited_at': timezone.now(),
                'invitation_email': email,
                'is_active': False,  # Pending until accepted
            }

            # Add organizer billing info
            if role == OrganizationMembership.Role.ORGANIZER:
                membership_data['organizer_billing_payer'] = billing_payer

            if assigned_course_uuid is not None:
                membership_data['assigned_course'] = assigned_course

            membership = OrganizationMembership.objects.create(**membership_data)
            membership.generate_invitation_token()

        # Send invitation email
        from django.conf import settings

        from integrations.services import email_service

        invitation_url = f"{settings.SITE_URL}/accept-invite/{membership.invitation_token}"

        email_service.send_email(
            template='organization_invitation',
            recipient=email,
            context={
                'invitee_email': email,
                'organization_name': organization.name,
                'inviter_name': request.user.full_name or request.user.email,
                'role': role,
                'invitation_url': invitation_url,
            },
        )

        if membership.user:
            try:
                from accounts.notifications import create_notification

                create_notification(
                    user=membership.user,
                    notification_type='org_invite',
                    title=f"Invitation to join {organization.name}",
                    message=f"{request.user.full_name or request.user.email} invited you to join as {role}.",
                    action_url=f"/accept-invite/{membership.invitation_token}",
                    metadata={
                        'organization_uuid': str(organization.uuid),
                        'organization_name': organization.name,
                        'role': role,
                    },
                )
            except Exception as exc:
                logger.warning("Failed to create invitation notification: %s", exc)

        try:
            log_audit_event(
                actor=request.user,
                action='org_member_invited',
                object_type='organization_membership',
                object_uuid=str(membership.uuid),
                organization=organization,
                metadata={'role': role, 'invitation_email': email},
                request=request,
            )
        except Exception:
            pass

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

        # Check permissions
        try:
            requester_membership = organization.memberships.get(user=request.user, is_active=True)
        except OrganizationMembership.DoesNotExist:
            return Response(
                {'detail': 'You are not a member of this organization.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        allowed_roles = ['admin', 'course_manager']
        if requester_membership.role not in allowed_roles:
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

        # Course Manager restriction: Can only manage instructors
        if requester_membership.role == 'course_manager':
            # Cannot manage non-instructors
            if membership.role != OrganizationMembership.Role.INSTRUCTOR:
                return Response(
                    {'detail': 'Course Managers can only manage Instructors.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            # Cannot change role to anything other than instructor (redundant but safe)
            new_role = request.data.get('role')
            if new_role and new_role != OrganizationMembership.Role.INSTRUCTOR:
                return Response(
                    {'detail': 'Course Managers can only assign the Instructor role.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        assigned_course_uuid = request.data.get('assigned_course_uuid')
        if assigned_course_uuid is not None:
            role_target = request.data.get('role') or membership.role
            if role_target != OrganizationMembership.Role.INSTRUCTOR:
                return Response(
                    {'detail': 'Only instructors can be assigned to a course.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if assigned_course_uuid:
                from learning.models import Course

                assigned_course = Course.objects.filter(
                    uuid=assigned_course_uuid,
                    organization=organization,
                ).first()
                if not assigned_course:
                    return Response(
                        {'detail': 'Assigned course not found for this organization.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        serializer = OrganizationMembershipUpdateSerializer(membership, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Update subscription seat count
        if hasattr(organization, 'subscription'):
            organization.subscription.update_seat_usage()

        try:
            log_audit_event(
                actor=request.user,
                action='org_member_updated',
                object_type='organization_membership',
                object_uuid=str(membership.uuid),
                organization=organization,
                metadata={'role': membership.role},
                request=request,
            )
        except Exception:
            pass

        return Response(OrganizationMembershipListSerializer(membership).data)

    @action(detail=True, methods=['delete'], url_path='members/(?P<member_uuid>[^/.]+)/remove')
    def remove_member(self, request, pk=None, member_uuid=None):
        """Remove a member from the organization."""
        organization = self.get_object()

        # Check permissions
        try:
            requester_membership = organization.memberships.get(user=request.user, is_active=True)
        except OrganizationMembership.DoesNotExist:
            return Response(
                {'detail': 'You are not a member of this organization.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        allowed_roles = ['admin', 'course_manager']
        if requester_membership.role not in allowed_roles:
            return Response(
                {'detail': 'You do not have permission to remove members.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        membership = get_object_or_404(
            organization.memberships.select_related('user'),
            uuid=member_uuid,  # Look up by membership UUID, not user UUID
        )

        # Can't remove yourself (only applies if membership has a linked user)
        if membership.user and membership.user == request.user:
            return Response(
                {'detail': 'You cannot remove yourself. Leave the organization instead.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Course Manager restriction: Can only remove instructors
        if requester_membership.role == 'course_manager':
            if membership.role != OrganizationMembership.Role.INSTRUCTOR:
                return Response(
                    {'detail': 'Course Managers can only remove Instructors.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Can't remove the last admin
        if membership.role == OrganizationMembership.Role.ADMIN:
            admin_count = organization.memberships.filter(
                role=OrganizationMembership.Role.ADMIN,
                is_active=True,
            ).count()
            if admin_count <= 1:
                return Response(
                    {'detail': 'Cannot remove the last admin. Assign another admin first.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        membership.deactivate()

        try:
            log_audit_event(
                actor=request.user,
                action='org_member_removed',
                object_type='organization_membership',
                object_uuid=str(membership.uuid),
                organization=organization,
                metadata={'role': membership.role},
                request=request,
            )
        except Exception:
            pass

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='link-organizer')
    def link_organizer(self, request, pk=None):
        """Link an individual organizer's data to this organization."""
        organization = self.get_object()

        # Check admin permission
        if not organization.memberships.filter(user=request.user, role__in=['admin'], is_active=True).exists():
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
            try:
                log_audit_event(
                    actor=request.user,
                    action='org_organizer_linked',
                    object_type='organization_membership',
                    object_uuid=str(result['membership'].uuid),
                    organization=organization,
                    metadata={'role': serializer.validated_data['role']},
                    request=request,
                )
            except Exception:
                pass
            return Response(
                {
                    'detail': 'Your data has been linked to this organization.',
                    'events_transferred': result['events_transferred'],
                    'templates_transferred': result['templates_transferred'],
                }
            )

        # Handle invitation for external email
        if serializer.validated_data.get('organizer_email'):
            email = serializer.validated_data['organizer_email']
            role = serializer.validated_data['role']

            # Check if membership already exists
            if OrganizationMembership.objects.filter(organization=organization, user__email=email, is_active=True).exists():
                return Response(
                    {'detail': 'User is already a member of this organization.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create pending membership (if user exists) or just send invite logic
            # For simplicity, we'll assume the user might not exist yet, but we need a user object for membership
            # if we strictly follow the model. However, commonly invites track email.
            # The model OrganizationMembership REQUIRES a user ForeignKey.
            # So typically we need to invite them to join the PLATFORM first, or if they exist, link them.

            # Re-checking model: OrganizationMembership has `user = ForeignKey`.
            # So we can only invite EXISTING users for now, unless we change the model to allow null user (which we haven't planned).
            # But wait, looking at the code I viewed earlier...
            # OrganizationMembership fields:
            # user = models.ForeignKey(settings.AUTH_USER_MODEL, ...) (Not null usually, let's check model again... yes on_delete=CASCADE)
            # So we can only invite existing users.

            from django.contrib.auth import get_user_model

            User = get_user_model()

            try:
                user_to_invite = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response(
                    {'detail': 'User with this email does not exist. Please ask them to sign up first.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create pending membership
            membership, created = OrganizationMembership.objects.get_or_create(
                organization=organization,
                user=user_to_invite,
                defaults={
                    'role': role,
                    'is_active': False,  # Pending acceptance
                    'invited_by': request.user,
                },
            )

            # Generate token
            token = membership.generate_invitation_token()

            # Send email
            invite_url = f"{settings.FRONTEND_URL}/dashboard/organizations/accept-invite?token={token}"
            email_service.send_email(
                template='organization_invitation',
                recipient=email,
                context={
                    'organization_name': organization.name,
                    'inviter_name': request.user.full_name,
                    'role': role,
                    'invitation_url': invite_url,
                },
            )

            try:
                from accounts.notifications import create_notification

                create_notification(
                    user=user_to_invite,
                    notification_type='org_invite',
                    title=f"Invitation to join {organization.name}",
                    message=f"{request.user.full_name or request.user.email} invited you to join as {role}.",
                    action_url=f"/accept-invite/{token}",
                    metadata={
                        'organization_uuid': str(organization.uuid),
                        'organization_name': organization.name,
                        'role': role,
                    },
                )
            except Exception as exc:
                logger.warning("Failed to create invitation notification: %s", exc)

            try:
                log_audit_event(
                    actor=request.user,
                    action='org_member_invited',
                    object_type='organization_membership',
                    object_uuid=str(membership.uuid),
                    organization=organization,
                    metadata={'role': role, 'invitation_email': email},
                    request=request,
                )
            except Exception:
                pass

            return Response({'detail': f'Invitation sent to {email}.'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='stripe/connect')
    def stripe_connect(self, request, pk=None):
        """
        Initiate Stripe Connect onboarding.
        Returns account onboarding URL.
        """
        organization = self.get_object()

        # Check admin permission
        if not organization.memberships.filter(user=request.user, role__in=['admin'], is_active=True).exists():
            return Response(
                {'detail': 'You do not have permission to manage billing.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        from billing.services import stripe_connect_service

        # 1. Ensure Organization has a Connect Account ID
        if not organization.stripe_connect_id:
            account_id = stripe_connect_service.create_account(
                email=organization.contact_email or request.user.email,
                country='US',  # Default to US for now, or make dynamic
            )
            if not account_id:
                return Response(
                    {'detail': 'Failed to create Stripe account.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            organization.stripe_connect_id = account_id
            organization.save(update_fields=['stripe_connect_id'])

        # 2. Generate Onboarding Link
        # Redirect back to frontend organization settings -> payments
        refresh_url = f"{settings.FRONTEND_URL}/organizer/organizations/{organization.slug}/settings/payments?refresh=true"
        return_url = f"{settings.FRONTEND_URL}/organizer/organizations/{organization.slug}/settings/payments?success=true"

        onboarding_url = stripe_connect_service.create_account_link(
            account_id=organization.stripe_connect_id,
            refresh_url=refresh_url,
            return_url=return_url,
        )

        if not onboarding_url:
            return Response(
                {'detail': 'Failed to generate onboarding link.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({'url': onboarding_url})

    @action(detail=True, methods=['post'], url_path='subscription/upgrade')
    def upgrade_subscription(self, request, pk=None):
        """
        Upgrade organization subscription.
        Creates a Stripe Checkout Session for the upgrade.
        """
        organization = self.get_object()

        # Check permissions (Admin only)
        if not organization.memberships.filter(user=request.user, role__in=['admin'], is_active=True).exists():
            return Response(
                {'detail': 'You do not have permission to manage billing.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        plan = request.data.get('plan')
        if not plan:
            return Response({'detail': 'Plan is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create checkout session
        success_url = f"{settings.FRONTEND_URL}/org/{organization.slug}/billing?success=true"
        cancel_url = f"{settings.FRONTEND_URL}/org/{organization.slug}/billing?canceled=true"

        result = stripe_service.create_checkout_session(
            user=request.user,
            plan=plan,
            success_url=success_url,
            cancel_url=cancel_url,
            organization_uuid=str(organization.uuid),  # Pass organization UUID for webhook
        )

        if not result.get('success'):
            return Response({'detail': result.get('error')}, status=status.HTTP_400_BAD_REQUEST)

        try:
            log_audit_event(
                actor=request.user,
                action='org_subscription_upgrade_started',
                object_type='organization',
                object_uuid=str(organization.uuid),
                organization=organization,
                metadata={'plan': plan},
                request=request,
            )
        except Exception:
            pass

        return Response({'url': result.get('url')})

    @action(detail=True, methods=['post'], url_path='subscription/confirm')
    def confirm_checkout(self, request, pk=None, slug=None):
        """Confirm valid Stripe checkout session for organization."""
        organization = self.get_object()
        session_id = request.data.get('session_id')

        if not session_id:
            return Response({'detail': 'Session ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        result = stripe_service.confirm_organization_checkout_session(organization=organization, session_id=session_id)

        if result['success']:
            try:
                log_audit_event(
                    actor=request.user,
                    action='org_subscription_confirmed',
                    object_type='organization',
                    object_uuid=str(organization.uuid),
                    organization=organization,
                    metadata={'status': result['subscription'].status},
                    request=request,
                )
            except Exception:
                pass
            return Response({'status': 'confirmed', 'subscription_status': result['subscription'].status})
        else:
            return Response(
                {'detail': result.get('error', 'Failed to confirm subscription')}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='subscription/add-seats')
    def add_seats(self, request, pk=None):
        """
        Add seats to organization subscription.
        Updates Stripe subscription quantity immediately.
        """
        organization = self.get_object()

        # Check permissions (Admin only)
        if not organization.memberships.filter(user=request.user, role__in=['admin'], is_active=True).exists():
            return Response(
                {'detail': 'You do not have permission to manage billing.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not hasattr(organization, 'subscription') or not organization.subscription.stripe_subscription_id:
            return Response(
                {'detail': 'Organization has no active Stripe subscription.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            seats_to_add = int(request.data.get('seats', 1))
            if seats_to_add < 1:
                return Response({'detail': 'Must add at least 1 seat.'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'detail': 'Invalid seat count.'}, status=status.HTTP_400_BAD_REQUEST)

        subscription = organization.subscription
        new_total_seats = subscription.total_seats + seats_to_add

        # Update Stripe
        result = stripe_service.update_subscription_quantity(subscription.stripe_subscription_id, quantity=new_total_seats)

        if not result.get('success'):
            return Response({'detail': result.get('error')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Update local
        subscription.additional_seats += seats_to_add
        subscription.save(update_fields=['additional_seats', 'updated_at'])

        try:
            log_audit_event(
                actor=request.user,
                action='org_seats_added',
                object_type='organization_subscription',
                object_uuid=str(subscription.uuid),
                organization=organization,
                metadata={'seats_added': seats_to_add, 'total_seats': subscription.total_seats},
                request=request,
            )
        except Exception:
            pass

        return Response(
            {
                'detail': f'Added {seats_to_add} seat(s).',
                'total_seats': subscription.total_seats,
                'additional_seats': subscription.additional_seats,
            }
        )

    @action(detail=True, methods=['post'], url_path='subscription/remove-seats')
    def remove_seats(self, request, pk=None):
        """
        Remove seats from organization subscription.
        Updates Stripe subscription quantity immediately.
        """
        organization = self.get_object()

        # Check permissions (Admin only)
        if not organization.memberships.filter(user=request.user, role__in=['admin'], is_active=True).exists():
            return Response(
                {'detail': 'You do not have permission to manage billing.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not hasattr(organization, 'subscription') or not organization.subscription.stripe_subscription_id:
            return Response(
                {'detail': 'Organization has no active Stripe subscription.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            seats_to_remove = int(request.data.get('seats', 1))
            if seats_to_remove < 1:
                return Response({'detail': 'Must remove at least 1 seat.'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'detail': 'Invalid seat count.'}, status=status.HTTP_400_BAD_REQUEST)

        subscription = organization.subscription

        # Check if we can remove
        # We can't remove seats that are currently occupied
        # unused_seats = total_seats - active_organizer_seats
        unused_seats = subscription.available_seats

        if seats_to_remove > unused_seats:
            return Response(
                {
                    'detail': f'Cannot remove {seats_to_remove} seats. Only {unused_seats} unused seats available.',
                    'unused_seats': unused_seats,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Also ensure we don't go below included seats
        # We can only remove 'additional_seats'
        if seats_to_remove > subscription.additional_seats:
            return Response(
                {'detail': 'Cannot check remove included base seats.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_total_seats = subscription.total_seats - seats_to_remove

        # Update Stripe
        result = stripe_service.update_subscription_quantity(subscription.stripe_subscription_id, quantity=new_total_seats)

        if not result.get('success'):
            return Response({'detail': result.get('error')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Update local
        subscription.additional_seats -= seats_to_remove
        subscription.save(update_fields=['additional_seats', 'updated_at'])

        try:
            log_audit_event(
                actor=request.user,
                action='org_seats_removed',
                object_type='organization_subscription',
                object_uuid=str(subscription.uuid),
                organization=organization,
                metadata={'seats_removed': seats_to_remove, 'total_seats': subscription.total_seats},
                request=request,
            )
        except Exception:
            pass

        return Response(
            {
                'detail': f'Removed {seats_to_remove} seat(s).',
                'total_seats': subscription.total_seats,
                'additional_seats': subscription.additional_seats,
            }
        )

    @action(detail=True, methods=['post'], url_path='portal')
    def portal(self, request, pk=None):
        """Create Stripe Customer Portal session."""
        organization = self.get_object()

        # Check permissions (Admin only)
        if not organization.memberships.filter(user=request.user, role__in=['admin'], is_active=True).exists():
            return Response(
                {'detail': 'You do not have permission to manage billing.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not hasattr(organization, 'subscription') or not organization.subscription.stripe_customer_id:
            return Response(
                {'detail': 'Organization has no billing account configured.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return_url = f"{settings.FRONTEND_URL}/org/{organization.slug}/billing"

        result = stripe_service.create_portal_session(
            user=request.user, return_url=return_url, customer_id=organization.subscription.stripe_customer_id
        )

        if result['success']:
            return Response({'url': result['url']})
        else:
            return Response(
                {'detail': result.get('error', 'Failed to create portal session')}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def plans(self, request):
        """
        Get available organization plans and capabilities.
        """
        from billing.models import StripeProduct
        from organizations.models import OrganizationSubscription

        plans = {}
        for plan_value, _ in OrganizationSubscription.Plan.choices:
            config = OrganizationSubscription.PLAN_CONFIG.get(
                plan_value,
                OrganizationSubscription.PLAN_CONFIG[OrganizationSubscription.Plan.ORGANIZATION],
            ).copy()

            product = StripeProduct.objects.filter(plan=plan_value, is_active=True).prefetch_related('prices').first()
            if product:
                feature_limits = product.get_feature_limits()
                for key, value in feature_limits.items():
                    if value is not None:
                        config[key] = value
                if product.included_seats is not None:
                    config['included_seats'] = product.included_seats
                if product.seat_price_cents is not None:
                    config['seat_price_cents'] = product.seat_price_cents
                monthly_price = product.prices.filter(billing_interval='month', is_active=True).first()
                if monthly_price:
                    config['price_cents'] = monthly_price.amount_cents
                annual_price = product.prices.filter(billing_interval='year', is_active=True).first()
                if annual_price:
                    config['annual_price_cents'] = annual_price.amount_cents
                config['show_contact_sales'] = product.show_contact_sales

            plans[plan_value] = config

        return Response(plans)

    @action(detail=True, methods=['get'], url_path='stripe/status')
    def stripe_status(self, request, pk=None):
        """
        Check and sync Stripe Connect status.
        """
        organization = self.get_object()

        # Check admin permission
        if not organization.memberships.filter(user=request.user, role__in=['admin'], is_active=True).exists():
            return Response(
                {'detail': 'You do not have permission to view billing status.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not organization.stripe_connect_id:
            return Response(
                {
                    'connected': False,
                    'status': 'not_connected',
                    'charges_enabled': False,
                }
            )

        from billing.services import stripe_connect_service

        status_info = stripe_connect_service.get_account_status(organization.stripe_connect_id)

        if 'error' in status_info:
            return Response(
                {'detail': 'Failed to retrieve status from Stripe.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Update local state
        organization.stripe_charges_enabled = status_info.get('charges_enabled', False)
        # Use details_submitted or charges_enabled to determine 'active' status
        if status_info.get('charges_enabled'):
            organization.stripe_account_status = 'active'
        elif status_info.get('details_submitted'):
            organization.stripe_account_status = 'pending_verification'
        else:
            organization.stripe_account_status = 'restricted'

        organization.save(update_fields=['stripe_charges_enabled', 'stripe_account_status'])

        return Response(
            {
                'connected': True,
                'status': organization.stripe_account_status,
                'charges_enabled': organization.stripe_charges_enabled,
                'stripe_id': organization.stripe_connect_id,
                'details': status_info,
            }
        )

    @action(detail=False, methods=['get'], url_path='public/(?P<slug>[^/.]+)', permission_classes=[AllowAny])
    def public_profile(self, request, slug=None):
        """
        Get public profile for an organization by slug.
        No authentication required.
        """
        organization = get_object_or_404(Organization.objects.filter(is_active=True, is_public=True), slug=slug)

        serializer = OrganizationPublicSerializer(organization, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='public', permission_classes=[AllowAny])
    def public_list(self, request):
        """
        List public organizations for discovery.
        """
        queryset = Organization.objects.filter(is_active=True, is_public=True)

        search = request.query_params.get('q', '').strip()
        if search:
            queryset = queryset.filter(name__icontains=search)

        queryset = queryset.order_by('-is_verified', 'name')
        serializer = OrganizationPublicSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)


@roles('attendee', 'organizer', 'admin', route_name='accept_invitation')
class AcceptInvitationView(APIView):
    """Accept an organization invitation."""

    permission_classes = [IsAuthenticated]

    def get(self, request, token):
        """Get invitation details without accepting."""
        membership = get_object_or_404(
            OrganizationMembership.objects.select_related('organization', 'invited_by'),
            invitation_token=token,
        )

        # Check if already accepted
        if membership.accepted_at:
            return Response(
                {'detail': 'This invitation has already been accepted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        requires_subscription = False
        if membership.role == OrganizationMembership.Role.ORGANIZER and membership.organizer_billing_payer == 'organizer':
            from billing.models import Subscription

            subscription = getattr(request.user, 'subscription', None)
            if not subscription or not subscription.is_active or subscription.plan == Subscription.Plan.ATTENDEE:
                requires_subscription = True

        return Response(
            {
                'organization': {
                    'uuid': str(membership.organization.uuid),
                    'name': membership.organization.name,
                    'slug': membership.organization.slug,
                    'logo_url': membership.organization.effective_logo_url,
                },
                'role': membership.role,
                'role_display': membership.get_role_display(),
                'billing_payer': membership.organizer_billing_payer,
                'requires_subscription': requires_subscription,
                'invited_by': membership.invited_by.full_name if membership.invited_by else 'Team Admin',
                'invited_by_email': membership.invited_by.email if membership.invited_by else None,
                'invitation_email': membership.invitation_email,
            }
        )

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

        # Organizer-paid invites require an active organizer subscription
        if membership.role == OrganizationMembership.Role.ORGANIZER and membership.organizer_billing_payer == 'organizer':
            from billing.models import Subscription

            subscription, _ = Subscription.objects.get_or_create(
                user=request.user, defaults={'plan': Subscription.Plan.ATTENDEE}
            )
            if not subscription.is_active or subscription.plan == Subscription.Plan.ATTENDEE:
                return Response(
                    {
                        'detail': 'An active organizer subscription is required to accept this invitation.',
                        'code': 'ORGANIZER_SUBSCRIPTION_REQUIRED',
                    },
                    status=status.HTTP_402_PAYMENT_REQUIRED,
                )

            membership.linked_subscription = subscription

        # Accept the invitation
        membership.accept_invitation()
        if membership.linked_subscription_id:
            membership.save(update_fields=['linked_subscription', 'updated_at'])

        try:
            log_audit_event(
                actor=request.user,
                action='org_invitation_accepted',
                object_type='organization_membership',
                object_uuid=str(membership.uuid),
                organization=membership.organization,
                metadata={'role': membership.role},
                request=request,
            )
        except Exception:
            pass

        return Response(
            {
                'detail': f'You have joined {membership.organization.name}.',
                'organization': OrganizationListSerializer(
                    membership.organization,
                    context={'request': request},
                ).data,
            }
        )


@roles('attendee', 'organizer', 'course_manager', 'admin', route_name='my_invitations')
class MyInvitationsView(APIView):
    """Get current user's pending organization invitations."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return pending invitations for the current user (matched by email or user)."""
        from django.db.models import Q

        # Find pending invitations for this user (by email or linked user)
        pending = (
            OrganizationMembership.objects.filter(
                Q(invitation_email=request.user.email) | Q(user=request.user),
                accepted_at__isnull=True,
            )
            .filter(
                # Must have a valid invitation token
                invitation_token__isnull=False,
            )
            .exclude(
                invitation_token='',
            )
            .select_related('organization', 'invited_by')
        )

        invitations = []
        for m in pending:
            invitations.append(
                {
                    'token': m.invitation_token,
                    'organization': {
                        'uuid': str(m.organization.uuid),
                        'name': m.organization.name,
                        'slug': m.organization.slug,
                        'logo_url': m.organization.effective_logo_url,
                    },
                    'role': m.role,
                    'role_display': m.get_role_display(),
                    'invited_by': m.invited_by.full_name if m.invited_by else 'Team Admin',
                    'invited_at': m.invited_at.isoformat() if m.invited_at else None,
                }
            )

        return Response(invitations)


@roles('organizer', 'admin', route_name='create_org_from_account')
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
