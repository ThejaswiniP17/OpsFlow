from django.db import models
from django.conf import settings

class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="User receiving the notification."
    )
    title = models.CharField(max_length=150, help_text="Brief subject of the notification.")
    message = models.TextField(help_text="Detailed notification content.")
    is_read = models.BooleanField(default=False, help_text="True if the user has viewed the notification.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f"Notification for {self.recipient.username} - Read: {self.is_read}"
