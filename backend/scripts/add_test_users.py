from django.contrib.auth import get_user_model
from billing.models import Subscription
from django.utils import timezone

User = get_user_model()

def create_test_user(email, plan_type, first_name, last_name):
    # Create or get user
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'first_name': first_name,
            'last_name': last_name,
            'is_active': True,
            'email_verified': True,
        }
    )
    if created:
        print(f"Created user: {email}")
    else:
        print(f"User already exists: {email}")
    
    user.set_password('password123')
    user.save()
    print(f"Set password for user: {email}")

    # Create or update subscription
    subscription, sub_created = Subscription.objects.get_or_create(
        user=user,
        defaults={
            'plan': plan_type,
            'status': Subscription.Status.ACTIVE,
            'billing_interval': Subscription.BillingInterval.MONTH,
            'current_period_start': timezone.now(),
        }
    )
    
    if not sub_created:
        subscription.plan = plan_type
        subscription.status = Subscription.Status.ACTIVE
        subscription.save()
        print(f"Updated subscription for {email} to {plan_type}")
    else:
        print(f"Created subscription for {email} as {plan_type}")

# Define users to create
test_users = [
    ('attendee@example.com', Subscription.Plan.ATTENDEE, 'Test', 'Attendee'),
    ('organizer@example.com', Subscription.Plan.ORGANIZER, 'Test', 'Organizer'),
    ('lms@example.com', Subscription.Plan.LMS, 'Test', 'LMS'),
    ('pro@example.com', Subscription.Plan.PRO, 'Test', 'Pro'),
]

for email, plan, first, last in test_users:
    create_test_user(email, plan, first, last)

print("Done creating test users.")
