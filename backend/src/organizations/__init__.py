"""
Organizations app - Organization accounts with team management.

Models:
- Organization: Entity that owns events, courses, and templates
- OrganizationMembership: Links users to organizations with roles
- OrganizationSubscription: Per-seat billing for organizations
"""

default_app_config = 'organizations.apps.OrganizationsConfig'
