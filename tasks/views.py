from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from .models import Task, Comment
from .forms import TaskForm, CommentForm, QuickStatusForm
from teams.models import Team, TeamMember
from activity_logs.utils import log_activity  # Phase 6
from notifications.utils import notify_user  # Phase 6

class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'tasks/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        
        # Base query: Admin sees all tasks; Member/Team Lead sees tasks from teams they are in
        if user.is_admin():
            queryset = Task.objects.all()
        else:
            queryset = Task.objects.filter(team__memberships__user=user)
            
        # Apply Search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
            
        # Apply Filters
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        priority_filter = self.request.GET.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
            
        team_filter = self.request.GET.get('team')
        if team_filter:
            queryset = queryset.filter(team_id=team_filter)
            
        assignee_filter = self.request.GET.get('assignee')
        if assignee_filter == 'me':
            queryset = queryset.filter(assigned_to=user)
        elif assignee_filter and assignee_filter.isdigit():
            queryset = queryset.filter(assigned_to_id=assignee_filter)
            
        return queryset.distinct().select_related('team', 'assigned_to').order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Populate filter choices in the template
        if user.is_admin():
            context['filter_teams'] = Team.objects.all()
        else:
            context['filter_teams'] = Team.objects.filter(memberships__user=user)
            
        context['status_choices'] = Task.STATUS_CHOICES
        context['priority_choices'] = Task.PRIORITY_CHOICES
        
        # Retain GET parameter filters for pagination links
        get_copy = self.request.GET.copy()
        if 'page' in get_copy:
            get_copy.pop('page')
        context['query_params'] = get_copy.urlencode()
        
        return context


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = 'tasks/task_detail.html'
    context_object_name = 'task'

    def get_object(self, queryset=None):
        task = super().get_object(queryset)
        # Verify user belongs to the team that owns the task (unless Admin)
        if not self.request.user.is_admin() and not TeamMember.objects.filter(team=task.team, user=self.request.user).exists():
            raise PermissionDenied("You do not have access to view this task.")
        return task

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.get_object()
        
        # Permissions flags
        user_membership = TeamMember.objects.filter(team=task.team, user=self.request.user).first()
        context['is_lead'] = (user_membership and user_membership.role == TeamMember.LEAD) or self.request.user.is_admin()
        context['is_assignee'] = task.assigned_to == self.request.user
        
        context['comments'] = task.comments.all().select_related('user').order_by('-created_at')
        context['comment_form'] = CommentForm()
        context['status_form'] = QuickStatusForm(instance=task)
        
        # List of other members in the team (for re-assigning task inside detail view)
        context['team_members'] = TeamMember.objects.filter(team=task.team).select_related('user')
        
        return context


class TaskCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'
    success_url = reverse_lazy('tasks:task_list')

    def test_func(self):
        # Only Team Leads and Admins can create tasks
        return self.request.user.is_team_lead()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        team_id = self.request.GET.get('team')
        if team_id:
            initial['team'] = team_id
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        # Log this audit log activity
        log_activity(
            actor=self.request.user,
            action_type='TASK_CREATE',
            description=f"Created task #{self.object.id} '{self.object.title}' in team '{self.object.team.name}'",
            task=self.object,
            team=self.object.team
        )
        
        # If assigned, send notification
        if self.object.assigned_to:
            notify_user(
                recipient=self.object.assigned_to,
                title="New Task Assignment",
                message=f"You have been assigned to task: '{self.object.title}' under team {self.object.team.name}."
            )
            
        messages.success(self.request, f"Task '{self.object.title}' created successfully!")
        return response


class TaskUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'

    def get_success_url(self):
        return reverse_lazy('tasks:task_detail', kwargs={'pk': self.object.pk})

    def test_func(self):
        task = self.get_object()
        # Allow editing if User is Admin, or Team Lead of this team, or Task Creator
        is_lead = TeamMember.objects.filter(team=task.team, user=self.request.user, role=TeamMember.LEAD).exists()
        return self.request.user.is_admin() or is_lead or task.created_by == self.request.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        old_task = Task.objects.get(pk=self.get_object().pk)
        response = super().form_valid(form)
        
        # Track changes for Activity Logging
        changes = []
        if old_task.status != self.object.status:
            changes.append(f"status from '{old_task.get_status_display()}' to '{self.object.get_status_display()}'")
        if old_task.assigned_to != self.object.assigned_to:
            old_name = old_task.assigned_to.username if old_task.assigned_to else "Unassigned"
            new_name = self.object.assigned_to.username if self.object.assigned_to else "Unassigned"
            changes.append(f"assignee from {old_name} to {new_name}")
            
            # Send notification to new assignee
            if self.object.assigned_to:
                notify_user(
                    recipient=self.object.assigned_to,
                    title="Task Assignment Update",
                    message=f"You have been assigned to task: '{self.object.title}' under team {self.object.team.name}."
                )
                
        if old_task.priority != self.object.priority:
            changes.append(f"priority from '{old_task.get_priority_display()}' to '{self.object.get_priority_display()}'")

        change_desc = f"Updated task #{self.object.id} '{self.object.title}': " + (", ".join(changes) if changes else "edited task details")
        
        log_activity(
            actor=self.request.user,
            action_type='TASK_UPDATE',
            description=change_desc,
            task=self.object,
            team=self.object.team
        )
        
        messages.success(self.request, "Task updated successfully!")
        return response


class TaskDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Task
    template_name = 'tasks/task_confirm_delete.html'
    success_url = reverse_lazy('tasks:task_list')

    def test_func(self):
        task = self.get_object()
        # Allow deleting if user is Admin, or Team Lead of this team
        is_lead = TeamMember.objects.filter(team=task.team, user=self.request.user, role=TeamMember.LEAD).exists()
        return self.request.user.is_admin() or is_lead

    def form_valid(self, form):
        task = self.get_object()
        log_activity(
            actor=self.request.user,
            action_type='TASK_DELETE',
            description=f"Deleted task #{task.id} '{task.title}'",
            team=task.team
        )
        messages.success(self.request, "Task deleted successfully.")
        return super().form_valid(form)


@login_required
def add_comment(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    # Check permission (must belong to task's team, or be Admin)
    is_member = TeamMember.objects.filter(team=task.team, user=request.user).exists()
    if not is_member and not request.user.is_admin():
        raise PermissionDenied("You cannot comment on this task.")
        
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task
            comment.user = request.user
            comment.save()
            
            log_activity(
                actor=request.user,
                action_type='TASK_COMMENT',
                description=f"Commented on task #{task.id} '{task.title}': '{comment.content[:30]}...'",
                task=task,
                team=task.team
            )
            
            # Notify task assignee if someone else comments
            if task.assigned_to and task.assigned_to != request.user:
                notify_user(
                    recipient=task.assigned_to,
                    title="New Comment on Task",
                    message=f"{request.user.get_full_name()} commented on task: '{task.title}'."
                )
                
            messages.success(request, "Comment posted successfully!")
            
    return redirect('tasks:task_detail', pk=pk)


@login_required
def quick_update_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    # Check permissions: must belong to the team, or be Admin
    is_member = TeamMember.objects.filter(team=task.team, user=request.user).exists()
    if not is_member and not request.user.is_admin():
        raise PermissionDenied("You do not have access to modify this task.")
        
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'status':
            old_status = task.get_status_display()
            new_status_val = request.POST.get('status')
            
            if new_status_val in dict(Task.STATUS_CHOICES):
                task.status = new_status_val
                task.save()
                
                log_activity(
                    actor=request.user,
                    action_type='TASK_STATUS_CHANGE',
                    description=f"Changed status of task #{task.id} '{task.title}' from '{old_status}' to '{task.get_status_display()}'",
                    task=task,
                    team=task.team
                )
                
                # Notify task creator if someone else changes status
                if task.created_by and task.created_by != request.user:
                    notify_user(
                        recipient=task.created_by,
                        title="Task Status Updated",
                        message=f"{request.user.get_full_name()} updated task: '{task.title}' to '{task.get_status_display()}'."
                    )
                    
                messages.success(request, f"Task status updated to {task.get_status_display()}.")
                
        elif action == 'assignee':
            # Only Team Leads or Admin can change assignee
            is_lead = TeamMember.objects.filter(team=task.team, user=request.user, role=TeamMember.LEAD).exists() or request.user.is_admin()
            if not is_lead:
                raise PermissionDenied("Only Team Leads can reassign tasks.")
                
            new_assignee_id = request.POST.get('assigned_to')
            old_assignee = task.assigned_to
            
            if new_assignee_id:
                new_assignee = get_object_or_404(User, id=new_assignee_id)
                # Verify that assignee is member of the team
                if not TeamMember.objects.filter(team=task.team, user=new_assignee).exists():
                    messages.error(request, "Selected assignee is not in this team.")
                    return redirect('tasks:task_detail', pk=pk)
                task.assigned_to = new_assignee
            else:
                task.assigned_to = None
                
            task.save()
            
            old_name = old_assignee.username if old_assignee else "Unassigned"
            new_name = task.assigned_to.username if task.assigned_to else "Unassigned"
            
            log_activity(
                actor=request.user,
                action_type='TASK_ASSIGN',
                description=f"Reassigned task #{task.id} '{task.title}' from {old_name} to {new_name}",
                task=task,
                team=task.team
            )
            
            # Notify new assignee
            if task.assigned_to and task.assigned_to != request.user:
                notify_user(
                    recipient=task.assigned_to,
                    title="Task Assigned to You",
                    message=f"You have been assigned to task: '{task.title}' under team {task.team.name}."
                )
                
            messages.success(request, f"Task assigned to {new_name}.")
            
    return redirect('tasks:task_detail', pk=pk)
