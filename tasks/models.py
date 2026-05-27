from django.db import models
from django.conf import settings
from teams.models import Team

class Task(models.Model):
    # Status Options
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'
    BLOCKED = 'BLOCKED'
    CLOSED = 'CLOSED'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (IN_PROGRESS, 'In Progress'),
        (COMPLETED, 'Completed'),
        (BLOCKED, 'Blocked'),
        (CLOSED, 'Closed'),
    ]

    # Priority Levels
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'
    
    PRIORITY_CHOICES = [
        (LOW, 'Low'),
        (MEDIUM, 'Medium'),
        (HIGH, 'High'),
        (CRITICAL, 'Critical'),
    ]

    title = models.CharField(max_length=200, help_text="Short title of the task.")
    description = models.TextField(blank=True, help_text="Detailed task description.")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        help_text="Workflow status of this task."
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=MEDIUM,
        help_text="Urgency or priority level."
    )
    due_date = models.DateField(null=True, blank=True, help_text="Deadline for task completion.")
    
    # Relationships
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='tasks', help_text="Team owning this task.")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        help_text="Member assigned to work on this task."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks',
        help_text="Creator of this task."
    )
    
    # Attachments
    attachment = models.FileField(upload_to='tasks/', blank=True, null=True, help_text="Any design doc, screenshot, or code attachment.")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"Task #{self.id}: {self.title} ({self.get_status_display()})"


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_comments')
    content = models.TextField(help_text="Write your comment...")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on Task #{self.task.id}"
