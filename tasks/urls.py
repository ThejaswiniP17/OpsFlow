from django.urls import path
from .views import (
    TaskListView, TaskDetailView, TaskCreateView, 
    TaskUpdateView, TaskDeleteView, add_comment, quick_update_task
)

app_name = 'tasks'

urlpatterns = [
    path('', TaskListView.as_view(), name='task_list'),
    path('<int:pk>/', TaskDetailView.as_view(), name='task_detail'),
    path('create/', TaskCreateView.as_view(), name='task_create'),
    path('<int:pk>/edit/', TaskUpdateView.as_view(), name='task_update'),
    path('<int:pk>/delete/', TaskDeleteView.as_view(), name='task_delete'),
    path('<int:pk>/comment/', add_comment, name='add_comment'),
    path('<int:pk>/quick-update/', quick_update_task, name='quick_update'),
]
