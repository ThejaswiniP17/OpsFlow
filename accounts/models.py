from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ADMIN = 'ADMIN'
    TEAM_LEAD = 'TEAM_LEAD'
    MEMBER = 'MEMBER'
    
    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (TEAM_LEAD, 'Team Lead'),
        (MEMBER, 'Member'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=MEMBER,
        help_text="Designates the system-wide role of the user."
    )
    bio = models.TextField(blank=True, max_length=500, help_text="Short bio of the user.")
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True, help_text="User profile picture.")

    def is_admin(self):
        return self.role == self.ADMIN or self.is_superuser

    def is_team_lead(self):
        return self.role == self.TEAM_LEAD or self.role == self.ADMIN

    def is_member(self):
        return self.role == self.MEMBER

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
