from django.contrib.auth import get_user_model
User = get_user_model()

# Organizer
if not User.objects.filter(email='organizer@example.com').exists():
    User.objects.create_user('organizer@example.com', 'password', full_name='Organizer User', account_type='organizer', is_staff=True, is_superuser=True)
    print("Created organizer@example.com")
else:
    print("Organizer already exists")

# Attendee
if not User.objects.filter(email='attendee@example.com').exists():
    User.objects.create_user('attendee@example.com', 'password', full_name='Attendee User', account_type='attendee')
    print("Created attendee@example.com")
else:
    print("Attendee already exists")
