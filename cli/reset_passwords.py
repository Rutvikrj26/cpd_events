from django.contrib.auth import get_user_model
User = get_user_model()

# Organizer
try:
    org = User.objects.get(email='organizer@example.com')
    org.set_password('password')
    org.save()
    print("Updated organizer password")
except User.DoesNotExist:
    print("Organizer does not exist")

# Attendee
try:
    att = User.objects.get(email='attendee@example.com')
    att.set_password('password')
    att.save()
    print("Updated attendee password")
except User.DoesNotExist:
    print("Attendee does not exist")
