from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from badges.models import BadgeTemplate, IssuedBadge
from badges.services import badge_service
from accounts.models import User
from registrations.models import Registration
from events.models import Event
from io import BytesIO
from PIL import Image
from unittest import mock

class BadgeServiceTest(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(email='test@example.com', password='password')
        
        # Create simple image for template
        img = Image.new('RGB', (100, 100), color='white')
        img_io = BytesIO()
        img.save(img_io, format='PNG')
        img_content = img_io.getvalue()
        
        self.template_image = SimpleUploadedFile(
            name='test_template.png',
            content=img_content,
            content_type='image/png'
        )
        
        # Create template
        self.template = BadgeTemplate.objects.create(
            owner=self.user,
            name="Test Badge",
            start_image=self.template_image,
            width_px=100,
            height_px=100,
            field_positions={
                'attendee_name': {'x': 10, 'y': 10, 'fontSize': 12, 'color': 'black'}
            }
        )

    def test_generate_badge_image(self):
        # Create a mock badge (without foreign keys for simplicity if allowed, 
        # but IssuedBadge requires recipient/template. 
        # Registration is optional but good for data)
        
        badge = IssuedBadge.objects.create(
            template=self.template,
            recipient=self.user,
            issued_by=self.user,
            badge_data={'attendee_name': 'John Doe'}
        )
        
        image_bytes = badge_service.generate_badge_image(badge)
        
        self.assertIsNotNone(image_bytes)
        self.assertTrue(len(image_bytes) > 0)
        
        # Verify it's a valid image
        generated_img = Image.open(BytesIO(image_bytes))
        self.assertEqual(generated_img.format, 'PNG')

    @mock.patch('badges.services.badge_service.send_badge_email')
    @mock.patch('badges.services.badge_service.upload_badge_image')
    @mock.patch('badges.services.badge_service.generate_badge_image')
    @mock.patch('billing.models.Subscription.check_certificate_limit')
    def test_issue_badge_success(self, mock_check_limit, mock_generate, mock_upload, mock_email):
        # Setup mock return
        mock_check_limit.return_value = True
        mock_generate.return_value = b'fake_image_bytes'
        from django.utils import timezone
        # Create registration
        event = Event.objects.create(
            owner=self.user, 
            title="Test Event",
            starts_at=timezone.now(),
            duration_minutes=60
        )
        registration = Registration.objects.create(
            event=event, 
            user=self.user,
            status='confirmed'
        )

        result = badge_service.issue_badge(template=self.template, registration=registration, issued_by=self.user)
        
        self.assertTrue(result['success'], msg=f"Issue failed with: {result.get('error')}")
        self.assertIsNotNone(result['badge'])
        self.assertEqual(result['badge'].recipient, self.user)
        
        # Check side effects
        mock_upload.assert_called_once()
        mock_email.assert_called_once()

    def test_issue_bulk(self):
        from django.utils import timezone
        # Setup
        event = Event.objects.create(
            owner=self.user, 
            title="Bulk Event",
            starts_at=timezone.now(),
            duration_minutes=60
        )
        
        # Create 3 registrations
        users = [User.objects.create_user(email=f'u{i}@test.com', password='pw') for i in range(3)]
        for u in users:
            Registration.objects.create(event=event, user=u, email=u.email, status='attended')
            
        # Ensure template is active and owned by event owner
        self.template.is_active = True
        self.template.save()
            
        with mock.patch('badges.services.badge_service.issue_badge') as mock_issue:
            mock_issue.side_effect = lambda template, registration, issued_by: {'success': True}
            
            results = badge_service.issue_bulk(event, issued_by=self.user)
            
            self.assertEqual(results['total'], 3)
            self.assertEqual(results['success'], 3)
            self.assertEqual(mock_issue.call_count, 3)

    def test_qr_code_generation(self):
        # Verify valid PIL image returned
        img = badge_service._generate_qr_code("https://example.com")
        self.assertIsNotNone(img)
        self.assertEqual(img.mode, 'RGB')
        self.assertTrue(img.size[0] > 0)

    def test_revoke_badge(self):
        """Test revoking a badge."""
        badge = IssuedBadge.objects.create(
            registration=None,
            template=self.template,
            recipient=self.user,
            issued_by=self.user,
            status='active'
        )
        
        self.assertTrue(badge.can_be_revoked)
        
        badge.revoke(user=self.user, reason="Test revocation")
        
        badge.refresh_from_db()
        self.assertEqual(badge.status, 'revoked')
        self.assertFalse(badge.can_be_revoked)
        
        # Check history
        history = badge.status_history.first()
        self.assertIsNotNone(history)
        self.assertEqual(history.from_status, 'active')
        self.assertEqual(history.to_status, 'revoked')
        self.assertEqual(history.changed_by, self.user)
        self.assertEqual(history.reason, "Test revocation")
        
        # Functionality check: cannot revoke again
        with self.assertRaises(ValueError):
            badge.revoke(user=self.user)
