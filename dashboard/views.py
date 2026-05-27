from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import date, timedelta
from tasks.models import Task
from teams.models import Team, TeamMember
from activity_logs.models import ActivityLog
from notifications.models import Notification

@login_required
def index_view(request):
    user = request.user
    today = date.today()
    
    # 1. Base Query Set Scoped by Roles
    if user.is_admin():
        task_qs = Task.objects.all()
        teams = Team.objects.all()
        activities = ActivityLog.objects.all().select_related('actor', 'task', 'team').order_by('-timestamp')[:8]
    else:
        # Get teams user is member of
        user_team_ids = TeamMember.objects.filter(user=user).values_list('team_id', flat=True)
        task_qs = Task.objects.filter(team_id__in=user_team_ids)
        teams = Team.objects.filter(id__in=user_team_ids)
        activities = ActivityLog.objects.filter(team_id__in=user_team_ids).select_related('actor', 'task', 'team').order_by('-timestamp')[:8]
        
    # 2. Compute Summary Metrics
    total_tasks = task_qs.count()
    completed_tasks = task_qs.filter(status=Task.COMPLETED).count()
    pending_tasks = task_qs.filter(status=Task.PENDING).count()
    blocked_tasks = task_qs.filter(status=Task.BLOCKED).count()
    
    # Overdue tasks: due_date in past, and not completed or closed
    overdue_tasks = task_qs.filter(
        due_date__lt=today,
        status__in=[Task.PENDING, Task.IN_PROGRESS, Task.BLOCKED]
    ).count()
    
    # 3. Chart Data Aggregations
    # A. Status breakdown
    status_data = {
        'PENDING': task_qs.filter(status=Task.PENDING).count(),
        'IN_PROGRESS': task_qs.filter(status=Task.IN_PROGRESS).count(),
        'COMPLETED': completed_tasks,
        'BLOCKED': blocked_tasks,
        'CLOSED': task_qs.filter(status=Task.CLOSED).count(),
    }
    
    # B. Priority breakdown
    priority_data = {
        'LOW': task_qs.filter(priority=Task.LOW).count(),
        'MEDIUM': task_qs.filter(priority=Task.MEDIUM).count(),
        'HIGH': task_qs.filter(priority=Task.HIGH).count(),
        'CRITICAL': task_qs.filter(priority=Task.CRITICAL).count(),
    }
    
    # C. Weekly Completion Trend (last 7 days completed tasks)
    trend_dates = []
    trend_counts = []
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        trend_dates.append(target_date.strftime('%b %d'))
        
        # Count tasks completed on target_date
        # Need to parse tasks where updated_at falls on target_date and status is COMPLETED
        completed_on_day = task_qs.filter(
            status=Task.COMPLETED,
            updated_at__date=target_date
        ).count()
        trend_counts.append(completed_on_day)

    context = {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'blocked_tasks': blocked_tasks,
        'overdue_tasks': overdue_tasks,
        'teams_count': teams.count(),
        
        # Chart Data Lists
        'status_labels': list(status_data.keys()),
        'status_values': list(status_data.values()),
        'priority_labels': list(priority_data.keys()),
        'priority_values': list(priority_data.values()),
        'trend_labels': trend_dates,
        'trend_values': trend_counts,
        
        'recent_activities': activities,
    }
    
    return render(request, 'dashboard/index.html', context)


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    return render(request, 'dashboard/notifications.html', {'notifications': notifications})


@login_required
def mark_all_notifications_read(request):
    if request.method == 'POST':
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect('dashboard:notifications')
