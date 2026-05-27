from django.db import models
from django.conf import settings
from tasks.models import Task
from teams.models import Team

class ActivityLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        help_text="The user who performed the action."
    )
    action_type = models.CharField(max_length=50, help_text="Type of action (e.g., LOGIN, TASK_CREATE, TASK_UPDATE).")
    description = models.TextField(help_text="Human-readable description of the event.")
    
    # Track related models
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        indexes = [
            models.Index(fields=['action_type']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        actor_name = self.actor.username if self.actor else "System"
        return f"{actor_name} - {self.action_type} at {self.timestamp}"
