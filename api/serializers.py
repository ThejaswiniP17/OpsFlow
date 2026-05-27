from rest_framework import serializers
from accounts.models import User
from teams.models import Team, TeamMember
from tasks.models import Task, Comment
from notifications.models import Notification
from activity_logs.models import ActivityLog

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'bio', 'profile_picture']
        read_only_fields = ['id', 'role']


class TeamMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = TeamMember
        fields = ['id', 'user', 'user_id', 'role', 'joined_at']


class TeamSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    members_count = serializers.IntegerField(source='memberships.count', read_only=True)

    class Meta:
        model = Team
        fields = ['id', 'name', 'description', 'created_by', 'created_at', 'members_count']
        read_only_fields = ['id', 'created_by', 'created_at']


class TaskSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'status', 'priority', 'due_date',
            'team', 'team_name', 'assigned_to', 'assigned_to_name', 
            'created_by', 'created_by_name', 'attachment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def validate(self, attrs):
        team = attrs.get('team') or (self.instance.team if self.instance else None)
        assigned_to = attrs.get('assigned_to') or (self.instance.assigned_to if self.instance else None)
        
        if team and assigned_to:
            # Validate that assignee is member of the team
            is_member = TeamMember.objects.filter(team=team, user=assigned_to).exists()
            if not is_member:
                raise serializers.ValidationError(
                    {"assigned_to": f"User is not a member of the selected team '{team.name}'."}
                )
        return attrs


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'task', 'user', 'content', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'is_read', 'created_at']
        read_only_fields = ['id', 'title', 'message', 'created_at']


class ActivityLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = ActivityLog
        fields = ['id', 'actor_username', 'action_type', 'description', 'task', 'task_title', 'team', 'team_name', 'timestamp']
        read_only_fields = ['id', 'timestamp']
