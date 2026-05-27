from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import PermissionDenied
from accounts.models import User
from teams.models import Team, TeamMember
from tasks.models import Task, Comment
from notifications.models import Notification
from activity_logs.models import ActivityLog
from activity_logs.utils import log_activity
from notifications.utils import notify_user
from .serializers import (
    UserSerializer, TeamSerializer, TeamMemberSerializer,
    TaskSerializer, CommentSerializer, NotificationSerializer, ActivityLogSerializer
)

class TeamViewSet(viewsets.ModelViewSet):
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin():
            return Team.objects.all()
        return Team.objects.filter(memberships__user=user)

    def perform_create(self, serializer):
        if not self.request.user.is_team_lead():
            raise PermissionDenied("Only Team Leads or Admins can create teams.")
        team = serializer.save(created_by=self.request.user)
        # Auto-assign creator as Team Lead
        TeamMember.objects.create(team=team, user=self.request.user, role=TeamMember.LEAD)
        log_activity(self.request.user, 'TEAM_CREATE', f"Created team '{team.name}' (API)", team=team)

    @action(detail=True, methods=['get', 'post'])
    def members(self, request, pk=None):
        team = self.get_object()
        # Permission check: must belong to the team
        is_member = TeamMember.objects.filter(team=team, user=request.user).exists()
        if not is_member and not request.user.is_admin():
            raise PermissionDenied("You do not belong to this team.")

        if request.method == 'GET':
            memberships = TeamMember.objects.filter(team=team).select_related('user')
            serializer = TeamMemberSerializer(memberships, many=True)
            return Response(serializer.data)

        # POST: Add member
        # Permission check: must be Lead or Admin
        is_lead = TeamMember.objects.filter(team=team, user=request.user, role=TeamMember.LEAD).exists() or request.user.is_admin()
        if not is_lead:
            raise PermissionDenied("Only Team Leads can add members.")

        serializer = TeamMemberSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            role = serializer.validated_data.get('role', TeamMember.MEMBER)
            
            if TeamMember.objects.filter(team=team, user=user).exists():
                return Response({"detail": "User is already a member of this team."}, status=status.HTTP_400_BAD_REQUEST)
                
            member = TeamMember.objects.create(team=team, user=user, role=role)
            log_activity(request.user, 'TEAM_MEMBER_ADD', f"Added {user.username} to team '{team.name}' (API)", team=team)
            
            return Response(TeamMemberSerializer(member).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description']

    def get_queryset(self):
        user = self.request.user
        if user.is_admin():
            queryset = Task.objects.all()
        else:
            queryset = Task.objects.filter(team__memberships__user=user)

        # Apply basic status/priority filters manually
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        priority_param = self.request.query_params.get('priority')
        if priority_param:
            queryset = queryset.filter(priority=priority_param)

        team_param = self.request.query_params.get('team')
        if team_param:
            queryset = queryset.filter(team_id=team_param)

        return queryset.distinct().select_related('team', 'assigned_to', 'created_by')

    def perform_create(self, serializer):
        # Must be Team Lead or Admin
        if not self.request.user.is_team_lead():
            raise PermissionDenied("Only Team Leads or Admins can create tasks.")
            
        task = serializer.save(created_by=self.request.user)
        log_activity(self.request.user, 'TASK_CREATE', f"Created task '{task.title}' (API)", task=task, team=task.team)
        
        if task.assigned_to:
            notify_user(task.assigned_to, "Task Assignment", f"You have been assigned to task: '{task.title}' (API)")

    def perform_update(self, serializer):
        task = self.get_object()
        # Must be Admin, Team Lead of that team, or task creator
        is_lead = TeamMember.objects.filter(team=task.team, user=self.request.user, role=TeamMember.LEAD).exists() or self.request.user.is_admin()
        is_creator = task.created_by == self.request.user
        
        # Exception: members can update task status
        if not (is_lead or is_creator):
            if set(serializer.validated_data.keys()) == {'status'}:
                # Only updating status is allowed
                pass
            else:
                raise PermissionDenied("You do not have permission to modify task details.")

        old_status = task.status
        old_assignee = task.assigned_to
        updated_task = serializer.save()

        # Track and log changes
        changes = []
        if old_status != updated_task.status:
            changes.append(f"status from '{old_status}' to '{updated_task.status}'")
        if old_assignee != updated_task.assigned_to:
            old_name = old_assignee.username if old_assignee else "None"
            new_name = updated_task.assigned_to.username if updated_task.assigned_to else "None"
            changes.append(f"assignee from '{old_name}' to '{new_name}'")
            if updated_task.assigned_to:
                notify_user(updated_task.assigned_to, "Task Reassigned", f"You have been assigned to task: '{updated_task.title}'")

        log_activity(
            self.request.user, 
            'TASK_UPDATE', 
            f"Updated task '{updated_task.title}': " + (", ".join(changes) if changes else "modified properties"), 
            task=updated_task, 
            team=updated_task.team
        )

    def perform_destroy(self, instance):
        is_lead = TeamMember.objects.filter(team=instance.team, user=self.request.user, role=TeamMember.LEAD).exists() or self.request.user.is_admin()
        if not is_lead:
            raise PermissionDenied("Only Team Leads or Admins can delete tasks.")
        log_activity(self.request.user, 'TASK_DELETE', f"Deleted task '{instance.title}'", team=instance.team)
        instance.delete()


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"detail": "All notifications marked as read."}, status=status.HTTP_200_OK)


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin():
            return ActivityLog.objects.all().order_by('-timestamp')
        user_team_ids = TeamMember.objects.filter(user=user).values_list('team_id', flat=True)
        return ActivityLog.objects.filter(team_id__in=user_team_ids).order_by('-timestamp')
