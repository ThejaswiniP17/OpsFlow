from django.urls import path
from .views import index_view, notifications_view, mark_all_notifications_read

app_name = 'dashboard'

urlpatterns = [
    path('', index_view, name='index'),
    path('notifications/', notifications_view, name='notifications'),
    path('notifications/read-all/', mark_all_notifications_read, name='mark_all_read'),
]
