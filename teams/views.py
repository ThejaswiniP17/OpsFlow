from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from .models import Team, TeamMember
from accounts.models import User
from activity_logs.utils import log_activity  # We will define this helper in Phase 6

class TeamListView(LoginRequiredMixin, ListView):
    model = Team
    template_name = 'teams/team_list.html'
    context_object_name = 'teams'

    def get_queryset(self):
        # Admins see all teams, other roles see only teams they belong to
        if self.request.user.is_admin():
            return Team.objects.all().order_by('name')
        return Team.objects.filter(memberships__user=self.request.user).distinct().order_by('name')


class TeamDetailView(LoginRequiredMixin, DetailView):
    model = Team
    template_name = 'teams/team_detail.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.get_object()
        
        # User role in this team
        user_membership = TeamMember.objects.filter(team=team, user=self.request.user).first()
        context['user_role'] = user_membership.role if user_membership else None
        context['is_lead'] = (user_membership and user_membership.role == TeamMember.LEAD) or self.request.user.is_admin()
        
        # Team members list
        context['members'] = TeamMember.objects.filter(team=team).select_related('user')
        
        # All active users not currently in the team, to display in the "Add Member" dropdown
        existing_user_ids = TeamMember.objects.filter(team=team).values_list('user_id', flat=True)
        context['available_users'] = User.objects.exclude(id__in=existing_user_ids).filter(is_active=True).order_by('username')
        
        # Tasks assigned to this team
        context['tasks'] = team.tasks.all().select_related('assigned_to').order_by('-updated_at')
        
        return context

    def get_object(self, queryset=None):
        team = super().get_object(queryset)
        # Check boundary security scope
        if not self.request.user.is_admin() and not TeamMember.objects.filter(team=team, user=self.request.user).exists():
            raise PermissionDenied("You are not a member of this team.")
        return team


class TeamCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Team
    fields = ['name', 'description']
    template_name = 'teams/team_form.html'
    success_url = reverse_lazy('teams:team_list')

    def test_func(self):
        return self.request.user.is_team_lead()

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        # Auto-assign creator as Team Lead in the TeamMember association
        TeamMember.objects.create(
            team=self.object,
            user=self.request.user,
            role=TeamMember.LEAD
        )
        
        # Log this audit log activity
        log_activity(
            actor=self.request.user,
            action_type='TEAM_CREATE',
            description=f"Created team '{self.object.name}'",
            team=self.object
        )
        
        messages.success(self.request, f"Team '{self.object.name}' created successfully!")
        return response


@login_required
def add_team_member(request, pk):
    team = get_object_or_404(Team, pk=pk)
    
    # Check if active user has permission to add members
    is_lead = TeamMember.objects.filter(team=team, user=request.user, role=TeamMember.LEAD).exists() or request.user.is_admin()
    if not is_lead:
        raise PermissionDenied("You do not have permission to add members to this team.")
        
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        role = request.POST.get('role', TeamMember.MEMBER)
        
        if user_id:
            user = get_object_or_404(User, id=user_id)
            try:
                member = TeamMember.objects.create(team=team, user=user, role=role)
                
                log_activity(
                    actor=request.user,
                    action_type='TEAM_MEMBER_ADD',
                    description=f"Added {user.username} to team '{team.name}' as {member.get_role_display()}",
                    team=team
                )
                
                messages.success(request, f"User {user.get_full_name()} added to the team.")
            except IntegrityError:
                messages.error(request, "This user is already a member of the team.")
                
    return redirect('teams:team_detail', pk=pk)


@login_required
def remove_team_member(request, pk, member_id):
    team = get_object_or_404(Team, pk=pk)
    member = get_object_or_404(TeamMember, pk=member_id, team=team)
    
    # Check if user has permission
    is_lead = TeamMember.objects.filter(team=team, user=request.user, role=TeamMember.LEAD).exists() or request.user.is_admin()
    if not is_lead:
        raise PermissionDenied("You do not have permission to remove members.")
        
    # Prevent self-removal if they are the only lead
    if member.user == request.user and member.role == TeamMember.LEAD:
        # Check if there are other leads
        other_leads = TeamMember.objects.filter(team=team, role=TeamMember.LEAD).exclude(id=member_id).exists()
        if not other_leads:
            messages.error(request, "You cannot remove yourself because you are the sole Team Lead.")
            return redirect('teams:team_detail', pk=pk)

    user_username = member.user.username
    member.delete()
    
    log_activity(
        actor=request.user,
        action_type='TEAM_MEMBER_REMOVE',
        description=f"Removed {user_username} from team '{team.name}'",
        team=team
    )
    
    messages.success(request, f"User {user_username} has been removed from the team.")
    return redirect('teams:team_detail', pk=pk)
