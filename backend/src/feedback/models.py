from django.db import models

from common.models import BaseModel


class EventFeedback(BaseModel):
    """
    Post-event feedback from attendees.

    Answers are stored as FeedbackFieldResponse rows pointing to FeedbackField
    definitions configured by the organizer. Required for CPD compliance to
    evaluate learning outcomes and speaker effectiveness.
    """

    event = models.ForeignKey(
        'events.Event', on_delete=models.CASCADE, related_name='feedback', help_text="Event being evaluated"
    )
    session = models.ForeignKey(
        'events.EventSession',
        on_delete=models.CASCADE,
        related_name='feedback',
        null=True,
        blank=True,
        help_text="Session being evaluated; null for event-level feedback",
    )
    registration = models.ForeignKey(
        'registrations.Registration',
        on_delete=models.CASCADE,
        related_name='feedback',
        help_text="Registration record of the attendee providing feedback",
    )

    # Privacy
    is_anonymous = models.BooleanField(default=False, help_text="If true, hide attendee identity from organizer")

    class Meta:
        db_table = 'event_feedback'
        ordering = ['-created_at']
        verbose_name = 'Event Feedback'
        verbose_name_plural = 'Event Feedback'
        constraints = [
            models.UniqueConstraint(
                fields=['event', 'session', 'registration'],
                name='unique_feedback_per_session_registration',
            ),
        ]

    def __str__(self):
        label = self.event.title
        if self.session_id:
            label = f"{label} / session {self.session_id}"
        return f"Feedback for {label} by {self.registration}"


class FeedbackField(BaseModel):
    """
    Admin-configurable question on an event's feedback form.
    """

    class FieldType(models.TextChoices):
        RATING = 'rating', 'Rating (1-5)'
        TEXT = 'text', 'Single Line Text'
        TEXTAREA = 'textarea', 'Multi-line Text'
        SELECT = 'select', 'Dropdown'
        MULTISELECT = 'multiselect', 'Multi-select'
        CHECKBOX = 'checkbox', 'Yes/No Checkbox'
        RADIO = 'radio', 'Radio Buttons'
        DATE = 'date', 'Date'
        NUMBER = 'number', 'Number'

    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='feedback_fields')

    label = models.CharField(max_length=200, help_text="Question label")
    field_type = models.CharField(max_length=20, choices=FieldType.choices)
    required = models.BooleanField(default=False)
    placeholder = models.CharField(max_length=200, blank=True)
    help_text = models.CharField(max_length=500, blank=True)

    # Select / multiselect / radio
    options = models.JSONField(default=list, blank=True, help_text="Choice list for select / multiselect / radio fields")

    # Number / rating bounds
    min_value = models.IntegerField(null=True, blank=True)
    max_value = models.IntegerField(null=True, blank=True)

    order = models.PositiveIntegerField(default=0, help_text="Display order (0 = first)")

    class Meta:
        db_table = 'feedback_fields'
        ordering = ['order', 'id']
        verbose_name = 'Feedback Field'
        verbose_name_plural = 'Feedback Fields'

    def __str__(self):
        return f"{self.event.title} - {self.label}"


class FeedbackFieldResponse(BaseModel):
    """
    An attendee's answer to a single FeedbackField.

    `value` stores the raw answer as JSON so that numeric, string, and list
    answers all fit in one column. Consumers should use `get_value()` /
    `set_value()` helpers rather than touching the column directly.
    """

    feedback = models.ForeignKey(EventFeedback, on_delete=models.CASCADE, related_name='field_responses')
    field = models.ForeignKey(FeedbackField, on_delete=models.CASCADE, related_name='responses')
    value = models.JSONField(null=True, blank=True, help_text="Answer (type depends on field.field_type)")

    class Meta:
        db_table = 'feedback_field_responses'
        ordering = ['field__order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['feedback', 'field'],
                name='unique_response_per_field',
            ),
        ]
        verbose_name = 'Feedback Field Response'
        verbose_name_plural = 'Feedback Field Responses'

    def __str__(self):
        return f"{self.feedback_id}: {self.field.label} = {self.value!r}"
