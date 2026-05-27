from django.urls import path
from .views import TeamListView, TeamDetailView, TeamCreateView, add_team_member, remove_team_member

app_name = 'teams'

urlpatterns = [
    path('', TeamListView.as_view(), name='team_list'),
    path('<int:pk>/', TeamDetailView.as_view(), name='team_detail'),
    path('create/', TeamCreateView.as_view(), name='team_create'),
    path('<int:pk>/add-member/', add_team_member, name='add_team_member'),
    path('<int:pk>/remove-member/<int:member_id>/', remove_team_member, name='remove_team_member'),
]
