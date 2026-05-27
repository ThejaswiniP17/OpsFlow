from django import forms
from django.core.exceptions import ValidationError
from .models import Task, Comment
from teams.models import Team, TeamMember
from accounts.models import User

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'status', 'priority', 'due_date', 'team', 'assigned_to', 'attachment']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Filter teams: Admin sees all, Team Leads see teams they lead, Members see nothing (they shouldn't reach this form)
            if user.is_admin():
                self.fields['team'].queryset = Team.objects.all().order_by('name')
            else:
                self.fields['team'].queryset = Team.objects.filter(
                    memberships__user=user,
                    memberships__role=TeamMember.LEAD
                ).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        team = cleaned_data.get('team')
        assigned_to = cleaned_data.get('assigned_to')
        
        if team and assigned_to:
            # Check if assignee belongs to the selected team
            is_member = TeamMember.objects.filter(team=team, user=assigned_to).exists()
            if not is_member:
                raise ValidationError({
                    'assigned_to': f"User {assigned_to.get_full_name()} is not a member of the selected team '{team.name}'."
                })
        return cleaned_data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write a comment or post an update...'}),
        }


class QuickStatusForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['status']
