from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.models import BaseModel


class EventFeedback(BaseModel):
    """
    Post-event feedback from attendees.
    
    Required for CPD compliance to evaluate learning outcomes and speaker effectiveness.
    """
    event = models.ForeignKey(
        'events.Event', on_delete=models.CASCADE, related_name='feedback', help_text="Event being evaluated"
    )
    registration = models.ForeignKey(
        'registrations.Registration', 
        on_delete=models.CASCADE, 
        related_name='feedback',
        help_text="Registration record of the attendee providing feedback"
    )
    
    # Quantitative Ratings (1-5 Scale)
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Overall event rating (1-5)"
    )
    content_quality_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating of content quality and relevance (1-5)"
    )
    speaker_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating of speaker effectiveness (1-5)"
    )
    
    # Qualitative Feedback
    comments = models.TextField(blank=True, help_text="General comments and suggestions")
    
    # Privacy
    is_anonymous = models.BooleanField(default=False, help_text="If true, hide attendee identity from organizer")

    class Meta:
        db_table = 'event_feedback'
        ordering = ['-created_at']
        verbose_name = 'Event Feedback'
        verbose_name_plural = 'Event Feedback'
        unique_together = ['event', 'registration']  # One feedback per registration

    def __str__(self):
        return f"Feedback for {self.event.title} by {self.registration}"
